#!/usr/bin/env python3
"""Validate cross-document authority and semantic documentation invariants."""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

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
    "docs/tools/mobile_dogfood_entry.md",
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
    ("docs", (".md",)),
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

        target_records = entry.get("target_records")
        if isinstance(target_records, list) and target_records:
            for record in target_records:
                if (
                    not isinstance(record, dict)
                    or not isinstance(record.get("target_path"), str)
                    or not isinstance(record.get("target_doc_type"), str)
                ):
                    errors.append(
                        f"{CUTOVER_RULES_PATH}: path_overrides[{old_path!r}].target_records "
                        f"has a malformed entry: {record!r}"
                    )
                    continue
                check_one(old_path, record["target_path"], record["target_doc_type"])
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
LAT1_REFERENCE_PATTERN = re.compile(r"docs/evaluation/lat1_retrieval_scaling_report\.md")
LAT1_METHOD_PATH = "docs/evaluation/lat1-retrieval-scaling.md"
LAT1_TEMPLATE_PATH = "docs/templates/evaluation/lat1-retrieval-scaling-report.md"

# Files whose entire content is historical/migration record-keeping and may
# legitimately name the retired literal without per-line review. This guard's
# own implementation necessarily names the pattern it detects.
LAT1_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        "docs/planning/documentation-cutover-rules.yaml",
        "scripts/relaylm_docs_semantic_audit.py",
    }
)

# Exact, reviewed line-content substrings that are legitimate occurrences of
# the retired LAT-1 scaffold literal inside otherwise-active/current files:
# the planning inventory's own corrected-disposition record, and this
# guard's counterpart existence check naming the path it rejects.
LAT1_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/planning/documentation-architecture-inventory.md": (
        "| `docs/evaluation/lat1_retrieval_scaling_report.md` |",
    ),
    "scripts/relaylm_documentation_current_boundary_smoke.py": (
        '"retired docs/evaluation/lat1_retrieval_scaling_report.md reintroduced "',
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
        if relative_path.startswith("docs/evidence/") and relative_path.endswith("-source.txt"):
            continue
        if _mvp_reference_status_allowlisted(ROOT, relative_path):
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


def check_implementation_evidence_index(errors: list[str]) -> None:
    index_path = "docs/evidence/implementation/README.md"
    index = read_text(index_path)
    reports = sorted((ROOT / "docs" / "evidence" / "implementation").glob("*_completion_report.md"))
    missing = [path.name for path in reports if path.name not in index]
    if missing:
        errors.append(f"{index_path}: unindexed implementation completion reports {missing!r}")


def check_operations_docs(errors: list[str]) -> None:
    mobile_path = "docs/tools/mobile_dogfood_entry.md"
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

    # 17. A frozen historical document's own mention of the retired LAT-1 scaffold
    # path is allowed by its declared front-matter status.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_lat1_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            "This slice added docs/evaluation/lat1_retrieval_scaling_report.md.\n",
        )
        check_silent(
            "a frozen historical document's own retired-LAT1-path mention is allowed",
            check_no_live_lat1_scaffold,
        )
    ROOT = real_root

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
