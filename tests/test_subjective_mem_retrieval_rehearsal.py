from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_rehearsal as owner
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalRequest,
)
from relaylm.subjective_mem_retrieval_characterization import (
    SubjectiveMemRetrievalPrimaryServedMetrics,
)
from relaylm.subjective_mem_retrieval_projection import (
    SubjectiveMemRetrievalProjectionSource,
    build_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem_retrieval_projection_store import (
    PROJECTION_BUNDLE_FILENAME,
    write_subjective_mem_retrieval_projection,
)
from test_subjective_mem_retrieval_projection import _one_active


def _inputs(root: Path, *, populated: bool = False):
    source = _one_active()[3] if populated else SubjectiveMemRetrievalProjectionSource(
        evidence_space_id="space-1",
        character_id="character-1",
        workspace_authority_digest="a" * 64,
        admitted_scope_binding_digest="b" * 64,
        snapshot_taken_at="2026-08-03T00:00:00Z",
        entries=(),
    )
    projection, reasons = build_subjective_mem_retrieval_projection(source)
    assert reasons == () and projection is not None
    request = SubjectiveMemRetrievalRequest(
        character_id=source.character_id,
        workspace_authority_digest=source.workspace_authority_digest,
        admitted_scope_binding_digest=source.admitted_scope_binding_digest,
        query_plan_digest="c" * 64,
        request_correlation_digest="d" * 64,
        projection_generation_id=projection.manifest.projection_generation_id,
        projection_manifest_digest=projection.manifest.manifest_digest,
        memory_kinds=("episodic", "semantic"),
        candidate_limit=8,
        token_budget=256,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
        boundary=SubjectiveMemRetrievalBoundary(),
    )
    primary = SubjectiveMemRetrievalPrimaryServedMetrics(
        attempted=True, candidate_count=len(projection.rows), selected_count=0,
        latency_class="within_bound",
    )
    characterization, reasons = owner._characterize(
        source, request, projection, projection, primary, "within_bound"
    )
    assert reasons == () and characterization is not None
    specification = owner.SubjectiveMemRetrievalRehearsalSpecification(
        binding_identity=(("deployment_id", "deployment-1"),),
        evidence_space_id=source.evidence_space_id,
        projection_generation_id=source.projection_generation_id,
        projection_source_digest=source.source_snapshot_digest,
        readiness_id="pending",
    )
    readiness_id = owner.derive_subjective_mem_retrieval_rehearsal_readiness_id(
        binding_identity=specification.binding_identity,
        projection_generation_id=projection.manifest.projection_generation_id,
        projection_source_digest=projection.manifest.source_snapshot_digest,
        projection_manifest_digest=projection.manifest.manifest_digest,
        row_population_digest=owner.canonical_digest(
            [row.row_digest for row in projection.rows]
        ),
        characterization_digest=owner.canonical_digest(characterization.to_dict()),
    )
    root.mkdir()
    return replace(specification, readiness_id=readiness_id), source, request, primary


def test_rehearsal_proves_exact_disposable_generation(tmp_path: Path) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert reasons == () and readiness is not None
    assert list(root.iterdir()) == []
    assert readiness.readiness_id == specification.readiness_id
    assert not readiness.subjective_serving
    assert not readiness.ordinary_usage_event_recorded
    assert not readiness.authority_state_written
    with pytest.raises(TypeError):
        owner.SubjectiveMemRetrievalRehearsalReadiness()  # type: ignore[call-arg]


def test_rehearsal_proves_nonempty_ordered_population(tmp_path: Path) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root, populated=True)
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert reasons == () and readiness is not None
    assert readiness.row_population_digest != owner.canonical_digest([])
    assert list(root.iterdir()) == []


def test_factory_proof_owns_flags_and_rejects_forged_identities(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert reasons == () and readiness is not None
    monkeypatch.setattr(owner.SubjectiveMemRetrievalRehearsalReadiness,
                        "subjective_serving", True, raising=False)
    assert readiness.subjective_serving is False
    with pytest.raises(TypeError):
        replace(readiness, authority_state_written=True)

    for field in (
        "readiness_id", "projection_generation_id", "projection_source_digest",
        "projection_manifest_digest", "row_population_digest",
        "characterization_digest",
    ):
        forged = object.__new__(owner.SubjectiveMemRetrievalRehearsalReadiness)
        for name in readiness.__dataclass_fields__:
            if hasattr(readiness, name):
                object.__setattr__(forged, name, getattr(readiness, name))
        object.__setattr__(forged, field, (
            "smretrievalready_" + "f" * 64 if field == "readiness_id"
            else "smretrievalgen_" + "f" * 64 if field == "projection_generation_id"
            else "f" * 64
        ))
        assert owner.validate_subjective_mem_retrieval_rehearsal_readiness(
            specification=specification, readiness=forged
        )

    forged = object.__new__(owner.SubjectiveMemRetrievalRehearsalReadiness)
    for name in readiness.__dataclass_fields__:
        if hasattr(readiness, name):
            object.__setattr__(forged, name, getattr(readiness, name))
    object.__delattr__(forged, "_factory_marker")
    assert owner.validate_subjective_mem_retrieval_rehearsal_readiness(
        specification=specification, readiness=forged
    ) == ("cutover_readiness_proof_factory_invalid",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("binding_identity", (("z", "one"), ("a", "two"))),
        ("evidence_space_id", "../unsafe"),
        ("projection_generation_id", "f" * 64),
        ("projection_source_digest", "wrong"),
        ("readiness_id", "ready"),
    ],
)
def test_malformed_specification_precedes_projection_store_effects(
    monkeypatch, tmp_path: Path, field: str, value: object
) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    malformed = replace(specification, **{field: value})
    monkeypatch.setattr(
        owner, "read_subjective_mem_retrieval_projection",
        lambda **_kwargs: pytest.fail("store effect before specification validation"),
    )
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=malformed, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == ("cutover_readiness_specification_invalid",)


def test_rehearsal_preserves_every_preexisting_bundle(tmp_path: Path) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    bundle = root / "subjective-mem-retrieval-projection.json"
    original = b"foreign-or-corrupt"
    bundle.write_bytes(original)
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == ("cutover_readiness_projection_root_not_fresh",)
    assert bundle.read_bytes() == original


@pytest.mark.parametrize("kind", ["exact", "stale", "unsafe", "unreadable"])
def test_rehearsal_rejects_each_preexisting_bundle_class(
    monkeypatch, tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    target = root / PROJECTION_BUNDLE_FILENAME
    if kind in {"exact", "stale"}:
        stored_source = source if kind == "exact" else replace(
            source, snapshot_taken_at="2026-08-04T00:00:00Z"
        )
        projection, reasons = build_subjective_mem_retrieval_projection(stored_source)
        assert reasons == () and projection is not None
        assert write_subjective_mem_retrieval_projection(
            projection_root=str(root), source=stored_source, projection=projection
        ) == ()
        before = target.read_bytes()
    elif kind == "unsafe":
        target.symlink_to(root / "missing")
        before = target.readlink()
    else:
        target.write_bytes(b"unreadable")
        before = target.read_bytes()
        monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(OSError()))
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == ("cutover_readiness_projection_root_not_fresh",)
    if kind == "unsafe":
        assert target.is_symlink() and target.readlink() == before
    elif kind == "unreadable":
        assert target.exists()
    else:
        assert target.read_bytes() == before


def test_failed_write_never_reads_or_deletes(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    real_read = owner.read_subjective_mem_retrieval_projection
    calls = 0

    def preflight_only(**kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1
        return real_read(**kwargs)

    monkeypatch.setattr(owner, "read_subjective_mem_retrieval_projection", preflight_only)
    monkeypatch.setattr(
        owner, "write_subjective_mem_retrieval_projection",
        lambda **_kwargs: ("subjective_mem_retrieval_projection_write_failed",),
    )
    monkeypatch.setattr(
        owner, "delete_subjective_mem_retrieval_projection",
        lambda **_kwargs: pytest.fail("delete after failed write"),
    )
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == ("subjective_mem_retrieval_projection_write_failed",)


def test_failed_trusted_read_never_deletes(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    real_read = owner.read_subjective_mem_retrieval_projection
    calls = 0

    def fail_second_read(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
        return real_read(**kwargs)

    monkeypatch.setattr(owner, "read_subjective_mem_retrieval_projection", fail_second_read)
    monkeypatch.setattr(
        owner, "delete_subjective_mem_retrieval_projection",
        lambda **_kwargs: pytest.fail("delete without trusted installation ownership"),
    )
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == ("subjective_mem_retrieval_projection_bundle_unreadable",)


@pytest.mark.parametrize("post_delete_failure", [False, True])
def test_delete_and_post_delete_failures_return_no_proof(
    monkeypatch, tmp_path: Path, post_delete_failure: bool
) -> None:
    root = tmp_path / "exclusive"
    specification, source, request, primary = _inputs(root)
    if post_delete_failure:
        real_read = owner.read_subjective_mem_retrieval_projection
        calls = 0

        def fail_final_read(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
            return real_read(**kwargs)

        monkeypatch.setattr(owner, "read_subjective_mem_retrieval_projection", fail_final_read)
    else:
        monkeypatch.setattr(
            owner, "delete_subjective_mem_retrieval_projection",
            lambda **_kwargs: ("subjective_mem_retrieval_projection_delete_failed",),
        )
    readiness, reasons = owner.evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification, source=source, projection_root=str(root),
        request=request, primary=primary, subjective_latency_class="within_bound",
    )
    assert readiness is None
    assert reasons == (("cutover_readiness_projection_delete_unverified",)
                       if post_delete_failure else
                       ("subjective_mem_retrieval_projection_delete_failed",))
