#!/usr/bin/env python3
"""Twin Extraction review -> Character Workspace governed import source bridge.

Converts a Twin Extraction ``twin_extraction_review.json`` review artifact
(produced by ``scripts/relaylm_twin_extraction_merge.py``) into governed
import-source artifacts under
``<workspace-root>/.relaylm/sources/imports/twin-extraction/`` for CW-A4
(``relaylm.character_workspace``) to read as user-assertion evidence.

This bridge is caller-invoked, bounded, offline, and runtime-non-contact,
matching the P1 Twin Extraction tooling: it does not import the ``relaylm``
package, does not connect to the RelayLM runtime, and never writes MEM /
SOUL / REL / Primary MEM or any uppercase source file directly. It only
ever writes into ``.relaylm/sources/imports/twin-extraction/`` under the
given ``--workspace-root``.

Approval boundary: everything defaults to unapproved (nothing written).
``--approved-facts general-only`` is required to write ``sensitivity ==
"general"`` fact candidates as import-source artifacts; ``private_only``
fact candidates are never written by this tool and there is no automatic
promotion path. ``style_observations`` are counted for the dry-run
projection only in this revision and are never written to disk.

stdout is always a single content-free JSON projection (counts and reason
ids only, never statement/description bodies, absolute paths, or raw
exception text).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "relaylm.twin_review_import_bridge_projection.v0"
IMPORT_SOURCE_SCHEMA_VERSION = "relaylm.twin_review_import_source.v0"
IMPORT_SUBPATH = (".relaylm", "sources", "imports", "twin-extraction")
MAX_REVIEW_BYTES = 50 * 1024 * 1024


class BridgeInputError(Exception):
    """Fail-closed input/write error. Messages must stay content-free."""


def _is_scalar(item: object) -> bool:
    return isinstance(item, (str, int, float)) and not isinstance(item, bool)


def _valid_evidence_id_list(raw: object) -> list[str] | None:
    if not isinstance(raw, list) or not raw:
        return None
    if not all(item is None or _is_scalar(item) for item in raw):
        return None
    evidence_ids = sorted({str(item) for item in raw if item is not None})
    if not evidence_ids:
        return None
    return evidence_ids


def _normalize_provenance(raw: object) -> list[str] | None:
    if _is_scalar(raw):
        labels = {str(raw)}
    elif isinstance(raw, list) and raw:
        if not all(_is_scalar(item) for item in raw):
            return None
        labels = {str(item) for item in raw}
    else:
        return None
    labels = {label for label in labels if label}
    if not labels:
        return None
    return sorted(labels)


def _normalize_time_contexts(raw: dict) -> list[str] | None:
    """Return a normalized time-context list, or None for an invalid shape.

    ``time_contexts`` (a list, matching merge output) takes precedence over
    a scalar ``time_context`` (a single batch-runner-era field), which is
    listified. Neither key present means no time-context evidence.
    """
    if "time_contexts" in raw:
        value = raw["time_contexts"]
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            return None
        return sorted(dict.fromkeys(value))
    if "time_context" in raw:
        value = raw["time_context"]
        if not isinstance(value, str) or not value:
            return None
        return [value]
    return []


def _normalize_fact_candidate(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    statement = raw.get("statement")
    fact_type = raw.get("type")
    if not isinstance(statement, str) or not statement.strip():
        return None
    if not isinstance(fact_type, str) or not fact_type.strip():
        return None
    evidence_ids = _valid_evidence_id_list(raw.get("evidence_ids"))
    if evidence_ids is None:
        return None
    provenance = _normalize_provenance(raw.get("provenance"))
    if provenance is None:
        return None
    time_contexts = _normalize_time_contexts(raw)
    if time_contexts is None:
        return None
    # Fail-closed default: anything other than an explicit "general" label
    # stays private_only, matching the merge CLI's own missing-sensitivity
    # default.
    sensitivity = "general" if raw.get("sensitivity") == "general" else "private_only"
    return {
        "statement": statement,
        "type": fact_type,
        "evidence_ids": evidence_ids,
        "provenance": provenance,
        "time_contexts": time_contexts,
        "sensitivity": sensitivity,
    }


def _normalize_style_observation(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    category = raw.get("category")
    description = raw.get("description")
    if not isinstance(category, str) or not category.strip():
        return None
    if not isinstance(description, str) or not description.strip():
        return None
    evidence_ids = _valid_evidence_id_list(raw.get("evidence_ids"))
    if evidence_ids is None:
        return None
    return {"category": category, "description": description, "evidence_ids": evidence_ids}


def load_review(path: Path) -> dict[str, list]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BridgeInputError("review file not found or unreadable") from exc
    if size > MAX_REVIEW_BYTES:
        raise BridgeInputError("review file exceeds maximum size")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BridgeInputError("review file not found or unreadable") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BridgeInputError("review file is not valid JSON") from exc
    if not isinstance(data, dict):
        raise BridgeInputError("review file has invalid shape")
    style_raw = data.get("style_observations", [])
    fact_raw = data.get("fact_candidates", [])
    if not isinstance(style_raw, list) or not isinstance(fact_raw, list):
        raise BridgeInputError("review file has invalid shape")
    return {"style_observations": style_raw, "fact_candidates": fact_raw}


def _hash_parts(*parts: object) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fact_artifact(fact: dict[str, Any]) -> tuple[str, str]:
    """Return (filename, serialized JSON text) for an approved general fact.

    The filename hash is derived only from the fact's stable identity
    (kind, statement, type, provenance, sensitivity) so that a rerun over
    an unchanged review is idempotent, and a genuinely different fact under
    the same identity is caught as a conflict rather than silently
    overwritten -- never from a timestamp or random id.
    """
    content_hash = _hash_parts("fact_candidate", fact["statement"], fact["type"], fact["provenance"], fact["sensitivity"])
    filename = f"fact-{content_hash[:24]}.json"
    artifact = {
        "schema_version": IMPORT_SOURCE_SCHEMA_VERSION,
        "source_kind": "twin_extraction_review",
        "role": "user",
        "kind": "fact_candidate",
        "text": fact["statement"],
        "metadata": {
            "fact_type": fact["type"],
            "provenance": fact["provenance"],
            "evidence_ids": fact["evidence_ids"],
            "time_contexts": fact["time_contexts"],
            "sensitivity": fact["sensitivity"],
            "approved": True,
        },
    }
    text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return filename, text


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _has_symlink_between(root_resolved: Path, root: Path, target_dir: Path) -> bool:
    current = root
    for part in target_dir.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return True
        if current.exists():
            try:
                resolved = current.resolve()
            except OSError:
                return True
            if not _is_relative_to(resolved, root_resolved):
                return True
    return False


def _validate_workspace_root(workspace_root: Path) -> str | None:
    if not workspace_root.exists() or not workspace_root.is_dir():
        return "workspace root missing or not a directory"
    if workspace_root.is_symlink():
        return "workspace root must not be a symlink"
    return None


def _preflight_fact_writes(workspace_root: Path, writes: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], str | None]:
    """Return (writes still needed, block reason). A block reason means the
    whole batch is rejected fail-closed; nothing is written."""
    root_resolved = workspace_root.resolve()
    import_dir = workspace_root.joinpath(*IMPORT_SUBPATH)
    if _has_symlink_between(root_resolved, workspace_root, import_dir):
        return [], "import write path rejected (symlink)"
    pending: list[tuple[str, str]] = []
    for filename, text in writes:
        target = import_dir / filename
        if target.is_symlink():
            return [], "import write path rejected (symlink)"
        if target.exists():
            if target.is_dir():
                return [], "import write path conflict"
            try:
                existing = target.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return [], "import artifact conflict"
            if existing != text:
                return [], "import artifact conflict"
            continue  # identical content already present: idempotent, nothing to do
        pending.append((filename, text))
    return pending, None


def run_bridge(
    review_path: Path,
    workspace_root: Path,
    *,
    write_imports: bool,
    approved_facts: str,
    approved_styles: str,
) -> dict[str, Any]:
    review = load_review(review_path)

    workspace_error = _validate_workspace_root(workspace_root)
    if workspace_error is not None:
        raise BridgeInputError(workspace_error)

    reviewed_style_count = len(review["style_observations"])
    reviewed_fact_count = len(review["fact_candidates"])

    normalized_facts = [fact for raw in review["fact_candidates"] if (fact := _normalize_fact_candidate(raw)) is not None]
    normalized_styles = [
        style for raw in review["style_observations"] if (style := _normalize_style_observation(raw)) is not None
    ]

    eligible_facts = [fact for fact in normalized_facts if fact["sensitivity"] == "general"]
    private_only_facts = [fact for fact in normalized_facts if fact["sensitivity"] != "general"]

    reason_ids: list[str] = ["style_observations_dry_run_projection_only", f"approved_styles_{approved_styles}"]
    if private_only_facts:
        reason_ids.append("private_only_excluded_by_default")

    written_count = 0
    if not write_imports:
        reason_ids.append("dry_run_no_write")
    elif approved_facts == "none":
        reason_ids.append("approved_facts_none_default")
    else:
        reason_ids.append("approved_facts_general_only")
        writes_by_filename: dict[str, str] = {}
        for fact in eligible_facts:
            filename, text = _fact_artifact(fact)
            if filename in writes_by_filename and writes_by_filename[filename] != text:
                # Same stable identity (statement/type/provenance/sensitivity) but
                # different content (e.g. differing evidence_ids) within one review
                # file: fail closed rather than silently picking a "last write wins"
                # version.
                raise BridgeInputError("duplicate fact identity produced conflicting import artifacts")
            writes_by_filename[filename] = text
        writes = list(writes_by_filename.items())
        pending, block_reason = _preflight_fact_writes(workspace_root, writes)
        if block_reason is not None:
            raise BridgeInputError(block_reason)
        if pending:
            import_dir = workspace_root.joinpath(*IMPORT_SUBPATH)
            import_dir.mkdir(parents=True, exist_ok=True)
            for filename, text in pending:
                (import_dir / filename).write_text(text, encoding="utf-8")
        written_count = len(writes)

    skipped_count = len(normalized_facts) - written_count

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "write_imports" if write_imports else "dry_run",
        "reviewed_style_count": reviewed_style_count,
        "reviewed_fact_count": reviewed_fact_count,
        "eligible_fact_count": len(eligible_facts),
        "eligible_style_count": len(normalized_styles),
        "private_only_fact_count": len(private_only_facts),
        "written_count": written_count,
        "skipped_count": skipped_count,
        "reason_ids": sorted(set(reason_ids)),
        "output_dir_relative": "/".join(IMPORT_SUBPATH),
        "content_free": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path, help="Path to a Twin Extraction twin_extraction_review.json")
    parser.add_argument("--workspace-root", required=True, type=Path, help="Character workspace root, e.g. runtime/characters/relm")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only; write nothing. This is the default.")
    mode.add_argument("--write-imports", action="store_true", help="Write only approved import-source artifacts.")
    parser.add_argument(
        "--approved-facts",
        choices=("general-only", "none"),
        default="none",
        help="Which fact_candidates are approved for import (default: none, nothing written).",
    )
    parser.add_argument(
        "--approved-styles",
        choices=("none",),
        default="none",
        help="style_observations are dry-run projection only in this revision; no other value is accepted.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        projection = run_bridge(
            args.review,
            args.workspace_root,
            write_imports=bool(args.write_imports),
            approved_facts=args.approved_facts,
            approved_styles=args.approved_styles,
        )
    except BridgeInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
