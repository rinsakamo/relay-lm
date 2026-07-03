"""RelaySCN scene-wiki matching boundary helpers.

The matcher accepts already-structured scene definitions and returns a
content-free candidate match. It never parses or exposes scene body text and it
never mutates the provided definitions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "relaylm.scene_wiki_match.v0"

SCENE_WIKI_SCENE_TYPES = frozenset({
    "unknown",
    "casual_chat",
    "implementation_work",
    "review_work",
    "design_talk",
    "formal_document",
    "medical_or_safety",
    "system_ops",
    "recovery",
    "vtuber_roleplay",
    "memory_management",
    "character_workspace",
})

MATCH_STRENGTHS = frozenset({"none", "weak", "medium", "strong"})
SCENE_WIKI_AUTHORITIES = frozenset({
    "explicit_scene_definition",
    "trusted_explicit",
    "trusted_route",
    "confirmed_user_action",
})

_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def match_scene_wiki_definition(
    *,
    candidate_scene_type: Any = None,
    candidate_scene_id: Any = None,
    candidate_scene_family: Any = None,
    scene_definitions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the best safe scene-wiki match for a structured candidate.

    The result is diagnostic/candidate evidence only. Matching a scene-wiki
    definition does not make the classifier authoritative and does not grant
    broad retrieval or update authority.
    """

    definitions = scene_definitions if isinstance(scene_definitions, Sequence) else []
    safe_candidate_type = _safe_scene_type(candidate_scene_type)
    safe_candidate_id = _safe_token(candidate_scene_id)
    safe_candidate_family = _safe_token(candidate_scene_family)

    best: dict[str, Any] | None = None
    best_rank = 0
    safe_definition_count = 0
    enabled_definition_count = 0

    for raw_definition in definitions:
        if not isinstance(raw_definition, Mapping):
            continue
        safe_definition_count += 1
        if raw_definition.get("enabled") is False:
            continue

        scene_id = _safe_token(raw_definition.get("scene_id"))
        scene_type = _safe_scene_type(raw_definition.get("scene_type"))
        scene_family = _safe_token(raw_definition.get("scene_family"))
        aliases = _safe_aliases(raw_definition.get("aliases"))
        authority = _safe_authority(raw_definition.get("authority"))
        if scene_id == "unknown" or scene_type == "unknown":
            continue
        enabled_definition_count += 1

        strength = "none"
        rank = 0
        if safe_candidate_id != "unknown" and safe_candidate_id in {scene_id, *aliases}:
            strength = "strong" if safe_candidate_type in {"unknown", scene_type} else "medium"
            rank = 3 if strength == "strong" else 2
        elif safe_candidate_type == scene_type and safe_candidate_family != "unknown" and safe_candidate_family == scene_family:
            strength = "medium"
            rank = 2
        elif safe_candidate_type == scene_type:
            strength = "weak"
            rank = 1

        if rank > best_rank:
            best_rank = rank
            best = {
                "matched_scene_wiki_id": scene_id,
                "matched_scene_type": scene_type,
                "matched_scene_family": scene_family,
                "match_strength": strength,
                "scene_wiki_authority": authority,
            }

    if best is None:
        best = {
            "matched_scene_wiki_id": None,
            "matched_scene_type": "unknown",
            "matched_scene_family": "unknown",
            "match_strength": "none",
            "scene_wiki_authority": "unknown",
        }

    reason_ids: list[str] = []
    if best["match_strength"] != "none":
        reason_ids.append("scene_wiki_candidate_match")
    if safe_candidate_type == "unknown":
        reason_ids.append("unknown_candidate_scene_type")

    return {
        "schema_version": SCHEMA_VERSION,
        "content_free": True,
        "candidate_scene_type": safe_candidate_type,
        "candidate_scene_family": safe_candidate_family,
        "matched_scene_wiki_id": best["matched_scene_wiki_id"],
        "matched_scene_type": best["matched_scene_type"],
        "matched_scene_family": best["matched_scene_family"],
        "match_strength": best["match_strength"],
        "scene_wiki_authority": best["scene_wiki_authority"],
        "safe_definition_count": safe_definition_count,
        "enabled_definition_count": enabled_definition_count,
        "reason_ids": tuple(reason_ids),
    }


def scene_wiki_match_public_projection(match: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a fixed content-free public projection for a matcher result."""

    raw = match if isinstance(match, Mapping) else {}
    match_strength = str(raw.get("match_strength") or "none")
    if match_strength not in MATCH_STRENGTHS:
        match_strength = "none"
    matched_id = _safe_token(raw.get("matched_scene_wiki_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "content_free": True,
        "candidate_scene_type": _safe_scene_type(raw.get("candidate_scene_type")),
        "candidate_scene_family": _safe_token(raw.get("candidate_scene_family")),
        "matched_scene_wiki_id": None if matched_id == "unknown" else matched_id,
        "match_strength": match_strength,
        "safe_definition_count": _safe_nonnegative_int(raw.get("safe_definition_count")),
        "enabled_definition_count": _safe_nonnegative_int(raw.get("enabled_definition_count")),
        "reason_ids": tuple(_safe_reason_ids(raw.get("reason_ids"))),
    }


def _safe_scene_type(value: Any) -> str:
    token = _safe_token(value)
    if token in SCENE_WIKI_SCENE_TYPES:
        return token
    return "unknown"


def _safe_token(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    token = value.strip().lower()
    if not _TOKEN_RE.fullmatch(token):
        return "unknown"
    return token


def _safe_aliases(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, Sequence):
        raw_values = value
    else:
        raw_values = ()
    return frozenset(token for token in (_safe_token(item) for item in raw_values) if token != "unknown")


def _safe_authority(value: Any) -> str:
    token = _safe_token(value)
    if token in SCENE_WIKI_AUTHORITIES:
        return token
    return "unknown"


def _safe_reason_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, Sequence):
        raw_values = value
    else:
        raw_values = ()
    allowed = {"scene_wiki_candidate_match", "unknown_candidate_scene_type"}
    result: list[str] = []
    for raw in raw_values:
        token = _safe_token(raw)
        if token in allowed and token not in result:
            result.append(token)
    return result


def _safe_nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0
