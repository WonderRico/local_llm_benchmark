#!/usr/bin/env python3
"""Check that model colors never repeat (per theme): python3 check_palette.py [n_models]."""

import json
import subprocess
import sys
from pathlib import Path

TEMPLATES = ["template-main.html", "template-detail.html"]

# Slice the palette declaration + color function out of the template's script: the code is
# plain JS, so it runs as-is instead of being re-typed here (which drifts from the template).
JS = """
const file = process.argv[2];
const src = require('fs').readFileSync(file, 'utf8');
const n = Number(process.argv[3]);
if (!Number.isInteger(n) || n < 1) throw new Error('bad model count: ' + process.argv[3]);

const decl = src.indexOf('PALETTES = {');
if (decl < 0) throw new Error('PALETTES not found in ' + file);
const declStart = Math.max(src.lastIndexOf('var PALETTES', decl), src.lastIndexOf('const PALETTES', decl));
const fnStart = src.indexOf('function paletteColor(i, dark)', decl);
if (fnStart < 0) throw new Error('paletteColor(i, dark) not found in ' + file);
let depth = 0, end = -1;
for (let i = src.indexOf('{', fnStart); i < src.length; i++) {
  if (src[i] === '{') depth++;
  else if (src[i] === '}' && --depth === 0) { end = i + 1; break; }
}
if (end < 0) throw new Error('unbalanced paletteColor in ' + file);

const make = new Function(
  'n',
  src.slice(declStart, end) + '\\nreturn (dark) => Array.from({length: n}, (_, i) => paletteColor(i, dark));'
)(n);
const out = {light: make(false), dark: make(true)};
for (const [theme, colors] of Object.entries(out)) {
  if (colors.length !== n || colors.some((c) => typeof c !== 'string' || !c)) {
    throw new Error(theme + ': expected ' + n + ' colors, got ' + JSON.stringify(colors.slice(0, 20)));
  }
}
process.stdout.write(JSON.stringify(out));
"""

for name in TEMPLATES:
    themes = json.loads(
        subprocess.run(
            [
                "node",
                "-e",
                JS,
                "",
                str(Path(__file__).parent / name),
                sys.argv[1] if len(sys.argv) > 1 else "60",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert len(themes) == 2, f"{name}: expected light + dark palettes, got {themes}"
    for theme, colors in themes.items():
        assert len(colors) == len(set(colors)), f"{name} [{theme}]: duplicate color in {colors}"
        print(f"{name} [{theme}]: {len(colors)} colors, {len(set(colors))} distinct")
