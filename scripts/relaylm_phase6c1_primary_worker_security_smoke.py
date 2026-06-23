"""Strict validation and leakage smoke for the Phase 6-C1-2 worker."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
import relaylm.relaymem_slp_primary_worker as worker
from relaylm.relaymem_primary_pipeline import (
    RelayMEMPrimaryPipelineCheckpointResult,
    execute_relaymem_primary_pipeline,
)
from relaylm.relaymem_slp_primary_worker import (
    build_relaymem_slp_primary_worker_node_result,
    execute_relaymem_slp_primary_worker,
    project_relaymem_slp_primary_worker,
)
from relaylm.relaymem_slp_primary_worker_source import (
    validate_relaymem_slp_primary_worker_source,
)

from relaylm_phase6c1_primary_worker_test_support import (
    assert_no_canary,
    build_request,
    claimed_record,
    fixed_queue_time,
    pipeline_request_from_worker,
    prepare_store,
    read_record,
    require,
    write_record,
)

CANARY_RAW = "CANARY_WORKER_RAW_MESSAGE_DO_NOT_LEAK"
CANARY_SUMMARY = "CANARY_WORKER_SUMMARY_DO_NOT_LEAK"
CANARY_NAMESPACE = "CANARY_WORKER_NAMESPACE_DO_NOT_LEAK"
CANARY_DISPATCH = "CANARY_WORKER_DISPATCH_KEY_DO_NOT_LEAK"
CANARY_MEMORY = "CANARY_WORKER_MEMORY_KEY_DO_NOT_LEAK"
CANARY_LEASE = "CANARY_WORKER_LEASE_TOKEN_DO_NOT_LEAK"
CANARY_QUEUE = "CANARY_WORKER_QUEUE_PATH_DO_NOT_LEAK"
CANARY_STORE = "CANARY_WORKER_STORE_PATH_DO_NOT_LEAK"
CANARIES = (
    CANARY_RAW, CANARY_SUMMARY, CANARY_NAMESPACE, CANARY_DISPATCH,
    CANARY_MEMORY, CANARY_LEASE, CANARY_QUEUE, CANARY_STORE,
)


def safe(value: object) -> None:
    text = repr(value)
    for canary in CANARIES:
        require(canary not in text, ("canary leak", canary))


def projection_and_output_leakage() -> None:
    out, err = io.StringIO(), io.StringIO()
    with (
        TemporaryDirectory(prefix=CANARY_QUEUE) as queue_dir,
        TemporaryDirectory(prefix=CANARY_STORE) as store_dir,
    ):
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(namespace=CANARY_NAMESPACE)
        record["lease_token"] = CANARY_LEASE
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        object.__setattr__(request.worker_source.governed_messages[1], "content", CANARY_RAW)
        with redirect_stdout(out), redirect_stderr(err), fixed_queue_time():
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "terminal_succeeded", result.to_log_dict())
        projection = project_relaymem_slp_primary_worker(result).to_log_dict()
        node = build_relaymem_slp_primary_worker_node_result(result).to_log_dict()
        queue_projection = result.queue_transition_result.to_log_dict()
        workflow_output = json.dumps(
            {"worker": projection, "node": node, "queue": queue_projection},
            sort_keys=True,
        )
        for value in (projection, node, queue_projection, workflow_output, repr(request), repr(result)):
            safe(value)
            assert_no_canary(value, queue_root, store_root, path, record["job_id"], record["dispatch_idempotency_key"])
        safe(out.getvalue())
        safe(err.getvalue())
        require(out.getvalue() == "" and err.getvalue() == "", "unexpected worker output")
        require(projection["private_pipeline_result_included"] is False, projection)
        require(projection["private_outcome_result_included"] is False, projection)
        require(projection["private_queue_result_included"] is False, projection)
        require(node["artifacts"][0]["private_result_omitted"] is True, node)
        require(read_record(path)["state"] == "succeeded", "queue state")


def checkpoint_validation_and_exception_sanitization() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-checkpoint-security")
        write_record(queue_root, record)
        prepare_store(store_root)
        request, scope = build_request(queue_root, store_root, record=record)
        compose_request = pipeline_request_from_worker(request)
        for callback in (
            lambda name: True,
            lambda name: {"allowed": True},
            lambda name: RelayMEMPrimaryPipelineCheckpointResult(1, ()),
            lambda name: RelayMEMPrimaryPipelineCheckpointResult(True, ("unexpected_reason",)),
        ):
            with patch.object(pipeline, "build_relaymem_primary_formation_dry_run") as m3a:
                result = execute_relaymem_primary_pipeline(compose_request, checkpoint=callback)
            require(result.status == "invalid_input", result.to_log_dict())
            require(not m3a.called, "malformed checkpoint reached M3a")
            exact, reasons = validate_relaymem_slp_primary_worker_source(
                request.worker_source, claimed_record=record, request_scope=scope
            )
            require(exact is request.worker_source and not reasons, reasons)

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-checkpoint-exception")
        write_record(queue_root, record)
        prepare_store(store_root)
        request, scope = build_request(queue_root, store_root, record=record)
        compose_request = pipeline_request_from_worker(request)

        def explode(name):
            raise OSError(CANARY_RAW + CANARY_STORE)

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = execute_relaymem_primary_pipeline(compose_request, checkpoint=explode)
        require(result.status == "invalid_input", result.to_log_dict())
        require(result.reason_ids == ("primary_pipeline_checkpoint_callback_failed",), result.to_log_dict())
        safe(result.to_log_dict())
        safe(out.getvalue())
        safe(err.getvalue())
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source, claimed_record=record, request_scope=scope
        )
        require(exact is request.worker_source and not reasons, reasons)


def worker_exception_sanitization() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-worker-exception")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with (
            fixed_queue_time(),
            patch.object(
                worker,
                "classify_relaymem_slp_primary_worker_outcome",
                side_effect=OSError(CANARY_RAW + CANARY_QUEUE),
            ),
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "pipeline_blocked", result.to_log_dict())
        require(result.reason_ids == ("primary_worker_outcome_classifier_failed",), result.to_log_dict())
        require(read_record(path)["state"] == "claimed", "classifier exception transitioned")
        safe(result.to_log_dict())
        safe(repr(result))


def main() -> int:
    projection_and_output_leakage()
    checkpoint_validation_and_exception_sanitization()
    worker_exception_sanitization()
    print("Phase 6-C1 one-claimed-job worker security smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
