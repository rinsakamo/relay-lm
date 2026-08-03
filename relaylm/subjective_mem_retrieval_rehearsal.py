"""Temporary, content-free RT-1D rehearsal coordinator.

This module owns the disposable projection build/store/delete/rebuild proof.  It
does not own cutover semantics, configuration, serving, or durable authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .evidence_common import canonical_digest
from .subjective_mem_retrieval import (
    SubjectiveMemRetrievalRequest,
    validate_subjective_mem_retrieval_request,
)
from .subjective_mem_retrieval_characterization import (
    RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED,
    SubjectiveMemRetrievalPrimaryServedMetrics,
    SubjectiveMemRetrievalShadowCharacterization,
    characterize_subjective_mem_retrieval_shadow,
)
from .subjective_mem_retrieval_projection import (
    SubjectiveMemRetrievalProjection,
    SubjectiveMemRetrievalProjectionSource,
    build_subjective_mem_retrieval_projection,
)
from .subjective_mem_retrieval_projection_store import (
    delete_subjective_mem_retrieval_projection,
    read_subjective_mem_retrieval_projection,
    write_subjective_mem_retrieval_projection,
)
from .subjective_mem_retrieval_selection import (
    SubjectiveMemRetrievalCanonicalPageBinding,
    select_subjective_mem_retrieval_handoff,
)

READINESS_SCHEMA = "relaylm.subjective_mem_retrieval_rehearsal_readiness.v1"
READINESS_PREFIX = "smretrievalready_"


@dataclass(frozen=True)
class SubjectiveMemRetrievalRehearsalSpecification:
    """Immutable content-free instruction supplied by the cutover owner."""

    binding_identity: tuple[tuple[str, object], ...]
    evidence_space_id: str
    projection_generation_id: str
    projection_source_digest: str
    readiness_id: str


@dataclass(frozen=True, init=False)
class SubjectiveMemRetrievalRehearsalReadiness:
    """Factory-only proof value; it grants no serving or write authority."""

    readiness_id: str
    projection_generation_id: str
    projection_source_digest: str
    projection_manifest_digest: str
    row_population_digest: str
    characterization_digest: str
    subjective_serving: bool = field(default=False, init=False)
    ordinary_usage_event_recorded: bool = field(default=False, init=False)
    authority_state_written: bool = field(default=False, init=False)

    def __new__(cls):
        raise TypeError("subjective_mem_retrieval_readiness_factory_required")

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def derive_subjective_mem_retrieval_rehearsal_readiness_id(
    *,
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    projection: SubjectiveMemRetrievalProjection,
    characterization: SubjectiveMemRetrievalShadowCharacterization,
) -> str:
    """Derive the exact readiness identity from every proof component."""

    digest = canonical_digest(
        {
            "schema": READINESS_SCHEMA,
            "binding": dict(specification.binding_identity),
            "manifest": projection.manifest.to_digest_input(),
            "rows": [row.row_digest for row in projection.rows],
            "characterization_digest": canonical_digest(characterization.to_dict()),
        }
    )
    return f"{READINESS_PREFIX}{digest}"


def evaluate_subjective_mem_retrieval_rehearsal(
    *,
    specification: object,
    source: object,
    projection_root: object,
    request: object,
    primary: object,
    subjective_latency_class: object,
) -> tuple[SubjectiveMemRetrievalRehearsalReadiness | None, tuple[str, ...]]:
    """Run one exclusive disposable rehearsal and return a closed proof."""

    reasons = _input_reasons(specification, source, request, primary)
    if reasons:
        return None, reasons
    assert isinstance(specification, SubjectiveMemRetrievalRehearsalSpecification)
    assert isinstance(source, SubjectiveMemRetrievalProjectionSource)
    assert isinstance(request, SubjectiveMemRetrievalRequest)
    built, reasons = build_subjective_mem_retrieval_projection(source)
    if built is None:
        return None, reasons
    if not _projection_matches(specification, source, request, built):
        return None, ("cutover_readiness_projection_binding_disagreement",)

    absent, preflight_reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if absent is not None or preflight_reasons != (
        "subjective_mem_retrieval_projection_absent",
    ):
        return None, ("cutover_readiness_projection_root_not_fresh",)
    write_reasons = write_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source, projection=built
    )
    if write_reasons:
        return None, write_reasons
    stored, read_reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if stored is None or read_reasons or stored != built:
        return None, read_reasons or ("cutover_readiness_stored_projection_disagreement",)
    delete_reasons = delete_subjective_mem_retrieval_projection(
        projection_root=projection_root
    )
    if delete_reasons:
        return None, delete_reasons
    remaining, final_reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if remaining is not None or final_reasons != (
        "subjective_mem_retrieval_projection_absent",
    ):
        return None, ("cutover_readiness_projection_delete_unverified",)
    rebuilt, rebuild_reasons = build_subjective_mem_retrieval_projection(source)
    if rebuilt is None or rebuild_reasons or rebuilt != stored:
        return None, rebuild_reasons or ("cutover_readiness_rebuild_disagreement",)
    characterization, reasons = _characterize(
        source, request, stored, rebuilt, primary, subjective_latency_class
    )
    if characterization is None:
        return None, reasons
    expected = derive_subjective_mem_retrieval_rehearsal_readiness_id(
        specification=specification,
        projection=rebuilt,
        characterization=characterization,
    )
    if specification.readiness_id != expected:
        return None, ("cutover_readiness_identity_disagreement",)
    return _readiness(expected, rebuilt, characterization), ()


def _input_reasons(
    specification: object, source: object, request: object, primary: object
) -> tuple[str, ...]:
    if type(specification) is not SubjectiveMemRetrievalRehearsalSpecification:
        return ("cutover_readiness_specification_invalid",)
    if type(source) is not SubjectiveMemRetrievalProjectionSource:
        return ("cutover_readiness_source_invalid",)
    if type(request) is not SubjectiveMemRetrievalRequest:
        return ("cutover_readiness_request_invalid",)
    if validate_subjective_mem_retrieval_request(request):
        return ("cutover_readiness_request_invalid",)
    if type(primary) is not SubjectiveMemRetrievalPrimaryServedMetrics:
        return ("cutover_readiness_primary_metrics_invalid",)
    return ()


def _projection_matches(
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    source: SubjectiveMemRetrievalProjectionSource,
    request: SubjectiveMemRetrievalRequest,
    projection: SubjectiveMemRetrievalProjection,
) -> bool:
    manifest = projection.manifest
    return (
        specification.evidence_space_id == source.evidence_space_id
        and specification.projection_generation_id == source.projection_generation_id
        == manifest.projection_generation_id
        == request.projection_generation_id
        and specification.projection_source_digest == source.source_snapshot_digest
        == manifest.source_snapshot_digest
        and request.projection_manifest_digest == manifest.manifest_digest
    )


def _characterize(
    source: SubjectiveMemRetrievalProjectionSource,
    request: SubjectiveMemRetrievalRequest,
    stored: SubjectiveMemRetrievalProjection,
    rebuilt: SubjectiveMemRetrievalProjection,
    primary: SubjectiveMemRetrievalPrimaryServedMetrics,
    latency: object,
) -> tuple[SubjectiveMemRetrievalShadowCharacterization | None, tuple[str, ...]]:
    pages = tuple(
        SubjectiveMemRetrievalCanonicalPageBinding(entry.canonical_page_bytes)
        for entry in source.entries
    )
    _, shadow = select_subjective_mem_retrieval_handoff(
        request=request, manifest=stored.manifest, rows=stored.rows,
        canonical_pages=pages, shadow=True,
    )
    _, replay = select_subjective_mem_retrieval_handoff(
        request=request, manifest=rebuilt.manifest, rows=rebuilt.rows,
        canonical_pages=pages, shadow=True,
    )
    value, reasons = characterize_subjective_mem_retrieval_shadow(
        primary=primary, shadow=shadow, replay=replay,
        subjective_latency_class=latency,
        projection_rebuild_equivalent=stored == rebuilt,
    )
    if value is None or reasons or not _characterization_ready(value):
        return None, reasons or ("cutover_readiness_characterization_not_ready",)
    return value, ()


def _characterization_ready(value: SubjectiveMemRetrievalShadowCharacterization) -> bool:
    return (
        value.deterministic_replay_class == "deterministic"
        and value.projection_rebuild_equivalence_class == "equivalent"
        and value.leakage_outcome == RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED
        and value.primary_latency_class == value.subjective_latency_class == "within_bound"
        and value.runtime_private_content_combined is False
    )


def _readiness(
    readiness_id: str,
    projection: SubjectiveMemRetrievalProjection,
    characterization: SubjectiveMemRetrievalShadowCharacterization,
) -> SubjectiveMemRetrievalRehearsalReadiness:
    value = object.__new__(SubjectiveMemRetrievalRehearsalReadiness)
    fields = {
        "readiness_id": readiness_id,
        "projection_generation_id": projection.manifest.projection_generation_id,
        "projection_source_digest": projection.manifest.source_snapshot_digest,
        "projection_manifest_digest": projection.manifest.manifest_digest,
        "row_population_digest": canonical_digest(
            [row.row_digest for row in projection.rows]
        ),
        "characterization_digest": canonical_digest(characterization.to_dict()),
    }
    for name, item in fields.items():
        object.__setattr__(value, name, item)
    return value


__all__ = [
    "SubjectiveMemRetrievalRehearsalReadiness",
    "SubjectiveMemRetrievalRehearsalSpecification",
    "derive_subjective_mem_retrieval_rehearsal_readiness_id",
    "evaluate_subjective_mem_retrieval_rehearsal",
]
