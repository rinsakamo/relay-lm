"""LC-1E Subjective MEM Consolidate runtime tests."""
from __future__ import annotations

import inspect
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.subjective_mem.models import SUBJECTIVE_MEM_REVISION_SCHEMA, SubjectiveMemStrength
from relaylm.subjective_mem.consolidate import (
    CONSOLIDATE_AUTHORIZATION_CLASS,
    CONSOLIDATE_POLICY_REVISION,
    CONSOLIDATE_REASON_CATEGORY,
    SubjectiveMemConsolidateBoundary,
    SubjectiveMemConsolidateProposal,
)
import relaylm.subjective_mem.consolidate_runtime as consolidate_runtime
from relaylm.subjective_mem.consolidate_runtime import consolidate_subjective_mem
from relaylm.subjective_mem.forget import (
    SubjectiveMemForgetBoundary,
    SubjectiveMemForgetProposal,
)
from relaylm.subjective_mem.lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    SubjectiveMemCorrectProposal,
    SubjectiveMemCorrectionBoundary,
)
from relaylm.subjective_mem.lifecycle_runtime import correct_subjective_mem
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem.pin_runtime import pin_subjective_mem
from relaylm.subjective_mem.forget_runtime import forget_subjective_mem
from test_subjective_mem_commit_runtime import _commit, _make_workspace
from test_subjective_mem_lifecycle_runtime import _correct, lifecycle_env  # noqa: F401
from test_subjective_mem_pin_runtime import _proposal as _pin_proposal
from relaylm.config import RelayLMConfig
from test_subjective_mem_runtime import (
    BASE_CONFIG,
    NOW,
    _asm_ready,
    _character,
    _create,
)

_SELECTOR_LOG = "subjective_mem_current_state"
_PROHIBITED_RECORD_KINDS = (
    "subjective_mem_forget_tombstone",
    "subjective_mem_forget_tombstone_release",
    "subjective_mem_relation",
    "subjective_mem_merge",
    "subjective_mem_supersession",
    "subjective_mem_usage_event",
    "relaymem_primary_mem",
    "subjective_mem_retrieval",
)


_GATE_TRIPLES = {
    "disabled": (False, True, False),
    "dry_run": (True, True, False),
    "apply": (True, False, True),
}


def _gate_fields(gate: str, mode: str) -> dict[str, bool]:
    enabled, dry_run_only, apply_enabled = _GATE_TRIPLES[mode]
    return {
        f"subjective_mem_{gate}_enabled": enabled,
        f"subjective_mem_{gate}_dry_run_only": dry_run_only,
        f"subjective_mem_{gate}_apply_enabled": apply_enabled,
    }


def _lifecycle_config(workspace: Path, *, lifecycle: str = "apply", commit: str | None = None):
    """Build a configuration the repository config authority itself accepts.

    The lifecycle gate depends on the lower Subjective MEM commit, create, and
    shared-assessment gates, so every coherent mode is produced through
    ``RelayLMConfig.model_validate`` rather than an unvalidated ``model_copy``.
    """

    commit = commit or ("apply" if lifecycle == "apply" else "dry_run")
    lower = "apply" if commit == "apply" else "dry_run"
    payload = {
        **BASE_CONFIG,
        "evidence_data_root": str((workspace.parent / "evidence").resolve()),
        "subjective_mem_workspace_root": str(workspace),
        **_gate_fields("lifecycle", lifecycle),
        **_gate_fields("commit", commit),
    }
    if lifecycle == "disabled" and commit == "disabled":
        payload.update(_gate_fields("create", "disabled"))
    else:
        payload.update(_gate_fields("create", lower))
        payload.update({
            "shared_assessment_enabled": True,
            "shared_assessment_dry_run_only": lower != "apply",
            "shared_assessment_apply_enabled": lower == "apply",
        })
    return RelayLMConfig.model_validate(payload)


def _incoherent_config(workspace: Path, **overrides: object):
    """Synthesize a gate state the config authority would reject.

    ``model_copy`` bypasses validation on purpose here: these configurations
    can only reach the runtime if some future caller constructs them outside
    the validated authority, and the runtime must still fail closed.
    """

    return _lifecycle_config(workspace, lifecycle="apply").model_copy(update=overrides)


@pytest.fixture()
def consolidate_env(tmp_path: Path):
    workspace = _make_workspace(tmp_path)
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    captured, assessment_revision, assessment_state = _asm_ready(store)
    sm1 = _create(store, captured, assessment_revision, assessment_state)
    env = {
        "store": store,
        "captured": captured,
        "workspace": workspace,
        "workspace_root": workspace,
        "config": _lifecycle_config(workspace),
        "authority": _character(),
        "assessment_revision": assessment_revision,
        "assessment_state": assessment_state,
    }
    st1 = _commit({**env, "sm1": sm1})
    assert st1.status == "committed" and st1.current_state is not None
    env.update({
        "st1": st1,
        "page_path": workspace / "char1/memory/episodes/subjective-mem-v1.md",
    })
    return env


def _current_page(env):
    page, reasons = parse_subjective_mem_page_bytes(env["page_path"].read_bytes())
    assert page is not None and not reasons
    return page


def _record(env, kind: str, record_id: str):
    return env["store"].read_record(
        evidence_space_id=env["captured"].evidence_space_id,
        record_kind=kind,
        record_id=record_id,
    )


def _selector_events(env, selector_id: str):
    return env["store"].read_log(
        evidence_space_id=env["captured"].evidence_space_id,
        log_kind=_SELECTOR_LOG,
        key=selector_id,
    )


def _binding(env, state):
    """Read the exact current page block, receipt, and authorization for one selector."""

    page = _current_page(env)
    block = next(
        item
        for item in page.blocks
        if item.revision.memory_id == state.memory_id
        and item.revision.memory_revision == state.current_revision
    )
    if state.current_revision == 1:
        receipt_model = env["st1"].receipt
        assert receipt_model is not None
        receipt_id, receipt = receipt_model.receipt_id, receipt_model.to_dict()
        authorization_kind = "subjective_mem_decision"
    else:
        assert state.current_receipt_id is not None
        receipt_id = state.current_receipt_id
        receipt = _record(env, "subjective_mem_lifecycle_receipt", receipt_id)
        authorization_kind = "subjective_mem_lifecycle_transition"
    assert isinstance(receipt, dict)
    authorization = _record(env, authorization_kind, block.revision.authorization_id)
    assert isinstance(authorization, dict)
    return page, block, receipt_id, receipt, authorization_kind, authorization


def _shared_expectations(env, state) -> dict[str, object]:
    page, block, receipt_id, receipt, _kind, _authorization = _binding(env, state)
    revision = block.revision
    return {
        "expected_memory_id": state.memory_id,
        "expected_current_revision": state.current_revision,
        "expected_lifecycle_state": state.lifecycle_state,
        "expected_mutation_state": "none",
        "expected_page_id": page.page_id,
        "expected_relative_path": "memory/episodes/subjective-mem-v1.md",
        "expected_block_id": block.block_id,
        "expected_page_digest": page.page_digest,
        "expected_current_selector_id": state.memory_state_id,
        "expected_current_selector_digest": canonical_digest(state.to_dict()),
        "expected_current_receipt_id": receipt_id,
        "expected_current_receipt_digest": receipt["receipt_digest"],
        "expected_memory_kind": revision.memory_kind,
        "expected_formation_stage": revision.formation_stage,
        "expected_scope_binding_digest": canonical_digest(revision.scope_binding.to_dict()),
        "expected_formation_snapshot_digest": canonical_digest(
            revision.formation_snapshot.to_dict()
        ),
        "expected_revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
        "expected_page_schema": PAGE_SCHEMA,
        "expected_block_schema": LIFECYCLE_BLOCK_SCHEMA,
        "expected_renderer_revision": RENDERER_REVISION,
        "expected_partition_revision": PAGE_PARTITION_REVISION,
        "expected_platform_revision": PLATFORM_REVISION,
    }


def _proposal(env, *, state=None, **changes) -> SubjectiveMemConsolidateProposal:
    state = state or env["st1"].current_state
    assert state is not None
    _page, block, _receipt_id, _receipt, kind, authorization = _binding(env, state)
    base = SubjectiveMemConsolidateProposal(
        **_shared_expectations(env, state),  # type: ignore[arg-type]
        expected_current_authorization_kind=kind,
        expected_current_authorization_id=block.revision.authorization_id,
        expected_current_authorization_digest=canonical_digest(authorization),
        expected_strength_digest=canonical_digest(block.revision.strength.to_dict()),
        authorization_class=CONSOLIDATE_AUTHORIZATION_CLASS,
        authorization_id="relaymem-consolidation-authorization-1",
        reason_category=CONSOLIDATE_REASON_CATEGORY,
        policy_revision=CONSOLIDATE_POLICY_REVISION,
        boundary=SubjectiveMemConsolidateBoundary(),
    )
    return replace(base, **changes)


def _forget_proposal(env, *, state=None) -> SubjectiveMemForgetProposal:
    state = state or env["st1"].current_state
    assert state is not None
    return SubjectiveMemForgetProposal(
        **_shared_expectations(env, state),  # type: ignore[arg-type]
        authorization_class="user_management",
        authorization_id="user-forget-authorization-1",
        reason_category="user_requested_forget",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemForgetBoundary(),
    )


def _correct_after(env, state):
    proposal = SubjectiveMemCorrectProposal(
        **_shared_expectations(env, state),  # type: ignore[arg-type]
        assessment_revision=env["assessment_revision"],
        assessment_current_state=env["assessment_state"],
        corrected_grounded_content=env["assessment_revision"].supported_content,
        corrected_subjective_meaning="I now remember this more precisely.",
        corrected_strength=SubjectiveMemStrength(
            grounded_confidence=0.8,
            subjective_conviction=0.6,
            salience="medium",
            reinforcement_count=0,
            strength_basis="subjective_interpretation",
        ),
        authorization_class="user_management",
        authorization_id="user-correction-authorization-1",
        reason_category="user_reported_inaccuracy",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemCorrectionBoundary(),
    )
    return correct_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace"]),
        operation_idempotency_key="correct-after-consolidate",
        proposal=proposal,
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=6),
        observed_at=NOW + timedelta(seconds=7),
    )


def _call(env, proposal, *, key="lc1e-consolidate", seconds=2, apply=True, fault=None,
          config=None):
    return consolidate_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=config or env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace"]),
        operation_idempotency_key=key,
        proposal=proposal,
        apply_enabled=apply,
        committed_at=NOW + timedelta(seconds=seconds),
        observed_at=NOW + timedelta(seconds=seconds + 1),
        fault_injector=fault,
    )


def _semantic_projection(revision):
    raw = revision.to_dict()
    for key in (
        "memory_revision",
        "formation_stage",
        "predecessor_revision_or_null",
        "authorization_ref",
        "created_at",
    ):
        raw.pop(key)
    return raw


# --- exact lifecycle and lower-commit gate --------------------------------


def _fingerprint(env) -> dict[str, object]:
    """Capture every durable surface an apply would have to touch."""

    root = env["store"].root
    state = env["st1"].current_state
    assert state is not None
    return {
        "page": env["page_path"].read_bytes(),
        "private": sorted(
            path.relative_to(env["workspace"]).as_posix()
            for path in (env["workspace"] / "char1/.relaylm").rglob("*")
            if path.is_file()
        ),
        "claims": sorted(str(path) for path in root.rglob("*lifecycle_claim*")),
        "intents": sorted(str(path) for path in root.rglob("*lifecycle_intent*")),
        "transitions": sorted(str(path) for path in root.rglob("*lifecycle_transition*")),
        "receipts": sorted(str(path) for path in root.rglob("*lifecycle_receipt*")),
        "results": sorted(str(path) for path in root.rglob("*idempotency_result*")),
        "selector": _selector_events(env, state.memory_state_id),
    }


def _assert_no_write(env, before: dict[str, object]) -> None:
    after = _fingerprint(env)
    for surface in before:
        assert after[surface] == before[surface], surface
    assert after["claims"] == [] and after["intents"] == []
    assert after["transitions"] == [] and after["receipts"] == []


def test_lifecycle_disabled_writes_nothing_for_either_caller_mode(consolidate_env) -> None:
    disabled = _lifecycle_config(
        consolidate_env["workspace"], lifecycle="disabled", commit="disabled"
    )
    for apply_requested in (False, True):
        before = _fingerprint(consolidate_env)
        result = _call(
            consolidate_env,
            _proposal(consolidate_env),
            config=disabled,
            apply=apply_requested,
            key=f"disabled-{apply_requested}",
        )
        assert result.status == "disabled", apply_requested
        assert result.blocked_reasons == (
            "subjective_mem_consolidate_lifecycle_disabled",
        )
        _assert_no_write(consolidate_env, before)


def test_lifecycle_dry_run_cannot_be_escalated_by_the_caller(consolidate_env) -> None:
    dry_run = _lifecycle_config(consolidate_env["workspace"], lifecycle="dry_run")

    before = _fingerprint(consolidate_env)
    ready = _call(consolidate_env, _proposal(consolidate_env), config=dry_run, apply=False)
    assert ready.status == "dry_run_ready", ready.blocked_reasons
    assert ready.recovery_outcome == "new_intent_ready"
    _assert_no_write(consolidate_env, before)

    escalated = _call(
        consolidate_env,
        _proposal(consolidate_env),
        config=dry_run,
        apply=True,
        key="dry-run-escalation",
    )
    assert escalated.status == "fail_closed"
    assert escalated.blocked_reasons == (
        "subjective_mem_consolidate_apply_not_configured",
    )
    _assert_no_write(consolidate_env, before)


def test_lifecycle_apply_requires_the_exact_lower_commit_apply_gate(consolidate_env) -> None:
    cases = {
        "commit_disabled": (
            _incoherent_config(
                consolidate_env["workspace"], **_gate_fields("commit", "disabled")
            ),
            "subjective_mem_consolidate_commit_gate_not_enabled",
        ),
        "commit_dry_run": (
            _incoherent_config(
                consolidate_env["workspace"], **_gate_fields("commit", "dry_run")
            ),
            "subjective_mem_consolidate_commit_gate_not_apply_enabled",
        ),
    }
    for label, (config, reason) in cases.items():
        before = _fingerprint(consolidate_env)
        result = _call(
            consolidate_env, _proposal(consolidate_env), config=config, key=label
        )
        assert result.status == "fail_closed", label
        assert result.blocked_reasons == (reason,), label
        _assert_no_write(consolidate_env, before)


def test_malformed_and_incoherent_gate_values_fail_closed(consolidate_env) -> None:
    workspace = consolidate_env["workspace"]
    cases = {
        "lifecycle_non_boolean": _incoherent_config(
            workspace, subjective_mem_lifecycle_dry_run_only="no"
        ),
        "lifecycle_unsupported_triple": _incoherent_config(
            workspace, subjective_mem_lifecycle_dry_run_only=True
        ),
        "commit_non_boolean": _incoherent_config(
            workspace, subjective_mem_commit_apply_enabled=1
        ),
        "commit_unsupported_triple": _incoherent_config(
            workspace, subjective_mem_commit_enabled=False
        ),
        "dependency_mismatch": _incoherent_config(
            workspace,
            **_gate_fields("lifecycle", "dry_run"),
            **_gate_fields("commit", "disabled"),
        ),
    }
    expected = {
        "lifecycle_non_boolean": "subjective_mem_consolidate_gate_configuration_invalid",
        "lifecycle_unsupported_triple": "subjective_mem_consolidate_gate_configuration_invalid",
        "commit_non_boolean": "subjective_mem_consolidate_gate_configuration_invalid",
        "commit_unsupported_triple": "subjective_mem_consolidate_gate_configuration_invalid",
        "dependency_mismatch": "subjective_mem_consolidate_commit_gate_not_enabled",
    }
    for label, config in cases.items():
        before = _fingerprint(consolidate_env)
        result = _call(
            consolidate_env, _proposal(consolidate_env), config=config, key=label
        )
        assert result.status == "fail_closed", label
        assert result.blocked_reasons == (expected[label],), (label, result.blocked_reasons)
        _assert_no_write(consolidate_env, before)


def test_configured_apply_with_caller_dry_run_is_write_free_and_content_free(
    consolidate_env,
) -> None:
    before = _fingerprint(consolidate_env)
    result = _call(consolidate_env, _proposal(consolidate_env), apply=False)
    assert result.status == "dry_run_ready", result.blocked_reasons
    assert result.recovery_outcome == "new_intent_ready"
    assert result.from_formation_stage == "primary"
    assert result.to_formation_stage == "secondary"
    _assert_no_write(consolidate_env, before)
    projection = result.to_log_dict()
    assert projection["content_free"] is True
    assert all(
        value not in json.dumps(projection)
        for value in ("I felt relieved", "safe again", str(consolidate_env["workspace"]))
    )


def test_exact_lifecycle_and_commit_apply_permits_publication(consolidate_env) -> None:
    config = consolidate_env["config"]
    assert (
        config.subjective_mem_lifecycle_enabled,
        config.subjective_mem_lifecycle_dry_run_only,
        config.subjective_mem_lifecycle_apply_enabled,
    ) == (True, False, True)
    assert (
        config.subjective_mem_commit_enabled,
        config.subjective_mem_commit_dry_run_only,
        config.subjective_mem_commit_apply_enabled,
    ) == (True, False, True)
    result = _call(consolidate_env, _proposal(consolidate_env), apply=True)
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 2
    assert _current_page(consolidate_env).blocks[-1].revision.formation_stage == "secondary"


def test_runtime_declares_no_second_gate_authority() -> None:
    source = inspect.getsource(consolidate_runtime)
    assert "resolve_subjective_mem_lifecycle_gate" not in source
    assert "SubjectiveMemLifecycleGate" not in source
    assert source.count("_GATE_MODES") == 2
    assert source.count("def _gate_mode_or_errors(") == 1


# --- exact primary -> secondary publication ------------------------------


def test_revision_one_st1_primary_is_consolidated_in_place(consolidate_env) -> None:
    original = _current_page(consolidate_env).blocks[0].revision
    assert original.memory_revision == 1
    assert original.authorization_kind == "formation_decision"
    assert original.formation_stage == "primary"

    result = _call(consolidate_env, _proposal(consolidate_env))
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    state = result.current_state
    assert (state.current_revision, state.lifecycle_state) == (2, "active")
    assert state.mutation_state == "none" and state.retrieval_eligible is True
    assert state.authorization_kind == "lifecycle_transition"
    assert state.authorization_id == result.transition_id
    assert state.current_receipt_id == result.receipt_id

    page = _current_page(consolidate_env)
    assert [item.revision.memory_revision for item in page.blocks] == [1, 2]
    successor = page.blocks[-1].revision
    assert successor.formation_stage == "secondary"
    assert successor.lifecycle_state == "active"
    assert successor.retrieval_visible is True
    assert successor.predecessor_revision_or_null == 1
    assert successor.authorization_kind == "lifecycle_transition"
    assert _semantic_projection(successor) == _semantic_projection(original)
    assert successor.strength.to_dict() == original.strength.to_dict()
    assert successor.scope_binding.to_dict() == original.scope_binding.to_dict()
    assert successor.formation_snapshot.to_dict() == original.formation_snapshot.to_dict()
    assert successor.memory_kind == original.memory_kind
    assert successor.assessment_id == original.assessment_id
    assert successor.assessment_revision == original.assessment_revision


def test_same_page_partition_is_preserved(consolidate_env) -> None:
    before = _current_page(consolidate_env)
    assert _call(consolidate_env, _proposal(consolidate_env)).status == "committed"
    after = _current_page(consolidate_env)
    assert (after.page_id, after.partition) == (before.page_id, before.partition)
    assert sorted(
        path.relative_to(consolidate_env["workspace"]).as_posix()
        for path in (consolidate_env["workspace"] / "char1/memory").rglob("*.md")
    ) == ["char1/memory/episodes/subjective-mem-v1.md"]
    assert {item.revision.memory_id for item in after.blocks} == {
        before.blocks[0].revision.memory_id
    }


def test_later_active_primary_lifecycle_predecessor_is_consolidated(lifecycle_env) -> None:
    corrected = _correct(lifecycle_env)
    assert corrected.status == "committed", corrected.blocked_reasons
    assert corrected.current_state is not None
    env = {
        **lifecycle_env,
        "workspace": lifecycle_env["workspace_root"],
        "config": _lifecycle_config(Path(lifecycle_env["workspace_root"])),
    }
    predecessor = _current_page(env).blocks[-1].revision
    assert predecessor.memory_revision == 2
    assert predecessor.authorization_kind == "lifecycle_transition"
    assert predecessor.formation_stage == "primary"

    result = _call(
        env,
        _proposal(env, state=corrected.current_state),
        key="consolidate-after-correct",
        seconds=6,
    )
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 3
    successor = _current_page(env).blocks[-1].revision
    assert successor.formation_stage == "secondary"
    assert successor.subjective_meaning == predecessor.subjective_meaning


def test_final_transition_and_receipt_carry_exact_policy_authority(consolidate_env) -> None:
    result = _call(consolidate_env, _proposal(consolidate_env))
    assert result.status == "committed" and result.transition_id is not None
    transition = _record(
        consolidate_env, "subjective_mem_lifecycle_transition", result.transition_id
    )
    assert isinstance(transition, dict)
    assert transition["operation"] == "consolidate"
    assert transition["from_lifecycle_state"] == "active"
    assert transition["to_lifecycle_state"] == "active"
    assert transition["from_formation_stage"] == "primary"
    assert transition["to_formation_stage"] == "secondary"
    assert transition["authorized_by"] == CONSOLIDATE_AUTHORIZATION_CLASS

    assert result.receipt_id is not None
    receipt = _record(
        consolidate_env, "subjective_mem_lifecycle_receipt", result.receipt_id
    )
    assert isinstance(receipt, dict)
    assert receipt["authorization_class"] == CONSOLIDATE_AUTHORIZATION_CLASS
    assert receipt["authorization_id"] == "relaymem-consolidation-authorization-1"
    assert receipt["reason_category"] == CONSOLIDATE_REASON_CATEGORY
    assert receipt["policy_revision"] == CONSOLIDATE_POLICY_REVISION
    assert receipt["projection_state"] == "rebuild_required"
    assert receipt["ordinary_retrieval_wired"] is False


def test_no_prohibited_record_kind_or_second_memory_is_created(consolidate_env) -> None:
    proposal = _proposal(consolidate_env)
    assert _call(consolidate_env, proposal).status == "committed"
    space = consolidate_env["store"].root / consolidate_env["captured"].evidence_space_id
    kinds = {path.name for path in (space / "records").iterdir()}
    assert not kinds.intersection(_PROHIBITED_RECORD_KINDS)
    logs = [
        key
        for key in (space / "logs" / _SELECTOR_LOG).iterdir()
        if key.is_file()
    ]
    assert len(logs) == 1
    events = _selector_events(consolidate_env, proposal.expected_current_selector_id)
    assert isinstance(events, list) and len(events) == 1
    assert events[0]["current_revision"] == 2
    assert events[0]["retrieval_eligible"] is True


# --- replay, idempotency, and first writer -------------------------------


def test_exact_replay_appends_no_revision(consolidate_env) -> None:
    proposal = _proposal(consolidate_env)
    first = _call(consolidate_env, proposal)
    page_after_first = consolidate_env["page_path"].read_bytes()
    second = _call(consolidate_env, proposal)
    assert first.status == "committed", first.blocked_reasons
    assert second.status == "duplicate_finalized", second.blocked_reasons
    assert second.recovery_outcome == "exact_replay"
    assert second.transition_id == first.transition_id
    assert second.receipt_id == first.receipt_id
    assert consolidate_env["page_path"].read_bytes() == page_after_first
    assert [item.revision.memory_revision for item in _current_page(consolidate_env).blocks] == [1, 2]


def test_changed_proposal_under_one_slot_conflicts(consolidate_env) -> None:
    assert _call(consolidate_env, _proposal(consolidate_env), key="shared").status == "committed"
    conflict = _call(
        consolidate_env,
        _proposal(consolidate_env, authorization_id="relaymem-consolidation-authorization-2"),
        key="shared",
        seconds=4,
    )
    assert conflict.status == "integrity_conflict"
    assert "subjective_mem_lifecycle_idempotency_conflict" in conflict.blocked_reasons
    assert [item.revision.memory_revision for item in _current_page(consolidate_env).blocks] == [1, 2]


def test_changed_operation_time_under_one_slot_conflicts(consolidate_env) -> None:
    proposal = _proposal(consolidate_env)
    assert _call(consolidate_env, proposal, key="slot", seconds=2).status == "committed"
    conflict = _call(consolidate_env, proposal, key="slot", seconds=8)
    assert conflict.status == "integrity_conflict"
    assert "subjective_mem_lifecycle_idempotency_conflict" in conflict.blocked_reasons


def test_first_writer_wins_and_the_loser_fails_closed(consolidate_env) -> None:
    proposal = _proposal(consolidate_env)
    assert _call(consolidate_env, proposal, key="winner").status == "committed"
    loser = _call(consolidate_env, proposal, key="loser", seconds=4)
    assert loser.status == "fail_closed"
    assert any(
        "selector" in reason or "revision" in reason for reason in loser.blocked_reasons
    )
    assert [item.revision.memory_revision for item in _current_page(consolidate_env).blocks] == [1, 2]


# --- rejection ------------------------------------------------------------


def test_already_secondary_predecessor_is_rejected(consolidate_env) -> None:
    first = _call(consolidate_env, _proposal(consolidate_env), key="first")
    assert first.status == "committed" and first.current_state is not None
    before = consolidate_env["page_path"].read_bytes()

    declared = _call(
        consolidate_env,
        _proposal(consolidate_env, state=first.current_state),
        key="second-declared",
        seconds=6,
    )
    assert declared.status == "fail_closed"
    assert (
        "subjective_mem_consolidate_formation_stage_invalid"
        in declared.blocked_reasons
    )

    forced = _call(
        consolidate_env,
        _proposal(
            consolidate_env, state=first.current_state, expected_formation_stage="primary"
        ),
        key="second-forced",
        seconds=8,
    )
    assert forced.status == "fail_closed"
    assert (
        "subjective_mem_consolidate_current_revision_invalid" in forced.blocked_reasons
    )
    assert consolidate_env["page_path"].read_bytes() == before


def test_pinned_and_hidden_lifecycle_predecessors_are_rejected(consolidate_env) -> None:
    pinned = pin_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=consolidate_env["authority"],
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="pin-before-consolidate",
        proposal=_pin_proposal(consolidate_env, "pin"),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
    )
    assert pinned.status == "committed", pinned.blocked_reasons
    assert pinned.current_state is not None
    before = consolidate_env["page_path"].read_bytes()
    result = _call(
        consolidate_env,
        _proposal(consolidate_env, state=pinned.current_state),
        key="consolidate-pinned",
        seconds=6,
    )
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_consolidate_transition_direction_invalid"
        in result.blocked_reasons
    )
    assert consolidate_env["page_path"].read_bytes() == before


def test_hidden_predecessor_is_rejected(consolidate_env) -> None:
    hidden = forget_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=consolidate_env["authority"],
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="forget-before-consolidate",
        proposal=_forget_proposal(consolidate_env),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
    )
    assert hidden.status == "committed", hidden.blocked_reasons
    assert hidden.current_state is not None
    before = consolidate_env["page_path"].read_bytes()
    result = _call(
        consolidate_env,
        _proposal(consolidate_env, state=hidden.current_state),
        key="consolidate-hidden",
        seconds=6,
    )
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_consolidate_transition_direction_invalid"
        in result.blocked_reasons
    )
    assert consolidate_env["page_path"].read_bytes() == before


def test_stale_and_wrong_binding_proposals_fail_closed(consolidate_env) -> None:
    before = consolidate_env["page_path"].read_bytes()
    other_digest = "9" * 64
    invalid_revision = "subjective_mem_consolidate_current_revision_invalid"
    cases = {
        "stale_revision": (
            {"expected_current_revision": 2},
            "subjective_mem_consolidate_current_selector_not_exact",
        ),
        "wrong_selector": (
            {"expected_current_selector_digest": other_digest},
            "subjective_mem_consolidate_current_selector_not_exact",
        ),
        "wrong_receipt": (
            {"expected_current_receipt_digest": other_digest},
            "subjective_mem_lifecycle_current_receipt_not_exact",
        ),
        "wrong_authorization_kind": (
            {"expected_current_authorization_kind": "subjective_mem_lifecycle_transition"},
            invalid_revision,
        ),
        "wrong_authorization_id": (
            {"expected_current_authorization_id": "decision-x"},
            invalid_revision,
        ),
        "wrong_authorization_digest": (
            {"expected_current_authorization_digest": other_digest},
            invalid_revision,
        ),
        "wrong_page": (
            {"expected_page_id": "smpage_" + "0" * 64},
            "subjective_mem_consolidate_page_identity_mismatch",
        ),
        "wrong_block": (
            {"expected_block_id": "smblock_" + "0" * 64},
            "subjective_mem_consolidate_current_revision_not_exact",
        ),
        "wrong_strength": ({"expected_strength_digest": other_digest}, invalid_revision),
        "wrong_scope": ({"expected_scope_binding_digest": other_digest}, invalid_revision),
        "wrong_snapshot": (
            {"expected_formation_snapshot_digest": other_digest},
            invalid_revision,
        ),
        "wrong_memory_kind": (
            {"expected_memory_kind": "semantic"},
            "subjective_mem_consolidate_page_identity_mismatch",
        ),
        "wrong_schema": (
            {"expected_block_schema": PAGE_SCHEMA},
            "subjective_mem_consolidate_contract_revision_mismatch",
        ),
        "wrong_policy_revision": (
            {"policy_revision": "relaylm.subjective_mem_lifecycle_policy.v1"},
            "subjective_mem_consolidate_policy_revision_invalid",
        ),
        "wrong_authorization_class": (
            {"authorization_class": "user_management"},
            "subjective_mem_consolidate_authorization_class_invalid",
        ),
        "wrong_reason": (
            {"reason_category": "user_requested_consolidation"},
            "subjective_mem_consolidate_reason_category_invalid",
        ),
        "unsafe_path": (
            {"expected_relative_path": "../escape.md"},
            "subjective_mem_consolidate_relative_path_invalid",
        ),
    }
    for label, (change, reason) in cases.items():
        result = _call(consolidate_env, _proposal(consolidate_env, **change), key=label)
        assert result.status == "fail_closed", (label, result.status)
        assert reason in result.blocked_reasons, (label, result.blocked_reasons)
    assert consolidate_env["page_path"].read_bytes() == before
    assert not list(consolidate_env["store"].root.rglob("*lifecycle_receipt*"))


def test_wrong_character_authority_fails_closed(consolidate_env) -> None:
    before = consolidate_env["page_path"].read_bytes()
    result = consolidate_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=_character("char2"),
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="wrong-character",
        proposal=_proposal(consolidate_env),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
    )
    assert result.status == "fail_closed"
    assert consolidate_env["page_path"].read_bytes() == before


def test_future_and_non_monotonic_operation_time_fail_closed(consolidate_env) -> None:
    future = consolidate_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=consolidate_env["authority"],
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="future",
        proposal=_proposal(consolidate_env),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=90),
        observed_at=NOW + timedelta(seconds=5),
    )
    assert future.status == "fail_closed"
    assert "subjective_mem_consolidate_time_in_future" in future.blocked_reasons

    stale_clock = _call(consolidate_env, _proposal(consolidate_env), key="stale-clock", seconds=-60)
    assert stale_clock.status == "fail_closed"
    assert (
        "subjective_mem_consolidate_current_revision_invalid"
        in stale_clock.blocked_reasons
    )


# --- forward-only recovery ------------------------------------------------


@pytest.mark.parametrize(
    "stage,outcome",
    [
        ("after_intent_before_page", "pre_image_pending_publication"),
        ("after_page_before_receipt", "post_image_pending_receipt"),
    ],
)
def test_bounded_crash_recovers_forward(consolidate_env, stage: str, outcome: str) -> None:
    def crash(current: str) -> None:
        if current == stage:
            raise RuntimeError("simulated")

    proposal = _proposal(consolidate_env)
    first = _call(consolidate_env, proposal, fault=crash)
    assert first.status == "recovery_pending", first.blocked_reasons
    assert first.recovery_outcome == outcome
    assert first.current_state is not None
    assert first.current_state.mutation_state == "prepared"
    assert first.current_state.retrieval_eligible is False
    events = _selector_events(consolidate_env, proposal.expected_current_selector_id)
    assert isinstance(events, list) and events[0]["mutation_state"] == "prepared"
    assert events[0]["retrieval_eligible"] is False

    second = _call(consolidate_env, proposal)
    assert second.status == "committed", second.blocked_reasons
    assert second.current_state is not None
    assert second.current_state.current_revision == 2
    assert second.current_state.retrieval_eligible is True
    assert _current_page(consolidate_env).blocks[-1].revision.formation_stage == "secondary"


def test_foreign_image_is_preserved_and_fenced(consolidate_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    proposal = _proposal(consolidate_env)
    assert _call(consolidate_env, proposal, fault=crash).status == "recovery_pending"
    consolidate_env["page_path"].write_text("# foreign\n", encoding="utf-8")
    result = _call(consolidate_env, proposal)
    assert result.status == "recovery_required"
    assert result.recovery_outcome == "foreign_image"
    assert consolidate_env["page_path"].read_text(encoding="utf-8") == "# foreign\n"
    assert result.current_state is not None
    assert result.current_state.mutation_state == "recovery_required"


def test_final_records_without_the_exact_post_image_never_succeed(consolidate_env) -> None:
    proposal = _proposal(consolidate_env)
    assert _call(consolidate_env, proposal).status == "committed"
    consolidate_env["page_path"].write_text("# foreign\n", encoding="utf-8")
    replayed = _call(consolidate_env, proposal)
    assert replayed.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_receipt_without_exact_page"
        in replayed.blocked_reasons
    )
    assert consolidate_env["page_path"].read_text(encoding="utf-8") == "# foreign\n"


# --- later operations consume the consolidated Secondary predecessor ------


def test_consolidated_secondary_is_accepted_by_later_pin(consolidate_env) -> None:
    first = _call(consolidate_env, _proposal(consolidate_env))
    assert first.status == "committed" and first.current_state is not None
    pinned = pin_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=consolidate_env["authority"],
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="pin-after-consolidate",
        proposal=_pin_proposal(consolidate_env, "pin", state=first.current_state),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=6),
        observed_at=NOW + timedelta(seconds=7),
    )
    assert pinned.status == "committed", pinned.blocked_reasons
    successor = _current_page(consolidate_env).blocks[-1].revision
    assert successor.memory_revision == 3
    assert successor.lifecycle_state == "pinned"
    assert successor.formation_stage == "secondary"


def test_consolidated_secondary_is_accepted_by_later_forget(consolidate_env) -> None:
    first = _call(consolidate_env, _proposal(consolidate_env))
    assert first.status == "committed" and first.current_state is not None
    hidden = forget_subjective_mem(
        store=consolidate_env["store"],
        evidence_space_id=consolidate_env["captured"].evidence_space_id,
        character_config=consolidate_env["config"],
        character_authority=consolidate_env["authority"],
        workspace_root=str(consolidate_env["workspace"]),
        operation_idempotency_key="forget-after-consolidate",
        proposal=_forget_proposal(consolidate_env, state=first.current_state),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=6),
        observed_at=NOW + timedelta(seconds=7),
    )
    assert hidden.status == "committed", hidden.blocked_reasons
    successor = _current_page(consolidate_env).blocks[-1].revision
    assert successor.lifecycle_state == "hidden"
    assert successor.formation_stage == "secondary"


def test_consolidated_secondary_is_accepted_by_later_correct(consolidate_env) -> None:
    first = _call(consolidate_env, _proposal(consolidate_env))
    assert first.status == "committed" and first.current_state is not None
    corrected = _correct_after(consolidate_env, first.current_state)
    assert corrected.status == "committed", corrected.blocked_reasons
    successor = _current_page(consolidate_env).blocks[-1].revision
    assert successor.memory_revision == 3
    assert successor.lifecycle_state == "active"
    assert successor.formation_stage == "secondary"


# --- ownership ------------------------------------------------------------


def test_runtime_is_the_only_consolidate_owner_using_shared_boundaries() -> None:
    source = inspect.getsource(consolidate_runtime)
    assert source.count("def consolidate_subjective_mem(") == 1
    for forbidden in (
        "subjective_mem.lifecycle_runtime import",
        "subjective_mem.forget_runtime import",
        "subjective_mem_pin_runtime import",
        "subjective_mem.restore_runtime import",
        "relaymem_primary",
        "ContextVar",
        "threading",
        "asyncio",
        "expected_current_transition_id",
    ):
        assert forbidden not in source, forbidden
    assert "load_subjective_mem_predecessor_authority_locked(" in source
    assert "reserve_lifecycle_publication(" in source
    assert "publish_lifecycle_post_image(" in source
    assert "resolve_finalized_replay(" in source
