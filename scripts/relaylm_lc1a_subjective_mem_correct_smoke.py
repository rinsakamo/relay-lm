#!/usr/bin/env python3
"""LC-1A exact canonical Subjective MEM Correct smoke."""
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
from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.config import RelayLMConfig
from relaylm.evidence.common import build_runtime_authority, canonical_digest
from relaylm.evidence.space import derive_evidence_space_id
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.user_input import capture_managed_user_input
from relaylm.shared_assessment.models import SharedAssessmentProposal, derive_shared_assessment_id
from relaylm.shared_assessment.runtime import (
    commit_shared_assessment_revision,
    prepare_shared_assessment_pass,
)
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCreateProposal,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemProposalBoundary,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem.commit_runtime import finalize_subjective_mem_create
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    SubjectiveMemCorrectProposal,
    SubjectiveMemCorrectionBoundary,
)
from relaylm.subjective_mem_lifecycle_runtime import correct_subjective_mem
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
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

        correct_proposal = SubjectiveMemCorrectProposal(
            expected_memory_id=committed.current_state.memory_id,
            expected_current_revision=1,
            expected_lifecycle_state="active",
            expected_mutation_state="none",
            expected_page_id=page.page_id,
            expected_relative_path="memory/episodes/subjective-mem-v1.md",
            expected_block_id=page.blocks[0].block_id,
            expected_page_digest=page.page_digest,
            expected_current_selector_id=committed.current_state.memory_state_id,
            expected_current_selector_digest=canonical_digest(committed.current_state.to_dict()),
            expected_current_receipt_id=committed.receipt.receipt_id,
            expected_current_receipt_digest=committed.receipt.to_dict()["receipt_digest"],
            expected_memory_kind=page.blocks[0].revision.memory_kind,
            expected_formation_stage=page.blocks[0].revision.formation_stage,
            expected_scope_binding_digest=canonical_digest(
                page.blocks[0].revision.scope_binding.to_dict()
            ),
            expected_formation_snapshot_digest=canonical_digest(
                page.blocks[0].revision.formation_snapshot.to_dict()
            ),
            expected_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
            expected_page_schema=PAGE_SCHEMA,
            expected_block_schema=LIFECYCLE_BLOCK_SCHEMA,
            expected_renderer_revision=RENDERER_REVISION,
            expected_partition_revision=PAGE_PARTITION_REVISION,
            expected_platform_revision=PLATFORM_REVISION,
            assessment_revision=assessment.revision,
            assessment_current_state=assessment.current_state,
            corrected_grounded_content=assessment.revision.supported_content,
            corrected_subjective_meaning=(
                "I now remember this more precisely as relief mixed with lingering uncertainty."
            ),
            corrected_strength=SubjectiveMemStrength(
                grounded_confidence=0.8,
                subjective_conviction=0.6,
                salience="medium",
                reinforcement_count=0,
                strength_basis="subjective_interpretation",
            ),
            authorization_class="user_management",
            authorization_id="lc1a-smoke-user-authorization",
            reason_category="user_reported_inaccuracy",
            policy_revision=LIFECYCLE_POLICY_REVISION,
            boundary=SubjectiveMemCorrectionBoundary(),
        )
        correct_request = dict(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            workspace_root=str(workspace_root),
            operation_idempotency_key="lc1a-smoke-correct",
            proposal=correct_proposal,
            committed_at=NOW + timedelta(seconds=3),
            observed_at=NOW + timedelta(seconds=4),
        )
        correct_dry = correct_subjective_mem(**correct_request, apply_enabled=False)
        require(correct_dry.status == "dry_run_ready", correct_dry)
        unchanged, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(unchanged is not None and not reasons and len(unchanged.blocks) == 1, reasons)
        print("PASS: LC-1A dry-run validates the exact successor without writes")

        corrected = correct_subjective_mem(**correct_request, apply_enabled=True)
        require(corrected.status == "committed", corrected)
        require(
            corrected.current_state is not None
            and corrected.current_state.current_revision == 2
            and corrected.current_state.mutation_state == "none"
            and corrected.current_state.retrieval_eligible is True,
            corrected,
        )
        corrected_page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(corrected_page is not None and not reasons, reasons)
        require([item.revision.memory_revision for item in corrected_page.blocks] == [1, 2], corrected_page)
        require(corrected_page.blocks[0].revision.to_dict() == sm1.revision.to_dict(), corrected_page)
        successor = corrected_page.blocks[1].revision
        require(successor.predecessor_revision_or_null == 1, successor)
        require(successor.authorization_kind == "lifecycle_transition", successor)
        print("PASS: Correct retains revision 1 and appends exactly one authorized revision 2")

        correct_retry = correct_subjective_mem(**correct_request, apply_enabled=True)
        require(correct_retry.status == "duplicate_finalized", correct_retry)
        require(correct_retry.transition_id == corrected.transition_id, correct_retry)
        print("PASS: exact Correct retry converges without a duplicate successor")

        duplicate = finalize_subjective_mem_create(**commit_request, apply_enabled=True)
        require(duplicate.status == "fail_closed", duplicate)
        print("PASS: stale ST-1 create finalization cannot replace the lifecycle successor")

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
                    successor.to_dict(),
                    corrected.current_state.to_dict(),
                    store.read_record(
                        evidence_space_id=captured.evidence_space_id,
                        record_kind="subjective_mem_lifecycle_transition",
                        record_id=corrected.transition_id,
                    ),
                ]
            }
        )
        diagnostic = json.dumps(corrected.to_log_dict(), sort_keys=True)
        require(sm1.revision.grounded_content not in diagnostic, diagnostic)
        require(sm1.revision.subjective_meaning not in diagnostic, diagnostic)
        require("memory/episodes" not in diagnostic, diagnostic)
        print("PASS: lifecycle schema and content-free public diagnostics remain valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
