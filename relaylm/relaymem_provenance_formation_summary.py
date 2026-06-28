"""E1-R3 speaker-provenance-safe Primary MEM formation summary helper.

The helper partitions protected finalized-turn evidence before a Primary MEM
candidate summary is formed.  Public projections are content-free; the private
formation summary may retain bounded source text with explicit speaker
provenance for worker-internal evidence review.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal

FORMATION_SUMMARY_SCHEMA = "relaymem.primary_formation_provenance_summary.v0"
FORMATION_SUMMARY_PROJECTION_SCHEMA = (
    "relaymem.primary_formation_provenance_summary_projection.v0"
)
MEMORY_CANDIDATE_PAYLOAD_SCHEMA = "relaymem.primary_memory_candidate_payload.v0"

MAX_MESSAGE_CHARS = 32_768
MAX_SUMMARY_CHARS = 2_048
MAX_TITLE_CHARS = 160
MAX_EVIDENCE_ITEMS = 32
MAX_REASONS = 32

_WHITESPACE_RE = re.compile(r"\s+")
_SPECULATION_MARKERS = (
    "maybe",
    "probably",
    "i think",
    "i guess",
    "might",
    "could be",
    "seems",
    "appears",
    "かもしれ",
    "かも",
    "おそらく",
    "たぶん",
    "推測",
    "推察",
)
_ACK_MARKERS = (
    "got it",
    "noted",
    "understood",
    "thanks",
    "thank you",
    "了解",
    "承知",
    "わかりました",
    "覚えておき",
    "記憶しました",
)
_BROWSER_TRUST_KEYS = frozenset({
    "trusted_home_scene_admission",
    "relaylm_trusted_scene_admission",
    "relaylm_trusted_home_scene_admission",
    "memory_persistence_trust",
    "x-relaylm-trusted-home-scene-admission",
    "x-relaylm-memory-persistence-trust",
})

FormationStatus = Literal[
    "disabled",
    "dry_run_ready",
    "ready",
    "formed",
    "blocked_no_user_assertion",
    "blocked_ambiguous_provenance",
    "blocked_browser_owned_trust",
    "blocked_untrusted_scene",
    "blocked_source_invalid",
    "source_role_missing",
    "source_digest_mismatch",
    "worker_input_invalid",
    "pipeline_blocked",
    "pipeline_failed",
    "content_leakage_guard_failed",
]


@dataclass(frozen=True)
class RelayMEMPrimaryFormationSummaryResult:
    """Private formation summary plus content-free public diagnostics."""

    status: FormationStatus
    enabled: bool
    dry_run_only: bool
    formation_summary: Mapping[str, object] | None = field(default=None, repr=False)
    memory_candidate_payload: Mapping[str, object] | None = field(default=None, repr=False)
    blocked_reasons: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        summary = self.formation_summary if isinstance(self.formation_summary, Mapping) else {}
        counts = summary.get("provenance_counts") if isinstance(summary, Mapping) else None
        if not isinstance(counts, Mapping):
            counts = {}
        return {
            "schema_version": FORMATION_SUMMARY_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "protected_source_body_included": False,
            "queue_payload_included": False,
            "store_root_included": False,
            "source_path_included": False,
            "claim_token_included": False,
            "lease_owner_included": False,
            "token_digest_included": False,
            "source_digest_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "formation_summary_present": self.formation_summary is not None,
            "memory_candidate_payload_present": self.memory_candidate_payload is not None,
            "user_assertion_evidence_count": int(counts.get("user_assertion_evidence", 0) or 0),
            "assistant_acknowledgement_evidence_count": int(
                counts.get("assistant_acknowledgement_evidence", 0) or 0
            ),
            "assistant_speculation_or_non_factual_evidence_count": int(
                counts.get("assistant_speculation_or_non_factual_evidence", 0) or 0
            ),
            "scene_qualification_evidence_count": int(
                counts.get("scene_qualification_evidence", 0) or 0
            ),
            "trust_admission_evidence_count": int(
                counts.get("trust_admission_evidence", 0) or 0
            ),
            "excluded_evidence_count": int(counts.get("excluded_evidence", 0) or 0),
            "user_assertion_promoted_to_candidate": self.memory_candidate_payload is not None,
            "assistant_text_promoted_to_user_fact": False,
            "scene_text_promoted_to_user_fact": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def build_relaymem_primary_formation_summary(
    *,
    character_id: object,
    namespace: object,
    source_event_kind: object,
    source_lineage_fingerprint: object | None = None,
    protected_source_identity: Mapping[str, object] | None = None,
    relayscn_scene_policy_artifact: object = None,
    trust_admission_evidence: object = None,
    governed_messages: object,
    enabled: bool = True,
    dry_run_only: bool = False,
) -> RelayMEMPrimaryFormationSummaryResult:
    """Partition finalized-turn evidence before Primary MEM summary formation.

    Only user messages can form the factual candidate payload.  Assistant text is
    retained as acknowledgement/non-factual context or excluded; scene/trust data
    remains separate qualification evidence.
    """

    if type(enabled) is not bool or type(dry_run_only) is not bool:
        return _result(
            "worker_input_invalid",
            enabled=bool(enabled),
            dry_run_only=bool(dry_run_only),
            blocked_reasons=("formation_gate_invalid",),
        )
    if not enabled:
        return _result("disabled", enabled=False, dry_run_only=dry_run_only)

    identity, identity_errors = _identity(
        character_id=character_id,
        namespace=namespace,
        source_event_kind=source_event_kind,
        source_lineage_fingerprint=source_lineage_fingerprint,
        protected_source_identity=protected_source_identity,
    )
    if identity_errors:
        return _result(
            _status_for_errors(identity_errors),
            enabled=True,
            dry_run_only=dry_run_only,
            blocked_reasons=identity_errors,
        )

    messages, message_errors = _partition_messages(governed_messages)
    if message_errors:
        return _result(
            _status_for_errors(message_errors),
            enabled=True,
            dry_run_only=dry_run_only,
            blocked_reasons=message_errors,
        )

    scene, scene_errors = _scene_evidence(relayscn_scene_policy_artifact)
    if scene_errors:
        return _result(
            _status_for_errors(scene_errors),
            enabled=True,
            dry_run_only=dry_run_only,
            blocked_reasons=scene_errors,
        )
    trust, trust_errors = _trust_evidence(trust_admission_evidence)
    if trust_errors:
        return _result(
            _status_for_errors(trust_errors),
            enabled=True,
            dry_run_only=dry_run_only,
            blocked_reasons=trust_errors,
        )

    user_assertions = messages["user_assertion_evidence"]
    if not user_assertions:
        return _result(
            "blocked_no_user_assertion",
            enabled=True,
            dry_run_only=dry_run_only,
            blocked_reasons=("user_assertion_evidence_missing",),
        )

    user_texts = [str(item["content"]) for item in user_assertions]
    candidate_summary = _normalise_summary_text("\n".join(user_texts), MAX_SUMMARY_CHARS)
    candidate_title = _normalise_summary_text(user_texts[0], MAX_TITLE_CHARS)
    memory_candidate_payload = {
        "schema_version": MEMORY_CANDIDATE_PAYLOAD_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "factual_source": "user_assertion_only",
        "assistant_text_included_as_user_fact": False,
        "scene_qualification_included_as_user_fact": False,
        "source_role": "user",
        "source_message_indexes": [item["message_index"] for item in user_assertions],
        "summary_text": candidate_summary,
        "title": candidate_title,
    }
    formation_summary = {
        "schema_version": FORMATION_SUMMARY_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "speaker_provenance_preserved": True,
        "assistant_text_promoted_to_user_fact": False,
        "scene_text_promoted_to_user_fact": False,
        "source_identity": identity,
        "user_assertion_evidence": user_assertions,
        "assistant_acknowledgement_evidence": messages[
            "assistant_acknowledgement_evidence"
        ],
        "assistant_speculation_or_non_factual_evidence": messages[
            "assistant_speculation_or_non_factual_evidence"
        ],
        "scene_qualification_evidence": scene,
        "trust_admission_evidence": trust,
        "excluded_evidence": messages["excluded_evidence"],
        "memory_candidate_payload": memory_candidate_payload,
        "provenance_counts": {
            "user_assertion_evidence": len(user_assertions),
            "assistant_acknowledgement_evidence": len(
                messages["assistant_acknowledgement_evidence"]
            ),
            "assistant_speculation_or_non_factual_evidence": len(
                messages["assistant_speculation_or_non_factual_evidence"]
            ),
            "scene_qualification_evidence": len(scene),
            "trust_admission_evidence": len(trust),
            "excluded_evidence": len(messages["excluded_evidence"]),
        },
    }
    status: FormationStatus = "dry_run_ready" if dry_run_only else "formed"
    return _result(
        status,
        enabled=True,
        dry_run_only=dry_run_only,
        formation_summary=formation_summary,
        memory_candidate_payload=memory_candidate_payload,
    )


def _partition_messages(value: object) -> tuple[dict[str, list[dict[str, object]]], tuple[str, ...]]:
    partitions = {
        "user_assertion_evidence": [],
        "assistant_acknowledgement_evidence": [],
        "assistant_speculation_or_non_factual_evidence": [],
        "excluded_evidence": [],
    }
    if type(value) not in {list, tuple}:
        return partitions, ("governed_messages_shape_invalid",)
    if len(value) < 1 or len(value) > MAX_EVIDENCE_ITEMS:
        return partitions, ("governed_messages_count_invalid",)
    for index, item in enumerate(value):
        if type(item) is not dict:
            return partitions, ("governed_message_shape_invalid",)
        if "role" not in item:
            return partitions, ("source_role_missing",)
        role = item.get("role")
        if type(role) is not str:
            return partitions, ("source_role_missing",)
        if role not in {"system", "developer", "user", "assistant"}:
            return partitions, ("ambiguous_provenance",)
        content, content_errors = _bounded_text(
            item.get("content"),
            reason="governed_message_content_invalid",
        )
        if content_errors:
            return partitions, content_errors
        evidence = {
            "message_index": index,
            "role": role,
            "content": content,
        }
        if role == "user":
            evidence["evidence_kind"] = "user_assertion"
            partitions["user_assertion_evidence"].append(evidence)
        elif role == "assistant":
            if _looks_like_acknowledgement(content):
                evidence["evidence_kind"] = "assistant_acknowledgement"
                partitions["assistant_acknowledgement_evidence"].append(evidence)
            else:
                evidence["evidence_kind"] = "assistant_non_factual_context"
                evidence["speculation_marker_present"] = _looks_like_speculation(content)
                partitions["assistant_speculation_or_non_factual_evidence"].append(evidence)
        else:
            evidence["evidence_kind"] = "excluded_non_conversation_role"
            partitions["excluded_evidence"].append(evidence)
    return partitions, ()


def _scene_evidence(value: object) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    if value is None:
        return [], ()
    if type(value) is not dict:
        return [], ("scene_qualification_invalid",)
    if _contains_browser_owned_trust(value):
        return [], ("browser_owned_trust_rejected",)
    persistence_block = value.get("persistence_block")
    if persistence_block is True:
        return [], ("scene_persistence_blocked",)
    if persistence_block is not None and type(persistence_block) is not bool:
        return [], ("scene_persistence_block_invalid",)
    if "scene_state" in value and type(value.get("scene_state")) is not dict:
        return [], ("scene_state_invalid",)
    if "scene_policy" in value and type(value.get("scene_policy")) is not dict:
        return [], ("scene_policy_invalid",)
    return [{
        "evidence_kind": "scene_qualification",
        "provenance": "route_owned_scene_policy",
        "scene_state_present": type(value.get("scene_state")) is dict,
        "scene_policy_present": type(value.get("scene_policy")) is dict,
        "persistence_block": bool(value.get("persistence_block", False)),
        "persistence_block_reason_count": _sequence_len(value.get("persistence_block_reasons")),
    }], ()


def _trust_evidence(value: object) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    if value is None:
        return [], ()
    if type(value) is not dict:
        return [], ("trust_admission_invalid",)
    if _contains_browser_owned_trust(value):
        return [], ("browser_owned_trust_rejected",)
    owner = value.get("trust_owner", "route_owned")
    if owner != "route_owned":
        return [], ("browser_owned_trust_rejected",)
    return [{
        "evidence_kind": "trust_admission",
        "provenance": "route_owned",
        "trust_owner": "route_owned",
        "admission_status": str(value.get("admission_status", "present")),
    }], ()


def _identity(
    *,
    character_id: object,
    namespace: object,
    source_event_kind: object,
    source_lineage_fingerprint: object | None,
    protected_source_identity: Mapping[str, object] | None,
) -> tuple[dict[str, object], tuple[str, ...]]:
    reasons: list[str] = []
    if not _token(character_id):
        reasons.append("character_id_invalid")
    if not _token(namespace):
        reasons.append("namespace_invalid")
    if source_event_kind not in {"turn", "session", "communication", "manual_import"}:
        reasons.append("source_event_kind_invalid")
    if source_lineage_fingerprint is not None and not _sha(source_lineage_fingerprint):
        reasons.append("source_lineage_fingerprint_invalid")
    identity: dict[str, object] = {
        "character_id": str(character_id) if _token(character_id) else "",
        "namespace": str(namespace) if _token(namespace) else "",
        "source_event_kind": str(source_event_kind) if isinstance(source_event_kind, str) else "",
        "source_lineage_fingerprint_present": source_lineage_fingerprint is not None,
    }
    if protected_source_identity is not None:
        try:
            identity["protected_source_identity"] = deepcopy(dict(protected_source_identity))
        except Exception:
            reasons.append("protected_source_identity_invalid")
    return identity, tuple(_dedupe(reasons))


def _result(
    status: FormationStatus,
    *,
    enabled: bool,
    dry_run_only: bool,
    formation_summary: Mapping[str, object] | None = None,
    memory_candidate_payload: Mapping[str, object] | None = None,
    blocked_reasons: Sequence[str] = (),
) -> RelayMEMPrimaryFormationSummaryResult:
    return RelayMEMPrimaryFormationSummaryResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        formation_summary=formation_summary,
        memory_candidate_payload=memory_candidate_payload,
        blocked_reasons=tuple(_dedupe(blocked_reasons))[:MAX_REASONS],
    )


def _status_for_errors(errors: Sequence[str]) -> FormationStatus:
    values = set(errors)
    if "source_role_missing" in values:
        return "source_role_missing"
    if "browser_owned_trust_rejected" in values:
        return "blocked_browser_owned_trust"
    if values & {"scene_persistence_blocked", "scene_qualification_invalid", "scene_state_invalid", "scene_policy_invalid", "scene_persistence_block_invalid"}:
        return "blocked_untrusted_scene"
    if values & {"ambiguous_provenance", "governed_message_shape_invalid"}:
        return "blocked_ambiguous_provenance"
    if "source_lineage_fingerprint_invalid" in values:
        return "source_digest_mismatch"
    if values & {"character_id_invalid", "namespace_invalid", "source_event_kind_invalid"}:
        return "blocked_source_invalid"
    return "worker_input_invalid"


def _bounded_text(value: object, *, reason: str) -> tuple[str, tuple[str, ...]]:
    if type(value) is not str or not value or len(value) > MAX_MESSAGE_CHARS:
        return "", (reason,)
    if any((ord(char) < 32 and char not in "\n\t") or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        return "", (reason,)
    return value, ()


def _normalise_summary_text(value: str, max_chars: int) -> str:
    normalised = _WHITESPACE_RE.sub(" ", value).strip()
    if len(normalised) <= max_chars:
        return normalised
    return normalised[: max(1, max_chars - 1)].rstrip() + "…"


def _looks_like_speculation(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SPECULATION_MARKERS)


def _looks_like_acknowledgement(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _ACK_MARKERS)


def _contains_browser_owned_trust(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower().replace("_", "-")
            if str(key).lower() in _BROWSER_TRUST_KEYS or key_text in _BROWSER_TRUST_KEYS:
                return True
            if key in {"trust_owner", "provenance"} and item in {"browser", "browser_owned", "frontend", "client"}:
                return True
            if _contains_browser_owned_trust(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_browser_owned_trust(item) for item in value)
    return False


def _sequence_len(value: object) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value)
    return 0


def _token(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value.strip()) <= 128
        and not any(char in value for char in "\n\r\t")
    )


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = [
    "FORMATION_SUMMARY_PROJECTION_SCHEMA",
    "FORMATION_SUMMARY_SCHEMA",
    "MEMORY_CANDIDATE_PAYLOAD_SCHEMA",
    "RelayMEMPrimaryFormationSummaryResult",
    "build_relaymem_primary_formation_summary",
]
