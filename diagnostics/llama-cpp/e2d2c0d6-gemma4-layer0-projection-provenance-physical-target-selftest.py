#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "tools" / "diagnostic_projection_provenance_target.py"


def load_target():
    spec = importlib.util.spec_from_file_location(
        "diagnostic_projection_provenance_target", TARGET
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load diagnostic physical target adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    target = load_target()
    checks = []

    if target.TARGET_NAME != "diagnostic:3006-projection-provenance":
        raise RuntimeError("physical target name drift")
    if target.EXPECTED_ATTEMPT_ID != "layer0-projection-provenance-20260925-a":
        raise RuntimeError("physical target measured attempt drift")
    if (
        target.EXPECTED_DESCRIPTOR_GENERATION
        != "provenance-measured-descriptor-20260925-b"
    ):
        raise RuntimeError("physical target descriptor generation drift")
    checks.append("identity")

    loaded = target._load_target()
    if loaded.ATTEMPT_ID != target.EXPECTED_ATTEMPT_ID:
        raise RuntimeError("loaded measured wrapper attempt mismatch")
    if (
        loaded.EXPECTED_DESCRIPTOR_GENERATION
        != target.EXPECTED_DESCRIPTOR_GENERATION
    ):
        raise RuntimeError("loaded measured wrapper descriptor generation mismatch")
    checks.append("real_wrapper_import")

    calls = []
    original = target._load_target
    try:
        def fake_main():
            calls.append(tuple(sys.argv[1:]))
            return 7
        target._load_target = lambda: SimpleNamespace(main=fake_main)
        rc = target.main(["--descriptor", "example.json"])
    finally:
        target._load_target = original
    if rc != 7 or calls != [("--descriptor", "example.json")]:
        raise RuntimeError("physical target did not delegate exactly once")
    checks.append("exactly_once_delegation")

    print(json.dumps({
        "status": "PROJECTION_PROVENANCE_PHYSICAL_TARGET_SELFTEST_PASS",
        "checks": checks,
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
