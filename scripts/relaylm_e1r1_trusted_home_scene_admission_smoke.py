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
from relaylm.routing import resolve_route
from relaylm.trusted_home_scene_admission import (
    resolve_trusted_home_scene_admission,
    trusted_home_scene_runtime_gate,
)

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


def _context(config: RelayLMConfig, payload: dict[str, object]) -> PipelineContext:
    route = _route(config)
    return PipelineContext(
        request_id="request-e1r1",
        run_id="run-e1r1",
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=route,
        stream_enabled=False,
    )


def _run_runtime(
    config: RelayLMConfig,
    payload: dict[str, object] | None = None,
):
    context = _context(config, payload or _payload())
    return run_relaymem_slp_runtime_enqueue_after_response(
        config=config,
        diagnostics=RequestDiagnostics(request_id=context.request_id, trace_enabled=False),
        pipeline_context=context,
        registry=RelayMEMSLPPrimaryWorkerSourceRegistry(max_entries=16, ttl_seconds=60),
        status_code=200,
        resolved_session_id="e1r1-session",
        relayscn_scene_policy_artifact=_scene(),
        relayemo_artifact=None,
        assistant_visible_text=ASSISTANT_CANARY,
        message_count=1,
    ), context


def _files(root: Path) -> tuple[list[Path], list[Path]]:
    return (
        sorted((root / "queue").glob("slp-dispatch-v0-*.json")),
        sorted((root / "protected").glob("protected-source-v0-*.json")),
    )


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
        result, context = _run_runtime(disabled)
        require(result.status == "disabled", result)
        require(_files(root / "disabled") == ([], []), _files(root / "disabled"))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())

        dry = _config(root / "dry", admission_mode="dry_run")
        result, context = _run_runtime(dry)
        require(result.status == "dry_run_ready", result)
        require(_files(root / "dry") == ([], []), _files(root / "dry"))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())

        apply = _config(root / "apply", admission_mode="apply")
        result, context = _run_runtime(apply)
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
        )
        require(result.status == "disabled", result)
        require(_files(root / "browser") == ([], []), _files(root / "browser"))
        node_dump = context.node_results_to_log_dicts()
        require("rejected_browser_owned_trust" in repr(node_dump), node_dump)
        _assert_public_content_free(node_dump)

        explicit = _config(root / "explicit", admission_mode="disabled", global_enqueue=True)
        result, context = _run_runtime(explicit)
        require(result.status in {"enqueued", "duplicate_existing"}, result)
        queue_files, source_files = _files(root / "explicit")
        require(len(queue_files) == 1 and len(source_files) == 1, (queue_files, source_files))
        _assert_public_content_free(result.to_log_dict())
        _assert_public_content_free(context.node_results_to_log_dicts())


def main() -> None:
    test_decision_statuses()
    test_runtime_admission_and_existing_lane()
    print("relaylm_e1r1_trusted_home_scene_admission_smoke: ok")


if __name__ == "__main__":
    main()
