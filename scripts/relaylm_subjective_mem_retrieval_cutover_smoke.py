#!/usr/bin/env python3
"""Bounded RT-1D-R1 read-only smoke."""

from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.evidence_common import canonical_digest
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.subjective_mem_retrieval_cutover import (
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_TRANSFERRED_SCOPE,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverRequest,
    rehearse_subjective_mem_retrieval_cutover,
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-rt1d-r1-") as temporary:
        store = EvidenceRecordStore(str(Path(temporary) / "store"))
        binding = SubjectiveMemRetrievalCutoverBinding(
            schema_version=1,
            authority_domain=CUTOVER_AUTHORITY_DOMAIN,
            transferred_scope=CUTOVER_TRANSFERRED_SCOPE,
            evidence_space_id="smoke-space",
            deployment_id="smoke-deployment",
            scope_id="ordinary-memory",
            policy_revision_id="policy-1",
            readiness_id="ready-1",
            bootstrap_main_sha="a" * 64,
            resulting_main_sha="b" * 64,
            projection_generation_id="c" * 64,
            projection_source_digest="d" * 64,
        )
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
        "PASS rt1d-r1 primary-only rehearsal exact-chain fail-closed content-free no-write"
    )


if __name__ == "__main__":
    main()
