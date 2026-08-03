#!/usr/bin/env python3
"""Bounded RT-1D-R1 read-only smoke."""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import yaml

from relaylm.evidence_common import canonical_digest
from relaylm.config import RelayLMConfig
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.subjective_mem_retrieval_characterization import (
    SubjectiveMemRetrievalPrimaryServedMetrics,
    characterize_subjective_mem_retrieval_shadow,
)
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION, SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalRequest,
)
from relaylm.subjective_mem_retrieval_projection import (
    SubjectiveMemRetrievalProjectionSource, build_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem_retrieval_selection import SubjectiveMemRetrievalSelectionProjection
from relaylm.subjective_mem_retrieval_cutover import (
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_TRANSFERRED_SCOPE,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverRequest,
    evaluate_subjective_mem_retrieval_rehearsal_readiness,
    rehearse_subjective_mem_retrieval_cutover,
    subjective_mem_retrieval_rehearsal_readiness_id,
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-rt1d-r1-") as temporary:
        store = EvidenceRecordStore(str(Path(temporary) / "store"))
        source = SubjectiveMemRetrievalProjectionSource(
            evidence_space_id="smoke-space", character_id="character-1",
            workspace_authority_digest="e" * 64, admitted_scope_binding_digest="f" * 64,
            snapshot_taken_at="2026-08-03T00:00:00Z", entries=(),
        )
        projection, reasons = build_subjective_mem_retrieval_projection(source)
        assert reasons == () and projection is not None
        request = SubjectiveMemRetrievalRequest(
            character_id=source.character_id,
            workspace_authority_digest=source.workspace_authority_digest,
            admitted_scope_binding_digest=source.admitted_scope_binding_digest,
            query_plan_digest="1" * 64, request_correlation_digest="2" * 64,
            projection_generation_id=projection.manifest.projection_generation_id,
            projection_manifest_digest=projection.manifest.manifest_digest,
            memory_kinds=("episodic", "semantic"), candidate_limit=8, token_budget=256,
            policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
            boundary=SubjectiveMemRetrievalBoundary(),
        )
        binding = SubjectiveMemRetrievalCutoverBinding(
            schema_version=1,
            authority_domain=CUTOVER_AUTHORITY_DOMAIN,
            transferred_scope=CUTOVER_TRANSFERRED_SCOPE,
            evidence_space_id="smoke-space",
            deployment_id="smoke-deployment",
            scope_id="ordinary-memory",
            policy_revision_id="policy-1",
            readiness_id="pending",
            bootstrap_main_sha="a" * 64,
            resulting_main_sha="b" * 64,
            projection_generation_id=source.projection_generation_id,
            projection_source_digest=source.source_snapshot_digest,
        )
        shadow = SubjectiveMemRetrievalSelectionProjection(
            status="prepared_empty", shadow=True, attempted=True,
            projection_generation_ready=True, candidate_count=0, eligible_count=0,
            selected_count=0, not_requested_kind_count=0,
            excluded_count_by_reason_class=(), handoff_shape_class="empty",
            token_budget_class="empty", blocked_reason_classes=(),
        )
        primary = SubjectiveMemRetrievalPrimaryServedMetrics(
            attempted=True, candidate_count=0, selected_count=0,
            latency_class="within_bound",
        )
        characterization, reasons = characterize_subjective_mem_retrieval_shadow(
            primary=primary, shadow=shadow, replay=shadow,
            subjective_latency_class="within_bound", projection_rebuild_equivalent=True,
        )
        assert reasons == () and characterization is not None
        binding = replace(
            binding, readiness_id=subjective_mem_retrieval_rehearsal_readiness_id(
                binding, projection, characterization
            )
        )
        config_values = yaml.safe_load(Path("config.example.yaml").read_text())
        config_values.update({
            "subjective_mem_retrieval_cutover_mode": "rehearsal",
            "subjective_mem_retrieval_cutover_store_root": str(Path(temporary) / "store"),
            **{
                f"subjective_mem_retrieval_cutover_{field}": getattr(binding, field)
                for field in (
                    "evidence_space_id", "deployment_id", "scope_id",
                    "policy_revision_id", "readiness_id", "bootstrap_main_sha",
                    "resulting_main_sha", "projection_generation_id",
                    "projection_source_digest",
                )
            },
        })
        config = RelayLMConfig.model_validate(config_values)
        (Path(temporary) / "projection").mkdir()
        readiness, reasons = evaluate_subjective_mem_retrieval_rehearsal_readiness(
            config=config, binding=binding, source=source,
            projection_root=str(Path(temporary) / "projection"), request=request,
            primary=primary,
            subjective_latency_class="within_bound",
        )
        assert reasons == (), reasons
        assert readiness is not None
        assert not readiness.subjective_serving and not readiness.ordinary_usage_event_recorded
        assert not readiness.authority_state_written
        default = rehearse_subjective_mem_retrieval_cutover(
            store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
        )
        rehearsal = rehearse_subjective_mem_retrieval_cutover(
            store=store,
            binding=binding,
            request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
        )
        assert (
            default.state == "primary_stable" and rehearsal.state == "rehearsal_ready"
        )
        binding_dict = binding.to_dict()
        record = {
            "schema_version": 1,
            "state": "primary_stable",
            "predecessor_state": None,
            "predecessor_digest": None,
            "binding": binding_dict,
            "binding_digest": canonical_digest(binding_dict),
        }
        record["record_digest"] = canonical_digest(record)
        with store.transaction(binding.evidence_space_id) as transaction:
            written = transaction.commit(
                transaction_id="smoke-seed",
                records=(),
                logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, (record,)),),
            )
        assert written.status == "created"
        exact = rehearse_subjective_mem_retrieval_cutover(
            store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
        )
        assert exact.state == "primary_stable"
        record["record_digest"] = "0" * 64
        tampered_store = EvidenceRecordStore(str(Path(temporary) / "tampered"))
        with tampered_store.transaction(binding.evidence_space_id) as transaction:
            transaction.commit(
                transaction_id="smoke-tamper",
                records=(),
                logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, (record,)),),
            )
        failed = rehearse_subjective_mem_retrieval_cutover(
            store=tampered_store,
            binding=binding,
            request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
        )
        assert (
            failed.state == "recovery_required" and failed.authority_class == "neither"
        )
        public = repr(
            (default.to_dict(), rehearsal.to_dict(), exact.to_dict(), failed.to_dict())
        )
        assert (
            str(temporary) not in public and "subjective_serving': True" not in public
        )
    print(
        "PASS rt1d-r3 fixed-source deterministic-readiness primary-only no-write"
    )


if __name__ == "__main__":
    main()
