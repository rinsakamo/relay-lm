#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  layer0-projection-provenance-build-run.sh OUT_ROOT LLAMA_SOURCE_REPO [JOBS]

Creates a disposable local clone of an existing llama.cpp repository, checks out
the exact frozen source revision, applies the aligned-reuse, logical-prefix, projection-origin, and projection-provenance
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
CUDA_TOOLKIT_ROOT=/usr/local/cuda-12.8
CUDA_NVCC="$CUDA_TOOLKIT_ROOT/bin/nvcc"
CUDA_NATIVE_PATH="$CUDA_TOOLKIT_ROOT/bin:/usr/bin:/bin"

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
origin_patch="$script_dir/e2d2c0d6-gemma4-layer0-projection-origin-diagnostic.patch"
provenance_patch="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-diagnostic.patch"
patch_selftest="$script_dir/e2d2c0d6-gemma4-kv-logical-prefix-patch-selftest.py"
origin_patch_selftest="$script_dir/e2d2c0d6-gemma4-layer0-projection-origin-patch-selftest.py"
provenance_patch_selftest="$script_dir/e2d2c0d6-gemma4-layer0-projection-provenance-patch-selftest.py"

for required in "$aligned_patch" "$logical_patch" "$origin_patch" "$provenance_patch" "$patch_selftest" "$origin_patch_selftest" "$provenance_patch_selftest"; do
  if [[ ! -f "$required" ]]; then
    echo "required diagnostic input missing: $required" >&2
    exit 68
  fi
done

mkdir -p "$out_root"
mkdir -p "$out_root/hermetic-home" "$out_root/hermetic-tmp"

# Host binding is intentionally explicit. WSL may inherit a Windows CUDA path;
# using it can make FindCUDAToolkit select nvcc.exe while Linux cudart remains
# unresolved. The replacement build is qualified only against this observed
# native Linux toolkit.
if [[ ! -d "$CUDA_TOOLKIT_ROOT" ]]; then
  echo "qualified native CUDA toolkit root missing: $CUDA_TOOLKIT_ROOT" >&2
  exit 72
fi
if [[ ! -x "$CUDA_NVCC" ]]; then
  echo "qualified native CUDA nvcc missing or non-executable: $CUDA_NVCC" >&2
  exit 73
fi

cuda_root_real=$(readlink -f "$CUDA_TOOLKIT_ROOT")
cuda_nvcc_real=$(readlink -f "$CUDA_NVCC")
if [[ "$cuda_root_real" != "$CUDA_TOOLKIT_ROOT" ]]; then
  echo "unexpected CUDA toolkit canonical root: $cuda_root_real" >&2
  exit 74
fi
if [[ "$cuda_nvcc_real" != "$CUDA_NVCC" ]]; then
  echo "unexpected CUDA nvcc canonical path: $cuda_nvcc_real" >&2
  exit 75
fi

PATH="$CUDA_NATIVE_PATH" "$CUDA_NVCC" --version >"$out_root/cuda-nvcc-version.txt" 2>&1
PATH="$CUDA_NATIVE_PATH" cmake --version >"$out_root/cmake-version.txt" 2>&1
PATH="$CUDA_NATIVE_PATH" cc --version >"$out_root/cc-version.txt" 2>&1
PATH="$CUDA_NATIVE_PATH" c++ --version >"$out_root/cxx-version.txt" 2>&1
if ! grep -Fq "release 12.8" "$out_root/cuda-nvcc-version.txt"; then
  echo "qualified CUDA nvcc is not release 12.8" >&2
  exit 76
fi

printf "%s\n" "$CUDA_TOOLKIT_ROOT" >"$out_root/cuda-toolkit-root.txt"
printf "%s\n" "$CUDA_NVCC" >"$out_root/cuda-nvcc.txt"
printf "%s\n" "$CUDA_NATIVE_PATH" >"$out_root/cuda-native-path.txt"
cat >"$out_root/build-environment.txt" <<EOF
HOME=$out_root/hermetic-home
TMPDIR=$out_root/hermetic-tmp
PATH=$CUDA_NATIVE_PATH
LANG=C.UTF-8
LC_ALL=C.UTF-8
CUDAToolkit_ROOT=$CUDA_TOOLKIT_ROOT
CUDACXX=$CUDA_NVCC
EOF
if [[ -f "$CUDA_TOOLKIT_ROOT/version.json" ]]; then
  sha256sum "$CUDA_TOOLKIT_ROOT/version.json" >"$out_root/cuda-version-json.sha256"
fi

python3 -m py_compile "$patch_selftest"
python3 "$patch_selftest" >"$out_root/logical-prefix-patch-selftest.json"
python3 "$origin_patch_selftest" --llama-repo "$llama_repo" >"$out_root/projection-origin-patch-selftest.json"
python3 "$provenance_patch_selftest" --llama-repo "$llama_repo" >"$out_root/projection-provenance-patch-selftest.json"

sha256sum "$aligned_patch" >"$out_root/aligned-reuse.patch.sha256"
sha256sum "$logical_patch" >"$out_root/logical-prefix.patch.sha256"
sha256sum "$origin_patch" >"$out_root/projection-origin.patch.sha256"
sha256sum "$provenance_patch" >"$out_root/projection-provenance.patch.sha256"

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
git -C "$src" apply --check "$origin_patch" >"$out_root/origin-apply-check.stdout.txt" 2>"$out_root/origin-apply-check.stderr.txt"
git -C "$src" apply "$origin_patch"
git -C "$src" apply --check "$provenance_patch" >"$out_root/provenance-apply-check.stdout.txt" 2>"$out_root/provenance-apply-check.stderr.txt"
git -C "$src" apply "$provenance_patch"
git -C "$src" diff --check >"$out_root/git-diff-check.stdout.txt" 2>"$out_root/git-diff-check.stderr.txt"
git -C "$src" diff --binary >"$out_root/applied.patch"
sha256sum "$out_root/applied.patch" >"$out_root/applied.patch.sha256"
git -C "$src" status --porcelain --untracked-files=all >"$out_root/source.status-after-patches.txt"

cat >"$out_root/cmake-contract.txt" <<'EOF'
GGML_CUDA=ON
GGML_CUDA_GRAPHS=ON
GGML_CUDA_FA=ON
GGML_NATIVE=ON
GGML_CCACHE=OFF
BUILD_SHARED_LIBS=ON
GGML_BACKEND_DL=OFF
CMAKE_BUILD_TYPE=Release
EOF

env -i \
HOME="$out_root/hermetic-home" \
TMPDIR="$out_root/hermetic-tmp" \
PATH="$CUDA_NATIVE_PATH" \
LANG=C.UTF-8 LC_ALL=C.UTF-8 \
CUDAToolkit_ROOT="$CUDA_TOOLKIT_ROOT" \
CUDACXX="$CUDA_NVCC" \
cmake -S "$src" -B "$build" \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_GRAPHS=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_NATIVE=ON \
  -DGGML_CCACHE=OFF \
  -DBUILD_SHARED_LIBS=ON \
  -DGGML_BACKEND_DL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDAToolkit_ROOT="$CUDA_TOOLKIT_ROOT" \
  -DCMAKE_CUDA_COMPILER="$CUDA_NVCC" \
  >"$out_root/cmake-configure.stdout.txt" 2>"$out_root/cmake-configure.stderr.txt"

env -i \
HOME="$out_root/hermetic-home" \
TMPDIR="$out_root/hermetic-tmp" \
PATH="$CUDA_NATIVE_PATH" \
LANG=C.UTF-8 LC_ALL=C.UTF-8 \
CUDAToolkit_ROOT="$CUDA_TOOLKIT_ROOT" \
CUDACXX="$CUDA_NVCC" \
cmake --build "$build" --target llama-server --parallel "$jobs" \
  >"$out_root/cmake-build.stdout.txt" 2>"$out_root/cmake-build.stderr.txt"

server_bin="$build/bin/llama-server"
if [[ ! -x "$server_bin" ]]; then
  echo "built llama-server is missing or non-executable: $server_bin" >&2
  exit 71
fi

sha256sum "$server_bin" >"$out_root/server-binary.sha256"
server_impl="$build/bin/libllama-server-impl.so"
llama_lib="$build/bin/libllama.so"
ggml_lib="$build/bin/libggml.so"
ggml_base="$build/bin/libggml-base.so"
ggml_cpu="$build/bin/libggml-cpu.so"
ggml_cuda="$build/bin/libggml-cuda.so"
for artifact in "$server_impl" "$llama_lib" "$ggml_lib" "$ggml_base" "$ggml_cpu" "$ggml_cuda"; do
  if [[ ! -f "$artifact" ]]; then
    echo "required runtime library missing: $artifact" >&2
    exit 77
  fi
done
sha256sum "$server_impl" >"$out_root/server-impl.sha256"
sha256sum "$llama_lib" >"$out_root/llama-lib.sha256"
sha256sum "$ggml_lib" >"$out_root/ggml-lib.sha256"
sha256sum "$ggml_base" >"$out_root/ggml-base.sha256"
sha256sum "$ggml_cpu" >"$out_root/ggml-cpu.sha256"
sha256sum "$ggml_cuda" >"$out_root/ggml-cuda.sha256"
readlink -f "$server_bin" >"$out_root/server-binary.resolved.txt"
readlink -f "$server_impl" >"$out_root/server-impl.resolved.txt"
readlink -f "$llama_lib" >"$out_root/llama-lib.resolved.txt"
readlink -f "$ggml_lib" >"$out_root/ggml-lib.resolved.txt"
readlink -f "$ggml_base" >"$out_root/ggml-base.resolved.txt"
readlink -f "$ggml_cpu" >"$out_root/ggml-cpu.resolved.txt"
readlink -f "$ggml_cuda" >"$out_root/ggml-cuda.resolved.txt"
chmod a-w "$server_bin" "$server_impl" "$llama_lib" "$ggml_lib" "$ggml_base" "$ggml_cpu" "$ggml_cuda" "$out_root/applied.patch"
LD_LIBRARY_PATH="$build/bin:/usr/local/cuda-12.8/lib64" "$server_bin" --version >"$out_root/server-version.stdout.txt" 2>"$out_root/server-version.stderr.txt"

python3 - "$out_root" "$server_bin" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
server = Path(sys.argv[2])

def first(path):
    return (root / path).read_text(encoding="utf-8").strip().split()[0]

out = {
    "preparation_generation": "provenance-preparation-20260923-d",
    "primary_classification": "LAYER0_PROJECTION_PROVENANCE_BUILD_READY",
    "source_head": (root / "source.head.txt").read_text(encoding="utf-8").strip(),
    "source_tree": (root / "source.tree.txt").read_text(encoding="utf-8").strip(),
    "aligned_reuse_patch_sha256": first("aligned-reuse.patch.sha256"),
    "logical_prefix_patch_sha256": first("logical-prefix.patch.sha256"),
    "projection_origin_patch_sha256": first("projection-origin.patch.sha256"),
    "projection_provenance_patch_sha256": first("projection-provenance.patch.sha256"),
    "applied_patch_sha256": first("applied.patch.sha256"),
    "cuda_toolkit_root": (root / "cuda-toolkit-root.txt").read_text(encoding="utf-8").strip(),
    "cuda_nvcc": (root / "cuda-nvcc.txt").read_text(encoding="utf-8").strip(),
    "cuda_nvcc_version": (root / "cuda-nvcc-version.txt").read_text(encoding="utf-8").strip(),
    "cuda_native_path": (root / "cuda-native-path.txt").read_text(encoding="utf-8").strip(),
    "cmake_contract": (root / "cmake-contract.txt").read_text(encoding="utf-8").strip().splitlines(),
    "build_environment": (root / "build-environment.txt").read_text(encoding="utf-8").strip().splitlines(),
    "cmake_version": (root / "cmake-version.txt").read_text(encoding="utf-8").strip(),
    "cc_version": (root / "cc-version.txt").read_text(encoding="utf-8").strip(),
    "cxx_version": (root / "cxx-version.txt").read_text(encoding="utf-8").strip(),
    "server_binary": str(server),
    "server_binary_resolved": (root / "server-binary.resolved.txt").read_text(encoding="utf-8").strip(),
    "server_sha256": first("server-binary.sha256"),
    "server_impl_resolved": (root / "server-impl.resolved.txt").read_text(encoding="utf-8").strip(),
    "server_impl_sha256": first("server-impl.sha256"),
    "llama_lib_resolved": (root / "llama-lib.resolved.txt").read_text(encoding="utf-8").strip(),
    "llama_lib_sha256": first("llama-lib.sha256"),
    "ggml_lib_resolved": (root / "ggml-lib.resolved.txt").read_text(encoding="utf-8").strip(),
    "ggml_lib_sha256": first("ggml-lib.sha256"),
    "ggml_base_resolved": (root / "ggml-base.resolved.txt").read_text(encoding="utf-8").strip(),
    "ggml_base_sha256": first("ggml-base.sha256"),
    "ggml_cpu_resolved": (root / "ggml-cpu.resolved.txt").read_text(encoding="utf-8").strip(),
    "ggml_cpu_sha256": first("ggml-cpu.sha256"),
    "ggml_cuda_resolved": (root / "ggml-cuda.resolved.txt").read_text(encoding="utf-8").strip(),
    "ggml_cuda_sha256": first("ggml-cuda.sha256"),
    "generated_requests": 0,
    "measured_attempt_consumed": False,
}
(root / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2, sort_keys=True))
PY
