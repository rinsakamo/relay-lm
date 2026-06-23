"""End-to-end content-free projection and output smoke for Phase 6-C1-4."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType

from relaylm.relaymem_slp_primary_worker import (
    build_relaymem_slp_primary_worker_node_result,
    execute_relaymem_slp_primary_worker,
    project_relaymem_slp_primary_worker,
)

from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    prepare_store,
    read_record,
    require,
    write_record,
)

CANARY_MESSAGE = "CANARY_G_WORKER_MESSAGE_DO_NOT_LEAK"
CANARY_SUMMARY = "CANARY_G_WORKER_SUMMARY_DO_NOT_LEAK"
CANARY_NAMESPACE = "CANARY_G_NAMESPACE_DO_NOT_LEAK"
CANARY_DISPATCH = "CANARY_G_DISPATCH_KEY_DO_NOT_LEAK"
CANARY_MEMORY = "CANARY_G_MEMORY_KEY_DO_NOT_LEAK"
CANARY_LEASE = "CANARY_G_LEASE_TOKEN_DO_NOT_LEAK"
CANARY_QUEUE = "CANARY_G_QUEUE_PATH_DO_NOT_LEAK"
CANARY_STORE = "CANARY_G_STORE_PATH_DO_NOT_LEAK"
CANARIES = (
    CANARY_MESSAGE,
    CANARY_SUMMARY,
    CANARY_NAMESPACE,
    CANARY_DISPATCH,
    CANARY_MEMORY,
    CANARY_LEASE,
    CANARY_QUEUE,
    CANARY_STORE,
)


def _require_content_free(value: object, forbidden: tuple[str, ...]) -> None:
    text = repr(value)
    require(all(token not in text for token in forbidden if token), "content leakage")


def public_surfaces_and_process_output_are_content_free() -> None:
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        TemporaryDirectory(prefix=CANARY_QUEUE) as queue_dir,
        TemporaryDirectory(prefix=CANARY_STORE) as store_dir,
    ):
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(namespace=CANARY_NAMESPACE)
        record["lease_token"] = CANARY_LEASE
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        object.__setattr__(
            request.worker_source.governed_messages[1],
            "content",
            CANARY_MESSAGE,
        )
        experience = dict(request.worker_source.governed_experience_artifact)
        experience.update(
            title=CANARY_SUMMARY,
            summary_text=CANARY_SUMMARY,
            summary_chars=len(CANARY_SUMMARY),
        )
        object.__setattr__(
            request.worker_source,
            "governed_experience_artifact",
            MappingProxyType(experience),
        )

        with redirect_stdout(stdout), redirect_stderr(stderr), fixed_queue_time():
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "terminal_succeeded", "worker success expected")
        projection = project_relaymem_slp_primary_worker(result).to_log_dict()
        node = build_relaymem_slp_primary_worker_node_result(result).to_log_dict()
        require(result.queue_transition_result is not None, "queue result missing")
        queue_projection = result.queue_transition_result.to_log_dict()
        page = next((store_root / "memory/mem/primary/projects").glob("*.md"))
        private_values = (
            *CANARIES,
            str(queue_root),
            str(store_root),
            str(queue_path),
            str(record["job_id"]),
            str(record["dispatch_idempotency_key"]),
            str(record["source_lineage_fingerprint"]),
            str(page.stem),
            str(record["claim_owner"]),
            str(record["record_revision"]),
            str(record["claim_generation"]),
        )
        workflow_projection = json.dumps(
            {
                "worker": projection,
                "node": node,
                "queue": queue_projection,
            },
            sort_keys=True,
        )
        for value in (
            projection,
            node,
            queue_projection,
            workflow_projection,
            repr(request),
            repr(result),
            stdout.getvalue(),
            stderr.getvalue(),
        ):
            _require_content_free(value, private_values)
        require(stdout.getvalue() == "", "unexpected stdout")
        require(stderr.getvalue() == "", "unexpected stderr")
        require(projection["private_pipeline_result_included"] is False, "pipeline leak flag")
        require(projection["private_outcome_result_included"] is False, "outcome leak flag")
        require(projection["private_queue_result_included"] is False, "queue leak flag")
        require(node["artifacts"][0]["private_result_omitted"] is True, "node privacy")


def same_dispatch_different_source_fails_closed_without_memory_mutation() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-c1-4-source-correlation")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        object.__setattr__(request.worker_source, "run_id", "different-source-c1-4")

        with fixed_queue_time():
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "terminal_failed", "correlation must fail terminally")
        require(result.outcome_result is not None, "correlation outcome missing")
        require(
            result.outcome_result.failure_class == "source_correlation_invalid",
            "correlation failure class",
        )
        durable = read_record(queue_path)
        require(durable["state"] == "failed", "correlation queue state")
        require(
            durable["failure_class"] == "source_correlation_invalid",
            "correlation durable class",
        )
        require(durable["state"] != "dead_letter", "dead-letter introduced")
        require(
            not list((store_root / "memory/mem/primary/projects").glob("*.md")),
            "correlation wrote page",
        )
        require(
            (store_root / "memory/mem/index.md").read_text(encoding="utf-8")
            == "# Index\n",
            "correlation wrote index",
        )
        require(
            (store_root / "memory/mem/log.md").read_text(encoding="utf-8")
            == "# Log\n",
            "correlation wrote log",
        )
        projection = project_relaymem_slp_primary_worker(result).to_log_dict()
        _require_content_free(
            projection,
            (
                "different-source-c1-4",
                str(record["job_id"]),
                str(record["dispatch_idempotency_key"]),
                str(queue_root),
                str(store_root),
            ),
        )


def main() -> int:
    public_surfaces_and_process_output_are_content_free()
    same_dispatch_different_source_fails_closed_without_memory_mutation()
    print("Phase 6-C1 integrated worker content leakage smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
