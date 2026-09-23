#!/usr/bin/env bash
# Re-run ../eval_verif.sh on every run folder under data/ and save the report it
# produces as eval2.json next to the existing eval.json.
# swebench writes logs/run_evaluation and the report json relative to the cwd, so each
# run folder gets its own dir under .eval-cache: that keeps reports apart when two
# folders share a model name, and lets an interrupted run resume.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
root=$here/..
logs=$here/.eval-cache
failed=()

# swebench resolves its log/report paths against the cwd
cd "$root" || exit 1
while IFS= read -r -d '' dir; do
  echo "=== ${dir#"$here/"}"
  work=$logs/${dir#"$here/"}
  mkdir -p "$work"
  (
    cd "$work" || exit 1
    "${EVAL_VERIF:-$root/eval_verif.sh}" "$dir"
  ) 2>&1 | tee "$work/eval.log"
  rc=${PIPESTATUS[0]}

  # eval_verif.sh prints "Report written to <model>.my-local-eval.json" (relative to cwd)
  report=$(sed -n 's/^Report written to //p' "$work/eval.log" | tail -1)
  if ((rc != 0)) || [[ -z $report || ! -s $work/$report ]]; then
    echo "!! evaluation failed for ${dir#"$here/"} (rc=$rc, see $work/eval.log)"
    failed+=("${dir#"$here/"}")
    continue
  fi
  cp "$work/$report" "$dir/eval2.json"
  echo "-> ${dir#"$here/"}/eval2.json"
done < <(find "$here/data" -name preds.json -printf '%h\0' | sort -z)

if ((${#failed[@]})); then
  echo "failed: ${failed[*]}"
  exit 1
fi
