"""Security and fail-closed smoke for O0 local one-job runner."""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import relaylm.local_worker_once as local_worker
from relaylm.local_worker_cli import main as cli_main
from relaylm.local_worker_once import execute_local_worker_once
from relaylm.relaymem_slp_queue_record import (
    FILENAME_PREFIX,
    MAX_RECORD_BYTES,
    canonical_json_bytes,
    record_filename,
)
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

from _relaylm_o0_local_worker_support import (
    assert_content_free,
    build_config,
    build_request,
    prepare_scoped_store,
    produce,
    write_config,
)
from relaylm_phase6c1_primary_worker_test_support import read_record, require

CANARY_EXCEPTION = "CANARY_O0_EXCEPTION_TEXT_DO_NOT_LEAK"
CANARY_PATH = "/CANARY/O0/PATH/DO_NOT/LEAK"


def _canonical_name(digit: str = "0") -> str:
    return f"{FILENAME_PREFIX}{digit * 64}.json"


def _primary_pages(root: Path) -> list[Path]:
    return [
        path
        for path in (root / "characters").rglob("*.md")
        if "/memory/mem/primary/" in path.as_posix()
    ]


def _unsafe_payload(payload: bytes, expected_reason: str) -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        path = queue_root / _canonical_name()
        path.write_bytes(payload)
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            "character/default",
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require(expected_reason in result.reason_ids, result.to_log_dict())
        require(path.read_bytes() == payload, "O0 repaired an unsafe record")
        assert_content_free(result, str(path), CANARY_EXCEPTION)
        assert_content_free(result.to_log_dict(), str(path), CANARY_EXCEPTION)


def gates_and_roots() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        disabled = build_config(
            queue_root,
            protected_root,
            memory_root,
            "character/default",
            mode="disabled",
        )
        result = execute_local_worker_once(build_request(disabled))
        require(result.status == "disabled", result.to_log_dict())
        require(list(queue_root.iterdir()) == [], "disabled mode discovered queue")

        invalid = disabled.model_copy(
            update={
                "relaymem_local_worker_enabled": True,
                "relaymem_local_worker_dry_run_only": True,
                "relaymem_local_worker_apply_enabled": True,
            }
        )
        result = execute_local_worker_once(build_request(invalid))
        require(result.status == "invalid_input", result.to_log_dict())
        require("local_worker_gate_mode_invalid" in result.reason_ids, result.to_log_dict())

        relative = build_config(
            queue_root,
            protected_root,
            memory_root,
            "character/default",
        ).model_copy(update={"relaymem_slp_queue_root": "../queue"})
        result = execute_local_worker_once(build_request(relative))
        require(result.status == "invalid_input", result.to_log_dict())
        require("local_worker_queue_root_invalid" in result.reason_ids, result.to_log_dict())


def unsafe_filesystem() -> None:
    _unsafe_payload(b"\xff\xfe", "queue_record_malformed_utf8")
    _unsafe_payload(b"{not-json", "queue_record_malformed_json")
    _unsafe_payload(b"[]", "queue_record_json_not_object")
    _unsafe_payload(b"x" * (MAX_RECORD_BYTES + 1), "queue_record_size_exceeded")
    _unsafe_payload(
        canonical_json_bytes({"schema_version": "wrong"}),
        "durable_job_shape_mismatch",
    )

    for kind in ("directory", "fifo"):
        with (
            TemporaryDirectory() as queue_dir,
            TemporaryDirectory() as protected_dir,
            TemporaryDirectory() as memory_dir,
        ):
            queue_root = Path(queue_dir)
            path = queue_root / _canonical_name()
            path.mkdir() if kind == "directory" else os.mkfifo(path)
            config = build_config(
                queue_root,
                Path(protected_dir),
                Path(memory_dir),
                "character/default",
            )
            result = execute_local_worker_once(build_request(config))
            require(result.status == "unsafe_queue_state", result.to_log_dict())
            require(
                "queue_record_unexpected_file_type" in result.reason_ids,
                result.to_log_dict(),
            )

    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as target_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        target = Path(target_dir) / "record.json"
        target.write_bytes(b"{}")
        (queue_root / _canonical_name()).symlink_to(target)
        config = build_config(
            queue_root,
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require("queue_record_symlink_blocked" in result.reason_ids, result.to_log_dict())

    with (
        TemporaryDirectory() as parent_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        parent = Path(parent_dir)
        actual = parent / "actual"
        actual.mkdir()
        link = parent / "queue-link"
        link.symlink_to(actual, target_is_directory=True)
        config = build_config(
            link.absolute(),
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require("queue_root_symlink_blocked" in result.reason_ids, result.to_log_dict())


def collision_bound_and_hardlink() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        canonical = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        collision = queue_root / _canonical_name("f")
        collision.write_bytes(canonical.read_bytes())
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require("queue_record_key_path_mismatch" in result.reason_ids, result.to_log_dict())
        require(read_record(canonical)["state"] == "queued", "collision mutated queue")
        require(source_path.exists(), "collision consumed source")

    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        canonical = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        os.link(canonical, queue_root / "extra-hardlink")
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require("queue_record_hardlink_count_invalid" in result.reason_ids, result.to_log_dict())
        require(source_path.exists(), "hardlink consumed source")

    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        for index in range(3):
            (queue_root / f"ignored-{index}").write_text("ignored", encoding="utf-8")
        config = build_config(
            queue_root,
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
            discovery_max_entries=2,
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require("queue_discovery_limit_exceeded" in result.reason_ids, result.to_log_dict())


def claimed_is_no_work() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        claimed = transition_relaymem_slp_queue_state(
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="claim",
                job_id=str(queued["job_id"]),
                dispatch_idempotency_key=str(queued["dispatch_idempotency_key"]),
                expected_record_revision=int(queued["record_revision"]),
                expected_state="queued",
                claim_owner="security-smoke-owner",
                claim_generation=int(queued["claim_generation"]),
                lease_duration_seconds=300,
            ),
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(claimed.status == "applied", claimed.to_log_dict())
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "no_eligible_work", result.to_log_dict())
        require(source_path.exists(), "claimed no-work consumed source")


def canonical_reread_races() -> None:
    for mutation in ("state", "revision", "generation", "retry", "bytes", "inode"):
        with (
            TemporaryDirectory() as queue_dir,
            TemporaryDirectory() as protected_dir,
            TemporaryDirectory() as memory_dir,
        ):
            queue_root = Path(queue_dir)
            protected_root = Path(protected_dir)
            memory_root = Path(memory_dir)
            prepare_scoped_store(memory_root)
            queued, source_path = produce(queue_root, protected_root)
            config = build_config(
                queue_root,
                protected_root,
                memory_root,
                str(queued["namespace"]),
            )
            original = local_worker._discover_candidate

            def mutate_after_selection(*args: object, **kwargs: object):
                candidate, status, reasons = original(*args, **kwargs)
                require(candidate is not None, (status, reasons))
                path = queue_root / candidate.filename
                current = dict(candidate.snapshot.record)
                if mutation == "state":
                    current["state"] = "succeeded"
                    current["terminal_reason_id"] = "security_fixture_terminal"
                elif mutation == "revision":
                    current["record_revision"] = int(current["record_revision"]) + 1
                elif mutation == "generation":
                    current["claim_generation"] = int(current["claim_generation"]) + 1
                    current["attempt_count"] = int(current["attempt_count"]) + 1
                    current["record_revision"] = int(current["record_revision"]) + 1
                elif mutation == "retry":
                    current["retry_not_before"] = current["created_at"]
                elif mutation == "bytes":
                    path.write_bytes(b"{malformed")
                    return candidate, status, reasons
                elif mutation == "inode":
                    replacement = path.with_name(path.name + ".replacement")
                    replacement.write_bytes(candidate.snapshot.data)
                    os.replace(replacement, path)
                    return candidate, status, reasons
                path.write_bytes(canonical_json_bytes(current))
                return candidate, status, reasons

            with (
                patch.object(local_worker, "_discover_candidate", mutate_after_selection),
                patch.object(
                    local_worker,
                    "execute_one_queued_relaymem_slp_primary_job",
                ) as delegated,
            ):
                result = execute_local_worker_once(build_request(config))
            require(
                result.status in {"candidate_changed", "unsafe_queue_state"},
                (mutation, result.to_log_dict()),
            )
            require(not delegated.called, (mutation, "C2 called with stale record"))
            require(source_path.exists(), (mutation, "race consumed source"))


def character_isolation() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        namespace = str(queued["namespace"])
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            namespace,
            mode="dry_run",
        )
        exact = execute_local_worker_once(build_request(config))
        require(exact.status == "dry_run_ready", exact.to_log_dict())
        explicit = execute_local_worker_once(
            build_request(config, character_id=next(iter(config.characters)))
        )
        require(explicit.status == "dry_run_ready", explicit.to_log_dict())

        unknown = execute_local_worker_once(
            build_request(config, character_id="unknown-character")
        )
        require(unknown.status == "invalid_input", unknown.to_log_dict())
        require(
            "local_worker_character_namespace_mismatch" in unknown.reason_ids,
            unknown.to_log_dict(),
        )

        ambiguous_config = build_config(
            queue_root,
            protected_root,
            memory_root,
            namespace,
            mode="dry_run",
            extra_character_id="second-character",
        )
        ambiguous = execute_local_worker_once(build_request(ambiguous_config))
        require(ambiguous.status == "invalid_input", ambiguous.to_log_dict())
        require(
            "local_worker_character_scope_ambiguous" in ambiguous.reason_ids,
            ambiguous.to_log_dict(),
        )
        require(source_path.exists(), "character rejection consumed source")
        require(not _primary_pages(memory_root), "wrong character store Primary write")


def content_free_and_cli() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
        TemporaryDirectory() as config_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )

        with patch.object(
            local_worker,
            "execute_one_queued_relaymem_slp_primary_job",
            side_effect=RuntimeError(CANARY_EXCEPTION),
        ):
            failed = execute_local_worker_once(build_request(config))
        require(failed.status == "execution_failed", failed.to_log_dict())
        assert_content_free(failed, CANARY_EXCEPTION, str(queue_root), str(source_path))
        assert_content_free(
            failed.to_log_dict(), CANARY_EXCEPTION, str(queue_root), str(source_path)
        )

        fake = SimpleNamespace(
            status="cleanup_required",
            claim_attempted=True,
            claim_performed=True,
            source_prepared=True,
            restart_rehydrated=True,
            worker_invoked=True,
            worker_status="terminal_succeeded",
            retryable=False,
            terminal=True,
            cleanup_required=True,
            reason_ids=("protected_source_cleanup_required",),
        )
        with patch.object(
            local_worker,
            "execute_one_queued_relaymem_slp_primary_job",
            return_value=fake,
        ):
            cleanup = execute_local_worker_once(build_request(config))
        assert_content_free(cleanup, CANARY_EXCEPTION, str(queue_root), str(source_path))
        assert_content_free(
            cleanup.to_log_dict(), CANARY_EXCEPTION, str(queue_root), str(source_path)
        )

        source_path.unlink()
        dry = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
            mode="dry_run",
        )
        missing = execute_local_worker_once(build_request(dry))
        require(missing.c2_result is not None, missing.to_log_dict())
        require(missing.c2_result.status == "source_unavailable", missing.to_log_dict())
        assert_content_free(missing, CANARY_EXCEPTION, str(queue_root), str(source_path))

        config_path = Path(config_dir) / "config.yaml"
        write_config(config_path, dry)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli_main(["--config", str(config_path), "--once"])
        require(code == 0, (code, stdout.getvalue(), stderr.getvalue()))
        require(stderr.getvalue() == "", "valid CLI stderr not empty")
        payload = json.loads(stdout.getvalue())
        require(payload["content_free"] is True, payload)
        require(str(config_path) not in stdout.getvalue(), "valid CLI path leak")

    for argv in (
        ["--config", CANARY_PATH],
        ["--config", CANARY_PATH, "--once", "--unknown-option"],
        ["--config", CANARY_PATH, "--once"],
    ):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli_main(argv)
        require(code == 64, (argv, code, stdout.getvalue(), stderr.getvalue()))
        require(stderr.getvalue() == "", (argv, "stderr not empty"))
        lines = stdout.getvalue().splitlines()
        require(len(lines) == 1, (argv, lines))
        payload = json.loads(lines[0])
        require(payload["content_free"] is True, payload)
        combined = stdout.getvalue() + stderr.getvalue()
        require(CANARY_PATH not in combined, (argv, "path leak"))
        require(CANARY_EXCEPTION not in combined, (argv, "exception leak"))

    invalid = execute_local_worker_once(object())
    require(invalid.status == "invalid_input", invalid.to_log_dict())
    assert_content_free(invalid, CANARY_EXCEPTION, CANARY_PATH)


def main() -> int:
    gates_and_roots()
    unsafe_filesystem()
    collision_bound_and_hardlink()
    claimed_is_no_work()
    canonical_reread_races()
    character_isolation()
    content_free_and_cli()
    print("O0 local one-job runner security smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
