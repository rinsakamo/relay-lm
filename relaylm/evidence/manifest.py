"""CanonicalSourceManifest v1 and its supporting value objects (Contract 1A).

Builds the canonical, content-addressed manifest for one governed source
occurrence. EV-1 only ever builds single-part ``text`` manifests for
``message``/``assistant_response`` occurrence kinds -- the full part-kind and
occurrence-kind vocabularies below are the real closed enums, but EV-1 only
exercises the subset needed for managed text conversation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence.common import PrincipalRef, canonical_digest, dedupe, utf8_text_digest

SCHEMA = "relaylm.canonical_source_manifest.v1"

OCCURRENCE_KINDS = frozenset(
    {
        "message",
        "assistant_response",
        "action",
        "tool_result",
        "sensor_result",
        "setting_change",
        "lifecycle_request",
        "import_record",
        "system_event",
    }
)
PART_KINDS = frozenset({"text", "audio", "image", "video", "structured", "binary", "reference"})
INITIAL_DISPOSITIONS = frozenset(
    {
        "protected",
        "quarantine_only",
        "reference_only",
        "omitted_secret",
        "omitted_security",
        "omitted_policy",
    }
)
PART_ORIGINS = frozenset(
    {
        "participant_authored",
        "assistant_authored",
        "tool_produced",
        "sensor_produced",
        "system_produced",
        "quoted_external",
        "forwarded_external",
        "imported_external",
        "unknown_external",
    }
)
PART_DERIVATION_CLASSES = frozenset(
    {
        "direct_occurrence",
        "model_generated",
        "product_knowledge_derived",
        "tool_derived",
        "transformed_external",
        "unknown",
    }
)


@dataclass(frozen=True)
class SourceOccurrenceTime:
    raw_value_or_null: str | None
    parsed_instant_or_null: str | None
    timezone_or_offset_or_null: str | None
    trust: str

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_value_or_null": self.raw_value_or_null,
            "parsed_instant_or_null": self.parsed_instant_or_null,
            "timezone_or_offset_or_null": self.timezone_or_offset_or_null,
            "trust": self.trust,
        }


_OCCURRENCE_TIME_TRUSTS = frozenset(
    {"trusted_source", "trusted_transport", "asserted", "inferred", "unknown"}
)


def build_source_occurrence_time(
    *, parsed_instant: str, trust: str = "trusted_transport"
) -> tuple[SourceOccurrenceTime | None, tuple[str, ...]]:
    if trust not in _OCCURRENCE_TIME_TRUSTS:
        return None, ("source_occurrence_time_trust_invalid",)
    if type(parsed_instant) is not str or not parsed_instant:
        return None, ("source_occurrence_time_instant_invalid",)
    return (
        SourceOccurrenceTime(
            raw_value_or_null=None,
            parsed_instant_or_null=parsed_instant,
            timezone_or_offset_or_null="UTC",
            trust=trust,
        ),
        (),
    )


_AUDIENCE_CLASSES = frozenset(
    {"private_direct", "private_group", "shared_scene", "public", "system_internal", "unknown"}
)
_AUDIENCE_TRUSTS = frozenset({"trusted_transport", "trusted_route", "asserted", "unresolved"})


@dataclass(frozen=True)
class OccurrenceAudienceSnapshot:
    audience_class: str
    participant_refs: tuple[PrincipalRef, ...]
    room_ref_or_null: str | None
    shared_scene_ref_or_null: str | None
    trust: str

    def to_dict(self) -> dict[str, object]:
        return {
            "audience_class": self.audience_class,
            "participant_refs": [ref.to_dict() for ref in self.participant_refs],
            "room_ref_or_null": self.room_ref_or_null,
            "shared_scene_ref_or_null": self.shared_scene_ref_or_null,
            "trust": self.trust,
        }


def build_private_direct_audience(
    *, participant_refs: tuple[PrincipalRef, ...], trust: str = "trusted_route"
) -> tuple[OccurrenceAudienceSnapshot | None, tuple[str, ...]]:
    if trust not in _AUDIENCE_TRUSTS:
        return None, ("occurrence_audience_trust_invalid",)
    if not participant_refs:
        return None, ("occurrence_audience_participant_refs_required",)
    deduped = tuple(sorted(set(participant_refs), key=lambda ref: ref.principal_id))
    return (
        OccurrenceAudienceSnapshot(
            audience_class="private_direct",
            participant_refs=deduped,
            room_ref_or_null=None,
            shared_scene_ref_or_null=None,
            trust=trust,
        ),
        (),
    )


_PROVENANCE_CAPTURE_METHODS = frozenset(
    {
        "trusted_connector",
        "managed_runtime",
        "verified_import",
        "trusted_tool",
        "trusted_sensor",
        "governed_system",
        "untrusted_external",
    }
)
_PROVENANCE_ASSURANCE = frozenset({"verified", "asserted", "unresolved", "conflicting"})
_INDEPENDENCE_STATUS = frozenset({"independent", "same_origin_group", "unknown"})
_SOURCE_MATERIAL_CLASSES = frozenset(
    {
        "personal_source",
        "assistant_generation",
        "product_knowledge_derived",
        "tool_derived",
        "external_reference",
        "system_policy",
        "unknown",
    }
)


@dataclass(frozen=True)
class ProvenanceSnapshot:
    capture_method: str
    provenance_assurance: str
    independence_status: str
    independence_group_id_or_null: str | None
    independence_basis_or_null: str | None
    source_material_classes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "capture_method": self.capture_method,
            "provenance_assurance": self.provenance_assurance,
            "independence_status": self.independence_status,
            "independence_group_id_or_null": self.independence_group_id_or_null,
            "independence_basis_or_null": self.independence_basis_or_null,
            "source_material_classes": list(self.source_material_classes),
        }


def build_managed_runtime_provenance(
    *, source_material_class: str
) -> tuple[ProvenanceSnapshot | None, tuple[str, ...]]:
    if source_material_class not in _SOURCE_MATERIAL_CLASSES:
        return None, ("provenance_source_material_class_invalid",)
    return (
        ProvenanceSnapshot(
            capture_method="managed_runtime",
            provenance_assurance="verified",
            independence_status="unknown",
            independence_group_id_or_null=None,
            independence_basis_or_null=None,
            source_material_classes=(source_material_class,),
        ),
        (),
    )


@dataclass(frozen=True)
class SourcePartManifest:
    part_id: str
    part_kind: str
    media_type: str
    byte_length_or_null: int | None
    content_digest_or_null: str | None
    initial_disposition: str
    part_origin: str
    part_derivation_class: str
    represented_source_ref_or_null: None = None
    reference_basis_or_null: None = None
    omission_reason_code_or_null: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "part_kind": self.part_kind,
            "media_type": self.media_type,
            "byte_length_or_null": self.byte_length_or_null,
            "content_digest_or_null": self.content_digest_or_null,
            "initial_disposition": self.initial_disposition,
            "part_origin": self.part_origin,
            "part_derivation_class": self.part_derivation_class,
            "represented_source_ref_or_null": self.represented_source_ref_or_null,
            "reference_basis_or_null": self.reference_basis_or_null,
            "omission_reason_code_or_null": self.omission_reason_code_or_null,
        }


def build_protected_text_part(
    text: str,
    *,
    part_origin: str,
    part_derivation_class: str,
    part_id: str = "part-0",
) -> tuple[SourcePartManifest | None, tuple[str, ...]]:
    reasons: list[str] = []
    if part_origin not in PART_ORIGINS:
        reasons.append("source_part_origin_invalid")
    if part_derivation_class not in PART_DERIVATION_CLASSES:
        reasons.append("source_part_derivation_class_invalid")
    if part_origin == "participant_authored" and part_derivation_class != "direct_occurrence":
        reasons.append("source_part_origin_derivation_mismatch")
    if part_origin == "assistant_authored" and part_derivation_class not in {
        "model_generated",
        "product_knowledge_derived",
        "tool_derived",
        "transformed_external",
    }:
        reasons.append("source_part_origin_derivation_mismatch")
    if type(text) is not str or not text:
        reasons.append("source_part_text_invalid")
    if reasons:
        return None, dedupe(reasons)
    encoded = text.encode("utf-8", errors="strict")
    return (
        SourcePartManifest(
            part_id=part_id,
            part_kind="text",
            media_type="text/plain",
            byte_length_or_null=len(encoded),
            content_digest_or_null=utf8_text_digest(text),
            initial_disposition="protected",
            part_origin=part_origin,
            part_derivation_class=part_derivation_class,
        ),
        (),
    )


@dataclass(frozen=True)
class CanonicalSourceManifest:
    schema: str
    occurrence_kind: str
    parts: tuple[SourcePartManifest, ...]
    manifest_extensions: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "occurrence_kind": self.occurrence_kind,
            "parts": [part.to_dict() for part in self.parts],
            "manifest_extensions": {},
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def build_canonical_source_manifest(
    *, occurrence_kind: str, parts: tuple[SourcePartManifest, ...]
) -> tuple[CanonicalSourceManifest | None, tuple[str, ...]]:
    reasons: list[str] = []
    if occurrence_kind not in OCCURRENCE_KINDS:
        reasons.append("occurrence_kind_invalid")
    if not parts:
        reasons.append("manifest_parts_required")
    part_ids = [part.part_id for part in parts]
    if len(part_ids) != len(set(part_ids)):
        reasons.append("manifest_part_ids_not_unique")
    if reasons:
        return None, dedupe(reasons)
    return CanonicalSourceManifest(schema=SCHEMA, occurrence_kind=occurrence_kind, parts=parts), ()


__all__ = [
    "SCHEMA",
    "OCCURRENCE_KINDS",
    "PART_KINDS",
    "INITIAL_DISPOSITIONS",
    "PART_ORIGINS",
    "PART_DERIVATION_CLASSES",
    "CanonicalSourceManifest",
    "OccurrenceAudienceSnapshot",
    "ProvenanceSnapshot",
    "SourceOccurrenceTime",
    "SourcePartManifest",
    "build_canonical_source_manifest",
    "build_managed_runtime_provenance",
    "build_private_direct_audience",
    "build_protected_text_part",
    "build_source_occurrence_time",
]
