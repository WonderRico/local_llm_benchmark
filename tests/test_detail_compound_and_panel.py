import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template-detail.html"

# Run the template's own functions instead of re-typing them (same trick as
# test_cell_gradient.py): slice them out of the HTML and eval them with fake globals.
JS = r"""
const src = require('fs').readFileSync(process.argv[2], 'utf8');
const slice = (sig) => {
  const s = src.indexOf(sig);
  if (s < 0) throw new Error(sig + ' not found in ' + process.argv[2]);
  let depth = 0, end = -1;
  for (let i = src.indexOf('{', s); i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) { end = i + 1; break; }
  }
  if (end < 0) throw new Error('unbalanced ' + sig);
  return src.slice(s, end);
};
const one = (re) => {
  const m = src.match(re);
  if (!m) throw new Error(re + ' not found');
  return m[0];
};

const bars = new Function(
  one(/const RUN_TAG = [^\n]*/) + '\n' + slice('function shortLabel(') + '\n'
  + slice('function compoundBars(') + '\nreturn compoundBars;'
)();
const V = (base, variant, tools) => ({
  model: base + ' (' + variant + ')', variant, key: base + '/' + variant, data: { total_tools: tools },
});
const runs = [
  V('DeepSeek-V4-Flash', '3107-high-run2_WQMXFP4_CQBF16', 3055),
  V('DeepSeek-V4-Flash', '3107-high_WQMXFP4_CQBF16', 3037),
  V('DeepSeek-V4-Pro', 'API', 4578),
];
const grouped = bars(runs, (v) => v.data.total_tools).map((g) =>
  ({ label: g.label, avg: g.avg, min: g.min, max: g.max, count: g.count }));

const vk = new Function(slice('function variantKey(') + '\nreturn variantKey;')();
const visibleVariants = {}, redraws = [];
const toggle = new Function(
  'visibleVariants', 'shownVariants', 'variantKey', 'renderAll',
  slice('function variantKey(') + '\n' + slice('function toggleModelFilter(') + '\nreturn toggleModelFilter;'
)(visibleVariants, () => ['a', 'b'], vk, () => redraws.push(1));
const qwen = ['a', 'b'].map((v) => V('qwen', v, 1));
qwen.forEach((v) => { visibleVariants[vk('qwen', v.variant)] = true; });
// getFilteredVariants is what the tables and charts actually draw from.
const keep = new Function(
  'visibleVariants', 'getModelKey', 'getAllVariants',
  slice('function variantKey(') + '\n' + slice('function getFilteredVariants(') + '\nreturn getFilteredVariants;'
)(visibleVariants, (v) => v.key.split('/')[0], () => qwen);
const kept = () => keep().map((v) => v.variant);
const cb = (base, variant, checked) => ({checked, getAttribute: (k) => (k === 'data-base' ? base : variant)});
toggle(cb('qwen', null, false)); // uncheck the group
const afterUncheck = kept();
toggle(cb('qwen', 'a', true)); // roll it open, tick one child back on
const afterChild = kept();
toggle(cb('qwen', null, true)); // check the group again

const isOpen = (checked, openBases) =>
  new Function('checked', 'openBases', 'base',
    'return (' + src.match(/const open = ([^;\n]+);/)[1] + ')')(checked, openBases, 'qwen');

process.stdout.write(JSON.stringify({ grouped, after_uncheck: afterUncheck, after_child: afterChild,
  after_recheck: kept(), redraws: redraws.length,
  open: [isOpen(false, { qwen: true }), isOpen(true, { qwen: true }), isOpen(true, {})] }));
"""


def _state() -> dict:
    return json.loads(
        subprocess.run(["node", "-e", JS, "", str(TEMPLATE)], check=True, capture_output=True, text=True).stdout
    )


def test_repeat_runs_compound_into_one_bar():
    assert _state()["grouped"] == [
        {"label": "DeepSeek-V4-Pro API", "avg": 4578.0, "min": 4578, "max": 4578, "count": 1},
        {"label": "DeepSeek-V4-Flash 3107-high MXFP4 BF16", "avg": 3046.0, "min": 3037, "max": 3055, "count": 2},
    ]  # runs of one config collapse, sorted by mean, whiskers carry min/max


def test_group_checkbox_drives_all_its_children():
    state = _state()
    assert state["after_uncheck"] == [], state  # unchecking the group hides the variants
    assert state["after_recheck"] == ["a", "b"], state  # and re-checking restores them all


def test_children_checked_while_the_group_is_off_are_shown():
    state = _state()
    assert state["after_child"] == ["a"], state  # a ticked child is never vetoed by its unticked group


def test_children_can_be_revealed_while_their_base_is_unchecked():
    state = _state()
    assert state["open"] == [True, True, False], state  # unchecked + rolled out shows the children
