#!/usr/bin/env python3
"""Validate RelayLM's D1 documentation-governance lock.

The validator enforces the complete canonical metadata contract for documents
that opt into the D1 graph fields. No transitional source family remains
registered: `records/documentation/transitional-assets.json` is the canonical
registry and currently holds zero families. It stays required and fully
validated, so any future family must be added as a reviewed atomic governance
change and is then held to the same path, consumer, removal-gate, replacement
and closed-growth constraints.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "docs/contracts/schemas/documentation-governance-v1"
RECORD_ROOT = ROOT / "records/documentation"

CATALOG_PATH = RECORD_ROOT / "current-records.json"
REGISTRY_PATH = RECORD_ROOT / "retained-record-registry.json"
MANIFEST_PATH = RECORD_ROOT / "retirement-manifest.json"
TRANSITIONAL_PATH = RECORD_ROOT / "transitional-assets.json"

EXPECTED_CLASSES = [
    "current_machine_registry",
    "external_audit_record",
    "recovery_checkpoint",
    "release_validation_receipt",
    "retirement_manifest",
    "stateful_migration_receipt",
]
GRANULARITY_FIELDS = [
    "relaylm_lifecycle",
    "relaylm_primary_consumers",
    "relaylm_authority_level",
]
CORE_FIELDS = [
    "relaylm_doc_type",
    "relaylm_authority",
    "relaylm_status",
    "relaylm_volatility",
    "relaylm_owner",
    "relaylm_update_trigger",
    "relaylm_not_authoritative_for",
]
LIFECYCLES = {
    "accepted_target",
    "current_state",
    "navigation",
    "release_gate",
    "stable",
    "template",
}
AUTHORITY_LEVELS = {
    "concept",
    "exact_contract",
    "lookup",
    "navigation",
    "operation",
    "release",
    "sequencing",
    "subsystem",
    "system",
    "template",
}
RELATIONSHIP_FIELDS = {
    "relaylm_current_status_source",
    "relaylm_decision_source",
    "relaylm_related_authority",
    "relaylm_related_contracts",
    "relaylm_related_decisions",
    "relaylm_related_schemas",
    "relaylm_code_sources",
    "relaylm_verified_by",
}
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
ACTIVE_COLLECTIONS ={"adr", "architecture", "contracts", "planning", "reference", "operations", "guides", "release", "templates"}
ACTIVE_FILENAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
MILESTONE_STEM_RE = re.compile(
    r"^(?:phase[-_]?\d+[a-h0-9]*|wave[-_]?\d+[a-h0-9]*|mvp[-_]?\d+[a-h0-9]*|i\d+[a-h0-9]*|o\d+[a-h0-9]*|e\d+(?:r\d+)?[a-h0-9]*|acg\d+[a-h0-9]*|cw[-_]?a\d+[a-h0-9]*|lc[-_]?\d+[a-h0-9]*|rt[-_]?\d+[a-h0-9]*|pm[-_]?d\d+[a-h0-9]*|ui[-_]?b\d+[a-h0-9]*)(?:[-_]|$)",
    re.IGNORECASE,
)


class GovernanceError(RuntimeError):
    """Raised for bounded validator setup failures."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"{relative(path)}: cannot read valid JSON: {exc}") from exc


def read_schema(root: Path, name: str) -> dict[str, Any]:
    path = root / "docs/contracts/schemas/documentation-governance-v1" / name
    value = read_json(path)
    if not isinstance(value, dict):
        raise GovernanceError(f"{relative(path, root)}: schema must be an object")
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:  # jsonschema reports several specific subclasses
        raise GovernanceError(f"{relative(path, root)}: invalid schema: {exc}") from exc
    return value


def schema_errors(schema: dict[str, Any], value: Any) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path)):
        pointer = "/".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{pointer}: {error.message}")
    return errors


def relative(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def repository_path_error(
    value: Any,
    *,
    prefixes: tuple[str, ...],
    allow_glob: bool = False,
) -> str | None:
    if not isinstance(value, str) or not value:
        return "must be a non-empty repository-relative path"
    if value.startswith("/") or "\\" in value:
        return "must be a canonical repository-relative POSIX path"
    if value.endswith("/") or "//" in value:
        return "must not contain empty path segments"
    if not allow_glob and "*" in value:
        return "must not contain glob syntax"
    if any(character in value for character in "?[]"):
        return "must not contain unsupported glob syntax"
    parts = PurePosixPath(value).parts
    if any(part in {".", ".."} for part in parts):
        return "must not contain dot path segments"
    if not any(value == prefix or value.startswith(f"{prefix}/") for prefix in prefixes):
        return f"must start with one of {sorted(prefixes)!r}"
    return None


def append_repository_path_error(
    errors: list[str],
    label: str,
    value: Any,
    *,
    prefixes: tuple[str, ...],
    allow_glob: bool = False,
) -> bool:
    detail = repository_path_error(value, prefixes=prefixes, allow_glob=allow_glob)
    if detail is None:
        return True
    errors.append(f"{label}: {detail}")
    return False


def parse_front_matter(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {}, [f"{relative(path)}: cannot read Markdown: {exc}"]
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, []
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return {}, [f"{relative(path)}: malformed front matter: {exc}"]
    if not isinstance(metadata, dict):
        return {}, [f"{relative(path)}: front matter must be a mapping"]
    return metadata, []


def allowed_doc_types(path: PurePosixPath) -> set[str]:
    posix = path.as_posix()
    if posix == "docs/README.md":
        return {"documentation_index"}
    if posix == "docs/PROJECT_STATUS.md":
        return {"status"}
    if posix == "docs/DOCUMENTATION_MODEL.md":
        return {"documentation_model"}
    if len(path.parts) < 2 or path.parts[0] != "docs" or path.parts[1] not in ACTIVE_COLLECTIONS:
        return set()
    if path.name == "README.md":
        return {"documentation_index"}
    collection = path.parts[1]
    return {
        "adr": {"adr"},
        "architecture": {"system_architecture", "subsystem_architecture", "concept_policy"},
        "contracts": {"contract"},
        "planning": {"planning"},
        "reference": {"reference"},
        "operations": {"operations"},
        "guides": {"guide"},
        "release": {"release"},
        "templates": {"template"},
    }.get(collection, set())


def iter_relationship_values(metadata: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for key in RELATIONSHIP_FIELDS:
        raw = metadata.get(key)
        if isinstance(raw, str):
            yield key, raw
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    yield key, item


def resolve_repository_path(root: Path, document: Path, value: str) -> Path | None:
    clean = value.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean or clean.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if "*" in clean or clean.endswith("..."):
        return None
    if clean.startswith("docs/") or clean.startswith("scripts/") or clean.startswith("relaylm/") or clean.startswith("records/") or clean.startswith(".github/"):
        return root / clean
    if clean.startswith("/"):
        return None
    if "/" not in clean and not clean.endswith((".md", ".json", ".py", ".yml", ".yaml", ".toml")):
        return None
    return (document.parent / clean).resolve()


def validate_active_documents(root: Path, required_canonical_paths: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    authorities: dict[str, str] = {}
    required_canonical_paths = required_canonical_paths or set()
    docs_root = root / "docs"
    if not docs_root.exists():
        return ["docs/: missing documentation root"]

    for path in sorted(docs_root.rglob("*.md")):
        metadata, parse_errors = parse_front_matter(path)
        errors.extend(parse_errors)
        rel = relative(path, root)
        required = rel in required_canonical_paths
        if not metadata:
            if required:
                errors.append(f"{rel}: new permanent document must define canonical graph metadata")
            continue
        has_granularity = any(field in metadata for field in GRANULARITY_FIELDS)
        if not has_granularity and not required:
            continue
        for field in [*CORE_FIELDS, *GRANULARITY_FIELDS]:
            if field not in metadata:
                errors.append(f"{rel}: canonical graph document missing {field}")

        path_value = PurePosixPath(rel)
        path_types = allowed_doc_types(path_value)
        doc_type = metadata.get("relaylm_doc_type")
        if path_value.name not in {"README.md", "PROJECT_STATUS.md", "DOCUMENTATION_MODEL.md"}:
            if not ACTIVE_FILENAME_RE.fullmatch(path_value.name):
                errors.append(f"{rel}: permanent active filename must use lowercase kebab-case")
            if MILESTONE_STEM_RE.match(path_value.stem):
                errors.append(f"{rel}: permanent active filename must not use a milestone or slice identifier")
        if not path_types:
            errors.append(f"{rel}: canonical graph document is outside the permanent active locations")
        elif doc_type not in path_types:
            errors.append(f"{rel}: relaylm_doc_type {doc_type!r} does not match allowed {sorted(path_types)}")

        if metadata.get("relaylm_status") not in {"current", "target"}:
            errors.append(f"{rel}: canonical graph document status must be current or target")
        if metadata.get("relaylm_lifecycle") not in LIFECYCLES:
            errors.append(f"{rel}: invalid relaylm_lifecycle")
        if metadata.get("relaylm_authority_level") not in AUTHORITY_LEVELS:
            errors.append(f"{rel}: invalid relaylm_authority_level")

        consumers = metadata.get("relaylm_primary_consumers")
        if not isinstance(consumers, list) or not consumers or not all(isinstance(item, str) and item for item in consumers):
            errors.append(f"{rel}: relaylm_primary_consumers must be a non-empty string list")
        triggers = metadata.get("relaylm_update_trigger")
        if not isinstance(triggers, list) or not triggers:
            errors.append(f"{rel}: relaylm_update_trigger must be a non-empty list")

        authority = metadata.get("relaylm_authority")
        if isinstance(authority, str) and authority:
            previous = authorities.get(authority)
            if previous is not None:
                errors.append(f"{rel}: duplicate canonical authority {authority!r}; first owned by {previous}")
            else:
                authorities[authority] = rel
        else:
            errors.append(f"{rel}: relaylm_authority must be a non-empty string")

        for key, value in iter_relationship_values(metadata):
            clean = value.split("#", 1)[0].split("?", 1)[0].strip()
            if clean.startswith("/") or "\\" in clean:
                errors.append(f"{rel}: {key} target must be repository-relative: {value}")
                continue
            resolved = resolve_repository_path(root, path, value)
            if resolved is None:
                continue
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{rel}: {key} target escapes repository: {value}")
            else:
                if not resolved.exists():
                    errors.append(f"{rel}: {key} target does not exist: {value}")

    return errors


def is_sorted_unique(values: list[str]) -> bool:
    return values == sorted(set(values))


def validate_records(root: Path) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    schema_dir = root / "docs/contracts/schemas/documentation-governance-v1"
    record_dir = root / "records/documentation"
    required_schemas = {
        "current-machine-registry.schema.json": read_schema(root, "current-machine-registry.schema.json"),
        "retained-record-envelope.schema.json": read_schema(root, "retained-record-envelope.schema.json"),
        "retained-record-registry.schema.json": read_schema(root, "retained-record-registry.schema.json"),
        "retirement-manifest.schema.json": read_schema(root, "retirement-manifest.schema.json"),
        "transitional-asset-registry.schema.json": read_schema(root, "transitional-asset-registry.schema.json"),
    }
    special_paths = {
        record_dir / "current-records.json": "current-machine-registry.schema.json",
        record_dir / "retained-record-registry.json": "retained-record-registry.schema.json",
        record_dir / "retirement-manifest.json": "retirement-manifest.schema.json",
        record_dir / "transitional-assets.json": "transitional-asset-registry.schema.json",
    }
    special_values: dict[str, Any] = {}
    for path, schema_name in special_paths.items():
        if not path.exists():
            errors.append(f"{relative(path, root)}: required record missing")
            special_values[schema_name] = {}
            continue
        value = read_json(path)
        special_values[schema_name] = value
        for detail in schema_errors(required_schemas[schema_name], value):
            errors.append(f"{relative(path, root)}: {detail}")

    catalog = special_values.get("current-machine-registry.schema.json", {})
    registry = special_values.get("retained-record-registry.schema.json", {})
    manifest = special_values.get("retirement-manifest.schema.json", {})
    transitional = special_values.get("transitional-asset-registry.schema.json", {})

    classes = registry.get("record_classes", []) if isinstance(registry, dict) else []
    class_ids = [item.get("class_id") for item in classes if isinstance(item, dict)]
    if class_ids != EXPECTED_CLASSES:
        errors.append(
            f"records/documentation/retained-record-registry.json: class order/set must equal {EXPECTED_CLASSES}"
        )
    class_map = {item.get("class_id"): item for item in classes if isinstance(item, dict)}
    catalog_records = catalog.get("records", []) if isinstance(catalog, dict) else []
    catalog_paths = [item.get("path") for item in catalog_records if isinstance(item, dict)]
    if catalog_paths != sorted(set(catalog_paths)):
        errors.append("records/documentation/current-records.json: records must be sorted by unique path")
    catalog_map = {item.get("path"): item for item in catalog_records if isinstance(item, dict)}
    for item in catalog_records:
        if not isinstance(item, dict):
            continue
        record_path = item.get("path")
        append_repository_path_error(
            errors,
            f"records/documentation/current-records.json: {record_path} path",
            record_path,
            prefixes=("records",),
        )
        class_record = class_map.get(item.get("record_class"))
        if not isinstance(class_record, dict):
            errors.append(f"records/documentation/current-records.json: {record_path} has unknown class")
        elif item.get("media_type") not in class_record.get("media_types", []):
            errors.append(f"records/documentation/current-records.json: {record_path} media type is not allowed by its class")
        for key in ("current_consumers", "validator_paths", "authority_paths"):
            values = item.get(key)
            if isinstance(values, list) and not is_sorted_unique(values):
                errors.append(f"records/documentation/current-records.json: {record_path} {key} must be sorted and unique")
        schema_path = item.get("schema_path")
        if isinstance(schema_path, str):
            valid_schema_path = append_repository_path_error(
                errors,
                f"records/documentation/current-records.json: {record_path} schema_path",
                schema_path,
                prefixes=("docs/contracts/schemas",),
            )
            if valid_schema_path and not (root / schema_path).is_file():
                errors.append(f"records/documentation/current-records.json: missing schema: {schema_path}")
        for key, prefixes in (("validator_paths", ("scripts",)), ("authority_paths", ("docs",))):
            for target in item.get(key, []):
                if not isinstance(target, str):
                    continue
                valid_target = append_repository_path_error(
                    errors,
                    f"records/documentation/current-records.json: {record_path} {key}",
                    target,
                    prefixes=prefixes,
                )
                if valid_target and not (root / target).is_file():
                    errors.append(f"records/documentation/current-records.json: missing {key} target: {target}")
    for item in classes:
        if not isinstance(item, dict):
            continue
        schema_path = item.get("schema_path")
        if isinstance(schema_path, str):
            valid_schema_path = append_repository_path_error(
                errors,
                f"records/documentation/retained-record-registry.json: {item.get('class_id')} schema_path",
                schema_path,
                prefixes=("docs/contracts/schemas/documentation-governance-v1",),
            )
            if valid_schema_path:
                candidate = root / schema_path
                if not candidate.exists():
                    errors.append(f"records/documentation/retained-record-registry.json: missing schema {schema_path}")
                elif schema_dir.resolve() not in candidate.resolve().parents:
                    errors.append(f"records/documentation/retained-record-registry.json: schema outside governance root: {schema_path}")
        for key in ("media_types", "current_consumers"):
            values = item.get(key)
            if isinstance(values, list) and not is_sorted_unique(values):
                errors.append(f"records/documentation/retained-record-registry.json: {item.get('class_id')} {key} must be sorted and unique")

    entries = manifest.get("entries", []) if isinstance(manifest, dict) else []
    old_paths = [item.get("old_path") for item in entries if isinstance(item, dict)]
    if old_paths != sorted(set(old_paths)):
        errors.append("records/documentation/retirement-manifest.json: entries must be sorted by unique old_path")
    for item in entries:
        if isinstance(item, dict):
            old_path = item.get("old_path")
            append_repository_path_error(
                errors,
                f"records/documentation/retirement-manifest.json: {old_path} old_path",
                old_path,
                prefixes=("docs",),
            )
            replacements = item.get("replacement_paths")
            if isinstance(replacements, list) and not is_sorted_unique(replacements):
                errors.append(
                    f"records/documentation/retirement-manifest.json: {old_path} replacement_paths must be sorted and unique"
                )
            if isinstance(replacements, list):
                for replacement in replacements:
                    append_repository_path_error(
                        errors,
                        f"records/documentation/retirement-manifest.json: {old_path} replacement_path",
                        replacement,
                        prefixes=("docs", "records"),
                    )

    families = transitional.get("families", []) if isinstance(transitional, dict) else []
    family_ids = [item.get("family_id") for item in families if isinstance(item, dict)]
    if family_ids != sorted(set(family_ids)):
        errors.append("records/documentation/transitional-assets.json: families must be sorted by unique family_id")
    for item in families:
        if not isinstance(item, dict):
            continue
        for key in ("paths", "current_consumers", "replacement_validation"):
            values = item.get(key)
            if isinstance(values, list) and not is_sorted_unique(values):
                errors.append(f"records/documentation/transitional-assets.json: {item.get('family_id')} {key} must be sorted and unique")
        for transitional_path in item.get("paths", []):
            append_repository_path_error(
                errors,
                f"records/documentation/transitional-assets.json: {item.get('family_id')} path",
                transitional_path,
                prefixes=(".github", "docs", "records", "scripts", "tests"),
                allow_glob=True,
            )

    records_root = root / "records"
    actual_paths: set[str] = set()
    if records_root.exists():
        for path in sorted(item for item in records_root.rglob("*") if item.is_file()):
            rel = relative(path, root)
            actual_paths.add(rel)
            entry = catalog_map.get(rel)
            if not isinstance(entry, dict):
                errors.append(f"{rel}: unregistered record path; records/ is not a free-form archive")
                continue
            media = entry.get("media_type")
            expected = "application/json" if path.suffix == ".json" else "application/yaml" if path.suffix in {".yaml", ".yml"} else None
            if media != expected:
                errors.append(f"{rel}: media type {media!r} does not match file extension")
                continue
            if path in special_paths:
                continue
            try:
                value = read_json(path) if media == "application/json" else yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, yaml.YAMLError) as exc:
                errors.append(f"{rel}: cannot read valid {media}: {exc}")
                continue
            if not isinstance(value, dict):
                errors.append(f"{rel}: retained record must be a mapping/object")
                continue
            schema_path = entry.get("schema_path")
            if isinstance(schema_path, str):
                for detail in schema_errors(read_json(root / schema_path), value):
                    errors.append(f"{rel}: {detail}")
    for rel in sorted(set(catalog_map) - actual_paths):
        errors.append(f"records/documentation/current-records.json: cataloged record does not exist: {rel}")

    return errors, registry, manifest, transitional


def expand_registry_paths(root: Path, transitional: dict[str, Any]) -> tuple[set[str], list[str]]:
    exact: set[str] = set()
    errors: list[str] = []
    for family in transitional.get("families", []):
        if not isinstance(family, dict):
            continue
        for raw in family.get("paths", []):
            if not isinstance(raw, str):
                continue
            if repository_path_error(
                raw,
                prefixes=(".github", "docs", "records", "scripts", "tests"),
                allow_glob=True,
            ) is not None:
                continue
            if "*" in raw:
                matches = sorted(path for path in root.glob(raw) if path.is_file())
                if not matches:
                    errors.append(f"records/documentation/transitional-assets.json: pattern has no current match: {raw}")
                continue
            exact.add(raw)
            if not (root / raw).exists():
                errors.append(f"records/documentation/transitional-assets.json: transitional asset missing: {raw}")
    return exact, errors


def validate_transitional_assets(
    root: Path,
    transitional: dict[str, Any],
    new_paths: set[str] | None = None,
) -> list[str]:
    exact, errors = expand_registry_paths(root, transitional)
    new_paths = new_paths or set()
    for family in transitional.get("families", []):
        if not isinstance(family, dict) or family.get("growth_policy") != "closed":
            continue
        patterns = [item for item in family.get("paths", []) if isinstance(item, str)]
        for path in sorted(new_paths):
            if any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
                errors.append(
                    f"{path}: new path is forbidden by closed transitional family {family.get('family_id')}"
                )
    current_guards = {
        relative(path, root)
        for path in (root / "scripts").glob("*_handoff_cutover_guard.py")
        if path.is_file()
    }
    allowed_guards = {path for path in exact if path.endswith("_handoff_cutover_guard.py")}
    for path in sorted(current_guards - allowed_guards):
        errors.append(f"{path}: new bespoke handoff cutover guard is not permitted after D1")
    for path in sorted(allowed_guards - current_guards):
        errors.append(f"{path}: registered bespoke guard is absent; remove its registry entry in the owning cleanup PR")
    return errors


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def validate_git_recoverability(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = manifest.get("entries", []) if isinstance(manifest, dict) else []
    if entries and run_git(root, "rev-parse", "--git-dir").returncode != 0:
        return ["records/documentation/retirement-manifest.json: Git repository required for non-empty manifest"]
    for item in entries:
        if not isinstance(item, dict):
            continue
        old_path = str(item.get("old_path", ""))
        commit = str(item.get("last_live_commit", ""))
        expected_blob = str(item.get("old_blob_sha", ""))
        if repository_path_error(old_path, prefixes=("docs",)) is not None:
            continue
        ancestry = run_git(root, "merge-base", "--is-ancestor", commit, "HEAD")
        if ancestry.returncode != 0:
            errors.append(f"{old_path}: last_live_commit is not an ancestor of validator head")
        result = run_git(root, "rev-parse", f"{commit}:{old_path}")
        if result.returncode != 0:
            errors.append(f"{old_path}: cannot resolve last_live_commit path")
        elif result.stdout.strip() != expected_blob:
            errors.append(f"{old_path}: old_blob_sha does not match last_live_commit")
        if (root / old_path).exists():
            errors.append(f"{old_path}: retired path is still present at validator head")
        for replacement in item.get("replacement_paths", []):
            if repository_path_error(replacement, prefixes=("docs", "records")) is not None:
                continue
            if not (root / replacement).exists():
                errors.append(f"{old_path}: replacement path does not exist: {replacement}")
    return errors


def new_paths_since_base(root: Path, base_ref: str) -> set[str]:
    result = run_git(root, "diff", "--name-only", "--diff-filter=AR", f"{base_ref}...HEAD", "--")
    if result.returncode != 0:
        raise GovernanceError(f"cannot compare new paths against {base_ref}: {result.stderr.strip()}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def manifest_entries_at_ref(root: Path, base_ref: str) -> dict[str, dict[str, Any]]:
    exists = run_git(
        root,
        "cat-file",
        "-e",
        f"{base_ref}:records/documentation/retirement-manifest.json",
    )
    if exists.returncode != 0:
        return {}
    result = run_git(
        root,
        "show",
        f"{base_ref}:records/documentation/retirement-manifest.json",
    )
    if result.returncode != 0:
        raise GovernanceError(
            f"cannot read base retirement manifest from {base_ref}: {result.stderr.strip()}"
        )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GovernanceError(f"base retirement manifest is invalid JSON: {exc}") from exc
    entries = value.get("entries", []) if isinstance(value, dict) else []
    return {
        item["old_path"]: item
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("old_path"), str)
    }


def validate_manifest_change_attribution(
    root: Path,
    manifest: dict[str, Any],
    base_ref: str | None,
    pull_request_number: int | None,
) -> list[str]:
    if pull_request_number is None:
        return []
    if base_ref is None:
        return ["retirement manifest PR attribution requires --base-ref"]
    errors: list[str] = []
    base_entries = manifest_entries_at_ref(root, base_ref)
    current_entries = {
        item["old_path"]: item
        for item in manifest.get("entries", [])
        if isinstance(item, dict) and isinstance(item.get("old_path"), str)
    }
    for old_path in sorted(set(base_entries) - set(current_entries)):
        errors.append(f"{old_path}: retirement manifest entries must not be removed")
    for old_path, item in sorted(current_entries.items()):
        previous = base_entries.get(old_path)
        removed_by_pr = item.get("removed_by_pr")
        if previous is None:
            if removed_by_pr != pull_request_number:
                errors.append(
                    f"{old_path}: new retirement entry removed_by_pr must equal PR #{pull_request_number}"
                )
        elif removed_by_pr != previous.get("removed_by_pr"):
            errors.append(f"{old_path}: existing retirement entry removed_by_pr is immutable")
    return errors


def validate_repository(
    root: Path = ROOT,
    base_ref: str | None = None,
    pull_request_number: int | None = None,
) -> list[str]:
    new_paths = new_paths_since_base(root, base_ref) if base_ref else set()
    required = {
        path
        for path in new_paths
        if path.endswith(".md") and allowed_doc_types(PurePosixPath(path))
    }
    errors = validate_active_documents(root, required)
    record_errors, _registry, manifest, transitional = validate_records(root)
    errors.extend(record_errors)
    errors.extend(validate_transitional_assets(root, transitional, new_paths))
    errors.extend(validate_git_recoverability(root, manifest))
    errors.extend(
        validate_manifest_change_attribution(
            root,
            manifest,
            base_ref,
            pull_request_number,
        )
    )
    return sorted(set(errors))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect(label: str, condition: bool, failures: list[str]) -> None:
    if condition:
        print(f"PASS: {label}")
    else:
        print(f"FAIL: {label}")
        failures.append(label)


def canonical_doc(authority: str) -> str:
    return f"""---
relaylm_doc_type: contract
relaylm_authority: {authority}
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - governance changes
relaylm_not_authoritative_for:
  - runtime behavior
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - documentation maintainers
relaylm_authority_level: exact_contract
---
# Contract
"""


def self_test_transitional_family(paths: list[str]) -> dict[str, Any]:
    """A synthetic, schema-valid transitional family for self-test use only.

    The real registry is empty. Family-level validation must keep working for
    any family a future governance change registers, so the self-tests build
    one explicitly instead of depending on a registered production family.
    """
    return {
        "family_id": "self-test-transitional-family",
        "paths": sorted(paths),
        "owner": "documentation",
        "protected_boundary": "Self-test only: proves family validation still applies when a family exists.",
        "current_consumers": ["self-test"],
        "removal_gate": "Self-test only; never registered as a production transitional family.",
        "replacement_validation": ["active_document_authority"],
        "growth_policy": "closed",
    }


def self_test_transitional_registry(paths: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "relaylm.documentation.transitional-asset-registry.v1",
        "families": [self_test_transitional_family(paths)],
    }


def build_self_test_root() -> Path:
    temp = Path(tempfile.mkdtemp(prefix="relaylm-doc-governance-"))
    shutil.copytree(SCHEMA_ROOT, temp / "docs/contracts/schemas/documentation-governance-v1")
    shutil.copytree(RECORD_ROOT, temp / "records/documentation")
    write_json(
        temp / "records/documentation/retirement-manifest.json",
        {
            "schema_version": "relaylm.documentation.retirement-manifest.v1",
            "entries": [],
        },
    )
    (temp / "docs/contracts").mkdir(parents=True, exist_ok=True)
    (temp / "docs/contracts/example.md").write_text(canonical_doc("self_test_authority"), encoding="utf-8")
    catalog = read_json(temp / "records/documentation/current-records.json")
    for item in catalog["records"]:
        record = temp / item["path"]
        if not record.exists():
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("{}\n", encoding="utf-8")
        for target in item["validator_paths"]:
            target_path = temp / target
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.touch(exist_ok=True)
        for target in item["authority_paths"]:
            target_path = temp / target
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if not target_path.exists():
                target_path.write_text("# Self-test authority\n", encoding="utf-8")
    transitional = read_json(temp / "records/documentation/transitional-assets.json")
    for family in transitional["families"]:
        for raw in family["paths"]:
            if "*" in raw:
                target = temp / raw.replace("*", "self-test")
            else:
                target = temp / raw
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
    return temp


def self_test() -> int:
    failures: list[str] = []
    root = build_self_test_root()
    try:
        errors = validate_repository(root)
        expect("valid canonical document and governance records are accepted", not errors, failures)

        duplicate = root / "docs/contracts/duplicate.md"
        duplicate.write_text(canonical_doc("self_test_authority"), encoding="utf-8")
        errors = validate_repository(root)
        expect("duplicate canonical authority is rejected", any("duplicate canonical authority" in item for item in errors), failures)
        duplicate.unlink()

        incomplete = root / "docs/contracts/incomplete.md"
        incomplete.write_text(canonical_doc("incomplete_authority").replace("relaylm_authority_level: exact_contract\n", ""), encoding="utf-8")
        errors = validate_repository(root)
        expect("partial canonical granularity metadata is rejected", any("missing relaylm_authority_level" in item for item in errors), failures)
        incomplete.unlink()

        unopted = root / "docs/architecture/lc1b_subjective_mem_forget.md"
        unopted.parent.mkdir(parents=True, exist_ok=True)
        unopted.write_text("---\nrelaylm_doc_type: subsystem_architecture\n---\n# Legacy slice\n", encoding="utf-8")
        errors = validate_active_documents(root, {"docs/architecture/lc1b_subjective_mem_forget.md"})
        expect("new permanent document cannot bypass canonical graph metadata", any("missing relaylm_lifecycle" in item for item in errors), failures)
        expect("new permanent filename rejects slice identifiers", any("milestone or slice identifier" in item for item in errors), failures)
        expect("new permanent filename requires kebab-case", any("lowercase kebab-case" in item for item in errors), failures)
        unopted.unlink()

        evidence_readme = root / "docs/evidence/README.md"
        evidence_readme.parent.mkdir(parents=True, exist_ok=True)
        evidence_readme.write_text(canonical_doc("evidence_router").replace("relaylm_doc_type: contract", "relaylm_doc_type: documentation_index"), encoding="utf-8")
        errors = validate_active_documents(root, {"docs/evidence/README.md"})
        expect("README outside permanent active collections is rejected", any("outside the permanent active locations" in item for item in errors), failures)
        evidence_readme.unlink()

        escaped = root / "docs/contracts/escaped.md"
        escaped.write_text(
            canonical_doc("escaped_authority").replace(
                "relaylm_authority_level: exact_contract\n",
                "relaylm_authority_level: exact_contract\nrelaylm_related_authority: ../../../outside.md\n",
            ),
            encoding="utf-8",
        )
        errors = validate_active_documents(root)
        expect("relationship metadata cannot escape the repository", any("target escapes repository" in item for item in errors), failures)
        escaped.unlink()

        absolute = root / "docs/contracts/absolute.md"
        absolute.write_text(
            canonical_doc("absolute_authority").replace(
                "relaylm_authority_level: exact_contract\n",
                "relaylm_authority_level: exact_contract\nrelaylm_related_authority: /tmp/outside.md\n",
            ),
            encoding="utf-8",
        )
        errors = validate_active_documents(root)
        expect(
            "absolute relationship metadata is rejected",
            any("target must be repository-relative" in item for item in errors),
            failures,
        )
        absolute.unlink()

        i18n = root / "docs/architecture/i18n-policy.md"
        i18n.parent.mkdir(parents=True, exist_ok=True)
        i18n.write_text(
            canonical_doc("i18n_policy").replace("relaylm_doc_type: contract", "relaylm_doc_type: concept_policy"),
            encoding="utf-8",
        )
        errors = validate_active_documents(root)
        expect("ordinary i18n responsibility name is not treated as a milestone", not any("i18n-policy.md: permanent active filename must not use a milestone" in item for item in errors), failures)
        i18n.unlink()

        slice_named = root / "docs/architecture/i7ab-memory.md"
        slice_named.write_text(
            canonical_doc("slice_named_authority").replace(
                "relaylm_doc_type: contract",
                "relaylm_doc_type: concept_policy",
            ),
            encoding="utf-8",
        )
        errors = validate_active_documents(root)
        expect(
            "multi-letter milestone prefixes are rejected",
            any("i7ab-memory.md: permanent active filename must not use a milestone" in item for item in errors),
            failures,
        )
        slice_named.unlink()

        empty_registry = read_json(root / "records/documentation/transitional-assets.json")
        expect(
            "the production transitional registry is present and holds zero families",
            isinstance(empty_registry, dict) and empty_registry.get("families") == [],
            failures,
        )
        expect(
            "an empty transitional registry is accepted",
            not validate_transitional_assets(root, empty_registry),
            failures,
        )

        closed_addition_errors = validate_transitional_assets(
            root,
            self_test_transitional_registry(["docs/evidence/implementation/*_completion_report.md"]),
            {"docs/evidence/implementation/added_completion_report.md"},
        )
        expect("closed transitional families reject added or renamed paths", any("new path is forbidden by closed transitional family" in item for item in closed_addition_errors), failures)

        # A registered family whose protected path no longer exists must fail:
        # this is how removal validation proves removed family paths and
        # consumers were actually repaired rather than silently abandoned.
        stale_family_errors = validate_transitional_assets(
            root,
            self_test_transitional_registry(["scripts/relaylm_self_test_removed_asset.py"]),
        )
        expect(
            "a registered family whose protected path was removed is rejected",
            any("transitional asset missing" in item for item in stale_family_errors),
            failures,
        )
        stale_pattern_errors = validate_transitional_assets(
            root,
            self_test_transitional_registry(["scripts/relaylm_self_test_removed_asset_*.py"]),
        )
        expect(
            "a registered family whose protected pattern matches nothing is rejected",
            any("pattern has no current match" in item for item in stale_pattern_errors),
            failures,
        )

        free_form = root / "records/documentation/history.md"
        free_form.write_text("# archive\n", encoding="utf-8")
        errors = validate_repository(root)
        expect("free-form records archive content is rejected", any("unregistered record path" in item for item in errors), failures)
        free_form.unlink()

        unregistered_yaml = root / "records/repository/unregistered.yaml"
        unregistered_yaml.parent.mkdir(parents=True, exist_ok=True)
        unregistered_yaml.write_text("value: 1\n", encoding="utf-8")
        errors = validate_repository(root)
        expect("unregistered YAML record is rejected", any("unregistered record path" in item for item in errors), failures)
        unregistered_yaml.unlink()

        catalog_path = root / "records/documentation/current-records.json"
        catalog = read_json(catalog_path)
        lane_r = next(item for item in catalog["records"] if item["path"] == "records/repository/asset_classification_v1.yaml")
        lane_r["media_type"] = "application/json"
        write_json(catalog_path, catalog)
        errors = validate_repository(root)
        expect("record media type must match its extension", any("does not match file extension" in item for item in errors), failures)
        shutil.copy2(CATALOG_PATH, catalog_path)

        catalog = read_json(catalog_path)
        lane_r = next(item for item in catalog["records"] if item["path"] == "records/repository/asset_classification_v1.yaml")
        lane_r["validator_paths"] = ["scripts/../outside.py"]
        write_json(catalog_path, catalog)
        errors = validate_repository(root)
        expect(
            "catalog paths cannot traverse outside their canonical prefix",
            any("must not contain dot path segments" in item for item in errors),
            failures,
        )
        shutil.copy2(CATALOG_PATH, catalog_path)

        transitional_path = root / "records/documentation/transitional-assets.json"
        valid_family_asset = root / "docs/contracts/self-test-transitional-asset.md"
        valid_family_asset.parent.mkdir(parents=True, exist_ok=True)
        valid_family_asset.write_text("# self-test transitional asset\n", encoding="utf-8")
        write_json(
            transitional_path,
            self_test_transitional_registry(["docs/contracts/self-test-transitional-asset.md"]),
        )
        errors = validate_repository(root)
        expect(
            "one valid registered transitional family is still accepted",
            not errors,
            failures,
        )

        malformed = self_test_transitional_registry(
            ["docs/../outside.md", "docs/contracts/self-test-transitional-asset.md"]
        )
        write_json(transitional_path, malformed)
        errors = validate_repository(root)
        expect(
            "transitional paths cannot contain traversal segments",
            any("must not contain dot path segments" in item for item in errors),
            failures,
        )

        unsorted = self_test_transitional_registry(["docs/contracts/self-test-transitional-asset.md"])
        unsorted["families"][0]["current_consumers"] = ["second", "first"]
        write_json(transitional_path, unsorted)
        errors = validate_repository(root)
        expect(
            "a malformed family with unsorted current consumers is rejected",
            any("current_consumers must be sorted and unique" in item for item in errors),
            failures,
        )

        open_growth = self_test_transitional_registry(["docs/contracts/self-test-transitional-asset.md"])
        open_growth["families"][0]["growth_policy"] = "open"
        write_json(transitional_path, open_growth)
        errors = validate_repository(root)
        expect(
            "a family that is not closed-growth is rejected by the registry schema",
            any("growth_policy" in item for item in errors),
            failures,
        )

        valid_family_asset.unlink()
        shutil.copy2(TRANSITIONAL_PATH, transitional_path)
        errors = validate_repository(root)
        expect(
            "the empty production registry is accepted end to end",
            not errors,
            failures,
        )

        registry_path = root / "records/documentation/retained-record-registry.json"
        registry = read_json(registry_path)
        registry["record_classes"] = list(reversed(registry["record_classes"]))
        write_json(registry_path, registry)
        errors = validate_repository(root)
        expect("retained-record class order drift is rejected", any("class order/set" in item for item in errors), failures)
        shutil.copy2(REGISTRY_PATH, registry_path)

        new_guard = root / "scripts/relaylm_new_handoff_cutover_guard.py"
        new_guard.parent.mkdir(parents=True, exist_ok=True)
        new_guard.touch()
        errors = validate_repository(root)
        expect("new bespoke cutover guard is rejected", any("new bespoke handoff cutover guard" in item for item in errors), failures)
        new_guard.unlink()

        manifest_path = root / "records/documentation/retirement-manifest.json"
        manifest = read_json(manifest_path)
        manifest["entries"] = [{
            "old_path": "docs/old.md",
            "last_live_commit": "0" * 40,
            "old_blob_sha": "0" * 40,
            "removed_by_pr": 999,
            "replacement_paths": [],
            "disposition": "replaced",
            "retention_reason": "self test",
        }]
        write_json(manifest_path, manifest)
        errors = validate_repository(root)
        expect("replacement disposition requires a replacement path", any("replacement_paths" in item for item in errors), failures)

        write_json(manifest_path, {"schema_version": "relaylm.documentation.retirement-manifest.v1", "entries": []})
        run_git(root, "init")
        run_git(root, "config", "user.email", "self-test@example.invalid")
        run_git(root, "config", "user.name", "RelayLM self-test")
        old = root / "docs/old.md"
        old.write_text("old\n", encoding="utf-8")
        run_git(root, "add", "docs/old.md", "records/documentation/retirement-manifest.json")
        run_git(root, "commit", "-m", "self-test old")
        commit = run_git(root, "rev-parse", "HEAD").stdout.strip()
        blob = run_git(root, "rev-parse", f"{commit}:docs/old.md").stdout.strip()
        old.unlink()
        replacement = root / "docs/contracts/replacement.md"
        replacement.write_text(canonical_doc("replacement_authority"), encoding="utf-8")
        good_manifest = {
            "schema_version": "relaylm.documentation.retirement-manifest.v1",
            "entries": [{
                "old_path": "docs/old.md",
                "last_live_commit": commit,
                "old_blob_sha": blob,
                "removed_by_pr": 999,
                "replacement_paths": ["docs/contracts/replacement.md"],
                "disposition": "replaced",
                "retention_reason": "self-test replacement",
            }],
        }
        write_json(manifest_path, good_manifest)
        errors = validate_repository(
            root,
            base_ref=commit,
            pull_request_number=999,
        )
        expect("exact commit/blob Git recoverability and PR attribution are accepted", not errors, failures)

        good_manifest["entries"][0]["removed_by_pr"] = 998
        write_json(manifest_path, good_manifest)
        errors = validate_repository(
            root,
            base_ref=commit,
            pull_request_number=999,
        )
        expect(
            "new retirement entry must attribute the active pull request",
            any("removed_by_pr must equal PR #999" in item for item in errors),
            failures,
        )
        good_manifest["entries"][0]["removed_by_pr"] = 999

        good_manifest["entries"][0]["replacement_paths"] = ["docs/../outside.md"]
        write_json(manifest_path, good_manifest)
        errors = validate_repository(root)
        expect(
            "retirement replacements cannot traverse outside canonical paths",
            any("must not contain dot path segments" in item for item in errors),
            failures,
        )
        good_manifest["entries"][0]["replacement_paths"] = ["docs/contracts/replacement.md"]

        unrelated_tree = run_git(root, "write-tree").stdout.strip()
        unrelated_commit = run_git(root, "commit-tree", unrelated_tree, "-m", "self-test unrelated").stdout.strip()
        good_manifest["entries"][0]["last_live_commit"] = unrelated_commit
        write_json(manifest_path, good_manifest)
        errors = validate_repository(root)
        expect(
            "last_live_commit must be an ancestor of validator head",
            any("not an ancestor of validator head" in item for item in errors),
            failures,
        )
        good_manifest["entries"][0]["last_live_commit"] = commit

        good_manifest["entries"][0]["old_blob_sha"] = "f" * 40
        write_json(manifest_path, good_manifest)
        errors = validate_repository(root)
        expect("incorrect old blob identity is rejected", any("old_blob_sha does not match" in item for item in errors), failures)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print(f"SELF-TEST FAILED: {len(failures)} assertion(s)")
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--base-ref", help="Require newly added Markdown since this Git ref to use canonical graph metadata")
    parser.add_argument(
        "--pull-request-number",
        type=int,
        help="Require new retirement-manifest entries to attribute this pull request",
    )
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        errors = validate_repository(
            ROOT,
            args.base_ref,
            args.pull_request_number,
        )
    except GovernanceError as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"FAIL: documentation governance validation found {len(errors)} issue(s)")
        return 1
    print("PASS: documentation governance contract, records, transition registry, and Git recoverability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
