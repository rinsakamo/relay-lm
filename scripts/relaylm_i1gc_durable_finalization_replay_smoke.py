"""I1-GC one-record replay, duplicate, race, and completion convergence smoke."""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import yaml

import relaylm_i1gb_durable_finalization_publication_smoke as gb
import relaylm.relaymem_slp_durable_finalization_replay as replay_module
from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.relaymem_slp_durable_enqueue import enqueue_relaymem_slp_durable_job
from relaylm.relaymem_slp_durable_finalization_publication import (
    RelayMEMSLPDurableFinalizationPreparedTurn,
)
from relaylm.relaymem_slp_durable_finalization_record import canonical_json_bytes
from relaylm.relaymem_slp_durable_finalization_replay import (
    COMPLETION_SCHEMA,
    build_relaymem_slp_durable_finalization_replay_node_result,
    completion_filename,
    replay_relaymem_slp_durable_finalization_record,
)
from relaylm.relaymem_slp_finalized_turn_source import (
    build_relaymem_slp_finalized_turn_source,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
)
from relaylm.relaymem_slp_queue_record import canonical_json_bytes as queue_json_bytes
from relaylm.relaymem_slp_queue_record import record_filename
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_runtime_enqueue import prepare_relaymem_slp_runtime_enqueue
from relaylm.relaymem_slp_runtime_finalization import (
    run_relaymem_slp_runtime_enqueue_after_response,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LEAK_CANARY = "CANARY_I1GC_PRIVATE_EXCEPTION_DO_NOT_LEAK"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _config(root: Path, *, dry_run: bool = False) -> RelayLMConfig:
    queue_root = root / "queue"
    source_root = root / "source"
    finalization_root = root / "finalization"
    for path in (queue_root, source_root, finalization_root):
        path.mkdir(parents=True, exist_ok=True)
    raw = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text("utf-8"))
    raw["trace"] = {"enabled": False, "path": None}
    raw["relaymem_slp_queue_root"] = str(queue_root.resolve())
    raw["relaymem_slp_protected_source_root"] = str(source_root.resolve())
    raw["relaymem_slp_durable_finalization_root"] = str(finalization_root.resolve())
    raw["relaymem_slp_runtime_enqueue_enabled"] = True
    raw["relaymem_slp_runtime_enqueue_dry_run_only"] = dry_run
    raw["relaymem_slp_runtime_enqueue_apply_enabled"] = not dry_run
    raw["relaymem_slp_durable_finalization_enabled"] = True
    raw["relaymem_slp_durable_finalization_dry_run_only"] = dry_run
    raw["relaymem_slp_durable_finalization_apply_enabled"] = not dry_run
    raw["memory"].update({
        "store_enabled": False,
        "retrieval_dry_run_only": True,
        "ctx_block_apply_enabled": False,
        "snippet_extraction_enabled": False,
        "snippet_apply_enabled": False,
        "snippet_runtime_injection_enabled": False,
        "token_budget_truncation_enabled": False,
    })
    return RelayLMConfig.model_validate(raw)


def _source_and_preparation(request_id: str = gb.REQUEST_ID):
    source = build_relaymem_slp_finalized_turn_source(
        gb._context(request_id=request_id),
        assistant_visible_text=gb.ASSISTANT_CANARY,
        status_code=200,
        resolved_session_id=gb.SESSION_ID,
        relayscn_scene_policy_artifact=gb._scene(),
        relayemo_artifact=gb._emo(),
        response_finalized=True,
        enabled=True,
    )
    require(source.status == "ready", source.to_log_dict())
    preparation = prepare_relaymem_slp_runtime_enqueue(source)
    require(preparation.status == "dry_run_ready", preparation.to_log_dict())
    require(preparation.dispatch_result is not None, preparation)
    require(preparation.dispatch_result.durable_job is not None, preparation)
    require(type(preparation.protected_source_payload) is dict, preparation)
    return source, preparation


def _publish_sealed(root: Path, *, request_id: str = gb.REQUEST_ID):
    base, segments, seal = gb._records(request_id=request_id)
    store = gb._store(root / "finalization")
    gb._publish(store, base, segments, seal)
    source, preparation = _source_and_preparation(request_id)
    require(
        canonical_json_bytes(preparation.dispatch_result.durable_job.to_runtime_dict())
        == canonical_json_bytes(seal["durable_job"]),
        "fixture_identity_mismatch",
    )
    return base, seal, source, preparation


def _source_store(config: RelayLMConfig) -> RelayMEMSLPDurableProtectedSourceStore:
    return RelayMEMSLPDurableProtectedSourceStore(
        str(config.relaymem_slp_protected_source_root),
        max_artifact_bytes=config.relaymem_slp_protected_source_max_artifact_bytes,
    )


def _persist_source(config: RelayLMConfig, source: Any, preparation: Any, *, payload=None):
    exact_payload = (
        deepcopy(preparation.protected_source_payload)
        if payload is None else payload
    )
    result = _source_store(config).persist(
        source_payload=exact_payload,
        durable_job=preparation.dispatch_result.durable_job,
        character_id=source.source.character_id,
    )
    require(result.status in {"published_new", "duplicate_existing"}, result)
    return result


def _enqueue(config: RelayLMConfig, preparation: Any):
    result = enqueue_relaymem_slp_durable_job(
        preparation.dispatch_result,
        queue_root=config.relaymem_slp_queue_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(result.status in {"enqueued_new", "duplicate_existing"}, result)
    return result


def _replay(config: RelayLMConfig, locator: str, *, fault=None):
    return replay_relaymem_slp_durable_finalization_record(
        config,
        locator_digest=locator,
        registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
        fault_injector=fault,
    )


def _completion_path(config: RelayLMConfig, locator: str) -> Path:
    return Path(str(config.relaymem_slp_durable_finalization_root)) / completion_filename(locator)


def _queue_path(config: RelayLMConfig, preparation: Any) -> Path:
    key = preparation.dispatch_result.durable_job.dispatch_idempotency_key
    return Path(str(config.relaymem_slp_queue_root)) / record_filename(key)


def _snapshot(root: Path) -> tuple[tuple[str, int, str], ...]:
    rows: list[tuple[str, int, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        data = path.read_bytes()
        rows.append((str(path.relative_to(root)), len(data), hashlib.sha256(data).hexdigest()))
    return tuple(rows)


def _fault(stage: str):
    def inject(current: str) -> None:
        if current == stage:
            raise RuntimeError(LEAK_CANARY)
    return inject


def _assert_content_free(value: object, locator: str) -> None:
    rendered = repr(value) + "\n" + json.dumps(
        value.to_log_dict() if hasattr(value, "to_log_dict") else value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    for private in (
        gb.USER_CANARY,
        gb.ASSISTANT_CANARY,
        gb.NAMESPACE_CANARY,
        gb.RUN_ID,
        gb.SESSION_ID,
        gb.REQUEST_ID,
        LEAK_CANARY,
        locator,
        "slp-job-v0:",
        "slp-dispatch-v0:",
    ):
        require(private not in rendered, (private, rendered))


def test_basic_convergence_and_duplicates() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        first = _replay(config, locator)
        require(first.status == "completed", first)
        require(first.projection.source_created, first)
        require(first.projection.queue_created, first)
        require(first.projection.completion_created, first)
        require(_completion_path(config, locator).is_file(), first)
        before = _snapshot(root)
        second = _replay(config, locator)
        third = _replay(config, locator)
        require(second.status == "already_complete", second)
        require(third.status == "already_complete", third)
        require(_snapshot(root) == before, (_snapshot(root), before))
        node = build_relaymem_slp_durable_finalization_replay_node_result(second)
        _assert_content_free(first, locator)
        _assert_content_free(second, locator)
        _assert_content_free(node, locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        _persist_source(config, source, preparation)
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "completed", result)
        require(not result.projection.source_created, result)
        require(result.projection.queue_created, result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        _persist_source(config, source, preparation)
        _enqueue(config, preparation)
        queue_before = _queue_path(config, preparation).read_bytes()
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "completed", result)
        require(not result.projection.source_created, result)
        require(not result.projection.queue_created, result)
        require(result.projection.completion_created, result)
        require(_queue_path(config, preparation).read_bytes() == queue_before, result)


def test_incomplete_dry_run_and_missing() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _ = gb._records()
        require(gb._store(root / "finalization").publish_base(base).status == "published_new", base)
        locator = str(base["locator_digest"])
        result = _replay(config, locator)
        require(result.status == "not_replayable", result)
        require(not any(Path(str(config.relaymem_slp_protected_source_root)).iterdir()), result)
        require(not any(Path(str(config.relaymem_slp_queue_root)).iterdir()), result)
        require(not _completion_path(config, locator).exists(), result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        missing = _replay(config, "f" * 64)
        require(missing.status == "record_missing", missing)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, dry_run=True)
        base, _, _, _ = _publish_sealed(root)
        before = _snapshot(root)
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "dry_run_ready", result)
        require(_snapshot(root) == before, (_snapshot(root), before))


def _process_replay(root_text: str, locator: str, started: Any, release: Any, output: Any) -> None:
    config = _config(Path(root_text))

    def hold(stage: str) -> None:
        if stage == "after_lock_before_reread":
            started.set()
            if not release.wait(20):
                raise RuntimeError("parallel_release_timeout")

    result = _replay(config, locator, fault=hold)
    output.put(result.status)


def test_process_races_and_normal_finalizer() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        ctx = multiprocessing.get_context("fork")
        started = ctx.Event()
        release = ctx.Event()
        output = ctx.Queue()
        process = ctx.Process(target=_process_replay, args=(str(root), locator, started, release, output))
        process.start()
        require(started.wait(20), "parallel_replay_did_not_acquire_lock")
        loser = _replay(config, locator)
        require(loser.status == "replay_lock_busy", loser)
        release.set()
        process.join(20)
        require(process.exitcode == 0, process.exitcode)
        require(output.get(timeout=5) == "completed", "parallel_winner_failed")
        require(_replay(config, locator).status == "already_complete", locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        locator = str(base["locator_digest"])
        ctx = multiprocessing.get_context("fork")
        started = ctx.Event()
        release = ctx.Event()
        output = ctx.Queue()
        process = ctx.Process(target=_process_replay, args=(str(root), locator, started, release, output))
        process.start()
        require(started.wait(20), "restart_replay_did_not_acquire_lock")
        prepared_turn = RelayMEMSLPDurableFinalizationPreparedTurn(
            source_result=source,
            runtime_preparation=preparation,
        )
        first = run_relaymem_slp_runtime_enqueue_after_response(
            config=config,
            diagnostics=RequestDiagnostics(request_id=gb.REQUEST_ID),
            pipeline_context=gb._context(),
            registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
            status_code=200,
            resolved_session_id=gb.SESSION_ID,
            relayscn_scene_policy_artifact=gb._scene(),
            relayemo_artifact=gb._emo(),
            prepared_turn=prepared_turn,
            message_count=1,
        )
        require(first.status == "enqueue_failed", first)
        release.set()
        process.join(20)
        require(process.exitcode == 0, process.exitcode)
        require(output.get(timeout=5) == "completed", "restart_winner_failed")
        second = run_relaymem_slp_runtime_enqueue_after_response(
            config=config,
            diagnostics=RequestDiagnostics(request_id=gb.REQUEST_ID),
            pipeline_context=gb._context(),
            registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
            status_code=200,
            resolved_session_id=gb.SESSION_ID,
            relayscn_scene_policy_artifact=gb._scene(),
            relayemo_artifact=gb._emo(),
            prepared_turn=prepared_turn,
            message_count=1,
        )
        require(second.status == "duplicate_existing", second)


def test_fault_resume_and_ambiguity() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        stopped = _replay(config, locator, fault=_fault("after_source_commit_before_queue"))
        require(stopped.status == "queue_pending", stopped)
        require(stopped.projection.source_present, stopped)
        require(not stopped.projection.queue_present, stopped)
        require(_replay(config, locator).status == "completed", locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        stopped = _replay(config, locator, fault=_fault("after_queue_commit_before_completion"))
        require(stopped.status == "completion_pending", stopped)
        require(stopped.projection.source_present and stopped.projection.queue_present, stopped)
        require(not stopped.projection.completion_present, stopped)
        require(_replay(config, locator).status == "completed", locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        locator = str(base["locator_digest"])
        _persist_source(config, source, preparation)
        _enqueue(config, preparation)

        def ambiguous_rename(root_fd: int, temporary: str, final: str) -> str:
            os.rename(temporary, final, src_dir_fd=root_fd, dst_dir_fd=root_fd)
            return "failed"

        with patch.object(replay_module, "_rename_noreplace", side_effect=ambiguous_rename):
            result = _replay(config, locator)
        require(result.status == "exact_duplicate", result)
        require(result.projection.completion_present, result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        original = replay_module.apply_relaymem_slp_runtime_enqueue

        def ambiguous_enqueue(*args: Any, **kwargs: Any):
            applied = original(*args, **kwargs)
            require(applied.enqueue_result is not None, applied)
            enqueue = replace(
                applied.enqueue_result,
                status="write_failed",
                outcome="write_failed",
                durability_confirmed=False,
                blocked_reasons=("queue_outcome_unknown",),
            )
            return replace(
                applied,
                status="enqueue_failed",
                failure_stage="enqueue",
                blocked_reasons=("queue_outcome_unknown",),
                enqueue_result=enqueue,
            )

        with patch.object(replay_module, "apply_relaymem_slp_runtime_enqueue", side_effect=ambiguous_enqueue):
            result = _replay(config, locator)
        require(result.status == "completed", result)
        require(result.projection.queue_present, result)
        require(result.durable_runtime_result is not None, result)
        require(result.durable_runtime_result.status == "process_local_cache_degraded", result.durable_runtime_result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        result = _replay(config, locator, fault=_fault("after_completion_publish_before_return"))
        require(result.status == "completed", result)
        require(result.projection.completion_present, result)
        require(_replay(config, locator).status == "already_complete", locator)


def test_invariants_collisions_and_terminal() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, preparation = _publish_sealed(root)
        queue = _enqueue(config, preparation)
        queue_path = _queue_path(config, preparation)
        before = queue_path.read_bytes()
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "invariant_violation", result)
        require(queue_path.read_bytes() == before, result)
        require(not any(Path(str(config.relaymem_slp_protected_source_root)).iterdir()), result)
        require(queue.status == "enqueued_new", queue)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        payload = deepcopy(preparation.protected_source_payload)
        payload["governed_messages"][-1]["content"] = "different protected content"
        _persist_source(config, source, preparation, payload=payload)
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "content_collision", result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        _persist_source(config, source, preparation)
        queued = _enqueue(config, preparation)
        path = _queue_path(config, preparation)
        record = dict(queued.durable_record)
        record["namespace"] = "collision-namespace"
        path.write_bytes(queue_json_bytes(record))
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "content_collision", result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        _, other_preparation = _source_and_preparation("request-i1gc-other")
        with patch.object(replay_module, "prepare_relaymem_slp_runtime_enqueue", return_value=other_preparation):
            result = _replay(config, str(base["locator_digest"]))
        require(result.status == "invariant_violation", result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, source, preparation = _publish_sealed(root)
        _persist_source(config, source, preparation)
        queued = _enqueue(config, preparation)
        record = dict(queued.durable_record)
        claim = transition_relaymem_slp_queue_state(
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="claim",
                job_id=str(record["job_id"]),
                dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
                expected_record_revision=int(record["record_revision"]),
                expected_state=str(record["state"]),
                claim_owner="i1gc-smoke-worker",
                claim_generation=int(record["claim_generation"]),
                lease_duration_seconds=30,
            ),
            queue_root=config.relaymem_slp_queue_root,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(claim.status == "applied", claim)
        claimed = dict(claim.durable_record)
        terminal = transition_relaymem_slp_queue_state(
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="commit_terminal",
                job_id=str(claimed["job_id"]),
                dispatch_idempotency_key=str(claimed["dispatch_idempotency_key"]),
                expected_record_revision=int(claimed["record_revision"]),
                expected_state=str(claimed["state"]),
                claim_owner=str(claimed["claim_owner"]),
                claim_generation=int(claimed["claim_generation"]),
                lease_token=str(claimed["lease_token"]),
                terminal_state="succeeded",
                terminal_reason_id="i1gc_terminal_fixture",
            ),
            queue_root=config.relaymem_slp_queue_root,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(terminal.status == "applied", terminal)
        path = _queue_path(config, preparation)
        before = path.read_bytes()
        result = _replay(config, str(base["locator_digest"]))
        require(result.status == "completed", result)
        require(result.projection.queue_terminal, result)
        require(path.read_bytes() == before, result)


def _successful_fixture(root: Path):
    config = _config(root)
    base, _, _, _ = _publish_sealed(root)
    locator = str(base["locator_digest"])
    result = _replay(config, locator)
    require(result.status == "completed", result)
    path = _completion_path(config, locator)
    marker = json.loads(path.read_text("utf-8"))
    return config, locator, path, marker


def test_completion_corruption_schema_and_unsafe_types() -> None:
    cases = (
        ("truncated", lambda marker: b'{"schema_version":'),
        ("noncanonical", lambda marker: json.dumps(marker, indent=2).encode("utf-8")),
        (
            "duplicate-key",
            lambda marker: (
                canonical_json_bytes(marker).decode("utf-8")[:-1]
                + ',"schema_version":"' + COMPLETION_SCHEMA + '"}'
            ).encode("utf-8"),
        ),
        ("digest", lambda marker: canonical_json_bytes({**marker, "completion_digest": "0" * 64})),
    )
    for label, mutate in cases:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config, locator, path, marker = _successful_fixture(root)
            path.write_bytes(mutate(marker))
            result = _replay(config, locator)
            require(result.status == "corrupt", (label, result))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator, path, marker = _successful_fixture(root)
        marker["schema_version"] = "relaymem.slp_durable_finalization_completion.v999"
        marker["completion_digest"] = replay_module._hash_without(marker, "completion_digest")
        path.write_bytes(canonical_json_bytes(marker))
        result = _replay(config, locator)
        require(result.status == "schema_unsupported", result)

    for label in ("symlink", "hardlink", "directory"):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = _config(root)
            base, _, source, preparation = _publish_sealed(root)
            locator = str(base["locator_digest"])
            _persist_source(config, source, preparation)
            _enqueue(config, preparation)
            path = _completion_path(config, locator)
            target = path.with_name("completion-target")
            target.write_text("target", encoding="utf-8")
            if label == "symlink":
                path.symlink_to(target)
            elif label == "hardlink":
                os.link(target, path)
            else:
                path.mkdir()
            result = _replay(config, locator)
            require(result.status == "unsafe_path_or_type", (label, result))


def test_nonexecution_contract_and_fault_projection() -> None:
    module_text = (REPO_ROOT / "relaylm" / "relaymem_slp_durable_finalization_replay.py").read_text("utf-8")
    for forbidden in (
        "transition_relaymem_slp_queue_state",
        "run_one_queued",
        "execute_one_claimed",
        "compose_relaymem_primary_pipeline",
        "write_primary",
        "cleanup_after_terminal",
        "discard_unqueued",
    ):
        require(forbidden not in module_text, forbidden)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        base, _, _, _ = _publish_sealed(root)
        locator = str(base["locator_digest"])
        result = _replay(config, locator, fault=_fault("after_lock_before_reread"))
        require(result.status == "failed", result)
        node = build_relaymem_slp_durable_finalization_replay_node_result(result)
        _assert_content_free(result, locator)
        _assert_content_free(node, locator)
        require(result.to_log_dict()["worker_invoked"] is False, result)
        require(result.to_log_dict()["b3_transition_performed"] is False, result)
        require(result.to_log_dict()["writes_memory"] is False, result)


def main() -> None:
    test_basic_convergence_and_duplicates()
    test_incomplete_dry_run_and_missing()
    test_process_races_and_normal_finalizer()
    test_fault_resume_and_ambiguity()
    test_invariants_collisions_and_terminal()
    test_completion_corruption_schema_and_unsafe_types()
    test_nonexecution_contract_and_fault_projection()
    print("relaylm_i1gc_durable_finalization_replay_smoke: ok")


if __name__ == "__main__":
    main()
