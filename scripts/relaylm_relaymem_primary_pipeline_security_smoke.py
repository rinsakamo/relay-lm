from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_pipeline import (
    REQUEST_SCHEMA,
    STAGES,
    execute_relaymem_primary_pipeline,
    project_relaymem_primary_pipeline,
)

from relaylm_relaymem_primary_pipeline_smoke import (
    CANARY_MEMORY_KEY,
    CANARY_NAMESPACE,
    CANARY_SOURCE,
    CANARY_STORE_PATH,
    CANARY_SUMMARY,
    create_request,
    prepare_store,
    require,
)


def expect_frozen(target: object, field: str, value: object) -> None:
    try:
        setattr(target, field, value)
    except (FrozenInstanceError, AttributeError):
        return
    raise AssertionError("pipeline dataclass must be frozen")


def safe_text(value: object) -> None:
    text = repr(value)
    for token in (
        CANARY_SOURCE,
        CANARY_SUMMARY,
        CANARY_NAMESPACE,
        CANARY_MEMORY_KEY,
        CANARY_STORE_PATH,
        "memory/mem/",
        "slp-dispatch-v0:",
        "slp-job-v0:",
    ):
        require(token not in text, "protected canary leaked")


def main() -> int:
    generic = execute_relaymem_primary_pipeline(
        {
            "schema_version": REQUEST_SCHEMA,
            "enabled": True,
            "dry_run_only": False,
            "apply_enabled": True,
        }
    )
    require(generic.status == "invalid_input", generic.to_log_dict())

    with tempfile.TemporaryDirectory(prefix=CANARY_STORE_PATH) as temporary:
        root = Path(temporary)
        prepare_store(root)

        wrong_schema, _ = create_request(root)
        object.__setattr__(wrong_schema, "schema_version", "relaymem.primary_pipeline_request.v999")
        require(
            execute_relaymem_primary_pipeline(wrong_schema).status == "invalid_input",
            "wrong request schema accepted",
        )

        bool_int, _ = create_request(root)
        object.__setattr__(bool_int, "enabled", 1)
        require(
            execute_relaymem_primary_pipeline(bool_int).status == "invalid_input",
            "bool/int confusion accepted",
        )

        invalid_dry, _ = create_request(root, dry_run_only=True, apply_enabled=False)
        object.__setattr__(invalid_dry, "apply_enabled", True)
        require(
            execute_relaymem_primary_pipeline(invalid_dry).status == "invalid_input",
            "dry-run/apply contradiction accepted",
        )

        incomplete_apply, _ = create_request(root)
        object.__setattr__(incomplete_apply, "apply_enabled", False)
        require(
            execute_relaymem_primary_pipeline(incomplete_apply).status == "invalid_input",
            "incomplete apply gate accepted",
        )

        request, _ = create_request(root)
        from relaylm import relaymem_primary_pipeline as pipeline

        original = pipeline.build_relaymem_primary_formation_dry_run

        def unknown_field(**kwargs):
            result = original(**kwargs)
            result["unexpected_private_extension"] = CANARY_SOURCE
            return result

        with (
            patch.object(pipeline, "build_relaymem_primary_formation_dry_run", side_effect=unknown_field),
            patch.object(pipeline, "build_relaymem_primary_write_preflight_dry_run") as m3b,
        ):
            blocked = execute_relaymem_primary_pipeline(request)
        require(blocked.status == "blocked", blocked.to_log_dict())
        require(not m3b.called, "invalid M3a result reached M3b")
        safe_text(blocked.to_log_dict())
        safe_text(blocked)

        exception_request, _ = create_request(root)
        out = io.StringIO()
        err = io.StringIO()
        with (
            redirect_stdout(out),
            redirect_stderr(err),
            patch.object(
                pipeline,
                "build_relaymem_primary_formation_dry_run",
                side_effect=RuntimeError(CANARY_SOURCE),
            ),
        ):
            failed = execute_relaymem_primary_pipeline(exception_request)
        require(failed.status == "blocked", failed.to_log_dict())
        require(failed.reason_ids == ("m3a_execution_failed",), failed.to_log_dict())
        safe_text(failed.to_log_dict())
        require(CANARY_SOURCE not in out.getvalue(), "stdout leaked exception text")
        require(CANARY_SOURCE not in err.getvalue(), "stderr leaked exception text")

        dry_request, _ = create_request(root, dry_run_only=True, apply_enabled=False)
        dry = execute_relaymem_primary_pipeline(dry_request)
        require(tuple(item.stage for item in dry.stage_results) == STAGES, "stage order drift")
        require(len({item.stage for item in dry.stage_results}) == len(STAGES), "duplicate stage")
        require(
            all(item.status == "not_run" or item.stage in STAGES for item in dry.stage_results),
            "unknown stage",
        )
        expect_frozen(dry, "status", "blocked")
        expect_frozen(dry.stage_results[0], "stage", "m3h_recovery_audit")
        projection = project_relaymem_primary_pipeline(dry)
        expect_frozen(projection, "status", "blocked")
        safe_text(projection.to_log_dict())
        safe_text(dry)
        safe_text(dry.stage_results)

        public = projection.to_log_dict()
        forbidden_keys = {
            "worker_source",
            "claimed_record",
            "store_root",
            "namespace",
            "job_id",
            "run_id",
            "session_id",
            "dispatch_idempotency_key",
            "lineage_fingerprint",
            "idempotency_key",
            "target_relative_path",
            "page_markdown",
            "private_result",
            "exception",
        }
        require(not forbidden_keys.intersection(public), "private public-projection key")
        require(
            public["queue_io_performed"] is False
            and public["queue_transition_performed"] is False
            and public["lease_operation_performed"] is False
            and public["retry_sleep_performed"] is False,
            public,
        )

    print("RelayMEM Primary pipeline compose security smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
