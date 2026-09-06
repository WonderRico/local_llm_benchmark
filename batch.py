#!/usr/bin/env python3
"""Batch-process all model/variant directories under data/ and save results."""

import csv
import shutil
from pathlib import Path

from aggregator import aggregate
from parser import parse_dir
from render import format_duration, render_aggregate, render_failures, render_table
from traj_html import HTML_TRAJ_DIR, build_traj_html

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
STATS_CSV = Path(__file__).parent / "stats.csv"


def find_variant_dirs(data_dir: Path) -> list[Path]:
    """Find all variant directories that contain .traj.json files."""
    variants: list[Path] = []
    for model_dir in sorted(data_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        for variant_dir in sorted(model_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            if list(variant_dir.rglob("*.traj.json")):
                variants.append(variant_dir)
    return variants


def process_variant(variant_dir: Path, results_root: Path, *, with_traj_html: bool = True) -> dict | None:
    """Parse all trajectories in a variant and write summary/table/failures."""
    rel = variant_dir.relative_to(DATA_DIR)
    out_dir = results_root / rel
    out_dir.mkdir(parents=True, exist_ok=True)

    trajs = parse_dir(variant_dir, recursive=True)
    if not trajs:
        return None

    if with_traj_html:
        build_traj_html(variant_dir, HTML_TRAJ_DIR / rel)

    # Run span: earliest to latest tool timestamp across the whole variant,
    # not the sum of per-trajectory wall times.
    timestamps = [ts for t in trajs for ts in t.timestamps]

    stats = {
        "variant": str(rel),
        "requests": sum(t.requests for t in trajs),
        "request_time_seconds": round(sum(t.request_time_seconds for t in trajs), 1),
        "wall_time_seconds": round(max(timestamps) - min(timestamps), 1) if timestamps else 0.0,
        "input_tokens": sum(t.input_tokens for t in trajs),
        "output_tokens": sum(t.output_tokens for t in trajs),
    }
    print(
        f"{rel}: {stats['requests']} requests | "
        f"request time {format_duration(stats['request_time_seconds'])} | "
        f"wall time {format_duration(stats['wall_time_seconds'])} | "
        f"tokens in={stats['input_tokens']:,} out={stats['output_tokens']:,}"
    )

    (out_dir / "summary.txt").write_text(render_aggregate(aggregate(trajs)) + "\n")
    (out_dir / "table.txt").write_text(render_table(trajs) + "\n")
    (out_dir / "failures.txt").write_text(render_failures(trajs) + "\n")

    eval_src = variant_dir / "eval.json"
    if eval_src.exists():
        shutil.copy2(eval_src, out_dir / "eval.json")

    return stats


def main(*, with_traj_html: bool = True) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    variants = find_variant_dirs(DATA_DIR)
    stats_rows = [s for vd in variants if (s := process_variant(vd, RESULTS_DIR, with_traj_html=with_traj_html))]

    if stats_rows:
        with STATS_CSV.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(stats_rows[0]))
            writer.writeheader()
            writer.writerows(stats_rows)

    print(
        f"Processed {len(variants)} variant(s). Results saved to {RESULTS_DIR}, "
        f"trajectory pages to {HTML_TRAJ_DIR}, aggregate stats to {STATS_CSV}"
    )


if __name__ == "__main__":
    main()
