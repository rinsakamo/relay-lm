#!/usr/bin/env python3
"""Validate cross-document authority and semantic documentation invariants."""
from __future__ import annotations

import argparse
import datetime
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_METADATA_PATHS = (
    "docs/DOCUMENTATION_MODEL.md",
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/contracts/README.md",
    "docs/contracts/client_instruction_target_artifact_contract.md",
    "docs/evidence/implementation/README.md",
    "docs/evidence/waves/README.md",
    "docs/release/README.md",
    "docs/release/v0.1-release-readiness.md",
    "docs/evidence/releases/README.md",
    "docs/evidence/releases/v0.1-final-main-validation-tag-receipt.md",
    "docs/relaysoul/README.md",
    "docs/smoke/README.md",
    "docs/smoke/consolidated_workflow_maintenance.md",
    "docs/smoke/scripts_inventory.md",
    "docs/operations/mobile-dogfood-entry.md",
)

REQUIRED_METADATA_KEYS = (
    "relaylm_doc_type",
    "relaylm_authority",
    "relaylm_status",
    "relaylm_volatility",
    "relaylm_owner",
)

ALLOWED_STATUSES = {
    "current",
    "target",
    "compatibility",
    "historical",
    "historical_after_merge",
    "frozen",
}

SCRIPT_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(scripts/[A-Za-z0-9_./-]+\.py)\b")
MODEL_TYPE_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

RETIRED_RELEASE_PATHS = (
    "docs/mvp/v0.1_release_readiness.md",
    "docs/mvp/v0.1_final_validation_receipt.md",
)

RETIRED_TEMPLATE_PATHS = ("docs/mvp/IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md",)
CANONICAL_COMPLETION_REPORT_TEMPLATE_PATH = "docs/templates/implementation-completion-report.md"
RETIRED_MVP_TREE = "docs/mvp"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def parse_front_matter(relative_path: str) -> tuple[dict[str, Any], str]:
    text = read_text(relative_path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{relative_path}: missing YAML front matter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise AssertionError(f"{relative_path}: unterminated YAML front matter") from exc
    raw = "\n".join(lines[1:end])
    metadata = yaml.safe_load(raw)
    if not isinstance(metadata, dict):
        raise AssertionError(f"{relative_path}: front matter must be a mapping")
    body = "\n".join(lines[end + 1 :])
    return metadata, body


def section_body(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start < 0:
        raise AssertionError(f"missing section: {marker}")
    remainder = text[start + len(marker) :]
    next_heading = remainder.find("\n## ")
    return remainder if next_heading < 0 else remainder[:next_heading]


def check_metadata(errors: list[str]) -> None:
    model_text = read_text("docs/DOCUMENTATION_MODEL.md")
    allowed_types = set(MODEL_TYPE_RE.findall(model_text))
    for required_type in ("release", "evidence"):
        if required_type not in allowed_types:
            errors.append(f"docs/DOCUMENTATION_MODEL.md: {required_type} type missing")

    for relative_path in REQUIRED_METADATA_PATHS:
        try:
            metadata, _ = parse_front_matter(relative_path)
        except (AssertionError, OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(str(exc))
            continue

        missing = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
        if missing:
            errors.append(f"{relative_path}: missing metadata keys {missing!r}")

        doc_type = metadata.get("relaylm_doc_type")
        if doc_type not in allowed_types:
            errors.append(f"{relative_path}: unknown relaylm_doc_type {doc_type!r}")

        status = metadata.get("relaylm_status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{relative_path}: invalid relaylm_status {status!r}")

        for key in ("relaylm_update_trigger", "relaylm_not_authoritative_for"):
            value = metadata.get(key)
            if value is not None and not isinstance(value, list):
                errors.append(f"{relative_path}: {key} must be a YAML list when present")

        current_source = metadata.get("relaylm_current_status_source")
        if isinstance(current_source, str):
            target = ((ROOT / relative_path).parent / current_source).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"{relative_path}: current-status source escapes repository")
            else:
                if not target.is_file():
                    errors.append(
                        f"{relative_path}: missing relaylm_current_status_source {current_source}"
                    )


def check_e2_boundary(errors: list[str]) -> None:
    path = "docs/architecture/current_target_migration_guide.md"
    text = read_text(path)
    try:
        remaining = section_body(text, "RelaySLP and Primary MEM migration")
    except AssertionError as exc:
        errors.append(f"{path}: {exc}")
        return
    remaining_marker = "Remaining migration is deliberately narrower:"
    marker_index = remaining.find(remaining_marker)
    if marker_index < 0:
        errors.append(f"{path}: remaining-migration marker missing")
        return
    remaining_tail = remaining[marker_index:]
    if "durable-memory E2 value smoke" in remaining_tail:
        errors.append(f"{path}: completed E2 value smoke is still listed as remaining migration")
    completion = "The durable-memory E2 value smoke after O2/O3 scheduler draining is complete"
    if completion not in text:
        errors.append(f"{path}: completed E2 boundary statement missing")


def check_client_instruction_boundary(errors: list[str]) -> None:
    path = "docs/contracts/client_instruction_target_artifact_contract.md"
    text = read_text(path)
    required = (
        "trusted runtime-private typed-parse candidate validation",
        "default-off, dry-run-first independent cache writer",
        "no backend-response or frontend-metadata parse producer",
        "no semantic RelaySCN projection apply",
    )
    for anchor in required:
        if anchor not in text:
            errors.append(f"{path}: missing current/target anchor {anchor!r}")
    forbidden = (
        "not current:\n  cache writer",
        "Current\n  validate relaylm.client_instruction_cache.v0 entries read-only\n  no writer",
        "typed parse validation, cache-entry write, allowlisted RelaySCN projection apply",
    )
    for anchor in forbidden:
        if anchor in text:
            errors.append(f"{path}: stale writer boundary remains: {anchor!r}")


def check_release_assessment(errors: list[str]) -> None:
    assessment_path = "docs/release/v0.1-release-readiness.md"
    receipt_path = "docs/evidence/releases/v0.1-final-main-validation-tag-receipt.md"

    receipt_location = ROOT / receipt_path
    if not receipt_location.is_file():
        errors.append(f"{receipt_path}: canonical release-evidence receipt is missing")
        return

    assessment_metadata, assessment_body = parse_front_matter(assessment_path)
    if assessment_metadata.get("relaylm_doc_type") != "release":
        errors.append(f"{assessment_path}: must be relaylm_doc_type release")
    if assessment_metadata.get("relaylm_status") != "current":
        errors.append(f"{assessment_path}: must be relaylm_status current")

    receipt_metadata, receipt_body = parse_front_matter(receipt_path)
    if receipt_metadata.get("relaylm_doc_type") != "evidence":
        errors.append(f"{receipt_path}: must be relaylm_doc_type evidence")
    if receipt_metadata.get("relaylm_status") != "frozen":
        errors.append(f"{receipt_path}: final validation receipt must be frozen")

    validated_commit = receipt_metadata.get("relaylm_source_commit")
    if not isinstance(validated_commit, str) or FULL_SHA_RE.fullmatch(validated_commit) is None:
        errors.append(f"{receipt_path}: relaylm_source_commit must be a full lowercase SHA")
        validated_commit = None

    assessment_required = (
        "final main-HEAD validation: complete",
        "v0.1 tag creation: complete",
        "tag binding verification: exact match",
        "frozen final validation receipt: issued",
    )
    for anchor in assessment_required:
        if anchor not in assessment_body:
            errors.append(f"{assessment_path}: missing completed-validation anchor {anchor!r}")

    receipt_required = (
        "validation result: pass",
        "tag candidate: v0.1",
        "tag creation state: complete",
        "tag binding verification: exact match",
    )
    for anchor in receipt_required:
        if anchor not in receipt_body:
            errors.append(f"{receipt_path}: missing frozen receipt anchor {anchor!r}")

    if validated_commit is not None:
        for path, body in ((assessment_path, assessment_body), (receipt_path, receipt_body)):
            if validated_commit not in body:
                errors.append(f"{path}: validated commit {validated_commit!r} missing from body")

    rejected_pending_anchors = (
        "final main-HEAD validation: pending",
        "v0.1 tag creation: pending",
        "tag creation state: pending",
        "frozen release receipt: not yet issued",
        "final main-HEAD validation and a frozen tag receipt remain pending",
        "A final main-HEAD smoke pass is still required before tagging",
    )
    for path, body in ((assessment_path, assessment_body), (receipt_path, receipt_body)):
        for anchor in rejected_pending_anchors:
            if anchor in body:
                errors.append(f"{path}: stale pending-state anchor present {anchor!r}")

    for retired_path in RETIRED_RELEASE_PATHS:
        if (ROOT / retired_path).exists():
            errors.append(f"{retired_path}: retired release path must not be reintroduced")


def check_completion_report_template(errors: list[str]) -> None:
    for retired_path in RETIRED_TEMPLATE_PATHS:
        if (ROOT / retired_path).exists():
            errors.append(f"{retired_path}: retired template path must not be reintroduced")

    canonical_path = CANONICAL_COMPLETION_REPORT_TEMPLATE_PATH
    canonical_target = ROOT / canonical_path
    if not canonical_target.exists():
        errors.append(f"{canonical_path}: canonical completion-report template is missing")
        return

    metadata, body = parse_front_matter(canonical_path)
    if metadata.get("relaylm_doc_type") != "template":
        errors.append(f"{canonical_path}: relaylm_doc_type must be 'template'")
    if metadata.get("relaylm_status") != "target":
        errors.append(f"{canonical_path}: relaylm_status must be 'target'")
    if metadata.get("relaylm_authority") != "non_authoritative_implementation_completion_report_template":
        errors.append(f"{canonical_path}: relaylm_authority must be the non-authoritative template key")
    if "docs/evidence/implementation/" not in body:
        errors.append(f"{canonical_path}: must instruct the canonical evidence destination")

    retired_generated_profile_anchors = (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_status: historical_after_merge",
    )
    present_retired = [anchor for anchor in retired_generated_profile_anchors if anchor in body]
    if present_retired:
        errors.append(
            f"{canonical_path}: generated-report example must not reintroduce the retired "
            f"implementation_completion_report/historical_after_merge profile: {present_retired!r}"
        )

    migration_only_provenance_anchors = (
        "relaylm_source_origin_commit:",
        "relaylm_source_blob:",
        "relaylm_source_content_sha256:",
        "relaylm_pre_cutover_blob:",
        "relaylm_pre_cutover_content_sha256:",
        "relaylm_exact_source_snapshot:",
    )
    present_migration_only = [anchor for anchor in migration_only_provenance_anchors if anchor in body]
    if present_migration_only:
        errors.append(
            f"{canonical_path}: generated-report example must not require migration-only "
            f"provenance fields for a natively canonical report: {present_migration_only!r}"
        )

    if "relaylm_doc_type: evidence" not in body or "relaylm_status: frozen" not in body:
        errors.append(f"{canonical_path}: generated-report example must use the canonical evidence/frozen profile")

    templates_index = read_text("docs/templates/README.md")
    if "implementation-completion-report.md" not in templates_index:
        errors.append("docs/templates/README.md: missing canonical completion-report template link")

    implementation_index = read_text("docs/evidence/implementation/README.md")
    if "IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md" in implementation_index:
        errors.append("docs/evidence/implementation/README.md: still links the retired template path")
    if "../../templates/implementation-completion-report.md" not in implementation_index:
        errors.append(
            "docs/evidence/implementation/README.md: missing link to the canonical completion-report template"
        )


MVP_REFERENCE_PATTERN = re.compile(r"docs/mvp(?:/|\b)")

# Files whose *entire* content is historical/migration record-keeping by
# construction, never live current navigation. Kept short and explicit
# deliberately: this is not a place to hide a file merely because it is
# inconvenient to line-allowlist.
MVP_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        "docs/planning/documentation-cutover-rules.yaml",
        "docs/planning/documentation-cutover-tooling.md",
        # This guard's own implementation necessarily names the retired
        # literal it detects; excluding it is the same self-reference every
        # signature-based detector requires for its own signature database.
        "scripts/relaylm_docs_semantic_audit.py",
    }
)

# Statuses that mark a Markdown document's own body as a frozen/historical
# point-in-time record rather than current navigation. A retired-path mention
# inside such a document is historical by the document's own declared
# metadata, not something that needs per-line enumeration.
MVP_REFERENCE_HISTORICAL_STATUSES = frozenset({"frozen", "historical_after_merge", "historical"})

# Exact, reviewed line-content substrings that are legitimate occurrences of
# the retired docs/mvp/ literal inside otherwise-active/current files: guard
# code naming the path it rejects, committed self-test fixtures, and the one
# pinned historical-baseline workflow assertion. Any occurrence of the
# pattern NOT covered by a whole-file allowlist entry above and NOT matching
# one of these exact substrings fails closed.
MVP_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/evidence/implementation/README.md": (
        "no `docs/mvp/wave*/` path exists to route through",
    ),
    ".github/workflows/documentation-cutover-preparation.yml": (
        '"docs/mvp/mvp10_summary.md=docs/mvp/README.md"',
    ),
    "scripts/relaylm_ci_consolidated_smoke_contract.py": (
        'RETIRED_WAVE_REPORT_FAMILY = re.compile(r"^docs/mvp/wave\\d+/")',
        '["docs/mvp/wave3/i4d_completion_report.md"],',
        'fail(f"retired docs/mvp/wave<N>/ selector still present in {workflow}/{group}")',
    ),
    "scripts/relaylm_docs_cutover_prepare.py": (
        '"relative_after_mvp": path.removeprefix("docs/mvp/"),',
        'values = template_values("docs/mvp/wave9/example_completion_report.md")',
    ),
    "scripts/relaylm_docs_relative_link_inventory.py": (
        '"docs/mvp/README.md", "mvp10_summary.md"',
        ') == "docs/mvp/mvp10_summary.md"',
        '"docs/mvp/README.md", "../architecture/example.md#section"',
        '"docs/mvp/README.md", "https://example.com/x.md"',
    ),
    "scripts/relaylm_documentation_current_boundary_smoke.py": (
        "docs/mvp/wave6/e1r2_completion_report.md",
        '"retired docs/mvp/ tree reintroduced (retired by Cutover 1C-38)"',
    ),
    "scripts/relaylm_mvp_completion_report_smoke.py": (
        'OLD_TEMPLATE_PATH = "docs/mvp/IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md"',
        '"legacy docs/mvp/wave<N>/*_completion_report.md path(s) reintroduced "',
        '"retired docs/mvp/ tree reintroduced (retired by Cutover 1C-38; canonical "',
        'check("real repository: docs/mvp/ tree is absent", assert_no_mvp_tree)',
        "A synthetic reintroduced docs/mvp/README.md is rejected.",
        '"reintroduced docs/mvp/README.md is rejected",',
        '"retired docs/mvp/ tree reintroduced",',
        "A synthetic file anywhere below docs/mvp/ is rejected.",
        '"reintroduced file anywhere below docs/mvp/ is rejected",',
        "A clean synthetic tree with no docs/mvp/ directory at all is silent.",
        'check("clean synthetic tree with no docs/mvp/ directory is silent", _no_mvp_dir_silent)',
    ),
}

# Directories/suffixes making up the repository-wide active-reference scan
# scope. README.md, README_ja.md, config.example.yaml, and pyproject.toml are
# scanned individually below since they live at the repository root.
MVP_REFERENCE_SCAN_DIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("docs", (".md", ".yaml", ".yml")),
    ("scripts", (".py",)),
    (".github/workflows", (".yml", ".yaml")),
    ("relaylm", (".py",)),
    ("tests", (".py",)),
)
MVP_REFERENCE_SCAN_ROOT_FILES = ("README.md", "README_ja.md", "config.example.yaml", "pyproject.toml")


def _mvp_reference_scanned_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for name in MVP_REFERENCE_SCAN_ROOT_FILES:
        candidate = root / name
        if candidate.is_file():
            files.append(candidate)
    for directory, suffixes in MVP_REFERENCE_SCAN_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for suffix in suffixes:
            files.extend(sorted(base.rglob(f"*{suffix}")))
    return files


def _mvp_reference_file_allowlisted(relative_path: str) -> bool:
    if relative_path in MVP_REFERENCE_ALLOWLISTED_FILES:
        return True
    if relative_path.startswith("docs/evidence/") and relative_path.endswith("-source.txt"):
        return True
    if relative_path.startswith("docs/evidence/migrations/") and relative_path.endswith(".tsv"):
        return True
    return False


def _mvp_reference_status_allowlisted(root: Path, relative_path: str) -> bool:
    if not relative_path.endswith(".md"):
        return False
    try:
        text = (root / relative_path).read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return False
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except (OSError, UnicodeError, StopIteration, yaml.YAMLError):
        return False
    if not isinstance(metadata, dict):
        return False
    return metadata.get("relaylm_status") in MVP_REFERENCE_HISTORICAL_STATUSES


def check_no_live_mvp_tree(errors: list[str]) -> None:
    mvp_root = ROOT / RETIRED_MVP_TREE
    if mvp_root.exists():
        offenders = sorted(
            path.relative_to(ROOT).as_posix() for path in mvp_root.rglob("*") if path.is_file()
        )
        errors.append(
            f"{RETIRED_MVP_TREE}: retired transitional index tree reintroduced (retired by "
            f"Cutover 1C-38): {offenders or [RETIRED_MVP_TREE]}"
        )

    for path in _mvp_reference_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if _mvp_reference_file_allowlisted(relative_path):
            continue
        if _mvp_reference_status_allowlisted(ROOT, relative_path):
            continue
        allowed_lines = MVP_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if MVP_REFERENCE_PATTERN.search(line) is None:
                continue
            stripped = line.strip()
            if any(allowed in stripped for allowed in allowed_lines):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired docs/mvp/ tree: "
                f"{stripped!r}"
            )


CUTOVER_RULES_PATH = "docs/planning/documentation-cutover-rules.yaml"


def check_cutover_rule_target_types(errors: list[str]) -> None:
    """Every `path_overrides` entry's declared target document type(s) must
    match the actual `relaylm_doc_type` of its target file(s), whenever that
    target exists in the live tree. This planning document also records
    overrides for a proposed future architecture layout that has not been
    adopted, so an override whose target does not yet exist is skipped
    rather than treated as an error; only a real, existing destination can
    silently drift out of sync with its recorded type.

    An entry may declare either a single `target_doc_type` shared by every
    `target_paths` entry, or a `target_records` list of
    `{target_path, target_doc_type}` mappings for a source that splits into
    targets of different document types. A split entry must use
    `target_records`, never a single `target_doc_type` applied to every
    target, since that would silently misrepresent at least one target's
    real type.
    """
    rules_path = ROOT / CUTOVER_RULES_PATH
    try:
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{CUTOVER_RULES_PATH}: could not parse: {exc}")
        return
    overrides = rules.get("path_overrides") if isinstance(rules, dict) else None
    if not isinstance(overrides, dict):
        errors.append(f"{CUTOVER_RULES_PATH}: missing or malformed path_overrides mapping")
        return

    def check_one(old_path: str, target_path: str, declared_type: Any) -> None:
        target_file = ROOT / str(target_path)
        if not target_file.is_file():
            return
        try:
            metadata, _ = parse_front_matter(str(target_path))
        except AssertionError:
            return
        actual_type = metadata.get("relaylm_doc_type")
        if actual_type is not None and actual_type != declared_type:
            errors.append(
                f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}] target {target_path!r}'s "
                f"declared target_doc_type {declared_type!r} does not match its actual "
                f"relaylm_doc_type {actual_type!r}"
            )

    for old_path, entry in overrides.items():
        if not isinstance(entry, dict):
            errors.append(f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}] is not a mapping")
            continue

        has_target_records = "target_records" in entry
        has_legacy_shape = "target_paths" in entry or "target_doc_type" in entry
        if has_target_records and has_legacy_shape:
            errors.append(
                f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}] mixes target_records with "
                "legacy target_paths/target_doc_type; use exactly one shape"
            )
            continue

        if has_target_records:
            target_records = entry["target_records"]
            if not isinstance(target_records, list) or not target_records:
                errors.append(
                    f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records must be a "
                    "non-empty list"
                )
                continue
            seen_types: dict[str, str] = {}
            for record in target_records:
                if not isinstance(record, dict):
                    errors.append(
                        f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records has a "
                        f"non-mapping entry: {record!r}"
                    )
                    continue
                target_path = record.get("target_path")
                target_type = record.get("target_doc_type")
                if not isinstance(target_path, str) or not target_path:
                    errors.append(
                        f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records entry is "
                        f"missing a non-empty target_path: {record!r}"
                    )
                    continue
                if not isinstance(target_type, str) or not target_type:
                    errors.append(
                        f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records entry is "
                        f"missing a non-empty target_doc_type: {record!r}"
                    )
                    continue
                if target_path in seen_types:
                    if seen_types[target_path] != target_type:
                        errors.append(
                            f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records has "
                            f"conflicting document types for target_path {target_path!r}: "
                            f"{seen_types[target_path]!r} vs {target_type!r}"
                        )
                    else:
                        errors.append(
                            f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records has a "
                            f"duplicate target_path: {target_path!r}"
                        )
                    continue
                seen_types[target_path] = target_type
                check_one(old_path, target_path, target_type)
            continue

        if not has_legacy_shape:
            errors.append(
                f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}] must declare either "
                "target_records or target_doc_type"
            )
            continue

        declared_type = entry.get("target_doc_type")
        for target_path in entry.get("target_paths", []) or []:
            check_one(old_path, str(target_path), declared_type)


# ---------------------------------------------------------------------------
# Cutover 1C-39: docs/evaluation/lat1_retrieval_scaling_report.md retired,
# split into a canonical evaluation_method and a canonical template. Narrow,
# reviewed guard mirroring the docs/mvp/ active-reference scan above, scoped
# to this one retired path rather than a whole tree.
# ---------------------------------------------------------------------------
LAT1_RETIRED_SCAFFOLD_PATH = "docs/evaluation/lat1_retrieval_scaling_report.md"
# Matches the full retired path, the bare filename, and the stable underscore
# stem without an extension (e.g. an anchor or a script literal that never
# spells out ".md"), anywhere in a scanned file. Deliberately underscore-only:
# the canonical template's own filename is the *hyphenated* form of a similar
# stem (docs/templates/evaluation/lat1-retrieval-scaling-report.md), which is
# a live, current path, not a retired one -- flagging that hyphenated stem
# generically would make this guard reject the template's own legitimate
# name. Only the underscored stem ever identifies the retired source.
LAT1_REFERENCE_PATTERN = re.compile(r"\blat1_retrieval_scaling_report\b")
LAT1_METHOD_PATH = "docs/evaluation/lat1-retrieval-scaling.md"
LAT1_TEMPLATE_PATH = "docs/templates/evaluation/lat1-retrieval-scaling-report.md"

# Files whose entire content is historical/migration record-keeping by
# construction and may legitimately name the retired literal without
# per-line review. Kept short and explicit: `documentation-cutover-rules.yaml`
# is deliberately NOT here -- it is an active planning authority, not a
# historical record, so its one legitimate occurrence is line-allowlisted
# below instead of exempting the whole file. This guard's own implementation
# necessarily names the pattern it detects.
LAT1_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        "scripts/relaylm_docs_semantic_audit.py",
    }
)

# The one exact, reviewed frozen source snapshot that legitimately contains
# the retired literal as byte-for-byte historical evidence. Deliberately a
# closed set of exact paths, not a generic "*-source.txt" suffix rule: a
# future -source.txt snapshot must be individually reviewed and added here,
# not silently exempted by filename pattern alone.
LAT1_REFERENCE_EXACT_SNAPSHOT_ALLOWLIST = frozenset(
    {"docs/evidence/implementation/lat1_latency_measurement_completion_report-source.txt"}
)

# Exact, reviewed line-content substrings that are legitimate occurrences of
# the retired LAT-1 scaffold literal inside otherwise-active/current files.
# This check deliberately does NOT fall back to the generic
# frozen/historical_after_merge/historical whole-file status bypass used by
# the docs/mvp/ guard: every legitimate historical occurrence here is
# allowed by its own exact file and line, not by a document-wide status flag,
# so a genuinely new stale reference inside an otherwise-historical file
# cannot hide behind that document's status.
LAT1_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/planning/documentation-architecture-inventory.md": (
        "| `docs/evaluation/lat1_retrieval_scaling_report.md` |",
    ),
    "scripts/relaylm_documentation_current_boundary_smoke.py": (
        'assert not (ROOT / "docs" / "evaluation" / "lat1_retrieval_scaling_report.md").exists(), (',
        '"retired docs/evaluation/lat1_retrieval_scaling_report.md reintroduced "',
    ),
    "docs/planning/documentation-cutover-rules.yaml": (
        "docs/evaluation/lat1_retrieval_scaling_report.md:",
    ),
    "docs/evidence/implementation/lat1_latency_measurement_completion_report.md": (
        "- `docs/evaluation/lat1_retrieval_scaling_report.md`: report template with",
        "- `docs/evaluation/lat1_retrieval_scaling_report.md`",
        "- The retrieval scaling report (`docs/evaluation/lat1_retrieval_scaling_report.md`)",
    ),
}


def check_no_live_lat1_scaffold(errors: list[str]) -> None:
    if (ROOT / LAT1_RETIRED_SCAFFOLD_PATH).exists():
        errors.append(
            f"{LAT1_RETIRED_SCAFFOLD_PATH}: retired mixed method/template scaffold "
            "reintroduced (retired by Cutover 1C-39)"
        )

    for path in _mvp_reference_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path == LAT1_RETIRED_SCAFFOLD_PATH:
            continue
        if relative_path in LAT1_REFERENCE_ALLOWLISTED_FILES:
            continue
        if relative_path in LAT1_REFERENCE_EXACT_SNAPSHOT_ALLOWLIST:
            continue
        allowed_lines = LAT1_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if LAT1_REFERENCE_PATTERN.search(line) is None:
                continue
            stripped = line.strip()
            if any(allowed in stripped for allowed in allowed_lines):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{LAT1_RETIRED_SCAFFOLD_PATH}: {stripped!r}"
            )


def check_lat1_evaluation_split(errors: list[str]) -> None:
    method_file = ROOT / LAT1_METHOD_PATH
    template_file = ROOT / LAT1_TEMPLATE_PATH
    if not method_file.is_file():
        errors.append(f"{LAT1_METHOD_PATH}: canonical LAT-1 evaluation method is missing")
    if not template_file.is_file():
        errors.append(f"{LAT1_TEMPLATE_PATH}: canonical LAT-1 report template is missing")
    if not method_file.is_file() or not template_file.is_file():
        return

    try:
        method_metadata, method_body = parse_front_matter(LAT1_METHOD_PATH)
    except AssertionError as exc:
        errors.append(str(exc))
        return
    try:
        template_metadata, template_body = parse_front_matter(LAT1_TEMPLATE_PATH)
    except AssertionError as exc:
        errors.append(str(exc))
        return

    if method_metadata.get("relaylm_doc_type") != "evaluation_method":
        errors.append(f"{LAT1_METHOD_PATH}: relaylm_doc_type must be 'evaluation_method'")
    if template_metadata.get("relaylm_doc_type") != "template":
        errors.append(f"{LAT1_TEMPLATE_PATH}: relaylm_doc_type must be 'template'")

    for path, metadata in ((LAT1_METHOD_PATH, method_metadata), (LAT1_TEMPLATE_PATH, template_metadata)):
        if metadata.get("relaylm_doc_type") == "evaluation_record":
            errors.append(f"{path}: must not carry the retired legacy evaluation_record doc type")

    method_authority = method_metadata.get("relaylm_authority")
    template_authority = template_metadata.get("relaylm_authority")
    if method_authority and method_authority == template_authority:
        errors.append(
            f"{LAT1_METHOD_PATH}/{LAT1_TEMPLATE_PATH}: method and template must not share one "
            f"primary authority ({method_authority!r})"
        )

    if "not evidence" not in template_body.lower() and "non-authoritative" not in template_body.lower():
        errors.append(f"{LAT1_TEMPLATE_PATH}: must state that the template itself is not evidence")
    if "docs/evidence/evaluations/" not in template_body:
        errors.append(f"{LAT1_TEMPLATE_PATH}: must route a completed real run to docs/evidence/evaluations/")

    if "felt limit n:" in method_body.lower():
        errors.append(
            f"{LAT1_METHOD_PATH}: evaluation method must not itself carry result-recording cells"
        )
    if re.search(r"felt limit n:\s*\d", method_body, re.IGNORECASE):
        errors.append(f"{LAT1_METHOD_PATH}: must not claim a real scaling result has been recorded")


# ---------------------------------------------------------------------------
# Cutover 1C-40: docs/architecture/e1_local_runtime_evaluation_2026_06_25.md
# retired, moved verbatim to docs/evidence/evaluations/. Narrow, reviewed
# guard mirroring check_no_live_lat1_scaffold above, scoped to this one
# retired path.
#
# Review correction: an initial version of this guard matched only the full
# repository-root-qualified literal (docs/architecture/e1_local_runtime_...).
# It missed relative references -- a same-directory bare filename, "../",
# "../../", or a relaylm_related_authority front-matter entry -- that
# resolve to the exact same retired file. Both frozen -source.txt snapshots
# legitimately use the "../../architecture/..." relative form, which the
# prior literal-only pattern never even matched, making their allowlist
# entries untested. The guard now resolves candidate references (Markdown
# link targets and relaylm_related_authority list entries) against the
# referring file's own directory -- the same resolution model already used
# and independently tested by scripts/relaylm_docs_link_check.py's
# _resolve_local_target() -- and compares the *resolved* repository-relative
# path, not the raw text, against the retired path. It deliberately does not
# match on bare basename alone: the canonical target keeps the identical
# basename (only the directory changed), so a basename-only pattern would
# false-positive on every legitimate live reference to the new
# docs/evidence/evaluations/ location.
# ---------------------------------------------------------------------------
E1_LOCAL_RUNTIME_RETIRED_PATH = "docs/architecture/e1_local_runtime_evaluation_2026_06_25.md"
E1_LOCAL_RUNTIME_CANONICAL_PATH = "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md"

# Repository-root-qualified literal scan: catches occurrences that are not
# phrased as a Markdown link or a relaylm_related_authority entry at all
# (backtick code spans, table cells, script string literals).
E1_LOCAL_RUNTIME_REFERENCE_PATTERN = re.compile(
    r"docs/architecture/e1_local_runtime_evaluation_2026_06_25\.md"
)

# Same external-scheme set _resolve_local_target() in
# relaylm_docs_link_check.py treats as non-local and skips.
E1_LOCAL_RUNTIME_EXTERNAL_SCHEMES = frozenset(
    {"data", "file", "ftp", "http", "https", "javascript", "mailto", "sandbox", "tel"}
)
E1_LOCAL_RUNTIME_MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
E1_LOCAL_RUNTIME_RELATED_AUTHORITY_KEY_RE = re.compile(r"^relaylm_related_authority:\s*$")
E1_LOCAL_RUNTIME_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.+?)\s*$")

# Files whose entire content is historical/migration record-keeping by
# construction and may legitimately name the retired literal without
# per-line review. This guard's own implementation necessarily names the
# pattern it detects.
E1_LOCAL_RUNTIME_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        "scripts/relaylm_docs_semantic_audit.py",
    }
)

# The exact, reviewed frozen source snapshots that legitimately contain the
# retired reference (in its original relative form) as byte-for-byte
# historical evidence of the PRs that originally referenced the pre-move
# path. A closed set of exact paths, not a generic "*-source.txt" suffix
# rule. These are the two files that make the resolver above necessary: both
# use "../../architecture/e1_local_runtime_evaluation_2026_06_25.md" inside
# their own relaylm_related_authority front matter, not the repository-root
# literal. They carry a .txt extension (excluded from the standard
# docs/**/*.md scan scope), so they are explicitly added to the scan list
# below rather than relying on a broadened directory-wide *.txt walk.
E1_LOCAL_RUNTIME_REFERENCE_EXACT_SNAPSHOT_ALLOWLIST = frozenset(
    {
        "docs/evidence/implementation/e1_completion_report-source.txt",
        "docs/evidence/implementation/e1r2_completion_report-source.txt",
    }
)

# Exact, reviewed line-content substrings that are legitimate occurrences of
# the retired literal inside otherwise-active/current files. No generic
# frozen/historical_after_merge/historical whole-file status bypass: every
# legitimate historical occurrence is allowed by its own exact file and
# line, so a genuinely new stale reference cannot hide behind a document's
# status.
E1_LOCAL_RUNTIME_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/planning/documentation-architecture-inventory.md": (
        "(Cutover 1C-40: `moved` to `docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md`",
    ),
    "docs/planning/documentation-cutover-rules.yaml": (
        "docs/architecture/e1_local_runtime_evaluation_2026_06_25.md:",
    ),
}


def _e1_local_runtime_scanned_files(root: Path) -> list[Path]:
    files = list(_mvp_reference_scanned_files(root))
    existing = set(files)
    for extra in sorted(E1_LOCAL_RUNTIME_REFERENCE_EXACT_SNAPSHOT_ALLOWLIST):
        candidate = root / extra
        if candidate.is_file() and candidate not in existing:
            files.append(candidate)
            existing.add(candidate)
    return files


def _e1_local_runtime_resolve(source: Path, raw_target: str) -> str | None:
    """Resolve a Markdown link target or related-authority entry to a
    repository-relative POSIX path, mirroring
    relaylm_docs_link_check._resolve_local_target(): external schemes and
    root-relative web links are not local file references, and a target
    starting with "docs/" is treated as repository-root-qualified (the
    convention this repository's own relaylm_related_authority lists use)
    rather than relative to the referring file's own directory."""
    target = raw_target.strip()
    if not target:
        return None
    if target.startswith("<") and target.endswith(">") and len(target) >= 2:
        target = target[1:-1].strip()
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme.lower() in E1_LOCAL_RUNTIME_EXTERNAL_SCHEMES or parsed.netloc:
        return None
    path_text = unquote(parsed.path)
    if not path_text or path_text.startswith("/"):
        return None
    try:
        if path_text.startswith("docs/"):
            candidate = (ROOT / path_text).resolve()
        else:
            candidate = (source.parent / path_text).resolve()
        return candidate.relative_to(ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def check_no_live_e1_local_runtime_architecture_path(errors: list[str]) -> None:
    if (ROOT / E1_LOCAL_RUNTIME_RETIRED_PATH).exists():
        errors.append(
            f"{E1_LOCAL_RUNTIME_RETIRED_PATH}: retired dated evaluation record reintroduced "
            "under docs/architecture/ (moved to docs/evidence/evaluations/ by Cutover 1C-40)"
        )

    for path in _e1_local_runtime_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path == E1_LOCAL_RUNTIME_RETIRED_PATH:
            continue
        if relative_path == E1_LOCAL_RUNTIME_CANONICAL_PATH:
            continue
        if relative_path in E1_LOCAL_RUNTIME_REFERENCE_ALLOWLISTED_FILES:
            continue
        if relative_path in E1_LOCAL_RUNTIME_REFERENCE_EXACT_SNAPSHOT_ALLOWLIST:
            continue
        allowed_lines = E1_LOCAL_RUNTIME_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        resolve_references = path.suffix in (".md", ".txt")
        in_front_matter = False
        front_matter_seen = False
        in_related_authority = False

        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            # Pass 1: repository-root-qualified literal, anywhere in the line.
            if E1_LOCAL_RUNTIME_REFERENCE_PATTERN.search(line) is not None:
                if not any(allowed in stripped for allowed in allowed_lines):
                    errors.append(
                        f"{relative_path}:{line_number}: active reference to retired "
                        f"{E1_LOCAL_RUNTIME_RETIRED_PATH}: {stripped!r}"
                    )

            if not resolve_references:
                continue

            # Track the first "---"-delimited front-matter block so
            # relaylm_related_authority entries are only read from there,
            # not from a coincidental "- " bullet later in the document body.
            if stripped == "---":
                if not front_matter_seen:
                    in_front_matter = True
                    front_matter_seen = True
                elif in_front_matter:
                    in_front_matter = False
                    in_related_authority = False
                continue

            # Pass 2: Markdown link targets, resolved against this file's
            # own directory (or the repository root for a "docs/"-qualified
            # target).
            for match in E1_LOCAL_RUNTIME_MD_LINK_RE.finditer(line):
                raw_target = match.group(1).strip()
                resolved = _e1_local_runtime_resolve(path, raw_target)
                if resolved != E1_LOCAL_RUNTIME_RETIRED_PATH:
                    continue
                if any(allowed in stripped for allowed in allowed_lines):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{E1_LOCAL_RUNTIME_RETIRED_PATH}: markdown link target {raw_target!r}"
                )

            # Pass 3: relaylm_related_authority front-matter list entries.
            if not in_front_matter:
                continue
            if E1_LOCAL_RUNTIME_RELATED_AUTHORITY_KEY_RE.match(line) is not None:
                in_related_authority = True
                continue
            if not in_related_authority:
                continue
            item_match = E1_LOCAL_RUNTIME_LIST_ITEM_RE.match(line)
            if item_match is None:
                in_related_authority = False
                continue
            raw_target = item_match.group(1).strip()
            resolved = _e1_local_runtime_resolve(path, raw_target)
            if resolved != E1_LOCAL_RUNTIME_RETIRED_PATH:
                continue
            if any(allowed in stripped for allowed in allowed_lines):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{E1_LOCAL_RUNTIME_RETIRED_PATH}: relaylm_related_authority entry {raw_target!r}"
            )


# ---------------------------------------------------------------------------
# Cutover 1C-41: the mobile_dogfood_* method/template/operations family
# retired. Five source paths move to five distinct canonical destinations
# and document types (an evaluation method, an operations document, and
# three templates), unlike the single-path E1/LAT-1 guards above. Rather
# than duplicating five near-identical single-path guards, this generalizes
# the same reference-resolution model (mirroring
# relaylm_docs_link_check.py's _resolve_local_target(), exactly as
# check_no_live_e1_local_runtime_architecture_path() does above) to a
# dict of retired -> canonical path pairs sharing one resolver and one scan
# pass. It still does not match on bare basename alone for paths whose
# canonical target keeps a similar stem; every retired path here also
# changed its basename (underscore -> hyphen, and in one case also
# directory), so a same-directory bare-filename or ../ reference is only
# ever produced by genuinely stale content, never by a legitimate live
# reference to the new canonical name.
#
# Review correction: the first implementation resolved only Markdown link
# targets and relaylm_related_authority list entries via a hand-rolled
# per-key line-state parser, and whole-file-exempted this guard's own
# implementation file. Both were fail-open gaps. The corrected guard (1)
# parses the first YAML front-matter block with the real YAML loader and
# checks every path-bearing metadata key the documentation model uses
# (relaylm_current_status_source, relaylm_decision_source,
# relaylm_related_authority, relaylm_related_contracts,
# relaylm_related_decisions, relaylm_related_proposal, relaylm_code_sources,
# relaylm_verified_by) rather than one hardcoded key, and (2) replaces the
# whole-file self-exemption with an exact-line allowlist covering only the
# MOBILE_DOGFOOD_RETIRED_TO_CANONICAL constant's own dict-key entries -- the
# one place this file's source text must legitimately spell out a retired
# literal -- so a regression anywhere else in this file (including
# REQUIRED_METADATA_PATHS) is still caught.
# ---------------------------------------------------------------------------
MOBILE_DOGFOOD_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/evaluation/mobile_dogfood_observation_runbook.md": "docs/evaluation/mobile-dogfood-observation.md",
    "docs/tools/mobile_dogfood_entry.md": "docs/operations/mobile-dogfood-entry.md",
    "docs/evaluation/mobile_dogfood_summary_report_template.md": "docs/templates/evaluation/mobile-dogfood-summary-report.md",
    "docs/evaluation/templates/mobile_dogfood_daily_note_template.md": "docs/templates/evaluation/mobile-dogfood-daily-note.md",
    "docs/evaluation/templates/mobile_dogfood_weekly_review_template.md": "docs/templates/evaluation/mobile-dogfood-weekly-review.md",
}
MOBILE_DOGFOOD_RETIRED_PATHS = tuple(sorted(MOBILE_DOGFOOD_RETIRED_TO_CANONICAL))
MOBILE_DOGFOOD_CANONICAL_PATHS = frozenset(MOBILE_DOGFOOD_RETIRED_TO_CANONICAL.values())

# Repository-root-qualified literal scan: matches any of the five retired
# paths anywhere in a line (backtick code spans, table cells, script string
# literals, YAML mapping keys), independent of Markdown link syntax.
MOBILE_DOGFOOD_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in MOBILE_DOGFOOD_RETIRED_PATHS) + ")"
)

MOBILE_DOGFOOD_EXTERNAL_SCHEMES = E1_LOCAL_RUNTIME_EXTERNAL_SCHEMES
MOBILE_DOGFOOD_MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

# Parses only the first "---"-delimited YAML front-matter block, mirroring
# relaylm_docs_cutover_prepare.py's own FRONT_MATTER_RE (\A-anchored: a later
# "---" inside the document body is never mistaken for a second block).
MOBILE_DOGFOOD_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)

# Every path-bearing front-matter key docs/DOCUMENTATION_MODEL.md and
# established repository usage define: single-value keys hold one relative
# or docs/-qualified path, list keys hold zero or more. This replaces the
# prior relaylm_related_authority-only special case; a stale reference under
# any of these keys is now caught.
MOBILE_DOGFOOD_PATH_BEARING_SCALAR_KEYS = (
    "relaylm_current_status_source",
    "relaylm_decision_source",
)
MOBILE_DOGFOOD_PATH_BEARING_LIST_KEYS = (
    "relaylm_related_authority",
    "relaylm_related_contracts",
    "relaylm_related_decisions",
    "relaylm_related_proposal",
    "relaylm_code_sources",
    "relaylm_verified_by",
)

# Files whose entire content is historical/migration record-keeping by
# construction and may legitimately name a retired literal without per-line
# review: this receipt's own Cutover 1C-40 entry narrates why the family was
# left open at the time. This guard's own implementation file is
# deliberately NOT whole-file-exempted (see MOBILE_DOGFOOD_SELF_FILE below).
MOBILE_DOGFOOD_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
    }
)

# Exact, reviewed line-content substrings that are legitimate occurrences of
# a retired literal inside an otherwise-active/current file: the five
# path_overrides mapping keys in documentation-cutover-rules.yaml, each
# naming its own retired source path once. No generic frozen/historical/
# status bypass and no generic allowance beyond these exact lines.
MOBILE_DOGFOOD_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/planning/documentation-cutover-rules.yaml": tuple(
        f"{retired_path}:" for retired_path in MOBILE_DOGFOOD_RETIRED_PATHS
    ),
}

# This guard's own implementation file. Narrow, exact-line self-allowance
# only -- not a whole-file exemption. The only lines in this file that may
# legitimately spell out a retired literal are the
# MOBILE_DOGFOOD_RETIRED_TO_CANONICAL dict's own key: value entries (the
# guard's source of truth necessarily names the paths it rejects). Matched
# by exact stripped-line equality, not substring, so it cannot silently
# absorb an unrelated stale reference elsewhere in the file.
MOBILE_DOGFOOD_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
MOBILE_DOGFOOD_SELF_FILE_EXACT_LINES = frozenset(
    f'"{retired_path}": "{canonical_path}",'
    for retired_path, canonical_path in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL.items()
)


def _mobile_dogfood_scanned_files(root: Path) -> list[Path]:
    return _mvp_reference_scanned_files(root)


def _mobile_dogfood_resolve(source: Path, raw_target: str) -> str | None:
    """Resolve a Markdown link target or front-matter path-bearing value to a
    repository-relative POSIX path, mirroring _e1_local_runtime_resolve()
    and relaylm_docs_link_check.py's _resolve_local_target(). A URL fragment
    (anchor) or query component is stripped by urlsplit() before comparison,
    exactly as the established link resolver does."""
    target = raw_target.strip()
    if not target:
        return None
    if target.startswith("<") and target.endswith(">") and len(target) >= 2:
        target = target[1:-1].strip()
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
        return None
    path_text = unquote(parsed.path)
    if not path_text or path_text.startswith("/"):
        return None
    try:
        if path_text.startswith("docs/"):
            candidate = (ROOT / path_text).resolve()
        else:
            candidate = (source.parent / path_text).resolve()
        return candidate.relative_to(ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _mobile_dogfood_front_matter_path_values(text: str) -> list[tuple[str, str]]:
    """Return (metadata_key, raw_path_value) pairs for every supported
    path-bearing front-matter key present in the first YAML front-matter
    block only. Uses the actual parsed YAML mapping -- not per-key line
    parsing -- so every supported key is covered by one code path instead of
    a hardcoded special case for a single key. A value of the wrong shape
    (e.g. a scalar key holding a list, or a list item that is not a string)
    is skipped here rather than raised: this guard checks path references,
    it does not police front-matter shape, which is check_metadata's job."""
    match = MOBILE_DOGFOOD_FRONT_MATTER_RE.match(text)
    if match is None:
        return []
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return []
    if not isinstance(metadata, dict):
        return []

    pairs: list[tuple[str, str]] = []
    for key in MOBILE_DOGFOOD_PATH_BEARING_SCALAR_KEYS:
        value = metadata.get(key)
        if isinstance(value, str):
            pairs.append((key, value))
    for key in MOBILE_DOGFOOD_PATH_BEARING_LIST_KEYS:
        value = metadata.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    pairs.append((key, item))
    return pairs


def _mobile_dogfood_locate(lines: list[str], raw_value: str) -> tuple[int, str]:
    """Best-effort line lookup for diagnostics only: a front-matter path
    value parsed from YAML appears verbatim in the source text, either after
    "key: value" (scalar) or as its own "- value" list line. Falls back to
    line 1 if not found verbatim (e.g. quoted/escaped in a way the plain
    substring search misses), which only affects the reported line number,
    never whether the reference is rejected."""
    for line_number, line in enumerate(lines, start=1):
        if raw_value and raw_value in line:
            return line_number, line.strip()
    return 1, ""


def check_no_live_mobile_dogfood_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(
                f"{retired_path}: retired mobile-dogfood family path reintroduced "
                f"(moved to {canonical_path} by Cutover 1C-41)"
            )

    for path in _mobile_dogfood_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL:
            continue
        if relative_path in MOBILE_DOGFOOD_CANONICAL_PATHS:
            continue
        if relative_path in MOBILE_DOGFOOD_REFERENCE_ALLOWLISTED_FILES:
            continue
        is_self_file = relative_path == MOBILE_DOGFOOD_SELF_FILE
        allowed_lines = MOBILE_DOGFOOD_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()

        def _is_allowed(stripped_line: str) -> bool:
            if is_self_file:
                return stripped_line in MOBILE_DOGFOOD_SELF_FILE_EXACT_LINES
            return any(allowed in stripped_line for allowed in allowed_lines)

        # Pass 1: any of the five repository-root-qualified retired literals,
        # anywhere in the line (backtick spans, table cells, script string
        # literals, YAML mapping keys) -- independent of Markdown link or
        # front-matter syntax.
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            literal_match = MOBILE_DOGFOOD_REFERENCE_PATTERN.search(line)
            if literal_match is None or _is_allowed(stripped):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{literal_match.group(0)}: {stripped!r}"
            )

        if path.suffix not in (".md", ".txt"):
            continue

        # Pass 2: Markdown link targets, resolved against this file's own
        # directory (or the repository root for a "docs/"-qualified target).
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            for link_match in MOBILE_DOGFOOD_MD_LINK_RE.finditer(line):
                raw_target = link_match.group(1).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL:
                    continue
                if _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: markdown link target {raw_target!r}"
                )

        # Pass 3: every supported path-bearing front-matter key, resolved
        # via the actual parsed first-block YAML mapping.
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL:
                continue
            line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
            if _is_allowed(stripped):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: {key} entry {raw_target!r}"
            )


def check_mobile_dogfood_family_types(errors: list[str]) -> None:
    method_path = "docs/evaluation/mobile-dogfood-observation.md"
    method_meta, _ = parse_front_matter(method_path)
    if method_meta.get("relaylm_doc_type") != "evaluation_method":
        errors.append(
            f"{method_path}: must declare relaylm_doc_type: evaluation_method, "
            f"not {method_meta.get('relaylm_doc_type')!r}"
        )

    operations_path = "docs/operations/mobile-dogfood-entry.md"
    operations_meta, _ = parse_front_matter(operations_path)
    if operations_meta.get("relaylm_doc_type") != "operations":
        errors.append(
            f"{operations_path}: must declare relaylm_doc_type: operations, "
            f"not {operations_meta.get('relaylm_doc_type')!r}"
        )

    for template_path in (
        "docs/templates/evaluation/mobile-dogfood-summary-report.md",
        "docs/templates/evaluation/mobile-dogfood-daily-note.md",
        "docs/templates/evaluation/mobile-dogfood-weekly-review.md",
    ):
        template_meta, _ = parse_front_matter(template_path)
        if template_meta.get("relaylm_doc_type") != "template":
            errors.append(
                f"{template_path}: must declare relaylm_doc_type: template, not "
                f"{template_meta.get('relaylm_doc_type')!r} (never the retired "
                "evaluation_record type)"
            )


# ---------------------------------------------------------------------------
# Cutover 1C-39 correction: fail closed on a completed LAT-1 retrieval-scaling
# evidence record (docs/evidence/evaluations/lat1-retrieval-scaling-*.md) that
# is incomplete, unfilled, provenance-weak, or content-bearing. No such
# record exists in this repository yet; this check exists so the first one
# that is ever added cannot silently be a copy-with-blanks-left-in.
# ---------------------------------------------------------------------------
LAT1_EVIDENCE_DIR = "docs/evidence/evaluations"
LAT1_EVIDENCE_FILENAME_RE = re.compile(
    r"^lat1-retrieval-scaling-(?P<date>\d{4}-\d{2}-\d{2})-(?P<time>\d{6})Z-(?P<short_commit>[0-9a-f]{7,40})\.md$"
)
LAT1_EVIDENCE_UNFILLED_MARKERS = ("<placeholder>", "tbd", "not yet measured")
LAT1_EVIDENCE_FORBIDDEN_CONTENT_MARKERS = (
    "-----begin",
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "password",
    "secret_key",
)
LAT1_EVIDENCE_STORE_SIZES = ("100", "500", "2000", "5000")
# query_count and repeat must be strict positive integers (no zero, no
# negative, no decimal, no exponent notation, no NaN/Infinity); p50_ms,
# p95_ms, and avg_selected_count remain finite non-negative numbers.
LAT1_EVIDENCE_INTEGER_ROW_FIELDS = ("query_count", "repeat")
LAT1_EVIDENCE_FLOAT_ROW_FIELDS = ("p50_ms", "p95_ms", "avg_selected_count")
LAT1_EVIDENCE_POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]*$")
LAT1_EVIDENCE_ENV_FIELD_REPEAT = "--repeat"
LAT1_EVIDENCE_ENV_FIELD_MAX_CANDIDATES = "--max-candidates (bench flag; mirrors config.memory.candidate_limit)"
LAT1_EVIDENCE_ENV_FIELD_COMMIT = "Exact RelayLM commit SHA"
LAT1_EVIDENCE_ENV_FIELD_DATE = "Date"
LAT1_EVIDENCE_REQUIRED_ENV_FIELDS = (
    LAT1_EVIDENCE_ENV_FIELD_DATE,
    "Machine / CPU",
    "Filesystem (e.g. local SSD, network mount, container overlay)",
    "Python version",
    LAT1_EVIDENCE_ENV_FIELD_COMMIT,
    LAT1_EVIDENCE_ENV_FIELD_REPEAT,
    LAT1_EVIDENCE_ENV_FIELD_MAX_CANDIDATES,
    "Concurrent load on the machine during the run",
)
LAT1_EVIDENCE_JUDGMENT_MARKERS = (
    "- Estimated slope (ms per additional 1000 store pages):",
    "- Does `p50_ms`/`p95_ms` continue increasing beyond the internal discovery",
    "- If it plateaus, at approximately which N does it plateau?",
    "- Felt limit N:",
    "- Basis for this judgment:",
    "- Implication for candidate-limit (K), ANN adoption, or Secondary MEM",
)
LAT1_EVIDENCE_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")
LAT1_EVIDENCE_METHOD_AUTHORITY = "lat1_retrieval_scaling_bench_method"
LAT1_EVIDENCE_TEMPLATE_AUTHORITY = "non_authoritative_lat1_retrieval_scaling_report_template"


def _lat1_evidence_files(root: Path) -> list[Path]:
    directory = root / LAT1_EVIDENCE_DIR
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("lat1-retrieval-scaling-*.md") if p.is_file())


def _parse_iso_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_utc_hhmmss(value: str) -> bool:
    try:
        datetime.datetime.strptime(value, "%H%M%S")
    except ValueError:
        return False
    return True


def _parse_markdown_table(
    body: str, heading: str, relative_path: str, errors: list[str]
) -> list[dict[str, str]]:
    """Fails closed: a missing heading, malformed header/separator, a row with
    the wrong cell count, or a duplicate header field name each append an
    exact error and return no rows for that table, rather than silently
    skipping the offending line and returning a partial, plausible-looking
    result."""
    try:
        section = section_body(body, heading)
    except AssertionError:
        errors.append(f"{relative_path}: missing required section '## {heading}'")
        return []
    lines = [line for line in section.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        errors.append(f"{relative_path}: '## {heading}' table is missing a header or separator row")
        return []
    header = [cell.strip().replace("`", "") for cell in lines[0].strip().strip("|").split("|")]
    if not header or any(not cell for cell in header):
        errors.append(f"{relative_path}: '## {heading}' table header is malformed: {lines[0]!r}")
        return []
    if len(set(header)) != len(header):
        errors.append(f"{relative_path}: '## {heading}' table header has duplicate field names: {header!r}")
        return []
    separator = [cell.strip() for cell in lines[1].strip().strip("|").split("|")]
    if len(separator) != len(header) or not all(LAT1_EVIDENCE_SEPARATOR_CELL_RE.fullmatch(cell) for cell in separator):
        errors.append(f"{relative_path}: '## {heading}' table separator row is malformed: {lines[1]!r}")
        return []
    rows: list[dict[str, str]] = []
    for offset, line in enumerate(lines[2:]):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            errors.append(
                f"{relative_path}: '## {heading}' table row {offset + 1} has {len(cells)} cell(s), "
                f"expected {len(header)}: {line.strip()!r}"
            )
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _bullet_value(body: str, marker: str) -> str:
    marker_index = body.find(marker)
    if marker_index < 0:
        return ""
    remainder = body[marker_index + len(marker) :]
    end_candidates = [i for i in (remainder.find("\n- "), remainder.find("\n## ")) if i >= 0]
    end = min(end_candidates) if end_candidates else len(remainder)
    return re.sub(r"^[\s:?]+", "", remainder[:end]).strip()


def check_lat1_evaluation_evidence_records(errors: list[str]) -> None:
    files = _lat1_evidence_files(ROOT)

    # Pass 1: collect relaylm_authority across every completed record so reuse
    # (of the method's, the template's, or another record's authority) fails
    # closed even though each file is otherwise parsed independently below.
    authority_owners: dict[str, list[str]] = {}
    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        try:
            metadata, _ = parse_front_matter(relative_path)
        except (AssertionError, ValueError):
            continue
        authority = metadata.get("relaylm_authority")
        if isinstance(authority, str) and authority:
            authority_owners.setdefault(authority, []).append(relative_path)
    for authority, owners in authority_owners.items():
        if len(owners) > 1:
            for relative_path in owners:
                others = sorted(set(owners) - {relative_path})
                errors.append(
                    f"{relative_path}: relaylm_authority {authority!r} is not unique across completed "
                    f"LAT-1 evidence records (also used by {others!r})"
                )

    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        match = LAT1_EVIDENCE_FILENAME_RE.match(path.name)
        if match is None:
            errors.append(
                f"{relative_path}: filename does not match the deterministic collision-safe "
                "lat1-retrieval-scaling-YYYY-MM-DD-HHMMSSZ-<short-commit>.md convention"
            )
            continue

        try:
            metadata, body = parse_front_matter(relative_path)
        except (AssertionError, ValueError) as exc:
            # A calendar-invalid unquoted date scalar (e.g. relaylm_recorded_on:
            # 2026-99-99) makes PyYAML's timestamp constructor raise a bare
            # ValueError during front-matter parsing itself, before any
            # field-level check below ever runs; fail closed here instead of
            # letting it propagate.
            errors.append(f"{relative_path}: front matter is invalid or contains an impossible date: {exc}")
            continue

        if metadata.get("relaylm_doc_type") != "evidence":
            errors.append(f"{relative_path}: relaylm_doc_type must be 'evidence'")
        if metadata.get("relaylm_status") not in {"frozen", "historical"}:
            errors.append(f"{relative_path}: relaylm_status must be 'frozen' or 'historical'")
        if metadata.get("relaylm_owner") != "evaluation":
            errors.append(f"{relative_path}: relaylm_owner must be 'evaluation'")

        authority = metadata.get("relaylm_authority")
        if (
            not isinstance(authority, str)
            or not authority
            or authority in {LAT1_EVIDENCE_METHOD_AUTHORITY, LAT1_EVIDENCE_TEMPLATE_AUTHORITY}
        ):
            errors.append(
                f"{relative_path}: relaylm_authority must be a record-specific evaluation authority, "
                "not shared with the method or template"
            )

        # --- filename date/time: real calendar date, real UTC HHMMSS time ---
        filename_date_str = match.group("date")
        filename_date = _parse_iso_date(filename_date_str)
        if filename_date is None:
            errors.append(f"{relative_path}: filename date {filename_date_str!r} is not a real calendar date")
        filename_time_str = match.group("time")
        if not _parse_utc_hhmmss(filename_time_str):
            errors.append(f"{relative_path}: filename time {filename_time_str!r} is not a valid UTC HHMMSS time")

        # --- relaylm_recorded_on: real calendar date ---
        recorded_on_raw = metadata.get("relaylm_recorded_on")
        if isinstance(recorded_on_raw, datetime.date) and not isinstance(recorded_on_raw, datetime.datetime):
            # YAML parses an unquoted, calendar-valid YYYY-MM-DD scalar as a
            # date object; an invalid one (e.g. 2026-99-99) instead raises
            # ValueError inside parse_front_matter, already caught above.
            recorded_on_str: str | None = recorded_on_raw.isoformat()
        elif isinstance(recorded_on_raw, str):
            recorded_on_str = recorded_on_raw
        else:
            recorded_on_str = None
        recorded_on_date = _parse_iso_date(recorded_on_str)
        if recorded_on_date is None:
            errors.append(f"{relative_path}: relaylm_recorded_on must be a real, concrete ISO calendar date")

        source_commit = metadata.get("relaylm_source_commit")
        if not isinstance(source_commit, str) or FULL_SHA_RE.fullmatch(source_commit) is None:
            errors.append(
                f"{relative_path}: relaylm_source_commit must be a full 40-character lowercase "
                "commit SHA, not a branch name"
            )
            source_commit = None

        if source_commit is not None and not source_commit.startswith(match.group("short_commit")):
            errors.append(
                f"{relative_path}: filename short-commit {match.group('short_commit')!r} is not a "
                f"prefix of relaylm_source_commit {source_commit!r}"
            )

        lowered_body = body.lower()
        for marker in LAT1_EVIDENCE_UNFILLED_MARKERS:
            if marker in lowered_body:
                errors.append(
                    f"{relative_path}: unfilled placeholder marker {marker!r} present in a "
                    "completed record"
                )
        for marker in LAT1_EVIDENCE_FORBIDDEN_CONTENT_MARKERS:
            if marker in lowered_body:
                errors.append(
                    f"{relative_path}: forbidden content-bearing/credential marker {marker!r} present"
                )

        env_rows = _parse_markdown_table(body, "Execution environment", relative_path, errors)
        env_fields: dict[str, str] = {}
        seen_env_field_names: set[str] = set()
        for row in env_rows:
            field_name = row.get("Field", "").replace("`", "").strip()
            if field_name in seen_env_field_names:
                errors.append(f"{relative_path}: duplicate execution-environment field {field_name!r}")
                continue
            seen_env_field_names.add(field_name)
            env_fields[field_name] = row.get("Value", "")

        for field in LAT1_EVIDENCE_REQUIRED_ENV_FIELDS:
            value = env_fields.get(field)
            if not value or not value.strip() or value.strip() in {"-", "`<placeholder>`"}:
                errors.append(f"{relative_path}: execution environment field {field!r} is not populated")

        # --- execution environment Date: real calendar date, cross-checked ---
        env_date_str = env_fields.get(LAT1_EVIDENCE_ENV_FIELD_DATE, "").strip()
        env_date = _parse_iso_date(env_date_str) if env_date_str else None
        if env_date_str and env_date is None:
            errors.append(
                f"{relative_path}: execution environment 'Date' {env_date_str!r} is not a real calendar date"
            )

        known_dates = {
            "filename": filename_date,
            "relaylm_recorded_on": recorded_on_date,
            "execution environment Date": env_date,
        }
        distinct_known_dates = {d for d in known_dates.values() if d is not None}
        if len(distinct_known_dates) > 1:
            detail = ", ".join(f"{name}={d.isoformat()}" for name, d in known_dates.items() if d is not None)
            errors.append(
                f"{relative_path}: filename date, relaylm_recorded_on, and execution environment "
                f"Date must all match exactly: {detail}"
            )

        # --- execution environment exact commit SHA: cross-checked, not just non-empty ---
        env_commit = env_fields.get(LAT1_EVIDENCE_ENV_FIELD_COMMIT, "").strip()
        if env_commit and env_commit not in {"-", "`<placeholder>`"}:
            if FULL_SHA_RE.fullmatch(env_commit) is None:
                errors.append(
                    f"{relative_path}: execution environment {LAT1_EVIDENCE_ENV_FIELD_COMMIT!r} must be a "
                    "full 40-character lowercase commit SHA, not a branch name"
                )
            else:
                if source_commit is not None and env_commit != source_commit:
                    errors.append(
                        f"{relative_path}: execution environment {LAT1_EVIDENCE_ENV_FIELD_COMMIT!r} "
                        f"{env_commit!r} does not match relaylm_source_commit {source_commit!r}"
                    )
                if not env_commit.startswith(match.group("short_commit")):
                    errors.append(
                        f"{relative_path}: execution environment {LAT1_EVIDENCE_ENV_FIELD_COMMIT!r} "
                        f"{env_commit!r} does not match the filename short-commit "
                        f"{match.group('short_commit')!r}"
                    )

        # --- --repeat / --max-candidates: strict positive integers ---
        env_repeat_str = env_fields.get(LAT1_EVIDENCE_ENV_FIELD_REPEAT, "").strip()
        env_repeat_int: int | None = None
        if env_repeat_str and env_repeat_str not in {"-", "`<placeholder>`"}:
            if LAT1_EVIDENCE_POSITIVE_INT_RE.fullmatch(env_repeat_str) is None:
                errors.append(
                    f"{relative_path}: execution environment {LAT1_EVIDENCE_ENV_FIELD_REPEAT!r} must be a "
                    f"positive integer, got {env_repeat_str!r}"
                )
            else:
                env_repeat_int = int(env_repeat_str)

        max_candidates_str = env_fields.get(LAT1_EVIDENCE_ENV_FIELD_MAX_CANDIDATES, "").strip()
        if max_candidates_str and max_candidates_str not in {"-", "`<placeholder>`"}:
            if LAT1_EVIDENCE_POSITIVE_INT_RE.fullmatch(max_candidates_str) is None:
                errors.append(
                    f"{relative_path}: execution environment {LAT1_EVIDENCE_ENV_FIELD_MAX_CANDIDATES!r} "
                    f"must be a positive integer, got {max_candidates_str!r}"
                )

        # --- results table: exactly one row per required N, no duplicates, no extras ---
        result_rows = _parse_markdown_table(body, "Results by store size (N)", relative_path, errors)
        rows_by_n: dict[str, dict[str, str]] = {}
        size_occurrences: dict[str, int] = {}
        for row in result_rows:
            size = row.get("N (store size)", "").strip()
            size_occurrences[size] = size_occurrences.get(size, 0) + 1
            if size in rows_by_n:
                errors.append(f"{relative_path}: duplicate results row for N={size!r}")
                continue
            rows_by_n[size] = row
        for size in size_occurrences:
            if size not in LAT1_EVIDENCE_STORE_SIZES:
                errors.append(
                    f"{relative_path}: unexpected results row for N={size!r}; only "
                    f"{LAT1_EVIDENCE_STORE_SIZES!r} are allowed"
                )

        for size in LAT1_EVIDENCE_STORE_SIZES:
            row = rows_by_n.get(size)
            if row is None:
                errors.append(f"{relative_path}: missing results row for N={size}")
                continue
            parsed: dict[str, float] = {}
            for field in LAT1_EVIDENCE_INTEGER_ROW_FIELDS:
                raw_value = row.get(field, "").strip()
                if LAT1_EVIDENCE_POSITIVE_INT_RE.fullmatch(raw_value) is None:
                    errors.append(
                        f"{relative_path}: N={size} field {field!r} must be a positive integer, "
                        f"got {raw_value!r}"
                    )
                    continue
                parsed[field] = int(raw_value)
            for field in LAT1_EVIDENCE_FLOAT_ROW_FIELDS:
                raw_value = row.get(field, "").strip()
                try:
                    value = float(raw_value)
                except ValueError:
                    errors.append(f"{relative_path}: N={size} field {field!r} is not numeric: {raw_value!r}")
                    continue
                if not math.isfinite(value):
                    errors.append(
                        f"{relative_path}: N={size} field {field!r} must be a finite number, "
                        f"got {raw_value!r}"
                    )
                    continue
                if value < 0:
                    errors.append(f"{relative_path}: N={size} field {field!r} must be non-negative")
                    continue
                parsed[field] = value
            if "p50_ms" in parsed and "p95_ms" in parsed and parsed["p95_ms"] < parsed["p50_ms"]:
                errors.append(f"{relative_path}: N={size} p95_ms must be >= p50_ms")
            if "repeat" in parsed and env_repeat_int is not None and parsed["repeat"] != env_repeat_int:
                errors.append(
                    f"{relative_path}: N={size} repeat {parsed['repeat']} does not match execution "
                    f"environment --repeat {env_repeat_int}"
                )

        for marker in LAT1_EVIDENCE_JUDGMENT_MARKERS:
            value = _bullet_value(body, marker)
            if not value or "<placeholder>" in value.lower():
                errors.append(f"{relative_path}: judgment field {marker!r} is missing a populated value")


def check_implementation_evidence_index(errors: list[str]) -> None:
    index_path = "docs/evidence/implementation/README.md"
    index = read_text(index_path)
    reports = sorted((ROOT / "docs" / "evidence" / "implementation").glob("*_completion_report.md"))
    missing = [path.name for path in reports if path.name not in index]
    if missing:
        errors.append(f"{index_path}: unindexed implementation completion reports {missing!r}")


def check_operations_docs(errors: list[str]) -> None:
    mobile_path = "docs/operations/mobile-dogfood-entry.md"
    mobile_meta, mobile = parse_front_matter(mobile_path)
    if mobile_meta.get("relaylm_status") != "target":
        errors.append(f"{mobile_path}: must remain target until a dedicated origin is validated")
    for anchor in (
        "safe dedicated chat-only public origin: not implemented or identified",
        "Do not expose the Vite development server",
        "Do not point this service at RelayLM `:8090`, LM Studio `:1234`, or Vite `:5173`.",
    ):
        if anchor not in mobile:
            errors.append(f"{mobile_path}: missing public-exposure guard {anchor!r}")

    maintenance_path = "docs/smoke/consolidated_workflow_maintenance.md"
    maintenance = read_text(maintenance_path)
    inventory = read_text("docs/smoke/scripts_inventory.md")
    for relative_path, text in (
        (maintenance_path, maintenance),
        ("docs/smoke/scripts_inventory.md", inventory),
    ):
        if "generated/scripts_inventory.md" not in text:
            errors.append(f"{relative_path}: generated inventory output path missing")
        if "--output docs/smoke/scripts_inventory.md" in text:
            errors.append(f"{relative_path}: must not overwrite the reviewed summary")
    if "PR-14 must be restacked" in maintenance:
        errors.append(f"{maintenance_path}: historical PR stacking instruction remains current")


def check_referenced_repository_paths(errors: list[str]) -> None:
    paths = (
        "README.md",
        "README_ja.md",
        "apps/soul-lab/README.md",
        "docs/release/v0.1-release-readiness.md",
        "docs/evidence/releases/v0.1-final-main-validation-tag-receipt.md",
        "docs/smoke/consolidated_workflow_maintenance.md",
    )
    for relative_path in paths:
        text = read_text(relative_path)
        for candidate in sorted(set(SCRIPT_PATH_RE.findall(text))):
            clean = candidate.rstrip(".,:;)]}")
            target = ROOT / clean
            if not target.exists():
                errors.append(f"{relative_path}: referenced repository path does not exist: {clean}")


def _mvp_write(base: Path, relative: str, content: str) -> None:
    target = base / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test for the retired docs/mvp/ active-reference guard: bounded,
# deterministic, committed. Builds synthetic temp trees and monkeypatches the
# module-level ROOT rather than touching the real repository tree. Run with
# `--self-test`; wired into the documentation-current-boundary-smoke workflow.
# ---------------------------------------------------------------------------
def self_test() -> None:
    global ROOT
    real_root = ROOT
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            fn()
            results.append((name, True, ""))
        except AssertionError as exc:
            results.append((name, False, str(exc)))

    def check_rejects(name: str, fn, expected_substring: str) -> None:
        errors: list[str] = []
        fn(errors)
        ok = any(expected_substring in error for error in errors)
        results.append((name, ok, "" if ok else f"no matching error in: {errors!r}"))

    def check_silent(name: str, fn) -> None:
        errors: list[str] = []
        fn(errors)
        ok = not errors
        results.append((name, ok, "" if ok else f"unexpected errors: {errors!r}"))

    # 1. The real repository has zero active references to docs/mvp/.
    with_real = []
    check_no_live_mvp_tree(with_real)
    results.append(("real repository: no active docs/mvp/ reference", not with_real, "" if not with_real else repr(with_real)))

    # 2. A script reading docs/mvp/README.md is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "scripts/example_bad_script.py", 'text = read_text("docs/mvp/README.md")\n')
        check_rejects(
            "a script reading docs/mvp/README.md is rejected",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 3. A workflow path selector containing docs/mvp/** is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, ".github/workflows/example.yml", 'on:\n  push:\n    paths:\n      - "docs/mvp/**"\n')
        check_rejects(
            "a workflow docs/mvp/** path selector is rejected",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 4. A current Markdown document linking into docs/mvp/ (inline markdown-link form) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\nSee [old index](docs/mvp/README.md).\n",
        )
        check_rejects(
            "a current Markdown link into docs/mvp/ is rejected",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 5. A current document with an HTML link and a reference-style/autolink into docs/mvp/ is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_html.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            'See <a href="docs/mvp/README.md">the old index</a>.\n\n'
            "[ref]: docs/mvp/README.md\n",
        )
        check_rejects(
            "a current HTML/reference-style link into docs/mvp/ is rejected",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 6. An unallowlisted plain old-path literal (no link markup at all) in a current file is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_plain.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "Historical notes remain under docs/mvp/ for now.\n",
        )
        check_rejects(
            "an unallowlisted plain docs/mvp/ literal in a current document is rejected",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 7. The migration receipt's whole-file historical allowlist entry is recognized.
    def _receipt_allowlisted() -> None:
        assert _mvp_reference_file_allowlisted(
            "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
        ), "migration receipt not allowlisted"

    check("migration receipt historical literal is allowlisted", _receipt_allowlisted)

    # 8. An exact -source.txt snapshot literal is allowlisted by filename pattern.
    def _source_snapshot_allowlisted() -> None:
        assert _mvp_reference_file_allowlisted(
            "docs/evidence/implementation/example_completion_report-source.txt"
        ), "-source.txt snapshot not allowlisted"

    check("exact -source.txt snapshot literal is allowlisted", _source_snapshot_allowlisted)

    # 9. The pinned historical-baseline workflow assertion in
    # documentation-cutover-preparation.yml remains allowed (line-bounded, not whole-file).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            ".github/workflows/documentation-cutover-preparation.yml",
            "run: |\n"
            "  python scripts/relaylm_docs_relative_link_inventory.py \\\n"
            '    --assert-dependency "docs/mvp/mvp10_summary.md=docs/mvp/README.md" \\\n'
            "    --strict\n",
        )
        check_silent(
            "pinned historical-baseline workflow assertion remains allowed",
            check_no_live_mvp_tree,
        )
    ROOT = real_root

    # 10. A frozen/historical_after_merge evidence document's own retired-path
    # mention is allowed by its declared front-matter status, without being
    # individually line-allowlisted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_completion_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            "At the time of this PR, docs/mvp/README.md indexed this report.\n",
        )
        check_silent(
            "a frozen/historical_after_merge document's own retired-path mention is allowed",
            check_no_live_mvp_tree,
        )
    ROOT = real_root

    # 11. The same mention in a document declared `current` is NOT allowed by status alone.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_current_doc.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "At the time of this PR, docs/mvp/README.md indexed this report.\n",
        )
        check_rejects(
            "a current-status document's retired-path mention is not status-allowlisted",
            check_no_live_mvp_tree,
            "active reference to retired docs/mvp/ tree",
        )
    ROOT = real_root

    # 12. The real repository's cutover-rules path_overrides target types all match
    # their actual destination metadata.
    check_silent(
        "real repository: cutover-rules path_overrides target types match",
        check_cutover_rule_target_types,
    )

    # 13. A path_overrides entry whose declared target_doc_type does not match its
    # existing target file's real relaylm_doc_type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/documentation-cutover-rules.yaml",
            "path_overrides:\n"
            "  docs/example/old.md:\n"
            "    disposition: absorbed\n"
            "    target_doc_type: evidence\n"
            "    target_paths:\n"
            "      - docs/example/new.md\n",
        )
        _mvp_write(
            base,
            "docs/example/new.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a path_overrides entry with a drifted target_doc_type is rejected",
            check_cutover_rule_target_types,
            "does not match",
        )
    ROOT = real_root

    # 14. The real repository has no live reference to the retired LAT-1 scaffold.
    check_silent(
        "real repository: no active reference to the retired LAT-1 scaffold",
        check_no_live_lat1_scaffold,
    )

    # 15. A reintroduced retired LAT-1 scaffold file is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/lat1_retrieval_scaling_report.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_rejects(
            "a reintroduced retired LAT-1 scaffold file is rejected",
            check_no_live_lat1_scaffold,
            "retired mixed method/template scaffold reintroduced",
        )
    ROOT = real_root

    # 16. A current document with an active reference to the retired LAT-1 scaffold path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_lat1.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [old report](docs/evaluation/lat1_retrieval_scaling_report.md).\n",
        )
        check_rejects(
            "a current document referencing the retired LAT-1 scaffold path is rejected",
            check_no_live_lat1_scaffold,
            "active reference to retired docs/evaluation/lat1_retrieval_scaling_report.md",
        )
    ROOT = real_root

    # 17. A frozen/historical_after_merge document's own retired-path mention is
    # REJECTED when it has no exact line-allowlist entry: this guard does not
    # fall back to a generic whole-document status bypass the way the docs/mvp/
    # guard does, so status alone cannot hide a stale reference.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_lat1_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            "This slice added docs/evaluation/lat1_retrieval_scaling_report.md.\n",
        )
        check_rejects(
            "a frozen-status document's retired-LAT1-path mention is rejected without an exact line allowance",
            check_no_live_lat1_scaffold,
            "active reference to retired docs/evaluation/lat1_retrieval_scaling_report.md",
        )
    ROOT = real_root

    # 17a. A bare relative filename reference (no docs/evaluation/ prefix) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/example_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [old report](lat1_retrieval_scaling_report.md) for background.\n",
        )
        check_rejects(
            "a bare relative filename reference to the retired LAT-1 scaffold is rejected",
            check_no_live_lat1_scaffold,
            "active reference to retired docs/evaluation/lat1_retrieval_scaling_report.md",
        )
    ROOT = real_root

    # 17b. A stable underscore stem reference without a .md extension is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_stem.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See the historical lat1_retrieval_scaling_report discussion for context.\n",
        )
        check_rejects(
            "a stable underscore-stem reference (no .md extension) is rejected",
            check_no_live_lat1_scaffold,
            "active reference to retired docs/evaluation/lat1_retrieval_scaling_report.md",
        )
    ROOT = real_root

    # 17c. An unallowlisted occurrence in the active cutover-rules planning file is
    # rejected: that file is no longer whole-file allowlisted, only its one
    # exact reviewed override-key line is.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/documentation-cutover-rules.yaml",
            "path_overrides:\n"
            "  docs/evaluation/lat1_retrieval_scaling_report.md:\n"
            "    disposition: split\n"
            "# stray unreviewed mention: lat1_retrieval_scaling_report\n",
        )
        check_rejects(
            "an unallowlisted occurrence in the active cutover-rules file is rejected",
            check_no_live_lat1_scaffold,
            "active reference to retired docs/evaluation/lat1_retrieval_scaling_report.md",
        )
    ROOT = real_root

    # 17d. The exact reviewed frozen source snapshot is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/lat1_latency_measurement_completion_report-source.txt",
            "- `docs/evaluation/lat1_retrieval_scaling_report.md`: report template with\n",
        )
        check_silent(
            "the exact reviewed frozen source snapshot is allowed",
            check_no_live_lat1_scaffold,
        )
    ROOT = real_root

    # 17e. The exact receipt and guard-implementation self-reference occurrences
    # are allowed (real repository, no synthetic fixture needed).
    check_silent(
        "real repository: receipt and guard-implementation occurrences are allowed",
        check_no_live_lat1_scaffold,
    )

    # 18. The real repository's LAT-1 method/template split is structurally valid.
    check_silent(
        "real repository: LAT-1 evaluation method/template split is valid",
        check_lat1_evaluation_split,
    )

    # 19. A template missing the canonical `template` doc type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/lat1-retrieval-scaling.md",
            "---\nrelaylm_doc_type: evaluation_method\nrelaylm_authority: lat1_method\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/templates/evaluation/lat1-retrieval-scaling-report.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_authority: lat1_method\n---\n\n"
            "This is not evidence. Route completed runs to docs/evidence/evaluations/.\n",
        )
        check_rejects(
            "a drifted LAT-1 template doc type is rejected",
            check_lat1_evaluation_split,
            "relaylm_doc_type must be 'template'",
        )
    ROOT = real_root

    # 20. Shared method/template authority is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/lat1-retrieval-scaling.md",
            "---\nrelaylm_doc_type: evaluation_method\nrelaylm_authority: shared_key\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/templates/evaluation/lat1-retrieval-scaling-report.md",
            "---\nrelaylm_doc_type: template\nrelaylm_authority: shared_key\n---\n\n"
            "This is not evidence. Route completed runs to docs/evidence/evaluations/.\n",
        )
        check_rejects(
            "a shared method/template authority is rejected",
            check_lat1_evaluation_split,
            "must not share one primary authority",
        )
    ROOT = real_root

    # 21. An empty target_records list in the cutover rules is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/documentation-cutover-rules.yaml",
            "path_overrides:\n  docs/example/old.md:\n    disposition: split\n    target_records: []\n",
        )
        check_rejects(
            "an empty target_records list is rejected",
            check_cutover_rule_target_types,
            "must be a non-empty list",
        )
    ROOT = real_root

    # 22. A target_records entry mixing legacy target_doc_type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/documentation-cutover-rules.yaml",
            "path_overrides:\n"
            "  docs/example/old.md:\n"
            "    disposition: split\n"
            "    target_doc_type: evidence\n"
            "    target_records:\n"
            "      - target_path: docs/example/new.md\n"
            "        target_doc_type: evidence\n",
        )
        check_rejects(
            "target_records mixed with legacy target_doc_type is rejected",
            check_cutover_rule_target_types,
            "mixes target_records with legacy",
        )
    ROOT = real_root

    # 23. Duplicate target_path entries with conflicting document types are rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/documentation-cutover-rules.yaml",
            "path_overrides:\n"
            "  docs/example/old.md:\n"
            "    disposition: split\n"
            "    target_records:\n"
            "      - target_path: docs/example/new.md\n"
            "        target_doc_type: evidence\n"
            "      - target_path: docs/example/new.md\n"
            "        target_doc_type: template\n",
        )
        check_rejects(
            "duplicate target_path entries with conflicting document types are rejected",
            check_cutover_rule_target_types,
            "conflicting document types",
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # check_lat1_evaluation_evidence_records: a fully valid synthetic
    # completed record, then bounded mutations proving each fail-closed
    # requirement.
    # ------------------------------------------------------------------
    _LAT1_EVIDENCE_FRONT_MATTER = (
        "---\n"
        "relaylm_doc_type: {doc_type}\n"
        "relaylm_authority: {authority}\n"
        "relaylm_status: {status}\n"
        "relaylm_volatility: low\n"
        "relaylm_owner: {owner}\n"
        "relaylm_update_trigger:\n"
        "  - metadata or link repair only\n"
        "relaylm_not_authoritative_for:\n"
        "  - current runtime implementation status\n"
        "relaylm_current_status_source: ../../PROJECT_STATUS.md\n"
        "relaylm_source_commit: {source_commit}\n"
        "relaylm_recorded_on: {recorded_on}\n"
        "---\n\n"
    )
    _LAT1_EVIDENCE_BODY = (
        "# LAT-1 Retrieval Scaling Report\n\n"
        "## Execution environment\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        "| Date | {env_date} |\n"
        "| Machine / CPU | {machine} |\n"
        "| Filesystem (e.g. local SSD, network mount, container overlay) | local NVMe SSD |\n"
        "| Python version | 3.11.9 |\n"
        "| Exact RelayLM commit SHA | {env_commit} |\n"
        "| Branch or tag (optional context only) | main |\n"
        "| `--repeat` | {repeat_value} |\n"
        "| `--max-candidates` (bench flag; mirrors `config.memory.candidate_limit`) | {max_candidates} |\n"
        "| Concurrent load on the machine during the run | idle |\n\n"
        "## Results by store size (N)\n\n"
        "| N (store size) | query_count | repeat | p50_ms | p95_ms | avg_selected_count |\n"
        "|---|---|---|---|---|---|\n"
        "{result_rows}"
        "\n## Linear scaling coefficient estimate\n\n"
        "- Estimated slope (ms per additional 1000 store pages): 0.5\n"
        "- Does `p50_ms`/`p95_ms` continue increasing beyond the internal discovery\n"
        "  cap, or plateau? Plateaus above N=2000.\n"
        "- If it plateaus, at approximately which N does it plateau? 2000\n\n"
        "## Felt limit N judgment\n\n"
        "- Felt limit N: 2000\n"
        "- Basis for this judgment: retrieval_ms exceeds 10% of the response budget at N=2000\n"
        "- Implication for candidate-limit (K), ANN adoption, or Secondary MEM\n"
        "  integration priority (design decision only; not made in this report):\n"
        "  consider ANN adoption above N=2000\n"
    )
    _LAT1_EVIDENCE_VALID_ROWS = (
        "| 100 | 20 | 5 | 5.0 | 6.0 | 10 |\n"
        "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
        "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
        "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
    )

    def _lat1_evidence_write(
        base: Path,
        filename: str = "lat1-retrieval-scaling-2026-07-16-120000Z-abc1234a.md",
        doc_type: str = "evidence",
        authority: str = "lat1_retrieval_scaling_run_2026-07-16_abc1234a",
        status: str = "frozen",
        owner: str = "evaluation",
        source_commit: str = "abc1234a" + "0" * 32,
        recorded_on: str = "2026-07-16",
        machine: str = "Ryzen 9 5900X",
        repeat_value: str = "5",
        max_candidates: str = "128",
        result_rows: str = _LAT1_EVIDENCE_VALID_ROWS,
        env_date: str | None = None,
        env_commit: str | None = None,
        extra_body: str = "",
    ) -> None:
        content = _LAT1_EVIDENCE_FRONT_MATTER.format(
            doc_type=doc_type,
            authority=authority,
            status=status,
            owner=owner,
            source_commit=source_commit,
            recorded_on=recorded_on,
        ) + _LAT1_EVIDENCE_BODY.format(
            env_date=env_date if env_date is not None else recorded_on,
            machine=machine,
            env_commit=env_commit if env_commit is not None else source_commit,
            repeat_value=repeat_value,
            max_candidates=max_candidates,
            result_rows=result_rows,
        ) + extra_body
        _mvp_write(base, f"{LAT1_EVIDENCE_DIR}/{filename}", content)

    # 24. A fully valid completed record is accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base)
        check_silent(
            "a fully valid completed LAT-1 evidence record is accepted",
            check_lat1_evaluation_evidence_records,
        )
    ROOT = real_root

    # 25. Retained placeholders are rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, machine="`<placeholder>`")
        check_rejects(
            "a record with a retained placeholder is rejected",
            check_lat1_evaluation_evidence_records,
            "unfilled placeholder marker",
        )
    ROOT = real_root

    # 26. A missing/invalid exact commit SHA is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, source_commit="not-a-real-sha")
        check_rejects(
            "a record with an invalid commit SHA is rejected",
            check_lat1_evaluation_evidence_records,
            "must be a full 40-character lowercase",
        )
    ROOT = real_root

    # 27. Branch-only provenance (no exact commit SHA at all) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, source_commit="main")
        check_rejects(
            "branch-only provenance without an exact commit SHA is rejected",
            check_lat1_evaluation_evidence_records,
            "must be a full 40-character lowercase",
        )
    ROOT = real_root

    # 28. Missing environment values are rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, machine="-")
        check_rejects(
            "a record with a missing execution-environment value is rejected",
            check_lat1_evaluation_evidence_records,
            "execution environment field",
        )
    ROOT = real_root

    # 29. Missing N rows are rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a record missing an N=5000 results row is rejected",
            check_lat1_evaluation_evidence_records,
            "missing results row for N=5000",
        )
    ROOT = real_root

    # 30. Non-numeric measurements are rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | not-a-number | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a record with a non-numeric measurement is rejected",
            check_lat1_evaluation_evidence_records,
            "is not numeric",
        )
    ROOT = real_root

    # 31. p95_ms < p50_ms is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 9.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "p95_ms < p50_ms is rejected",
            check_lat1_evaluation_evidence_records,
            "p95_ms must be >= p50_ms",
        )
    ROOT = real_root

    # 32. The wrong document type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, doc_type="evaluation_record")
        check_rejects(
            "the retired evaluation_record document type is rejected",
            check_lat1_evaluation_evidence_records,
            "relaylm_doc_type must be 'evidence'",
        )
    ROOT = real_root

    # 33. A filename/date mismatch is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            filename="lat1-retrieval-scaling-2026-07-17-120000Z-abc1234a.md",
        )
        check_rejects(
            "a filename date not matching relaylm_recorded_on is rejected",
            check_lat1_evaluation_evidence_records,
            "must all match exactly",
        )
    ROOT = real_root

    # 34. A same-day, date-only, collision-prone filename is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, filename="lat1-retrieval-scaling-2026-07-16.md")
        check_rejects(
            "a same-day date-only collision-prone filename is rejected",
            check_lat1_evaluation_evidence_records,
            "does not match the deterministic collision-safe",
        )
    ROOT = real_root

    # 35. An impossible metadata date (relaylm_recorded_on) is rejected without crashing.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, recorded_on="2026-99-99")
        check_rejects(
            "an impossible relaylm_recorded_on metadata date is rejected",
            check_lat1_evaluation_evidence_records,
            "front matter is invalid or contains an impossible date",
        )
    ROOT = real_root

    # 36. An impossible filename date is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, filename="lat1-retrieval-scaling-2026-02-30-120000Z-abc1234a.md")
        check_rejects(
            "an impossible filename date is rejected",
            check_lat1_evaluation_evidence_records,
            "is not a real calendar date",
        )
    ROOT = real_root

    # 37. An impossible filename UTC time is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, filename="lat1-retrieval-scaling-2026-07-16-246000Z-abc1234a.md")
        check_rejects(
            "an impossible filename UTC time is rejected",
            check_lat1_evaluation_evidence_records,
            "is not a valid UTC HHMMSS time",
        )
    ROOT = real_root

    # 38. An execution-environment Date mismatch (filename/recorded_on agree, env differs) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, env_date="2026-07-17")
        check_rejects(
            "an execution-environment Date mismatch is rejected",
            check_lat1_evaluation_evidence_records,
            "must all match exactly",
        )
    ROOT = real_root

    # 39. An execution-environment commit SHA mismatch (valid SHA, but not the recorded one) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, env_commit="b" * 40)
        check_rejects(
            "an execution-environment commit SHA mismatch is rejected",
            check_lat1_evaluation_evidence_records,
            "does not match relaylm_source_commit",
        )
    ROOT = real_root

    # 39a. A branch name in the execution-environment commit SHA cell is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, env_commit="main")
        check_rejects(
            "a branch name in the execution-environment commit SHA cell is rejected",
            check_lat1_evaluation_evidence_records,
            "must be a full 40-character lowercase commit SHA, not a branch name",
        )
    ROOT = real_root

    # 39b. A filename short-commit not matching the execution-environment SHA is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            filename="lat1-retrieval-scaling-2026-07-16-120000Z-bbbbbbbb.md",
            env_commit="abc1234a" + "0" * 32,
            source_commit="abc1234a" + "0" * 32,
        )
        check_rejects(
            "a filename short-commit not matching the execution-environment SHA is rejected",
            check_lat1_evaluation_evidence_records,
            "does not match the filename short-commit",
        )
    ROOT = real_root

    # 40. NaN is rejected as a non-finite measurement.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | NaN | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "NaN is rejected as a non-finite measurement",
            check_lat1_evaluation_evidence_records,
            "must be a finite number",
        )
    ROOT = real_root

    # 41. Infinity is rejected as a non-finite measurement.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 5.0 | Infinity | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "Infinity is rejected as a non-finite measurement",
            check_lat1_evaluation_evidence_records,
            "must be a finite number",
        )
    ROOT = real_root

    # 42. A zero-valued integer field (query_count) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 0 | 5 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a zero-valued integer field is rejected",
            check_lat1_evaluation_evidence_records,
            "must be a positive integer",
        )
    ROOT = real_root

    # 43. A decimal value in an integer field (repeat) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5.5 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a decimal value in an integer field is rejected",
            check_lat1_evaluation_evidence_records,
            "must be a positive integer",
        )
    ROOT = real_root

    # 44. A per-row repeat value not matching execution environment --repeat is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 7 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a per-row repeat mismatched against --repeat is rejected",
            check_lat1_evaluation_evidence_records,
            "does not match execution environment --repeat",
        )
    ROOT = real_root

    # 45. A duplicate N row is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 5.0 | 6.0 | 10 |\n"
                "| 100 | 20 | 5 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a duplicate N row is rejected",
            check_lat1_evaluation_evidence_records,
            "duplicate results row for N='100'",
        )
    ROOT = real_root

    # 46. An unexpected extra N row is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 5.0 | 6.0 | 10 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
                "| 9999 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "an unexpected extra N row is rejected",
            check_lat1_evaluation_evidence_records,
            "unexpected results row for N='9999'",
        )
    ROOT = real_root

    # 47. A malformed table row (wrong cell count) is rejected, not silently skipped.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            result_rows=(
                "| 100 | 20 | 5 | 5.0 | 6.0 |\n"
                "| 500 | 20 | 5 | 8.0 | 9.0 | 12 |\n"
                "| 2000 | 20 | 5 | 15.0 | 18.0 | 12 |\n"
                "| 5000 | 20 | 5 | 16.0 | 19.0 | 12 |\n"
            ),
        )
        check_rejects(
            "a malformed table row with the wrong cell count is rejected",
            check_lat1_evaluation_evidence_records,
            "has 5 cell(s), expected 6",
        )
    ROOT = real_root

    # 48. A duplicate execution-environment field is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(base, extra_body="")
        # Inject a duplicate "Date" row directly, since the helper always
        # writes a well-formed single-Date table.
        target = base / LAT1_EVIDENCE_DIR / "lat1-retrieval-scaling-2026-07-16-120000Z-abc1234a.md"
        text = target.read_text(encoding="utf-8")
        text = text.replace(
            "| Date | 2026-07-16 |\n",
            "| Date | 2026-07-16 |\n| Date | 2026-07-16 |\n",
            1,
        )
        target.write_text(text, encoding="utf-8")
        check_rejects(
            "a duplicate execution-environment field is rejected",
            check_lat1_evaluation_evidence_records,
            "duplicate execution-environment field",
        )
    ROOT = real_root

    # 49. Two otherwise-valid records sharing one relaylm_authority are both rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _lat1_evidence_write(
            base,
            filename="lat1-retrieval-scaling-2026-07-16-120000Z-abc1234a.md",
            authority="lat1_retrieval_scaling_run_shared",
        )
        _lat1_evidence_write(
            base,
            filename="lat1-retrieval-scaling-2026-07-17-130000Z-def5678a.md",
            authority="lat1_retrieval_scaling_run_shared",
            source_commit="def5678a" + "0" * 32,
            recorded_on="2026-07-17",
        )
        check_rejects(
            "a duplicate authority reused across two completed records is rejected",
            check_lat1_evaluation_evidence_records,
            "is not unique across completed LAT-1 evidence records",
        )
    ROOT = real_root

    # 50. The real repository has no live reference to the retired E1 local
    # runtime evaluation architecture path.
    check_silent(
        "real repository: no active reference to the retired E1 local runtime evaluation path",
        check_no_live_e1_local_runtime_architecture_path,
    )

    # 51. A reintroduced retired E1 local runtime evaluation file is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a reintroduced retired E1 local runtime evaluation file is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "retired dated evaluation record reintroduced",
        )
    ROOT = real_root

    # 52. A current document with the full repository-root-qualified old path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_e1.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [old record](docs/architecture/e1_local_runtime_evaluation_2026_06_25.md).\n",
        )
        check_rejects(
            "a current document with the full root-qualified old path is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "active reference to retired docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
        )
    ROOT = real_root

    # 53. A same-directory bare-filename reference from another file under
    # docs/architecture/ resolves to the retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/architecture/example_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [old record](e1_local_runtime_evaluation_2026_06_25.md) for background.\n",
        )
        check_rejects(
            "a same-directory bare-filename reference resolving to the retired path is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "active reference to retired docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
        )
    ROOT = real_root

    # 54. A "../architecture/..." reference from a sibling directory of
    # docs/architecture/ resolves to the retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/example_other.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [old record](../architecture/e1_local_runtime_evaluation_2026_06_25.md).\n",
        )
        check_rejects(
            "a ../architecture/... reference resolving to the retired path is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "active reference to retired docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
        )
    ROOT = real_root

    # 55. A "../../architecture/..." Markdown link reference from
    # docs/evidence/implementation/, in a file that is NOT one of the two
    # exact allowlisted snapshots, resolves to the retired path and is
    # rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_other_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n---\n\n"
            "See [old record](../../architecture/e1_local_runtime_evaluation_2026_06_25.md).\n",
        )
        check_rejects(
            "a ../../architecture/... reference in a non-snapshot file is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "active reference to retired docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
        )
    ROOT = real_root

    # 56. A relaylm_related_authority front-matter entry that resolves to the
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_related_authority.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            "  - ../../architecture/e1_local_runtime_evaluation_2026_06_25.md\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_authority entry resolving to the retired path is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 57. A Markdown link with a trailing anchor still resolves (ignoring the
    # anchor) to the retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_anchor.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n---\n\n"
            "See [findings](../../architecture/e1_local_runtime_evaluation_2026_06_25.md#observed-findings).\n",
        )
        check_rejects(
            "a Markdown link with a trailing anchor resolving to the retired path is rejected",
            check_no_live_e1_local_runtime_architecture_path,
            "markdown link target",
        )
    ROOT = real_root

    # 58. A frozen/historical_after_merge document's own retired-path mention is
    # REJECTED when it has no exact line-allowlist entry: this guard does not
    # fall back to a generic whole-document status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_e1_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            "This slice added docs/architecture/e1_local_runtime_evaluation_2026_06_25.md.\n",
        )
        check_rejects(
            "a frozen-status document's retired-E1-path mention is rejected without an exact line allowance",
            check_no_live_e1_local_runtime_architecture_path,
            "active reference to retired docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
        )
    ROOT = real_root

    # 59. The canonical migrated document's own filename does not self-trigger the guard.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n\nBody.\n",
        )
        check_silent(
            "the canonical migrated document at its new path does not self-trigger the guard",
            check_no_live_e1_local_runtime_architecture_path,
        )
    ROOT = real_root

    # 60. A repository-root-qualified Markdown link to the canonical target is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/example_root_qualified_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "See [record](docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md).\n",
        )
        check_silent(
            "a repository-root-qualified link to the canonical target is allowed",
            check_no_live_e1_local_runtime_architecture_path,
        )
    ROOT = real_root

    # 61. A relative Markdown link to the canonical target, from a sibling
    # document in the same directory, is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/evidence/evaluations/example_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            "- [record](e1_local_runtime_evaluation_2026_06_25.md)\n",
        )
        check_silent(
            "a relative link to the canonical target from a sibling document is allowed",
            check_no_live_e1_local_runtime_architecture_path,
        )
    ROOT = real_root

    # 62. The exact reviewed frozen source snapshots are allowed ONLY because
    # of the exact-path allowlist: the identical historical relative-form
    # relaylm_related_authority entry is first proven to be REJECTED in a
    # non-allowlisted file (proving the resolver and rejection path actually
    # fire for this exact content), then proven SILENT only at each of the
    # two exact allowlisted snapshot paths.
    snapshot_related_authority = (
        "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n"
        "relaylm_related_authority:\n"
        "  - ../../architecture/e1_evaluation_consolidation.md\n"
        "  - ../../architecture/e1_local_runtime_evaluation_2026_06_25.md\n"
        "---\n\nBody.\n"
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_not_allowlisted_report.md",
            snapshot_related_authority,
        )
        check_rejects(
            "the exact historical snapshot content is rejected in a non-allowlisted file",
            check_no_live_e1_local_runtime_architecture_path,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/e1_completion_report-source.txt",
            snapshot_related_authority,
        )
        _mvp_write(
            base,
            "docs/evidence/implementation/e1r2_completion_report-source.txt",
            snapshot_related_authority,
        )
        check_silent(
            "the identical content is silent only at the two exact allowlisted snapshot paths",
            check_no_live_e1_local_runtime_architecture_path,
        )
    ROOT = real_root

    # Lookups for the five retired paths, resolved dynamically from the
    # module-level constant rather than spelled out as source-code literals:
    # every full retired-path literal in this file's own source text is now
    # itself subject to Pass 1 (see the self-file exact-line allowance
    # correction above), so a hardcoded literal in a self-test fixture would
    # make this file fail its own audit. Each lookup marker below is a
    # substring shorter than the full retired path, so it is never itself
    # matched by MOBILE_DOGFOOD_REFERENCE_PATTERN.
    mobile_dogfood_entry_retired = next(p for p in MOBILE_DOGFOOD_RETIRED_PATHS if p.startswith("docs/tools/"))
    mobile_dogfood_observation_retired = next(
        p for p in MOBILE_DOGFOOD_RETIRED_PATHS if p.endswith("observation_runbook.md")
    )
    mobile_dogfood_summary_retired = next(
        p for p in MOBILE_DOGFOOD_RETIRED_PATHS if p.endswith("summary_report_template.md")
    )
    mobile_dogfood_daily_retired = next(
        p for p in MOBILE_DOGFOOD_RETIRED_PATHS if p.endswith("daily_note_template.md")
    )
    mobile_dogfood_weekly_retired = next(
        p for p in MOBILE_DOGFOOD_RETIRED_PATHS if p.endswith("weekly_review_template.md")
    )

    # 63. The real repository has no live reference to any retired
    # mobile-dogfood family path (Cutover 1C-41). Since the self-file
    # whole-file exemption was removed, this also proves that this file's
    # own MOBILE_DOGFOOD_RETIRED_TO_CANONICAL constant entries and every
    # self-test fixture below are silent under the guard's real-repository
    # scan -- not merely under a synthetic tree.
    check_silent(
        "real repository: no active reference to any retired mobile-dogfood path",
        check_no_live_mobile_dogfood_retired_paths,
    )

    # 64. Each of the five retired mobile-dogfood files being reintroduced is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        for retired_path in MOBILE_DOGFOOD_RETIRED_PATHS:
            _mvp_write(
                base,
                retired_path,
                "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
            )
        reintroduced_errors: list[str] = []
        check_no_live_mobile_dogfood_retired_paths(reintroduced_errors)
        missing = [
            retired_path
            for retired_path in MOBILE_DOGFOOD_RETIRED_PATHS
            if not any(retired_path in error and "reintroduced" in error for error in reintroduced_errors)
        ]
        results.append(
            (
                "each of the five reintroduced retired mobile-dogfood files is rejected",
                not missing,
                "" if not missing else f"missing rejection for: {missing!r}",
            )
        )
    ROOT = real_root

    # 65. A root-qualified Markdown link to the retired P0 entry path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_mobile_dogfood_root_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old entry]({mobile_dogfood_entry_retired}).\n",
        )
        check_rejects(
            "a root-qualified link to the retired P0 mobile-dogfood entry path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
        )
    ROOT = real_root

    # 66. A same-directory bare-filename reference to a retired path (from
    # another file under docs/evaluation/) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/example_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old runbook]({mobile_dogfood_observation_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a same-directory bare-filename reference resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_observation_retired}",
        )
    ROOT = real_root

    # 67. A "../evaluation/templates/..." reference from a sibling directory
    # resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/tools/example_other.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old daily note](../evaluation/templates/{mobile_dogfood_daily_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../evaluation/templates/... reference resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_daily_retired}",
        )
    ROOT = real_root

    # 68. A "../../evaluation/..." reference resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/templates/evaluation/example_other_template.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old summary](../../evaluation/{mobile_dogfood_summary_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../../evaluation/... reference resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_summary_retired}",
        )
    ROOT = real_root

    # 69. A Markdown link with a trailing anchor still resolves (ignoring the
    # anchor) to a retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_anchor_mobile_dogfood.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old runbook]({mobile_dogfood_observation_retired}#daily-review).\n",
        )
        check_rejects(
            "a Markdown link with an anchor resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "markdown link target",
        )
    ROOT = real_root

    # 70. A relaylm_related_authority front-matter entry resolving to a
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/example_related_authority.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {mobile_dogfood_observation_retired.rsplit('/', 1)[-1]}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_authority entry resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 71. A frozen/historical_after_merge document's own unallowlisted mention
    # of a retired path is REJECTED: this guard does not fall back to a
    # generic whole-document status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_mobile_dogfood_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            f"This slice added {mobile_dogfood_entry_retired}.\n",
        )
        check_rejects(
            "a frozen-status document's unallowlisted retired mobile-dogfood mention is rejected without an exact line allowance",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
        )
    ROOT = real_root

    # 72. Root-qualified Markdown links to all five canonical mobile-dogfood
    # targets are allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        for canonical_path in MOBILE_DOGFOOD_CANONICAL_PATHS:
            _mvp_write(
                base,
                canonical_path,
                "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\nBody.\n",
            )
        _mvp_write(
            base,
            "docs/example_root_qualified_mobile_dogfood_links.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            + "\n".join(
                f"- [target]({canonical_path})" for canonical_path in sorted(MOBILE_DOGFOOD_CANONICAL_PATHS)
            )
            + "\n",
        )
        check_silent(
            "root-qualified links to all five canonical mobile-dogfood targets are allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 73. A relative link to a canonical target from a sibling document in the
    # same directory is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: evaluation_method\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/evaluation/example_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            "- [method](mobile-dogfood-observation.md)\n",
        )
        check_silent(
            "a relative link to the canonical mobile-dogfood-observation.md target is allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 74. The exact reviewed documentation-cutover-rules.yaml path_overrides
    # key line is allowed ONLY because of the exact-line allowlist: the
    # identical literal is first proven REJECTED in a non-allowlisted file,
    # then proven SILENT only at the one exact allowlisted path.
    override_key_line = f"  {mobile_dogfood_entry_retired}:\n    disposition: moved\n"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", override_key_line)
        check_rejects(
            "the exact cutover-rules.yaml override key literal is rejected in a non-allowlisted file",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/documentation-cutover-rules.yaml", override_key_line)
        check_silent(
            "the identical override key literal is silent only at the exact allowlisted cutover-rules.yaml path",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 75. Zero duplicate live copies: a retired path coexisting with its own
    # already-created canonical target is still rejected for the retired path.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            mobile_dogfood_entry_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: target\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/mobile-dogfood-entry.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_rejects(
            "a retired file coexisting with its own canonical target (duplicate live copy) is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "retired mobile-dogfood family path reintroduced",
        )
    ROOT = real_root

    # 76. A mobile-dogfood template synthetically typed evaluation_record
    # (the retired legacy type) is rejected: reject-then-allow pairing proving
    # check_mobile_dogfood_family_types actually fires.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/templates/evaluation/mobile-dogfood-summary-report.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_status: target\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/templates/evaluation/mobile-dogfood-daily-note.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/templates/evaluation/mobile-dogfood-weekly-review.md",
            "---\nrelaylm_doc_type: evaluation_record\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/evaluation/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: evaluation_method\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/mobile-dogfood-entry.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_rejects(
            "a mobile-dogfood template synthetically typed evaluation_record is rejected",
            check_mobile_dogfood_family_types,
            "must declare relaylm_doc_type: template, not 'evaluation_record'",
        )
    ROOT = real_root

    # 77. The real repository's mobile-dogfood family declares the correct
    # canonical types: templates are `template` (not the retired
    # `evaluation_record`), the observation document is `evaluation_method`,
    # and the P0 entry is `operations`.
    check_silent(
        "the real repository's mobile-dogfood family declares the correct canonical types",
        check_mobile_dogfood_family_types,
    )

    # 78. relaylm_current_status_source scalar resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/example_status_source.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            f"relaylm_current_status_source: {mobile_dogfood_entry_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_current_status_source scalar resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_current_status_source entry",
        )
    ROOT = real_root

    # 79. relaylm_related_contracts list entry resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/contracts/example_contract.md",
            "---\nrelaylm_doc_type: contract\nrelaylm_status: current\n"
            "relaylm_related_contracts:\n"
            f"  - {mobile_dogfood_summary_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_contracts entry resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_related_contracts entry",
        )
    ROOT = real_root

    # 80. relaylm_related_decisions list entry resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/adr/example_decision.md",
            "---\nrelaylm_doc_type: adr\nrelaylm_status: target\n"
            "relaylm_related_decisions:\n"
            f"  - {mobile_dogfood_daily_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_decisions entry resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_related_decisions entry",
        )
    ROOT = real_root

    # 81. relaylm_decision_source scalar resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/adr/example_decision_source.md",
            "---\nrelaylm_doc_type: adr\nrelaylm_status: target\n"
            f"relaylm_decision_source: {mobile_dogfood_weekly_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_decision_source scalar resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_decision_source entry",
        )
    ROOT = real_root

    # 82. relaylm_code_sources list entry resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/architecture/example_code_sources.md",
            "---\nrelaylm_doc_type: subsystem_architecture\nrelaylm_status: current\n"
            "relaylm_code_sources:\n"
            f"  - {mobile_dogfood_observation_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_code_sources entry resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_code_sources entry",
        )
    ROOT = real_root

    # 83. relaylm_verified_by list entry resolving to a retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/architecture/example_verified_by.md",
            "---\nrelaylm_doc_type: subsystem_architecture\nrelaylm_status: current\n"
            "relaylm_verified_by:\n"
            f"  - {mobile_dogfood_entry_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_verified_by entry resolving to a retired mobile-dogfood path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_verified_by entry",
        )
    ROOT = real_root

    # 84. A supported path-bearing metadata value with a URL fragment still
    # resolves (ignoring the fragment) to a retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/architecture/example_fragment.md",
            "---\nrelaylm_doc_type: subsystem_architecture\nrelaylm_status: current\n"
            "relaylm_verified_by:\n"
            f"  - {mobile_dogfood_observation_retired}#some-anchor\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_verified_by entry with a URL fragment still resolving to a retired path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_verified_by entry",
        )
    ROOT = real_root

    # 85. A frozen/historical document's own stale relative metadata path is
    # REJECTED: proves the generic front-matter path check does not fall
    # back to a whole-document status bypass either.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_frozen_metadata.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n"
            "relaylm_related_authority:\n"
            f"  - ../../{mobile_dogfood_weekly_retired.split('docs/', 1)[1]}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a frozen document's stale relaylm_related_authority path is rejected without a status bypass",
            check_no_live_mobile_dogfood_retired_paths,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 86. A synthetic copy of this guard's own self-file containing a stale
    # path reintroduced into a REQUIRED_METADATA_PATHS-shaped tuple is
    # REJECTED: proves removing the whole-file exemption actually catches a
    # regression in this file's own live path-bound consumers.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            MOBILE_DOGFOOD_SELF_FILE,
            "REQUIRED_METADATA_PATHS = (\n"
            f'    "{mobile_dogfood_entry_retired}",\n'
            ")\n",
        )
        check_rejects(
            "a synthetic self-file REQUIRED_METADATA_PATHS entry reintroducing a retired path is rejected",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
        )
    ROOT = real_root

    # 87. The same synthetic self-file, with REQUIRED_METADATA_PATHS instead
    # using the canonical target, is silent -- the reject-then-allow pairing
    # proving the self-file scan is genuinely exercised, not merely absent.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            MOBILE_DOGFOOD_SELF_FILE,
            "REQUIRED_METADATA_PATHS = (\n"
            f'    "{MOBILE_DOGFOOD_RETIRED_TO_CANONICAL[mobile_dogfood_entry_retired]}",\n'
            ")\n",
        )
        check_silent(
            "a synthetic self-file REQUIRED_METADATA_PATHS entry using the canonical target is silent",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 88. A retired literal appearing in an UNRELATED, non-allowlisted Python
    # constant inside a synthetic self-file is REJECTED: the exact-line
    # allowance is scoped to the MOBILE_DOGFOOD_RETIRED_TO_CANONICAL dict's
    # own lines specifically, not to "any constant in this file."
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            MOBILE_DOGFOOD_SELF_FILE,
            "SOME_UNRELATED_CONSTANT = (\n"
            f'    "{mobile_dogfood_entry_retired}",\n'
            ")\n",
        )
        check_rejects(
            "a retired literal in an unrelated, non-allowlisted Python constant is rejected in the self-file",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
        )
    ROOT = real_root

    # 89. The MOBILE_DOGFOOD_RETIRED_TO_CANONICAL constant's own dict-key
    # entries, in isolation, remain narrowly allowed in the self-file --
    # paired against 88 above to prove the allowance is scoped to exactly
    # these lines, not a broad substring or the whole file.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            MOBILE_DOGFOOD_SELF_FILE,
            "MOBILE_DOGFOOD_RETIRED_TO_CANONICAL: dict[str, str] = {\n"
            + "".join(
                f'    "{retired_path}": "{canonical_path}",\n'
                for retired_path, canonical_path in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL.items()
            )
            + "}\n",
        )
        check_silent(
            "the retired-path mapping constant's own dict-key entries remain allowed in the self-file",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 90. Root-qualified canonical values for every supported path-bearing
    # front-matter key are allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        canonical_list = sorted(MOBILE_DOGFOOD_CANONICAL_PATHS)
        front_matter = (
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            f"relaylm_current_status_source: {canonical_list[0]}\n"
            f"relaylm_decision_source: {canonical_list[1]}\n"
            "relaylm_related_authority:\n"
            f"  - {canonical_list[2]}\n"
            "relaylm_related_contracts:\n"
            f"  - {canonical_list[3]}\n"
            "relaylm_related_decisions:\n"
            f"  - {canonical_list[4]}\n"
            "relaylm_related_proposal:\n"
            f"  - {canonical_list[0]}\n"
            "relaylm_code_sources:\n"
            f"  - {canonical_list[1]}\n"
            "relaylm_verified_by:\n"
            f"  - {canonical_list[2]}\n"
            "---\n\nBody.\n"
        )
        _mvp_write(base, "docs/example_all_keys_root_qualified.md", front_matter)
        check_silent(
            "root-qualified canonical values for every supported path-bearing front-matter key are allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 91. Relative canonical values (from a sibling document in the same
    # directory) for every supported path-bearing front-matter key are
    # allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evaluation/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: evaluation_method\nrelaylm_status: current\n---\n\nBody.\n",
        )
        front_matter = (
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            "relaylm_current_status_source: mobile-dogfood-observation.md\n"
            "relaylm_decision_source: mobile-dogfood-observation.md\n"
            "relaylm_related_authority:\n"
            "  - mobile-dogfood-observation.md\n"
            "relaylm_related_contracts:\n"
            "  - mobile-dogfood-observation.md\n"
            "relaylm_related_decisions:\n"
            "  - mobile-dogfood-observation.md\n"
            "relaylm_related_proposal:\n"
            "  - mobile-dogfood-observation.md\n"
            "relaylm_code_sources:\n"
            "  - mobile-dogfood-observation.md\n"
            "relaylm_verified_by:\n"
            "  - mobile-dogfood-observation.md\n"
            "---\n\nBody.\n"
        )
        _mvp_write(base, "docs/evaluation/example_all_keys_relative.md", front_matter)
        check_silent(
            "relative canonical values for every supported path-bearing front-matter key are allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    failed = [(name, message) for name, ok, message in results if not ok]
    for name, ok, message in results:
        status = "PASS" if ok else "FAIL"
        suffix = f" ({message})" if message and not ok else ""
        print(f"{status}: {name}{suffix}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)}/{len(results)} assertions failed", file=sys.stderr)
        raise SystemExit(1)
    print(f"\nRelayLM docs semantic audit self-test passed: {len(results)} assertions")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    errors: list[str] = []
    checks = (
        check_metadata,
        check_e2_boundary,
        check_client_instruction_boundary,
        check_release_assessment,
        check_completion_report_template,
        check_implementation_evidence_index,
        check_no_live_mvp_tree,
        check_cutover_rule_target_types,
        check_no_live_lat1_scaffold,
        check_lat1_evaluation_split,
        check_lat1_evaluation_evidence_records,
        check_no_live_e1_local_runtime_architecture_path,
        check_no_live_mobile_dogfood_retired_paths,
        check_mobile_dogfood_family_types,
        check_operations_docs,
        check_referenced_repository_paths,
    )
    for check in checks:
        try:
            check(errors)
        except Exception as exc:  # fail closed with the check name for diagnostics
            errors.append(f"{check.__name__}: unexpected error: {exc}")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"error: documentation semantic audit found {len(errors)} issue(s)", file=sys.stderr)
        return 1

    print(
        "RelayLM documentation semantic audit passed "
        f"({len(REQUIRED_METADATA_PATHS)} metadata documents, "
        f"{len(tuple((ROOT / 'docs' / 'evidence' / 'implementation').glob('*_completion_report.md')))} "
        "implementation completion reports)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
