#!/usr/bin/env python3
"""Shared utilities for the benchmark dashboards.

Used by `generate_dashboard.py` (full benchmark) and
`generate_parallel_dashboard.py` (parallel-tasks sweet-spot dashboard).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import bleach
import jinja2
import markdown

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_CSV = SCRIPT_DIR / "data.csv"
TEXT_MD = SCRIPT_DIR / "text.md"
RESULTS_DIR = SCRIPT_DIR / "results"
TEMPLATE_MAIN = SCRIPT_DIR / "template-main.html"
TEMPLATE_DETAIL = SCRIPT_DIR / "template-detail.html"
OUTPUT_MAIN = SCRIPT_DIR / "benchmark-main.html"
OUTPUT_DETAIL = SCRIPT_DIR / "benchmark-detail.html"

# Normalised CSV header label -> field name used by the templates.
HEADER_NAMES = {
    "base": "base",
    "model name": "model",
    "reasoning effort": "reasoning_effort",
    "total params (b)": "total_params",
    "active params (b)": "active_params",
    "n-grams params (b)": "ngram_params",
    "model size (gb)": "model_size",
    "weights quantization": "weights_quant",
    "kv cache quantization": "kv_cache_quant",
    "ple quantization": "ple_quant",
    "engine": "engine",
    "nb gpu": "nb_gpu",
    "spec": "spec",
    "license": "license",
    "model ref": "model_ref",
    "max kv ktokens": "max_kv_ktokens",
    "score /100": "score",
    "duration": "duration",
    "requests": "requests",
    "req/pts": "req_pts",
    "in mtok": "tokens_processed_mt",
    "out mtok": "tokens_generated_mt",
    "total tg/s": "total_tg_s",
    "parallel tasks": "parallel_tasks",
    "tg/s per task": "tg_s_per_task",
    "total cost $": "total_cost",
    "ktok/pt": "ktok_per_pt",
    "gen tok /req": "gen_tok_per_req",
    "notes": "notes",
}

DECIMAL_FIELDS = (
    "score",
    "requests",
    "req_pts",
    "tokens_processed_mt",
    "tokens_generated_mt",
    "total_tg_s",
    "parallel_tasks",
    "tg_s_per_task",
)

NUMERIC_FIELDS = {
    "score": "score_num",
    "total_params": "total_params_num",
    "active_params": "active_params_num",
    "ngram_params": "ngram_params_num",
    "model_size": "model_size_num",
    "requests": "requests_num",
    "req_pts": "req_pts_num",
    "tokens_processed_mt": "tokens_processed_num",
    "tokens_generated_mt": "tokens_generated_num",
    "total_tg_s": "total_tg_s_num",
    "parallel_tasks": "parallel_tasks_num",
    "tg_s_per_task": "tg_s_per_task_num",
    "total_cost": "total_cost_num",
}

SAFE_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "code",
    "pre",
    "a",
    "hr",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]
SAFE_ATTRS = ["href", "title", "rel"]


def parse_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    header_row = next((i for i, row in enumerate(rows) if "score" in _header_columns(row)), None)
    if header_row is None:
        return []
    cols = _header_columns(rows[header_row])

    records: list[dict] = []
    for row in rows[header_row + 1 :]:
        if not row or not row[0].strip():
            continue
        if len(row) <= cols["score"] or not _is_score_cell(row[cols["score"]].strip()):
            continue
        rec: dict = {name: (row[ci].strip() if ci < len(row) else "") for name, ci in cols.items()}
        _normalise_record(rec)
        records.append(rec)

    for i, rec in enumerate(records):
        rec["__idx"] = i

    return records


def _header_columns(row: list[str]) -> dict[str, int]:
    """Map field names to their column index, so CSV columns can be reordered freely."""
    return {
        field: ci
        for ci, label in enumerate(row)
        if (field := HEADER_NAMES.get(re.sub(r"\s+", " ", label).strip().lower()))
    }


def _is_score_cell(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if s.lower().startswith("crash"):
        return True
    return _parse_decimal(s) is not None


def _parse_decimal(s: str) -> float | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    if s.lower() in ("crash...", "crash", "#div/0!"):
        return None
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return None
    if re.fullmatch(r"-?\d+,\d{1,2}", s):
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _duration_to_seconds(s: str) -> int | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None
    return None


def _normalise_record(rec: dict) -> dict:
    rec["score_num"] = _parse_decimal(rec.get("score", ""))
    rec["duration_s"] = _duration_to_seconds(rec.get("duration", ""))
    for src, dst in NUMERIC_FIELDS.items():
        if dst == "score_num":
            continue
        rec[dst] = _parse_decimal(rec.get(src, ""))
    return rec


def render_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    html_body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return bleach.clean(
        html_body,
        tags=SAFE_TAGS,
        attributes=SAFE_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def render_html(template_path: Path, output_path: Path, **context) -> None:
    """Render a Jinja2 template with the given context and write the output."""
    env = jinja2.Environment(autoescape=False)
    template_src = template_path.read_text(encoding="utf-8")
    html = env.from_string(template_src).render(**context)
    if not html.endswith("\n"):
        html += "\n"
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to {output_path}")


def render_dashboard(
    *,
    csv_path: Path = DATA_CSV,
    md_path: Path = TEXT_MD,
    template_path: Path = TEMPLATE_MAIN,
    output_path: Path = OUTPUT_MAIN,
) -> None:
    """Parse CSV + Markdown, render the main dashboard template, write the HTML."""
    records = parse_csv(csv_path)
    valid = [r for r in records if r["score_num"] is not None]
    print(f"Parsed {len(records)} records from {csv_path} ({len(valid)} with valid score)")

    md_html = render_markdown(md_path)
    json_str = json.dumps(records, ensure_ascii=False)
    render_html(template_path, output_path, md_html=md_html, json_data=json_str)
