import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template-main.html"

# Run the template's own nameKey + rowVisible + toggleModelFilter instead of
# re-typing them (same trick as test_cell_gradient.py), feeding fake globals.
JS = """
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
const visibleModels = {qwen: true}; // unused by the template, kept so pre-fix versions still run
const visibleNames = {};
['a', 'b'].forEach((m) => { visibleNames['qwen\\n' + m] = true; });
const renders = [];
const body = ['function nameKey(', 'function rowVisible(', 'function toggleModelFilter(']
  .map(slice).join('\\n') + '\\nreturn {toggle: toggleModelFilter, visible: rowVisible};';
const api = new Function(
  'visibleModels', 'visibleNames', 'baseNames', 'renderModelFilter', 'onFilterChange', body
)(visibleModels, visibleNames, {qwen: ['a', 'b']}, () => renders.push(1), () => {});
const cb = (base, model, checked) => ({checked, getAttribute: (k) => (k === 'data-base' ? base : model)});
const shown = () => ['a', 'b'].filter((m) => api.visible({base: 'qwen', model: m}));
api.toggle(cb('qwen', null, false)); // uncheck the group
const afterUncheck = shown();
api.toggle(cb('qwen', 'a', true)); // roll it open, tick one child back on
const afterChild = shown();
api.toggle(cb('qwen', null, true)); // check the group again
process.stdout.write(JSON.stringify([afterUncheck, afterChild, shown(), renders.length]));
"""


def _trace() -> list:
    return json.loads(
        subprocess.run(["node", "-e", JS, "", str(TEMPLATE)], check=True, capture_output=True, text=True).stdout
    )


def test_group_checkbox_drives_all_its_children():
    after_uncheck, _, after_recheck, renders = _trace()
    assert after_uncheck == [], after_uncheck  # unchecking the group hides the children
    assert after_recheck == ["a", "b"], after_recheck  # and re-checking restores them all
    assert renders == 3, renders  # the panel is redrawn so the visible checkboxes match


def test_children_checked_while_the_group_is_off_are_shown():
    _, after_child, _, _ = _trace()
    assert after_child == ["a"], after_child  # a ticked child is never vetoed by its unticked group
