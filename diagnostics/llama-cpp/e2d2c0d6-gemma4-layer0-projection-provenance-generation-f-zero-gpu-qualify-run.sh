#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  generation-f-zero-gpu-qualify-run.sh OUT_ROOT

Canonical zero-GPU launcher for provenance preparation generation-f.
Checks the output root before starting Python, removes PYTHONPYCACHEPREFIX,
and disables bytecode writes for the orchestrator process.
EOF
}

if (( $# != 1 )); then
  usage
  exit 64
fi

out_root=$1
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

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-generation-f-zero-gpu-qualify.py"

if [[ ! -f "$runner" ]]; then
  echo "zero-GPU orchestrator missing: $runner" >&2
  exit 69
fi

exec env -u PYTHONPYCACHEPREFIX   PYTHONDONTWRITEBYTECODE=1   python3 "$runner" --out-root "$out_root"
