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
    characterize_subjective_mem_retrieval_shadow,
)
from relaylm.subjective_mem_retrieval_projection import (
    SubjectiveMemRetrievalProjectionSource,
    build_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem_retrieval_selection import (
    select_subjective_mem_retrieval_handoff,
)


def _inputs(root: Path):
    source = SubjectiveMemRetrievalProjectionSource(
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
        attempted=True, candidate_count=0, selected_count=0,
        latency_class="within_bound",
    )
    _, shadow = select_subjective_mem_retrieval_handoff(
        request=request, manifest=projection.manifest, rows=projection.rows,
        canonical_pages=(), shadow=True,
    )
    characterization, reasons = characterize_subjective_mem_retrieval_shadow(
        primary=primary, shadow=shadow, replay=shadow,
        subjective_latency_class="within_bound",
        projection_rebuild_equivalent=True,
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
        specification=specification,
        projection=projection,
        characterization=characterization,
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
