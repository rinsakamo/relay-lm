"""Security and fail-closed smoke for Phase 6-C2 one queued-job integration."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_slp_one_queued_job_runner as runner
from relaylm._relaymem_slp_protected_source_artifact import canonical_json_bytes
from relaylm.relaymem_slp_one_queued_job_runner import (
    build_relaymem_slp_one_queued_job_runner_node_result,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_adapter import (
    RelayMEMSLPPreparedWorkerSourceResult,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_queue_record import record_filename

from _relaylm_phase6c1_durable_source_support import (
    PRIVATE_TOKENS,
    apply_durable,
    artifact_path,
)
from relaylm_phase6c1_primary_worker_test_support import (
    prepare_store,
    read_record,
    require,
)
from relaylm_phase6c2_one_queued_job_runner_smoke import request, queued_from


class RequestLookalike(dict[str, object]):
    pass


def assert_content_free(value: object) -> None:
    text = repr(value)
    for token in PRIVATE_TOKENS:
        require(token not in text, ("protected leak", token))


def invalid_inputs() -> None:
    invalid = execute_one_queued_relaymem_slp_primary_job(RequestLookalike())
    require(invalid.status == "invalid_input", invalid.to_log_dict())
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        base = request(
            queue_root,
            protected_root,
            memory_root,
            queued,
            RelayMEMSLPPrimaryWorkerSourceRegistry(),
            dry_run_only=True,
        )
        cases = (
            replace(base, enabled=1),
            replace(base, queue_root="relative/queue"),
            replace(base, dry_run_only=False, apply_enabled=False),
            replace(base, queued_record={**queued, "unexpected": True}),
        )
        for case in cases:
            result = execute_one_queued_relaymem_slp_primary_job(case)
            require(result.status == "invalid_input", result.to_log_dict())
            require(not result.claim_performed, result.to_log_dict())


def run_corrupt_case(kind: str) -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
        TemporaryDirectory() as outside_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        outside_root = Path(outside_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        source_path = artifact_path(protected_root)
        if kind == "missing":
            source_path.unlink()
        elif kind == "malformed_json":
            source_path.write_bytes(b"{")
        elif kind in {"wrong_schema", "identity_mismatch", "digest_mismatch", "source_schema"}:
            artifact = json.loads(source_path.read_text(encoding="utf-8"))
            if kind == "wrong_schema":
                artifact["schema_version"] = "relaymem.slp_protected_source_artifact.v999"
            elif kind == "identity_mismatch":
                artifact["job_id"] = "slp-job-v0:" + "0" * 64
            elif kind == "digest_mismatch":
                artifact["source_integrity_digest"] = "0" * 64
            else:
                artifact["source_schema_version"] = "relaymem.slp_primary_worker_source.v999"
            source_path.write_bytes(canonical_json_bytes(artifact))
        elif kind == "symlink":
            target = outside_root / "outside.json"
            target.write_text("{}", encoding="utf-8")
            source_path.unlink()
            source_path.symlink_to(target)
        else:
            raise AssertionError(kind)

        worker_calls = 0

        def forbidden_worker(_: object):
            nonlocal worker_calls
            worker_calls += 1
            raise AssertionError("worker must not be invoked")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(runner, "execute_relaymem_slp_primary_worker", forbidden_worker),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = execute_one_queued_relaymem_slp_primary_job(
                request(
                    queue_root,
                    protected_root,
                    memory_root,
                    queued,
                    RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    owner=f"worker-corrupt-{kind}",
                )
            )
        expected = "source_unavailable" if kind == "missing" else "source_blocked"
        require(result.status == expected, (kind, result.to_log_dict()))
        require(result.claim_performed, (kind, result.to_log_dict()))
        require(not result.source_prepared, (kind, result.to_log_dict()))
        require(not result.worker_invoked and worker_calls == 0, (kind, result.to_log_dict()))
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        require(read_record(queue_path)["state"] == "claimed", (kind, "claim not retained"))
        assert_content_free(result)
        assert_content_free(result.to_log_dict())
        assert_content_free(
            build_relaymem_slp_one_queued_job_runner_node_result(result).to_log_dict()
        )
        combined = stdout.getvalue() + stderr.getvalue()
        for token in PRIVATE_TOKENS:
            require(token not in combined, (kind, "stdio leak", token))


def source_store_retryable() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        retryable = RelayMEMSLPPreparedWorkerSourceResult(
            status="retryable",
            retained=True,
            source_available=True,
            restart_rehydrated=False,
            blocked_reasons=("protected_source_store_lock_unavailable",),
        )
        worker_calls = 0

        def forbidden_worker(_: object):
            nonlocal worker_calls
            worker_calls += 1
            raise AssertionError("worker must not run during source-store contention")

        with (
            patch.object(
                runner,
                "prepare_relaymem_slp_primary_worker_source_for_claim",
                return_value=retryable,
            ),
            patch.object(runner, "execute_relaymem_slp_primary_worker", forbidden_worker),
        ):
            result = execute_one_queued_relaymem_slp_primary_job(
                request(
                    queue_root,
                    protected_root,
                    memory_root,
                    queued,
                    RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    owner="worker-source-lock-c2",
                )
            )
        require(result.status == "source_retryable", result.to_log_dict())
        require(result.retryable and result.claim_performed, result.to_log_dict())
        require(not result.source_prepared and not result.worker_invoked, result.to_log_dict())
        require(worker_calls == 0, worker_calls)
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        require(read_record(queue_path)["state"] == "claimed", "retryable source rewound claim")
        require(artifact_path(protected_root).exists(), "retryable source deleted artifact")
        assert_content_free(result.to_log_dict())


def lost_claim_before_rehydrate() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        worker_calls = 0

        def forbidden_worker(_: object):
            nonlocal worker_calls
            worker_calls += 1
            raise AssertionError("worker must not run after claim loss")

        with (
            patch.object(
                runner,
                "_check_active_claim",
                return_value=(False, None, ("lease_token_mismatch",)),
            ),
            patch.object(runner, "execute_relaymem_slp_primary_worker", forbidden_worker),
        ):
            result = execute_one_queued_relaymem_slp_primary_job(
                request(
                    queue_root,
                    protected_root,
                    memory_root,
                    queued,
                    RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    owner="worker-lost-c2",
                )
            )
        require(result.status == "claim_lost_before_rehydrate", result.to_log_dict())
        require(worker_calls == 0 and not result.worker_invoked, result.to_log_dict())
        require(artifact_path(protected_root).exists(), "claim loss deleted source")


def main() -> int:
    invalid_inputs()
    for kind in (
        "missing",
        "malformed_json",
        "wrong_schema",
        "identity_mismatch",
        "digest_mismatch",
        "source_schema",
        "symlink",
    ):
        run_corrupt_case(kind)
    source_store_retryable()
    lost_claim_before_rehydrate()
    print("Phase 6-C2 one queued-job security smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
