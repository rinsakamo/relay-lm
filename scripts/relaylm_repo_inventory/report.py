"""Deterministic JSON and Markdown rendering for inventory reports."""
from __future__ import annotations

import json
from pathlib import Path

from . import invocations as invocation_scan
from . import repo, subprocess_aliases, yaml_config_locations
from .invocation_hardening import harden_inventory_dicts

INCLUSION_RULES = (
    "Storage scan covers *.py, *.ts, *.tsx, *.mjs, *.js under relaylm/, scripts/, and apps/.",
    "Storage records require a code-bound artifact path declaration or observed storage/I/O/locking/durability API; vocabulary and displayed path labels are excluded.",
    "Invocation scan covers relaylm/, scripts/, tests/, apps/*/package.json, apps/*/src, "
    "pyproject.toml, and .github/workflows/*.yml.",
    "Config scan covers pyproject.toml, apps/*/package.json, config.example.yaml, "
    "relaylm/, scripts/, tests/, and .github/workflows/*.yml.",
    "Directories excluded from all scans: .git, __pycache__, node_modules, .pytest_cache, "
    ".mypy_cache, .ruff_cache, dist, build, generated, .venv, venv, *.egg-info.",
    "Detection is static and non-executing. Python route/import/subprocess discovery uses AST analysis; "
    "other surfaces use bounded text, JSON, and YAML parsing. Dynamic control flow is not executed.",
)

LIMITATIONS = (
    "This tool performs no removal, migration, or dead-code determination. "
    "classification_state on every storage record is always \"unclassified\".",
    "Every field influenced by pattern-matching or naming-convention inference is listed "
    "in that record's heuristic_fields array; treat those values as leads, not facts.",
    "Storage vocabulary, displayed file names, and in-memory json.dumps/json.loads conversion "
    "without a code-bound path or persistent I/O anchor are intentionally omitted. "
    "This improves precision but can miss storage hidden behind project-specific wrappers.",
    "reachable_from_fastapi_import_graph describes the core relaylm.app import graph only. "
    "Routes reachable through relaylm.soul_lab_app are called out separately in notes. "
    "Absence from either graph is NOT evidence that a module is dead.",
    "invocation_roots on storage records is a best-effort textual cross-reference "
    "(substring match of the storage module's filename stem inside a candidate root's "
    "source or normalized command), not a resolved call graph. It can both over- and under-match.",
    "Subprocess analysis enumerates literal commands, direct literal loop iterables, and "
    "statically declared string sequences where safe. Dynamically assembled targets remain "
    "explicit unresolved subprocess roots.",
    "Dynamic-import records come only from Python AST call nodes. Comments and string literals "
    "are excluded; dynamically assembled target names remain unresolved.",
    "Registry entries (root_kind=\"registry\") point at files that dynamically resolve "
    "further commands; this tool does not expand or evaluate that dynamic content.",
    "This report is generated output for human review. It is not documentation authority "
    "and must not be committed as or treated as a substitute for docs/, ADRs, migration "
    "receipts, or PROJECT_STATUS.",
)

_SHARED_ENTRY_ROOT_KINDS = frozenset(
    {"npm_script", "github_actions_step", "frontend_route"}
)


def _remove_replaced_unresolved_children(
    invocations: list[dict] | None,
) -> list[dict] | None:
    if invocations is None:
        return None
    resolved_locations = {
        (record.get("source_path"), record.get("source_line"))
        for record in invocations
        if record.get("root_kind") == "subprocess_child"
        and record.get("command_or_symbol")
        != "unresolved subprocess invocation"
        and any(
            "direct literal tuple/list" in str(note)
            for note in record.get("notes", [])
        )
    }
    return [
        record
        for record in invocations
        if not (
            record.get("root_kind") == "subprocess_child"
            and record.get("command_or_symbol")
            == "unresolved subprocess invocation"
            and (
                record.get("source_path"),
                record.get("source_line"),
            )
            in resolved_locations
        )
    ]


def _is_package_internal_operator_root(record: dict) -> bool:
    if record.get("root_kind") != "operator_cli":
        return False
    source_path = Path(str(record.get("source_path") or ""))
    if not source_path.parts or source_path.parts[0] != "scripts":
        return False

    scripts_root = repo.ROOT / "scripts"
    path = repo.ROOT / source_path
    current = path.parent
    while current != scripts_root and scripts_root in current.parents:
        if (current / "__init__.py").is_file():
            return True
        current = current.parent
    return False


def _canonical_invocations(
    invocations: list[dict] | None,
) -> list[dict]:
    if invocations is None:
        records = invocation_scan.collect_all()
        records.extend(subprocess_aliases.scan_subprocess_aliases())
        records.sort(key=lambda record: record.sort_key())
        invocations = [record.to_dict() for record in records]

    _, hardened = harden_inventory_dicts(None, invocations)
    hardened = _remove_replaced_unresolved_children(hardened) or []
    hardened = [
        record
        for record in hardened
        if not _is_package_internal_operator_root(record)
    ]
    hardened.sort(
        key=lambda record: (
            str(record.get("root_kind", "")),
            str(record.get("root_id", "")),
        )
    )
    return hardened


def _root_source_texts(invocations: list[dict]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for root in invocations:
        source_path = str(root.get("source_path") or "")
        if not source_path or source_path in texts:
            continue
        text = repo.read_text(repo.ROOT / source_path)
        if text is not None:
            texts[source_path] = text
    return texts


def _relink_storage(
    storage: list[dict],
    invocations: list[dict],
) -> list[dict]:
    root_texts = _root_source_texts(invocations)
    result: list[dict] = []
    for raw_record in storage:
        record = dict(raw_record)
        source_path = str(record.get("source_path") or "")
        source_stem = Path(source_path).stem
        roots: set[str] = set()
        for root in invocations:
            root_id = str(root.get("root_id") or "")
            if not root_id:
                continue
            root_source = str(root.get("source_path") or "")
            command = str(root.get("command_or_symbol") or "")
            root_kind = str(root.get("root_kind") or "")
            if root_source == source_path:
                roots.add(root_id)
                continue
            if root_kind in _SHARED_ENTRY_ROOT_KINDS:
                if source_stem and source_stem in command:
                    roots.add(root_id)
                continue
            source_text = root_texts.get(root_source)
            if source_text is not None and source_stem in source_text:
                roots.add(root_id)
                continue
            if source_path and source_path in command:
                roots.add(root_id)
        record["invocation_roots"] = sorted(roots)
        result.append(record)
    result.sort(
        key=lambda record: (
            str(record.get("source_path", "")),
            str(record.get("artifact_pattern", "")),
        )
    )
    return result


def _canonical_config(config: list[dict]) -> list[dict]:
    records = [
        dict(record)
        for record in config
        if record.get("key_kind")
        not in {"config_key", "feature_flag"}
    ]
    records.extend(
        record.to_dict()
        for record in yaml_config_locations.scan_config_keys_and_flags()
    )
    records.sort(
        key=lambda record: (
            str(record.get("key_kind", "")),
            str(record.get("name", "")),
            str(record.get("source_context", "")),
        )
    )
    return records


def build_payload(
    tool_version: str,
    source_commit_sha: str,
    modes: list[str],
    storage: list[dict] | None,
    invocations: list[dict] | None,
    config: list[dict] | None,
) -> dict:
    canonical_invocations = None
    if storage is not None or invocations is not None:
        canonical_invocations = _canonical_invocations(invocations)
    if storage is not None:
        storage = _relink_storage(
            storage,
            canonical_invocations or [],
        )
    if invocations is not None:
        invocations = canonical_invocations
    if config is not None:
        config = _canonical_config(config)

    payload: dict = {
        "tool": "relaylm_repo_inventory",
        "tool_version": tool_version,
        "source_commit_sha": source_commit_sha,
        "modes": sorted(modes),
        "inclusion_rules": list(INCLUSION_RULES),
        "limitations": list(LIMITATIONS),
    }
    if storage is not None:
        payload["storage"] = storage
        payload["storage_count"] = len(storage)
    if invocations is not None:
        payload["invocations"] = invocations
        payload["invocations_count"] = len(invocations)
    if config is not None:
        payload["config"] = config
        payload["config_count"] = len(config)
    return payload


def render_json(payload: dict) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=False,
        ensure_ascii=True,
    ) + "\n"


def _md_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, (list, tuple)):
                value = ", ".join(str(item) for item in value)
            cells.append(
                str(value).replace("|", "\\|").replace("\n", " ")[:200]
            )
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append("# RelayLM Repository & Storage Inventory")
    lines.append("")
    lines.append(
        "Mechanically generated. Maintainer/review evidence only -- "
        "not documentation authority."
    )
    lines.append("")
    lines.append(f"- tool: `{payload['tool']}`")
    lines.append(f"- tool_version: `{payload['tool_version']}`")
    lines.append(
        f"- source_commit_sha: `{payload['source_commit_sha']}`"
    )
    lines.append(f"- modes: {', '.join(payload['modes'])}")
    lines.append("")
    lines.append("## Inclusion rules")
    lines.append("")
    for rule in payload["inclusion_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for limitation in payload["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")

    if "storage" in payload:
        lines.append(
            f"## A. Storage artifacts ({payload['storage_count']})"
        )
        lines.append("")
        columns = [
            "source_path",
            "artifact_pattern",
            "artifact_format",
            "probable_owner",
            "classification_state",
            "user_owned_data_possible",
            "invocation_roots",
            "heuristic_fields",
        ]
        lines.extend(_md_table(payload["storage"], columns))
        lines.append("")

    if "invocations" in payload:
        lines.append(
            f"## B. Invocation roots ({payload['invocations_count']})"
        )
        lines.append("")
        columns = [
            "root_kind",
            "root_id",
            "command_or_symbol",
            "source_path",
            "source_line",
            "reachable_from_fastapi_import_graph",
            "notes",
        ]
        lines.extend(_md_table(payload["invocations"], columns))
        lines.append("")

    if "config" in payload:
        lines.append(
            "## C. Config, feature flags, and dependencies "
            f"({payload['config_count']})"
        )
        lines.append("")
        lines.extend(
            _md_table(
                payload["config"],
                [
                    "key_kind",
                    "name",
                    "source_context",
                    "referenced_in",
                ],
            )
        )
        lines.append("")

    return "\n".join(lines) + "\n"
