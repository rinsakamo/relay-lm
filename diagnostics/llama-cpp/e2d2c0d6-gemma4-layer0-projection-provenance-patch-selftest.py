#!/usr/bin/env python3
import argparse
import ast
import json
import re
from pathlib import Path
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
        here / "e2d2c0d6-gemma4-layer0-projection-provenance-diagnostic.patch",
    ]
    for patch in patches:
        if not patch.is_file():
            raise RuntimeError(f"required patch missing: {patch}")

    provenance_text = patches[-1].read_text(encoding="utf-8")

    required_patch_markers = (
        '"provenance.tsv"',
        'ggml_graph_get_tensor(gf, name)',
        'ggml_op_name(tensor->op)',
    )
    missing = [x for x in required_patch_markers if x not in provenance_text]
    if missing:
        raise RuntimeError(f"provenance patch markers missing: {missing}")

    # The TSV header is intentionally emitted as multiple adjacent/streamed C++
    # string literals. Validate the decoded header schema instead of requiring
    # every field name to appear as its own separately quoted literal.
    header_start = provenance_text.find('<< "name\\\\ttensor_ptr')
    if header_start < 0:
        raise RuntimeError("provenance TSV header start missing")
    header_end = provenance_text.find(";", header_start)
    if header_end < 0:
        raise RuntimeError("provenance TSV header terminator missing")
    header_region = provenance_text[header_start:header_end]
    string_tokens = re.findall(r'"(?:\\\\.|[^"\\\\])*"', header_region)
    try:
        decoded_header = "".join(ast.literal_eval(token) for token in string_tokens)
    except (SyntaxError, ValueError) as exc:
        raise RuntimeError(f"unable to decode provenance TSV header literals: {exc}") from exc
    header_fields = decoded_header.rstrip("\\n").split("\\t")

    expected_header_fields = [
        "name", "tensor_ptr", "data_ptr", "buffer_ptr", "view_src_ptr",
        "view_src_data_ptr", "view_offs", "op", "flags", "type", "ne0",
        "ne1", "nb0", "nb1", "src0_ptr", "src0_name", "src0_type",
        "src0_data_ptr", "src0_buffer_ptr", "src0_op", "src1_ptr",
        "src1_name", "src1_type", "src1_data_ptr", "src1_buffer_ptr",
        "src1_op",
    ]
    if header_fields != expected_header_fields:
        raise RuntimeError(
            f"provenance TSV header schema mismatch: {header_fields!r}"
        )

    forbidden = (
        "ggml_mul_mat(",
        "ggml_add(",
        "ggml_mul(",
        "ggml_scale(",
        "ggml_backend_sched_set_eval_callback",
        "ggml_backend_graph_compute",
    )
    present_forbidden = [x for x in forbidden if x in provenance_text]
    if present_forbidden:
        raise RuntimeError(f"provenance patch unexpectedly adds execution/arithmetic: {present_forbidden}")

    run(["git", "-C", str(repo), "cat-file", "-e", f"{REV}^{{commit}}"])

    with tempfile.TemporaryDirectory(prefix="relaylm-projection-provenance-patch-") as td:
        src = Path(td) / "source"
        run(["git", "clone", "--no-local", str(repo), str(src)])
        run(["git", "-C", str(src), "checkout", "--detach", REV])
        head = run(["git", "-C", str(src), "rev-parse", "HEAD"]).stdout.strip()
        if head != REV:
            raise RuntimeError(f"frozen source checkout mismatch: {head}")

        for patch in patches:
            run(["git", "-C", str(src), "apply", "--check", str(patch)])
            run(["git", "-C", str(src), "apply", str(patch)])

        run(["git", "-C", str(src), "diff", "--check"])

        context = (src / "src" / "llama-context.cpp").read_text(encoding="utf-8")
        required_source_markers = (
            'root / "provenance.tsv"',
            '<< name',
            "<< '\\t' << tensor",
            "<< '\\t' << tensor->data",
            "<< '\\t' << tensor->buffer",
            "<< '\\t' << tensor->view_src",
            "<< '\\t' << tensor->view_offs",
            "emit_src(tensor->src[0])",
            "emit_src(tensor->src[1])",
            "ggml_backend_sched_synchronize(sched.get())",
            "ggml_set_output(cur)",
        )
        missing = [x for x in required_source_markers if x not in context]
        if missing:
            raise RuntimeError(f"patched provenance source markers missing: {missing}")

        status = run(
            ["git", "-C", str(src), "status", "--porcelain", "--untracked-files=all"]
        ).stdout.splitlines()
        if not status:
            raise RuntimeError("expected diagnostic patch modifications are absent")

        result = {
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PATCH_STATIC_PASS",
            "selftest_generation": "projection-provenance-static-20260923-b",
            "provenance_header_fields": expected_header_fields,
            "frozen_source_head": REV,
            "patches": [p.name for p in patches],
            "changed_paths": sorted(line[3:] for line in status if len(line) >= 4),
            "physical_calls": 0,
            "gpu_calls": 0,
            "model_loads": 0,
            "generation_requests": 0,
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
