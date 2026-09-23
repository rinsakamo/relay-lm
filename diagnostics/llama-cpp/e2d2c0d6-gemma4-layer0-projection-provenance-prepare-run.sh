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
case "$out_root" in
  /*) ;;
  *)
    echo "absolute persistent preparation evidence path required: $out_root" >&2
    exit 67
    ;;
esac
case "$out_root" in
  /tmp/*|/var/tmp/*)
    echo "persistent preparation evidence root required; refusing volatile path: $out_root" >&2
    exit 68
    ;;
esac
if [[ "$out_root" =~ [[:space:]] ]]; then
  echo "preparation evidence path must not contain whitespace: $out_root" >&2
  exit 68
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null || true)
authority_head=${RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD:-}
authority_ref="refs/remotes/origin/diagnostic/llama-cpp-gemma4-swa-live-prefix-20260916"
build_runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-build-run.sh"
qual_runner="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-qualification-run.sh"
static_selftest="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-preparation-static-selftest.py"

if [[ -z "$repo_root" || -z "$authority_head" ]]; then
  echo "isolated authority-bound RelayLM checkout and RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD are required" >&2
  exit 69
fi
case "$out_root" in
  "$repo_root"|"$repo_root"/*)
    echo "preparation evidence root must be outside the authority apparatus checkout" >&2
    exit 70
    ;;
esac
if ! git -C "$repo_root" show-ref --verify --quiet "$authority_ref"; then
  echo "fresh diagnostic remote-tracking ref missing: $authority_ref" >&2
  exit 71
fi
origin_url=$(git -C "$repo_root" remote get-url origin)
case "$origin_url" in
  https://github.com/rinsakamo/relay-lm|https://github.com/rinsakamo/relay-lm.git|git@github.com:rinsakamo/relay-lm.git) ;;
  *)
    echo "unexpected RelayLM authority origin: $origin_url" >&2
    exit 72
    ;;
esac
remote_head=$(git -C "$repo_root" rev-parse "$authority_ref")
local_head=$(git -C "$repo_root" rev-parse HEAD)
if [[ "$remote_head" != "$authority_head" || "$local_head" != "$authority_head" ]]; then
  echo "authority mismatch: remote=$remote_head local=$local_head expected=$authority_head" >&2
  exit 72
fi
if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]]; then
  echo "authority-bound RelayLM apparatus checkout is not clean" >&2
  exit 73
fi

if [[ ! -f "$build_runner" || ! -f "$qual_runner" || ! -f "$static_selftest" ]]; then
  echo "required replacement runners missing" >&2
  exit 74
fi

mkdir -p "$out_root"
printf '%s\n' "$authority_head" >"$out_root/relaylm-authority.head.txt"
printf '%s\n' "$remote_head" >"$out_root/relaylm-authority.remote-head.txt"
printf '%s\n' "$origin_url" >"$out_root/relaylm-authority.origin-url.txt"
git -C "$repo_root" rev-parse "HEAD^{tree}" >"$out_root/relaylm-authority.tree.txt"

PYTHONPYCACHEPREFIX="$out_root/pycache" python3 "$static_selftest" >"$out_root/preparation-static-selftest.json"
static_rc=$?
printf '%d\n' "$static_rc" >"$out_root/preparation-static-selftest.exit-code.txt"
if (( static_rc != 0 )); then
  echo "internal preparation static gate failed" >&2
  exit 72
fi
if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]]; then
  echo "authority apparatus checkout changed during static gate" >&2
  exit 75
fi

bash -n "$build_runner" || exit 73
bash -n "$qual_runner" || exit 73

build_root="$out_root/build-stage"
qual_root="$out_root/qualification-stage"

set +e
PYTHONPYCACHEPREFIX="$out_root/pycache" bash "$build_runner" "$build_root" "$llama_repo" "$jobs" \
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
  PYTHONPYCACHEPREFIX="$out_root/pycache" bash "$qual_runner" "$qual_root" "$server_bin" "$model_path" "$port_plain" "$port_probe" \
    >"$out_root/qualification-stage.stdout.txt" 2>"$out_root/qualification-stage.stderr.txt"
  qual_rc=$?
  set -e
else
  server_bin=""
  qual_rc=125
fi
printf "%d\n" "$qual_rc" >"$out_root/qualification-stage.exit-code.txt"

if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]]; then
  echo "authority apparatus checkout changed during preparation stages" >&2
  exit 76
fi

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

if build is not None and build.get("preparation_generation") != "provenance-preparation-20260923-d":
    errors.append("unexpected build preparation generation")
if qual is not None and qual.get("preparation_generation") != "provenance-preparation-20260923-d":
    errors.append("unexpected qualification preparation generation")

if build is not None and qual is not None:
    if build.get("server_sha256") != qual.get("server_sha256"):
        errors.append("build/qualification server SHA mismatch")
    runtime = qual.get("runtime_artifacts") or {}
    if build.get("server_impl_sha256") != (runtime.get("llama_server_impl") or {}).get("sha256"):
        errors.append("build/qualification server-impl SHA mismatch")
    if build.get("llama_lib_sha256") != (runtime.get("llama") or {}).get("sha256"):
        errors.append("build/qualification libllama SHA mismatch")
    for bkey, rkey, label in (
        ("ggml_lib_sha256", "ggml", "libggml"),
        ("ggml_base_sha256", "ggml_base", "libggml-base"),
        ("ggml_cpu_sha256", "ggml_cpu", "libggml-cpu"),
        ("ggml_cuda_sha256", "ggml_cuda", "libggml-cuda"),
    ):
        if build.get(bkey) != (runtime.get(rkey) or {}).get("sha256"):
            errors.append(f"build/qualification {label} SHA mismatch")
    patch_pairs = (
        ("aligned_reuse_patch_sha256", "aligned_reuse_patch_sha256"),
        ("logical_prefix_patch_sha256", "logical_prefix_patch_sha256"),
        ("projection_origin_patch_sha256", "projection_origin_patch_sha256"),
        ("projection_provenance_patch_sha256", "projection_provenance_patch_sha256"),
    )
    for bkey, qkey in patch_pairs:
        if build.get(bkey) != qual.get(qkey):
            errors.append(f"build/qualification patch SHA mismatch: {bkey}")

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
terminal_rc=$?

if (( terminal_rc == 0 )); then
  {
    sha256sum "$out_root/build-stage/build/bin/llama-server"
    sha256sum "$out_root/build-stage/build/bin/libllama-server-impl.so"
    sha256sum "$out_root/build-stage/build/bin/libllama.so"
    sha256sum "$out_root/build-stage/build/bin/libggml.so"
    sha256sum "$out_root/build-stage/build/bin/libggml-base.so"
    sha256sum "$out_root/build-stage/build/bin/libggml-cpu.so"
    sha256sum "$out_root/build-stage/build/bin/libggml-cuda.so"
    sha256sum "$out_root/build-stage/applied.patch"
    sha256sum "$out_root/terminal.json"
  } >"$out_root/prepared-artifact-manifest.sha256"
  chmod -R a-w "$out_root"
fi

exit "$terminal_rc"
