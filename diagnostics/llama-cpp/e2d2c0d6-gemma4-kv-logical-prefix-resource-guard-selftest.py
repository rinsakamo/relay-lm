#!/usr/bin/env python3
import errno
import importlib.util
import json
from pathlib import Path
import tempfile
import sys


def load_guard():
    here = Path(__file__).resolve().parent
    path = here / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
    spec = importlib.util.spec_from_file_location("logical_prefix_resource_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load resource guard")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_runtime_error(fn):
    try:
        fn()
    except RuntimeError:
        return True
    return False


def main():
    g = load_guard()
    results = []
    results.append({"name": "canonical_resource_key", "ok": g.RESOURCE_KEY == "llama-cpp:local-gpu"})
    results.append({"name": "canonical_lock_root", "ok": str(g.LOCK_ROOT) == "/tmp/relaylm/physical/locks"})
    results.append({"name": "busy_process_names", "ok": g.BUSY_NAMES == {"llama-server", "llama-cli", "llama-run"}})
    expected_lock = "a820834e5681ba28.lock"
    results.append({"name": "canonical_lock_filename", "ok": g.safe_resource_id(g.RESOURCE_KEY) == expected_lock})
    results.append({"name": "connect_success_is_busy", "ok": g.interpret_connect_ex(0) is True})
    results.append({"name": "connection_refused_is_idle", "ok": g.interpret_connect_ex(errno.ECONNREFUSED) is False})
    for name, code in (("eperm", errno.EPERM), ("eacces", errno.EACCES), ("timeout", errno.ETIMEDOUT)):
        results.append({"name": f"{name}_is_inconclusive", "ok": expect_runtime_error(lambda code=code: g.interpret_connect_ex(code))})

    original_names = g.process_executable_names
    original_listener = g.listener_busy
    original_gpu_compute = g.gpu_compute_processes
    original_sleep = g.time.sleep
    try:
        calls = {"names": 0, "listener": 0, "gpu": 0, "sleep": []}
        g.process_executable_names = lambda: calls.__setitem__("names", calls["names"] + 1) or set()
        g.listener_busy = lambda host, port: calls.__setitem__("listener", calls["listener"] + 1) or False
        g.gpu_compute_processes = lambda: calls.__setitem__("gpu", calls["gpu"] + 1) or []
        g.time.sleep = lambda seconds: calls["sleep"].append(seconds)
        with tempfile.TemporaryDirectory(prefix="relaylm-logical-prefix-guard-selftest-") as td:
            root = Path(td)
            obs = g.require_external_quiescence(root)
            saved = json.loads((root / "external-quiescence.json").read_text(encoding="utf-8"))
        results.append({
            "name": "two_idle_observations_five_seconds_apart",
            "ok": len(obs) == 2 and len(saved) == 2 and calls == {"names": 2, "listener": 2, "gpu": 2, "sleep": [5]}
                and all(x.get("gpu_compute_processes") == [] for x in obs),
        })

        g.process_executable_names = lambda: {"llama-server"}
        g.listener_busy = lambda host, port: False
        g.gpu_compute_processes = lambda: []
        g.time.sleep = lambda seconds: None
        with tempfile.TemporaryDirectory(prefix="relaylm-logical-prefix-guard-busy-") as td:
            busy_failed = expect_runtime_error(lambda: g.require_external_quiescence(Path(td)))
        results.append({"name": "busy_process_fails_closed", "ok": busy_failed})

        g.process_executable_names = lambda: set()
        g.listener_busy = lambda host, port: False
        g.gpu_compute_processes = lambda: [{"pid": 123, "process_name": "python3"}]
        with tempfile.TemporaryDirectory(prefix="relaylm-logical-prefix-guard-gpu-busy-") as td:
            gpu_busy_failed = expect_runtime_error(lambda: g.require_external_quiescence(Path(td)))
        results.append({"name": "gpu_compute_process_fails_closed", "ok": gpu_busy_failed})
    finally:
        g.process_executable_names = original_names
        g.listener_busy = original_listener
        g.gpu_compute_processes = original_gpu_compute
        g.time.sleep = original_sleep

    errors = [r["name"] for r in results if not r["ok"]]
    out = {
        "status": "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS" if not errors else "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_FAIL",
        "results": results,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
