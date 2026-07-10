#!/usr/bin/env bash
set -euo pipefail

STACK_BASE="a3d50f6d043fa9a2802ffb029b0123f827180a00"
PR8_OLD_BASE="d002120bd2cf2115a01dcf4a69a691060def03ec"
PR9_OLD_BASE="f57e8338c4b54e5d9b12af7a25b1561e90b409c8"
PR10_OLD_BASE="cf370a107c08ba00f3bf12e275f95c12ce032283"
PR11_OLD_BASE="103a7ebfb3603f98d1660981f651bd65bd1c4b67"
WORKFLOW_PATH=".github/workflows/rebase-pr07-pr11.yml"
SCRIPT_PATH=".github/scripts/rebase-pr07-pr11.sh"

git config user.name "RelayLM stack maintenance"
git config user.email "actions@users.noreply.github.com"
git fetch origin \
  main \
  claude/pr-07-stage-runner \
  claude/pr-08-input-stages \
  claude/pr-09-memory-stages \
  claude/pr-10-prebackend-stages \
  claude/pr-11-response-service

MAIN_OBSERVED="$(git rev-parse origin/main)"
PR7_OBSERVED="$(git rev-parse origin/claude/pr-07-stage-runner)"
PR8_OBSERVED="$(git rev-parse origin/claude/pr-08-input-stages)"
PR9_OBSERVED="$(git rev-parse origin/claude/pr-09-memory-stages)"
PR10_OBSERVED="$(git rev-parse origin/claude/pr-10-prebackend-stages)"
PR11_OBSERVED="$(git rev-parse origin/claude/pr-11-response-service)"

verify_branch() {
  local label="$1"
  echo "::group::verify ${label}"
  python -m compileall -q relaylm tests
  pytest -q
  python scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
  python scripts/relaylm_p0_pipeline_ordering_smoke.py
  echo "::endgroup::"
}

patch_relayint_anchors() {
  python - <<'PY'
from pathlib import Path
import re

path = Path("scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py")
text = path.read_text(encoding="utf-8")
replacement = '''"relayint": {
        "build_relayint_reference_intent_artifact",
        "build_relayint_reference_repair_dry_run",
        "run_relayint_stage",
    },'''
updated, count = re.subn(
    r'"relayint":\s*\{[^}]*\},',
    replacement,
    text,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise SystemExit("could not locate exactly one RelayINT identifier set")
if updated != text:
    path.write_text(updated, encoding="utf-8")
PY
}

commit_relayint_anchors() {
  patch_relayint_anchors
  if ! git diff --quiet -- scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py; then
    git add scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
    git commit -m "Fix RelayINT ordering smoke anchors"
  fi
}

rebase_in_progress() {
  [[ -d .git/rebase-merge || -d .git/rebase-apply ]]
}

continue_expected_rebase() {
  local label="$1"
  while rebase_in_progress; do
    mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
    if [[ ${#conflicts[@]} -gt 0 ]]; then
      for path in "${conflicts[@]}"; do
        case "${label}:${path}" in
          pr9:scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py)
            git checkout --theirs -- "$path"
            ;;
          *)
            echo "Unexpected rebase conflict for ${label}: ${path}" >&2
            exit 1
            ;;
        esac
      done
      patch_relayint_anchors
      git add "${conflicts[@]}" scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
    fi

    set +e
    GIT_EDITOR=true git rebase --continue
    rc=$?
    set -e
    if [[ $rc -ne 0 ]] && ! rebase_in_progress; then
      exit "$rc"
    fi
  done
}

rebase_layer() {
  local label="$1"
  local remote_ref="$2"
  local new_base="$3"
  local old_base="$4"
  local current_tip
  current_tip="$(git rev-parse "$remote_ref")"

  git switch --detach "$current_tip"
  if git merge-base --is-ancestor "$new_base" HEAD; then
    commit_relayint_anchors
    return
  fi
  if ! git merge-base --is-ancestor "$old_base" HEAD; then
    echo "${label} no longer contains expected old base ${old_base}" >&2
    exit 1
  fi
  if ! git rebase --onto "$new_base" "$old_base"; then
    continue_expected_rebase "$label"
  fi
  commit_relayint_anchors
}

# Create the final clean main commit locally first. The workflow and this helper
# are deleted in that commit, so the five rebuilt branches inherit a clean tree.
git switch --detach "$MAIN_OBSERVED"
git rm "$WORKFLOW_PATH" "$SCRIPT_PATH"
git commit -m "chore: remove one-shot PR-7–PR-11 rebase workflow"
CLEAN_MAIN="$(git rev-parse HEAD)"

# PR-7 has six old Wave A commits followed by three PR-7 commits and three
# review-fix commits. Drop the Wave A lineage and replay only the PR-7 slice.
git switch --detach "$PR7_OBSERVED"
mapfile -t pr7_commits < <(git rev-list --reverse "${STACK_BASE}..HEAD")
if [[ ${#pr7_commits[@]} -ne 12 ]]; then
  printf 'Unexpected PR-7 commit count: %s\n' "${#pr7_commits[@]}" >&2
  printf '%s\n' "${pr7_commits[@]}" >&2
  exit 1
fi
pr7_wave_a_tip="${pr7_commits[5]}"
git rebase --onto "$CLEAN_MAIN" "$pr7_wave_a_tip"
commit_relayint_anchors
verify_branch pr7
PR7_NEW="$(git rev-parse HEAD)"

rebase_layer pr8 origin/claude/pr-08-input-stages "$PR7_NEW" "$PR8_OLD_BASE"
verify_branch pr8
PR8_NEW="$(git rev-parse HEAD)"

rebase_layer pr9 origin/claude/pr-09-memory-stages "$PR8_NEW" "$PR9_OLD_BASE"
verify_branch pr9
PR9_NEW="$(git rev-parse HEAD)"

rebase_layer pr10 origin/claude/pr-10-prebackend-stages "$PR9_NEW" "$PR10_OLD_BASE"
verify_branch pr10
PR10_NEW="$(git rev-parse HEAD)"

rebase_layer pr11 origin/claude/pr-11-response-service "$PR10_NEW" "$PR11_OLD_BASE"

python - <<'PY'
from pathlib import Path

smoke = Path("scripts/relaylm_relayemo_smoke.py")
smoke_text = smoke.read_text(encoding="utf-8")
old_smoke_import = '''from relaylm.managed_chat_runtime import (
    _apply_relayemo_marker_to_response,
    _build_relayemo_text_marker_preview,
)'''
new_smoke_import = '''from relaylm.relayemo_response_marker import (
    apply_relayemo_marker_to_response as _apply_relayemo_marker_to_response,
    build_relayemo_text_marker_preview as _build_relayemo_text_marker_preview,
)'''
if old_smoke_import in smoke_text:
    smoke.write_text(smoke_text.replace(old_smoke_import, new_smoke_import), encoding="utf-8")
elif new_smoke_import not in smoke_text:
    raise SystemExit("neither old nor canonical response marker import was found")

runtime = Path("relaylm/managed_chat_runtime.py")
runtime_text = runtime.read_text(encoding="utf-8")
old_runtime_import = '''from relaylm.relayemo_response_marker import (
    # These two aliases are no longer used in this module (the response-side
    # marker application they backed moved to
    # relaylm.managed_chat_response._build_nonstream_response, which imports
    # the same functions under their plain names). The aliased imports stay
    # here solely because scripts/relaylm_relayemo_smoke.py imports them by
    # these names directly from relaylm.managed_chat_runtime.
    apply_relayemo_marker_to_response as _apply_relayemo_marker_to_response,
    build_relayemo_text_marker_preview as _build_relayemo_text_marker_preview,
)
'''
if old_runtime_import in runtime_text:
    runtime.write_text(runtime_text.replace(old_runtime_import, ""), encoding="utf-8")
PY
if ! git diff --quiet -- relaylm/managed_chat_runtime.py scripts/relaylm_relayemo_smoke.py; then
  git add relaylm/managed_chat_runtime.py scripts/relaylm_relayemo_smoke.py
  git commit -m "Remove response marker compatibility aliases"
fi

verify_branch pr11
PR11_NEW="$(git rev-parse HEAD)"

cat > /tmp/rebased-heads.txt <<EOF_HEADS
CLEAN_MAIN=${CLEAN_MAIN}
PR7_NEW=${PR7_NEW}
PR8_NEW=${PR8_NEW}
PR9_NEW=${PR9_NEW}
PR10_NEW=${PR10_NEW}
PR11_NEW=${PR11_NEW}
EOF_HEADS
cat /tmp/rebased-heads.txt

# Update main and all five stack refs atomically. If any observed ref moved,
# force-with-lease rejects the whole update rather than overwriting new work.
git push --atomic origin \
  --force-with-lease="refs/heads/main:${MAIN_OBSERVED}" \
  --force-with-lease="refs/heads/claude/pr-07-stage-runner:${PR7_OBSERVED}" \
  --force-with-lease="refs/heads/claude/pr-08-input-stages:${PR8_OBSERVED}" \
  --force-with-lease="refs/heads/claude/pr-09-memory-stages:${PR9_OBSERVED}" \
  --force-with-lease="refs/heads/claude/pr-10-prebackend-stages:${PR10_OBSERVED}" \
  --force-with-lease="refs/heads/claude/pr-11-response-service:${PR11_OBSERVED}" \
  "${CLEAN_MAIN}:refs/heads/main" \
  "+${PR7_NEW}:refs/heads/claude/pr-07-stage-runner" \
  "+${PR8_NEW}:refs/heads/claude/pr-08-input-stages" \
  "+${PR9_NEW}:refs/heads/claude/pr-09-memory-stages" \
  "+${PR10_NEW}:refs/heads/claude/pr-10-prebackend-stages" \
  "+${PR11_NEW}:refs/heads/claude/pr-11-response-service"
