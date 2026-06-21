"""Shared bounded validators for RelayMEM M3e."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

PAGE_SCHEMA = "relaymem.primary_page.v0"
EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
KIND_TARGET = {
    "recent_project_event": "primary_projects",
    "relationship_moment": "primary_relationships",
    "session_episode": "primary_sessions",
    "scene_bound_memory": "primary_scenes",
    "experience_event": "primary_scenes",
}
TARGET_DIR = {
    "primary_projects": "memory/mem/primary/projects",
    "primary_relationships": "memory/mem/primary/relationships",
    "primary_sessions": "memory/mem/primary/sessions",
    "primary_scenes": "memory/mem/primary/scenes",
}
FRONT_MATTER_KEYS = (
    "summary",
    "schema_version",
    "memory_layer",
    "memory_kind",
    "source_event_kind",
    "promotion_policy",
    "safety_scope",
    "namespace",
    "lineage_fingerprint",
    "idempotency_key",
    "summary_origin",
    "content_role",
    "title",
)
MAX_TOKEN = 128
MAX_TITLE = 160
MAX_SUMMARY = 2048
MAX_PAGE_BYTES = 8192
FORBIDDEN_CONTENT_KEYS = {
    "raw_source_text",
    "source_text",
    "raw_text",
    "messages",
    "source_messages",
    "message_history",
    "raw_message_history",
    "raw_affect",
    "raw_affect_estimates",
    "affect_estimates",
}
PROJECTION_FORBIDDEN_KEYS = {
    "store_root_path",
    "candidate_id",
    "namespace",
    "target_relative_path",
    "lineage_fingerprint",
    "idempotency_key",
    "page_markdown",
    "page_digest",
}


def parse_page_markdown(markdown: str) -> dict[str, Any]:
    if not markdown.startswith("---\n"):
        return invalid("primary_writer_handoff_page_front_matter_missing")
    remainder = markdown[4:]
    marker = "\n---\n"
    if marker not in remainder:
        return invalid("primary_writer_handoff_page_front_matter_invalid")
    front_matter, body = remainder.split(marker, 1)
    metadata: dict[str, str] = {}
    keys: list[str] = []
    for line in front_matter.splitlines():
        key, separator, raw_value = line.partition(": ")
        if not separator or not key or key in metadata:
            return invalid("primary_writer_handoff_page_front_matter_invalid")
        try:
            parsed_value = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            return invalid("primary_writer_handoff_page_front_matter_invalid")
        if not isinstance(parsed_value, str) or bad_text(parsed_value):
            return invalid("primary_writer_handoff_page_front_matter_invalid")
        keys.append(key)
        metadata[key] = parsed_value
    if tuple(keys) != FRONT_MATTER_KEYS:
        return invalid("primary_writer_handoff_page_front_matter_keys_invalid")
    return {"valid": True, "metadata": metadata, "body": body, "blocked_reasons": []}


def path_reasons(value: object, expected: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return ["primary_writer_handoff_target_path_invalid"]
    if bad_text(value) or "\\" in value or value.startswith("/"):
        return ["primary_writer_handoff_target_path_invalid"]
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        return ["primary_writer_handoff_target_path_invalid"]
    if path.as_posix() != value or value != expected:
        return ["primary_writer_handoff_target_path_mismatch"]
    if not any(value.startswith(f"{directory}/") for directory in TARGET_DIR.values()):
        return ["primary_writer_handoff_target_path_outside_primary_scope"]
    return []


def contains_forbidden_content_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key in FORBIDDEN_CONTENT_KEYS:
                return True
            if contains_forbidden_content_key(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(contains_forbidden_content_key(item) for item in value)
    return False


def contains_key(value: object, keys: set[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key in keys:
                return True
            if contains_key(item, keys):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(contains_key(item, keys) for item in value)
    return False


def exact_fields(
    value: Mapping[str, Any], expected: set[str], reason: str
) -> list[str]:
    return [] if set(value.keys()) == expected else [reason]


def exact(
    value: Mapping[str, Any], expected: Mapping[str, Any], prefix: str
) -> list[str]:
    reasons: list[str] = []
    for key, wanted in expected.items():
        actual = value.get(key)
        matches = (
            type(actual) is bool and actual is wanted
            if isinstance(wanted, bool)
            else actual == wanted
        )
        if not matches:
            reasons.append(f"{prefix}{key}_invalid")
    return reasons


def token(value: object, reason: str) -> tuple[str, list[str]]:
    if not isinstance(value, str):
        return "", [reason]
    normalized = value.strip()
    if (
        value != normalized
        or not normalized
        or len(normalized) > MAX_TOKEN
        or bad_text(normalized)
        or any(char in normalized for char in "\n\r\t")
    ):
        return "", [reason]
    return normalized, []


def bad_text(value: str) -> bool:
    return any(
        (ord(char) < 32 and char not in "\n\t")
        or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def stable_hash(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": dedupe(reasons)}
