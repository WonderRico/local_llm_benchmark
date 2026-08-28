#!/usr/bin/env python3
"""Check that model colors never repeat: python3 check_palette.py [n_models]."""

import json
import subprocess
import sys
from pathlib import Path

TEMPLATES = {"template-main.html": "paletteColor", "template-detail.html": "nthColor"}

JS = """
const src = require('fs').readFileSync(process.argv[2], 'utf8');
const [fnName, n] = [process.argv[3], +process.argv[4]];
const palette = src.match(/(var BASE_PALETTE|const COLORS) = \\[[\\s\\S]*?\\];/)[0];
const fn = src.match(new RegExp('function ' + fnName + '\\\\(i\\\\)\\\\s*\\\\{[\\\\s\\\\S]*?\\\\n\\\\s*\\\\}'))[0];
const colors = new Function(palette + '\\n' + fn + '\\nreturn Array.from({length: ' + n + '}, (_, i) => ' + fnName + '(i));')();
process.stdout.write(JSON.stringify(colors));
"""

for name, fn_name in TEMPLATES.items():
    colors = json.loads(
        subprocess.run(
            [
                "node",
                "-e",
                JS,
                "",
                str(Path(__file__).parent / name),
                fn_name,
                sys.argv[1] if len(sys.argv) > 1 else "60",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert len(colors) == len(set(colors)), f"{name}: duplicate color in {colors}"
    print(f"{name}: {len(colors)} colors, {len(set(colors))} distinct")
