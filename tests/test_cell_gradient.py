import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template-main.html"

# Slice cellBg out of the template's script: it is plain JS, so it runs as-is instead of
# being re-typed here (which drifts from the template). Same trick as check_palette.py.
JS = """
const src = require('fs').readFileSync(process.argv[2], 'utf8');
const start = src.indexOf('function cellBg(');
if (start < 0) throw new Error('cellBg not found in ' + process.argv[2]);
let depth = 0, end = -1;
for (let i = src.indexOf('{', start); i < src.length; i++) {
  if (src[i] === '{') depth++;
  else if (src[i] === '}' && --depth === 0) { end = i + 1; break; }
}
if (end < 0) throw new Error('unbalanced cellBg');
const cellBg = new Function(src.slice(start, end) + '\\nreturn cellBg;')();
const ok = (nc, v) => (cellBg(nc, v, 0, 10).match(/var\\(--ok\\) (\\d+)%/) || []).pop();
const at = (better) => [0, 1, 5, 9, 10].map((v) => ok({higherBetter: better}, v));
process.stdout.write(JSON.stringify({
  up: at(true), down: at(false),
  flat: cellBg({higherBetter: true}, 5, 5, 5),
  wash: cellBg({higherBetter: true}, 10, 0, 10).endsWith('40%, transparent)'),
}));
"""


def test_ramp_runs_bad_to_good_and_inverts_for_cost_columns():
    out = json.loads(
        subprocess.run(["node", "-e", JS, "", str(TEMPLATE)], check=True, capture_output=True, text=True).stdout
    )
    assert out["up"] == ["0", "10", "50", "90", "100"], out  # green at the top of a higher-better column
    assert out["down"] == ["100", "90", "50", "10", "0"], out  # red at the top of a lower-better column
    assert out["flat"] == "" and out["wash"], out  # constant column stays untinted, wash stays 40%
