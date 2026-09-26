#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
  echo "usage: measured-descriptor-prepare-run.sh OUT_ROOT MODEL_PATH" >&2
  exit 64
fi

out_root=$1
model=$2

if [[ "$out_root" != /* ]]; then
  echo "absolute output root required" >&2
  exit 65
fi
if [[ -e "$out_root" ]]; then
  echo "output root must not exist before canonical launcher: $out_root" >&2
  exit 66
fi
case "$out_root" in
  /tmp/*|/var/tmp/*)
    echo "persistent non-/tmp output root required" >&2
    exit 67
    ;;
esac
if [[ "$out_root" =~ [[:space:]] ]]; then
  echo "output root must not contain whitespace" >&2
  exit 68
fi
if [[ ! -f "$model" ]]; then
  echo "model missing: $model" >&2
  exit 69
fi
if [[ -z "${RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD:-}" ]]; then
  echo "RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD is required" >&2
  exit 71
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor-prepare.py"
if [[ ! -f "$runner" ]]; then
  echo "descriptor transaction orchestrator missing: $runner" >&2
  exit 70
fi

exec env \
  -u PYTHONPYCACHEPREFIX \
  -u PYTHONPATH \
  -u PYTHONHOME \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONNOUSERSITE=1 \
  /usr/bin/python3 -B -I "$runner" --out-root "$out_root" --model "$model"
