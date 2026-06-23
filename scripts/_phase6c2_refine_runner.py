from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "relaylm/relaymem_slp_one_queued_job_runner.py"
SECURITY = ROOT / "scripts/relaylm_phase6c2_one_queued_job_runner_security_smoke.py"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label}: replacement anchor missing")
    return text.replace(old, new, 1)


def refine_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    "blocked",\n    "dry_run_ready",\n    "claim_not_applied",\n    "claimed_record_invalid",\n',
        '    "dry_run_ready",\n    "claim_not_applied",\n',
        label="unused statuses",
    )
    text = replace_once(
        text,
        '    if not exact.dry_run_only and not exact.apply_enabled:\n'
        '        return _result("blocked", exact, reasons=("apply_gate_incomplete",))\n\n',
        "",
        label="unreachable gate branch",
    )
    old = '''    try:\n        active, _, active_reasons = _check_active_claim(\n            claimed,\n            queue_root=exact.queue_root,\n            lease_duration_seconds=exact.lease_duration_seconds,\n            renew=False,\n        )\n    except Exception:\n        active = False\n        active_reasons = ("one_queued_job_claim_revalidation_failed",)\n    if not active:\n        return _result(\n            "claim_lost_before_rehydrate",\n            exact,\n            claim_attempted=True,\n            claim_performed=True,\n            claim_result=claim,\n            claim_status=claim.status,\n            reasons=active_reasons or ("one_queued_job_claim_not_current",),\n        )\n\n'''
    new = '''    try:\n        active, checked_claim, active_reasons = _check_active_claim(\n            claimed,\n            queue_root=exact.queue_root,\n            lease_duration_seconds=exact.lease_duration_seconds,\n            renew=False,\n        )\n    except Exception:\n        active = False\n        checked_claim = None\n        active_reasons = ("one_queued_job_claim_revalidation_failed",)\n    checked_record = (\n        checked_claim.durable_record if checked_claim is not None else None\n    )\n    if not active or not _exact_claimed_record(checked_record):\n        reasons = active_reasons or (\n            "one_queued_job_checked_record_invalid"\n            if active\n            else "one_queued_job_claim_not_current"\n        )\n        return _result(\n            "claim_lost_before_rehydrate",\n            exact,\n            claim_attempted=True,\n            claim_performed=True,\n            claim_result=claim,\n            claim_status=claim.status,\n            reasons=reasons,\n        )\n    assert type(checked_record) is dict\n    claimed = dict(checked_record)\n\n'''
    text = replace_once(text, old, new, label="canonical claim reread")
    RUNNER.write_text(text, encoding="utf-8")


def refine_security() -> None:
    text = SECURITY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'from relaylm.relaymem_slp_primary_worker_source_registry import (\n'
        '    RelayMEMSLPPrimaryWorkerSourceRegistry,\n'
        ')\n',
        'from relaylm.relaymem_slp_primary_worker_source_adapter import (\n'
        '    RelayMEMSLPPreparedWorkerSourceResult,\n'
        ')\n'
        'from relaylm.relaymem_slp_primary_worker_source_registry import (\n'
        '    RelayMEMSLPPrimaryWorkerSourceRegistry,\n'
        ')\n',
        label="prepared result import",
    )
    anchor = '''\ndef lost_claim_before_rehydrate() -> None:\n'''
    addition = '''\ndef source_store_retryable() -> None:\n    with (\n        TemporaryDirectory() as queue_dir,\n        TemporaryDirectory() as protected_dir,\n        TemporaryDirectory() as memory_dir,\n    ):\n        queue_root = Path(queue_dir)\n        protected_root = Path(protected_dir)\n        memory_root = Path(memory_dir)\n        prepare_store(memory_root)\n        applied = apply_durable(\n            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()\n        )\n        queued = queued_from(applied)\n        retryable = RelayMEMSLPPreparedWorkerSourceResult(\n            status="retryable",\n            retained=True,\n            source_available=True,\n            restart_rehydrated=False,\n            blocked_reasons=("protected_source_store_lock_unavailable",),\n        )\n        worker_calls = 0\n\n        def forbidden_worker(_: object):\n            nonlocal worker_calls\n            worker_calls += 1\n            raise AssertionError("worker must not run during source-store contention")\n\n        with (\n            patch.object(\n                runner,\n                "prepare_relaymem_slp_primary_worker_source_for_claim",\n                return_value=retryable,\n            ),\n            patch.object(runner, "execute_relaymem_slp_primary_worker", forbidden_worker),\n        ):\n            result = execute_one_queued_relaymem_slp_primary_job(\n                request(\n                    queue_root,\n                    protected_root,\n                    memory_root,\n                    queued,\n                    RelayMEMSLPPrimaryWorkerSourceRegistry(),\n                    owner="worker-source-lock-c2",\n                )\n            )\n        require(result.status == "source_retryable", result.to_log_dict())\n        require(result.retryable and result.claim_performed, result.to_log_dict())\n        require(not result.source_prepared and not result.worker_invoked, result.to_log_dict())\n        require(worker_calls == 0, worker_calls)\n        queue_path = queue_root / record_filename(\n            str(queued["dispatch_idempotency_key"])\n        )\n        require(read_record(queue_path)["state"] == "claimed", "retryable source rewound claim")\n        require(artifact_path(protected_root).exists(), "retryable source deleted artifact")\n        assert_content_free(result.to_log_dict())\n\n\ndef lost_claim_before_rehydrate() -> None:\n'''
    text = replace_once(text, anchor, addition, label="source retryable test")
    text = replace_once(
        text,
        '    lost_claim_before_rehydrate()\n',
        '    source_store_retryable()\n    lost_claim_before_rehydrate()\n',
        label="source retryable invocation",
    )
    SECURITY.write_text(text, encoding="utf-8")


def main() -> None:
    refine_runner()
    refine_security()
    print("Phase 6-C2 runner canonical reread refinement applied.")


if __name__ == "__main__":
    main()
