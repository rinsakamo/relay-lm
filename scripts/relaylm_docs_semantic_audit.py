#!/usr/bin/env python3
"""Validate cross-document authority and semantic documentation invariants."""
from __future__ import annotations

import re
import sys
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
    "docs/mvp/README.md",
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

    mvp_index = read_text("docs/mvp/README.md")
    if "IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md" in mvp_index:
        errors.append("docs/mvp/README.md: still links the retired template path")
    if "../templates/implementation-completion-report.md" not in mvp_index:
        errors.append("docs/mvp/README.md: missing link to the canonical completion-report template")


def check_wave8_index(errors: list[str]) -> None:
    index_path = "docs/mvp/README.md"
    index = read_text(index_path)
    reports = sorted((ROOT / "docs" / "mvp" / "wave8").glob("*_completion_report.md"))
    missing = [path.name for path in reports if path.name not in index]
    if missing:
        errors.append(f"{index_path}: unindexed Wave 8 completion reports {missing!r}")


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


def main() -> int:
    errors: list[str] = []
    checks = (
        check_metadata,
        check_e2_boundary,
        check_client_instruction_boundary,
        check_release_assessment,
        check_completion_report_template,
        check_wave8_index,
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
        f"{len(tuple((ROOT / 'docs' / 'mvp' / 'wave8').glob('*_completion_report.md')))} "
        "Wave 8 reports)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
