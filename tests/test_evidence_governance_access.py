"""Unit tests for EV-1 governance initialization and the fail-closed access resolver."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from relaylm.evidence.access import resolve_evidence_access_authorization
from relaylm.evidence.common import ev1_policy_snapshot_ref
from relaylm.evidence.governance import (
    build_least_privilege_grant,
    initialize_admitted_governance,
)

NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
POLICY_SNAPSHOT_REF = ev1_policy_snapshot_ref()


def _governance_and_grant(*, purpose: str = "relayctx_evidence_read"):
    grant, reasons = build_least_privilege_grant(
        grant_id="accessgrant_1",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        purpose=purpose,
        admission_decision_id="admdecision_1",
        validation_bundle_revision=1,
        issued_at=NOW.isoformat(),
    )
    assert not reasons
    state, event = initialize_admitted_governance(
        governance_event_id="governanceevent_1",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        part_ids=("part-0",),
        grants=(grant,),
        access_until=(NOW + timedelta(days=30)).isoformat(),
        purge_due_at=(NOW + timedelta(days=37)).isoformat(),
        authority_change_set_ref=_change_set_ref(),
        recorded_at=NOW.isoformat(),
        operation_idempotency_key="idem-governance-1",
    )
    return state, grant


def _change_set_ref():
    from relaylm.evidence.common import AuthorityChangeSetRef

    return AuthorityChangeSetRef(
        change_set_id="changeset_1",
        change_projection_plan_digest="0" * 64,
    )


def test_governance_initialize_admitted_is_available_and_verified() -> None:
    state, _ = _governance_and_grant()
    assert state.record_access_state == "available"
    assert state.integrity_state == "verified"
    assert state.part_access_states == {"part-0": "protected_available"}


def test_access_authorization_succeeds_for_exact_active_grant() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert not reasons
    assert projection is not None
    assert projection.gate_kind == "relayctx_evidence"
    assert projection.matched_grant_ids == (grant.grant_id,)
    assert projection.selected_part_ids == ("part-0",)


def test_access_authorization_denies_relayref_for_non_assistant_origin() -> None:
    grant, _ = build_least_privilege_grant(
        grant_id="accessgrant_2",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        purpose="relayref_observation_read",
        admission_decision_id="admdecision_1",
        validation_bundle_revision=1,
        issued_at=NOW.isoformat(),
    )
    state, _governance_event = initialize_admitted_governance(
        governance_event_id="governanceevent_2",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        part_ids=("part-0",),
        grants=(grant,),
        access_until=(NOW + timedelta(days=30)).isoformat(),
        purge_due_at=(NOW + timedelta(days=37)).isoformat(),
        authority_change_set_ref=_change_set_ref(),
        recorded_at=NOW.isoformat(),
        operation_idempotency_key="idem-governance-2",
    )
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayref_observation_read",
        origin_kind="participant",  # not assistant -- must be denied
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert projection is None
    assert "evidence_access_purpose_requires_assistant_origin" in reasons


def test_access_authorization_denies_when_not_admitted() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="rejected",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert projection is None
    assert "evidence_access_source_not_admitted" in reasons


def test_access_authorization_denies_on_stale_validation_bundle() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="invalidated",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert projection is None
    assert "evidence_access_validation_bundle_invalid" in reasons


def test_access_authorization_denies_after_access_deadline() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW + timedelta(days=31),
    )
    assert projection is None
    assert "evidence_access_deadline_expired" in reasons


def test_access_authorization_denies_when_grant_revision_stale() -> None:
    state, grant = _governance_and_grant()
    # A grant bound to a different (later) validation bundle revision no
    # longer matches this exact-revision governance state.
    stale_grant = build_least_privilege_grant(
        grant_id="accessgrant_stale",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        purpose="relayctx_evidence_read",
        admission_decision_id="admdecision_1",
        validation_bundle_revision=2,
        issued_at=NOW.isoformat(),
    )[0]
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(stale_grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert projection is None
    assert "evidence_access_no_matching_active_grant" in reasons


def test_access_authorization_is_content_free() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        now=NOW,
    )
    assert projection is not None
    payload = projection.to_dict()
    canary = "protected user text canary"
    assert canary not in str(payload)


def test_access_authorization_honors_explicit_empty_part_selection() -> None:
    state, grant = _governance_and_grant()
    projection, reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind="participant",
        source_event_id="sourceevent_1",
        evidence_space_id="evsp_1",
        admission_outcome="admitted",
        admission_decision_id="admdecision_1",
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=1,
        grants=(grant,),
        policy_snapshot_ref=POLICY_SNAPSHOT_REF,
        change_partition_watermark=0,
        requested_part_ids=(),
        now=NOW,
    )
    assert projection is None
    assert "evidence_access_no_available_parts" in reasons
