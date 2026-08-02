"""E1-R1 trusted Home scene-admission smoke.

The smoke proves the server-owned Home admission gate is explicit, route-owned,
content-free, and delegated to the existing I1-B durable source/queue authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.config import (
    BackendConfig,
    CharacterConfig,
    MemorySelectionConfig,
    ModelRoute,
    RelayLMConfig,
)
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_runtime_finalization import (
    run_relaymem_slp_runtime_enqueue_after_response,
)
from relaylm.request_scope import extract_request_scope_identity
from relaylm.routing import resolve_route
from relaylm.subjective_mem_retrieval_cutover import (
    PRIMARY_WRITER_PERMITTED,
    SubjectiveMemRetrievalPrimaryWriterDecision,
    resolve_subjective_mem_retrieval_primary_writer_decision,
)
from relaylm.trusted_home_scene_admission import (
    resolve_trusted_home_scene_admission,
    trusted_home_scene_runtime_gate,
)

_FENCED_REASON = "cutover_primary_writer_fenced"
USER_CANARY = "CANARY_E1R1_USER_TEXT_DO_NOT_LEAK"
ASSISTANT_CANARY = "CANARY_E1R1_ASSISTANT_TEXT_DO_NOT_LEAK"
PATH_CANARY = "CANARY_E1R1_PRIVATE_PATH_DO_NOT_LEAK"
NAMESPACE = "e1r1_namespace"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _payload(**extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": "relaylm-home",
        "messages": [{"role": "user", "content": USER_CANARY}],
        "stream": False,
        "metadata": {"scene_state": {"scene_type": "home", "confidence": 0.99}},
    }
    payload.update(extra)
    return payload


def _scene() -> dict[str, object]:
    return {
        "scene_state": {"scene_type": "home", "confidence": 0.99},
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _config(
    root: Path,
    *,
    admission_mode: str = "disabled",
    scene_id: str = "home",
    global_enqueue: bool = False,
    queue_present: bool = True,
    protected_present: bool = True,
    store_present: bool = True,
    route_mode: str = "memory_light",
    namespace: str = NAMESPACE,
    character_id: str = "default",
) -> RelayLMConfig:
    queue = root / "queue"
    protected = root / "protected"
    memory = root / "memory"
    if queue_present:
        queue.mkdir(parents=True, exist_ok=True)
    if protected_present:
        protected.mkdir(parents=True, exist_ok=True)
    if store_present:
        (memory / "characters" / character_id).mkdir(parents=True, exist_ok=True)
    return RelayLMConfig(
        mode="memory_light",
        backends={"local": BackendConfig(base_url="http://127.0.0.1:1234/v1")},
        model_routes={
            "relaylm-home": ModelRoute(
                backend="local",
                backend_model="backend-model",
                character_id=character_id,
                mode=route_mode,
                cache_namespace="e1r1-cache",
                memory_namespace=namespace,
                scene_id=scene_id,
                session_id="e1r1-session",
                trusted_home_scene_admission_mode=admission_mode,  # type: ignore[arg-type]
            )
        },
        characters={
            character_id: CharacterConfig(soul="test soul", output_policy="test output")
        },
        memory=MemorySelectionConfig(root_path=str(memory.resolve()), store_enabled=True),
        relaymem_slp_runtime_enqueue_enabled=global_enqueue,
        relaymem_slp_runtime_enqueue_dry_run_only=not global_enqueue,
        relaymem_slp_runtime_enqueue_apply_enabled=global_enqueue,
        relaymem_slp_queue_root=str(queue.resolve()),
        relaymem_slp_protected_source_root=str(protected.resolve()),
    )


def _route(config: RelayLMConfig):
    return resolve_route(config, "relaylm-home")


def _context(
    config: RelayLMConfig,
    payload: dict[str, object],
    *,
    request_headers: dict[str, str] | None = None,
) -> PipelineContext:
    route = _route(config)
    return PipelineContext(
        request_id="request-e1r1",
        run_id="run-e1r1",
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=route,
        stream_enabled=False,
        request_headers=request_headers or {},
    )


def _writer_decision(
    config: RelayLMConfig,
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    """Derive the explicit primary_only decision from this smoke's own config."""
    decision = resolve_subjective_mem_retrieval_primary_writer_decision(config)
    require(decision.writer_class == PRIMARY_WRITER_PERMITTED, decision)
    require((decision.state, decision.recovery_required) == ("primary_stable", False), decision)
    return decision


def _run_runtime(
    config: RelayLMConfig,
    payload: dict[str, object] | None = None,
    *,
    request_headers: dict[str, str] | None = None,
    primary_writer_decision: object,
):
    context = _context(
        config,
        payload or _payload(),
        request_headers=request_headers,
    )
    return run_relaymem_slp_runtime_enqueue_after_response(
        config=config,
        diagnostics=RequestDiagnostics(request_id=context.request_id, trace_enabled=False),
        pipeline_context=context,
        registry=RelayMEMSLPPrimaryWorkerSourceRegistry(max_entries=16, ttl_seconds=60),
        status_code=200,
        resolved_session_id="e1r1-session",
        relayscn_scene_policy_artifact=_scene(),
        relayemo_artifact=None,
        primary_writer_decision=primary_writer_decision,
        assistant_visible_text=ASSISTANT_CANARY,
        message_count=1,
    ), context


def _files(root: Path) -> tuple[list[Path], list[Path]]:
    return (
        sorted((root / "queue").glob("slp-dispatch-v0-*.json")),
        sorted((root / "protected").glob("protected-source-v0-*.json")),
    )


def _durable_bytes(root: Path) -> dict[str, bytes]:
    queue_files, source_files = _files(root)
    return {path.name: path.read_bytes() for path in (*queue_files, *source_files)}


def _tampered_decision() -> SubjectiveMemRetrievalPrimaryWriterDecision:
    """Return a frozen decision whose invariants were broken after construction."""
    decision = SubjectiveMemRetrievalPrimaryWriterDecision(
        1, "primary_writer_fenced", "rejected", False, (_FENCED_REASON,), True
    )
    object.__setattr__(decision, "writer_class", PRIMARY_WRITER_PERMITTED)
    return decision


def _assert_public_content_free(value: object) -> None:
    public = repr(value)
    for forbidden in (
        USER_CANARY,
        ASSISTANT_CANARY,
        PATH_CANARY,
        "slp-job-v0:",
        "slp-dispatch-v0:",
        "Traceback",
    ):
        require(forbidden not in public, (forbidden, public))


def test_decision_statuses() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg = _config(root, admission_mode="disabled")
        decision = resolve_trusted_home_scene_admission(
            config=cfg,
            route=_route(cfg),
            payload=_payload(),
        )
        require(decision.status == "disabled", decision)
        require(trusted_home_scene_runtime_gate(cfg, decision) == (False, True, False), decision)

        cfg = _config(root / "dry", admission_mode="dry_run")
        decision = resolve_trusted_home_scene_admission(
            config=cfg,
            route=_route(cfg),
            payload=_payload(),
        )
        require(decision.status == "dry_run_ready", decision)
        require(cfg.trusted_home_scene_admission_runtime_trigger_enabled is True, cfg)
        require(trusted_home_scene_runtime_gate(cfg, decision) == (True, True, False), decision)

        cfg = _config(root / "apply", admission_mode="apply")
        decision = resolve_trusted_home_scene_admission(
            config=cfg,
            route=_route(cfg),
            payload=_payload(),
        )
        require(decision.status == "accepted", decision)
        require(trusted_home_scene_runtime_gate(cfg, decision) == (True, False, True), decision)

        payload = _payload(metadata={"trusted_home_scene_admission": "apply"})
        decision = resolve_trusted_home_scene_admission(
            config=cfg,
            route=_route(cfg),
            payload=payload,
        )
        require(decision.status == "rejected_browser_owned_trust", decision)
        require(trusted_home_scene_runtime_gate(cfg, decision) == (False, True, False), decision)

        decision = resolve_trusted_home_scene_admission(
            config=cfg,
            route=_route(cfg),
            payload=_payload(),
            headers={"x-relaylm-trusted-home-scene-admission": "apply"},
        )
        require(decision.status == "rejected_browser_owned_trust", decision)

        bad_scene = _config(root / "scene", admission_mode="apply", scene_id="not-home")
        decision = resolve_trusted_home_scene_admission(
            config=bad_scene,
            route=_route(bad_scene),
            payload=_payload(),
        )
        require(decision.status == "invalid_scene", decision)

        pass_route = _config(root / "pass", admission_mode="apply", route_mode="pass_through")
        decision = resolve_trusted_home_scene_admission(
            config=pass_route,
            route=_route(pass_route),
            payload=_payload(),
        )
        require(decision.status == "unsupported_scope", decision)

        missing_store = _config(root / "missing", admission_mode="apply", store_present=False)
        decision = resolve_trusted_home_scene_admission(
            config=missing_store,
            route=_route(missing_store),
            payload=_payload(),
        )
        require(decision.status == "missing_character_store", decision)

        missing_downstream = _config(
            root / "downstream",
            admission_mode="apply",
            protected_present=False,
        )
        decision = resolve_trusted_home_scene_admission(
            config=missing_downstream,
            route=_route(missing_downstream),
            payload=_payload(),
        )
        require(decision.status == "downstream_existing_admission_failure", decision)
        _assert_public_content_free(decision.to_log_dict())


def test_runtime_admission_and_existing_lane() -> None:
    with TemporaryDirectory(prefix=PATH_CANARY) as tmp:
        root = Path(tmp)

        disabled = _config(root / "disabled", admission_mode="disabled")
        result, context = _run_runtime(disabled, primary_writer_decision=_writer_decision(disabled))
        require(result.status == "disabled", result)
        require(_files(root / "disabled") == ([], []), _files(root / "disabled"))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())

        dry = _config(root / "dry", admission_mode="dry_run")
        result, context = _run_runtime(dry, primary_writer_decision=_writer_decision(dry))
        require(result.status == "dry_run_ready", result)
        require(_files(root / "dry") == ([], []), _files(root / "dry"))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())

        apply = _config(root / "apply", admission_mode="apply")
        result, context = _run_runtime(apply, primary_writer_decision=_writer_decision(apply))
        require(result.status in {"enqueued", "duplicate_existing"}, result)
        queue_files, source_files = _files(root / "apply")
        require(len(queue_files) == 1 and len(source_files) == 1, (queue_files, source_files))
        queue_record = json.loads(queue_files[0].read_text("utf-8"))
        source_record = json.loads(source_files[0].read_text("utf-8"))
        require(queue_record["schema_version"] == "relaymem.slp_durable_job.v0", queue_record)
        require(
            source_record["schema_version"]
            == "relaymem.slp_protected_source_artifact.v0",
            source_record,
        )
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())

        browser = _config(root / "browser", admission_mode="apply")
        result, context = _run_runtime(
            browser,
            _payload(metadata={"relaylm_trusted_scene_admission": "apply"}),
            primary_writer_decision=_writer_decision(browser),
        )
        require(result.status == "disabled", result)
        require(_files(root / "browser") == ([], []), _files(root / "browser"))
        node_dump = context.node_results_to_log_dicts()
        require("rejected_browser_owned_trust" in repr(node_dump), node_dump)
        _assert_public_content_free(node_dump)

        browser_header = _config(root / "browser-header", admission_mode="apply")
        result, context = _run_runtime(
            browser_header,
            request_headers={"x-relaylm-trusted-home-scene-admission": "apply"},
            primary_writer_decision=_writer_decision(browser_header),
        )
        require(result.status == "disabled", result)
        require(
            _files(root / "browser-header") == ([], []),
            _files(root / "browser-header"),
        )
        node_dump = context.node_results_to_log_dicts()
        require("rejected_browser_owned_trust" in repr(node_dump), node_dump)
        _assert_public_content_free(node_dump)

        app_like = _config(root / "request-scope", admission_mode="apply")
        context = _context(app_like, _payload())
        extract_request_scope_identity(
            {"x-relaylm-trusted-home-scene-admission": "apply"},
            context.original_payload,
        )
        require(
            "x-relaylm-trusted-home-scene-admission" in context.request_headers,
            context.request_headers,
        )
        result = run_relaymem_slp_runtime_enqueue_after_response(
            config=app_like,
            diagnostics=RequestDiagnostics(request_id=context.request_id, trace_enabled=False),
            pipeline_context=context,
            registry=RelayMEMSLPPrimaryWorkerSourceRegistry(max_entries=16, ttl_seconds=60),
            status_code=200,
            resolved_session_id="e1r1-session",
            relayscn_scene_policy_artifact=_scene(),
            relayemo_artifact=None,
            primary_writer_decision=_writer_decision(app_like),
            assistant_visible_text=ASSISTANT_CANARY,
            message_count=1,
        )
        require(result.status == "disabled", result)
        require(_files(root / "request-scope") == ([], []), _files(root / "request-scope"))

        explicit = _config(root / "explicit", admission_mode="disabled", global_enqueue=True)
        result, context = _run_runtime(explicit, primary_writer_decision=_writer_decision(explicit))
        require(result.status in {"enqueued", "duplicate_existing"}, result)
        queue_files, source_files = _files(root / "explicit")
        require(len(queue_files) == 1 and len(source_files) == 1, (queue_files, source_files))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())


def test_primary_writer_decision_dominates_finalization() -> None:
    """RT-1D-R2A: the writer decision dominates every governed finalization effect."""
    fenced = SubjectiveMemRetrievalPrimaryWriterDecision(
        1, "primary_writer_fenced", "rejected", False, (_FENCED_REASON,), True
    )
    recovery = SubjectiveMemRetrievalPrimaryWriterDecision(
        1, "recovery_required", "rejected", True, ("cutover_writer_state_unsupported",), True
    )
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        # The decision is required: no default, no unbound class, no Optional.
        missing = _config(root / "missing", admission_mode="disabled", global_enqueue=True)
        context = _context(missing, _payload())
        try:
            run_relaymem_slp_runtime_enqueue_after_response(
                config=missing,
                diagnostics=RequestDiagnostics(
                    request_id=context.request_id, trace_enabled=False
                ),
                pipeline_context=context,
                registry=RelayMEMSLPPrimaryWorkerSourceRegistry(
                    max_entries=16, ttl_seconds=60
                ),
                status_code=200,
                resolved_session_id="e1r1-session",
                relayscn_scene_policy_artifact=_scene(),
                relayemo_artifact=None,
                assistant_visible_text=ASSISTANT_CANARY,
                message_count=1,
            )
        except TypeError as exc:
            require("primary_writer_decision" in str(exc), exc)
        else:
            raise AssertionError("missing_primary_writer_decision_must_fail_closed")
        require(_files(root / "missing") == ([], []), _files(root / "missing"))

        # Rejected, recovery-required, foreign-typed, and tampered values all
        # block before any replay, protected-source write, or queue enqueue.
        for label, decision in (
            ("fenced", fenced),
            ("recovery", recovery),
            ("foreign", "primary_only"),
            ("tampered", _tampered_decision()),
        ):
            blocked = _config(root / label, admission_mode="apply", global_enqueue=True)
            result, context = _run_runtime(blocked, primary_writer_decision=decision)
            require(result.status not in {"enqueued", "duplicate_existing"}, (label, result))
            require(_files(root / label) == ([], []), (label, _files(root / label)))
            _assert_public_content_free(result.to_log_dict())
            _assert_public_content_free(context.node_results_to_log_dicts())

        # The permitted primary_only path keeps its exact existing outcome, and
        # a later rejected call leaves those durable bytes byte-identical.
        permitted = _config(root / "permitted", admission_mode="disabled", global_enqueue=True)
        result, _ = _run_runtime(permitted, primary_writer_decision=_writer_decision(permitted))
        require(result.status in {"enqueued", "duplicate_existing"}, result)
        published = _durable_bytes(root / "permitted")
        require(len(published) == 2, sorted(published))
        blocked_result, _ = _run_runtime(permitted, primary_writer_decision=fenced)
        require(
            blocked_result.status not in {"enqueued", "duplicate_existing"}, blocked_result
        )
        require(_durable_bytes(root / "permitted") == published, "reject_mutated_durable_state")


def main() -> None:
    test_decision_statuses()
    test_runtime_admission_and_existing_lane()
    test_primary_writer_decision_dominates_finalization()
    print("relaylm_e1r1_trusted_home_scene_admission_smoke: ok")


if __name__ == "__main__":
    main()
