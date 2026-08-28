#!/usr/bin/env python3
"""RelayLM v1 repository authority declarations.

This module is the canonical schema for owner-local repository authority. A
semantic owner declares its own identity, canonical surfaces, supporting
implementation/test surfaces, dependencies, and produced or referenced
evidence in exactly one writable declaration under ``.ai/authority/``.

The rules enforced here implement one repository invariant:

    every authoritative fact has exactly one canonical writer.

Canonical authority surfaces are therefore exclusive: two owners may share an
implementation or test surface, because code and tests are write surfaces
rather than authority claims, but one authority document has one writer.
Reverse relationships (``consumed_by``) and aggregate views are derived from
these declarations rather than declared a second time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

import yaml

AUTHORITY_DIRECTORY = ".ai/authority"
AGENT_CONTRACT_PATH = ".ai/agent-contract.yaml"
DOCUMENTATION_DIRECTORY = "docs"
DECLARATION_SCHEMA_VERSION = 1

#: Aggregates that a semantic lane would otherwise have to share a write on.
PROHIBITED_AGGREGATES = ("docs/authority-map.yaml",)

#: Freshness classes every agent contract must declare.
REQUIRED_FRESHNESS_CLASSES = ("evidence", "historical", "live", "repository")

#: Repository/host facts that must always be re-fetched rather than remembered.
REQUIRED_LIVE_FACTS = (
    "ci_check_state",
    "issue_state",
    "open_pull_requests",
    "repository_head",
)

_OWNER_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_EVIDENCE_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"
_OWNER_ID_RE = re.compile(_OWNER_ID_PATTERN)
_COMMIT_RE = re.compile(r"\b[0-9a-f]{40}\b")
_EVIDENCE_ID_RE = re.compile(_EVIDENCE_ID_PATTERN)

_SURFACE_FIELDS = ("canonical_surfaces", "references", "implementation", "tests", "annotations")
_DECLARATION_FIELDS = (
    "schema_version",
    "id",
    "summary",
    "owner_issue",
    *_SURFACE_FIELDS,
    "qualification_inputs",
    "depends_on",
    "evidence",
    "evidence_refs",
)
_EVIDENCE_FIELDS = ("id", "summary", "surfaces")
_CONTRACT_FIELDS = ("schema_version", "bootstrap", "freshness")
_BOOTSTRAP_FIELDS = ("path", "purpose")
_FRESHNESS_FIELDS = ("classes", "facts")
_FRESHNESS_CLASS_FIELDS = ("summary", "persistent_authority")


class AuthorityError(ValueError):
    """Raised when repository authority declarations are not valid."""


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One evidence artifact owned by its producing semantic owner."""

    id: str
    summary: str
    surfaces: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Declaration:
    """One semantic owner's local repository authority."""

    id: str
    summary: str
    path: str
    owner_issue: int | None = None
    canonical_surfaces: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    implementation: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    annotations: tuple[str, ...] = ()
    qualification_inputs: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BootstrapStep:
    """One ordered step an agent reads when orienting in the repository."""

    path: str
    purpose: str


@dataclass(frozen=True, slots=True)
class FreshnessClass:
    """One freshness class and whether it may be persistent repository authority."""

    id: str
    summary: str
    persistent_authority: bool


@dataclass(frozen=True, slots=True)
class AgentContract:
    """The repository bootstrap read order and freshness contract."""

    bootstrap: tuple[BootstrapStep, ...]
    classes: Mapping[str, FreshnessClass]
    facts: Mapping[str, str]

    def freshness_of(self, fact: str) -> str:
        """Return the declared freshness class of ``fact``."""

        try:
            return self.facts[fact]
        except KeyError:
            raise AuthorityError(
                f"freshness fact '{fact}' is not classified by {AGENT_CONTRACT_PATH}"
            ) from None

    def is_persistent_authority(self, fact: str) -> bool:
        """Return whether ``fact`` may be stored as persistent repository authority."""

        return self.classes[self.freshness_of(fact)].persistent_authority


@dataclass(slots=True)
class _Parsed:
    path: str
    stem: str
    document: Mapping[str, Any] | None
    errors: list[str] = field(default_factory=list)
    declaration: Declaration | None = None


def declaration_paths(root: Path) -> tuple[Path, ...]:
    """Return the declaration files under ``root`` in deterministic order."""

    directory = root / AUTHORITY_DIRECTORY
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.yaml")))


def validate_repository(root: Path) -> tuple[str, ...]:
    """Return sorted validation errors for the declarations under ``root``."""

    parsed = [_parse(root, path) for path in declaration_paths(root)]
    errors: list[str] = [message for item in parsed for message in item.errors]
    declarations = [item.declaration for item in parsed if item.declaration is not None]

    if not parsed:
        errors.append("no semantic owner declaration exists")

    errors.extend(_cross_owner_errors(declarations))
    return tuple(sorted(errors))


def load_declarations(root: Path) -> tuple[Declaration, ...]:
    """Return validated declarations under ``root`` ordered by owner id."""

    errors = validate_repository(root)
    if errors:
        raise AuthorityError("\n".join(errors))
    parsed = [_parse(root, path) for path in declaration_paths(root)]
    declarations = [item.declaration for item in parsed if item.declaration is not None]
    return tuple(sorted(declarations, key=lambda item: item.id))


def consumers_of(declarations: Sequence[Declaration]) -> dict[str, tuple[str, ...]]:
    """Return the derived reverse dependency view keyed by owner id."""

    derived: dict[str, list[str]] = {item.id: [] for item in declarations}
    for declaration in declarations:
        for dependency in declaration.depends_on:
            derived.setdefault(dependency, []).append(declaration.id)
    return {owner: tuple(sorted(consumers)) for owner, consumers in sorted(derived.items())}


QUALIFICATION_MANIFEST_FORMAT_VERSION = 1


def qualification_owner_closure(
    declarations: Sequence[Declaration],
    *,
    roots: Sequence[str],
) -> tuple[str, ...]:
    """Return the deterministic transitive owner closure for qualification roots."""

    owners_by_id = {declaration.id: declaration for declaration in declarations}
    normalized_roots = tuple(sorted(set(roots)))
    if not normalized_roots:
        raise AuthorityError("qualification roots must not be empty")
    for root in normalized_roots:
        if root not in owners_by_id:
            raise AuthorityError(f"unknown qualification root '{root}'")

    closure: set[str] = set()

    def walk(owner: str) -> None:
        if owner in closure:
            return
        closure.add(owner)
        for dependency in owners_by_id[owner].depends_on:
            walk(dependency)

    for root in normalized_roots:
        walk(root)
    return tuple(sorted(closure))


def qualification_manifest(
    root: Path,
    declarations: Sequence[Declaration],
    *,
    roots: Sequence[str],
) -> dict[str, object]:
    """Derive the owner-local qualification manifest for ``roots``."""

    del root  # paths were validated while declarations were loaded
    owners_by_id = {declaration.id: declaration for declaration in declarations}
    normalized_roots = tuple(sorted(set(roots)))
    closure = qualification_owner_closure(declarations, roots=normalized_roots)
    return {
        "format_version": QUALIFICATION_MANIFEST_FORMAT_VERSION,
        "roots": list(normalized_roots),
        "owners": [
            {
                "id": owner,
                "qualification_inputs": list(owners_by_id[owner].qualification_inputs),
            }
            for owner in closure
        ],
    }


def qualification_fingerprint(
    root: Path,
    declarations: Sequence[Declaration],
    *,
    roots: Sequence[str],
) -> str:
    """Hash manifest identity and exact selected file bytes for ``roots``."""

    manifest = qualification_manifest(root, declarations, roots=roots)
    manifest_bytes = json.dumps(
        manifest,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(b"relaylm-qualification-fingerprint-v1\0")
    digest.update(len(manifest_bytes).to_bytes(8, "big"))
    digest.update(manifest_bytes)

    selected_paths = sorted(
        {
            path
            for owner in manifest["owners"]
            for path in owner["qualification_inputs"]  # type: ignore[index]
        }
    )
    for relative in selected_paths:
        path_bytes = str(relative).encode("utf-8")
        content = (root / str(relative)).read_bytes()
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def _parse(root: Path, path: Path) -> _Parsed:
    relative = path.relative_to(root).as_posix()
    stem = path.stem
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:  # pragma: no cover - defensive
        return _Parsed(relative, stem, None, [f"{relative}: declaration is not readable YAML: {error}"])

    if not isinstance(document, Mapping):
        return _Parsed(relative, stem, None, [f"{relative}: declaration must be a YAML mapping"])

    item = _Parsed(relative, stem, document)
    _validate_document(root, item)
    return item


def _validate_document(root: Path, item: _Parsed) -> None:
    document = item.document
    assert document is not None
    prefix = item.path
    errors = item.errors
    for key in document:
        if key not in _DECLARATION_FIELDS:
            errors.append(f"{prefix}: unknown field '{key}'")

    for value in _scalar_strings(document):
        for match in sorted(set(_COMMIT_RE.findall(value))):
            errors.append(
                f"{prefix}: live repository state '{match}' must not be copied into"
                " persistent authority"
            )

    if document.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        errors.append(f"{prefix}: schema_version must be {DECLARATION_SCHEMA_VERSION}")

    identifier = document.get("id")
    if not isinstance(identifier, str) or not _OWNER_ID_RE.fullmatch(identifier):
        errors.append(f"{prefix}: id '{identifier}' must match '{_OWNER_ID_PATTERN}'")
        identifier = None
    elif identifier != item.stem:
        errors.append(f"{prefix}: file stem must equal owner id '{identifier}'")

    summary = document.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append(f"{prefix}: summary must be a non-empty string")
        summary = ""

    owner_issue = document.get("owner_issue")
    if owner_issue is not None and (
        isinstance(owner_issue, bool) or not isinstance(owner_issue, int) or owner_issue <= 0
    ):
        errors.append(f"{prefix}: owner_issue must be a positive integer")
        owner_issue = None

    surfaces: dict[str, tuple[str, ...]] = {}
    for name in _SURFACE_FIELDS:
        surfaces[name] = _read_paths(root, prefix, name, document.get(name), errors)

    depends_on = _read_identifiers(prefix, "depends_on", document.get("depends_on"), errors)
    if identifier is not None and identifier in depends_on:
        errors.append(f"{prefix}: depends_on must not include the owner itself")
        depends_on = tuple(value for value in depends_on if value != identifier)

    evidence = _read_evidence(root, prefix, document.get("evidence"), errors)
    qualification_inputs = _read_paths(
        root,
        prefix,
        "qualification_inputs",
        document.get("qualification_inputs"),
        errors,
    )
    evidence_refs = _read_identifiers(
        prefix, "evidence_refs", document.get("evidence_refs"), errors, pattern=_EVIDENCE_ID_RE
    )
    produced = {record.id for record in evidence}
    for reference in evidence_refs:
        if reference in produced:
            errors.append(
                f"{prefix}: evidence_refs '{reference}' is already produced by this owner"
            )

    if identifier is not None:
        owned_surfaces = {
            *surfaces["canonical_surfaces"],
            *surfaces["implementation"],
            *surfaces["tests"],
            *surfaces["annotations"],
            *(surface for record in evidence for surface in record.surfaces),
        }
        for qualification_input in qualification_inputs:
            if qualification_input not in owned_surfaces:
                errors.append(
                    f"{prefix}: qualification input '{qualification_input}' must already"
                    f" be declared by {identifier}"
                )
            elif not (root / qualification_input).is_file():
                errors.append(
                    f"{prefix}: qualification input '{qualification_input}' must be a file"
                )

    if identifier is None:
        return

    item.declaration = Declaration(
        id=identifier,
        summary=summary.strip(),
        path=prefix,
        owner_issue=owner_issue,
        canonical_surfaces=surfaces["canonical_surfaces"],
        references=surfaces["references"],
        implementation=surfaces["implementation"],
        tests=surfaces["tests"],
        annotations=surfaces["annotations"],
        qualification_inputs=qualification_inputs,
        depends_on=depends_on,
        evidence=evidence,
        evidence_refs=evidence_refs,
    )


def _scalar_strings(value: Any) -> Iterable[str]:
    """Yield every string scalar reachable from ``value``."""

    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for entry in value.values():
            yield from _scalar_strings(entry)
    elif isinstance(value, list):
        for entry in value:
            yield from _scalar_strings(entry)


def _read_paths(
    root: Path, prefix: str, name: str, value: Any, errors: list[str]
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        errors.append(f"{prefix}: {name} must be a list of repository paths")
        return ()

    seen: list[str] = []
    for entry in value:
        if entry in seen:
            errors.append(f"{prefix}: {name} repeats '{entry}'")
            continue
        seen.append(entry)
        if not _is_repository_relative(entry):
            errors.append(f"{prefix}: {name} path '{entry}' must be repository-relative")
            continue
        if not (root / entry).exists():
            errors.append(f"{prefix}: {name} path '{entry}' does not exist")
    return tuple(seen)


def _is_repository_relative(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or value.endswith("/"):
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and all(part not in ("..", ".") for part in parts)


def _read_identifiers(
    prefix: str,
    name: str,
    value: Any,
    errors: list[str],
    *,
    pattern: re.Pattern[str] = _OWNER_ID_RE,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        errors.append(f"{prefix}: {name} must be a list of identifiers")
        return ()

    seen: list[str] = []
    for entry in value:
        if entry in seen:
            errors.append(f"{prefix}: {name} repeats '{entry}'")
            continue
        seen.append(entry)
        if not pattern.fullmatch(entry):
            errors.append(f"{prefix}: {name} '{entry}' must match '{pattern.pattern}'")
    return tuple(seen)


def _read_evidence(
    root: Path, prefix: str, value: Any, errors: list[str]
) -> tuple[EvidenceRecord, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        errors.append(f"{prefix}: evidence must be a list of evidence records")
        return ()

    records: list[EvidenceRecord] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            errors.append(f"{prefix}: evidence record must be a mapping")
            continue
        for key in entry:
            if key not in _EVIDENCE_FIELDS:
                errors.append(f"{prefix}: unknown evidence field '{key}'")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not _EVIDENCE_ID_RE.fullmatch(identifier):
            errors.append(f"{prefix}: evidence id '{identifier}' must match '{_EVIDENCE_ID_PATTERN}'")
            continue
        summary = entry.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"{prefix}: evidence '{identifier}' summary must be a non-empty string")
            summary = ""
        surfaces = _read_paths(
            root, prefix, f"evidence '{identifier}' surfaces", entry.get("surfaces"), errors
        )
        if not surfaces:
            errors.append(f"{prefix}: evidence '{identifier}' must declare at least one surface")
        if any(record.id == identifier for record in records):
            errors.append(f"{prefix}: evidence repeats '{identifier}'")
            continue
        records.append(EvidenceRecord(identifier, summary.strip(), surfaces))
    return tuple(records)


def _cross_owner_errors(declarations: Sequence[Declaration]) -> list[str]:
    errors: list[str] = []

    owners_by_id = {declaration.id: declaration for declaration in declarations}
    duplicate_ids = _duplicates(declaration.id for declaration in declarations)
    for identifier in sorted(duplicate_ids):
        errors.append(f"{identifier}: semantic owner is declared more than once")

    canonical_writers: dict[str, list[str]] = {}
    for declaration in declarations:
        for surface in declaration.canonical_surfaces:
            canonical_writers.setdefault(surface, []).append(declaration.id)
    for surface, writers in sorted(canonical_writers.items()):
        if len(writers) > 1:
            joined = ", ".join(sorted(writers))
            errors.append(f"{surface}: canonical surface is claimed by {joined}")

    for declaration in declarations:
        for surface in declaration.references:
            writers = canonical_writers.get(surface)
            if not writers:
                errors.append(
                    f"{declaration.path}: reference '{surface}' is not a canonical surface"
                    " of any semantic owner"
                )
            elif declaration.id in writers:
                errors.append(
                    f"{declaration.path}: reference '{surface}' is already owned by"
                    f" {declaration.id}"
                )

        for dependency in declaration.depends_on:
            if dependency not in owners_by_id:
                errors.append(
                    f"{declaration.path}: depends_on '{dependency}' is not a declared"
                    " semantic owner"
                )

    producers: dict[str, list[str]] = {}
    for declaration in declarations:
        for record in declaration.evidence:
            producers.setdefault(record.id, []).append(declaration.id)
    for evidence_id, owners in sorted(producers.items()):
        if len(owners) > 1:
            joined = ", ".join(sorted(owners))
            errors.append(f"{evidence_id}: evidence is produced by {joined}")

    for declaration in declarations:
        for reference in declaration.evidence_refs:
            if reference not in producers:
                errors.append(
                    f"{declaration.path}: evidence_refs '{reference}' is not produced by"
                    " any semantic owner"
                )

    errors.extend(_dependency_cycle_errors(owners_by_id))
    errors.extend(_evidence_surface_errors(declarations))
    return errors


def _evidence_surface_errors(declarations: Sequence[Declaration]) -> list[str]:
    """Return errors where an evidence surface is claimed outside its producer."""

    errors: list[str] = []
    producers: dict[str, str] = {}
    for declaration in declarations:
        for record in declaration.evidence:
            for surface in record.surfaces:
                producers.setdefault(surface, declaration.id)

    for declaration in declarations:
        owned = {
            surface for record in declaration.evidence for surface in record.surfaces
        }
        for name in _SURFACE_FIELDS:
            for surface in getattr(declaration, name):
                producer = producers.get(surface)
                if producer is None:
                    continue
                if surface in owned:
                    errors.append(
                        f"{declaration.path}: '{surface}' is an evidence surface and"
                        f" must not also be declared as {name}"
                    )
                else:
                    errors.append(
                        f"{surface}: evidence surface owned by {producer} must not be"
                        f" declared by {declaration.id}"
                    )
    return errors


def _dependency_cycle_errors(owners_by_id: Mapping[str, Declaration]) -> list[str]:
    errors: list[str] = []
    reported: set[frozenset[str]] = set()

    def walk(owner: str, path: list[str]) -> None:
        if owner in path:
            cycle = path[path.index(owner):] + [owner]
            key = frozenset(cycle)
            if key not in reported:
                reported.add(key)
                errors.append("depends_on cycle: " + " -> ".join(cycle))
            return
        declaration = owners_by_id.get(owner)
        if declaration is None:
            return
        for dependency in declaration.depends_on:
            walk(dependency, [*path, owner])

    for owner in sorted(owners_by_id):
        walk(owner, [])
    return errors


def agent_contract_errors(root: Path) -> tuple[str, ...]:
    """Return sorted validation errors for the repository agent contract."""

    path = root / AGENT_CONTRACT_PATH
    if not path.is_file():
        return (f"{AGENT_CONTRACT_PATH}: agent contract is missing",)

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:  # pragma: no cover - defensive
        return (f"{AGENT_CONTRACT_PATH}: agent contract is not readable YAML: {error}",)

    errors: list[str] = []
    if not isinstance(document, Mapping):
        return (f"{AGENT_CONTRACT_PATH}: agent contract must be a YAML mapping",)

    for key in document:
        if key not in _CONTRACT_FIELDS:
            errors.append(f"{AGENT_CONTRACT_PATH}: unknown field '{key}'")

    if document.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        errors.append(
            f"{AGENT_CONTRACT_PATH}: schema_version must be {DECLARATION_SCHEMA_VERSION}"
        )

    errors.extend(_bootstrap_errors(root, document.get("bootstrap")))
    errors.extend(_freshness_errors(document.get("freshness")))
    return tuple(sorted(errors))


def read_agent_contract(root: Path) -> AgentContract:
    """Return the validated agent contract declared under ``root``."""

    errors = agent_contract_errors(root)
    if errors:
        raise AuthorityError("\n".join(errors))

    document = yaml.safe_load((root / AGENT_CONTRACT_PATH).read_text(encoding="utf-8"))
    bootstrap = tuple(
        BootstrapStep(str(step["path"]), str(step["purpose"]))
        for step in document["bootstrap"]
    )
    freshness = document["freshness"]
    classes = {
        name: FreshnessClass(
            name, str(body["summary"]), bool(body["persistent_authority"])
        )
        for name, body in sorted(freshness["classes"].items())
    }
    facts = {name: str(value) for name, value in sorted(freshness["facts"].items())}
    return AgentContract(bootstrap, classes, facts)


def _bootstrap_errors(root: Path, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(step, Mapping) for step in value):
        return [f"{AGENT_CONTRACT_PATH}: bootstrap must be a list of read steps"]
    if not value:
        return [f"{AGENT_CONTRACT_PATH}: bootstrap must declare at least one read step"]

    errors: list[str] = []
    seen: list[str] = []
    for step in value:
        for key in step:
            if key not in _BOOTSTRAP_FIELDS:
                errors.append(f"{AGENT_CONTRACT_PATH}: unknown bootstrap field '{key}'")
        path = step.get("path")
        purpose = step.get("purpose")
        if not isinstance(path, str) or not _is_repository_relative(path):
            errors.append(f"{AGENT_CONTRACT_PATH}: bootstrap path '{path}' must be repository-relative")
            continue
        if not isinstance(purpose, str) or not purpose.strip():
            errors.append(
                f"{AGENT_CONTRACT_PATH}: bootstrap step '{path}' must state a purpose"
            )
        if path in seen:
            errors.append(f"{AGENT_CONTRACT_PATH}: bootstrap repeats '{path}'")
            continue
        seen.append(path)
        if not (root / path).exists():
            errors.append(f"{AGENT_CONTRACT_PATH}: bootstrap path '{path}' does not exist")
    return errors


def _freshness_errors(value: Any) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{AGENT_CONTRACT_PATH}: freshness must be a mapping"]

    errors: list[str] = []
    for key in value:
        if key not in _FRESHNESS_FIELDS:
            errors.append(f"{AGENT_CONTRACT_PATH}: unknown freshness field '{key}'")

    declared = value.get("classes")
    classes: dict[str, bool] = {}
    if not isinstance(declared, Mapping):
        errors.append(f"{AGENT_CONTRACT_PATH}: freshness.classes must be a mapping")
        declared = {}
    for name, body in sorted(declared.items()):
        if not isinstance(body, Mapping):
            errors.append(f"{AGENT_CONTRACT_PATH}: freshness class '{name}' must be a mapping")
            continue
        for key in body:
            if key not in _FRESHNESS_CLASS_FIELDS:
                errors.append(
                    f"{AGENT_CONTRACT_PATH}: unknown freshness class field '{key}'"
                )
        summary = body.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(
                f"{AGENT_CONTRACT_PATH}: freshness class '{name}' summary must be a"
                " non-empty string"
            )
        persistent = body.get("persistent_authority")
        if not isinstance(persistent, bool):
            errors.append(
                f"{AGENT_CONTRACT_PATH}: freshness class '{name}' persistent_authority"
                " must be a boolean"
            )
            continue
        classes[str(name)] = persistent

    known = {str(name) for name in declared}
    missing_required = {
        required for required in REQUIRED_FRESHNESS_CLASSES if required not in known
    }
    for required in sorted(missing_required):
        errors.append(f"{AGENT_CONTRACT_PATH}: freshness.classes must declare '{required}'")

    facts = value.get("facts")
    if not isinstance(facts, Mapping):
        errors.append(f"{AGENT_CONTRACT_PATH}: freshness.facts must be a mapping")
        facts = {}
    for name, class_id in sorted(facts.items()):
        if class_id not in known and class_id not in missing_required:
            errors.append(
                f"{AGENT_CONTRACT_PATH}: freshness fact '{name}' names undeclared"
                f" class '{class_id}'"
            )

    for required in REQUIRED_LIVE_FACTS:
        if required not in facts:
            errors.append(
                f"{AGENT_CONTRACT_PATH}: freshness.facts must classify '{required}'"
            )
            continue
        class_id = facts[required]
        if classes.get(class_id, False):
            errors.append(
                f"{AGENT_CONTRACT_PATH}: freshness fact '{required}' must be classified"
                " as a non-persistent class that is re-fetched live"
            )

    return errors


def documentation_coverage_errors(root: Path) -> tuple[str, ...]:
    """Return sorted errors for documents without a declared semantic owner."""

    errors: list[str] = []
    for aggregate in PROHIBITED_AGGREGATES:
        if (root / aggregate).exists():
            errors.append(
                f"{aggregate}: hand-maintained authority aggregates are prohibited;"
                " owner-local declarations under .ai/authority/ are the canonical writer"
            )

    owned: set[str] = set()
    for path in declaration_paths(root):
        parsed = _parse(root, path)
        document = parsed.document
        if document is None:
            continue
        for name in ("canonical_surfaces", "annotations"):
            value = document.get(name)
            if isinstance(value, list):
                owned.update(entry for entry in value if isinstance(entry, str))

    documentation = root / DOCUMENTATION_DIRECTORY
    if documentation.is_dir():
        for candidate in sorted(documentation.rglob("*")):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(root).as_posix()
            if relative in PROHIBITED_AGGREGATES or relative in owned:
                continue
            errors.append(f"{relative}: document has no semantic owner")

    return tuple(sorted(errors))


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root to validate"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate owner-local authority declarations")

    arguments = parser.parse_args(argv)
    errors = tuple(
        sorted(
            validate_repository(arguments.root)
            + agent_contract_errors(arguments.root)
            + documentation_coverage_errors(arguments.root)
        )
    )
    for message in errors:
        print(message, file=sys.stderr)
    if errors:
        return 1
    print(f"repository authority valid: {len(declaration_paths(arguments.root))} semantic owners")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
