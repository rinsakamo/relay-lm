#!/usr/bin/env python3
"""ASM-1 end-to-end Shared Assessment runtime smoke.

Exercises EV-1 user and assistant Evidence admission, exact Shared Assessment
read authorization, the character-independent split Assessment Pass,
revision/current-selector publication, idempotent retry, stale-output fencing,
and formation-time authorization receipt issuance.  It asserts that no
Subjective MEM record family is created.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.evidence.common import build_runtime_authority, canonical_digest
from relaylm.evidence.response_capture import (
    capture_managed_assistant_response_nonstream,
)
from relaylm.evidence.space import derive_evidence_space_id
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.user_input import capture_managed_user_input
from relaylm.shared_assessment.models import SharedAssessmentProposal, derive_shared_assessment_id
from relaylm.shared_assessment.runtime import (
    build_shared_assessment_formation_receipt,
    commit_shared_assessment_revision,
    prepare_shared_assessment_pass,
)

NOW = datetime(2026, 7, 22, 8, 0, 0, tzinfo=timezone.utc)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def route_snapshot(*, capture_profile: str) -> dict[str, object]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
    )
    digest = canonical_digest(
        {
            "route": "asm1-smoke-private-route",
            "evidence_space_id": evidence_space_id,
            "capture_profile": capture_profile,
        }
    )
    principal, scope = build_runtime_authority(
        scope_kind="route_configuration_authority",
        allowed_operations=("route_capture_snapshot_issue",),
        evidence_space_id=evidence_space_id,
        issued_at=NOW.isoformat(),
    )
    assistant = capture_profile == "managed_assistant_response"
    return {
        "schema": "relaylm.route_capture_grant_snapshot.v1",
        "route_binding_id": "routebind_"
        + canonical_digest(
            {"route_contract_snapshot_digest": digest, "validated_at": NOW.isoformat()}
        ),
        "route_contract_ref": "relaylm.asm1_smoke_private_route",
        "route_contract_revision": 1,
        "route_contract_snapshot_digest": digest,
        "evidence_space_id": evidence_space_id,
        "route_mode": "managed_conversation",
        "capture_profile": capture_profile,
        "allowed_origin_kinds": ["assistant" if assistant else "participant"],
        "allowed_capture_stream_kinds": [capture_profile],
        "allowed_stream_directions": ["outbound" if assistant else "inbound"],
        "effective_from": NOW.isoformat(),
        "expires_at_or_null": None,
        "revocation_revision_observed": 0,
        "validated_at": NOW.isoformat(),
        "validator_principal_ref": principal.to_dict(),
        "validator_authority_scope": scope.to_dict(),
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "evidence"
        store = EvidenceRecordStore(str(root))
        user = capture_managed_user_input(
            store=store,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            current_user_text="I have been tired lately.",
            fail_closed_reasons=(),
            operation_idempotency_key="asm1-smoke-user",
            route_snapshot_payload=route_snapshot(
                capture_profile="managed_user_input"
            ),
            now=NOW,
        )
        require(user.status == "admitted", user)
        assistant = capture_managed_assistant_response_nonstream(
            store=store,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="asm1-smoke-response",
            delivery_cohort_id="asm1-smoke-cohort",
            request_source_event_ids=(user.source_event_id,),
            assistant_visible_text="You said you have been tired lately.",
            operation_idempotency_key="asm1-smoke-assistant",
            route_snapshot_payload=route_snapshot(
                capture_profile="managed_assistant_response"
            ),
            now=NOW,
        )
        require(assistant.status == "admitted", assistant)

        prepared = prepare_shared_assessment_pass(
            store=store,
            evidence_space_id=user.evidence_space_id,
            source_event_ids=(user.source_event_id, assistant.source_event_id),
            assessment_pass_id="asm1-smoke-pass",
            now=NOW,
        )
        require(prepared.status == "ready", prepared.blocked_reasons)
        require(prepared.bundle is not None, "missing Assessment Pass bundle")
        serialized_bundle = json.dumps(
            prepared.bundle.to_dict(), ensure_ascii=False, sort_keys=True
        )
        for forbidden in (
            "character_id",
            "soul_revision",
            "subjective_meaning",
            "relationship_id",
            "scene_id",
        ):
            require(forbidden not in serialized_bundle, forbidden)
        print("PASS: exact EV-1 authorization produced a character-independent pass")

        proposal = SharedAssessmentProposal(
            assessment_id=derive_shared_assessment_id(
                user.evidence_space_id, "asm1-smoke-assessment"
            ),
            supported_content="The user reported recent tiredness.",
            support_state="supported",
            uncertainty=("exact_duration_unknown",),
            temporal_state="current",
            governance_revision="shared-assessment-policy-v1",
            expected_current_revision_or_null=None,
        )
        committed = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=proposal,
            operation_idempotency_key="asm1-smoke-commit",
            apply_enabled=True,
            now=NOW,
        )
        require(committed.status == "committed", committed.blocked_reasons)
        require(
            committed.revision is not None
            and committed.revision.assessment_revision == 1,
            committed,
        )
        require(
            committed.current_state is not None
            and committed.current_state.current_revision == 1,
            committed,
        )
        retry = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=proposal,
            operation_idempotency_key="asm1-smoke-commit",
            apply_enabled=True,
            now=NOW,
        )
        require(retry.status == "duplicate_existing", retry)
        print("PASS: revision and single current selector commit idempotently")

        stale = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=SharedAssessmentProposal(
                assessment_id=proposal.assessment_id,
                supported_content="Stale generated output.",
                support_state="supported",
                uncertainty=(),
                temporal_state="current",
                governance_revision="shared-assessment-policy-v1",
                expected_current_revision_or_null=None,
            ),
            operation_idempotency_key="asm1-smoke-stale",
            apply_enabled=True,
            now=NOW,
        )
        require(
            stale.blocked_reasons
            == ("shared_assessment_expected_current_revision_stale",),
            stale,
        )
        print("PASS: stale Assessment Pass output fails closed")

        with store.transaction(user.evidence_space_id) as tx:
            receipt = build_shared_assessment_formation_receipt(
                tx=tx,
                evidence_space_id=user.evidence_space_id,
                assessment_id=proposal.assessment_id,
                assessment_revision=1,
                decision_id="asm1-smoke-decision",
                decision_input_digest="a" * 64,
                decided_at=NOW,
            )
        require(receipt.status == "ready", receipt.blocked_reasons)
        require(receipt.receipt is not None, receipt)
        receipt_payload = receipt.receipt.to_dict()
        require("supported_content" not in receipt_payload, receipt_payload)
        require("character_id" not in receipt_payload, receipt_payload)
        require(receipt.receipt.is_self_authenticating(), receipt_payload)
        print("PASS: decision-bound formation authorization receipt prepared")

        space_root = root / user.evidence_space_id
        subjective_paths = list(space_root.rglob("*subjective_mem*"))
        require(subjective_paths == [], subjective_paths)
        print("PASS: ASM-1 created no Subjective MEM records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
