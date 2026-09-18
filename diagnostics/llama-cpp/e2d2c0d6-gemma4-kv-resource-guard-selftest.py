#!/usr/bin/env python3
import errno
import importlib.util
import json
from pathlib import Path
import sys


def load_wrapper():
    here = Path(__file__).resolve().parent
    wrapper_path = here / "e2d2c0d6-gemma4-kv-prefix-provenance-resume-run.py"
    spec = importlib.util.spec_from_file_location("kv_prefix_provenance_resume_wrapper", wrapper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load KV provenance resume wrapper")
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
    wrapper = load_wrapper()
    results = [
        {
            "name": "connect_success_is_busy",
            "ok": wrapper.interpret_connect_ex(0) is True,
        },
        {
            "name": "connection_refused_is_idle",
            "ok": wrapper.interpret_connect_ex(errno.ECONNREFUSED) is False,
        },
        {
            "name": "eperm_is_inconclusive",
            "ok": expect_runtime_error(lambda: wrapper.interpret_connect_ex(errno.EPERM)),
        },
        {
            "name": "eacces_is_inconclusive",
            "ok": expect_runtime_error(lambda: wrapper.interpret_connect_ex(errno.EACCES)),
        },
        {
            "name": "timeout_is_inconclusive",
            "ok": expect_runtime_error(lambda: wrapper.interpret_connect_ex(errno.ETIMEDOUT)),
        },
    ]
    errors = [r["name"] for r in results if not r["ok"]]
    out = {
        "status": (
            "RESOURCE_GUARD_SELFTEST_PASS"
            if not errors
            else "RESOURCE_GUARD_SELFTEST_FAIL"
        ),
        "results": results,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
