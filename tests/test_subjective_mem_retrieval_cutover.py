from __future__ import annotations

import dataclasses
import hashlib
import inspect
from pathlib import Path

import pytest
import yaml

from relaylm.config import RelayLMConfig
from relaylm.evidence_common import canonical_digest
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.subjective_mem_retrieval_cutover import (
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_SCHEMA_VERSION,
    CUTOVER_TRANSFERRED_SCOPE,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverError,
    SubjectiveMemRetrievalCutoverRequest,
    rehearse_subjective_mem_retrieval_cutover,
)

_DIGEST = "a" * 64
_STATES = (
    "primary_stable",
    "rehearsal_ready",
    "transfer_intent",
    "primary_reader_fenced",
    "primary_writer_fenced",
    "subjective_generation_bound",
    "subjective_reader_enabled",
    "transfer_receipt_finalized",
    "post_transfer_validated",
    "retirement_complete",
)


def _binding(**changes: object) -> SubjectiveMemRetrievalCutoverBinding:
    values = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "authority_domain": CUTOVER_AUTHORITY_DOMAIN,
        "transferred_scope": CUTOVER_TRANSFERRED_SCOPE,
        "evidence_space_id": "space-1",
        "deployment_id": "deployment-1",
        "scope_id": "ordinary-memory",
        "policy_revision_id": "policy-1",
        "readiness_id": "ready-1",
        "bootstrap_main_sha": _DIGEST,
        "resulting_main_sha": "b" * 64,
        "projection_generation_id": "c" * 64,
        "projection_source_digest": "d" * 64,
    }
    values.update(changes)
    return SubjectiveMemRetrievalCutoverBinding(**values)


def _records(binding: SubjectiveMemRetrievalCutoverBinding, count: int) -> list[dict]:
    result: list[dict] = []
    predecessor_digest = None
    binding_dict = binding.to_dict()
    for index, state in enumerate(_STATES[:count]):
        record = {
            "schema_version": 1,
            "state": state,
            "predecessor_state": None if index == 0 else _STATES[index - 1],
            "predecessor_digest": predecessor_digest,
            "binding": binding_dict,
            "binding_digest": canonical_digest(binding_dict),
        }
        record["record_digest"] = canonical_digest(record)
        result.append(record)
        predecessor_digest = record["record_digest"]
    return result


def _seed(
    store: EvidenceRecordStore,
    binding: SubjectiveMemRetrievalCutoverBinding,
    records: list[dict],
    *,
    key: str = CUTOVER_LOG_KEY,
) -> None:
    with store.transaction(binding.evidence_space_id) as transaction:
        result = transaction.commit(
            transaction_id="test-seed",
            records=(),
            logs=((CUTOVER_LOG_KIND, key, records),),
        )
    assert result.status == "created"


def _config_tuple(root: Path) -> dict[str, object]:
    return {
        "subjective_mem_retrieval_cutover_mode": "rehearsal",
        "subjective_mem_retrieval_cutover_store_root": str(root),
        "subjective_mem_retrieval_cutover_evidence_space_id": "space-1",
        "subjective_mem_retrieval_cutover_deployment_id": "deployment-1",
        "subjective_mem_retrieval_cutover_scope_id": "ordinary-memory",
        "subjective_mem_retrieval_cutover_bootstrap_main_sha": "a" * 64,
        "subjective_mem_retrieval_cutover_resulting_main_sha": "b" * 64,
        "subjective_mem_retrieval_cutover_policy_revision_id": "policy-1",
        "subjective_mem_retrieval_cutover_projection_generation_id": "c" * 64,
        "subjective_mem_retrieval_cutover_projection_source_digest": "d" * 64,
        "subjective_mem_retrieval_cutover_readiness_id": "ready-1",
    }


def _config(values: dict[str, object] | None = None) -> RelayLMConfig:
    payload = yaml.safe_load(Path("config.example.yaml").read_text())
    payload.update(values or {})
    return RelayLMConfig.model_validate(payload)


def test_default_config_is_primary_only_and_old_config_loads() -> None:
    config = _config()
    assert config.subjective_mem_retrieval_cutover_mode == "primary_only"
    assert config.subjective_mem_retrieval_cutover_store_root is None


def test_config_example_loads_and_has_each_field_once() -> None:
    text = Path("config.example.yaml").read_text()
    data = yaml.safe_load(text)
    RelayLMConfig.model_validate(data)
    for key in _config_tuple(Path("/tmp/cutover")):
        assert text.count(f"{key}:") == 1


def test_valid_rehearsal_config_and_closed_modes(tmp_path: Path) -> None:
    config = _config(_config_tuple(tmp_path / "store"))
    assert config.subjective_mem_retrieval_cutover_mode == "rehearsal"
    with pytest.raises(ValueError, match="literal_error"):
        _config({"subjective_mem_retrieval_cutover_mode": "subjective"})


@pytest.mark.parametrize("missing", list(_config_tuple(Path("/tmp/store"))))
def test_every_partial_rehearsal_tuple_is_rejected(missing: str) -> None:
    values = _config_tuple(Path("/tmp/store"))
    if missing == "subjective_mem_retrieval_cutover_mode":
        values["subjective_mem_retrieval_cutover_mode"] = "primary_only"
    else:
        del values[missing]
    with pytest.raises(ValueError, match="cutover_"):
        _config(values)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"schema_version": 2}, "schema_unsupported"),
        ({"authority_domain": "wrong"}, "authority_domain_mismatch"),
        ({"transferred_scope": "wrong"}, "transferred_scope_mismatch"),
        ({"deployment_id": "../private"}, "identifier_invalid"),
        ({"bootstrap_main_sha": "wrong"}, "digest_invalid"),
    ],
)
def test_binding_rejects_unsupported_or_unsafe_values(
    change: dict, reason: str
) -> None:
    with pytest.raises(SubjectiveMemRetrievalCutoverError, match=reason):
        _binding(**change)


def test_binding_is_immutable_closed_and_canonical() -> None:
    binding = _binding()
    with pytest.raises(dataclasses.FrozenInstanceError):
        binding.deployment_id = "changed"  # type: ignore[misc]
    assert binding.canonical_bytes() == _binding().canonical_bytes()
    assert SubjectiveMemRetrievalCutoverBinding.from_dict(binding.to_dict()) == binding
    assert "aaaa" not in repr(binding)
    with pytest.raises(SubjectiveMemRetrievalCutoverError, match="schema_invalid"):
        SubjectiveMemRetrievalCutoverBinding.from_dict(
            {**binding.to_dict(), "prose": "private"}
        )


def test_absent_chain_is_primary_only_and_rehearsal_is_in_memory(
    tmp_path: Path,
) -> None:
    store = EvidenceRecordStore(str(tmp_path / "store"))
    binding = _binding()
    default = rehearse_subjective_mem_retrieval_cutover(
        store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
    )
    rehearsal = rehearse_subjective_mem_retrieval_cutover(
        store=store,
        binding=binding,
        request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
    )
    assert (default.state, default.authority_class) == (
        "primary_stable",
        "primary_only",
    )
    assert (rehearsal.state, rehearsal.authority_class) == (
        "rehearsal_ready",
        "primary_only",
    )
    assert not rehearsal.diagnostics.subjective_serving
    assert rehearsal.diagnostics.runtime_private_evidence_omitted


def test_exact_seeded_rehearsal_chain_is_read_only(tmp_path: Path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "store"))
    binding = _binding()
    _seed(store, binding, _records(binding, 2))
    before = _tree_digest(store.root)
    first = rehearse_subjective_mem_retrieval_cutover(
        store=store,
        binding=binding,
        request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
    )
    second = rehearse_subjective_mem_retrieval_cutover(
        store=store,
        binding=binding,
        request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
    )
    assert first == second
    assert first.state == "rehearsal_ready"
    assert _tree_digest(store.root) == before


@pytest.mark.parametrize("count", range(3, 11))
def test_future_complete_chain_parses_but_r1_fails_closed(
    tmp_path: Path, count: int
) -> None:
    store = EvidenceRecordStore(str(tmp_path / f"store-{count}"))
    binding = _binding(evidence_space_id=f"space-{count}")
    _seed(store, binding, _records(binding, count))
    result = rehearse_subjective_mem_retrieval_cutover(
        store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
    )
    assert result.state == "recovery_required"
    assert result.authority_class == "neither"


@pytest.mark.parametrize("mutation", ["tamper", "skip", "binding", "schema", "extra"])
def test_malformed_chains_fail_closed(tmp_path: Path, mutation: str) -> None:
    store = EvidenceRecordStore(str(tmp_path / mutation))
    binding = _binding(evidence_space_id=f"space-{mutation}")
    records = _records(binding, 2)
    if mutation == "tamper":
        records[1]["record_digest"] = "0" * 64
    if mutation == "skip":
        records[1]["state"] = "transfer_intent"
    if mutation == "binding":
        records[1]["binding_digest"] = "0" * 64
    if mutation == "schema":
        records[1]["schema_version"] = 2
    if mutation == "extra":
        records[1]["private_context"] = "forbidden"
    _seed(store, binding, records)
    result = rehearse_subjective_mem_retrieval_cutover(
        store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
    )
    assert result.state == "recovery_required"
    assert result.authority_class == "neither"
    assert not result.diagnostics.reader_fence and not result.diagnostics.writer_fence


def test_multiple_chain_heads_fail_closed(tmp_path: Path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "store"))
    binding = _binding()
    _seed(store, binding, _records(binding, 1), key="other")
    result = rehearse_subjective_mem_retrieval_cutover(
        store=store, binding=binding, request=SubjectiveMemRetrievalCutoverRequest()
    )
    assert result.reasons == ("cutover_multiple_chains",)


def test_public_result_is_content_free(tmp_path: Path) -> None:
    result = rehearse_subjective_mem_retrieval_cutover(
        store=EvidenceRecordStore(str(tmp_path / "secret-path")),
        binding=_binding(),
        request=SubjectiveMemRetrievalCutoverRequest("rehearsal"),
    )
    projection = repr(result) + repr(result.to_dict())
    for forbidden in (
        str(tmp_path),
        "query",
        "prompt",
        "memory prose",
        "private_context",
    ):
        assert forbidden not in projection


def test_structure_and_immutable_store() -> None:
    module = Path("relaylm/subjective_mem_retrieval_cutover.py")
    assert len(module.read_text().splitlines()) < 700
    import relaylm.subjective_mem_retrieval_cutover as owner

    assert (
        max(
            len(inspect.getsource(value).splitlines())
            for value in vars(owner).values()
            if inspect.isfunction(value) and value.__module__ == owner.__name__
        )
        <= 80
    )
    assert (
        hashlib.sha256(Path("relaylm/evidence_store.py").read_bytes()).hexdigest()
        == "41cfa9af6c32c1359be04f497924883ffbc4abb4e39313a44755494f92e2b41f"
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
