#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  layer0-projection-origin-qualification-run.sh OUT_ROOT SERVER_BIN MODEL_PATH PORT_PLAIN PORT_PROBE

Strictly pre-measured replacement qualification:
  patch/classifier/resource-guard self-tests
  -> binary provenance preflight
  -> canonical local-GPU flock + two-sample external quiescence
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
origin_posthoc="$script_dir/e2d2c0d6-gemma4-layer0-projection-origin-posthoc.py"
origin_posthoc_selftest="$script_dir/e2d2c0d6-gemma4-layer0-projection-origin-posthoc-selftest.py"
binary_preflight="$script_dir/e2d2c0d6-gemma4-layer0-projection-origin-binary-preflight.py"
startup_run="$script_dir/e2d2c0d6-gemma4-kv-startup-recovery-run.sh"
startup_classify="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-startup-classify.py"
startup_classifier_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-startup-classifier-selftest.py"
resource_guard="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
resource_guard_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"

for required in "$patch_selftest" "$origin_posthoc" "$origin_posthoc_selftest" "$binary_preflight" "$startup_run" "$startup_classify" "$startup_classifier_selftest" "$resource_guard" "$resource_guard_selftest"; do
  if [[ ! -f "$required" ]]; then
    echo "required helper missing: $required" >&2
    exit 67
  fi
done

mkdir -p "$out_root"

python3 -m py_compile \
  "$patch_selftest" \
  "$origin_posthoc" \
  "$origin_posthoc_selftest" \
  "$binary_preflight" \
  "$startup_classify" \
  "$startup_classifier_selftest" \
  "$resource_guard" \
  "$resource_guard_selftest"

bash -n "$startup_run"
bash -n "$script_dir/e2d2c0d6-gemma4-kv-startup-recovery.sh"

python3 "$startup_classifier_selftest" \
  >"$out_root/logical-prefix-startup-classifier-selftest.json"

python3 "$resource_guard_selftest" \
  >"$out_root/logical-prefix-resource-guard-selftest.json"

python3 "$patch_selftest" >"$out_root/logical-prefix-patch-selftest.json"
python3 "$origin_posthoc_selftest" >"$out_root/projection-origin-posthoc-selftest.txt"

python3 "$binary_preflight" \
  --server-bin "$server_bin" \
  --model "$model_path" \
  --out "$out_root/logical-prefix-binary-preflight.json" \
  >"$out_root/logical-prefix-binary-preflight.stdout.json"

startup_root="$out_root/startup-recovery"
guard_root="$out_root/shared-resource-guard"

set +e
python3 "$resource_guard" \
  --evidence-root "$guard_root" -- \
  bash "$startup_run" \
    "$startup_root" \
    "$server_bin" \
    "$model_path" \
    "$port_plain" \
    "$port_probe" \
  >"$out_root/startup-recovery.stdout.json" \
  2>"$out_root/startup-recovery.stderr.txt"
startup_rc=$?
set -e
printf '%d\n' "$startup_rc" >"$out_root/startup-recovery.exit-code.txt"

if (( startup_rc != 0 )); then
  python3 - "$out_root" "$startup_rc" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
startup_rc = int(sys.argv[2])

def maybe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

out = {
    "primary_classification": "LAYER0_PROJECTION_ORIGIN_NOT_READY",
    "errors": [f"guarded startup recovery failed: rc={startup_rc}"],
    "resource_guard": maybe_json(root / "shared-resource-guard" / "guard.json"),
    "external_quiescence": maybe_json(root / "shared-resource-guard" / "external-quiescence.json"),
    "generated_requests": 0,
    "measured_l0_submitted": False,
    "measured_attempt_consumed": False,
    "measured_execution_authorized_by_this_result": False,
}
(root / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2, sort_keys=True))
PY
  exit 1
fi

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
guard_selftest = load("logical-prefix-resource-guard-selftest.json")
guard = load("shared-resource-guard/guard.json")
quiescence = load("shared-resource-guard/external-quiescence.json")

errors = []
if patch.get("status") != "LOGICAL_PREFIX_PATCH_SELFTEST_PASS":
    errors.append("patch self-test did not pass")
if binary.get("status") != "LAYER0_PROJECTION_ORIGIN_BINARY_PREFLIGHT_PASS":
    errors.append("projection-origin binary provenance preflight did not pass")
if startup.get("primary_classification") != "LOGICAL_PREFIX_STARTUP_QUALIFIED":
    errors.append("strict startup qualification did not pass")
if guard_selftest.get("status") != "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS":
    errors.append("resource guard self-test did not pass")

if guard.get("resource_key") != "llama-cpp:local-gpu":
    errors.append("resource guard used unexpected resource key")
if guard.get("guard_state") != "RELEASED_CANONICAL_DIAGNOSTIC_FLOCK":
    errors.append("canonical diagnostic GPU flock was not released cleanly")
if guard.get("lock_acquired") is not True:
    errors.append("canonical diagnostic GPU flock was not acquired")
if guard.get("child_invoked") is not True:
    errors.append("guarded startup child was not invoked")
if guard.get("child_returncode") != 0:
    errors.append("guarded startup child did not exit zero")
if guard.get("campaign_queue_receipt_created") is not False:
    errors.append("diagnostic preparation unexpectedly created a campaign queue receipt")
if guard.get("campaign_queue_or_spend_artifact_touched") is not False:
    errors.append("diagnostic preparation unexpectedly touched campaign queue/spend state")

if not isinstance(quiescence, list) or len(quiescence) != 2:
    errors.append("external quiescence did not record exactly two observations")
else:
    for index, observation in enumerate(quiescence, start=1):
        if observation.get("observation") != index:
            errors.append(f"external quiescence observation ordinal mismatch: {index}")
        if observation.get("busy_processes") != []:
            errors.append(f"external quiescence observation {index} saw busy process")
        if observation.get("listener_127_0_0_1_1234") is not False:
            errors.append(f"external quiescence observation {index} saw/inferred busy default listener")

server_sha = binary.get("server_sha256")
old_sha = "0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e"
if server_sha == old_sha:
    errors.append("replacement binary unexpectedly equals consumed apparatus binary SHA")

out = {
    "primary_classification": (
        "LAYER0_PROJECTION_ORIGIN_PREMEASURED_READY"
        if not errors
        else "LAYER0_PROJECTION_ORIGIN_NOT_READY"
    ),
    "errors": errors,
    "server_sha256": server_sha,
    "model_sha256": binary.get("model_sha256"),
    "logical_prefix_patch_sha256": binary.get("logical_prefix_patch_sha256"),
    "aligned_reuse_patch_sha256": binary.get("aligned_reuse_patch_sha256"),
    "projection_origin_patch_sha256": binary.get("projection_origin_patch_sha256"),
    "runtime_artifacts": binary.get("runtime_artifacts"),
    "required_runtime_markers": binary.get("required_runtime_markers"),
    "forbidden_old_marker_present": binary.get("forbidden_old_marker_present"),
    "resource_guard": guard,
    "external_quiescence": quiescence,
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
