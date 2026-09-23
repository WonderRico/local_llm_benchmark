#!/usr/bin/env python3
"""Shared utilities for the benchmark dashboards."""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

import bleach
import jinja2
import markdown

SCRIPT_DIR = Path(__file__).resolve().parent
STATS_CSV = SCRIPT_DIR / "stats.csv"
TEXT_MD = SCRIPT_DIR / "text.md"
RESULTS_DIR = SCRIPT_DIR / "results"
TEMPLATE_MAIN = SCRIPT_DIR / "template-main.html"
TEMPLATE_DETAIL = SCRIPT_DIR / "template-detail.html"
OUTPUT_MAIN = SCRIPT_DIR / "benchmark-main.html"
OUTPUT_DETAIL = SCRIPT_DIR / "benchmark-detail.html"

# Normalised CSV header label -> field name used by the templates.
HEADER_NAMES = {
    "base": "base",
    "variant": "model",
    "wq": "weights_quant",
    "cq": "kv_cache_quant",
    "score": "score",
    "requests": "requests",
    "request_time_seconds": "request_time_s",
    "wall_time_seconds": "duration_s",
    "input_tokens": "tokens_processed_mt",
    "output_tokens": "tokens_generated_mt",
    "req/pt": "req_pts",
}

# stats.csv counts raw tokens; the dashboard reports them in millions.
SCALES = {"tokens_processed_mt": 1e-6, "tokens_generated_mt": 1e-6}

NUMERIC_FIELDS = {
    "requests": "requests_num",
    "req_pts": "req_pts_num",
    "request_time_s": "request_time_s_num",
    "tokens_processed_mt": "tokens_processed_num",
    "tokens_generated_mt": "tokens_generated_num",
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


def _normalise_record(rec: dict) -> dict:
    for field, scale in SCALES.items():
        if (v := _parse_decimal(rec.get(field, ""))) is not None:
            rec[field] = f"{v * scale:.1f}"
    rec["score_num"] = _parse_decimal(rec.get("score", ""))
    for src, dst in NUMERIC_FIELDS.items():
        rec[dst] = _parse_decimal(rec.get(src, ""))
    if (seconds := _parse_decimal(rec.get("duration_s", ""))) is not None:
        rec["duration_s"] = seconds
        rec["duration"] = time.strftime("%H:%M:%S", time.gmtime(seconds))
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


HALL_SECTION = re.compile(r"(<h2>Hall of fame</h2>)(.*?)(?=<h2>|\Z)", re.DOTALL)
UPDATE_BLOCK = re.compile(r"<h3>(.*?)</h3>(.*?)(?=<h3>|\Z)", re.DOTALL)


def collapse_updates(md_html: str) -> str:
    """Fold each Hall of fame update into its own <details>, newest one left open."""

    def fold(section: re.Match) -> str:
        head, *blocks = re.split(r"(?=<h3>)", section[2])
        folded = "".join(
            f"<details{' open' if not i else ''}><summary>{title}</summary>{body}</details>"
            for i, (title, body) in enumerate(UPDATE_BLOCK.findall("".join(blocks)))
        )
        return f"{section[1]}{head}{folded}"

    return HALL_SECTION.sub(fold, md_html)


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
    csv_path: Path = STATS_CSV,
    md_path: Path = TEXT_MD,
    template_path: Path = TEMPLATE_MAIN,
    output_path: Path = OUTPUT_MAIN,
) -> None:
    """Parse CSV + Markdown, render the main dashboard template, write the HTML."""
    records = parse_csv(csv_path)
    valid = [r for r in records if r["score_num"] is not None]
    print(f"Parsed {len(records)} records from {csv_path} ({len(valid)} with valid score)")

    md_html = collapse_updates(render_markdown(md_path))
    json_str = json.dumps(records, ensure_ascii=False)
    render_html(template_path, output_path, md_html=md_html, json_data=json_str)
