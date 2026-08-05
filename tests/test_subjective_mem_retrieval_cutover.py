from __future__ import annotations

import ast
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
    PRIMARY_WRITER_DECISION_SCHEMA_VERSION,
    PRIMARY_WRITER_PERMITTED,
    PRIMARY_WRITER_REJECTED,
    SubjectiveMemRetrievalCutoverBinding,
    SubjectiveMemRetrievalCutoverError,
    SubjectiveMemRetrievalCutoverRequest,
    SubjectiveMemRetrievalPrimaryWriterDecision,
    primary_writer_decision_permits_write,
    rehearse_subjective_mem_retrieval_cutover,
    resolve_subjective_mem_retrieval_primary_writer_decision,
    evaluate_subjective_mem_retrieval_rehearsal_readiness,
    subjective_mem_retrieval_rehearsal_readiness_id,
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
    assert canonical_digest(binding.to_dict()) == canonical_digest(
        _binding().to_dict()
    )
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


# ---------------------------------------------------------------------------
# RT-1D-R2A: the sole immutable Primary writer decision, its resolver, and the
# exact state-to-writer mapping.
# ---------------------------------------------------------------------------


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
    return SubjectiveMemRetrievalPrimaryWriterDecision(**values)  # type: ignore[arg-type]


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
    monkeypatch.setattr(owner, "reconstruct_cutover_chain", _forbidden)
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
        if _STATES[count - 1] != "subjective_reader_enabled"
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


def test_a_chain_ending_at_reader_enablement_is_never_reconstructible(
    tmp_path: Path,
) -> None:
    """Enablement and the finalized receipt publish atomically, so a chain that
    holds only the first is partial durable state, not an accepted state."""

    count = _STATES.index("subjective_reader_enabled") + 1
    decision = _seeded_rehearsal_decision(tmp_path, count)
    assert decision.state == "recovery_required"
    assert decision.recovery_required is True
    assert decision.reasons == ("cutover_activation_pair_incomplete",)
    assert not primary_writer_decision_permits_write(decision)


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
    assert _imported_modules(owner.__file__ or "") == {
        "__future__",
        "dataclasses",
        "typing",
        "._subjective_mem_retrieval_cutover_activation",
        "._subjective_mem_retrieval_runtime_projection",
        ".config",
        ".evidence_common",
        ".evidence_store",
        ".subjective_mem_retrieval_rehearsal",
    }
    # The private mechanics owners never import back, so the direction is one-way.
    for private in (
        "relaylm/_subjective_mem_retrieval_cutover_activation.py",
        "relaylm/_subjective_mem_retrieval_runtime_projection.py",
    ):
        imported = _imported_modules(private)
        assert ".subjective_mem_retrieval_cutover" not in imported
        assert ".config" not in imported
    assert ".subjective_mem_retrieval_selection" not in _imported_modules(
        "relaylm/_subjective_mem_retrieval_runtime_projection.py"
    )


def test_structure_and_immutable_store() -> None:
    # The RT-1D-R4 cutover-facade structural budget amendment replaced the
    # roughly-700 gate with one measured, RT-1D-R4-only strict-below-1000 gate;
    # each private mechanics owner stays below roughly 600 lines.
    module = Path("relaylm/subjective_mem_retrieval_cutover.py")
    assert len(module.read_text().splitlines()) < 1000
    for private in (
        "relaylm/_subjective_mem_retrieval_cutover_activation.py",
        "relaylm/_subjective_mem_retrieval_runtime_projection.py",
    ):
        assert len(Path(private).read_text().splitlines()) < 600
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


# ---------------------------------------------------------------------------
# RT-1D-R4 requested mode, ordinary reader decision, and one-authority
# activation. Configuration is a deployment request throughout: only the exact
# finalized durable transfer receipt ever authorizes Subjective serving.
# ---------------------------------------------------------------------------

from relaylm._subjective_mem_retrieval_cutover_activation import (  # noqa: E402
    ACTIVATION_STEPS,
    advance_cutover_chain,
)
from relaylm.subjective_mem_retrieval import (  # noqa: E402
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalRequest,
)
from relaylm.subjective_mem_retrieval_characterization import (  # noqa: E402
    SubjectiveMemRetrievalPrimaryServedMetrics,
)
from relaylm.subjective_mem_retrieval_cutover import (  # noqa: E402
    SubjectiveMemRetrievalPrimaryReaderDecision,
    activate_subjective_mem_retrieval_cutover,
    subjective_mem_retrieval_cutover_binding_from_config,
    resolve_subjective_mem_retrieval_primary_reader_decision,
    subjective_mem_retrieval_primary_reader_class,
)
from relaylm.subjective_mem_retrieval_projection import (  # noqa: E402
    build_subjective_mem_retrieval_projection,
)
import relaylm.subjective_mem_retrieval_rehearsal as _rehearsal  # noqa: E402
from test_subjective_mem_retrieval_projection import _one_active  # noqa: E402

_NEITHER_STATES = (
    "primary_reader_fenced",
    "primary_writer_fenced",
    "subjective_generation_bound",
)
_SERVING_STATES = (
    "transfer_receipt_finalized",
    "post_transfer_validated",
    "retirement_complete",
)


def _subjective_config(tmp_path: Path, **changes: object) -> RelayLMConfig:
    values = _config_tuple(tmp_path / "store")
    values["subjective_mem_retrieval_cutover_mode"] = "subjective_only"
    values["subjective_mem_retrieval_projection_root"] = str(tmp_path / "projection")
    values.update(changes)
    return _config(values)


def test_subjective_only_requires_the_one_distinct_projection_root(
    tmp_path: Path,
) -> None:
    assert _subjective_config(tmp_path).subjective_mem_retrieval_projection_root
    values = _config_tuple(tmp_path / "store")
    values["subjective_mem_retrieval_cutover_mode"] = "subjective_only"
    with pytest.raises(ValueError, match="requires_projection_root"):
        _config(values)
    with pytest.raises(ValueError, match="projection_root_invalid"):
        _subjective_config(tmp_path, subjective_mem_retrieval_projection_root="relative")
    with pytest.raises(ValueError, match="projection_root_not_distinct"):
        _subjective_config(
            tmp_path,
            subjective_mem_retrieval_projection_root=str(tmp_path / "store"),
        )


@pytest.mark.parametrize("mode", ["primary_only", "rehearsal"])
def test_no_other_mode_may_carry_the_ordinary_projection_root(
    tmp_path: Path, mode: str
) -> None:
    values = _config_tuple(tmp_path / "store") if mode == "rehearsal" else {}
    values = {
        **values,
        "subjective_mem_retrieval_cutover_mode": mode,
        "subjective_mem_retrieval_projection_root": str(tmp_path / "projection"),
    }
    expected = (
        "requires_empty_tuple"
        if mode == "primary_only"
        else "projection_root_requires_subjective_only"
    )
    with pytest.raises(ValueError, match=expected):
        _config(values)


def _reader_decision(tmp_path: Path, count: int) -> SubjectiveMemRetrievalPrimaryReaderDecision:
    """Seed an exact chain of ``count`` states, then resolve the reader decision."""

    config = _subjective_config(tmp_path / f"chain-{count}")
    root = config.subjective_mem_retrieval_cutover_store_root
    assert root is not None
    binding = _binding()
    _seed(EvidenceRecordStore(root), binding, _records(binding, count))
    return resolve_subjective_mem_retrieval_primary_reader_decision(config)


@pytest.mark.parametrize("count", range(1, _STATES.index("primary_reader_fenced") + 1))
def test_primary_alone_serves_before_the_durable_reader_fence(
    tmp_path: Path, count: int
) -> None:
    decision = _reader_decision(tmp_path, count)
    assert decision.state == _STATES[count - 1]
    assert decision.reader_class == "primary_only"
    assert decision.reasons == ()
    assert subjective_mem_retrieval_primary_reader_class(decision) == "primary_only"


@pytest.mark.parametrize("state", _NEITHER_STATES)
def test_neither_authority_serves_between_the_reader_fence_and_the_receipt(
    tmp_path: Path, state: str
) -> None:
    decision = _reader_decision(tmp_path, _STATES.index(state) + 1)
    assert decision.state == state
    assert decision.reader_class == "neither"
    assert decision.reasons == ("cutover_primary_reader_fenced",)


@pytest.mark.parametrize("state", _SERVING_STATES)
def test_only_the_exact_finalized_receipt_authorizes_subjective_serving(
    tmp_path: Path, state: str
) -> None:
    decision = _reader_decision(tmp_path, _STATES.index(state) + 1)
    assert decision.state == state
    assert decision.reader_class == "subjective_only"
    assert subjective_mem_retrieval_primary_reader_class(decision) == "subjective_only"


def test_configuration_alone_never_serves_subjective(tmp_path: Path) -> None:
    """A requested `subjective_only` deployment with no durable chain at all is
    still exactly Primary; configuration is a request, never authority."""

    decision = resolve_subjective_mem_retrieval_primary_reader_decision(
        _subjective_config(tmp_path)
    )
    assert (decision.state, decision.reader_class) == ("primary_stable", "primary_only")


@pytest.mark.parametrize("mutation", ["tamper", "skip", "binding"])
def test_a_divergent_chain_fails_closed_for_the_reader(
    tmp_path: Path, mutation: str
) -> None:
    config = _subjective_config(tmp_path / mutation)
    root = config.subjective_mem_retrieval_cutover_store_root
    assert root is not None
    binding = _binding()
    records = _records(binding, len(_STATES))
    if mutation == "tamper":
        records[-1]["record_digest"] = "0" * 64
    elif mutation == "skip":
        del records[3]
    else:
        records[-1]["binding_digest"] = "0" * 64
    _seed(EvidenceRecordStore(root), binding, records)
    decision = resolve_subjective_mem_retrieval_primary_reader_decision(config)
    assert decision.reader_class == "neither"
    assert decision.recovery_required is True
    assert subjective_mem_retrieval_primary_reader_class(decision) == "neither"


def test_only_a_valid_decision_value_can_release_an_authority() -> None:
    for forged in (None, "subjective_only", object(), _decision()):
        assert subjective_mem_retrieval_primary_reader_class(forged) == "neither"


def _activation_environment(tmp_path: Path, last_state: str | None = None):
    """One complete `subjective_only` deployment, its binding, and its proof."""

    from test_rt1d_reader_seams import _subjective_environment

    config, _route, _source, _revision, _root, readiness = _subjective_environment(
        tmp_path, last_state
    )
    binding = subjective_mem_retrieval_cutover_binding_from_config(config)
    assert binding is not None
    store = EvidenceRecordStore(str(config.subjective_mem_retrieval_cutover_store_root))
    return config, binding, readiness, store


def test_activation_publishes_the_whole_chain_and_replays_idempotently(
    tmp_path: Path,
) -> None:
    config, binding, readiness, store = _activation_environment(tmp_path)
    result = activate_subjective_mem_retrieval_cutover(
        config=config, readiness=readiness
    )
    assert result.state == "transfer_receipt_finalized"
    assert result.authority_class == "subjective_only"
    assert result.reasons == ()
    assert result.diagnostics.subjective_serving is True
    assert result.diagnostics.reader_fence and result.diagnostics.writer_fence

    with store.transaction(binding.evidence_space_id) as transaction:
        chain = transaction.read_log(log_kind=CUTOVER_LOG_KIND, key=CUTOVER_LOG_KEY)
    assert [record["state"] for record in chain] == list(
        _STATES[: _STATES.index("transfer_receipt_finalized") + 1]
    )

    replay = activate_subjective_mem_retrieval_cutover(
        config=config, readiness=readiness
    )
    assert replay == result
    with store.transaction(binding.evidence_space_id) as transaction:
        assert transaction.read_log(log_kind=CUTOVER_LOG_KIND, key=CUTOVER_LOG_KEY) == chain


def test_reader_enablement_and_the_receipt_publish_in_one_transaction(
    tmp_path: Path,
) -> None:
    _config, binding, _readiness, store = _activation_environment(tmp_path)
    for step in ACTIVATION_STEPS[:-1]:
        state, reasons = advance_cutover_chain(store, binding.to_dict(), step)
        assert reasons == () and state == step[-1]
    assert ACTIVATION_STEPS[-1] == (
        "subjective_reader_enabled",
        "transfer_receipt_finalized",
    )
    # Nothing has served yet: the last complete state is still pre-receipt.
    assert _reader_class_of(store, binding) == "neither"
    state, reasons = advance_cutover_chain(store, binding.to_dict(), ACTIVATION_STEPS[-1])
    assert reasons == () and state == "transfer_receipt_finalized"
    assert _reader_class_of(store, binding) == "subjective_only"


def _reader_class_of(store: EvidenceRecordStore, binding) -> str:
    from relaylm._subjective_mem_retrieval_cutover_activation import (
        reconstruct_cutover_chain,
    )

    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    assert reasons == ()
    return "subjective_only" if state == "transfer_receipt_finalized" else "neither"


def test_activation_refuses_a_foreign_readiness_proof_before_any_durable_write(
    tmp_path: Path,
) -> None:
    config, binding, readiness, store = _activation_environment(tmp_path)
    for forged in ("ready-1", object()):
        result = activate_subjective_mem_retrieval_cutover(
            config=config, readiness=forged
        )
        assert result.state == "primary_stable"
        assert result.authority_class == "primary_only"
        assert result.diagnostics.subjective_serving is False
    foreign = config.model_copy(
        update={"subjective_mem_retrieval_cutover_deployment_id": "deployment-2"}
    )
    result = activate_subjective_mem_retrieval_cutover(
        config=foreign, readiness=readiness
    )
    assert result.state == "primary_stable"
    with store.transaction(binding.evidence_space_id) as transaction:
        assert not transaction.read_log(log_kind=CUTOVER_LOG_KIND, key=CUTOVER_LOG_KEY)


def test_an_ambiguous_transferred_character_scope_fails_closed(tmp_path: Path) -> None:
    """One generation per projection root means exactly one transferred character."""

    config, binding, readiness, store = _activation_environment(tmp_path)
    characters = dict(config.characters)
    ambiguous = config.model_copy(
        update={"characters": {**characters, "other": next(iter(characters.values()))}}
    )
    result = activate_subjective_mem_retrieval_cutover(
        config=ambiguous, readiness=readiness
    )
    assert result.state == "primary_stable"
    assert result.reasons == ("subjective_mem_retrieval_route_locator_missing",)
    with store.transaction(binding.evidence_space_id) as transaction:
        assert not transaction.read_log(log_kind=CUTOVER_LOG_KIND, key=CUTOVER_LOG_KEY)


def test_rehearsal_and_activation_never_accept_each_other_s_mode(
    tmp_path: Path,
) -> None:
    config, binding, readiness, store = _activation_environment(tmp_path)
    with pytest.raises(
        SubjectiveMemRetrievalCutoverError, match="cutover_rehearsal_mode_unsupported"
    ):
        rehearse_subjective_mem_retrieval_cutover(
            store=store,
            binding=binding,
            request=SubjectiveMemRetrievalCutoverRequest("subjective_only"),
        )
    rehearsal = config.model_copy(
        update={
            "subjective_mem_retrieval_cutover_mode": "rehearsal",
            "subjective_mem_retrieval_projection_root": None,
        }
    )
    result = activate_subjective_mem_retrieval_cutover(
        config=rehearsal, readiness=readiness
    )
    assert result.reasons == ("cutover_activation_mode_unsupported",)
    assert result.authority_class == "primary_only"
