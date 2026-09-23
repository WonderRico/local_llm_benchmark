#!/usr/bin/env python3
"""Compare every eval.json (original verdicts) with its eval2.json (re-verified run).

Usage:
    python compare_evals.py                  # writes eval-diff.md + eval-diff.csv
    python compare_evals.py --data-dir data-sav --out-prefix eval-diff

Both reports list, per run folder, the resolved/completed/error counts of each file, the
delta, and the instance ids whose verdict flipped. Folders whose pair is missing or
unusable are listed too, so the sweep's progress is visible. A per task flip tally (which
tasks disagree between the two evals most often, and how many runs judged them) goes to
<out-prefix>-flips.csv and, for the tasks that flipped at least once, into the markdown.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import typer

FILES = ("eval.json", "eval2.json")
COUNTS = ("submitted_instances", "completed_instances", "resolved_instances", "error_instances")
OK = ("same", "flipped")


def load(path: Path) -> dict | str | None:
    """None if absent, "invalid" if unreadable: one bad file must not kill the whole report."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "invalid"


def model_name(folder: Path) -> str:
    preds = load(folder / "preds.json")
    first = next(iter(preds.values()), None) if isinstance(preds, dict) else None
    return first.get("model_name_or_path", "") if isinstance(first, dict) else ""


def why(values: dict[str, dict | str | None]) -> str:
    return ", ".join(
        f"{'invalid' if v == 'invalid' else 'missing'} {n}" for n, v in values.items() if not isinstance(v, dict)
    )


def pct(ev: dict) -> float:
    return round(100 * ev["resolved_instances"] / (ev["submitted_instances"] or 1), 1)


def blank(r: dict) -> dict:
    return (
        r
        | {c: "" for c in COUNTS}
        | {f"{c}_orig": "" for c in COUNTS}
        | {
            "delta": "",
            "resolved_pct": "",
            "resolved_pct_orig": "",
            "gained": [],
            "lost": [],
            "tasks": [],
        }
    )


def row(folder: Path, data_dir: Path) -> dict:
    values = {n: load(folder / n) for n in FILES}
    r = {"run": str(folder.relative_to(data_dir)), "model_name": model_name(folder)}
    ev1, ev2 = values[FILES[0]], values[FILES[1]]
    if not isinstance(ev1, dict) or not isinstance(ev2, dict):
        return blank(r | {"status": why(values)})

    gained = set(ev2.get("resolved_ids", [])) - set(ev1.get("resolved_ids", []))
    lost = set(ev1.get("resolved_ids", [])) - set(ev2.get("resolved_ids", []))
    return r | {
        "status": "flipped" if gained or lost else "same",
        **{c: ev2[c] for c in COUNTS},
        **{f"{c}_orig": ev1[c] for c in COUNTS},
        "delta": ev2["resolved_instances"] - ev1["resolved_instances"],
        "resolved_pct": pct(ev2),
        "resolved_pct_orig": pct(ev1),
        "gained": sorted(gained),
        "lost": sorted(lost),
        "tasks": sorted(set(ev2.get("submitted_ids", []))),
    }


def write_csv(rows: list[dict], path: Path) -> None:
    cols = (
        ["run", "model_name", "status"]
        + [c for name in COUNTS for c in (name, f"{name}_orig")]
        + ["delta", "resolved_pct", "resolved_pct_orig", "gained", "lost"]
    )
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r | {k: ";".join(r[k]) for k in ("gained", "lost")})


def flip_rows(rows: list[dict]) -> list[dict]:
    """Per task, across all compared runs: how often its verdict differed (flips), in which
    direction, and how many runs evaluated it (the denominator)."""
    tally: dict[str, dict] = {}
    for r in rows:
        for task in r["tasks"]:
            t = tally.setdefault(task, {"task": task, "flips": 0, "gained": 0, "lost": 0, "runs": 0})
            t["runs"] += 1
        for k in ("gained", "lost"):
            for task in r[k]:
                t = tally.setdefault(task, {"task": task, "flips": 0, "gained": 0, "lost": 0, "runs": 1})
                t[k] += 1
                t["flips"] += 1
    return sorted(tally.values(), key=lambda t: (-t["flips"], t["task"]))


def write_flips_csv(flips: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, ["task", "flips", "gained", "lost", "runs"])
        w.writeheader()
        w.writerows(flips)


def write_md(rows: list[dict], path: Path) -> None:
    done = [r for r in rows if r["status"] in OK]
    broken = [(r["run"], r["status"]) for r in rows if r["status"] not in OK]
    lines = ["# eval.json vs eval2.json", ""]
    if done:
        lines += [
            f"Compared {len(done)} run folders — original {sum(r['resolved_instances_orig'] for r in done)}"
            f" vs verified {sum(r['resolved_instances'] for r in done)} resolved of"
            f" {sum(r['submitted_instances'] for r in done)} submitted.",
            "",
            "| run | model_name | status | submitted | resolved | verified | Δ | verified % |",
            "|---|---|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['run']} | {r['model_name']} | {r['status']} | {r['submitted_instances']} |"
            f" {r['resolved_instances_orig']}"
            f" | {r['resolved_instances']} | {r['delta']} | {r['resolved_pct']} |"
            for r in sorted(done, key=lambda r: (-abs(r["delta"]), r["run"]))
        ]
        lines += ["", "## Verdict changes", ""]
        for r in sorted((r for r in done if r["gained"] or r["lost"]), key=lambda r: r["run"]):
            lines.append(f"**{r['run']}**")
            if r["gained"]:
                lines.append(f"- resolved only in eval2: {', '.join(r['gained'])}")
            if r["lost"]:
                lines.append(f"- resolved only in eval: {', '.join(r['lost'])}")
            lines.append("")
        flips = flip_rows(done)
        lines += ["", "## Flips per task", ""]
        lines += [
            "| task | flips | resolved only in eval2 | resolved only in eval | runs evaluated |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {t['task']} | {t['flips']} | {t['gained']} | {t['lost']} | {t['runs']} |" for t in flips if t["flips"]
        ]
        lines += [
            "",
            f"{sum(1 for t in flips if not t['flips'])} of {len(flips)} tasks never flipped"
            f" across the {len(done)} compared run folders (all tasks are in the -flips.csv).",
            "",
        ]
    if broken:
        lines += (
            [f"## Uncompared folders ({len(broken)})", ""] + [f"- {run} — {status}" for run, status in broken] + [""]
        )
    path.write_text("\n".join(lines))


def main(data_dir: Path = Path("data"), out_prefix: Path = Path("eval-diff")) -> None:
    folders = {p.parent for p in data_dir.rglob("eval.json")} | {p.parent for p in data_dir.rglob("eval2.json")}
    rows = [row(f, data_dir) for f in sorted(folders)]
    write_csv(rows, out_prefix.with_suffix(".csv"))
    write_flips_csv(flip_rows([r for r in rows if r["status"] in OK]), out_prefix.with_name(f"{out_prefix}-flips.csv"))
    write_md(rows, out_prefix.with_suffix(".md"))
    print(f"{len(rows)} run folders -> {out_prefix}.csv / {out_prefix}-flips.csv / {out_prefix}.md")


if __name__ == "__main__":
    typer.run(main)
