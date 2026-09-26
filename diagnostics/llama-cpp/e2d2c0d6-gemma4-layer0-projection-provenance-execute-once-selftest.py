#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-execute-once.py"

def load_module():
    spec = importlib.util.spec_from_file_location("projection_provenance_wrapper", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load provenance execute-once wrapper")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    m = load_module()
    if m.ATTEMPT_ID != "layer0-projection-provenance-20260925-a":
        raise RuntimeError("execute-once attempt identity drift")
    if m.EXPECTED_DESCRIPTOR_GENERATION != "provenance-measured-descriptor-20260925-b":
        raise RuntimeError("execute-once descriptor generation drift")

    with tempfile.TemporaryDirectory(prefix="relaylm-provenance-wrapper-selftest-") as td:
        root = Path(td)

        absent = root / "absent"
        a = m.reconcile(absent, 9)
        if a["primary_classification"] != "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED":
            raise RuntimeError("absent W record must be unexercised")
        if a["measured_attempt_consumed"] is not False:
            raise RuntimeError("unexercised case incorrectly consumed")
        if a["rerun_authorized"] is not False:
            raise RuntimeError("unexercised wrapper must not self-authorize rerun")

        partial = root / "partial"
        (partial / "server-W").mkdir(parents=True)
        (partial / "server-W" / "W.request.json").write_text("{}\n", encoding="utf-8")
        b = m.reconcile(partial, 8)
        if b["primary_classification"] != "LAYER0_PROJECTION_PROVENANCE_PROBE_EXERCISED_INCOMPLETE":
            raise RuntimeError("W durable record must conservatively consume attempt")
        if b["measured_attempt_consumed"] is not True:
            raise RuntimeError("W durable record did not consume attempt")
        if b["measured_w_submitted"] is not True or b["measured_c_submitted"] is not False:
            raise RuntimeError("partial W/C submission flags incorrect")
        if b["rerun_authorized"] is not False:
            raise RuntimeError("consumed incomplete case incorrectly authorizes rerun")

        partial_c = root / "partial-c"
        (partial_c / "server-W").mkdir(parents=True)
        (partial_c / "server-C").mkdir(parents=True)
        (partial_c / "server-W" / "W.request.json").write_text("{}\n", encoding="utf-8")
        (partial_c / "server-C" / "C.request.json").write_text("{}\n", encoding="utf-8")
        c = m.reconcile(partial_c, 8)
        if c["measured_attempt_consumed"] is not True:
            raise RuntimeError("W/C durable records did not consume attempt")
        if c["measured_w_submitted"] is not True or c["measured_c_submitted"] is not True:
            raise RuntimeError("partial W/C flags incorrect")

        unsealed = root / "unsealed-terminal"
        (unsealed / "server-W").mkdir(parents=True)
        (unsealed / "server-W" / "W.request.json").write_text("{}\n", encoding="utf-8")
        (unsealed / "terminal.json").write_text(
            json.dumps({"primary_classification": "SHOULD_NOT_BE_TRUSTED"}) + "\n",
            encoding="utf-8",
        )
        u = m.reconcile(unsealed, 8)
        if u["primary_classification"] != "LAYER0_PROJECTION_PROVENANCE_PROBE_EXERCISED_INCOMPLETE":
            raise RuntimeError("unsealed terminal was incorrectly accepted as complete")

        complete = root / "complete"
        complete.mkdir()
        terminal = {
            "primary_classification": "K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED",
            "measured_attempt_consumed": True,
        }
        terminal_path = complete / "terminal.json"
        terminal_path.write_text(json.dumps(terminal) + "\n", encoding="utf-8")
        manifest_path = complete / "measured-artifact-manifest.sha256"
        manifest_path.write_text(
            f"{m.sha256(terminal_path)}  terminal.json\n",
            encoding="utf-8",
        )
        terminal_path.chmod(0o444)
        manifest_path.chmod(0o444)
        complete.chmod(0o555)
        try:
            d = m.reconcile(complete, 0)
        finally:
            complete.chmod(0o755)
            terminal_path.chmod(0o644)
            manifest_path.chmod(0o644)
        if d["primary_classification"] != terminal["primary_classification"]:
            raise RuntimeError("complete terminal classification not preserved")
        if d["measured_terminal_present"] is not True:
            raise RuntimeError("complete sealed terminal not detected")
        if d.get("measured_evidence_sealed") is not True:
            raise RuntimeError("complete measured evidence seal not recognized")
        if d["measured_attempt_consumed"] is not True or d["rerun_authorized"] is not False:
            raise RuntimeError("complete measured case has wrong consumption flags")

    source = TARGET.read_text(encoding="utf-8")
    if source.count(
        "subprocess.run(guard_cmd, check=False, pass_fds=(queue_lease_fd,))"
    ) != 1:
        raise RuntimeError("execute-once must invoke guarded measured child exactly once")
    for marker in (
        "canonical physical queue lease fd is required",
        '"--inherited-lock-fd", str(queue_lease_fd)',
        '"--expected-gpu-inventory", str(expected_gpu_path)',
        "validate_descriptor_and_checkout",
        "measured_seal_sha",
        "seal_preflight_root",
        "execute-once-artifact-manifest.sha256",
    ):
        if marker not in source:
            raise RuntimeError(f"execute-once hardening marker missing: {marker}")
    if '"-m", "py_compile"' in source:
        raise RuntimeError("execute-once regressed to checkout-writing py_compile")
    for forbidden in ("while True", "retry", "RETRY", "rerun_authorized\": True"):
        if forbidden in source:
            raise RuntimeError(f"retry/rerun surface present: {forbidden}")

    print(json.dumps({
        "status": "LAYER0_PROJECTION_PROVENANCE_EXECUTE_ONCE_SELFTEST_PASS",
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
