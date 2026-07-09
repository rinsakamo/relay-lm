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

Metadata safety: ``provenance`` is restricted to a closed allowlist
(``x_post`` / ``chatgpt_reconstructed``); ``evidence_ids``, ``time_contexts``,
and ``type`` must be short, non-empty, control-character/newline-free
strings that do not resemble a credential/secret. A fact_candidate or
style_observation that fails any of these checks is dropped as invalid
(fail-closed, never written) rather than silently coerced -- ``statement``
and ``description`` bodies themselves are not subject to the credential
heuristic since they are free-form first-person text, not metadata.

Every write (directory creation, atomic file write, existing-file read
during conflict detection) is fail-closed: any ``OSError`` is wrapped into
a content-free ``BridgeInputError`` and never surfaces a raw traceback,
absolute path, or exception message. Writing multiple approved facts is
all-or-nothing within one run: if any file in the batch fails to write,
every file newly written during that same run is rolled back so no
partial batch is left on disk. Each artifact's temp file is created with
``O_EXCL`` (and ``O_NOFOLLOW`` where supported), so a pre-created symlink
or stale temp file at that exact path is never followed or written
through, and it is committed to its final name with ``os.link`` -- never
``os.replace`` -- so a target that already exists at commit time (for
example one that appeared after preflight, a TOCTOU race) is never
silently clobbered.

stdout is always a single content-free JSON projection (counts and reason
ids only, never statement/description bodies, absolute paths, or raw
exception text).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "relaylm.twin_review_import_bridge_projection.v1"
IMPORT_SOURCE_SCHEMA_VERSION = "relaylm.twin_review_import_source.v0"
IMPORT_SUBPATH = (".relaylm", "sources", "imports", "twin-extraction")
MAX_REVIEW_BYTES = 50 * 1024 * 1024

ALLOWED_PROVENANCE = frozenset({"x_post", "chatgpt_reconstructed"})
MAX_EVIDENCE_ID_LENGTH = 200
MAX_TIME_CONTEXT_LENGTH = 32
MAX_FACT_TYPE_LENGTH = 64
MAX_CATEGORY_LENGTH = 64

_CONTROL_OR_NEWLINE_RE = re.compile(r"[\x00-\x1f\x7f]")
_CREDENTIAL_LIKE_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}"
    r"|gh[opsu]_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{12,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:bearer\s+[A-Za-z0-9._-]{10,})"
    r"|(?i:\b(?:password|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*\S+)"
)


class BridgeInputError(Exception):
    """Fail-closed input/write error. Messages must stay content-free."""


def _is_scalar(item: object) -> bool:
    return isinstance(item, (str, int, float)) and not isinstance(item, bool)


def _is_safe_identifier(value: object, *, max_length: int) -> bool:
    """Non-empty, bounded-length, single-line, non-credential-shaped string.

    Used for structured metadata identifiers (evidence_ids, time_contexts,
    fact type, style category) -- never for free-form statement/description
    text, which legitimately spans multiple lines and is not screened
    against the credential heuristic.
    """
    if not isinstance(value, str) or not (1 <= len(value) <= max_length):
        return False
    if _CONTROL_OR_NEWLINE_RE.search(value):
        return False
    if _CREDENTIAL_LIKE_RE.search(value):
        return False
    return True


def _valid_evidence_id_list(raw: object) -> list[str] | None:
    if not isinstance(raw, list) or not raw:
        return None
    if not all(item is None or _is_scalar(item) for item in raw):
        return None
    evidence_ids = sorted({str(item) for item in raw if item is not None})
    if not evidence_ids:
        return None
    if not all(_is_safe_identifier(item, max_length=MAX_EVIDENCE_ID_LENGTH) for item in evidence_ids):
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
    if not labels.issubset(ALLOWED_PROVENANCE):
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
        if not isinstance(value, list) or not all(_is_safe_identifier(item, max_length=MAX_TIME_CONTEXT_LENGTH) for item in value):
            return None
        return sorted(dict.fromkeys(value))
    if "time_context" in raw:
        value = raw["time_context"]
        if not _is_safe_identifier(value, max_length=MAX_TIME_CONTEXT_LENGTH):
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
    if not _is_safe_identifier(fact_type, max_length=MAX_FACT_TYPE_LENGTH):
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
    if not _is_safe_identifier(category, max_length=MAX_CATEGORY_LENGTH):
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
        try:
            if current.is_symlink():
                return True
            if current.exists():
                resolved = current.resolve()
                if not _is_relative_to(resolved, root_resolved):
                    return True
        except OSError:
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
    try:
        root_resolved = workspace_root.resolve()
    except OSError:
        return [], "workspace root resolve failed"
    import_dir = workspace_root.joinpath(*IMPORT_SUBPATH)
    if _has_symlink_between(root_resolved, workspace_root, import_dir):
        return [], "import write path rejected (symlink)"
    pending: list[tuple[str, str]] = []
    for filename, text in writes:
        target = import_dir / filename
        try:
            if target.is_symlink():
                return [], "import write path rejected (symlink)"
            exists = target.exists()
            if exists and target.is_dir():
                return [], "import write path conflict"
            existing = target.read_text(encoding="utf-8") if exists else None
        except (OSError, UnicodeDecodeError):
            return [], "import artifact unreadable"
        if exists:
            if existing != text:
                return [], "import artifact conflict"
            continue  # identical content already present: idempotent, nothing to do
        pending.append((filename, text))
    return pending, None


def _create_temp_file_exclusive(import_dir: Path, filename: str, text: str) -> Path:
    """Create a uniquely-named temp file next to ``filename`` and write
    ``text`` into it.

    Uses ``O_EXCL`` so the call fails instead of succeeding if anything
    already occupies that exact path -- a pre-created symlink or a stale
    leftover temp file from a previous run -- and ``O_NOFOLLOW`` (where
    supported) as defense in depth against ever traversing a symlink at
    the final path component. Never uses ``Path.write_text``/``open()``
    for this step, since plain ``open()`` follows an existing symlink and
    would write through it to wherever it points.
    """
    temp_target = import_dir / f".{filename}.tmp-{os.getpid()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(temp_target, flags, 0o644)
    except OSError as exc:
        raise BridgeInputError("import artifact write failed") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        # We created this exact file ourselves (the os.open above
        # succeeded), so it is ours to remove on a partial-write failure.
        temp_target.unlink(missing_ok=True)
        raise BridgeInputError("import artifact write failed") from exc
    return temp_target


def _commit_temp_to_target(temp_target: Path, target: Path) -> None:
    """Commit ``temp_target`` to its final ``target`` name without ever
    clobbering an existing target.

    Uses ``os.link`` (an atomic, no-clobber hard-link) rather than
    ``os.replace``/``os.rename``, since replace/rename unconditionally
    overwrite an existing destination. If ``target`` already exists at
    commit time -- for example it appeared after preflight found nothing
    there, a TOCTOU race -- ``os.link`` fails with ``FileExistsError``
    and the pre-existing ``target`` is left completely untouched. The
    temp file is always removed afterward either way.
    """
    try:
        os.link(temp_target, target)
    except OSError as exc:
        temp_target.unlink(missing_ok=True)
        raise BridgeInputError("import artifact target already exists") from exc
    temp_target.unlink(missing_ok=True)


def _write_pending_atomically(import_dir: Path, pending: list[tuple[str, str]]) -> None:
    """Write every pending (filename, text) artifact, or none at all.

    Each artifact is written to an exclusively-created temp file and then
    committed to its final name with a no-clobber hard link (see
    ``_create_temp_file_exclusive`` / ``_commit_temp_to_target``). If any
    step in the batch fails, every target already committed during this
    call is rolled back (unlinked), so a partial failure never leaves a
    half-written batch on disk. Only ``OSError`` (never a raw traceback)
    can surface, and only as a content-free ``BridgeInputError``.
    """
    try:
        import_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BridgeInputError("import directory create failed") from exc

    written_targets: list[Path] = []
    for filename, text in pending:
        target = import_dir / filename
        try:
            temp_target = _create_temp_file_exclusive(import_dir, filename, text)
            _commit_temp_to_target(temp_target, target)
        except BridgeInputError:
            for committed in written_targets:
                committed.unlink(missing_ok=True)
            raise
        written_targets.append(target)


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
    invalid_fact_count = reviewed_fact_count - len(normalized_facts)
    invalid_style_count = reviewed_style_count - len(normalized_styles)

    eligible_facts = [fact for fact in normalized_facts if fact["sensitivity"] == "general"]
    private_only_facts = [fact for fact in normalized_facts if fact["sensitivity"] != "general"]

    reason_ids: list[str] = ["style_observations_dry_run_projection_only", f"approved_styles_{approved_styles}"]
    if private_only_facts:
        reason_ids.append("private_only_excluded_by_default")
    if invalid_fact_count:
        reason_ids.append("invalid_fact_candidates_dropped")
    if invalid_style_count:
        reason_ids.append("invalid_style_observations_dropped")

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
            _write_pending_atomically(import_dir, pending)
        written_count = len(writes)

    skipped_count = len(normalized_facts) - written_count

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "write_imports" if write_imports else "dry_run",
        "reviewed_style_count": reviewed_style_count,
        "reviewed_fact_count": reviewed_fact_count,
        "invalid_fact_count": invalid_fact_count,
        "invalid_style_count": invalid_style_count,
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
