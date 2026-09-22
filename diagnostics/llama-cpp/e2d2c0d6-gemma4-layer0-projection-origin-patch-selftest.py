#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


REV = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"


def run(cmd, *, cwd=None):
    cp = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"command failed ({cp.returncode}): {' '.join(map(str, cmd))}\n"
            f"stdout:\n{cp.stdout}\nstderr:\n{cp.stderr}"
        )
    return cp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama-repo", type=Path, required=True)
    args = ap.parse_args()

    repo = args.llama_repo.resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"not a git checkout: {repo}")

    here = Path(__file__).resolve().parent
    patches = [
        here / "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch",
        here / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch",
        here / "e2d2c0d6-gemma4-layer0-projection-origin-diagnostic.patch",
    ]
    for patch in patches:
        if not patch.is_file():
            raise RuntimeError(f"required patch missing: {patch}")

    origin_text = patches[-1].read_text(encoding="utf-8")
    if "ggml_backend_sched_set_eval_callback" in origin_text:
        raise RuntimeError("origin patch must not install an eval callback")
    for marker in (
        'ggml_set_output(cur)',
        '"attn_norm"',
        '"Kcur"',
        '"Vcur"',
        'ubatch.n_tokens == 371',
        'ubatch.n_tokens == 508',
        'ubatch.n_tokens == 512',
        'ggml_backend_sched_synchronize(sched.get())',
        'ggml_backend_tensor_get',
    ):
        if marker not in origin_text:
            raise RuntimeError(f"origin patch marker missing: {marker}")

    run(["git", "-C", str(repo), "cat-file", "-e", f"{REV}^{{commit}}"])

    with tempfile.TemporaryDirectory(prefix="relaylm-projection-origin-patch-") as td:
        src = Path(td) / "source"
        run(["git", "clone", "--no-local", str(repo), str(src)])
        run(["git", "-C", str(src), "checkout", "--detach", REV])

        if run(["git", "-C", str(src), "rev-parse", "HEAD"]).stdout.strip() != REV:
            raise RuntimeError("frozen source checkout mismatch")

        for patch in patches:
            run(["git", "-C", str(src), "apply", "--check", str(patch)])
            run(["git", "-C", str(src), "apply", str(patch)])

        run(["git", "-C", str(src), "diff", "--check"])

        context = (src / "src" / "llama-context.cpp").read_text(encoding="utf-8")
        required = (
            "relay_projection_origin_probe_enabled",
            "relay_projection_origin_target_ubatch",
            "relay_projection_origin_dump",
            "LLAMA_PROJECTION_ORIGIN_PROBE_DIR",
            "LLAMA_PROJECTION_ORIGIN_PROBE_LABEL",
        )
        missing = [x for x in required if x not in context]
        if missing:
            raise RuntimeError(f"patched source markers missing: {missing}")

        status = run(
            ["git", "-C", str(src), "status", "--porcelain", "--untracked-files=all"]
        ).stdout.splitlines()
        if not status:
            raise RuntimeError("expected diagnostic patch modifications are absent")

        result = {
            "primary_classification": "LAYER0_PROJECTION_ORIGIN_PATCH_STATIC_PASS",
            "frozen_source_head": REV,
            "patches": [str(p.name) for p in patches],
            "changed_paths": sorted(
                line[3:] for line in status if len(line) >= 4
            ),
            "gpu_calls": 0,
            "model_loads": 0,
            "generation_requests": 0,
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
