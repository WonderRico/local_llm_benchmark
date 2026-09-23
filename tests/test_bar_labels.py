import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template-main.html"

# Run the metric chart's grouping block, and the groupKey it calls, straight out of the
# template (see check_palette.py) rather than re-typing either here.
JS = """
const src = require('fs').readFileSync(process.argv[2], 'utf8');
const gkStart = src.indexOf('function groupKey(r){');
const gkEnd = src.indexOf('}', src.indexOf('{', gkStart)) + 1;
const start = src.indexOf('var records = getActiveRecords();');
const marker = 'var labels = agg.map(function(a){return a.label;});';
const end = src.indexOf(marker, start);
if (gkStart < 0 || start < 0 || end < 0) throw new Error('bar grouping not found in ' + process.argv[2]);
const body = src.slice(start, end + marker.length).replace('getActiveRecords()', 'records');
const run = new Function('records', 'key', 'nk',
  src.slice(gkStart, gkEnd) + '\\n' + body + '\\nreturn {labels: labels, agg: agg};');
const row = (base, model, score) => ({base, model, weights_quant: '', kv_cache_quant: '', score_num: score});
const out = run([
  row('Alpha', 'API', 40), row('Alpha', 'API', 60), row('Alpha', 'API-run2', 20),
  row('Beta', 'notag', 10), row('Beta', 'notag-run2', 30), row('Beta', 'notag-run3', 50),
], 'score_num', {higherBetter: true});
process.stdout.write(JSON.stringify(out));
"""


def test_bars_carry_base_and_compound_repeat_runs():
    out = json.loads(
        subprocess.run(["node", "-e", JS, "", str(TEMPLATE)], check=True, capture_output=True, text=True).stdout
    )
    # One bar per base (model names like "API" repeat across bases), one per config:
    # API/API-run2 and notag/notag-run2/notag-run3 each collapse into a single labelled bar.
    assert out["labels"] == ["Alpha \u00b7 API -/-", "Beta \u00b7 notag -/-"], out["labels"]
    assert [a["count"] for a in out["agg"]] == [3, 3], out["agg"]
    assert [a["avg"] for a in out["agg"]] == [40, 30], out["agg"]
