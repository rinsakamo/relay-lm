"""Temporary, content-free RT-1D rehearsal coordinator.

This module owns the disposable projection build/store/delete/rebuild proof. It
owns neither cutover semantics nor configuration, serving, or durable authority.
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
_GENERATION_PREFIX = "smretrievalgen_"
_FACTORY_MARKER = object()


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

    binding_identity: tuple[tuple[str, object], ...]
    readiness_id: str
    projection_generation_id: str
    projection_source_digest: str
    projection_manifest_digest: str
    row_population_digest: str
    characterization_digest: str
    subjective_serving: bool = field(init=False)
    ordinary_usage_event_recorded: bool = field(init=False)
    authority_state_written: bool = field(init=False)
    _factory_marker: object = field(init=False, repr=False, compare=False)

    def __new__(cls):
        raise TypeError("subjective_mem_retrieval_readiness_factory_required")

    def to_dict(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "_factory_marker"
        }


def derive_subjective_mem_retrieval_rehearsal_readiness_id(
    *,
    binding_identity: tuple[tuple[str, object], ...],
    projection_generation_id: str,
    projection_source_digest: str,
    projection_manifest_digest: str,
    row_population_digest: str,
    characterization_digest: str,
) -> str:
    """Derive the readiness identity from all consumer-verifiable identities."""

    digest = canonical_digest(
        {
            "schema": READINESS_SCHEMA,
            "binding": dict(binding_identity),
            "projection_generation_id": projection_generation_id,
            "projection_source_digest": projection_source_digest,
            "projection_manifest_digest": projection_manifest_digest,
            "row_population_digest": row_population_digest,
            "characterization_digest": characterization_digest,
        }
    )
    return f"{READINESS_PREFIX}{digest}"


def validate_subjective_mem_retrieval_rehearsal_readiness(
    *, specification: object, readiness: object
) -> tuple[str, ...]:
    """Re-derive every identity and reject non-factory or forged proof values."""

    if type(specification) is not SubjectiveMemRetrievalRehearsalSpecification:
        return ("cutover_readiness_specification_invalid",)
    if _specification_reasons(specification):
        return ("cutover_readiness_specification_invalid",)
    if type(readiness) is not SubjectiveMemRetrievalRehearsalReadiness:
        return ("cutover_readiness_proof_type_invalid",)
    required = tuple(
        name for name in readiness.__dataclass_fields__ if name != "_factory_marker"
    )
    if any(not hasattr(readiness, name) for name in required):
        return ("cutover_readiness_proof_incomplete",)
    if getattr(readiness, "_factory_marker", None) is not _FACTORY_MARKER:
        return ("cutover_readiness_proof_factory_invalid",)
    if any(
        getattr(readiness, name) is not False
        for name in (
            "subjective_serving",
            "ordinary_usage_event_recorded",
            "authority_state_written",
        )
    ):
        return ("cutover_readiness_proof_authority_invalid",)
    return _proof_identity_reasons(specification, readiness)


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
    stored, reasons = _store_round_trip(
        projection_root=projection_root, source=source, built=built
    )
    if stored is None:
        return None, reasons
    rebuilt, rebuild_reasons = build_subjective_mem_retrieval_projection(source)
    if rebuilt is None or rebuild_reasons or rebuilt != stored:
        return None, rebuild_reasons or ("cutover_readiness_rebuild_disagreement",)
    characterization, reasons = _characterize(
        source, request, stored, rebuilt, primary, subjective_latency_class
    )
    if characterization is None:
        return None, reasons
    readiness = _readiness(specification, rebuilt, characterization)
    reasons = validate_subjective_mem_retrieval_rehearsal_readiness(
        specification=specification, readiness=readiness
    )
    return (None, reasons) if reasons else (readiness, ())


def _input_reasons(
    specification: object, source: object, request: object, primary: object
) -> tuple[str, ...]:
    if type(specification) is not SubjectiveMemRetrievalRehearsalSpecification:
        return ("cutover_readiness_specification_invalid",)
    if _specification_reasons(specification):
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


def _specification_reasons(
    specification: SubjectiveMemRetrievalRehearsalSpecification,
) -> tuple[str, ...]:
    identity = specification.binding_identity
    if type(identity) is not tuple or not identity:
        return ("cutover_readiness_binding_identity_invalid",)
    if any(
        type(item) is not tuple
        or len(item) != 2
        or not _safe_token(item[0])
        or not _identity_value(item[1])
        for item in identity
    ):
        return ("cutover_readiness_binding_identity_invalid",)
    names = tuple(item[0] for item in identity)
    if names != tuple(sorted(names)) or len(names) != len(set(names)):
        return ("cutover_readiness_binding_identity_invalid",)
    if not _safe_token(specification.evidence_space_id):
        return ("cutover_readiness_evidence_space_invalid",)
    if not _generation(specification.projection_generation_id):
        return ("cutover_readiness_generation_invalid",)
    if not _digest(specification.projection_source_digest):
        return ("cutover_readiness_source_digest_invalid",)
    if not _prefixed_digest(specification.readiness_id, READINESS_PREFIX):
        return ("cutover_readiness_identity_invalid",)
    return ()


def _proof_identity_reasons(
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    readiness: SubjectiveMemRetrievalRehearsalReadiness,
) -> tuple[str, ...]:
    fields = (
        readiness.projection_source_digest,
        readiness.projection_manifest_digest,
        readiness.row_population_digest,
        readiness.characterization_digest,
    )
    if readiness.binding_identity != specification.binding_identity:
        return ("cutover_readiness_proof_binding_disagreement",)
    if readiness.projection_generation_id != specification.projection_generation_id:
        return ("cutover_readiness_proof_generation_disagreement",)
    if readiness.projection_source_digest != specification.projection_source_digest:
        return ("cutover_readiness_proof_source_disagreement",)
    if not _generation(readiness.projection_generation_id) or not all(
        _digest(value) for value in fields
    ):
        return ("cutover_readiness_proof_identity_invalid",)
    expected = derive_subjective_mem_retrieval_rehearsal_readiness_id(
        binding_identity=readiness.binding_identity,
        projection_generation_id=readiness.projection_generation_id,
        projection_source_digest=readiness.projection_source_digest,
        projection_manifest_digest=readiness.projection_manifest_digest,
        row_population_digest=readiness.row_population_digest,
        characterization_digest=readiness.characterization_digest,
    )
    if readiness.readiness_id != specification.readiness_id or readiness.readiness_id != expected:
        return ("cutover_readiness_proof_identity_disagreement",)
    return ()


def _store_round_trip(
    *, projection_root: object, source: object, built: SubjectiveMemRetrievalProjection
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    absent, reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if absent is not None or reasons != ("subjective_mem_retrieval_projection_absent",):
        return None, ("cutover_readiness_projection_root_not_fresh",)
    reasons = write_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source, projection=built
    )
    if reasons:
        return None, reasons
    stored, reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if stored is None or reasons or stored != built:
        return None, reasons or ("cutover_readiness_stored_projection_disagreement",)
    reasons = delete_subjective_mem_retrieval_projection(projection_root=projection_root)
    if reasons:
        return None, reasons
    remaining, reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if remaining is not None or reasons != ("subjective_mem_retrieval_projection_absent",):
        return None, ("cutover_readiness_projection_delete_unverified",)
    return stored, ()


def _projection_matches(
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    source: SubjectiveMemRetrievalProjectionSource,
    request: SubjectiveMemRetrievalRequest,
    projection: SubjectiveMemRetrievalProjection,
) -> bool:
    manifest = projection.manifest
    return (
        specification.evidence_space_id == source.evidence_space_id
        and specification.projection_generation_id
        == source.projection_generation_id
        == manifest.projection_generation_id
        == request.projection_generation_id
        and specification.projection_source_digest
        == source.source_snapshot_digest
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
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    projection: SubjectiveMemRetrievalProjection,
    characterization: SubjectiveMemRetrievalShadowCharacterization,
) -> SubjectiveMemRetrievalRehearsalReadiness:
    values = {
        "binding_identity": specification.binding_identity,
        "projection_generation_id": projection.manifest.projection_generation_id,
        "projection_source_digest": projection.manifest.source_snapshot_digest,
        "projection_manifest_digest": projection.manifest.manifest_digest,
        "row_population_digest": canonical_digest([row.row_digest for row in projection.rows]),
        "characterization_digest": canonical_digest(characterization.to_dict()),
    }
    readiness_id = derive_subjective_mem_retrieval_rehearsal_readiness_id(**values)
    value = object.__new__(SubjectiveMemRetrievalRehearsalReadiness)
    for name, item in {**values, "readiness_id": readiness_id}.items():
        object.__setattr__(value, name, item)
    for name in ("subjective_serving", "ordinary_usage_event_recorded", "authority_state_written"):
        object.__setattr__(value, name, False)
    object.__setattr__(value, "_factory_marker", _FACTORY_MARKER)
    return value


def _safe_token(value: object) -> bool:
    return type(value) is str and 1 <= len(value) <= 128 and all(
        character.isalnum() or character in "._-" for character in value
    )


def _identity_value(value: object) -> bool:
    return type(value) in (str, int, bool) and (type(value) is not str or _safe_token(value))


def _digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _prefixed_digest(value: object, prefix: str) -> bool:
    return type(value) is str and value.startswith(prefix) and _digest(value[len(prefix):])


def _generation(value: object) -> bool:
    return _prefixed_digest(value, _GENERATION_PREFIX)


__all__ = [
    "SubjectiveMemRetrievalRehearsalReadiness",
    "SubjectiveMemRetrievalRehearsalSpecification",
    "derive_subjective_mem_retrieval_rehearsal_readiness_id",
    "evaluate_subjective_mem_retrieval_rehearsal",
    "validate_subjective_mem_retrieval_rehearsal_readiness",
]
