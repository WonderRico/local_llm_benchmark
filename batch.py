#!/usr/bin/env python3
"""Batch-process all model/variant directories under data/ and save results."""

from pathlib import Path
import shutil

from parser import parse_dir
from aggregator import aggregate
from render import render_aggregate, render_table, render_failures

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"


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


def process_variant(variant_dir: Path, results_root: Path) -> None:
    """Parse all trajectories in a variant and write summary/table/failures."""
    rel = variant_dir.relative_to(DATA_DIR)
    out_dir = results_root / rel
    out_dir.mkdir(parents=True, exist_ok=True)

    trajs = parse_dir(variant_dir, recursive=True)
    if not trajs:
        return

    (out_dir / "summary.txt").write_text(render_aggregate(aggregate(trajs)) + "\n")
    (out_dir / "table.txt").write_text(render_table(trajs) + "\n")
    (out_dir / "failures.txt").write_text(render_failures(trajs) + "\n")

    eval_src = variant_dir / "eval.json"
    if eval_src.exists():
        shutil.copy2(eval_src, out_dir / "eval.json")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    variants = find_variant_dirs(DATA_DIR)
    for vd in variants:
        process_variant(vd, RESULTS_DIR)

    print(f"Processed {len(variants)} variant(s). Results saved to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
