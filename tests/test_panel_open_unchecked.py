import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template-main.html"

# Run the template's own `var open = ...` expression instead of re-typing it
# (same trick as test_cell_gradient.py), so this fails when the collapse rule regresses.
JS = """
const src = require('fs').readFileSync(process.argv[2], 'utf8');
const m = src.match(/var open = ([^;\\n]+);/);
if (!m) throw new Error('open expression not found in ' + process.argv[2]);
const open = (checked, bases) =>
  new Function('checked', 'openBases', 'b', 'return (' + m[1] + ')')(checked, bases, 'qwen');
process.stdout.write(JSON.stringify([open(false, {qwen: true}), open(true, {qwen: true}), open(true, {})]));
"""


def test_children_can_be_revealed_while_their_base_is_unchecked():
    out = json.loads(
        subprocess.run(["node", "-e", JS, "", str(TEMPLATE)], check=True, capture_output=True, text=True).stdout
    )
    assert out == [True, True, False], out  # unchecked + rolled out still shows the children
