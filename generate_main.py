#!/usr/bin/env python3
"""Generate the main benchmark dashboard from data.csv + text.md.

Output: benchmark-dashboard.html (drop-in for WordPress via Custom HTML block).
"""

from __future__ import annotations

from pathlib import Path

from dashboard_lib import render_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    render_dashboard(
        csv_path=SCRIPT_DIR / "data.csv",
        md_path=SCRIPT_DIR / "text.md",
        template_path=SCRIPT_DIR / "template-main.html",
        output_path=SCRIPT_DIR / "benchmark-main.html",
    )


if __name__ == "__main__":
    main()
