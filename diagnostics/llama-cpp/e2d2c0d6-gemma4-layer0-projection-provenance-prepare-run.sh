#!/usr/bin/env bash
set -uo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  layer0-projection-provenance-prepare-run.sh OUT_ROOT LLAMA_SOURCE_REPO MODEL_PATH PORT_PLAIN PORT_PROBE [JOBS]

Pre-measured replacement preparation only:
  isolated exact-source build
  -> binary provenance
  -> plain/probe non-generative startup qualification

This wrapper never sends a generation request and never authorizes measured L0.
EOF
}

if (( $# < 5 || $# > 6 )); then
  usage
  exit 64
fi

out_root=$1
llama_repo=$2
model_path=$3
port_plain=$4
port_probe=$5
jobs=${6:-4}

if [[ "$port_plain" == "$port_probe" ]]; then
  echo "plain and probe ports must differ" >&2
  exit 65
fi
if [[ -e "$out_root" ]]; then
  echo "output root must not exist: $out_root" >&2
  exit 66
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null || true)
authority_head=${RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD:-}
build_runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-build-run.sh"
qual_runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-qualification-run.sh"
static_selftest="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-preparation-static-selftest.py"

if [[ -z "$repo_root" || -z "$authority_head" ]]; then
  echo "isolated authority-bound RelayLM checkout and RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD are required" >&2
  exit 67
fi
local_head=$(git -C "$repo_root" rev-parse HEAD)
if [[ "$local_head" != "$authority_head" ]]; then
  echo "local apparatus HEAD does not match fresh diagnostic authority: $local_head != $authority_head" >&2
  exit 68
fi
if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]]; then
  echo "authority-bound RelayLM apparatus checkout is not clean" >&2
  exit 69
fi

if [[ ! -f "$build_runner" || ! -f "$qual_runner" || ! -f "$static_selftest" ]]; then
  echo "required replacement runners missing" >&2
  exit 70
fi

mkdir -p "$out_root"
printf '%s\n' "$authority_head" >"$out_root/relaylm-authority.head.txt"
git -C "$repo_root" rev-parse "HEAD^{tree}" >"$out_root/relaylm-authority.tree.txt"

python3 "$static_selftest" >"$out_root/preparation-static-selftest.json"
static_rc=$?
printf '%d\n' "$static_rc" >"$out_root/preparation-static-selftest.exit-code.txt"
if (( static_rc != 0 )); then
  echo "internal preparation static gate failed" >&2
  exit 71
fi

bash -n "$build_runner" || exit 72
bash -n "$qual_runner" || exit 72

build_root="$out_root/build-stage"
qual_root="$out_root/qualification-stage"

set +e
bash "$build_runner" "$build_root" "$llama_repo" "$jobs" \
  >"$out_root/build-stage.stdout.txt" 2>"$out_root/build-stage.stderr.txt"
build_rc=$?
set -e
printf "%d\n" "$build_rc" >"$out_root/build-stage.exit-code.txt"

if (( build_rc == 0 )); then
  server_bin=$(python3 - "$build_root/terminal.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["server_binary"])
PY
  )

  set +e
  bash "$qual_runner" "$qual_root" "$server_bin" "$model_path" "$port_plain" "$port_probe" \
    >"$out_root/qualification-stage.stdout.txt" 2>"$out_root/qualification-stage.stderr.txt"
  qual_rc=$?
  set -e
else
  server_bin=""
  qual_rc=125
fi
printf "%d\n" "$qual_rc" >"$out_root/qualification-stage.exit-code.txt"

python3 - "$out_root" "$build_rc" "$qual_rc" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
build_rc = int(sys.argv[2])
qual_rc = int(sys.argv[3])
errors = []
build = None
qual = None

if build_rc != 0:
    errors.append(f"build stage failed: rc={build_rc}")
else:
    try:
        build = json.loads((root / "build-stage" / "terminal.json").read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"build terminal unavailable: {exc}")

if build_rc == 0:
    if qual_rc != 0:
        errors.append(f"qualification stage failed: rc={qual_rc}")
    else:
        try:
            qual = json.loads((root / "qualification-stage" / "terminal.json").read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"qualification terminal unavailable: {exc}")

if build is not None and build.get("primary_classification") != "LAYER0_PROJECTION_PROVENANCE_BUILD_READY":
    errors.append("unexpected build terminal classification")
if qual is not None and qual.get("primary_classification") != "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY":
    errors.append("unexpected qualification terminal classification")

out = {
    "preparation_generation": "provenance-preparation-20260923-d",
    "primary_classification": (
        "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY"
        if not errors
        else "LAYER0_PROJECTION_PROVENANCE_PREPARATION_FAILED"
    ),
    "errors": errors,
    "relaylm_authority_head": (root / "relaylm-authority.head.txt").read_text(encoding="utf-8").strip(),
    "relaylm_authority_tree": (root / "relaylm-authority.tree.txt").read_text(encoding="utf-8").strip(),
    "preparation_static_selftest": json.loads((root / "preparation-static-selftest.json").read_text(encoding="utf-8")),
    "build_returncode": build_rc,
    "qualification_returncode": qual_rc,
    "build": build,
    "qualification": qual,
    "generated_requests": 0,
    "measured_l0_submitted": False,
    "measured_attempt_consumed": False,
    "measured_execution_authorized_by_this_result": False,
}
(root / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 1)
PY
