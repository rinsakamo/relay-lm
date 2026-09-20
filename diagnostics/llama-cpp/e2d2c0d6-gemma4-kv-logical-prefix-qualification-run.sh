#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  logical-prefix-qualification-run.sh OUT_ROOT SERVER_BIN MODEL_PATH PORT_PLAIN PORT_PROBE

Strictly pre-measured replacement qualification:
  patch self-test
  -> binary provenance preflight
  -> non-generative plain/probe startup recovery
  -> strict startup/runtime geometry classification

No completion/chat/generation request is sent.
EOF
}

if (( $# != 5 )); then
  usage
  exit 64
fi

out_root=$1
server_bin=$2
model_path=$3
port_plain=$4
port_probe=$5

if [[ "$port_plain" == "$port_probe" ]]; then
  echo "plain and probe ports must differ" >&2
  exit 65
fi

if [[ -e "$out_root" ]]; then
  echo "output root must not exist: $out_root" >&2
  exit 66
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
patch_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-patch-selftest.py"
binary_preflight="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-binary-preflight.py"
startup_run="$script_dir/e2d2c0d6-gemma4-kv-startup-recovery-run.sh"
startup_classify="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-startup-classify.py"
startup_classifier_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-startup-classifier-selftest.py"

for required in "$patch_selftest" "$binary_preflight" "$startup_run" "$startup_classify" "$startup_classifier_selftest"; do
  if [[ ! -f "$required" ]]; then
    echo "required helper missing: $required" >&2
    exit 67
  fi
done

mkdir -p "$out_root"

python3 -m py_compile \
  "$patch_selftest" \
  "$binary_preflight" \
  "$startup_classify" \
  "$startup_classifier_selftest"

bash -n "$startup_run"
bash -n "$script_dir/e2d2c0d6-gemma4-kv-startup-recovery.sh"

python3 "$startup_classifier_selftest" \
  >"$out_root/logical-prefix-startup-classifier-selftest.json"

python3 "$patch_selftest" >"$out_root/logical-prefix-patch-selftest.json"

python3 "$binary_preflight" \
  --server-bin "$server_bin" \
  --model "$model_path" \
  --out "$out_root/logical-prefix-binary-preflight.json" \
  >"$out_root/logical-prefix-binary-preflight.stdout.json"

startup_root="$out_root/startup-recovery"
bash "$startup_run" \
  "$startup_root" \
  "$server_bin" \
  "$model_path" \
  "$port_plain" \
  "$port_probe" \
  >"$out_root/startup-recovery.stdout.json"

python3 "$startup_classify" \
  "$startup_root/plain" \
  "$startup_root/probe" \
  >"$out_root/logical-prefix-startup-classification.json"

python3 - "$out_root" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])

def load(name):
    return json.loads((root / name).read_text(encoding="utf-8"))

patch = load("logical-prefix-patch-selftest.json")
binary = load("logical-prefix-binary-preflight.json")
startup = load("logical-prefix-startup-classification.json")

errors = []
if patch.get("status") != "LOGICAL_PREFIX_PATCH_SELFTEST_PASS":
    errors.append("patch self-test did not pass")
if binary.get("status") != "LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS":
    errors.append("binary provenance preflight did not pass")
if startup.get("primary_classification") != "LOGICAL_PREFIX_STARTUP_QUALIFIED":
    errors.append("strict startup qualification did not pass")

server_sha = binary.get("server_sha256")
old_sha = "0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e"
if server_sha == old_sha:
    errors.append("replacement binary unexpectedly equals consumed apparatus binary SHA")

out = {
    "primary_classification": (
        "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY"
        if not errors
        else "LOGICAL_PREFIX_REPLACEMENT_NOT_READY"
    ),
    "errors": errors,
    "server_sha256": server_sha,
    "model_sha256": binary.get("model_sha256"),
    "logical_prefix_patch_sha256": binary.get("logical_prefix_patch_sha256"),
    "aligned_reuse_patch_sha256": binary.get("aligned_reuse_patch_sha256"),
    "startup": startup,
    "generated_requests": 0,
    "measured_l0_submitted": False,
    "measured_attempt_consumed": False,
    "measured_execution_authorized_by_this_result": False,
}
(root / "terminal.json").write_text(
    json.dumps(out, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 1)
PY
