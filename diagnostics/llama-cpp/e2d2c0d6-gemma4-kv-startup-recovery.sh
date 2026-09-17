#!/usr/bin/env bash
set -uo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  kv-startup-recovery.sh OUT_DIR SERVER_BIN MODEL_PATH PORT MODE

MODE:
  plain  - no KV probe environment
  probe  - set KV probe environment but send no generation request

This helper is strictly non-generative.
EOF
}

if (( $# != 5 )); then
  usage
  exit 64
fi

out_dir=$1
server_bin=$2
model_path=$3
port=$4
mode=$5

case "$mode" in
  plain|probe) ;;
  *) usage; exit 64 ;;
esac

mkdir -p "$out_dir"
: >"$out_dir/events.txt"

event() {
  printf '%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$out_dir/events.txt" >&2
}

cleanup_pid=""
cleanup() {
  if [[ -n "$cleanup_pid" ]] && kill -0 "$cleanup_pid" 2>/dev/null; then
    kill "$cleanup_pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "$cleanup_pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$cleanup_pid" 2>/dev/null; then
      kill -KILL "$cleanup_pid" 2>/dev/null || true
    fi
    wait "$cleanup_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

event "begin mode=$mode"

if [[ ! -x "$server_bin" ]]; then
  printf 'SERVER_BINARY_NOT_EXECUTABLE\n' >"$out_dir/classification.txt"
  exit 21
fi
if [[ ! -f "$model_path" ]]; then
  printf 'MODEL_PATH_INVALID\n' >"$out_dir/classification.txt"
  exit 22
fi

sha256sum "$server_bin" >"$out_dir/server-binary.sha256"
sha256sum "$model_path" >"$out_dir/model.sha256"
command -v file >/dev/null 2>&1 && file "$server_bin" >"$out_dir/server-binary.file.txt" 2>&1 || true
command -v ldd >/dev/null 2>&1 && ldd "$server_bin" >"$out_dir/server-binary.ldd.txt" 2>&1 || true
command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >"$out_dir/nvidia-smi.before.txt" 2>&1 || true

set +e
"$server_bin" --version >"$out_dir/server-version.stdout.txt" 2>"$out_dir/server-version.stderr.txt"
version_rc=$?
set -e
printf '%d\n' "$version_rc" >"$out_dir/server-version.exit-code.txt"
if (( version_rc != 0 )); then
  printf 'SERVER_VERSION_FAILED\n' >"$out_dir/classification.txt"
  exit 23
fi

if command -v ss >/dev/null 2>&1; then
  ss -ltnp >"$out_dir/ports.before.txt" 2>&1 || true
  if grep -Eq "[.:]${port}[[:space:]]" "$out_dir/ports.before.txt"; then
    printf 'PORT_ALREADY_OCCUPIED\n' >"$out_dir/classification.txt"
    exit 24
  fi
fi

cmd=(
  "$server_bin"
  --model "$model_path"
  --host 127.0.0.1
  --port "$port"
  --ctx-size 8192
  --parallel 1
  --gpu-layers 999
  --no-context-shift
  --batch-size 512
  --ubatch-size 512
  --flash-attn on
  --log-verbosity 4
)

{
  printf 'mode=%s\n' "$mode"
  printf 'argv_count=%d\n' "${#cmd[@]}"
  i=0
  for arg in "${cmd[@]}"; do
    printf 'argv_%d=%q\n' "$i" "$arg"
    i=$((i + 1))
  done
  printf 'shell='
  printf '%q ' "${cmd[@]}"
  printf '\n'
} >"$out_dir/server.argv.txt"

probe_root=""
if [[ "$mode" == "probe" ]]; then
  probe_root="$out_dir/probe-root"
  mkdir -p "$probe_root"
  export LLAMA_KV_PROBE_DIR="$probe_root"
  export LLAMA_KV_PROBE_LABEL="PRE"
  {
    printf 'LLAMA_KV_PROBE_DIR=%q\n' "$LLAMA_KV_PROBE_DIR"
    printf 'LLAMA_KV_PROBE_LABEL=%q\n' "$LLAMA_KV_PROBE_LABEL"
  } >"$out_dir/probe-env.txt"
else
  unset LLAMA_KV_PROBE_DIR || true
  unset LLAMA_KV_PROBE_LABEL || true
fi

event "launching server"
"${cmd[@]}" >"$out_dir/server.stdout.txt" 2>"$out_dir/server.stderr.txt" &
pid=$!
cleanup_pid=$pid
printf '%d\n' "$pid" >"$out_dir/server.pid.txt"

if [[ -r "/proc/$pid/cmdline" ]]; then
  tr '\0' '\n' <"/proc/$pid/cmdline" >"$out_dir/proc-cmdline.txt" 2>/dev/null || true
fi
if [[ -r "/proc/$pid/status" ]]; then
  cat "/proc/$pid/status" >"$out_dir/proc-status.initial.txt" 2>/dev/null || true
fi

timeout_s=${STARTUP_TIMEOUT_S:-180}
deadline=$((SECONDS + timeout_s))
health_ok=0
attempt=0

while (( SECONDS < deadline )); do
  attempt=$((attempt + 1))
  if ! kill -0 "$pid" 2>/dev/null; then
    set +e
    wait "$pid"
    rc=$?
    set -e
    cleanup_pid=""
    printf '%d\n' "$rc" >"$out_dir/server.exit-code.txt"
    if (( rc >= 128 )); then
      printf '%d\n' "$((rc - 128))" >"$out_dir/server.exit-signal.txt"
    fi
    command -v ss >/dev/null 2>&1 && ss -ltnp >"$out_dir/ports.after-exit.txt" 2>&1 || true
    command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >"$out_dir/nvidia-smi.after-exit.txt" 2>&1 || true
    dmesg 2>/dev/null | tail -n 300 >"$out_dir/dmesg.tail.txt" || true
    event "server exited before readiness rc=$rc attempt=$attempt"
    printf 'SERVER_EXITED_BEFORE_READINESS\n' >"$out_dir/classification.txt"
    exit 25
  fi

  set +e
  http=$(curl --silent --show-error --max-time 2 --output "$out_dir/health-response.tmp" --write-out '%{http_code}' "http://127.0.0.1:${port}/health" 2>"$out_dir/health-curl.stderr.tmp")
  curl_rc=$?
  set -e
  printf '%d\t%d\t%s\n' "$attempt" "$curl_rc" "$http" >>"$out_dir/health-attempts.tsv"

  if (( curl_rc == 0 )) && [[ "$http" == "200" ]]; then
    mv "$out_dir/health-response.tmp" "$out_dir/health-response.json"
    mv "$out_dir/health-curl.stderr.tmp" "$out_dir/health-curl.stderr.txt"
    health_ok=1
    break
  fi
  sleep 1
done

if (( health_ok == 0 )); then
  command -v ss >/dev/null 2>&1 && ss -ltnp >"$out_dir/ports.timeout.txt" 2>&1 || true
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >"$out_dir/nvidia-smi.timeout.txt" 2>&1 || true
  dmesg 2>/dev/null | tail -n 300 >"$out_dir/dmesg.tail.txt" || true
  event "startup timeout"
  printf 'STARTUP_READINESS_TIMEOUT\n' >"$out_dir/classification.txt"
  exit 26
fi

event "health ready"

# Strictly non-generative. Clean shutdown immediately after readiness.
kill "$pid" 2>/dev/null || true
set +e
wait "$pid"
rc=$?
set -e
cleanup_pid=""
printf '%d\n' "$rc" >"$out_dir/server.exit-code-after-health.txt"

grep -Ei 'flash|attention|cuda|n_batch|n_ubatch|ctx|context|parallel|slot|model|swa|error|fatal|assert' "$out_dir/server.stdout.txt" "$out_dir/server.stderr.txt" >"$out_dir/startup-evidence.filtered.txt" 2>/dev/null || true

if ! grep -Eqi 'flash[^[:alnum:]]*att|flash_attn|flash attention' "$out_dir/startup-evidence.filtered.txt"; then
  printf 'FLASH_ATTN_EVIDENCE_MISSING\n' >"$out_dir/classification.txt"
  exit 27
fi
if ! grep -Eqi 'n_batch[^0-9]*512|n_batch *= *512' "$out_dir/startup-evidence.filtered.txt"; then
  printf 'BATCH_EVIDENCE_MISSING\n' >"$out_dir/classification.txt"
  exit 28
fi
if ! grep -Eqi 'n_ubatch[^0-9]*512|n_ubatch *= *512' "$out_dir/startup-evidence.filtered.txt"; then
  printf 'UBATCH_EVIDENCE_MISSING\n' >"$out_dir/classification.txt"
  exit 29
fi

if [[ "$mode" == "probe" ]] && find "$probe_root" -mindepth 1 -print -quit | grep -q .; then
  printf 'UNEXPECTED_DUMP_DURING_NON_GENERATIVE_PREFLIGHT\n' >"$out_dir/classification.txt"
  exit 30
fi

printf 'READY_NON_GENERATIVE\n' >"$out_dir/classification.txt"
event "success READY_NON_GENERATIVE"
