#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  kv-startup-recovery-run.sh OUT_ROOT SERVER_BIN MODEL_PATH PORT_PLAIN PORT_PROBE

Runs the strictly non-generative startup recovery sequence:
  plain -> probe -> classifier

No generation request is sent.
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

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
startup="$script_dir/e2d2c0d6-gemma4-kv-startup-recovery.sh"
classifier="$script_dir/e2d2c0d6-gemma4-kv-startup-recovery-classify.py"

if [[ ! -f "$startup" || ! -f "$classifier" ]]; then
  echo "required recovery helpers missing" >&2
  exit 66
fi

mkdir -p "$out_root"
plain="$out_root/plain"
probe="$out_root/probe"

if [[ -e "$plain" || -e "$probe" || -e "$out_root/startup-recovery-terminal.json" ]]; then
  echo "output root is not fresh: $out_root" >&2
  exit 67
fi

mkdir -p "$plain" "$probe"

set +e
bash "$startup" "$plain" "$server_bin" "$model_path" "$port_plain" plain
plain_rc=$?
set -e
printf '%d\n' "$plain_rc" >"$out_root/plain.runner-exit-code.txt"
if (( plain_rc != 0 )); then
  printf 'NOT_INVOKED_AFTER_PLAIN_FAILURE\n' >"$out_root/probe.runner-state.txt"
  exit "$plain_rc"
fi

set +e
bash "$startup" "$probe" "$server_bin" "$model_path" "$port_probe" probe
probe_rc=$?
set -e
printf '%d\n' "$probe_rc" >"$out_root/probe.runner-exit-code.txt"
if (( probe_rc != 0 )); then
  exit "$probe_rc"
fi

python3 "$classifier" "$plain" "$probe" >"$out_root/startup-recovery-terminal.json"
cat "$out_root/startup-recovery-terminal.json"
