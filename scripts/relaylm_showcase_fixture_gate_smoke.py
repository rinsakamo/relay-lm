#!/usr/bin/env python3
"""Validate the ReLM showcase fixture template public gate.

This smoke intentionally validates the authored public sample fixture in
``docs/tools/relm_showcase_fixture_template.md`` without importing RelayLM
runtime code. The fixture is synthetic/showcase-only and must remain separate
from private Twin Extraction evidence paths.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "tools" / "relm_showcase_fixture_template.md"

ENTRY_ID_RE = re.compile(r"^relm_fx_[0-9]{4}$")
REQUIRED_ENTRY_KEYS = {
    "id",
    "statement",
    "type",
    "provenance",
    "authored_by",
    "time_context",
    "sensitivity",
    "world_refs",
}
ALLOWED_TYPES = {"knowledge", "episodic"}
FORBIDDEN_TWIN_PROVENANCE = {"x_post", "chatgpt_reconstructed"}


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _fenced_block_after_heading(markdown: str, heading: str, language: str = "yaml") -> str:
    start_heading = markdown.find(heading)
    require(start_heading >= 0, f"heading not found: {heading}")
    section = markdown[start_heading:]
    fence = f"```{language}"
    start_fence = section.find(fence)
    require(start_fence >= 0, f"{language} fence not found after: {heading}")
    start = start_fence + len(fence)
    end = section.find("```", start)
    require(end >= 0, f"closing fence not found after: {heading}")
    return section[start:end].strip("\n")


def _strip_inline_comment(value: str) -> str:
    return value.split("#", 1)[0].strip()


def _parse_allowlist(block: str) -> set[str]:
    refs: set[str] = set()
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        refs.add(_strip_inline_comment(line[2:]))
    return refs


def _parse_entries(block: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in block.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("- id: "):
            if current is not None:
                entries.append(current)
            current = {"id": raw_line.split(":", 1)[1].strip()}
            continue
        require(current is not None, f"field before first entry: {raw_line!r}")
        require(raw_line.startswith("  "), f"unexpected sample line shape: {raw_line!r}")
        key, separator, value = raw_line.strip().partition(":")
        require(separator == ":", f"missing key separator: {raw_line!r}")
        current[key] = value.strip()
    if current is not None:
        entries.append(current)
    return entries


def _parse_world_refs(raw_value: str) -> list[str]:
    value = raw_value.strip()
    require(value.startswith("[") and value.endswith("]"), f"world_refs must be inline list: {raw_value!r}")
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip() for item in inner.split(",")]


def _validate_entry(entry: dict[str, str], allowlist: set[str], seen_ids: set[str]) -> None:
    missing = REQUIRED_ENTRY_KEYS - set(entry)
    extra = set(entry) - REQUIRED_ENTRY_KEYS
    require(not missing, {"id": entry.get("id"), "missing": sorted(missing)})
    require("evidence_ids" not in entry, {"id": entry["id"], "evidence_ids_must_be_absent": True})
    require(not extra, {"id": entry["id"], "unexpected_keys": sorted(extra)})

    require(ENTRY_ID_RE.match(entry["id"]), {"invalid_id": entry["id"]})
    require(entry["id"] not in seen_ids, {"duplicate_id": entry["id"]})
    seen_ids.add(entry["id"])

    require(entry["statement"], {"id": entry["id"], "empty_statement": True})
    require(entry["type"] in ALLOWED_TYPES, {"id": entry["id"], "type": entry["type"]})
    require(entry["provenance"] == "synthetic", {"id": entry["id"], "provenance": entry["provenance"]})
    require(entry["provenance"] not in FORBIDDEN_TWIN_PROVENANCE, entry)
    require(entry["authored_by"], {"id": entry["id"], "empty_authored_by": True})
    require(entry["time_context"], {"id": entry["id"], "empty_time_context": True})
    require(entry["sensitivity"] == "general", {"id": entry["id"], "sensitivity": entry["sensitivity"]})
    require(entry["sensitivity"] != "private_only", entry)

    refs = _parse_world_refs(entry["world_refs"])
    unknown_refs = sorted(set(refs) - allowlist)
    require(not unknown_refs, {"id": entry["id"], "unknown_world_refs": unknown_refs})


def main() -> int:
    markdown = DOC_PATH.read_text(encoding="utf-8")
    sample_block = _fenced_block_after_heading(markdown, "## サンプルエントリ")
    allowlist_block = _fenced_block_after_heading(markdown, "## world_refs許可リスト(初期)")

    allowlist = _parse_allowlist(allowlist_block)
    require(allowlist, "world_refs allowlist must not be empty")

    entries = _parse_entries(sample_block)
    require(entries, "sample entries must not be empty")

    seen_ids: set[str] = set()
    for entry in entries:
        _validate_entry(entry, allowlist, seen_ids)

    require(any("マスターのお下がり" in entry["statement"] for entry in entries), "expected hoodie hand-me-down lore")
    print("RelayLM ReLM showcase fixture gate smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
