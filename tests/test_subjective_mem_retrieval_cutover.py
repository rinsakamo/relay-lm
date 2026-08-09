from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
from pathlib import Path

import pytest
import yaml

from relaylm.config import RelayLMConfig
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore
from relaylm._subjective_mem_retrieval_cutover_activation import (
    FORWARD_STATES,
    reconstruct_cutover_chain,
)
from relaylm.subjective_mem_retrieval_cutover import (
    RETIREMENT_STEPS,
    CUTOVER_AUTHORITY_DOMAIN,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_SCHEMA_VERSION,
    CUTOVER_TRANSFERRED_SCOPE,
    PRIMARY_WRITER_DECISION_SCHEMA_VERSION,
    PRIMARY_WRITER_PERMITTED,
    PRIMARY_WRITER_REJECTED,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverError,
    SubjectiveMemRetrievalCutoverRequest,
    SubjectiveMemRetrievalPrimaryWriterDecision,
    primary_writer_decision_permits_write,
    retire_subjective_mem_retrieval_cutover,
    resolve_subjective_mem_retrieval_primary_writer_decision,
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
_FENCE = _STATES.index("primary_writer_fenced")
_PRE_FENCE_STATES = _STATES[:_FENCE]
_FENCED_STATES = _STATES[_FENCE:]
# `subjective_reader_enabled` and `transfer_receipt_finalized` publish in one
# atomic log write, so a reconstructible chain can never end at the first of
# that pair. A seeded chain that does is a half-published activation.
_HALF_PUBLISHED_COUNT = _STATES.index("subjective_reader_enabled") + 1


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
        "projection_generation_id": "smretrievalgen_" + "c" * 64,
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
        "subjective_mem_retrieval_cutover_projection_generation_id": "smretrievalgen_" + "c" * 64,
        "subjective_mem_retrieval_cutover_projection_source_digest": "d" * 64,
        "subjective_mem_retrieval_cutover_readiness_id": "ready-1",
        # `rehearsal` requires its own disposable projection root, distinct by
        # normalized identity from the cutover store root and every other
        # operational root.
        "subjective_mem_retrieval_rehearsal_projection_root": str(
            root.with_name(f"{root.name}-rehearsal-projection")
        ),
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
    with pytest.raises(ValueError, match="subjective_mem_retrieval_cutover_mode_unsupported"):
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


@pytest.mark.parametrize(
    "generation_id",
    [
        "c" * 64,
        "other_" + "c" * 64,
        "smretrievalgen_" + "C" * 64,
        "smretrievalgen_" + "g" * 64,
        "smretrievalgen_" + "c" * 63,
        "smretrievalgen_" + "c" * 65,
    ],
)
def test_binding_and_config_reject_noncanonical_projection_generation(
    tmp_path: Path, generation_id: str
) -> None:
    with pytest.raises(
        SubjectiveMemRetrievalCutoverError,
        match="cutover_binding_projection_generation_invalid",
    ):
        _binding(projection_generation_id=generation_id)
    values = _config_tuple(tmp_path / "store")
    values["subjective_mem_retrieval_cutover_projection_generation_id"] = generation_id
    with pytest.raises(
        ValueError,
        match="subjective_mem_retrieval_cutover_projection_generation_id_invalid",
    ):
        _config(values)


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


def test_absent_chain_reconstructs_as_primary_stable(tmp_path: Path) -> None:
    """RT-1D-R5 retired the rehearsal entry point; reconstruction is unchanged.

    The chain the cutover semantic owner reconstructs is the same durable
    artefact it always was. Only the retired rehearsal/characterization
    execution surface is gone, so an absent chain is still exactly the genesis
    state rather than a recovery condition.
    """

    store = EvidenceRecordStore(str(tmp_path / "store"))
    state, reasons = reconstruct_cutover_chain(store, _binding().to_dict())
    assert (state, reasons) == ("primary_stable", ())


def test_exact_seeded_rehearsal_chain_reconstructs_read_only(tmp_path: Path) -> None:
    """An accepted R3 `rehearsal_ready` record stays valid and is never rewritten."""

    store = EvidenceRecordStore(str(tmp_path / "store"))
    binding = _binding()
    _seed(store, binding, _records(binding, 2))
    before = _tree_digest(store.root)
    first = reconstruct_cutover_chain(store, binding.to_dict())
    second = reconstruct_cutover_chain(store, binding.to_dict())
    assert first == second == ("rehearsal_ready", ())
    assert _tree_digest(store.root) == before


@pytest.mark.parametrize("count", range(3, 11))
def test_longer_chains_reconstruct_exactly_or_fail_closed(
    tmp_path: Path, count: int
) -> None:
    """Every prefix length reconstructs to its exact state, or fails closed.

    The one admitted exception is the atomic activation pair: a chain ending at
    `subjective_reader_enabled` can never be observed half-published.
    """

    store = EvidenceRecordStore(str(tmp_path / f"store-{count}"))
    binding = _binding(evidence_space_id=f"space-{count}")
    _seed(store, binding, _records(binding, count))
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    expected = FORWARD_STATES[count - 1]
    if expected == "subjective_reader_enabled":
        assert state == "recovery_required"
        assert reasons == ("cutover_activation_pair_incomplete",)
    else:
        assert (state, reasons) == (expected, ())


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
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    assert state == "recovery_required"
    assert reasons and reasons != ()


def test_multiple_chain_heads_fail_closed(tmp_path: Path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "store"))
    binding = _binding()
    _seed(store, binding, _records(binding, 1), key="other")
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    assert state == "recovery_required"
    assert reasons == ("cutover_multiple_chains",)


def test_retirement_result_is_content_free(tmp_path: Path) -> None:
    """The retirement entry point releases no path, prose, or private material."""

    config = _config(
        {
            **_config_tuple(tmp_path / "secret-path"),
            "subjective_mem_retrieval_cutover_mode": "subjective_only",
            "subjective_mem_retrieval_rehearsal_projection_root": None,
            "subjective_mem_retrieval_projection_root": str(
                tmp_path / "secret-path-projection"
            ),
        }
    )
    result = retire_subjective_mem_retrieval_cutover(config=config)
    projection = repr(result) + repr(result.to_dict())
    for forbidden in (
        str(tmp_path),
        "query",
        "prompt",
        "memory prose",
        "private_context",
    ):
        assert forbidden not in projection


def test_retirement_requires_an_exact_finalized_receipt(tmp_path: Path) -> None:
    """Retirement is not a second transfer: it is admitted only over the receipt."""

    config = _config(
        {
            **_config_tuple(tmp_path / "store"),
            "subjective_mem_retrieval_cutover_mode": "subjective_only",
            "subjective_mem_retrieval_rehearsal_projection_root": None,
            "subjective_mem_retrieval_projection_root": str(tmp_path / "projection"),
        }
    )
    root = config.subjective_mem_retrieval_cutover_store_root
    assert root is not None
    store = EvidenceRecordStore(root)
    binding = _binding()
    # A chain that has not reached `transfer_receipt_finalized` is refused.
    _seed(store, binding, _records(binding, 2))
    result = retire_subjective_mem_retrieval_cutover(config=config)
    assert result.state != "retirement_complete"
    assert "cutover_retirement_receipt_required" in result.reasons


def _decision(**changes: object) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    values: dict[str, object] = {
        "schema_version": PRIMARY_WRITER_DECISION_SCHEMA_VERSION,
        "state": "primary_stable",
        "writer_class": PRIMARY_WRITER_PERMITTED,
        "recovery_required": False,
        "reasons": (),
        "runtime_private_evidence_omitted": True,
    }
    values.update(changes)
    return SubjectiveMemRetrievalPrimaryWriterDecision(**values)


def test_retirement_steps_extend_the_chain_without_re_entering_it() -> None:
    """R5 records exactly the two retirement states, in order, and nothing else."""

    assert RETIREMENT_STEPS == (("post_transfer_validated",), ("retirement_complete",))
    tail = FORWARD_STATES[-2:]
    assert tail == ("post_transfer_validated", "retirement_complete")


def _rehearsal_config(tmp_path: Path, root_name: str = "store") -> RelayLMConfig:
    return _config(_config_tuple(tmp_path / root_name))


def _seeded_rehearsal_decision(
    tmp_path: Path, count: int, *, mutate=None
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    """Seed an exact chain of ``count`` states, then resolve the writer decision."""
    config = _rehearsal_config(tmp_path, f"store-{count}")
    root = config.subjective_mem_retrieval_cutover_store_root
    assert root is not None
    store = EvidenceRecordStore(root)
    binding = _binding()
    records = _records(binding, count)
    if mutate is not None:
        mutate(records)
    _seed(store, binding, records)
    return resolve_subjective_mem_retrieval_primary_writer_decision(config)


def test_decision_type_is_frozen_closed_and_content_free() -> None:
    decision = _decision()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.writer_class = PRIMARY_WRITER_REJECTED  # type: ignore[misc]
    assert decision == _decision()
    assert set(decision.to_dict()) == {
        "schema_version",
        "state",
        "writer_class",
        "recovery_required",
        "reasons",
        "runtime_private_evidence_omitted",
    }
    assert decision.runtime_private_evidence_omitted is True
    projection = repr(decision) + repr(decision.to_dict())
    for forbidden in ("/", "query", "prompt", "memory prose", "private_context", "binding"):
        assert forbidden not in projection


def test_primary_only_binds_primary_stable_permit_with_no_store_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import relaylm.subjective_mem_retrieval_cutover as owner

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("primary_only_must_not_touch_the_evidence_store")

    monkeypatch.setattr(owner, "EvidenceRecordStore", _forbidden)
    monkeypatch.setattr(owner, "_reconstruct", _forbidden)
    decision = resolve_subjective_mem_retrieval_primary_writer_decision(_config())
    assert decision == _decision()
    assert primary_writer_decision_permits_write(decision)
    assert decision.reasons == ()


def test_primary_only_touches_no_filesystem_path(tmp_path: Path) -> None:
    before = sorted(item.name for item in tmp_path.iterdir())
    decision = resolve_subjective_mem_retrieval_primary_writer_decision(_config())
    assert decision.state == "primary_stable"
    assert sorted(item.name for item in tmp_path.iterdir()) == before


@pytest.mark.parametrize("count", range(1, len(_PRE_FENCE_STATES) + 1))
def test_every_complete_pre_writer_fence_state_permits(tmp_path: Path, count: int) -> None:
    decision = _seeded_rehearsal_decision(tmp_path, count)
    assert decision.state == _STATES[count - 1]
    assert decision.state in _PRE_FENCE_STATES
    assert decision.writer_class == PRIMARY_WRITER_PERMITTED
    assert decision.recovery_required is False
    assert decision.reasons == ()
    assert primary_writer_decision_permits_write(decision)


@pytest.mark.parametrize(
    "count",
    [
        count
        for count in range(len(_PRE_FENCE_STATES) + 1, len(_STATES) + 1)
        if count != _HALF_PUBLISHED_COUNT
    ],
)
def test_writer_fence_and_every_later_state_rejects(tmp_path: Path, count: int) -> None:
    decision = _seeded_rehearsal_decision(tmp_path, count)
    assert decision.state == _STATES[count - 1]
    assert decision.state in _FENCED_STATES
    assert decision.writer_class == PRIMARY_WRITER_REJECTED
    assert decision.recovery_required is False
    assert decision.reasons == ("cutover_primary_writer_fenced",)
    assert not primary_writer_decision_permits_write(decision)


def test_half_published_activation_pair_is_recovery_required(tmp_path: Path) -> None:
    """The atomic pair is never observable half-published, so this fails closed.

    Writes stay rejected here exactly as they are for every complete
    writer-fenced state, but the chain is not a supported state at all: it is
    recovery-required, and recovery stays forward-only.
    """

    decision = _seeded_rehearsal_decision(tmp_path, _HALF_PUBLISHED_COUNT)
    assert decision.state == "recovery_required"
    assert decision.writer_class == PRIMARY_WRITER_REJECTED
    assert decision.recovery_required is True
    assert decision.reasons == ("cutover_activation_pair_incomplete",)
    assert primary_writer_decision_permits_write(decision) is False


@pytest.mark.parametrize("mutation", ["tamper", "skip", "binding", "schema", "extra"])
def test_malformed_state_rejects_with_recovery_required(
    tmp_path: Path, mutation: str
) -> None:
    def _mutate(records: list[dict]) -> None:
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

    decision = _seeded_rehearsal_decision(tmp_path, 2, mutate=_mutate)
    assert decision.state == "recovery_required"
    assert decision.writer_class == PRIMARY_WRITER_REJECTED
    assert decision.recovery_required is True
    assert decision.reasons and all(reason.startswith("cutover_") for reason in decision.reasons)
    assert not primary_writer_decision_permits_write(decision)


def test_unreadable_store_and_config_disagreement_fail_closed(tmp_path: Path) -> None:
    unreadable = _rehearsal_config(tmp_path, "unreadable")
    root = Path(unreadable.subjective_mem_retrieval_cutover_store_root or "")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text("not a directory", encoding="utf-8")
    unreadable_decision = resolve_subjective_mem_retrieval_primary_writer_decision(
        unreadable
    )
    assert unreadable_decision.recovery_required is True
    assert not primary_writer_decision_permits_write(unreadable_decision)
    for foreign in (None, object(), {"subjective_mem_retrieval_cutover_mode": "primary_only"}):
        decision = resolve_subjective_mem_retrieval_primary_writer_decision(foreign)
        assert decision.reasons == ("cutover_writer_config_invalid",)
        assert not primary_writer_decision_permits_write(decision)


def test_no_unbound_default_or_optional_permit_class_exists() -> None:
    signature = inspect.signature(SubjectiveMemRetrievalPrimaryWriterDecision)
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    resolver = inspect.signature(resolve_subjective_mem_retrieval_primary_writer_decision)
    assert list(resolver.parameters) == ["config"]
    assert resolver.parameters["config"].default is inspect.Parameter.empty
    # Exactly two writer classes; no third `unbound` or compatibility class.
    module = Path("relaylm/subjective_mem_retrieval_cutover.py").read_text()
    assert "unbound" not in module
    for absent in (None, "permitted", 0, False, {"writer_class": PRIMARY_WRITER_PERMITTED}):
        assert not primary_writer_decision_permits_write(absent)
    # The guard stays exact: it never became a generic exception swallower.
    guard = inspect.getsource(primary_writer_decision_permits_write)
    assert "except SubjectiveMemRetrievalCutoverError:" in guard
    assert "except Exception" not in guard and "except:" not in guard


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"schema_version": 2}, "schema_unsupported"),
        ({"state": "subjective_serving"}, "state_invalid"),
        ({"writer_class": "unbound"}, "class_invalid"),
        ({"recovery_required": 1}, "boolean_invalid"),
        ({"runtime_private_evidence_omitted": False}, "boolean_invalid"),
        ({"reasons": ["cutover_x"]}, "reasons_invalid"),
        ({"reasons": ("../private",)}, "reasons_invalid"),
        ({"reasons": tuple(f"cutover_r{index}" for index in range(9))}, "reasons_invalid"),
        ({"state": "primary_writer_fenced"}, "class_state_mismatch"),
        ({"recovery_required": True}, "recovery_mismatch"),
        ({"reasons": ("cutover_extra",)}, "reasons_invalid"),
    ],
)
def test_invalid_decision_construction_fails_closed(change: dict, reason: str) -> None:
    with pytest.raises(SubjectiveMemRetrievalCutoverError, match=reason):
        _decision(**change)


def test_tampered_frozen_decision_is_revalidated_and_fails_closed() -> None:
    fenced = _decision(
        state="primary_writer_fenced",
        writer_class=PRIMARY_WRITER_REJECTED,
        reasons=("cutover_primary_writer_fenced",),
    )
    assert not primary_writer_decision_permits_write(fenced)
    object.__setattr__(fenced, "writer_class", PRIMARY_WRITER_PERMITTED)
    assert not primary_writer_decision_permits_write(fenced)
    object.__setattr__(fenced, "writer_class", "unbound")
    assert not primary_writer_decision_permits_write(fenced)


def test_exact_decision_with_no_initialized_fields_returns_false() -> None:
    decision = object.__new__(SubjectiveMemRetrievalPrimaryWriterDecision)
    assert primary_writer_decision_permits_write(decision) is False


@pytest.mark.parametrize(
    "missing_field",
    (
        "schema_version",
        "state",
        "writer_class",
        "recovery_required",
        "reasons",
        "runtime_private_evidence_omitted",
    ),
)
def test_partial_exact_decision_with_each_missing_field_returns_false(
    missing_field: str,
) -> None:
    decision = _decision()
    object.__delattr__(decision, missing_field)
    assert primary_writer_decision_permits_write(decision) is False


class _RaisingEquality:
    def __eq__(self, other: object) -> bool:
        raise AssertionError("malformed field equality must not execute")


@pytest.mark.parametrize("field", ["schema_version", "state", "writer_class"])
def test_hostile_equality_field_returns_false_without_comparison(field: str) -> None:
    decision = _decision()
    object.__setattr__(decision, field, _RaisingEquality())
    assert primary_writer_decision_permits_write(decision) is False


@pytest.mark.parametrize("unhashable", [[], {}, set(), bytearray(b"x")])
@pytest.mark.parametrize("field", ["state", "writer_class", "reasons"])
def test_unhashable_tampered_field_fails_closed_without_raising(
    field: str, unhashable: object
) -> None:
    """A corrupted decision must converge to False, never to a raised TypeError.

    A frozen dataclass can still be corrupted through ``object.__setattr__``.
    Validating a field with set membership would raise ``TypeError`` for an
    unhashable value, escaping the single stable error identity every caller
    catches, so the validator has to stay total over arbitrary field values.
    """
    decision = _decision()
    assert primary_writer_decision_permits_write(decision) is True
    object.__setattr__(decision, field, unhashable)
    assert primary_writer_decision_permits_write(decision) is False
    with pytest.raises(
        SubjectiveMemRetrievalCutoverError, match="primary_writer_decision_"
    ):
        decision.__post_init__()


def _imported_modules(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text())
    return {
        "." * node.level + node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_resolver_dependency_direction_creates_no_cycle() -> None:
    import relaylm.config as config_module
    import relaylm.subjective_mem_retrieval_cutover as owner

    # The owner depends on the config model; the config model depends on
    # nothing inside ``relaylm``, so taking `RelayLMConfig` as the resolver
    # input cannot close a cycle.
    assert _imported_modules(config_module.__file__ or "") == {
        "__future__",
        "os",
        "pathlib",
        "typing",
        "yaml",
        "pydantic",
    }
    # Exact set equality, not a subset: the facade depends one-way on the two
    # authorized private RT-1D-R4 owners, and on nothing else new. Neither
    # private owner imports the facade, so the direction cannot close a cycle.
    assert _imported_modules(owner.__file__ or "") == {
        "__future__",
        "dataclasses",
        "typing",
        "._subjective_mem_retrieval_cutover_activation",
        "._subjective_mem_retrieval_runtime_projection",
        ".config",
        ".evidence.common",
        ".evidence.store",
    }


def test_structure_and_immutable_store() -> None:
    module = Path("relaylm/subjective_mem_retrieval_cutover.py")
    # The merged RT-1D-R4 cutover-facade structural amendment (PR #831) replaced
    # the earlier roughly-700 gate with one measured RT-1D-R4-only exception:
    # the facade must remain strictly below 1000 normally formatted lines.
    assert len(module.read_text().splitlines()) < 1000
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
        hashlib.sha256(Path("relaylm/evidence/store.py").read_bytes()).hexdigest()
        == "4d90f539c3efc661cd7994a9b059aa5db1744f2cc761da409afad67c809d50be"
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
