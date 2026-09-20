#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  logical-prefix-build-run.sh OUT_ROOT LLAMA_SOURCE_REPO [JOBS]

Creates a disposable local clone of an existing llama.cpp repository, checks out
the exact frozen source revision, applies the aligned-reuse and logical-prefix
diagnostic patches, and builds only llama-server with CUDA enabled.

This helper performs no model load and no generation.
EOF
}

if (( $# < 2 || $# > 3 )); then
  usage
  exit 64
fi

out_root=$1
llama_repo=$2
jobs=${3:-4}

REV=e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d

if [[ -e "$out_root" ]]; then
  echo "output root must not exist: $out_root" >&2
  exit 65
fi
if [[ ! -d "$llama_repo/.git" ]]; then
  echo "llama source repository is not a git checkout: $llama_repo" >&2
  exit 66
fi
if ! git -C "$llama_repo" cat-file -e "${REV}^{commit}" 2>/dev/null; then
  echo "frozen llama.cpp revision is unavailable in source repository" >&2
  exit 67
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
aligned_patch="$script_dir/e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch"
logical_patch="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"
patch_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-patch-selftest.py"

for required in "$aligned_patch" "$logical_patch" "$patch_selftest"; do
  if [[ ! -f "$required" ]]; then
    echo "required diagnostic input missing: $required" >&2
    exit 68
  fi
done

mkdir -p "$out_root"
python3 -m py_compile "$patch_selftest"
python3 "$patch_selftest" >"$out_root/logical-prefix-patch-selftest.json"

sha256sum "$aligned_patch" >"$out_root/aligned-reuse.patch.sha256"
sha256sum "$logical_patch" >"$out_root/logical-prefix.patch.sha256"

src="$out_root/source"
build="$out_root/build"

git clone --no-local "$llama_repo" "$src" >"$out_root/git-clone.stdout.txt" 2>"$out_root/git-clone.stderr.txt"
git -C "$src" checkout --detach "$REV" >"$out_root/git-checkout.stdout.txt" 2>"$out_root/git-checkout.stderr.txt"

actual_head=$(git -C "$src" rev-parse HEAD)
actual_tree=$(git -C "$src" rev-parse "HEAD^{tree}")
printf "%s\n" "$actual_head" >"$out_root/source.head.txt"
printf "%s\n" "$actual_tree" >"$out_root/source.tree.txt"
if [[ "$actual_head" != "$REV" ]]; then
  echo "unexpected source HEAD: $actual_head" >&2
  exit 69
fi
if [[ -n "$(git -C "$src" status --porcelain --untracked-files=all)" ]]; then
  echo "fresh disposable source checkout is not clean" >&2
  exit 70
fi

git -C "$src" apply --check "$aligned_patch" >"$out_root/aligned-apply-check.stdout.txt" 2>"$out_root/aligned-apply-check.stderr.txt"
git -C "$src" apply "$aligned_patch"
git -C "$src" apply --check "$logical_patch" >"$out_root/logical-apply-check.stdout.txt" 2>"$out_root/logical-apply-check.stderr.txt"
git -C "$src" apply "$logical_patch"
git -C "$src" diff --check >"$out_root/git-diff-check.stdout.txt" 2>"$out_root/git-diff-check.stderr.txt"
git -C "$src" diff --binary >"$out_root/applied.patch"
sha256sum "$out_root/applied.patch" >"$out_root/applied.patch.sha256"
git -C "$src" status --porcelain --untracked-files=all >"$out_root/source.status-after-patches.txt"

cmake -S "$src" -B "$build" \
  -DGGML_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release \
  >"$out_root/cmake-configure.stdout.txt" 2>"$out_root/cmake-configure.stderr.txt"

cmake --build "$build" --target llama-server --parallel "$jobs" \
  >"$out_root/cmake-build.stdout.txt" 2>"$out_root/cmake-build.stderr.txt"

server_bin="$build/bin/llama-server"
if [[ ! -x "$server_bin" ]]; then
  echo "built llama-server is missing or non-executable: $server_bin" >&2
  exit 71
fi

sha256sum "$server_bin" >"$out_root/server-binary.sha256"
"$server_bin" --version >"$out_root/server-version.stdout.txt" 2>"$out_root/server-version.stderr.txt"

python3 - "$out_root" "$server_bin" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
server = Path(sys.argv[2])

def first(path):
    return (root / path).read_text(encoding="utf-8").strip().split()[0]

out = {
    "primary_classification": "LOGICAL_PREFIX_REPLACEMENT_BUILD_READY",
    "source_head": (root / "source.head.txt").read_text(encoding="utf-8").strip(),
    "source_tree": (root / "source.tree.txt").read_text(encoding="utf-8").strip(),
    "aligned_reuse_patch_sha256": first("aligned-reuse.patch.sha256"),
    "logical_prefix_patch_sha256": first("logical-prefix.patch.sha256"),
    "applied_patch_sha256": first("applied.patch.sha256"),
    "server_binary": str(server),
    "server_sha256": first("server-binary.sha256"),
    "generated_requests": 0,
    "measured_attempt_consumed": False,
}
(root / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2, sort_keys=True))
PY
