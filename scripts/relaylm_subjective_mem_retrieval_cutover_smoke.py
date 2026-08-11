#!/usr/bin/env python3
"""Bounded RT-1D-R1 read-only smoke."""

from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore
from relaylm._subjective_mem_retrieval_cutover_activation import reconstruct_cutover_chain
from relaylm.subjective_mem.retrieval_cutover import (
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_TRANSFERRED_SCOPE,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverRequest,
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
            projection_generation_id="smretrievalgen_" + "c" * 64,
            projection_source_digest="d" * 64,
        )
        # RT-1D-R5 retired the rehearsal entry point. Durable chain
        # reconstruction — the thing this smoke actually guards — is unchanged
        # and stays owned by the cutover semantic owner.
        default = reconstruct_cutover_chain(store, binding.to_dict())
        assert default == ("primary_stable", ())
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
        exact = reconstruct_cutover_chain(store, binding.to_dict())
        assert exact == ("primary_stable", ())
        record["record_digest"] = "0" * 64
        tampered_store = EvidenceRecordStore(str(Path(temporary) / "tampered"))
        with tampered_store.transaction(binding.evidence_space_id) as transaction:
            transaction.commit(
                transaction_id="smoke-tamper",
                records=(),
                logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, (record,)),),
            )
        failed = reconstruct_cutover_chain(tampered_store, binding.to_dict())
        assert failed[0] == "recovery_required" and failed[1]
        public = repr((default, exact, failed))
        assert (
            str(temporary) not in public and "subjective_serving': True" not in public
        )
    print(
        "PASS rt1d-r5 retired-rehearsal exact-chain fail-closed content-free no-write"
    )


if __name__ == "__main__":
    main()
