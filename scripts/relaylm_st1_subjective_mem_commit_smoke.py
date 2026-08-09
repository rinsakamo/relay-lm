#!/usr/bin/env python3
"""ST-1 exact SM-1-to-canonical-publication/finalization smoke."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.character_workspace import (
    INTERNAL_DIRECTORIES,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    REQUIRED_SOURCE_FILENAMES,
    validate_character_workspace,
)
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
from relaylm.subjective_mem_commit_runtime import finalize_subjective_mem_create
from relaylm.subjective_mem_markdown import parse_subjective_mem_page_bytes
from relaylm.subjective_mem_runtime import create_subjective_mem

NOW = datetime(2026, 7, 23, 1, 0, 0, tzinfo=timezone.utc)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _route_snapshot() -> dict[str, object]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
        memory_namespace="ns1",
        session_id="st1-smoke-session",
    )
    digest = canonical_digest(
        {
            "route": "st1-smoke-private-route",
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
                "route_contract_snapshot_digest": digest,
                "validated_at": NOW.isoformat(),
            }
        ),
        "route_contract_ref": "relaylm.st1_smoke_private_route",
        "route_contract_revision": 1,
        "route_contract_snapshot_digest": digest,
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


def _workspace(root: Path) -> Path:
    workspace_root = root / "characters"
    character_root = workspace_root / "char1"
    character_root.mkdir(parents=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        (character_root / filename).write_text(f"# {filename}\n", encoding="utf-8")
    for relative in LOWERCASE_WORKSPACE_DIRECTORIES + INTERNAL_DIRECTORIES:
        (character_root / relative).mkdir(parents=True, exist_ok=True)
    validation = validate_character_workspace(
        character_root, character_id="char1", public=False
    )
    require(validation.is_valid, validation)
    return workspace_root.resolve()


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        workspace_root = _workspace(root)
        store = EvidenceRecordStore(str(root / "evidence"))
        captured = capture_managed_user_input(
            store=store,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="st1-smoke-session",
            current_user_text="I felt relieved after the appointment.",
            fail_closed_reasons=(),
            operation_idempotency_key="st1-smoke-source",
            route_snapshot_payload=_route_snapshot(),
            now=NOW,
        )
        require(captured.status == "admitted", captured)
        prepared = prepare_shared_assessment_pass(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            source_event_ids=(captured.source_event_id,),
            assessment_pass_id="st1-smoke-pass",
            now=NOW,
        )
        require(prepared.status == "ready" and prepared.bundle is not None, prepared)
        assessment = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=SharedAssessmentProposal(
                assessment_id=derive_shared_assessment_id(
                    captured.evidence_space_id, "st1-smoke-assessment"
                ),
                supported_content="The user reported feeling relieved after the appointment.",
                support_state="supported",
                uncertainty=("appointment_type_unknown",),
                temporal_state="historical",
                governance_revision="shared-assessment-policy-v1",
                expected_current_revision_or_null=None,
            ),
            operation_idempotency_key="st1-smoke-assessment-commit",
            apply_enabled=True,
            now=NOW,
        )
        require(
            assessment.status == "committed"
            and assessment.revision is not None
            and assessment.current_state is not None,
            assessment,
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
                    "relaylm-default": {"backend": "local", "mode": "memory_light"}
                },
                "characters": {
                    "char1": {
                        "soul": "examples/profiles/default/SOUL.md",
                        "output_policy": "examples/profiles/default/style.md",
                    }
                },
                "subjective_mem_workspace_root": str(workspace_root),
            }
        )
        authority, reasons = resolve_subjective_mem_character_authority(
            config,
            workspace_or_tenant_ref="relaylm-local",
            character_id="char1",
        )
        require(authority is not None and not reasons, reasons)
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
        sm1_request = dict(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            assessment_revision=assessment.revision,
            assessment_current_state=assessment.current_state,
            proposal=proposal,
            operation_idempotency_key="st1-smoke-create",
            apply_enabled=True,
            decided_at=NOW,
            observed_at=NOW,
        )
        sm1 = create_subjective_mem(**sm1_request)
        require(sm1.status == "committed" and sm1.revision is not None, sm1)
        require(sm1.revision.to_dict()["retrieval_visible"] is True, sm1)
        require(sm1.current_state and not sm1.current_state.retrieval_eligible, sm1)

        commit_request = dict(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            workspace_root=str(workspace_root),
            sm1_operation_idempotency_key="st1-smoke-create",
            finalized_at=NOW + timedelta(seconds=1),
            observed_at=NOW + timedelta(seconds=2),
        )
        dry = finalize_subjective_mem_create(**commit_request, apply_enabled=False)
        require(dry.status == "dry_run_ready", dry)
        page_path = workspace_root / "char1/memory/episodes/subjective-mem-v1.md"
        require(not page_path.exists(), "dry-run wrote canonical page")
        print("PASS: ST-1 dry-run validated an exact SM-1 bundle without writes")

        committed = finalize_subjective_mem_create(**commit_request, apply_enabled=True)
        require(committed.status == "committed", committed)
        require(
            committed.current_state is not None
            and committed.current_state.mutation_state == "none"
            and committed.current_state.retrieval_eligible is True,
            committed,
        )
        page, parse_reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(page is not None and not parse_reasons and len(page.blocks) == 1, parse_reasons)
        require(page.blocks[0].revision.to_dict() == sm1.revision.to_dict(), page)
        print("PASS: canonical Markdown and durable finalization agree exactly")

        duplicate = finalize_subjective_mem_create(**commit_request, apply_enabled=True)
        require(duplicate.status == "duplicate_finalized", duplicate)
        sm1_retry = create_subjective_mem(**sm1_request)
        require(sm1_retry.status == "duplicate_finalized", sm1_retry)
        require(sm1_retry.finalization_id == committed.finalization_id, sm1_retry)
        print("PASS: ST-1 and SM-1 retries converge on one finalized identity")

        schema = json.loads(
            (
                REPO_ROOT
                / "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(
            {
                "records": [
                    sm1.decision.to_dict(),
                    sm1.revision.to_dict(),
                    committed.current_state.to_dict(),
                ]
            }
        )
        diagnostic = json.dumps(committed.to_log_dict(), sort_keys=True)
        require(sm1.revision.grounded_content not in diagnostic, diagnostic)
        require(sm1.revision.subjective_meaning not in diagnostic, diagnostic)
        require("memory/episodes" not in diagnostic, diagnostic)
        print("PASS: target schema and content-free public diagnostics remain valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
