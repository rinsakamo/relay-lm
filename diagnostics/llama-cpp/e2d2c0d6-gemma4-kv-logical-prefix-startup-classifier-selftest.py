#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import sys


def load_classifier():
    here = Path(__file__).resolve().parent
    path = here / "e2d2c0d6-gemma4-kv-logical-prefix-startup-classify.py"
    spec = importlib.util.spec_from_file_location("logical_prefix_startup_classifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load startup classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_block(*, n_seq=1, n_ctx=8192, n_batch=512, n_ubatch=512, flash="enabled", base=8192, swa=1536):
    return (
        "llama_kv_cache_iswa: creating non-SWA KV cache, size = %d cells\n" % base
        + "llama_kv_cache_iswa: creating     SWA KV cache, size = %d cells\n" % swa
        + "llama_context: constructing llama_context\n"
        + "llama_context: n_seq_max             = %d\n" % n_seq
        + "llama_context: n_ctx                 = %d\n" % n_ctx
        + "llama_context: n_batch               = %d\n" % n_batch
        + "llama_context: n_ubatch              = %d\n" % n_ubatch
        + "llama_context: flash_attn            = %s\n" % flash
    )


def all_checks_true(evidence):
    return (
        evidence["context_block_count"] >= 1
        and all(v["ok"] for v in evidence["checks"].values())
    )


def main():
    c = load_classifier()
    errors = []

    valid = valid_block()
    if not all_checks_true(c.final_context_evidence(valid)):
        errors.append("valid final context did not pass")
    if not c.compact_swa_evidence(valid)["ok"]:
        errors.append("valid compact SWA did not pass")

    full = valid_block(swa=8192)
    if c.compact_swa_evidence(full)["ok"]:
        errors.append("full-size SWA incorrectly passed")

    wrong_compact = valid_block(swa=1024)
    if c.compact_swa_evidence(wrong_compact)["ok"]:
        errors.append("non-frozen compact SWA incorrectly passed")

    wrong_base = valid_block(base=4096)
    if c.compact_swa_evidence(wrong_base)["ok"]:
        errors.append("wrong base KV size incorrectly passed")

    missing_alloc = (
        "llama_context: constructing llama_context\n"
        "llama_context: n_seq_max = 1\n"
        "llama_context: n_ctx = 8192\n"
        "llama_context: n_batch = 512\n"
        "llama_context: n_ubatch = 512\n"
        "llama_context: flash_attn = enabled\n"
    )
    if c.compact_swa_evidence(missing_alloc)["ok"]:
        errors.append("missing allocation log incorrectly passed")

    split = valid_block() + valid_block(n_ctx=4096)
    split_evidence = c.final_context_evidence(split)
    if split_evidence["checks"]["n_ctx_8192"]["ok"]:
        errors.append("final-context selector mixed evidence across contexts")

    wrong_flash = valid_block(flash="disabled")
    if c.final_context_evidence(wrong_flash)["checks"]["flash_attn_enabled"]["ok"]:
        errors.append("disabled flash attention incorrectly passed")

    with tempfile.TemporaryDirectory(prefix="relaylm-startup-argv-selftest-") as td:
        root = Path(td)
        (root / "server-binary.resolved.txt").write_text("/tmp/llama-server\n", encoding="utf-8")
        (root / "model.resolved.txt").write_text("/tmp/model.gguf\n", encoding="utf-8")
        good = [
            "server_bin=/tmp/llama-server",
            "model_path=/tmp/model.gguf",
            *c.EXPECTED_CANONICAL_STATIC_ARGV,
        ]
        (root / "server.argv.canonical.txt").write_text("\n".join(good) + "\n", encoding="utf-8")
        if not c.canonical_argv_contract(root)["ok"]:
            errors.append("exact canonical argv contract did not pass")
        bad = good.copy()
        bad[5] = "--gpu-layers=998"
        (root / "server.argv.canonical.txt").write_text("\n".join(bad) + "\n", encoding="utf-8")
        if c.canonical_argv_contract(root)["ok"]:
            errors.append("drifted canonical argv incorrectly passed")

    with tempfile.TemporaryDirectory(prefix="relaylm-startup-env-selftest-") as td:
        root = Path(td)
        (root / "server-impl.resolved.txt").write_text("/evidence/bin/libllama-server-impl.so\n", encoding="utf-8")
        (root / "llama-lib.resolved.txt").write_text("/evidence/bin/libllama.so\n", encoding="utf-8")
        (root / "ggml-lib.resolved.txt").write_text("/evidence/bin/libggml.so\n", encoding="utf-8")
        (root / "ggml-base.resolved.txt").write_text("/evidence/bin/libggml-base.so\n", encoding="utf-8")
        (root / "ggml-cpu.resolved.txt").write_text("/evidence/bin/libggml-cpu.so\n", encoding="utf-8")
        (root / "ggml-cuda.resolved.txt").write_text("/evidence/bin/libggml-cuda.so\n", encoding="utf-8")
        base_env = {
            "HOME": "/home/test",
            "PATH": "/usr/local/cuda-12.8/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "LD_LIBRARY_PATH": "/evidence/bin:/usr/local/cuda-12.8/lib64",
            "CUDA_VISIBLE_DEVICES": "0",
            "GGML_CUDA_GRAPH_OPT": "0",
            "GGML_CUDA_DISABLE_FUSION": "0",
        }
        def write_env(path, env):
            path.write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8")

        write_env(root / "runtime-environment.effective.txt", base_env)
        write_env(root / "proc-environ.health-ready.txt", base_env)
        if not c.environment_contract("plain", root)["ok"]:
            errors.append("exact plain runtime environment did not pass")

        drift = dict(base_env)
        drift["GGML_CUDA_GRAPH_OPT"] = "1"
        write_env(root / "proc-environ.health-ready.txt", drift)
        if c.environment_contract("plain", root)["ok"]:
            errors.append("runtime environment drift incorrectly passed")

        probe_env = dict(base_env)
        probe_env["LLAMA_KV_PROBE_DIR"] = "/evidence/probe"
        probe_env["LLAMA_KV_PROBE_LABEL"] = "PRE"
        write_env(root / "runtime-environment.effective.txt", probe_env)
        write_env(root / "proc-environ.health-ready.txt", probe_env)
        if not c.environment_contract("probe", root)["ok"]:
            errors.append("exact probe runtime environment did not pass")

        (root / "proc-maps.health-ready.txt").write_text(
            "7f00-7f10 r-xp 0 00:00 0 /evidence/bin/libllama-server-impl.so\n"
            "7f10-7f20 r-xp 0 00:00 0 /evidence/bin/libllama.so\n"
            "7f20-7f30 r-xp 0 00:00 0 /evidence/bin/libggml.so\n"
            "7f30-7f40 r-xp 0 00:00 0 /evidence/bin/libggml-base.so\n"
            "7f40-7f50 r-xp 0 00:00 0 /evidence/bin/libggml-cpu.so\n"
            "7f50-7f60 r-xp 0 00:00 0 /evidence/bin/libggml-cuda.so\n",
            encoding="utf-8",
        )
        if not c.runtime_library_contract(root)["ok"]:
            errors.append("exact runtime library closure did not pass")
        (root / "proc-maps.health-ready.txt").write_text(
            "7f00-7f10 r-xp 0 00:00 0 /evidence/bin/libllama-server-impl.so\n"
            "7f10-7f20 r-xp 0 00:00 0 /evidence/bin/libllama.so\n"
            "7f20-7f30 r-xp 0 00:00 0 /evidence/bin/libggml.so\n"
            "7f30-7f40 r-xp 0 00:00 0 /evidence/bin/libggml-base.so\n"
            "7f40-7f50 r-xp 0 00:00 0 /evidence/bin/libggml-cpu.so\n"
            "7f50-7f60 r-xp 0 00:00 0 /other/libggml-cuda.so\n",
            encoding="utf-8",
        )
        if c.runtime_library_contract(root)["ok"]:
            errors.append("wrong runtime library path incorrectly passed")

    status = (
        "LOGICAL_PREFIX_STARTUP_CLASSIFIER_SELFTEST_PASS"
        if not errors
        else "LOGICAL_PREFIX_STARTUP_CLASSIFIER_SELFTEST_FAIL"
    )
    import json
    print(json.dumps({"status": status, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
