"""Validate and render the Lane R repository asset classification registry.

The human-reviewed records remain embedded in
``docs/reference/repository-asset-classification.md``. The YAML registry is a
machine-readable mirror. This tool verifies that the mirror has not drifted,
validates lifecycle/caller/path requirements, and renders navigation evidence.
It never infers retirement from reachability and never edits repository files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml
from yaml.resolver import BaseResolver


DOC_PATH = Path("docs/reference/repository-asset-classification.md")
REGISTRY_PATH = Path("records/repository/asset_classification_v1.yaml")

RESPONSIBILITIES = {
    "ordinary_test",
    "process_smoke",
    "operator_cli",
    "offline_tooling",
    "generator",
    "migration_or_maintenance",
    "benchmark",
    "repository_validation",
    "planned_inactive",
    "unclassified",
}
LIFECYCLES = {"active", "transitional", "retired"}
CONFIDENCE_VALUES = {"confirmed", "provisional", "unclassified"}
INVOCATION_ROOTS = {
    "console_script",
    "dynamic_import",
    "fastapi_route",
    "frontend_route",
    "github_actions_step",
    "npm_script",
    "operator_cli",
    "pytest_root",
    "python_dash_m",
    "registry",
    "smoke_only_root",
    "static_or_package_data",
    "subprocess_child",
}
REQUIRED_RECORD_FIELDS = {
    "asset_id",
    "paths",
    "responsibility",
    "lifecycle",
    "owner",
    "protected_boundary",
    "current_callers",
    "invocation_roots",
    "evidence",
    "removal_gate",
    "replacement_validation",
    "confidence",
}
ASSET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GLOB_CHARS = set("*?[]{}")
OPERATOR_ROOTS = {"console_script", "operator_cli"}
R6_PRIMARY_ASSET_PREFIX = "r6.primary."
R6_PRIMARY_RECALL_E1_PATTERN = "relaylm_e1r5_primary_mem_recall_*_smoke.py"
R6_DISPOSITIONS = {
    "retired_after_cutover",
    "migration_or_characterization_dependency",
    "rollback_dependency",
    "operator_or_recovery_dependency",
    "retained_current_component",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ValueError(f"unhashable YAML mapping key: {key!r}") from exc
        if duplicate:
            raise ValueError(f"duplicate YAML mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml_text(text: str) -> dict[str, Any]:
    payload = yaml.load(text, Loader=UniqueKeyLoader)
    if not isinstance(payload, dict):
        raise ValueError("YAML top level must be a mapping")
    return payload


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return load_yaml_text(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def extract_document_registry(document_text: str) -> dict[str, Any]:
    marker = "## Bounded classification registry"
    marker_index = document_text.find(marker)
    if marker_index < 0:
        raise ValueError(f"missing section: {marker}")

    fence_start = document_text.find("```yaml", marker_index)
    if fence_start < 0:
        raise ValueError("missing YAML fence after bounded registry heading")
    content_start = fence_start + len("```yaml")
    fence_end = document_text.find("```", content_start)
    if fence_end < 0:
        raise ValueError("unterminated YAML fence in classification document")

    try:
        return load_yaml_text(document_text[content_start:fence_end])
    except ValueError as exc:
        raise ValueError(f"classification document YAML: {exc}") from exc


def mirrored_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "classification_version": payload.get("classification_version"),
        "source_commit": payload.get("source_commit"),
        "records": payload.get("records"),
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, allow_empty: bool = False) -> bool:
    if not isinstance(value, list):
        return False
    if not allow_empty and not value:
        return False
    return all(_nonempty_string(item) for item in value)


def validate_registry(payload: dict[str, Any], *, root: Path) -> list[str]:
    errors: list[str] = []

    if payload.get("registry_version") != 1:
        errors.append("registry_version must be 1")
    if payload.get("classification_version") != 1:
        errors.append("classification_version must be 1")

    source_document = payload.get("generated_from")
    if source_document != DOC_PATH.as_posix():
        errors.append(f"generated_from must be {DOC_PATH.as_posix()}")

    source_commit = payload.get("source_commit")
    if not isinstance(source_commit, str) or not SHA_RE.fullmatch(source_commit):
        errors.append("source_commit must be a lowercase 40-character git SHA")

    records = payload.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records must be a non-empty list")
        return errors

    asset_ids: set[str] = set()
    record_by_id: dict[str, dict[str, Any]] = {}
    r6_path_owners: dict[str, str] = {}

    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be a mapping")
            continue

        missing = sorted(REQUIRED_RECORD_FIELDS - set(record))
        if missing:
            errors.append(f"{prefix} missing required fields: {', '.join(missing)}")

        asset_id = record.get("asset_id")
        if not _nonempty_string(asset_id) or not ASSET_ID_RE.fullmatch(asset_id):
            errors.append(f"{prefix}.asset_id is invalid")
            record_id = prefix
        else:
            record_id = asset_id
            if asset_id in asset_ids:
                errors.append(f"duplicate asset_id: {asset_id}")
            asset_ids.add(asset_id)
            record_by_id[asset_id] = record

        is_r6_primary = isinstance(asset_id, str) and asset_id.startswith(
            R6_PRIMARY_ASSET_PREFIX
        )
        r6_disposition = record.get("r6_disposition")
        if is_r6_primary and r6_disposition not in R6_DISPOSITIONS:
            errors.append(
                f"{record_id}.r6_disposition must be exactly one recognized R6 Primary disposition"
            )
        elif not is_r6_primary and r6_disposition is not None:
            errors.append(f"{record_id}.r6_disposition is only valid for R6 Primary assets")

        paths = record.get("paths")
        if not _string_list(paths):
            errors.append(f"{record_id}.paths must be a non-empty string list")
        else:
            for path_text in paths:
                if any(character in path_text for character in GLOB_CHARS):
                    errors.append(f"{record_id}.paths contains an unexpanded glob: {path_text}")
                    continue
                candidate = Path(path_text)
                if candidate.is_absolute() or ".." in candidate.parts:
                    errors.append(f"{record_id}.paths must stay repository-relative: {path_text}")
                elif not (root / candidate).exists():
                    errors.append(f"{record_id}.paths does not exist: {path_text}")
                elif is_r6_primary:
                    prior_owner = r6_path_owners.get(path_text)
                    if prior_owner is not None:
                        errors.append(
                            f"R6 Primary path has multiple classification owners: "
                            f"{path_text} ({prior_owner}, {record_id})"
                        )
                    else:
                        r6_path_owners[path_text] = record_id

        responsibility = record.get("responsibility")
        if responsibility not in RESPONSIBILITIES:
            errors.append(f"{record_id}.responsibility is unknown: {responsibility!r}")

        lifecycle = record.get("lifecycle")
        if lifecycle not in LIFECYCLES:
            errors.append(f"{record_id}.lifecycle is unknown: {lifecycle!r}")

        confidence = record.get("confidence")
        if confidence not in CONFIDENCE_VALUES:
            errors.append(f"{record_id}.confidence is unknown: {confidence!r}")

        if not _nonempty_string(record.get("owner")):
            errors.append(f"{record_id}.owner must be non-empty")

        callers = record.get("current_callers")
        roots = record.get("invocation_roots")
        evidence = record.get("evidence")
        if not _string_list(evidence):
            errors.append(f"{record_id}.evidence must be a non-empty string list")
        if not _string_list(roots, allow_empty=True):
            errors.append(f"{record_id}.invocation_roots must be a string list")
        elif any(root_kind not in INVOCATION_ROOTS for root_kind in roots):
            unknown = sorted({root_kind for root_kind in roots if root_kind not in INVOCATION_ROOTS})
            errors.append(f"{record_id}.invocation_roots contains unknown values: {', '.join(unknown)}")
        elif lifecycle != "retired" and not roots and not _nonempty_string(record.get("invocation_root_reason")):
            errors.append(f"{record_id} has no invocation roots and no invocation_root_reason")

        if lifecycle in {"active", "transitional"}:
            if not _nonempty_string(record.get("protected_boundary")):
                errors.append(f"{record_id}.protected_boundary must be non-empty for {lifecycle}")
            if not _string_list(callers):
                errors.append(f"{record_id}.current_callers must be non-empty for {lifecycle}")
        elif lifecycle == "retired":
            if callers not in ([], None):
                errors.append(f"{record_id}.current_callers must be empty for retired assets")
            if record.get("protected_boundary") not in (None, "none"):
                errors.append(f"{record_id}.protected_boundary must be null or 'none' for retired assets")
            if roots not in ([], None):
                errors.append(f"{record_id}.invocation_roots must be empty for retired assets")

        removal_gate = record.get("removal_gate")
        replacement_validation = record.get("replacement_validation")
        if lifecycle == "transitional":
            if not _nonempty_string(removal_gate):
                errors.append(f"{record_id}.removal_gate must be non-empty for transitional assets")
            if not _nonempty_string(replacement_validation):
                errors.append(f"{record_id}.replacement_validation must be non-empty for transitional assets")
        elif removal_gate is not None or replacement_validation is not None:
            errors.append(f"{record_id} may define removal fields only when transitional")

        entrypoint = record.get("entrypoint")
        if entrypoint is not None and not _nonempty_string(entrypoint):
            errors.append(f"{record_id}.entrypoint must be a non-empty string when present")

    canonical_entries = payload.get("canonical_entrypoints")
    canonical_claims_by_asset: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(canonical_entries, list) or not canonical_entries:
        errors.append("canonical_entrypoints must be a non-empty list")
    else:
        groups: set[str] = set()
        commands: set[str] = set()
        claimed_assets: set[str] = set()
        for index, entry in enumerate(canonical_entries):
            prefix = f"canonical_entrypoints[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            group = entry.get("group")
            command = entry.get("command")
            asset_id = entry.get("asset_id")
            if not _nonempty_string(group) or not ASSET_ID_RE.fullmatch(group):
                errors.append(f"{prefix}.group is invalid")
            elif group in groups:
                errors.append(f"competing canonical entrypoint group: {group}")
            else:
                groups.add(group)
            if not _nonempty_string(command) or "\n" in command or "\r" in command:
                errors.append(f"{prefix}.command must be one non-empty line")
            elif command in commands:
                errors.append(f"duplicate canonical entrypoint command: {command}")
            else:
                commands.add(command)
            if not _nonempty_string(asset_id) or asset_id not in record_by_id:
                errors.append(f"{prefix}.asset_id does not reference a classified asset: {asset_id!r}")
                continue
            canonical_claims_by_asset.setdefault(asset_id, []).append(entry)
            if asset_id in claimed_assets:
                errors.append(f"asset has multiple canonical entrypoint claims: {asset_id}")
            claimed_assets.add(asset_id)
            record = record_by_id[asset_id]
            if record.get("lifecycle") != "active":
                errors.append(f"canonical entrypoint asset must be active: {asset_id}")
            record_roots = set(record.get("invocation_roots") or [])
            if not (record_roots & OPERATOR_ROOTS):
                errors.append(f"canonical entrypoint asset lacks an operator root: {asset_id}")

        for asset_id, record in record_by_id.items():
            record_roots = set(record.get("invocation_roots") or [])
            claims = canonical_claims_by_asset.get(asset_id, [])
            if record.get("lifecycle") == "active" and record_roots & OPERATOR_ROOTS and len(claims) != 1:
                errors.append(f"active operator-root asset must have exactly one canonical entrypoint claim: {asset_id}")

            entrypoint = record.get("entrypoint")
            if not _nonempty_string(entrypoint):
                continue
            command = entrypoint.split("=", 1)[0].strip()
            matches = [entry for entry in claims if entry.get("command") == command]
            if len(matches) != 1:
                errors.append(f"{asset_id}.entrypoint is not represented exactly once in canonical_entrypoints")

    recall_e1_root = root / "scripts"
    if recall_e1_root.exists():
        expected_recall_e1_paths = {
            path.relative_to(root).as_posix()
            for path in recall_e1_root.glob(R6_PRIMARY_RECALL_E1_PATTERN)
        }
        missing_recall_e1_paths = sorted(expected_recall_e1_paths - set(r6_path_owners))
        for path in missing_recall_e1_paths:
            errors.append(f"R6 Primary recall E1 asset is unclassified: {path}")

    return errors


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_markdown(payload: dict[str, Any]) -> str:
    records = payload["records"]
    active = sum(record["lifecycle"] == "active" for record in records)
    transitional = sum(record["lifecycle"] == "transitional" for record in records)
    retired = sum(record["lifecycle"] == "retired" for record in records)
    lines = [
        "# Repository Asset Classification Registry",
        "",
        f"Source: `{payload['generated_from']}` at `{payload['source_commit']}`",
        "",
        f"Records: {len(records)} (active {active}, transitional {transitional}, retired {retired})",
        "",
        "| Asset | Responsibility | Lifecycle | Owner | Paths |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        paths = "<br>".join(f"`{path}`" for path in record["paths"])
        lines.append(
            f"| `{record['asset_id']}` | `{record['responsibility']}` | "
            f"`{record['lifecycle']}` | `{record['owner']}` | {paths} |"
        )
    lines.extend(
        [
            "",
            "> Generated navigation and review evidence only. This output does not authorize retirement, deletion, movement, rename, or behavior change.",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and render the repository asset classification registry."
    )
    parser.add_argument("--check", action="store_true", help="Validate schema, drift, paths, gates, and entrypoint claims.")
    parser.add_argument("--render-json", type=Path, default=None, help="Write deterministic JSON navigation evidence.")
    parser.add_argument("--render-markdown", type=Path, default=None, help="Write deterministic Markdown navigation evidence.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.check or args.render_json or args.render_markdown):
        raise SystemExit("at least one of --check, --render-json, or --render-markdown is required")

    root = repository_root()
    try:
        registry = load_yaml(root / REGISTRY_PATH)
        document = extract_document_registry((root / DOC_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_registry(registry, root=root)
    if mirrored_payload(registry) != mirrored_payload(document):
        errors.append(
            f"registry records drift from {DOC_PATH.as_posix()}; regenerate the mirror from the reviewed document"
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.check:
        counts = {
            lifecycle: sum(record["lifecycle"] == lifecycle for record in registry["records"])
            for lifecycle in sorted(LIFECYCLES)
        }
        print(
            "PASS: repository asset classification registry is valid and synchronized "
            f"({len(registry['records'])} records; "
            f"active={counts['active']}, transitional={counts['transitional']}, retired={counts['retired']})."
        )
    if args.render_json is not None:
        write_output(args.render_json, render_json(registry))
    if args.render_markdown is not None:
        write_output(args.render_markdown, render_markdown(registry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
