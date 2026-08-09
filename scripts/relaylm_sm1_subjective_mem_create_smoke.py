#!/usr/bin/env python3
"""SM-1 exact create-path smoke over EV-1 and ASM-1."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.evidence.common import build_runtime_authority, canonical_digest
from relaylm.evidence.space import derive_evidence_space_id
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.user_input import capture_managed_user_input
from relaylm.shared_assessment import SharedAssessmentProposal, derive_shared_assessment_id
from relaylm.shared_assessment_runtime import (
    commit_shared_assessment_revision,
    prepare_shared_assessment_pass,
)
from relaylm.subjective_mem import (
    SubjectiveMemCreateProposal,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemProposalBoundary,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_runtime import create_subjective_mem

NOW = datetime(2026, 7, 23, 1, 0, 0, tzinfo=timezone.utc)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def route_snapshot() -> dict[str, object]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
        memory_namespace="ns1",
        session_id="sm1-smoke-session",
    )
    snapshot_digest = canonical_digest(
        {
            "route": "sm1-smoke-private-route",
            "evidence_space_id": evidence_space_id,
            "capture_profile": "managed_user_input",
        }
    )
    principal, scope = build_runtime_authority(
        scope_kind="route_configuration_authority",
        allowed_operations=("route_capture_snapshot_issue",),
        evidence_space_id=evidence_space_id,
        issued_at=NOW.isoformat(),
    )
    return {
        "schema": "relaylm.route_capture_grant_snapshot.v1",
        "route_binding_id": "routebind_"
        + canonical_digest(
            {
                "route_contract_snapshot_digest": snapshot_digest,
                "validated_at": NOW.isoformat(),
            }
        ),
        "route_contract_ref": "relaylm.sm1_smoke_private_route",
        "route_contract_revision": 1,
        "route_contract_snapshot_digest": snapshot_digest,
        "evidence_space_id": evidence_space_id,
        "route_mode": "managed_conversation",
        "capture_profile": "managed_user_input",
        "allowed_origin_kinds": ["participant"],
        "allowed_capture_stream_kinds": ["managed_user_input"],
        "allowed_stream_directions": ["inbound"],
        "effective_from": NOW.isoformat(),
        "expires_at_or_null": None,
        "revocation_revision_observed": 0,
        "validated_at": NOW.isoformat(),
        "validator_principal_ref": principal.to_dict(),
        "validator_authority_scope": scope.to_dict(),
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        store = EvidenceRecordStore(str(Path(temporary) / "evidence"))
        captured = capture_managed_user_input(
            store=store,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sm1-smoke-session",
            current_user_text="I felt relieved after the appointment.",
            fail_closed_reasons=(),
            operation_idempotency_key="sm1-smoke-source",
            route_snapshot_payload=route_snapshot(),
            now=NOW,
        )
        require(captured.status == "admitted", captured)
        prepared = prepare_shared_assessment_pass(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            source_event_ids=(captured.source_event_id,),
            assessment_pass_id="sm1-smoke-pass",
            now=NOW,
        )
        require(prepared.status == "ready" and prepared.bundle is not None, prepared)
        committed = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=SharedAssessmentProposal(
                assessment_id=derive_shared_assessment_id(
                    captured.evidence_space_id, "sm1-smoke-assessment"
                ),
                supported_content="The user reported feeling relieved after the appointment.",
                support_state="supported",
                uncertainty=("appointment_type_unknown",),
                temporal_state="historical",
                governance_revision="shared-assessment-policy-v1",
                expected_current_revision_or_null=None,
            ),
            operation_idempotency_key="sm1-smoke-assessment-commit",
            apply_enabled=True,
            now=NOW,
        )
        require(
            committed.status == "committed"
            and committed.revision is not None
            and committed.current_state is not None,
            committed,
        )
        proposal = SubjectiveMemCreateProposal(
            subjective_meaning="I remember this as a moment when the user felt safe again.",
            memory_kind="episodic",
            scope_binding=SubjectiveMemScopeBinding(),
            formation_snapshot=SubjectiveMemFormationSnapshot(
                soul_revision="soul-revision-opaque-1",
                memory_policy_revision="memory-policy-v1",
                boundary_revision="boundary-v1",
                scene_policy_revision_or_null=None,
                relationship_revision_or_null=None,
                formation_schema_version="subjective-mem-v1",
                model_revision="caller-proposal-model-v1",
            ),
            strength=SubjectiveMemStrength(
                grounded_confidence=0.8,
                subjective_conviction=0.7,
                salience="medium",
                reinforcement_count=0,
                strength_basis="subjective_interpretation",
            ),
            boundary=SubjectiveMemProposalBoundary(),
        )
        config = RelayLMConfig.model_validate(
            {
                "backends": {
                    "local": {
                        "type": "openai_compatible",
                        "base_url": "http://127.0.0.1:8000/v1",
                    }
                },
                "model_routes": {
                    "relaylm-default": {
                        "backend": "local", "mode": "memory_light"
                    }
                },
                "characters": {
                    "char1": {
                        "soul": "examples/profiles/default/SOUL.md",
                        "output_policy": "examples/profiles/default/style.md",
                    }
                },
            }
        )
        authority, authority_reasons = resolve_subjective_mem_character_authority(
            config,
            workspace_or_tenant_ref="relaylm-local",
            character_id="char1",
        )
        require(authority is not None and not authority_reasons, authority_reasons)
        request = dict(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            assessment_revision=committed.revision,
            assessment_current_state=committed.current_state,
            proposal=proposal,
            operation_idempotency_key="sm1-smoke-create",
            apply_enabled=True,
            decided_at=NOW,
            observed_at=NOW,
        )
        created = create_subjective_mem(**request)
        require(created.status == "committed", created.blocked_reasons)
        require(created.decision and created.revision and created.current_state, created)
        require(created.prepared_manifest and created.formation_receipt, created)
        require(created.current_state.to_dict()["mutation_state"] == "prepared", created)
        require(created.current_state.to_dict()["retrieval_eligible"] is False, created)
        require(created.revision.to_dict()["retrieval_visible"] is True, created)
        require(created.prepared_manifest.to_dict()["canonical_markdown_published"] is False, created)
        require(list(store.root.rglob("*.md")) == [], "canonical Markdown emitted")
        print("PASS: exact ASM-1 authority produced one prepared SM-1 create result")

        retry = create_subjective_mem(**request)
        require(retry.status == "duplicate_existing", retry)
        require(retry.decision == created.decision, retry)
        require(retry.revision == created.revision, retry)
        print("PASS: retry preserved exact decision/result/current-state linkage")

        schema = json.loads(
            (REPO_ROOT / "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(
            {
                "records": [
                    created.decision.to_dict(),
                    created.revision.to_dict(),
                    created.current_state.to_dict(),
                ]
            }
        )
        diagnostic = json.dumps(created.to_log_dict(), sort_keys=True)
        require(created.revision.grounded_content not in diagnostic, diagnostic)
        require(created.revision.subjective_meaning not in diagnostic, diagnostic)
        print("PASS: target schema validates and public diagnostics remain content-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
