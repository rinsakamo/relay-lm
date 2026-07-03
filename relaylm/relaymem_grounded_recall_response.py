"""E1-R4 evidence-grounded recall response helper.

Builds a private backend-bound grounding context from already retrieved Primary
MEM projections. Public diagnostics remain content-free.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from relaylm.query_detail_analyzer import (
    QueryDetailAnalysis,
    analyze_query_detail_candidate,
)

GROUNDED_RECALL_CONTEXT_SCHEMA = "relaymem.grounded_recall_context.v0"
GROUNDED_RECALL_PROJECTION_SCHEMA = "relaymem.grounded_recall_projection.v0"
MAX_EVIDENCE_ITEMS = 32
MAX_FACT_TEXT_CHARS = 2048

GroundingStatus = Literal[
    "disabled", "ready", "grounding_applied", "no_retrieved_evidence",
    "unsupported_detail_suppressed", "ambiguous_evidence", "provenance_missing",
    "retrieval_excluded", "context_build_failed", "backend_request_unchanged",
    "content_leakage_guard_failed",
]
SupportStatus = Literal[
    "directly_supported", "inferred_from_supported", "unsupported",
    "no_retrieved_evidence", "ambiguous_evidence", "excluded_by_lifecycle",
    "excluded_by_scope", "provenance_missing", "content_leakage_guard_failed",
]

_EXCLUDED_STATES = {"hidden", "prior", "prepared", "recovery_required", "corrupt", "deleted", "tombstoned", "held"}
_ELIGIBLE_STATES = {"active", "current", "eligible", "pinned"}
_DIRECT = {"user_assertion", "user_assertion_only", "primary_recall_selected_memory"}
_INFERRED = {"scene_qualification", "other_allowed_source"}
_UNSUPPORTED = {"assistant_acknowledgement", "assistant_speculation", "assistant_non_factual_context", "assistant_decoration", "unknown"}
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
_LONG_HEX_RE = re.compile(r"^[0-9a-f]{32,}$")
_SPACE_RE = re.compile(r"\s+")
_DATE_LIKE_RE = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{4}\b|令和|平成|昭和|\d{1,2}月\d{1,2}日", re.I)
_QUANTITY_LIKE_RE = re.compile(r"\b\d+(?:\.\d+)?\b|一つ|二つ|三つ|[0-9]+個|[0-9]+回")
_NAME_LIKE_RE = re.compile(r"\b(name is|called|named)\b|名前は", re.I)
_REL_LIKE_RE = re.compile(r"\b(friend|family|parent|child|coworker|relationship)\b|友人|家族|同僚|関係", re.I)
_CAUSE_LIKE_RE = re.compile(r"\b(because|reason|cause|due to)\b|理由|原因|なぜなら", re.I)
_PREFERENCE_LIKE_RE = re.compile(r"\b(favorite|favourite|prefer|preference|like|love|dislike|hobby|taste)\b|好き|好み|お気に入り|嫌い", re.I)
_LOCATION_LIKE_RE = re.compile(r"\b(?:location|place|address|city|country|venue|station|room|building|site)\s*(?:is|:|=)|場所[は:：]|住所[は:：]|会場[は:：]|駅[は:：]|部屋[は:：]|市[は:：]|国[は:：]|県[は:：]", re.I)
_IDENTITY_LIKE_RE = re.compile(r"\b(identity|profile|name is|called|named)\b|身元|名前は|プロフィール", re.I)
_FAVORITE_DETAIL_RE = re.compile(r"\bfavo[u]?rite\s+([A-Za-z][A-Za-z0-9_-]{0,32})", re.I)


@dataclass(frozen=True)
class RelayMEMGroundedRecallResult:
    status: GroundingStatus
    enabled: bool
    backend_request_changed: bool
    grounded_recall_context: Mapping[str, object] | None = field(default=None, repr=False)
    blocked_reasons: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        ctx = self.grounded_recall_context if isinstance(self.grounded_recall_context, Mapping) else {}
        evidence = ctx.get("evidence_items") if isinstance(ctx, Mapping) else []
        excluded = ctx.get("excluded_evidence") if isinstance(ctx, Mapping) else []
        query_detail = ctx.get("query_detail_analysis") if isinstance(ctx, Mapping) else {}
        query_detail_map = query_detail if isinstance(query_detail, Mapping) else {}
        query_detail_types = ctx.get("query_detail_types") if isinstance(ctx, Mapping) else []
        return {
            "schema_version": GROUNDED_RECALL_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "grounding_enabled": self.enabled,
            "status": self.status,
            "backend_request_changed": self.backend_request_changed,
            "grounded_item_count": len(evidence) if isinstance(evidence, Sequence) else 0,
            "excluded_evidence_count": len(excluded) if isinstance(excluded, Sequence) else 0,
            "unsupported_detail_policy": str(ctx.get("unsupported_detail_policy", "suppress")) if isinstance(ctx, Mapping) else "suppress",
            "unsupported_detail_count": int(ctx.get("unsupported_detail_count", 0) or 0) if isinstance(ctx, Mapping) else 0,
            "ambiguous_evidence_count": int(ctx.get("ambiguous_evidence_count", 0) or 0) if isinstance(ctx, Mapping) else 0,
            "query_detail_type_count": len(query_detail_types) if isinstance(query_detail_types, Sequence) else 0,
            "query_detail_unsupported_detail_risk": bool(ctx.get("unsupported_detail_risk", False)) if isinstance(ctx, Mapping) else False,
            "query_detail_source_class": str(query_detail_map.get("source_class", "unknown")),
            "query_detail_restrictive_only": bool(query_detail_map.get("restrictive_only", True)),
            "query_detail_content_free": bool(query_detail_map.get("content_free", True)),
            "evidence_content_included": False,
            "runtime_private_evidence_omitted": True,
            "raw_memory_text_included": False,
            "raw_user_text_included": False,
            "raw_assistant_text_included": False,
            "protected_source_body_included": False,
            "queue_payload_included": False,
            "store_root_included": False,
            "source_path_included": False,
            "claim_token_included": False,
            "lease_owner_included": False,
            "token_digest_included": False,
            "source_digest_included": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def build_grounded_recall_context(
    *,
    retrieved_memories: object,
    query_text: object = "",
    character_id: object | None = None,
    namespace: object | None = None,
    enabled: bool = True,
    unsupported_detail_policy: object = "suppress",
    query_detail_candidate: object | None = None,
) -> RelayMEMGroundedRecallResult:
    if type(enabled) is not bool:
        return _result("context_build_failed", bool(enabled), False, None, ("grounding_enabled_invalid",))
    if not enabled:
        return _result("disabled", False, False, None, ())
    if unsupported_detail_policy not in {"suppress", "qualify_uncertain", "omit"}:
        return _result("context_build_failed", True, False, None, ("unsupported_detail_policy_invalid",))
    if type(query_text) is not str or type(retrieved_memories) not in {list, tuple} or len(retrieved_memories) > MAX_EVIDENCE_ITEMS:
        return _result("context_build_failed", True, False, None, ("request_shape_invalid",))

    query_detail_analysis = analyze_query_detail_candidate(
        query_text=query_text,
        candidate=query_detail_candidate,
    )
    if not retrieved_memories:
        ctx = _context([], [], query_detail_analysis, str(unsupported_detail_policy), 0, 0, no_evidence=True)
        return _result("no_retrieved_evidence", True, True, ctx, ("no_retrieved_evidence",))

    items: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    ambiguous = 0
    missing = 0
    for index, raw in enumerate(retrieved_memories):
        if type(raw) is not dict:
            excluded.append(_excluded(index, "ambiguous_evidence", "retrieved_memory_shape_invalid")); ambiguous += 1; continue
        scope = _scope_status(raw, character_id, namespace)
        if scope != "ok":
            excluded.append(_excluded(index, "excluded_by_scope", scope)); continue
        lifecycle = _lifecycle_status(raw)
        if lifecycle != "ok":
            excluded.append(_excluded(index, "excluded_by_lifecycle", lifecycle)); continue
        support = classify_grounded_recall_support(raw)
        if support == "provenance_missing":
            excluded.append(_excluded(index, "provenance_missing", "provenance_missing")); missing += 1; continue
        if support == "ambiguous_evidence":
            excluded.append(_excluded(index, "ambiguous_evidence", "ambiguous_evidence")); ambiguous += 1; continue
        if support == "unsupported":
            excluded.append(_excluded(index, "unsupported", "unsupported_provenance")); continue
        fact = _fact_text(raw)
        if not fact:
            excluded.append(_excluded(index, "ambiguous_evidence", "fact_text_missing")); ambiguous += 1; continue
        items.append({
            "memory_ref": _safe_ref(raw.get("memory_id") or raw.get("id") or raw.get("idempotency_key") or raw.get("evidence_id"), index),
            "revision_ref": _safe_revision(raw.get("revision") or raw.get("rev")),
            "lifecycle_current_eligible": True,
            "pinned": bool(raw.get("pinned") is True or raw.get("pin_state") == "pinned"),
            "provenance_source": _provenance(raw),
            "fact_text": fact,
            "support_level": "directly_supported" if support == "directly_supported" else "inferred_from_supported",
            "unsupported_detail_policy": str(unsupported_detail_policy),
        })

    items.sort(key=lambda item: (not bool(item.get("pinned")), str(item.get("memory_ref", ""))))
    unsupported = _unsupported_detail_count(query_text, items, query_detail_analysis)
    ctx = _context(items, excluded, query_detail_analysis, str(unsupported_detail_policy), unsupported, ambiguous, no_evidence=False)
    if items and unsupported:
        return _result("unsupported_detail_suppressed", True, True, ctx, ("requested_detail_not_supported_by_retrieved_memory",))
    if items:
        return _result("grounding_applied", True, True, ctx, ())
    status: GroundingStatus = "provenance_missing" if missing else "ambiguous_evidence" if ambiguous else "retrieval_excluded"
    return _result(status, True, True, ctx, tuple(str(x["reason"]) for x in excluded))


def classify_grounded_recall_support(memory: Mapping[str, object]) -> SupportStatus:
    if _scope_status(memory, None, None) != "ok":
        return "excluded_by_scope"
    if _lifecycle_status(memory) != "ok":
        return "excluded_by_lifecycle"
    provenance = _provenance(memory)
    if not provenance:
        return "provenance_missing"
    if provenance in _DIRECT:
        return "directly_supported"
    if provenance in _INFERRED:
        return "inferred_from_supported"
    if provenance in _UNSUPPORTED:
        return "unsupported"
    return "ambiguous_evidence"


def _context(
    items: list[dict[str, object]],
    excluded: list[dict[str, object]],
    query_detail_analysis: QueryDetailAnalysis,
    policy: str,
    unsupported: int,
    ambiguous: int,
    *,
    no_evidence: bool,
) -> dict[str, object]:
    instruction = _instruction(no_evidence=no_evidence, unsupported=unsupported, policy=policy)
    content = _backend_message_content(instruction, items, unsupported)
    public_query_detail = query_detail_analysis.to_public_dict()
    return {
        "schema_version": GROUNDED_RECALL_CONTEXT_SCHEMA,
        "runtime_private": True,
        "enabled": True,
        "evidence_items": items,
        "excluded_evidence": excluded,
        "unsupported_detail_policy": policy,
        "unsupported_detail_count": unsupported,
        "ambiguous_evidence_count": ambiguous,
        "query_detail_types": list(query_detail_analysis.requested_detail_types),
        "unsupported_detail_risk": query_detail_analysis.unsupported_detail_risk,
        "query_detail_analysis": public_query_detail,
        "instruction": instruction,
        "backend_messages": [{"role": "system", "content": content}],
    }


def _backend_message_content(instruction: str, items: Sequence[Mapping[str, object]], unsupported: int) -> str:
    lines = [
        "[RelayMEM Grounded Recall Context]",
        instruction,
        "",
        "Evidence items:",
    ]
    if not items:
        lines.append("- none")
    for index, item in enumerate(items, start=1):
        lines.append(
            f"- {index}. support={item.get('support_level')}; ref={item.get('memory_ref')}; text={item.get('fact_text')}"
        )
    lines.extend([
        "",
        f"unsupported_detail_count={unsupported}",
        "Do not mention this block unless asked about context handling.",
    ])
    return "\n".join(lines)


def _instruction(*, no_evidence: bool, unsupported: int, policy: str) -> str:
    base = "Use only the grounded_recall_context evidence_items for remembered facts. Treat directly_supported evidence as remembered fact. Mark inferred_from_supported statements explicitly as inference. Do not invent dates, names, preferences, quantities, relationships, locations, identities, or causes. Assistant acknowledgements, assistant speculation, hidden/prior/prepared/recovery/corrupt/cross-scope memories, and Held Governance evidence do not create recalled facts. Pin ordering may rank eligible evidence earlier but never creates factual support."
    if no_evidence:
        return base + " No retrieved evidence is present; do not claim to remember the requested detail. Say the memory does not support that detail."
    if unsupported:
        if policy == "qualify_uncertain":
            return base + " The retrieved memory does not directly support at least one requested detail; qualify it as uncertain rather than presenting it as memory."
        return base + " The retrieved memory does not support at least one requested detail; suppress or omit that detail and say the memory does not support it."
    return base + " Answer only from directly supported evidence for remembered facts."


def _scope_status(memory: Mapping[str, object], character_id: object | None, namespace: object | None) -> str:
    if character_id is not None and memory.get("character_id") not in {None, character_id}:
        return "character_scope_mismatch"
    if namespace is not None and memory.get("namespace") not in {None, namespace}:
        return "namespace_scope_mismatch"
    if memory.get("scope_status") in {"cross_scope", "scope_mismatch", "excluded_by_scope"}:
        return str(memory.get("scope_status"))
    return "ok"


def _lifecycle_status(memory: Mapping[str, object]) -> str:
    state = str(memory.get("lifecycle_state") or memory.get("state") or memory.get("status") or "active")
    if state in _EXCLUDED_STATES:
        return state
    for key, reason in (("hidden", "hidden"), ("prepared", "prepared"), ("recovery_required", "recovery_required"), ("corrupt", "corrupt")):
        if memory.get(key) is True:
            return reason
    if memory.get("current") is False:
        return "prior"
    return "ok" if state in _ELIGIBLE_STATES else "ambiguous_lifecycle"


def _provenance(memory: Mapping[str, object]) -> str:
    for key in ("provenance_source", "provenance", "factual_source", "source_kind"):
        value = memory.get(key)
        if type(value) is str and value.strip():
            return "user_assertion" if value.strip() == "user_assertion_only" else value.strip()
    summary = memory.get("formation_summary")
    counts = summary.get("provenance_counts") if isinstance(summary, Mapping) else None
    if isinstance(counts, Mapping) and int(counts.get("user_assertion_evidence", 0) or 0) > 0:
        return "user_assertion"
    if _looks_like_current_primary_recall_evidence(memory):
        return "primary_recall_selected_memory"
    return ""


def _fact_text(memory: Mapping[str, object]) -> str:
    for key in ("fact_text", "summary_text", "summary", "snippet_text", "allowed_memory_snippet", "memory_snippet", "text"):
        value = memory.get(key)
        if type(value) is str and value.strip():
            text = _SPACE_RE.sub(" ", value).strip()
            return text if len(text) <= MAX_FACT_TEXT_CHARS else text[:MAX_FACT_TEXT_CHARS - 1].rstrip() + "…"
    payload = memory.get("memory_candidate_payload")
    return _fact_text(payload) if isinstance(payload, Mapping) else ""


def _looks_like_current_primary_recall_evidence(memory: Mapping[str, object]) -> bool:
    if memory.get("memory_layer") not in {None, "primary"}:
        return False
    if not _fact_text_without_payload(memory):
        return False
    if not any(key in memory for key in ("snippet_text", "summary")):
        return False
    return any(key in memory for key in ("evidence_id", "idempotency_key", "physical_idempotency_key", "revision"))


def _fact_text_without_payload(memory: Mapping[str, object]) -> str:
    for key in ("fact_text", "summary_text", "summary", "snippet_text", "allowed_memory_snippet", "memory_snippet", "text"):
        value = memory.get(key)
        if type(value) is str and value.strip():
            return value.strip()
    return ""


def _safe_ref(value: object, index: int) -> str:
    if type(value) is str:
        text = value.strip()
        if _SAFE_REF_RE.match(text) and "/" not in text and "\\" not in text and not _LONG_HEX_RE.match(text):
            return text
    return f"memory_ref_{index + 1}"


def _safe_revision(value: object) -> str:
    if type(value) is int and value >= 0:
        return f"rev:{value}"
    if type(value) is str and value.strip() and len(value.strip()) <= 32 and not _LONG_HEX_RE.match(value.strip()):
        return value.strip()
    return "revision_present" if value not in {None, ""} else "revision_unknown"


def _unsupported_detail_count(query: str, items: Sequence[Mapping[str, object]], analysis: QueryDetailAnalysis) -> int:
    facts = "\n".join(str(item.get("fact_text", "")) for item in items)
    requested = set(analysis.requested_detail_types)
    return sum((
        bool("date_or_time" in requested and not _DATE_LIKE_RE.search(facts)),
        bool("quantity" in requested and not _QUANTITY_LIKE_RE.search(facts)),
        bool("person_or_name" in requested and not _NAME_LIKE_RE.search(facts)),
        bool("relationship" in requested and not _REL_LIKE_RE.search(facts)),
        bool("cause_or_reason" in requested and not _CAUSE_LIKE_RE.search(facts)),
        _preference_detail_missing(query, facts, requested),
        bool("location" in requested and not _LOCATION_LIKE_RE.search(facts)),
        bool("identity" in requested and not _IDENTITY_LIKE_RE.search(facts)),
        bool("unknown" in requested),
    ))


def _preference_detail_missing(query: str, facts: str, requested: set[str]) -> bool:
    if "preference" not in requested:
        return False
    query_lower = query.lower()
    facts_lower = facts.lower()
    requested_details = [match.group(1).lower() for match in _FAVORITE_DETAIL_RE.finditer(query_lower)]
    if requested_details:
        return not any(
            f"favorite {detail}" in facts_lower or f"favourite {detail}" in facts_lower
            for detail in requested_details
        )
    return not _PREFERENCE_LIKE_RE.search(facts)


def _excluded(index: int, status: str, reason: str) -> dict[str, object]:
    return {"memory_ref": f"memory_ref_{index + 1}", "support_status": status, "reason": reason, "content_included": False}


def _result(status: GroundingStatus, enabled: bool, changed: bool, ctx: Mapping[str, object] | None, reasons: Sequence[str]) -> RelayMEMGroundedRecallResult:
    return RelayMEMGroundedRecallResult(status=status, enabled=enabled, backend_request_changed=changed, grounded_recall_context=ctx, blocked_reasons=tuple(dict.fromkeys(str(r) for r in reasons if r))[:32])


__all__ = [
    "GROUNDED_RECALL_CONTEXT_SCHEMA",
    "GROUNDED_RECALL_PROJECTION_SCHEMA",
    "RelayMEMGroundedRecallResult",
    "build_grounded_recall_context",
    "classify_grounded_recall_support",
]
