#!/usr/bin/env python3
"""Generate the benchmark dashboards (both pages from one entry point).

Usage:
    python generate.py               # generate both pages
    python generate.py main          # main dashboard only
    python generate.py detail        # detail report only
    python generate.py detail --skip-batch   # reuse existing results/

The main dashboard (`benchmark-main.html`) is built from `data.csv` + `text.md`.
The detail report (`benchmark-detail.html`) is built from `results/`, which is
regenerated from `data/` trajectories (unless `--skip-batch` is given). Each
trajectory also gets a redacted HTML page under `html_traj/`, mirroring `data/`.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import batch
import dashboard_lib
import typer
from dashboard_lib import RESULTS_DIR
from traj_html import HTML_TRAJ_DIR, html_name

app = typer.Typer(help="Generate the benchmark dashboards (benchmark-main.html, benchmark-detail.html).")

# Trajectory pages stay unlinked unless the report is viewed from the LAN or the serving machine itself.
TRAJ_HOST_RE = r"^(192\.168\.|localhost$|127\.)"


def parse_summary(text: str) -> dict:
    d = {}
    m = re.search(r"Total trajectories:\s*(\d+)", text)
    d["total_trajectories"] = int(m.group(1)) if m else 0
    m = re.search(r"Submitted:\s*(\d+)", text)
    d["submitted"] = int(m.group(1)) if m else 0
    m = re.search(r"Other exits:\s*(\d+)", text)
    d["other_exits"] = int(m.group(1)) if m else 0
    m = re.search(r"Submissions with diff:\s*(\d+)", text)
    d["submissions_with_diff"] = int(m.group(1)) if m else 0

    for label, key in [
        ("API calls", "api"),
        ("Tool calls", "tools"),
    ]:
        m = re.search(
            rf"{label}:\s*avg=([\d.]+),\s*median=([\d.]+),\s*min=(\d+),\s*max=(\d+)",
            text,
        )
        if m:
            d[f"{key}_avg"] = float(m.group(1))
            d[f"{key}_median"] = float(m.group(2))
            d[f"{key}_min"] = int(m.group(3))
            d[f"{key}_max"] = int(m.group(4))

    m = re.search(r"Wall time:\s*avg=(.*?),\s*median=(.*?),\s*min=(.*?),\s*max=(.*)", text)
    if m:
        d["wall_avg"] = m.group(1).strip()
        d["wall_median"] = m.group(2).strip()
        d["wall_min"] = m.group(3).strip()
        d["wall_max"] = m.group(4).strip()

    m = re.search(r"Non-zero return codes:\s*avg=([\d.]+),\s*median=([\d.]+)", text)
    if m:
        d["nonzero_rc_avg"] = float(m.group(1))
        d["nonzero_rc_median"] = float(m.group(2))

    exit_section = re.search(r"Exit statuses:\s*\n((?:\s+.+\n?)*)\n", text)
    if exit_section:
        d["exit_statuses"] = {}
        for line in exit_section.group(1).strip().split("\n"):
            parts = line.strip().split(":")
            if len(parts) == 2 and parts[1].strip().isdigit():
                d["exit_statuses"][parts[0].strip()] = int(parts[1].strip())

    return d


def parse_table(text: str) -> list[dict]:
    rows = []
    pattern = re.compile(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+m\s*\d+s|\d+\.?\d*s)\s+(\d+)\s*$")
    for line in text.split("\n"):
        m = pattern.match(line.strip())
        if m:
            rows.append(
                {
                    "instance": m.group(1),
                    "exit": m.group(2),
                    "api": int(m.group(3)),
                    "tools": int(m.group(4)),
                    "messages": int(m.group(5)),
                    "wall_time": m.group(6),
                    "nonzero_rc": int(m.group(7)),
                }
            )
    return rows


def parse_eval(json_text: str) -> dict:
    d = json.loads(json_text)
    out = {
        "submitted": d.get("submitted_instances", 0),
        "resolved": d.get("resolved_instances", 0),
        "unresolved": d.get("unresolved_instances", 0),
        "empty_patch": d.get("empty_patch_instances", 0),
        "error": d.get("error_instances", 0),
        "instance_status": {},
    }
    for inst in d.get("resolved_ids", []):
        out["instance_status"][inst] = "resolved"
    for inst in d.get("unresolved_ids", []):
        out["instance_status"][inst] = "unresolved"
    for inst in d.get("empty_patch_ids", []):
        out["instance_status"][inst] = "empty_patch"
    for inst in d.get("error_ids", []):
        out["instance_status"][inst] = "error"
    return out


def parse_failures(text: str) -> dict:
    d = {"total_nonzero": 0, "reasons": {}, "per_trajectory": []}
    m = re.match(r"(\d+) non-zero return codes", text)
    if m:
        d["total_nonzero"] = int(m.group(1))

    reason_block = re.search(r"Reason\s+Count\n-+\n((?:[^\n]+\n?)*)", text)
    if reason_block:
        for line in reason_block.group(1).strip().split("\n"):
            parts = line.rsplit(None, 1)
            if len(parts) == 2:
                d["reasons"][parts[0]] = int(parts[1])

    traj_section = re.search(r"Non-zero return codes per trajectory.*?\n((?:[^\n]+\n?)*)", text, re.DOTALL)
    if traj_section:
        header_skipped = False
        for line in traj_section.group(1).strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("Instance") or line.startswith("---"):
                continue
            parts = line.rsplit(None, 1)
            if len(parts) == 2:
                d["per_trajectory"].append({"instance": parts[0], "errors": int(parts[1])})

    return d


def parse_all_results() -> dict:
    """Read results/<model>/<variant>/ into the JSON blob embedded in the detail page."""
    models = {}
    for model_dir in sorted(RESULTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        models[model_name] = {}
        for variant_dir in sorted(model_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            variant_name = variant_dir.name
            display_model_name = f"{model_name} ({variant_name})"
            data: dict = {"model": display_model_name, "variant": variant_name}

            summary_file = variant_dir / "summary.txt"
            if summary_file.exists():
                data["summary"] = parse_summary(summary_file.read_text())

            table_file = variant_dir / "table.txt"
            if table_file.exists():
                data["table"] = parse_table(table_file.read_text())

            failures_file = variant_dir / "failures.txt"
            if failures_file.exists():
                data["failures"] = parse_failures(failures_file.read_text())

            eval_file = variant_dir / "eval.json"
            if eval_file.exists():
                data["eval"] = parse_eval(eval_file.read_text())

            # Hrefs of the human-readable trajectory pages, relative to this page (html_traj/ mirrors data/).
            data["traj"] = {
                f.parent.name: (Path(HTML_TRAJ_DIR.name) / f.relative_to(batch.DATA_DIR))
                .with_name(html_name(f))
                .as_posix()
                for f in sorted((batch.DATA_DIR / model_name / variant_name).rglob("*.traj.json"))
            }

            table = data.get("table")
            if table:
                data["total_tools"] = sum(r["tools"] for r in table)
                data["total_api"] = sum(r["api"] for r in table)
                data["total_nonzero_rc"] = sum(r["nonzero_rc"] for r in table)
            else:
                data["total_tools"] = 0
                data["total_api"] = 0
                data["total_nonzero_rc"] = 0

            models[model_name][variant_name] = data
    return models


def build_detail(*, skip_batch: bool, skip_traj_html: bool = False) -> None:
    if not skip_batch:
        print(f"Cleaning up {RESULTS_DIR}...")
        if RESULTS_DIR.exists():
            shutil.rmtree(RESULTS_DIR)
        print("Regenerating results from data...")
        batch.main(with_traj_html=not skip_traj_html)

    print(f"Scanning {RESULTS_DIR}...")
    data = parse_all_results()

    count = sum(len(v) for v in data.values())
    print(f"Found {len(data)} models, {count} variants")

    json_data = json.dumps(data, indent=2)
    dashboard_lib.render_html(
        dashboard_lib.TEMPLATE_DETAIL,
        dashboard_lib.OUTPUT_DETAIL,
        JSON_DATA=json_data,
        TRAJ_HOST_RE=json.dumps(TRAJ_HOST_RE),
    )


@app.command()
def run(
    which: str = typer.Argument("all", help="Pages to generate: 'all', 'main', or 'detail'"),
    skip_batch: bool = typer.Option(
        False,
        "--skip-batch",
        help="Reuse existing results/ instead of regenerating from data/ (detail only)",
    ),
    skip_traj_html: bool = typer.Option(
        False,
        "--skip-traj-html",
        help="Skip writing html_traj/ trajectory pages (detail only)",
    ),
) -> None:
    if which not in ("all", "main", "detail"):
        typer.echo(f"Unknown page '{which}' (choose: all, main, detail)", err=True)
        raise typer.Exit(code=2)
    if which in ("all", "main"):
        dashboard_lib.render_dashboard()
    if which in ("all", "detail"):
        build_detail(skip_batch=skip_batch, skip_traj_html=skip_traj_html)


if __name__ == "__main__":
    app()
