#!/usr/bin/env python3
"""Canonical Subjective MEM Forget publication and tombstone process smoke."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION
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
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCreateProposal,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemProposalBoundary,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_commit_runtime import finalize_subjective_mem_create
from relaylm.subjective_mem_forget import (
    SubjectiveMemForgetBoundary,
    SubjectiveMemForgetProposal,
)
from relaylm.subjective_mem_forget_runtime import forget_subjective_mem
from relaylm.subjective_mem_lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_reformation import check_subjective_mem_reformation
from relaylm.subjective_mem_runtime import create_subjective_mem

NOW = datetime(2026, 7, 24, 1, 0, 0, tzinfo=timezone.utc)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _route_snapshot() -> dict[str, object]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
        memory_namespace="ns1",
        session_id="subjective-mem-forget-smoke-session",
    )
    digest = canonical_digest(
        {
            "route": "subjective-mem-forget-smoke-private-route",
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
        "route_contract_ref": "relaylm.subjective_mem_forget_smoke_private_route",
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
            session_id="subjective-mem-forget-smoke-session",
            current_user_text="I felt relieved after the appointment.",
            fail_closed_reasons=(),
            operation_idempotency_key="subjective-mem-forget-smoke-source",
            route_snapshot_payload=_route_snapshot(),
            now=NOW,
        )
        require(captured.status == "admitted", captured)

        prepared = prepare_shared_assessment_pass(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            source_event_ids=(captured.source_event_id,),
            assessment_pass_id="subjective-mem-forget-smoke-pass",
            now=NOW,
        )
        require(prepared.status == "ready" and prepared.bundle is not None, prepared)
        assessment = commit_shared_assessment_revision(
            store=store,
            bundle=prepared.bundle,
            proposal=SharedAssessmentProposal(
                assessment_id=derive_shared_assessment_id(
                    captured.evidence_space_id,
                    "subjective-mem-forget-smoke-assessment",
                ),
                supported_content=(
                    "The user reported feeling relieved after the appointment."
                ),
                support_state="supported",
                uncertainty=("appointment_type_unknown",),
                temporal_state="historical",
                governance_revision="shared-assessment-policy-v1",
                expected_current_revision_or_null=None,
            ),
            operation_idempotency_key="subjective-mem-forget-smoke-assessment-commit",
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
        authority, authority_reasons = resolve_subjective_mem_character_authority(
            config,
            workspace_or_tenant_ref="relaylm-local",
            character_id="char1",
        )
        require(authority is not None and not authority_reasons, authority_reasons)

        create_proposal = SubjectiveMemCreateProposal(
            subjective_meaning=(
                "I remember this as a moment when the user felt safe again."
            ),
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
        sm1_key = "subjective-mem-forget-smoke-create"
        sm1 = create_subjective_mem(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            assessment_revision=assessment.revision,
            assessment_current_state=assessment.current_state,
            proposal=create_proposal,
            operation_idempotency_key=sm1_key,
            apply_enabled=True,
            decided_at=NOW,
            observed_at=NOW,
        )
        require(sm1.status == "committed" and sm1.revision is not None, sm1)

        committed = finalize_subjective_mem_create(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            workspace_root=str(workspace_root),
            sm1_operation_idempotency_key=sm1_key,
            apply_enabled=True,
            finalized_at=NOW + timedelta(seconds=1),
            observed_at=NOW + timedelta(seconds=2),
        )
        require(
            committed.status == "committed"
            and committed.current_state is not None
            and committed.receipt is not None,
            committed,
        )
        page_path = workspace_root / "char1/memory/episodes/subjective-mem-v1.md"
        page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(page is not None and not reasons and len(page.blocks) == 1, reasons)
        predecessor = page.blocks[0].revision

        forget_proposal = SubjectiveMemForgetProposal(
            expected_memory_id=committed.current_state.memory_id,
            expected_current_revision=1,
            expected_lifecycle_state="active",
            expected_mutation_state="none",
            expected_page_id=page.page_id,
            expected_relative_path="memory/episodes/subjective-mem-v1.md",
            expected_block_id=page.blocks[0].block_id,
            expected_page_digest=page.page_digest,
            expected_current_selector_id=committed.current_state.memory_state_id,
            expected_current_selector_digest=canonical_digest(
                committed.current_state.to_dict()
            ),
            expected_current_receipt_id=committed.receipt.receipt_id,
            expected_current_receipt_digest=committed.receipt.to_dict()[
                "receipt_digest"
            ],
            expected_memory_kind=predecessor.memory_kind,
            expected_formation_stage=predecessor.formation_stage,
            expected_scope_binding_digest=canonical_digest(
                predecessor.scope_binding.to_dict()
            ),
            expected_formation_snapshot_digest=canonical_digest(
                predecessor.formation_snapshot.to_dict()
            ),
            expected_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
            expected_page_schema=PAGE_SCHEMA,
            expected_block_schema=LIFECYCLE_BLOCK_SCHEMA,
            expected_renderer_revision=RENDERER_REVISION,
            expected_partition_revision=PAGE_PARTITION_REVISION,
            expected_platform_revision=PLATFORM_REVISION,
            authorization_class="user_management",
            authorization_id="subjective-mem-forget-smoke-authorization",
            reason_category="user_requested_forget",
            policy_revision=LIFECYCLE_POLICY_REVISION,
            boundary=SubjectiveMemForgetBoundary(),
        )
        request = dict(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_config=config,
            character_authority=authority,
            workspace_root=str(workspace_root),
            operation_idempotency_key="subjective-mem-forget-smoke-operation",
            proposal=forget_proposal,
            committed_at=NOW + timedelta(seconds=3),
            observed_at=NOW + timedelta(seconds=4),
        )

        before = page_path.read_bytes()
        dry = forget_subjective_mem(**request, apply_enabled=False)
        require(dry.status == "dry_run_ready", dry)
        require(page_path.read_bytes() == before, "Forget dry-run changed the page")
        print("PASS: Forget dry-run validates the exact hidden successor without writes")

        forgotten = forget_subjective_mem(**request, apply_enabled=True)
        require(forgotten.status == "committed", forgotten)
        require(
            forgotten.current_state is not None
            and forgotten.current_state.current_revision == 2
            and forgotten.current_state.lifecycle_state == "hidden"
            and forgotten.current_state.mutation_state == "none"
            and forgotten.current_state.retrieval_eligible is False,
            forgotten,
        )
        hidden_page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(hidden_page is not None and not reasons, reasons)
        require(
            [item.revision.memory_revision for item in hidden_page.blocks] == [1, 2],
            hidden_page,
        )
        successor = hidden_page.blocks[1].revision
        require(successor.lifecycle_state == "hidden", successor)
        require(successor.retrieval_visible is False, successor)
        require(successor.grounded_content == predecessor.grounded_content, successor)
        require(
            successor.grounded_content_digest == predecessor.grounded_content_digest,
            successor,
        )
        require(successor.subjective_meaning == predecessor.subjective_meaning, successor)
        require(successor.strength.to_dict() == predecessor.strength.to_dict(), successor)
        require(
            successor.scope_binding.to_dict() == predecessor.scope_binding.to_dict(),
            successor,
        )
        require(
            successor.formation_snapshot.to_dict()
            == predecessor.formation_snapshot.to_dict(),
            successor,
        )
        print("PASS: canonical Forget appends one semantic-preserving hidden successor")

        tombstone = store.read_record(
            evidence_space_id=captured.evidence_space_id,
            record_kind="subjective_mem_forget_tombstone",
            record_id=forgotten.tombstone_id,
        )
        require(isinstance(tombstone, dict), tombstone)
        require(tombstone.get("content_free") is True, tombstone)
        require(tombstone.get("formation_stage") == predecessor.formation_stage, tombstone)
        require(isinstance(tombstone.get("transition_digest"), str), tombstone)
        serialized_tombstone = json.dumps(tombstone, sort_keys=True)
        require(predecessor.grounded_content not in serialized_tombstone, tombstone)
        require(predecessor.subjective_meaning not in serialized_tombstone, tombstone)
        require("memory/episodes" not in serialized_tombstone, tombstone)
        print("PASS: Forget tombstone is durable, self-bound, and content-free")

        reformation = check_subjective_mem_reformation(
            store=store,
            evidence_space_id=captured.evidence_space_id,
            character_id=predecessor.character_id,
            grounded_content_digest=predecessor.grounded_content_digest,
            subjective_meaning=predecessor.subjective_meaning,
            memory_kind=predecessor.memory_kind,
            scope_binding=predecessor.scope_binding,
        )
        require(reformation.status == "blocked", reformation)
        require(reformation.tombstone_ids == (forgotten.tombstone_id,), reformation)
        print("PASS: exact automatic re-formation is blocked by resolved tombstone lineage")

        retry = forget_subjective_mem(**request, apply_enabled=True)
        require(retry.status == "duplicate_finalized", retry)
        require(retry.transition_id == forgotten.transition_id, retry)
        require(retry.tombstone_id == forgotten.tombstone_id, retry)
        retry_page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
        require(retry_page is not None and not reasons, reasons)
        require(len(retry_page.blocks) == 2, retry_page)
        print("PASS: exact Forget retry converges without another revision or tombstone")

        diagnostic = json.dumps(forgotten.to_log_dict(), sort_keys=True)
        require(predecessor.grounded_content not in diagnostic, diagnostic)
        require(predecessor.subjective_meaning not in diagnostic, diagnostic)
        require("memory/episodes" not in diagnostic, diagnostic)
        print("PASS: public Forget diagnostics remain bounded and content-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
