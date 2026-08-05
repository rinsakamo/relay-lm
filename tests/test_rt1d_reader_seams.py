"""Structural and public-equivalence coverage for the RT-1D-S1 reader seams."""

from __future__ import annotations
import ast
import inspect
from collections.abc import Mapping
from pathlib import Path

from relaylm.managed_chat_runtime import handle_managed_chat_completion
from relaylm.managed_chat_pipeline_runtime import (
    _extract_ctx_hints,
    run_managed_chat_pipeline,
)
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relaymem_retrieval import (
    build_relaymem_retrieval_dry_run_artifact,
    run_relaymem_retrieval_stage,
)

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "relaylm/managed_chat_pipeline_runtime.py",
    "relaylm/relaymem_retrieval_dry_run.py",
    "relaylm/_relaymem_retrieval_candidates.py",
    "relaylm/_relaymem_retrieval_snippet.py",
    "relaylm/relaymem_primary_recall_selection.py",
    "relaylm/relaymem_primary_recall_store.py",
)


def _tree(path: str) -> ast.Module:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def _function(path: str, name: str):
    return next(
        node
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def _imports(path: str) -> set[str]:
    return {
        node.module
        for node in _tree(path).body
        if isinstance(node, ast.ImportFrom) and node.module
    }


def test_public_facades_and_signatures_remain_stable() -> None:
    assert inspect.iscoroutinefunction(handle_managed_chat_completion)
    assert inspect.iscoroutinefunction(run_managed_chat_pipeline)
    assert list(inspect.signature(apply_relaymem_primary_recall_scope).parameters) == [
        "retrieval_artifact",
        "scoped_store_root",
        "expected_namespace",
        "max_snippet_chars",
        "max_snippet_candidates",
        "snippet_budget",
        "chars_per_token",
    ]
    assert callable(resolve_relaymem_character_store_root)
    assert callable(build_relaymem_retrieval_dry_run_artifact)
    assert callable(run_relaymem_retrieval_stage)


def test_managed_facade_delegates_once_and_owner_preserves_order() -> None:
    facade = _function(
        "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
    )
    owner = _function(
        "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
    )
    delegations = [
        node
        for node in ast.walk(facade)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_managed_chat_pipeline"
    ]
    assert len(delegations) == 1
    calls = {
        name: min(
            node.lineno
            for node in ast.walk(owner)
            if isinstance(node, ast.Name) and node.id == name
        )
        for name in (
            "run_relayrel_stage",
            "run_relayscn_stage",
            "run_relayemo_stage",
            "run_relayint_stage",
        )
    }
    assert (
        calls["run_relayrel_stage"]
        < calls["run_relayscn_stage"]
        < calls["run_relayemo_stage"]
        < calls["run_relayint_stage"]
    )
    assert any(
        isinstance(node, ast.keyword)
        and node.arg == "offload"
        and isinstance(node.value, ast.Constant)
        and node.value.value is True
        for node in ast.walk(_tree("relaylm/managed_chat_pipeline_runtime.py"))
    )


def test_moved_ctx_hints_preserve_relayint_mapping_contract() -> None:
    source_ctx = {"current_topic": "alpha"}
    hints = _extract_ctx_hints({"metadata": {"ctx": source_ctx}})
    assert hints == {"current_topic": "alpha"}
    assert hints is not source_ctx
    assert isinstance(hints, Mapping)
    assert isinstance(hints, dict)

    fallback = _extract_ctx_hints(
        {
            "metadata": {
                "ctx": {"current_topic": "alpha"},
                "ctx_handoff_guess": "candidate",
            }
        }
    )
    assert fallback == {
        "current_topic": "alpha",
        "ctx_handoff_guess": "candidate",
    }

    existing = _extract_ctx_hints(
        {
            "metadata": {
                "ctx": {"ctx_handoff_guess": "existing"},
                "ctx_handoff_guess": "fallback",
            }
        }
    )
    assert existing["ctx_handoff_guess"] == "existing"


def test_moved_ctx_hints_fail_closed_and_ignore_top_level_list() -> None:
    payloads = (
        {},
        {"metadata": None},
        {"metadata": []},
        {"metadata": {"ctx": []}},
        {"ctx_hints": [{"current_topic": "wrong"}]},
    )
    for payload in payloads:
        hints = _extract_ctx_hints(payload)
        assert hints == {}
        assert isinstance(hints, Mapping)
        assert isinstance(hints, dict)


def test_dependency_direction_and_moved_ownership() -> None:
    assert "relaylm.relaymem_retrieval_dry_run" in _imports(
        "relaylm/relaymem_retrieval.py"
    )
    for path in (
        "relaylm/relaymem_retrieval_dry_run.py",
        "relaylm/_relaymem_retrieval_candidates.py",
        "relaylm/_relaymem_retrieval_snippet.py",
    ):
        assert "relaylm.relaymem_retrieval" not in _imports(path)
    assert "relaylm.relaymem_primary_recall" not in _imports(
        "relaylm/relaymem_primary_recall_selection.py"
    )
    assert "relaylm.relaymem_primary_recall" not in _imports(
        "relaylm/relaymem_primary_recall_store.py"
    )
    assert "build_relaymem_retrieval_dry_run_artifact" not in {
        node.name
        for node in _tree("relaylm/relaymem_retrieval.py").body
        if isinstance(node, ast.FunctionDef)
    }
    assert "_load_validated_page" not in {
        node.name
        for node in _tree("relaylm/relaymem_primary_recall.py").body
        if isinstance(node, ast.FunctionDef)
    }


def test_bounded_modules_and_orchestration() -> None:
    for path in NEW_MODULES:
        assert len((ROOT / path).read_text(encoding="utf-8").splitlines()) < 700
    assert (
        _function(
            "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
        ).end_lineno
        - _function(
            "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
        ).lineno
        + 1
        <= 80
    )
    assert (
        _function(
            "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
        ).end_lineno
        - _function(
            "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
        ).lineno
        + 1
        <= 80
    )
    assert (
        _function(
            "relaylm/relaymem_primary_recall.py", "apply_relaymem_primary_recall_scope"
        ).end_lineno
        - _function(
            "relaylm/relaymem_primary_recall.py", "apply_relaymem_primary_recall_scope"
        ).lineno
        + 1
        <= 80
    )


def test_primary_empty_input_shape_remains_fail_closed() -> None:
    result = apply_relaymem_primary_recall_scope(
        None,
        scoped_store_root=None,
        expected_namespace=None,
        max_snippet_chars=512,
        max_snippet_candidates=3,
        snippet_budget=512,
    )
    assert result["primary_recall_runtime"]["content_included"] is False
    assert result["primary_recall_runtime"]["selected_memories"] == []
    assert result["primary_recall_projection"]["retrieval_attempted"] is False
    assert (
        "character_store_scope_unavailable"
        in result["primary_recall_projection"]["blocked_reason_ids"]
    )


# ---------------------------------------------------------------------------
# RT-1D-R4 one-authority ordinary routing.
#
# The reader seam now serves exactly the one authority the immutable RT-1D
# reader decision names. These cases prove the whole ordinary path end to end:
# exact source acquisition, the disposable live projection bundle, exact
# selection, durable usage finalization before admission, and the absence of
# any fallback in either direction.
# ---------------------------------------------------------------------------

import json
from dataclasses import replace

import pytest
import yaml

from relaylm.character_workspace import (
    INTERNAL_DIRECTORIES,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    REQUIRED_SOURCE_FILENAMES,
    validate_character_workspace,
)
from relaylm._subjective_mem_retrieval_cutover_activation import (
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_SCHEMA_VERSION,
    FORWARD_STATES,
)
from relaylm._subjective_mem_retrieval_runtime_projection import (
    SubjectiveMemRetrievalRuntimeProjectionSpec,
    acquire_subjective_mem_retrieval_runtime_projection,
)
from relaylm.config import RelayLMConfig
from relaylm.evidence_common import canonical_digest
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.relayctx_repack import _ordinary_selected_memories
from relaylm.relaymem_retrieval import (
    ORDINARY_MEMORY_AUTHORITY_KEY,
    SUBJECTIVE_RUNTIME_KEY,
    run_relaymem_retrieval_stage,
)
from relaylm.routing import resolve_route
from relaylm.subjective_mem_retrieval_cutover import (
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_TRANSFERRED_SCOPE,
    SubjectiveMemRetrievalCutoverBinding,
    resolve_subjective_mem_retrieval_primary_reader_decision,
)
from relaylm.subjective_mem_retrieval_projection_store import (
    PROJECTION_BUNDLE_FILENAME,
)
from relaylm.subjective_mem_retrieval_usage_ledger import (
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
)
from test_subjective_mem_retrieval_projection import (
    CHARACTER,
    NOW,
    SPACE,
    _one_active,
    _receipt_id,
)

_MEMORY_PAGE = "memory/episodes/subjective-mem-v1.md"


def _character_workspace(root: Path) -> Path:
    workspace_root = root / "characters"
    character_root = workspace_root / CHARACTER
    character_root.mkdir(parents=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        (character_root / filename).write_text(f"# {filename}\n", encoding="utf-8")
    for relative in LOWERCASE_WORKSPACE_DIRECTORIES + INTERNAL_DIRECTORIES:
        (character_root / relative).mkdir(parents=True, exist_ok=True)
    result = validate_character_workspace(
        character_root, character_id=CHARACTER, public=False
    )
    assert result.is_valid, result.errors
    return workspace_root.resolve()


def _seed_subjective_evidence(root: Path, source) -> EvidenceRecordStore:
    """Persist exactly the selector, receipt, and authorization one memory names."""

    store = EvidenceRecordStore(str(root))
    entry = source.entries[0]
    selector = entry.current_selector_record
    receipt_kind = (
        "subjective_mem_st1_commit_receipt"
        if selector["current_revision"] == 1
        else "subjective_mem_lifecycle_receipt"
    )
    reference = selector["authority_binding"]["authorization_ref"]
    authorization_kind = {
        "formation_decision": "subjective_mem_decision",
        "lifecycle_transition": "subjective_mem_lifecycle_transition",
    }[reference["authority_kind"]]
    with store.transaction(SPACE) as transaction:
        result = transaction.commit(
            transaction_id="rt1d-r4-seed",
            records=(
                (
                    receipt_kind,
                    selector["authority_binding"]["current_receipt_id"],
                    entry.current_receipt_record,
                ),
                (
                    authorization_kind,
                    reference["authority_id"],
                    entry.authorization_record,
                ),
            ),
            logs=(("subjective_mem_current_state", selector["memory_state_id"], (selector,)),),
        )
    assert result.status == "created"
    return store


def _seed_cutover_chain(root: Path, binding, last_state: str) -> None:
    """Seed one exact predecessor-linked chain ending at ``last_state``."""

    body = binding.to_dict()
    digest = canonical_digest(body)
    records: list[dict] = []
    previous: dict | None = None
    for state in FORWARD_STATES[: FORWARD_STATES.index(last_state) + 1]:
        record = {
            "schema_version": CUTOVER_SCHEMA_VERSION,
            "state": state,
            "predecessor_state": previous["state"] if previous else None,
            "predecessor_digest": previous["record_digest"] if previous else None,
            "binding": body,
            "binding_digest": digest,
        }
        record["record_digest"] = canonical_digest(record)
        records.append(record)
        previous = record
    store = EvidenceRecordStore(str(root))
    with store.transaction(binding.evidence_space_id) as transaction:
        result = transaction.commit(
            transaction_id=f"rt1d-r4-chain-{last_state}",
            records=(),
            logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, tuple(records)),),
        )
    assert result.status == "created"


def _subjective_environment(tmp_path: Path, last_state: str):
    """One deployment whose durable chain ends exactly at ``last_state``."""

    revision, page, _committed, source = _one_active()
    workspace_root = _character_workspace(tmp_path)
    (workspace_root / CHARACTER / _MEMORY_PAGE).parent.mkdir(parents=True, exist_ok=True)
    (workspace_root / CHARACTER / _MEMORY_PAGE).write_bytes(page)
    evidence_root = tmp_path / "evidence"
    cutover_root = tmp_path / "cutover"
    projection_root = tmp_path / "projection"
    projection_root.mkdir()
    _seed_subjective_evidence(evidence_root, source)
    binding = SubjectiveMemRetrievalCutoverBinding(
        schema_version=CUTOVER_SCHEMA_VERSION,
        authority_domain=CUTOVER_AUTHORITY_DOMAIN,
        transferred_scope=CUTOVER_TRANSFERRED_SCOPE,
        evidence_space_id=SPACE,
        deployment_id="deployment-1",
        scope_id="ordinary-memory",
        policy_revision_id="policy-1",
        readiness_id="ready-1",
        bootstrap_main_sha="a" * 64,
        resulting_main_sha="b" * 64,
        projection_generation_id=source.projection_generation_id,
        projection_source_digest=source.source_snapshot_digest,
    )
    _seed_cutover_chain(cutover_root, binding, last_state)
    payload = yaml.safe_load(Path("config.example.yaml").read_text())
    payload.update(
        {
            "subjective_mem_retrieval_cutover_mode": "subjective_only",
            "subjective_mem_retrieval_cutover_store_root": str(cutover_root),
            "subjective_mem_retrieval_cutover_evidence_space_id": SPACE,
            "subjective_mem_retrieval_cutover_deployment_id": "deployment-1",
            "subjective_mem_retrieval_cutover_scope_id": "ordinary-memory",
            "subjective_mem_retrieval_cutover_bootstrap_main_sha": "a" * 64,
            "subjective_mem_retrieval_cutover_resulting_main_sha": "b" * 64,
            "subjective_mem_retrieval_cutover_policy_revision_id": "policy-1",
            "subjective_mem_retrieval_cutover_projection_generation_id": (
                source.projection_generation_id
            ),
            "subjective_mem_retrieval_cutover_projection_source_digest": (
                source.source_snapshot_digest
            ),
            "subjective_mem_retrieval_cutover_readiness_id": "ready-1",
            "subjective_mem_retrieval_projection_root": str(projection_root),
            "evidence_data_root": str(evidence_root),
            "subjective_mem_workspace_root": str(workspace_root),
        }
    )
    config = RelayLMConfig.model_validate(payload)
    route = resolve_route(config, next(iter(config.model_routes)))
    return config, replace(route, character_id=CHARACTER), source, revision, projection_root


def _usage_event_records(config) -> list[Path]:
    """Every durable content-free usage-event record this deployment persisted."""

    directory = (
        Path(str(config.evidence_data_root))
        / SPACE
        / "records"
        / SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND
    )
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def _run_stage(config, route):
    return run_relaymem_retrieval_stage(
        config=config,
        route=route,
        relaymem_configured_store_root=None,
        relayscn_scene_policy_artifact=None,
        relayint_intent_artifact=None,
        messages=[{"role": "user", "content": "what do you remember"}],
        primary_reader_decision=(
            resolve_subjective_mem_retrieval_primary_reader_decision(config)
        ),
        request_correlation="run-rt1d-r4",
    )


def test_runtime_projection_acquires_the_exact_source_and_installs_one_bundle(
    tmp_path: Path,
) -> None:
    config, route, source, _revision, projection_root = _subjective_environment(
        tmp_path, "transfer_receipt_finalized"
    )
    spec = SubjectiveMemRetrievalRuntimeProjectionSpec(
        evidence_space_id=SPACE,
        workspace_root=str(config.subjective_mem_workspace_root),
        projection_root=str(projection_root),
        character_id=CHARACTER,
        query_plan_digest="c" * 64,
        request_correlation_digest="d" * 64,
        memory_kinds=("episodic", "semantic"),
        candidate_limit=8,
        token_budget=256,
    )
    store = EvidenceRecordStore(str(config.evidence_data_root))
    acquired, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    assert reasons == () and acquired is not None
    assert acquired.source == source
    assert acquired.projection.manifest.projection_generation_id == (
        source.projection_generation_id
    )
    assert acquired.canonical_page_images
    bundle = projection_root / PROJECTION_BUNDLE_FILENAME
    assert bundle.exists()

    # A second acquisition exact-verifies the installed bundle rather than
    # rewriting it, and returns the same immutable value.
    again, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    assert reasons == () and again == acquired

    # A foreign bundle is never repaired, replaced, or read as trusted.
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    payload["manifest"]["source_snapshot_digest"] = "e" * 64
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    drifted, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    assert drifted is None and reasons
    assert json.loads(bundle.read_text(encoding="utf-8")) == payload
    assert "runtime_private_evidence_omitted=True" in repr(acquired)


def test_subjective_only_serves_subjective_and_finalizes_usage_before_admission(
    tmp_path: Path,
) -> None:
    config, route, _source, revision, _root = _subjective_environment(
        tmp_path, "transfer_receipt_finalized"
    )
    _diagnostics, artifact = _run_stage(config, route)
    assert artifact[ORDINARY_MEMORY_AUTHORITY_KEY] == "subjective_only"
    assert "primary_recall_runtime" not in artifact
    runtime = artifact[SUBJECTIVE_RUNTIME_KEY]
    assert runtime["usage_event_recorded"] is True
    assert runtime["primary_fallback_performed"] is False
    assert runtime["blocked_reason_classes"] == []
    assert [item["memory_id"] for item in runtime["selected_memories"]] == [
        revision.memory_id
    ]
    assert _ordinary_selected_memories(artifact) == runtime["selected_memories"]

    # The content-free usage event is durable before the evidence is released.
    store = EvidenceRecordStore(str(config.evidence_data_root))
    with store.transaction(SPACE) as transaction:
        inventory = transaction.list_logs(log_kind="subjective_mem_current_state", limit=8)
    assert len(inventory) == 1
    events = _usage_event_records(config)
    assert len(events) == 1
    body = json.loads(events[0].read_text(encoding="utf-8"))
    assert body["memory_id"] == revision.memory_id
    assert "fact_text" not in body and "grounded_content" not in body


def test_subjective_replay_admits_the_same_evidence_without_a_second_usage_pair(
    tmp_path: Path,
) -> None:
    config, route, _source, _revision, _root = _subjective_environment(
        tmp_path, "transfer_receipt_finalized"
    )
    first = _run_stage(config, route)[1][SUBJECTIVE_RUNTIME_KEY]
    second = _run_stage(config, route)[1][SUBJECTIVE_RUNTIME_KEY]
    assert first["selected_memories"] == second["selected_memories"]
    assert len(_usage_event_records(config)) == 1


@pytest.mark.parametrize(
    "last_state",
    ["primary_reader_fenced", "primary_writer_fenced", "subjective_generation_bound"],
)
def test_between_the_reader_fence_and_the_receipt_neither_authority_serves(
    tmp_path: Path, last_state: str
) -> None:
    config, route, _source, _revision, _root = _subjective_environment(
        tmp_path, last_state
    )
    _diagnostics, artifact = _run_stage(config, route)
    assert artifact[ORDINARY_MEMORY_AUTHORITY_KEY] == "neither"
    assert "primary_recall_runtime" not in artifact
    assert SUBJECTIVE_RUNTIME_KEY not in artifact
    assert _ordinary_selected_memories(artifact) == []


def test_source_drift_after_activation_fails_closed_without_primary_fallback(
    tmp_path: Path,
) -> None:
    config, route, source, _revision, _root = _subjective_environment(
        tmp_path, "transfer_receipt_finalized"
    )
    # The canonical source moves on after activation; the finalized receipt still
    # binds only the exact generation it was finalized with.
    selector = source.entries[0].current_selector_record
    (
        Path(str(config.evidence_data_root))
        / SPACE
        / "logs"
        / "subjective_mem_current_state"
        / f"{selector['memory_state_id']}.json"
    ).unlink()
    _diagnostics, artifact = _run_stage(config, route)
    assert artifact[ORDINARY_MEMORY_AUTHORITY_KEY] == "subjective_only"
    runtime = artifact[SUBJECTIVE_RUNTIME_KEY]
    assert runtime["selected_memories"] == []
    assert runtime["usage_event_recorded"] is False
    assert runtime["blocked_reason_classes"] == ["subjective_mem_retrieval_source_drift"]
    assert "primary_recall_runtime" not in artifact
    assert _ordinary_selected_memories(artifact) == []


def test_a_missing_or_tampered_reader_decision_releases_no_memory(tmp_path: Path) -> None:
    config, route, _source, _revision, _root = _subjective_environment(
        tmp_path, "transfer_receipt_finalized"
    )
    for decision in (None, "subjective_only", object()):
        _diagnostics, artifact = run_relaymem_retrieval_stage(
            config=config,
            route=route,
            relaymem_configured_store_root=None,
            relayscn_scene_policy_artifact=None,
            relayint_intent_artifact=None,
            messages=[{"role": "user", "content": "hello"}],
            primary_reader_decision=decision,
            request_correlation="run-rt1d-r4",
        )
        assert artifact[ORDINARY_MEMORY_AUTHORITY_KEY] == "neither"
        assert _ordinary_selected_memories(artifact) == []
