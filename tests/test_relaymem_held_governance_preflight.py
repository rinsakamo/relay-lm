from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA
from relaylm.relaymem_held_governance_preflight import (
    preflight_held_apply,
    preflight_held_discard,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def candidate(**updates):
    value = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": "held-candidate-1",
        "operation_id": "held-operation-1",
        "character_id": "char-a",
        "namespace": "ns-a",
        "scope": "primary_formation",
        "status": "held",
        "queue_state": "claimed",
        "source_authority": "primary_worker_outcome",
        "source_evidence_digest": SHA_A,
        "source_evidence_present": True,
        "source_evidence_corrupt": False,
        "source_evidence_ambiguous": False,
        "source_content_included": False,
        "related_primary_memory_id": None,
        "related_primary_expected_revision": None,
        "related_primary_physical_id": None,
    }
    value.update(updates)
    return value


def assert_content_free(public):
    text = repr(public)
    assert "SECRET_USER_TEXT" not in text
    assert "SECRET_MODEL_OUTPUT" not in text
    assert public["content_free"] is True
    assert public["source_body_included"] is False
    assert public["model_output_included"] is False
    assert public["memory_content_included"] is False
    assert public["queue_payload_included"] is False
    assert public["queue_state_mutated"] is False
    assert public["primary_mem_mutated"] is False
    assert public["worker_started"] is False
    assert public["scheduler_started"] is False
    assert public["automatic_retry_or_release"] is False


def test_valid_held_apply_preflight():
    result = preflight_held_apply(
        candidate(),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    public = result.to_public_dict()
    assert public["schema_version"] == "relaylm.lab.held_apply_preflight.v0"
    assert public["status"] == "ready"
    assert public["action"] == "apply"
    assert public["reason_code"] == "ready"
    assert public["effects"]["held_item_adopted_contract"] is True
    assert_content_free(public)


def test_valid_held_discard_preflight():
    result = preflight_held_discard(
        candidate(),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    public = result.to_public_dict()
    assert public["schema_version"] == "relaylm.lab.held_discard_preflight.v0"
    assert public["status"] == "ready"
    assert public["action"] == "discard"
    assert public["effects"]["held_item_discarded_contract"] is True
    assert_content_free(public)


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("blocked", "candidate_blocked_not_held"),
        ("failed", "candidate_failed_not_held"),
        ("recovery_required", "candidate_recovery_required_not_held"),
        ("corrupt", "candidate_corrupt_not_held"),
        ("applied", "already_applied"),
        ("discarded", "already_discarded"),
        ("terminal_succeeded", "candidate_terminal_succeeded"),
        ("terminal_failed", "candidate_terminal_failed"),
    ],
)
def test_non_held_and_terminal_candidate_rejection(status, reason):
    result = preflight_held_apply(
        candidate(status=status),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "blocked"
    assert result.reason_code == reason
    assert_content_free(result.to_public_dict())


@pytest.mark.parametrize(
    ("queue_state", "reason"),
    [
        ("succeeded", "queue_terminal_succeeded"),
        ("failed", "queue_terminal_failed"),
    ],
)
def test_terminal_queue_state_blocks_held_preflight(queue_state, reason):
    result = preflight_held_apply(
        candidate(queue_state=queue_state),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "blocked"
    assert result.reason_code == reason


def test_missing_source_safe_failure():
    result = preflight_held_apply(
        candidate(source_evidence_present=False),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "safe_failure"
    assert result.reason_code == "source_evidence_missing"


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("source_evidence_corrupt", "source_evidence_corrupt"),
        ("source_evidence_ambiguous", "source_evidence_ambiguous"),
    ],
)
def test_corrupt_or_ambiguous_source_safe_failure(field, reason):
    result = preflight_held_discard(
        candidate(**{field: True}),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "safe_failure"
    assert result.reason_code == reason


def test_wrong_character_rejection():
    result = preflight_held_apply(
        candidate(character_id="char-b"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "blocked"
    assert result.reason_code == "wrong_character"


def test_wrong_namespace_rejection():
    result = preflight_held_apply(
        candidate(namespace="ns-b"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "blocked"
    assert result.reason_code == "wrong_namespace"


def install_fake_primary_state(monkeypatch, state=None, error_code=None):
    class PrimaryCurrentStateError(RuntimeError):
        def __init__(self, code):
            super().__init__(code)
            self.code = code

    def resolve_primary_current_state(*args, **kwargs):
        if error_code is not None:
            raise PrimaryCurrentStateError(error_code)
        return state

    module = types.ModuleType("relaylm.relaymem_primary_current_state")
    module.PrimaryCurrentStateError = PrimaryCurrentStateError
    module.resolve_primary_current_state = resolve_primary_current_state
    monkeypatch.setitem(sys.modules, "relaylm.relaymem_primary_current_state", module)


@dataclass(frozen=True)
class FakePrimaryState:
    lifecycle_state: str = "active"
    mutation_state: str = "none"
    retrieval_eligible: bool = True
    current_physical_id: str = SHA_B
    current_revision: int = 3
    controls_valid: bool = True
    page_valid: bool = True


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (FakePrimaryState(lifecycle_state="hidden"), "related_primary_hidden"),
        (FakePrimaryState(mutation_state="prepared"), "related_primary_prepared"),
        (FakePrimaryState(mutation_state="recovery_required"), "related_primary_recovery_required"),
        (FakePrimaryState(mutation_state="corrupt"), "related_primary_corrupt"),
        (FakePrimaryState(current_physical_id=SHA_C), "related_primary_prior"),
    ],
)
def test_related_primary_memory_safe_failures(monkeypatch, tmp_path, state, reason):
    install_fake_primary_state(monkeypatch, state=state)
    result = preflight_held_apply(
        candidate(
            related_primary_memory_id=SHA_A,
            related_primary_expected_revision=3,
            related_primary_physical_id=SHA_B,
        ),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
        store_root=tmp_path,
    )
    assert result.status == "safe_failure"
    assert result.reason_code == reason
    assert result.related_memory_checked is True


def test_related_primary_without_store_root_safe_failure():
    result = preflight_held_apply(
        candidate(
            related_primary_memory_id=SHA_A,
            related_primary_expected_revision=3,
            related_primary_physical_id=SHA_B,
        ),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "safe_failure"
    assert result.reason_code == "related_primary_store_root_required"
    assert result.related_memory_checked is False


def test_content_leakage_canary_rejected_shape_is_content_free():
    bad = candidate()
    bad["runtime_private_note"] = "SECRET_USER_TEXT SECRET_MODEL_OUTPUT"
    result = preflight_held_apply(
        bad,
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    )
    assert result.status == "invalid_input"
    assert result.reason_code == "candidate_shape_mismatch"
    assert_content_free(result.to_public_dict())


def test_no_filesystem_mutation(tmp_path):
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    result = preflight_held_discard(
        candidate(),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
        store_root=tmp_path,
    )
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert result.status == "ready"
    assert before == after


def test_no_queue_transition_mutation_flags():
    public = preflight_held_apply(
        candidate(queue_state="claimed"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).to_public_dict()
    assert public["queue_state"] == "claimed"
    assert public["queue_state_mutated"] is False
    assert public["effects"]["queue_state_mutated"] is False
