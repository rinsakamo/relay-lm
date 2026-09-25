#!/usr/bin/env python3
import fcntl
import importlib.util
import json
import os
import sys
from pathlib import Path
import tempfile
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
    if target.QUEUE_LEASE_FD_ENV != "RELAYLM_PHYSICAL_QUEUE_LEASE_FD":
        raise RuntimeError("physical target queue lease environment drift")
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

    original_lock_path = target.CANONICAL_LOCK_PATH
    try:
        with tempfile.TemporaryDirectory(prefix="relaylm-target-lease-selftest-") as td:
            target.CANONICAL_LOCK_PATH = Path(td) / "queue.lock"
            held = target.CANONICAL_LOCK_PATH.open("a+", encoding="utf-8")
            try:
                fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                detected = target._require_inherited_queue_lease_fd()
                if detected != held.fileno():
                    raise RuntimeError("target did not identify the inherited held queue fd")
                fcntl.flock(held.fileno(), fcntl.LOCK_UN)
                try:
                    target._require_inherited_queue_lease_fd()
                except target.ProjectionProvenanceTargetError:
                    pass
                else:
                    raise RuntimeError("target accepted an unlocked inherited queue fd")
            finally:
                held.close()
    finally:
        target.CANONICAL_LOCK_PATH = original_lock_path
    checks.append("real_flock_lease_validation")

    calls = []
    original_load = target._load_target
    original_lease = target._require_inherited_queue_lease_fd
    try:
        def fake_main():
            calls.append((
                tuple(sys.argv[1:]),
                os.environ.get(target.QUEUE_LEASE_FD_ENV),
            ))
            return 7
        target._load_target = lambda: SimpleNamespace(main=fake_main)
        target._require_inherited_queue_lease_fd = lambda: 9
        rc = target.main(["--descriptor", "example.json"])
    finally:
        target._load_target = original_load
        target._require_inherited_queue_lease_fd = original_lease
    if rc != 7 or calls != [(("--descriptor", "example.json"), "9")]:
        raise RuntimeError("physical target did not delegate exactly once under queue lease")
    if target.QUEUE_LEASE_FD_ENV in os.environ:
        raise RuntimeError("physical target leaked queue lease environment")
    checks.append("exactly_once_delegation")

    source = TARGET.read_text(encoding="utf-8")
    for marker in (
        "_require_inherited_queue_lease_fd",
        "fcntl.LOCK_EX | fcntl.LOCK_NB",
        "inherited canonical queue fd exists but no queue flock is held",
        "RELAYLM_PHYSICAL_QUEUE_LEASE_FD",
    ):
        if marker not in source:
            raise RuntimeError(f"queue lease marker missing: {marker}")
    checks.append("canonical_queue_lease_required")

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
