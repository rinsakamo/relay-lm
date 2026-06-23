"""Regression smoke for the Phase 6-C1-2 compose checkpoint seam."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
from relaylm.relaymem_primary_pipeline import (
    RelayMEMPrimaryPipelineCheckpointResult,
    execute_relaymem_primary_pipeline,
)
from relaylm.relaymem_slp_primary_worker_source import validate_relaymem_slp_primary_worker_source

from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    pipeline_request_from_worker,
    prepare_store,
    require,
)


def build_compose(store_root: Path, *, run_id: str):
    queue_root = store_root / "queue-unused"
    queue_root.mkdir()
    request, scope = build_request(
        queue_root, store_root, record=claimed_record(run_id=run_id)
    )
    return pipeline_request_from_worker(request), request, scope


def normal_order() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        prepare_store(root)
        compose, _, _ = build_compose(root, run_id="run-checkpoint-order")
        seen: list[str] = []

        def checkpoint(name):
            seen.append(name)
            return RelayMEMPrimaryPipelineCheckpointResult(True, ())

        result = execute_relaymem_primary_pipeline(compose, checkpoint=checkpoint)
        require(result.status == "recovery_not_required", result.to_log_dict())
        require(seen == [
            "before_source_consumption",
            "before_m3e_page_writer",
            "before_m3g_reconciliation_apply",
        ], seen)


def deny_source() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        prepare_store(root)
        compose, request, scope = build_compose(root, run_id="run-checkpoint-source")
        with patch.object(pipeline, "build_relaymem_primary_formation_dry_run") as m3a:
            result = execute_relaymem_primary_pipeline(
                compose,
                checkpoint=lambda name: RelayMEMPrimaryPipelineCheckpointResult(
                    False, ("test_source_checkpoint_denied",)
                ),
            )
        require(result.status == "invalid_input" and not m3a.called, result.to_log_dict())
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source,
            claimed_record=request.claimed_record,
            request_scope=scope,
        )
        require(exact is request.worker_source and not reasons, reasons)


def deny_m3e() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        prepare_store(root)
        compose, request, scope = build_compose(root, run_id="run-checkpoint-m3e")

        def checkpoint(name):
            return RelayMEMPrimaryPipelineCheckpointResult(
                name != "before_m3e_page_writer",
                () if name != "before_m3e_page_writer" else ("test_m3e_checkpoint_denied",),
            )

        with patch.object(pipeline, "apply_relaymem_primary_page_write") as m3e:
            result = execute_relaymem_primary_pipeline(compose, checkpoint=checkpoint)
        require(result.status == "blocked" and not m3e.called, result.to_log_dict())
        require(not list((root / "memory/mem/primary/projects").glob("*.md")), "M3e side effect")
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source,
            claimed_record=request.claimed_record,
            request_scope=scope,
        )
        require(exact is None and reasons == ("worker_source_already_consumed",), reasons)


def deny_m3g() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        prepare_store(root)
        compose, _, _ = build_compose(root, run_id="run-checkpoint-m3g")

        def checkpoint(name):
            return RelayMEMPrimaryPipelineCheckpointResult(
                name != "before_m3g_reconciliation_apply",
                () if name != "before_m3g_reconciliation_apply" else ("test_m3g_checkpoint_denied",),
            )

        with patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation") as m3g:
            result = execute_relaymem_primary_pipeline(compose, checkpoint=checkpoint)
        require(result.status == "blocked" and not m3g.called, result.to_log_dict())
        require(len(list((root / "memory/mem/primary/projects").glob("*.md"))) == 1, "M3e missing")
        require((root / "memory/mem/index.md").read_text() == "# Index\n", "index changed")
        require((root / "memory/mem/log.md").read_text() == "# Log\n", "log changed")


def main() -> int:
    normal_order()
    deny_source()
    deny_m3e()
    deny_m3g()
    print("RelayMEM Primary pipeline checkpoint seam smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
