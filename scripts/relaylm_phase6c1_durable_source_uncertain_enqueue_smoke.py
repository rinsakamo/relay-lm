"""Uncertain B2 outcome regression for Phase 6-C1-5."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_slp_durable_runtime_enqueue as durable_runtime
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    apply_relaymem_slp_runtime_enqueue,
    build_relaymem_slp_runtime_enqueue_failure_result,
)

from _relaylm_phase6c1_durable_source_support import (
    artifact_path,
    assert_content_free,
    finalized,
)
from relaylm_phase6c1_primary_worker_test_support import require


def uncertain_enqueue_retains_source() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as protected_dir:
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        source_result = finalized()
        preparation = apply_relaymem_slp_runtime_enqueue(
            source_result,
            registry=registry,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(preparation.status == "dry_run_ready", preparation.to_log_dict())
        simulated_failure = build_relaymem_slp_runtime_enqueue_failure_result(
            "simulated_uncertain_enqueue_failure"
        )
        with patch.object(
            durable_runtime,
            "apply_relaymem_slp_runtime_enqueue",
            side_effect=(preparation, simulated_failure),
        ):
            result = durable_runtime.apply_relaymem_slp_durable_runtime_enqueue(
                source_result,
                registry=registry,
                source_store=RelayMEMSLPDurableProtectedSourceStore(
                    str(protected_root)
                ),
                queue_root=str(queue_root),
                enabled=True,
                dry_run_only=False,
                apply_enabled=True,
            )
        require(result.status == "enqueue_failed", result.to_log_dict())
        require(result.source_persisted_before_enqueue, result.to_log_dict())
        require(artifact_path(protected_root).is_file(), result.to_log_dict())
        require(result.orphan_cleanup_result is not None, result.to_log_dict())
        require(
            result.orphan_cleanup_result.status == "cleanup_required",
            result.to_log_dict(),
        )
        require(
            "protected_source_orphan_reconciliation_required"
            in result.blocked_reasons,
            result.to_log_dict(),
        )
        require(
            result.to_log_dict()["orphan_reconciliation_required"] is True,
            result.to_log_dict(),
        )
        require(not list(queue_root.glob("slp-dispatch-v0-*.json")), queue_root)
        assert_content_free(result)
        assert_content_free(result.to_log_dict())


def main() -> int:
    uncertain_enqueue_retains_source()
    print("Phase 6-C1-5 uncertain enqueue smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
