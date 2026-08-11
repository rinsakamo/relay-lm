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
    "docs/evidence/evaluations/scripts_inventory.md",
    "docs/operations/mobile-dogfood-entry.md",
    "docs/operations/consolidated-smoke-workflow-maintenance.md",
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


MVP_REFERENCE_PATTERN = re.compile(r"docs/mvp(?:/|\b)")

# Files whose *entire* content is historical record-keeping by construction,
# never live current navigation. Kept short and explicit deliberately: this
# is not a place to hide a file merely because it is inconvenient to
# line-allowlist.
MVP_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
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
# code naming the path it rejects and committed self-test fixtures. Any
# occurrence of the pattern NOT covered by a whole-file allowlist entry above
# and NOT matching one of these exact substrings fails closed.
MVP_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "scripts/relaylm_ci_consolidated_smoke_contract.py": (
        'RETIRED_WAVE_REPORT_FAMILY = re.compile(r"^docs/mvp/wave\\d+/")',
        '["docs/mvp/wave3/i4d_completion_report.md"],',
        'fail(f"retired docs/mvp/wave<N>/ selector still present in {workflow}/{group}")',
    ),
    "scripts/relaylm_documentation_current_boundary_smoke.py": (
        "docs/mvp/wave6/e1r2_completion_report.md",
        '"retired docs/mvp/ tree reintroduced (retired by Cutover 1C-38)"',
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
LAT1_METHOD_PATH = "docs/operations/lat1-retrieval-scaling.md"
LAT1_TEMPLATE_PATH = "docs/templates/evaluation/lat1-retrieval-scaling-report.md"

# Files whose entire content is historical record-keeping by construction
# and may legitimately name the retired literal without per-line review.
# Kept short and explicit. This guard's own implementation necessarily names
# the pattern it detects.
LAT1_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
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

    if method_metadata.get("relaylm_doc_type") != "operations":
        errors.append(f"{LAT1_METHOD_PATH}: relaylm_doc_type must be 'operations'")
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

# Files whose entire content is historical record-keeping by construction
# and may legitimately name the retired literal without per-line review.
# This guard's own implementation necessarily names the pattern it detects.
E1_LOCAL_RUNTIME_REFERENCE_ALLOWLISTED_FILES = frozenset(
    {
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
    "docs/evaluation/mobile_dogfood_observation_runbook.md": "docs/operations/mobile-dogfood-observation.md",
    "docs/evaluation/mobile-dogfood-observation.md": "docs/operations/mobile-dogfood-observation.md",
    "docs/evaluation/lat1-retrieval-scaling.md": "docs/operations/lat1-retrieval-scaling.md",
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

# Parses only the first "---"-delimited YAML front-matter block (\A-anchored:
# a later "---" inside the document body is never mistaken for a second
# block).
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

# Files whose entire content is historical record-keeping by construction
# and may legitimately name a retired literal without per-line review.
# Empty: no current file carries this retired literal as whole-file history.
# This guard's own implementation file is deliberately NOT whole-file-exempted
# (see MOBILE_DOGFOOD_SELF_FILE below).
MOBILE_DOGFOOD_REFERENCE_ALLOWLISTED_FILES: frozenset[str] = frozenset()

# Exact, reviewed line-content substrings that are legitimate occurrences of
# a retired literal inside an otherwise-active/current file. Empty: no active
# current file legitimately names one of these retired literals. No generic
# frozen/historical/status bypass and no generic allowance beyond exact
# reviewed lines added here.
MOBILE_DOGFOOD_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "docs/planning/documentation-architecture-inventory.md": tuple(
        f"| `{retired_path}` |"
        for retired_path, canonical_path in MOBILE_DOGFOOD_RETIRED_TO_CANONICAL.items()
        if canonical_path in {
            "docs/operations/lat1-retrieval-scaling.md",
            "docs/operations/mobile-dogfood-observation.md",
        }
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
    method_path = "docs/operations/mobile-dogfood-observation.md"
    method_meta, _ = parse_front_matter(method_path)
    if method_meta.get("relaylm_doc_type") != "operations":
        errors.append(
            f"{method_path}: must declare relaylm_doc_type: operations, "
            f"not {method_meta.get('relaylm_doc_type')!r}"
        )

    lat1_path = "docs/operations/lat1-retrieval-scaling.md"
    lat1_meta, _ = parse_front_matter(lat1_path)
    if lat1_meta.get("relaylm_doc_type") != "operations":
        errors.append(
            f"{lat1_path}: must declare relaylm_doc_type: operations, "
            f"not {lat1_meta.get('relaylm_doc_type')!r}"
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
# Cutover 1C-42: the Twin Extraction offline tooling family (prompt
# specification, execution runbook, and the PR2 review-import-bridge -> CW-A4
# workspace-candidate connective flow) retired from docs/tools/. Three source
# paths move to three canonical docs/operations/ destinations, retyped
# runbook -> operations.
#
# This reuses the same generic helpers the mobile-dogfood guard (Cutover
# 1C-41) already defined -- _mobile_dogfood_resolve(),
# _mobile_dogfood_front_matter_path_values(), _mobile_dogfood_locate(), and
# _mobile_dogfood_scanned_files() are parameterized only by the retired-path
# argument(s) passed to them and this module's shared external-scheme /
# path-bearing-key constants, not by anything mobile-dogfood-specific, so
# this guard calls them directly instead of redefining a third copy of the
# same resolution logic.
#
# Every scanned file is checked, including the three canonical Twin
# Extraction destination documents themselves -- a retired-path reference
# reintroduced inside one of them (e.g. a stale self-link surviving a
# copy/paste) is exactly as much a live violation as one in any other
# document, so there is no canonical-path scan bypass. A link or
# front-matter value that resolves to *another* canonical Twin Extraction
# path remains accepted; only a reference that resolves to one of the three
# *retired* paths is rejected.
#
# Unlike the mobile-dogfood guard, this guard does NOT run its
# repository-root-qualified literal scan (mobile-dogfood's Pass 1, which
# matches a retired path's literal text anywhere in a line, including inside
# backtick code spans) against Markdown/text documents. The twin family's own
# frozen completion report
# (docs/evidence/implementation/twin_extraction_completion_report.md)
# preserves several backtick-literal exact historical records of what source
# PR #503 did (e.g. its "Changed files" bullet list spells out each retired
# doc path verbatim in inline code, not as a Markdown link) that are
# historical record text, not live references, and must not be rewritten or
# allowlisted merely because a literal scan would flag them.
#
# For `.md`/`.txt` documents, detection is restricted to resolved Markdown
# link targets (covering root-qualified, bare same-directory, ./, ../, and
# ../../ spellings, with anchors and query strings stripped) and front-matter
# path-bearing keys -- the two syntactic forms that are actually live,
# followable references in prose. This means the frozen report needs no
# allowance beyond its one live link (repaired in this same cutover; see
# TWIN_EXTRACTION_REFERENCE_ALLOWLISTED_FILES below, which deliberately does
# NOT include the completion report).
#
# For every other scanned file -- i.e. every non-`.md`/`.txt` suffix the
# shared scanner returns, determined by branching on the negative condition
# rather than maintaining a fixed positive suffix allowlist -- neither
# Markdown link syntax nor a YAML front-matter block is the applicable
# reference form, so this guard instead runs the literal
# repository-root-qualified pattern match there. This is what makes this
# guard's own TWIN_EXTRACTION_RETIRED_TO_CANONICAL dict-key entries in its
# own `.py` source (plain Python string literals, not links) and a retired
# literal in a root-scanned file with no dedicated suffix entry such as
# `pyproject.toml` detectable, and is exactly why each legitimate
# occurrence needs its own narrow, exact-stripped-line allowance below
# (matched by exact equality, never substring containment) rather than
# being silently invisible to the guard or wrongly allowed by mere
# containment.
# ---------------------------------------------------------------------------
TWIN_EXTRACTION_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/tools/twin_extraction_prompts.md": "docs/operations/twin-extraction-prompts.md",
    "docs/tools/twin_extraction_runbook.md": "docs/operations/twin-extraction.md",
    "docs/tools/twin_review_to_workspace_candidates.md": "docs/operations/twin-review-to-workspace-candidates.md",
}
TWIN_EXTRACTION_RETIRED_PATHS = tuple(sorted(TWIN_EXTRACTION_RETIRED_TO_CANONICAL))
TWIN_EXTRACTION_CANONICAL_PATHS = frozenset(TWIN_EXTRACTION_RETIRED_TO_CANONICAL.values())

# Reuses the mobile-dogfood guard's Markdown link regex: it is a generic
# `[text](target)` matcher, not specific to that family.
TWIN_EXTRACTION_MD_LINK_RE = MOBILE_DOGFOOD_MD_LINK_RE

# Repository-root-qualified literal scan, applied to every scanned file
# whose suffix is not `.md`/`.txt` (see the module comment above) -- matches
# any of the three retired paths anywhere in a line (YAML mapping keys,
# Python string literals, TOML keys/values, and any other non-Markdown/text
# suffix the shared scanner returns), independent of Markdown link or
# front-matter syntax.
TWIN_EXTRACTION_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in TWIN_EXTRACTION_RETIRED_PATHS) + ")"
)

# Files whose entire content is historical record-keeping by construction.
# Empty: no current file narrates the three retired paths as whole-file
# history. The frozen completion report is deliberately NOT here -- see the
# module comment above; its one live link is repaired instead of allowlisted.
TWIN_EXTRACTION_REFERENCE_ALLOWLISTED_FILES: frozenset[str] = frozenset()

# Exact, reviewed whole-line contents that are legitimate occurrences of a
# retired literal inside an otherwise-active/current file. Empty: no active
# current file legitimately names one of these retired literals. Any entry
# added here is matched by exact stripped-line equality, never substring
# containment -- a line that merely contains such a string as a fragment
# (extra prefix/suffix text on the same line, or a second, unrelated
# reference tacked onto the same line) is not allowed. No generic
# frozen/historical/status bypass.
TWIN_EXTRACTION_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {}

# This guard's own implementation file. Narrow, exact-line self-allowance
# only -- not a whole-file exemption, following the
# MOBILE_DOGFOOD_SELF_FILE_EXACT_LINES precedent. The only lines in this
# file that may legitimately spell out a retired literal are the
# TWIN_EXTRACTION_RETIRED_TO_CANONICAL dict's own key: value entries.
# Matched by exact stripped-line equality, not substring.
TWIN_EXTRACTION_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
TWIN_EXTRACTION_SELF_FILE_EXACT_LINES = frozenset(
    f'"{retired_path}": "{canonical_path}",'
    for retired_path, canonical_path in TWIN_EXTRACTION_RETIRED_TO_CANONICAL.items()
)


def check_no_live_twin_extraction_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in TWIN_EXTRACTION_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(
                f"{retired_path}: retired twin-extraction family path reintroduced "
                f"(moved to {canonical_path} by Cutover 1C-42)"
            )

    for path in _mobile_dogfood_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in TWIN_EXTRACTION_RETIRED_TO_CANONICAL:
            continue
        if relative_path in TWIN_EXTRACTION_REFERENCE_ALLOWLISTED_FILES:
            continue
        is_self_file = relative_path == TWIN_EXTRACTION_SELF_FILE
        allowed_lines = TWIN_EXTRACTION_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()

        def _is_allowed(stripped_line: str) -> bool:
            if is_self_file:
                return stripped_line in TWIN_EXTRACTION_SELF_FILE_EXACT_LINES
            return stripped_line in allowed_lines

        if path.suffix not in (".md", ".txt"):
            # Every other scanned suffix (`.yaml`, `.yml`, `.py`, `.toml`,
            # and any further suffix the shared scanner returns): neither
            # Markdown link syntax nor a YAML front-matter block is the
            # applicable reference form here, so use a literal
            # repository-root-qualified match instead (see the module
            # comment above). Branching on the negative condition, rather
            # than maintaining a fixed positive suffix allowlist, is what
            # makes a retired literal in `pyproject.toml` (or any other
            # non-Markdown/text file the scanner returns) detectable.
            for line_number, line in enumerate(lines, start=1):
                stripped = line.strip()
                literal_match = TWIN_EXTRACTION_REFERENCE_PATTERN.search(line)
                if literal_match is None or _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{literal_match.group(0)}: {stripped!r}"
                )
            continue

        # `.md`/`.txt` document -- including the three canonical Twin
        # Extraction destination documents themselves; there is no
        # canonical-path scan bypass (see the module comment above).

        # Pass 1: Markdown link targets, resolved against this file's own
        # directory (or the repository root for a "docs/"-qualified target).
        # Covers root-qualified, bare same-directory, ./, ../, ../../, and
        # anchored spellings via the shared resolver.
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            for link_match in TWIN_EXTRACTION_MD_LINK_RE.finditer(line):
                raw_target = link_match.group(1).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in TWIN_EXTRACTION_RETIRED_TO_CANONICAL:
                    continue
                if _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: markdown link target {raw_target!r}"
                )

        # Pass 2: every supported path-bearing front-matter key, resolved
        # via the actual parsed first-block YAML mapping.
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in TWIN_EXTRACTION_RETIRED_TO_CANONICAL:
                continue
            line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
            if _is_allowed(stripped):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: {key} entry {raw_target!r}"
            )


def check_twin_extraction_family_types(errors: list[str]) -> None:
    for canonical_path in sorted(TWIN_EXTRACTION_CANONICAL_PATHS):
        meta, _ = parse_front_matter(canonical_path)
        if meta.get("relaylm_doc_type") != "operations":
            errors.append(
                f"{canonical_path}: must declare relaylm_doc_type: operations, not "
                f"{meta.get('relaylm_doc_type')!r} (never the retired runbook type)"
            )


# ---------------------------------------------------------------------------
# Cutover 1C-43: retirement guard for the single-document Consolidated Smoke
# Workflow Maintenance authority, following the CORRECTED Cutover 1C-42
# twin-extraction guard pattern (post-`81d173a` state) as the binding
# precedent: canonical documents are scanned like any other document (no
# canonical-target skip), the reference-line allowlist is exact
# stripped-line equality (never substring containment), and the
# non-Markdown literal scan applies to every scanned file whose suffix is
# not `.md`/`.txt` (no fixed positive suffix allowlist, so a retired
# literal in e.g. `pyproject.toml` remains detectable).
#
# This family has exactly one retired->canonical pair, unlike the
# three-member mobile-dogfood and twin-extraction families, but reuses the
# same shared scanning/resolution helpers (`_mobile_dogfood_scanned_files`,
# `_mobile_dogfood_resolve`, `_mobile_dogfood_front_matter_path_values`,
# `_mobile_dogfood_locate`, `MOBILE_DOGFOOD_MD_LINK_RE`) rather than pasting
# a third bespoke copy of the scanning machinery.
#
# The frozen scripts-inventory evidence is distinct from the current
# operations maintenance authority. The pairing check reads both permanent
# paths while generation continues to target only generated output.
# ---------------------------------------------------------------------------
SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/smoke/consolidated_workflow_maintenance.md": "docs/operations/consolidated-smoke-workflow-maintenance.md",
}
SMOKE_MAINTENANCE_RETIRED_PATHS = tuple(sorted(SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL))
SMOKE_MAINTENANCE_CANONICAL_PATHS = frozenset(SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL.values())

# Reuses the mobile-dogfood guard's generic `[text](target)` Markdown link
# matcher.
SMOKE_MAINTENANCE_MD_LINK_RE = MOBILE_DOGFOOD_MD_LINK_RE

# Repository-root-qualified literal scan, applied to every scanned file
# whose suffix is not `.md`/`.txt` -- matches the one retired path anywhere
# in a line (YAML mapping keys, Python string literals, TOML keys/values,
# and any other non-Markdown/text suffix the shared scanner returns),
# independent of Markdown link or front-matter syntax.
SMOKE_MAINTENANCE_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in SMOKE_MAINTENANCE_RETIRED_PATHS) + ")"
)

# Files whose entire content is historical record-keeping by construction.
# Empty: no current file names this retired path as whole-file history,
# matching the established mobile-dogfood/twin-extraction precedent.
SMOKE_MAINTENANCE_REFERENCE_ALLOWLISTED_FILES: frozenset[str] = frozenset()

# Exact, reviewed whole-line contents that are legitimate occurrences of the
# retired literal inside an otherwise-active/current file. Empty: no active
# current file legitimately names this retired literal. Any entry added here
# is matched by exact stripped-line equality, never substring containment.
SMOKE_MAINTENANCE_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {}

# This guard's own implementation file. Narrow, exact-line self-allowance
# only -- not a whole-file exemption. The only line in this file that may
# legitimately spell out the retired literal is the
# SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL dict's own key: value entry.
# Matched by exact stripped-line equality, not substring.
SMOKE_MAINTENANCE_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
SMOKE_MAINTENANCE_SELF_FILE_EXACT_LINES = frozenset(
    f'"{retired_path}": "{canonical_path}",'
    for retired_path, canonical_path in SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL.items()
)


def check_no_live_smoke_maintenance_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(
                f"{retired_path}: retired smoke-workflow-maintenance path reintroduced "
                f"(moved to {canonical_path} by Cutover 1C-43)"
            )

    for path in _mobile_dogfood_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL:
            continue
        if relative_path in SMOKE_MAINTENANCE_REFERENCE_ALLOWLISTED_FILES:
            continue
        is_self_file = relative_path == SMOKE_MAINTENANCE_SELF_FILE
        allowed_lines = SMOKE_MAINTENANCE_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()

        def _is_allowed(stripped_line: str) -> bool:
            if is_self_file:
                return stripped_line in SMOKE_MAINTENANCE_SELF_FILE_EXACT_LINES
            return stripped_line in allowed_lines

        if path.suffix not in (".md", ".txt"):
            # Every other scanned suffix (`.yaml`, `.yml`, `.py`, `.toml`,
            # and any further suffix the shared scanner returns): use a
            # literal repository-root-qualified match, not Markdown link
            # syntax or a YAML front-matter block.
            for line_number, line in enumerate(lines, start=1):
                stripped = line.strip()
                literal_match = SMOKE_MAINTENANCE_REFERENCE_PATTERN.search(line)
                if literal_match is None or _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{literal_match.group(0)}: {stripped!r}"
                )
            continue

        # `.md`/`.txt` document -- including the canonical destination
        # document itself; there is no canonical-path scan bypass.

        # Pass 1: Markdown link targets, resolved against this file's own
        # directory (or the repository root for a "docs/"-qualified
        # target). Covers root-qualified, bare same-directory, ./, ../,
        # ../../, and anchored spellings via the shared resolver.
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            for link_match in SMOKE_MAINTENANCE_MD_LINK_RE.finditer(line):
                raw_target = link_match.group(1).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL:
                    continue
                if _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: markdown link target {raw_target!r}"
                )

        # Pass 2: every supported path-bearing front-matter key, resolved
        # via the actual parsed first-block YAML mapping.
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL:
                continue
            line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
            if _is_allowed(stripped):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: {key} entry {raw_target!r}"
            )


def check_smoke_maintenance_family_types(errors: list[str]) -> None:
    for canonical_path in sorted(SMOKE_MAINTENANCE_CANONICAL_PATHS):
        meta, _ = parse_front_matter(canonical_path)
        if meta.get("relaylm_doc_type") != "operations":
            errors.append(
                f"{canonical_path}: must declare relaylm_doc_type: operations, not "
                f"{meta.get('relaylm_doc_type')!r} (never the retired runbook type)"
            )
        if meta.get("relaylm_status") != "current":
            errors.append(
                f"{canonical_path}: must declare relaylm_status: current, not "
                f"{meta.get('relaylm_status')!r}"
            )


# ---------------------------------------------------------------------------
# Cutover 1C-44: retirement guard for the single-document O1 Manual One-Round
# authority, following the CORRECTED Cutover 1C-43 smoke-maintenance guard
# pattern as the binding precedent: canonical documents are scanned like any
# other document (no canonical-target skip), the reference-line allowlist is
# exact stripped-line equality (never substring containment), and the
# non-Markdown literal scan applies to every scanned file whose suffix is not
# `.md`/`.txt` (no fixed positive suffix allowlist).
#
# This family has exactly one retired->canonical pair and reuses the same
# shared scanning/resolution helpers (`_mobile_dogfood_scanned_files`,
# `_mobile_dogfood_resolve`, `_mobile_dogfood_front_matter_path_values`,
# `_mobile_dogfood_locate`, `MOBILE_DOGFOOD_MD_LINK_RE`) rather than pasting a
# fourth bespoke copy of the scanning machinery.
#
# Unlike the Cutover 1C-43 smoke-maintenance family, this moved document's
# canonical `relaylm_status` is `compatibility`, not `current`:
# docs/DOCUMENTATION_MODEL.md's "Status values" section defines `compatibility`
# as an existing-only pre-cutover status with no normalize-during-cutover rule
# (unlike `historical_after_merge`), so a moved existing document retains it.
# `check_o1_manual_one_round_family_types()` below enforces the full profile
# (`relaylm_doc_type: operations` AND `relaylm_status: compatibility`) with an
# independent fail-closed diagnostic per mismatch, per the C1C43 correction
# round's established precedent that type-only enforcement is a defect.
# ---------------------------------------------------------------------------
O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/smoke/o1_manual_one_round_runbook.md": "docs/operations/o1-manual-one-round.md",
}
O1_MANUAL_ONE_ROUND_RETIRED_PATHS = tuple(sorted(O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL))
O1_MANUAL_ONE_ROUND_CANONICAL_PATHS = frozenset(O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL.values())

# Reuses the mobile-dogfood guard's generic `[text](target)` Markdown link
# matcher.
O1_MANUAL_ONE_ROUND_MD_LINK_RE = MOBILE_DOGFOOD_MD_LINK_RE

# Repository-root-qualified literal scan, applied to every scanned file whose
# suffix is not `.md`/`.txt` -- matches the one retired path anywhere in a
# line (YAML mapping keys, Python string literals, TOML keys/values, and any
# other non-Markdown/text suffix the shared scanner returns), independent of
# Markdown link or front-matter syntax.
O1_MANUAL_ONE_ROUND_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in O1_MANUAL_ONE_ROUND_RETIRED_PATHS) + ")"
)

# Retired basenames are used as the terminal component for bounded prose-token
# detection. Candidates are resolved before rejection, so the basename alone is
# never treated as a global substring ban.
O1_MANUAL_ONE_ROUND_RETIRED_BASENAMES = tuple(
    sorted({Path(path).name for path in O1_MANUAL_ONE_ROUND_RETIRED_PATHS})
)
# Bounded Markdown/text prose path-token matcher for plain prose and inline-code
# mentions that are not Markdown links or front-matter values. It intentionally
# matches path-like tokens ending in the exact retired basename and then resolves
# each candidate against the referring file with `_mobile_dogfood_resolve()`; it
# is not a global basename substring rejection. The optional leading relative
# path is bounded to avoid pathological prose scans while still covering the
# documented same-directory, `./`, and additional `../` spellings.
O1_MANUAL_ONE_ROUND_PROSE_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,8})"
    r"(?:" + "|".join(re.escape(name) for name in O1_MANUAL_ONE_ROUND_RETIRED_BASENAMES) + r"))"
    r"(?:#[A-Za-z0-9_.~/%:-]+)?"
    r"(?![A-Za-z0-9_.-])"
)

# Bounded Markdown-visible navigation carriers not handled by the inline
# Markdown-link regex: local HTML href attributes and reference-style link
# definitions. Each extracted destination is still resolved through
# `_mobile_dogfood_resolve()`, so external URLs, root-absolute paths, empty
# anchors, query strings, fragments, and %-encoding follow the same behavior as
# the existing link/front-matter passes.
O1_MANUAL_ONE_ROUND_HTML_HREF_RE = re.compile(
    r"\bhref\s*=\s*([\"'])([^\"'<>\s][^\"'<>]*)\1",
    re.IGNORECASE,
)
O1_MANUAL_ONE_ROUND_REFERENCE_DEFINITION_RE = re.compile(
    r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^ \t\n]+))"
)

# Files whose entire content is historical record-keeping by construction.
# Empty: no current file names this retired path as whole-file history,
# matching the established precedent.
O1_MANUAL_ONE_ROUND_REFERENCE_ALLOWLISTED_FILES: frozenset[str] = frozenset()

# Exact, reviewed whole-line contents that are legitimate occurrences of the
# retired literal inside an otherwise-active/current file. Empty: no active
# current file legitimately names this retired literal. Any entry added here
# is matched by exact stripped-line equality, never substring containment.
O1_MANUAL_ONE_ROUND_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {}

# This guard's own implementation file. Narrow, exact-line self-allowance
# only -- not a whole-file exemption. The only line in this file that may
# legitimately spell out the retired literal is the
# O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL dict's own key: value entry.
# Matched by exact stripped-line equality, not substring.
O1_MANUAL_ONE_ROUND_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
O1_MANUAL_ONE_ROUND_SELF_FILE_EXACT_LINES = frozenset(
    f'"{retired_path}": "{canonical_path}",'
    for retired_path, canonical_path in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL.items()
)


def _o1_manual_one_round_scanned_files(root: Path) -> list[Path]:
    """This guard's scan universe: the shared `_mobile_dogfood_scanned_files`
    file set, plus every `docs/**/*.txt` file.

    The shared `MVP_REFERENCE_SCAN_DIRS` constant (reused by the
    mobile-dogfood, twin-extraction, and smoke-maintenance guards) only lists
    `.md`/`.yaml`/`.yml` suffixes for `docs/`, so no `.txt` file is currently
    part of that shared scan universe even though `docs/evidence/**/*.txt`
    (`-source.txt`) files exist and already carry a dedicated allowlist
    exemption elsewhere in this module. The Codex review correction for this
    guard requires `.txt` coverage; rather than widen the shared constant
    (which would also change what the mobile-dogfood/twin-extraction/
    smoke-maintenance guards scan -- an out-of-scope redesign per the
    accepted correction scope), this helper adds `docs/**/*.txt` locally, for
    this guard only.
    """
    files = list(_mobile_dogfood_scanned_files(root))
    seen = {file_path.resolve() for file_path in files}
    docs_root = root / "docs"
    if docs_root.is_dir():
        for candidate in sorted(docs_root.rglob("*.txt")):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            files.append(candidate)
            seen.add(resolved)
    return files


def check_no_live_o1_manual_one_round_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(
                f"{retired_path}: retired o1-manual-one-round path reintroduced "
                f"(moved to {canonical_path} by Cutover 1C-44)"
            )

    for path in _o1_manual_one_round_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
            continue
        if relative_path in O1_MANUAL_ONE_ROUND_REFERENCE_ALLOWLISTED_FILES:
            continue
        is_self_file = relative_path == O1_MANUAL_ONE_ROUND_SELF_FILE
        allowed_lines = O1_MANUAL_ONE_ROUND_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()

        def _is_allowed(stripped_line: str) -> bool:
            if is_self_file:
                return stripped_line in O1_MANUAL_ONE_ROUND_SELF_FILE_EXACT_LINES
            return stripped_line in allowed_lines

        def _is_inside_external_html_href(line_text: str, start: int, end: int) -> bool:
            for href_match in O1_MANUAL_ONE_ROUND_HTML_HREF_RE.finditer(line_text):
                value_start, value_end = href_match.span(2)
                if not (value_start <= start and end <= value_end):
                    continue
                parsed = urlsplit(href_match.group(2).strip())
                if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
                    return True
            return False

        if path.suffix not in (".md", ".txt"):
            # Every other scanned suffix (`.yaml`, `.yml`, `.py`, `.toml`,
            # and any further suffix the shared scanner returns): use a
            # literal repository-root-qualified match, not Markdown link
            # syntax or a YAML front-matter block.
            for line_number, line in enumerate(lines, start=1):
                stripped = line.strip()
                literal_match = O1_MANUAL_ONE_ROUND_REFERENCE_PATTERN.search(line)
                if literal_match is None or _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{literal_match.group(0)}: {stripped!r}"
                )
            continue

        # `.md`/`.txt` document -- including the canonical destination
        # document itself; there is no canonical-path scan bypass.
        reported_line_numbers: set[int] = set()

        # Pass 1: Markdown link targets, resolved against this file's own
        # directory (or the repository root for a "docs/"-qualified target).
        # Covers root-qualified, bare same-directory, ./, ../, ../../, and
        # anchored spellings via the shared resolver.
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            for link_match in O1_MANUAL_ONE_ROUND_MD_LINK_RE.finditer(line):
                raw_target = link_match.group(1).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
                    continue
                if _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: markdown link target {raw_target!r}"
                )
                reported_line_numbers.add(line_number)

        # Pass 2: every supported path-bearing front-matter key, resolved via
        # the actual parsed first-block YAML mapping.
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
                continue
            line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
            if _is_allowed(stripped):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: {key} entry {raw_target!r}"
            )
            reported_line_numbers.add(line_number)

        # Pass 3 (Codex review correction, first round): literal retired-path
        # mentions in Markdown/text prose or inline code (backticks) that are
        # not expressed as a Markdown link or a front-matter path value --
        # e.g. a plain-prose or backtick-quoted mention of the old path in
        # running text. Uses the same repository-root-qualified literal
        # pattern as the non-Markdown branch above. Lines already reported by
        # Pass 1 or Pass 2 are skipped here so a link or front-matter value
        # that also happens to contain the literal is not double-reported.
        for line_number, line in enumerate(lines, start=1):
            if line_number in reported_line_numbers:
                continue
            stripped = line.strip()
            literal_match = O1_MANUAL_ONE_ROUND_REFERENCE_PATTERN.search(line)
            if literal_match is None or _is_allowed(stripped):
                continue
            if _is_inside_external_html_href(line, literal_match.start(), literal_match.end()):
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{literal_match.group(0)}: {stripped!r}"
            )
            reported_line_numbers.add(line_number)

        # Pass 4 (Codex review correction, fourth round): Markdown-visible
        # navigation carriers not covered by Pass 1's inline Markdown-link
        # syntax: HTML `href` attributes and reference-style link
        # definitions. Extracted targets are resolved with the same helper as
        # inline links/front-matter values and only the exact retired path is
        # rejected. Lines already reported by earlier passes are skipped to
        # avoid duplicate diagnostics.
        for line_number, line in enumerate(lines, start=1):
            if line_number in reported_line_numbers:
                continue
            stripped = line.strip()
            if _is_allowed(stripped):
                continue
            for href_match in O1_MANUAL_ONE_ROUND_HTML_HREF_RE.finditer(line):
                raw_target = href_match.group(2).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: HTML href {raw_target!r}: {stripped!r}"
                )
                reported_line_numbers.add(line_number)
                break
            if line_number in reported_line_numbers:
                continue
            reference_match = O1_MANUAL_ONE_ROUND_REFERENCE_DEFINITION_RE.match(line)
            if reference_match is None:
                continue
            raw_target = (reference_match.group(1) or reference_match.group(2) or "").strip()
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: reference definition {raw_target!r}: {stripped!r}"
            )
            reported_line_numbers.add(line_number)

        # Pass 5 (Codex review correction, second round): bounded
        # Markdown/text prose path tokens in plain prose or backticks, not
        # expressed as Markdown links, front-matter values, HTML hrefs, or
        # reference definitions. Each candidate is resolved exactly like a
        # Markdown link/front-matter path via `_mobile_dogfood_resolve()`, and
        # only candidates resolving to the retired repository path are
        # rejected. This catches bare same-directory, `./`, `../smoke/`, and
        # bounded additional relative spellings without using a global
        # basename substring check or rejecting the same basename in unrelated
        # directories. Lines already reported by earlier passes are skipped to
        # avoid duplicate diagnostics.
        for line_number, line in enumerate(lines, start=1):
            if line_number in reported_line_numbers:
                continue
            stripped = line.strip()
            if _is_allowed(stripped):
                continue
            for token_match in O1_MANUAL_ONE_ROUND_PROSE_PATH_TOKEN_RE.finditer(line):
                raw_target = token_match.group(1)
                if _is_inside_external_html_href(line, token_match.start(1), token_match.end(1)):
                    continue
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved not in O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL:
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{resolved}: prose path token {raw_target!r}: {stripped!r}"
                )
                reported_line_numbers.add(line_number)
                break



# Cutover 1C-45: OpenWebUI / LM Studio manual-validation family retired paths.
OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/smoke/openwebui_lmstudio_manual_smoke.md": "docs/operations/openwebui-lmstudio-manual-smoke.md",
    "docs/smoke/client_history_exclusion_manual_smoke.md": "docs/operations/client-history-exclusion-manual-smoke.md",
    "docs/smoke/relayrun_recovery_diagnostics_manual_smoke.md": "docs/operations/relayrun-recovery-diagnostics-manual-smoke.md",
    "docs/smoke/openwebui_lmstudio_manual_smoke_results_template.md": "docs/templates/evaluation/openwebui-lmstudio-manual-smoke-results.md",
    "docs/smoke/openwebui_lmstudio_manual_smoke_result_2026_05_26.md": "docs/evidence/evaluations/openwebui-lmstudio-manual-smoke-2026-05-26.md",
}
OPENWEBUI_MANUAL_VALIDATION_RETIRED_PATHS = tuple(sorted(OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL))
OPENWEBUI_MANUAL_VALIDATION_CANONICAL_TYPES = {
    "docs/operations/openwebui-lmstudio-manual-smoke.md": ("operations", "current"),
    "docs/operations/client-history-exclusion-manual-smoke.md": ("operations", "current"),
    "docs/operations/relayrun-recovery-diagnostics-manual-smoke.md": ("operations", "current"),
    "docs/templates/evaluation/openwebui-lmstudio-manual-smoke-results.md": ("template", "target"),
    "docs/evidence/evaluations/openwebui-lmstudio-manual-smoke-2026-05-26.md": ("evidence", "frozen"),
}
OPENWEBUI_MANUAL_VALIDATION_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in OPENWEBUI_MANUAL_VALIDATION_RETIRED_PATHS) + ")"
)
OPENWEBUI_MANUAL_VALIDATION_BASENAMES = tuple(sorted({Path(path).name for path in OPENWEBUI_MANUAL_VALIDATION_RETIRED_PATHS}))
OPENWEBUI_MANUAL_VALIDATION_PROSE_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,8})(?:"
    + "|".join(re.escape(name) for name in OPENWEBUI_MANUAL_VALIDATION_BASENAMES)
    + r"))(?:[?#][A-Za-z0-9_.~/%=&:-]+)?(?![A-Za-z0-9_.-])"
)
OPENWEBUI_MANUAL_VALIDATION_HTML_LINK_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])([^\"'<>\s][^\"'<>]*)\1", re.IGNORECASE)
OPENWEBUI_MANUAL_VALIDATION_REFERENCE_DEFINITION_RE = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^ \t\n]+))")
OPENWEBUI_MANUAL_VALIDATION_ALLOWLISTED_FILES: frozenset[str] = frozenset()
OPENWEBUI_MANUAL_VALIDATION_LINE_ALLOWLIST = {
    "docs/evidence/evaluations/openwebui-lmstudio-manual-smoke-2026-05-26.md": (
        "relaylm_source_path: docs/smoke/openwebui_lmstudio_manual_smoke_result_2026_05_26.md",
    ),
}
OPENWEBUI_MANUAL_VALIDATION_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
OPENWEBUI_MANUAL_VALIDATION_SELF_LINES = frozenset(
    [
        *(
            f'"{retired_path}": "{canonical_path}",'
            for retired_path, canonical_path in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL.items()
        ),
        '"relaylm_source_path: docs/smoke/'
        + 'openwebui_lmstudio_manual_smoke_result_2026_05_26.md",',
    ]
)


def _openwebui_manual_validation_scanned_files(root: Path) -> list[Path]:
    files = list(_mobile_dogfood_scanned_files(root))
    seen = {file_path.resolve() for file_path in files}
    docs_root = root / "docs"
    if docs_root.is_dir():
        for candidate in sorted(docs_root.rglob("*.txt")):
            if candidate.is_file() and candidate.resolve() not in seen:
                files.append(candidate)
                seen.add(candidate.resolve())
    return files


def check_no_live_openwebui_manual_validation_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(f"{retired_path}: retired OpenWebUI manual-validation path reintroduced (moved to {canonical_path} by Cutover 1C-45)")
    for path in _openwebui_manual_validation_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL or relative_path in OPENWEBUI_MANUAL_VALIDATION_ALLOWLISTED_FILES:
            continue
        is_self = relative_path == OPENWEBUI_MANUAL_VALIDATION_SELF_FILE
        allowed = OPENWEBUI_MANUAL_VALIDATION_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        def ok(stripped: str) -> bool:
            return stripped in OPENWEBUI_MANUAL_VALIDATION_SELF_LINES if is_self else stripped in allowed
        reported: set[int] = set()
        def outside_external_href(line: str, start: int, end: int) -> bool:
            for m in OPENWEBUI_MANUAL_VALIDATION_HTML_LINK_RE.finditer(line):
                if m.start(2) <= start and end <= m.end(2):
                    parsed = urlsplit(m.group(2).strip())
                    if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
                        return False
            for m in MOBILE_DOGFOOD_MD_LINK_RE.finditer(line):
                if m.start(1) <= start and end <= m.end(1):
                    parsed = urlsplit(m.group(1).strip())
                    if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
                        return False
            return True
        if path.suffix not in (".md", ".txt"):
            for line_number, line in enumerate(lines, 1):
                stripped = line.strip(); m = OPENWEBUI_MANUAL_VALIDATION_REFERENCE_PATTERN.search(line)
                if m and not ok(stripped):
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {m.group(0)}: {stripped!r}")
            continue
        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()
            if ok(stripped):
                continue
            for m in MOBILE_DOGFOOD_MD_LINK_RE.finditer(line):
                raw = m.group(1).strip()
                parsed_raw = urlsplit(raw)
                if parsed_raw.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed_raw.netloc:
                    continue
                resolved = _mobile_dogfood_resolve(path, raw)
                if resolved in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL:
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {resolved}: markdown link target {raw!r}"); reported.add(line_number); break
            if line_number in reported: continue
            for m in OPENWEBUI_MANUAL_VALIDATION_HTML_LINK_RE.finditer(line):
                raw = m.group(2).strip(); resolved = _mobile_dogfood_resolve(path, raw)
                if resolved in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL:
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {resolved}: HTML href/src {raw!r}: {stripped!r}"); reported.add(line_number); break
            if line_number in reported: continue
            rm = OPENWEBUI_MANUAL_VALIDATION_REFERENCE_DEFINITION_RE.match(line)
            if rm:
                raw = (rm.group(1) or rm.group(2) or "").strip(); resolved = _mobile_dogfood_resolve(path, raw)
                if resolved in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL:
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {resolved}: reference definition {raw!r}: {stripped!r}"); reported.add(line_number)
            if line_number in reported: continue
            lm = OPENWEBUI_MANUAL_VALIDATION_REFERENCE_PATTERN.search(line)
            if lm and outside_external_href(line, lm.start(), lm.end()):
                errors.append(f"{relative_path}:{line_number}: active reference to retired {lm.group(0)}: {stripped!r}"); reported.add(line_number); continue
            for tm in OPENWEBUI_MANUAL_VALIDATION_PROSE_PATH_TOKEN_RE.finditer(line):
                if not outside_external_href(line, tm.start(1), tm.end(1)):
                    continue
                raw = tm.group(1); resolved = _mobile_dogfood_resolve(path, raw)
                if resolved in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL:
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {resolved}: prose path token {raw!r}: {stripped!r}"); reported.add(line_number); break
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved in OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL:
                line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
                if not ok(stripped) and line_number not in reported:
                    errors.append(f"{relative_path}:{line_number}: active reference to retired {resolved}: {key} entry {raw_target!r}")


def check_openwebui_manual_validation_family_types(errors: list[str]) -> None:
    for canonical_path, (doc_type, status) in sorted(OPENWEBUI_MANUAL_VALIDATION_CANONICAL_TYPES.items()):
        meta, _ = parse_front_matter(canonical_path)
        if meta.get("relaylm_doc_type") != doc_type:
            errors.append(f"{canonical_path}: must declare relaylm_doc_type: {doc_type}, not {meta.get('relaylm_doc_type')!r}")
        if meta.get("relaylm_status") != status:
            errors.append(f"{canonical_path}: must declare relaylm_status: {status}, not {meta.get('relaylm_status')!r}")


def check_o1_manual_one_round_family_types(errors: list[str]) -> None:
    for canonical_path in sorted(O1_MANUAL_ONE_ROUND_CANONICAL_PATHS):
        meta, _ = parse_front_matter(canonical_path)
        if meta.get("relaylm_doc_type") != "operations":
            errors.append(
                f"{canonical_path}: must declare relaylm_doc_type: operations, not "
                f"{meta.get('relaylm_doc_type')!r} (never the retired runbook type)"
            )
        if meta.get("relaylm_status") != "compatibility":
            errors.append(
                f"{canonical_path}: must declare relaylm_status: compatibility, not "
                f"{meta.get('relaylm_status')!r}"
            )


# ---------------------------------------------------------------------------
# Cutover 1C-46: retirement guard for the single-document ReLM Showcase
# Fixture Authoring guide, following the CORRECTED Cutover 1C-45 OpenWebUI
# guard pattern as the binding precedent (the most recently corrected
# single/multi-member family guard): canonical documents are scanned like any
# other document (no canonical-target skip); the reference-line allowlist is
# exact stripped-line equality (never substring containment); and, for
# `.md`/`.txt` referrers, retired-path detection covers Markdown links, HTML
# `href`/`src` attributes, Markdown reference-style link definitions, bare
# repository-root-qualified literal mentions (plain prose or backtick-quoted,
# not only inside a Markdown link), bounded prose path tokens ending in a
# retired basename, and path-bearing front-matter values -- not only Markdown
# links and front matter. A Codex review on this cutover's own PR found the
# earlier Cutover 1C-42/1C-43/1C-44(pre-correction) `.md`/`.txt` branch
# (Markdown links + front matter only) repeats the exact P2 gap the Cutover
# 1C-44 correction round fixed for the O1 guard: a plain-prose or
# backtick-quoted retired-path mention in a `.md`/`.txt` file was silently
# accepted. This guard is written with the full corrected coverage from the
# start rather than needing its own later correction round.
#
# The shared `_mobile_dogfood_scanned_files()` file set (reused by the
# mobile-dogfood/twin-extraction/smoke-maintenance/O1 guards) does not
# include `.txt` files under `docs/`; `_showcase_fixture_scanned_files()`
# adds `docs/**/*.txt` locally, matching the Cutover 1C-44/1C-45 `.txt`
# coverage fix, without widening the shared constant those other guards use.
#
# This family has exactly one retired->canonical pair and otherwise reuses
# the shared resolution helpers (`_mobile_dogfood_resolve`,
# `_mobile_dogfood_front_matter_path_values`, `_mobile_dogfood_locate`,
# `MOBILE_DOGFOOD_MD_LINK_RE`, `MOBILE_DOGFOOD_EXTERNAL_SCHEMES`) rather than
# pasting a further bespoke copy of the resolution machinery.
#
# docs/tools/ held no other live file at the time of this cutover (its two
# prior occupants were already retired by Cutover 1C-41 and 1C-42), so its
# full retirement is also covered independently by
# scripts/relaylm_documentation_current_boundary_smoke.py's
# assert_no_docs_tools_tree().
# ---------------------------------------------------------------------------
SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL: dict[str, str] = {
    "docs/tools/relm_showcase_fixture_template.md": "docs/operations/relm-showcase-fixture-authoring.md",
}
SHOWCASE_FIXTURE_RETIRED_PATHS = tuple(sorted(SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL))
SHOWCASE_FIXTURE_CANONICAL_PATHS = frozenset(SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL.values())

# Reuses the mobile-dogfood guard's generic `[text](target)` Markdown link
# matcher.
SHOWCASE_FIXTURE_MD_LINK_RE = MOBILE_DOGFOOD_MD_LINK_RE

# Repository-root-qualified literal scan: matches the one retired path
# anywhere in a line (YAML mapping keys, Python string literals, plain prose,
# backtick-quoted inline code, table cells), independent of Markdown link or
# front-matter syntax.
SHOWCASE_FIXTURE_REFERENCE_PATTERN = re.compile(
    "(?:" + "|".join(re.escape(path) for path in SHOWCASE_FIXTURE_RETIRED_PATHS) + ")"
)

# Retired basenames are used as the terminal component for bounded prose-token
# detection. Candidates are resolved before rejection, so the basename alone
# is never treated as a global substring ban.
SHOWCASE_FIXTURE_BASENAMES = tuple(sorted({Path(path).name for path in SHOWCASE_FIXTURE_RETIRED_PATHS}))
SHOWCASE_FIXTURE_PROSE_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,8})(?:"
    + "|".join(re.escape(name) for name in SHOWCASE_FIXTURE_BASENAMES)
    + r"))(?:[?#][A-Za-z0-9_.~/%=&:-]+)?(?![A-Za-z0-9_.-])"
)

# Bounded Markdown-visible navigation carriers not handled by the inline
# Markdown-link regex: local HTML `href`/`src` attributes and reference-style
# link definitions.
SHOWCASE_FIXTURE_HTML_LINK_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])([^\"'<>\s][^\"'<>]*)\1", re.IGNORECASE)
SHOWCASE_FIXTURE_REFERENCE_DEFINITION_RE = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^ \t\n]+))")

# Files whose entire content is historical record-keeping by construction.
# Empty: no current file names this retired path as whole-file history,
# matching the established
# mobile-dogfood/twin-extraction/smoke-maintenance/O1/openwebui precedent.
SHOWCASE_FIXTURE_REFERENCE_ALLOWLISTED_FILES: frozenset[str] = frozenset()

# Exact, reviewed whole-line contents that are legitimate occurrences of the
# retired literal inside an otherwise-active/current file. Empty: no active
# current file legitimately names this retired literal. Any entry added here
# is matched by exact stripped-line equality, never substring containment.
SHOWCASE_FIXTURE_REFERENCE_LINE_ALLOWLIST: dict[str, tuple[str, ...]] = {}

# This guard's own implementation file. Narrow, exact-line self-allowance
# only -- not a whole-file exemption. The only line in this file that may
# legitimately spell out the retired literal is the
# SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL dict's own key: value entry.
SHOWCASE_FIXTURE_SELF_FILE = "scripts/relaylm_docs_semantic_audit.py"
SHOWCASE_FIXTURE_SELF_FILE_EXACT_LINES = frozenset(
    f'"{retired_path}": "{canonical_path}",'
    for retired_path, canonical_path in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL.items()
)


def _showcase_fixture_scanned_files(root: Path) -> list[Path]:
    """This guard's scan universe: the shared `_mobile_dogfood_scanned_files`
    file set, plus every `docs/**/*.txt` file (the shared scan universe does
    not include `.txt`, matching the Cutover 1C-44/1C-45 `.txt`-coverage
    fix), added locally so the shared constant other guards reuse is
    unaffected."""
    files = list(_mobile_dogfood_scanned_files(root))
    seen = {file_path.resolve() for file_path in files}
    docs_root = root / "docs"
    if docs_root.is_dir():
        for candidate in sorted(docs_root.rglob("*.txt")):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            files.append(candidate)
            seen.add(resolved)
    return files


def check_no_live_showcase_fixture_retired_paths(errors: list[str]) -> None:
    for retired_path, canonical_path in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL.items():
        if (ROOT / retired_path).exists():
            errors.append(
                f"{retired_path}: retired showcase-fixture-authoring path reintroduced "
                f"(moved to {canonical_path} by Cutover 1C-46)"
            )

    for path in _showcase_fixture_scanned_files(ROOT):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
            continue
        if relative_path in SHOWCASE_FIXTURE_REFERENCE_ALLOWLISTED_FILES:
            continue
        is_self_file = relative_path == SHOWCASE_FIXTURE_SELF_FILE
        allowed_lines = SHOWCASE_FIXTURE_REFERENCE_LINE_ALLOWLIST.get(relative_path, ())
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()

        def _is_allowed(stripped_line: str) -> bool:
            if is_self_file:
                return stripped_line in SHOWCASE_FIXTURE_SELF_FILE_EXACT_LINES
            return stripped_line in allowed_lines

        def _outside_external_href(line_text: str, start: int, end: int) -> bool:
            """True unless [start, end) sits inside an external-scheme/netloc
            href or src attribute value or Markdown link target -- i.e. true
            for a genuine local retired-path mention, false for e.g. a
            retired basename that happens to appear inside an external URL's
            query string."""
            for href_match in SHOWCASE_FIXTURE_HTML_LINK_RE.finditer(line_text):
                if href_match.start(2) <= start and end <= href_match.end(2):
                    parsed = urlsplit(href_match.group(2).strip())
                    if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
                        return False
            for link_match in MOBILE_DOGFOOD_MD_LINK_RE.finditer(line_text):
                if link_match.start(1) <= start and end <= link_match.end(1):
                    parsed = urlsplit(link_match.group(1).strip())
                    if parsed.scheme.lower() in MOBILE_DOGFOOD_EXTERNAL_SCHEMES or parsed.netloc:
                        return False
            return True

        if path.suffix not in (".md", ".txt"):
            # Every other scanned suffix: use a literal repository-root-
            # qualified match, not Markdown link syntax or a YAML
            # front-matter block.
            for line_number, line in enumerate(lines, start=1):
                stripped = line.strip()
                literal_match = SHOWCASE_FIXTURE_REFERENCE_PATTERN.search(line)
                if literal_match is None or _is_allowed(stripped):
                    continue
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{literal_match.group(0)}: {stripped!r}"
                )
            continue

        # `.md`/`.txt` document -- including the canonical destination
        # document itself; there is no canonical-path scan bypass. Each line
        # is reported at most once (`reported_line_numbers`) even if it
        # matches more than one pass.
        reported_line_numbers: set[int] = set()

        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if _is_allowed(stripped):
                continue

            # Pass 1: Markdown link targets, resolved against this file's own
            # directory (or the repository root for a "docs/"-qualified
            # target).
            for link_match in SHOWCASE_FIXTURE_MD_LINK_RE.finditer(line):
                raw_target = link_match.group(1).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
                    errors.append(
                        f"{relative_path}:{line_number}: active reference to retired "
                        f"{resolved}: markdown link target {raw_target!r}"
                    )
                    reported_line_numbers.add(line_number)
                    break
            if line_number in reported_line_numbers:
                continue

            # Pass 2: local HTML `href`/`src` attributes.
            for href_match in SHOWCASE_FIXTURE_HTML_LINK_RE.finditer(line):
                raw_target = href_match.group(2).strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
                    errors.append(
                        f"{relative_path}:{line_number}: active reference to retired "
                        f"{resolved}: HTML href/src {raw_target!r}: {stripped!r}"
                    )
                    reported_line_numbers.add(line_number)
                    break
            if line_number in reported_line_numbers:
                continue

            # Pass 3: Markdown reference-style link definitions.
            reference_match = SHOWCASE_FIXTURE_REFERENCE_DEFINITION_RE.match(line)
            if reference_match is not None:
                raw_target = (reference_match.group(1) or reference_match.group(2) or "").strip()
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
                    errors.append(
                        f"{relative_path}:{line_number}: active reference to retired "
                        f"{resolved}: reference definition {raw_target!r}: {stripped!r}"
                    )
                    reported_line_numbers.add(line_number)
            if line_number in reported_line_numbers:
                continue

            # Pass 4: bare repository-root-qualified literal mentions --
            # plain prose or backtick-quoted, not expressed as a Markdown
            # link, HTML attribute, or reference definition.
            literal_match = SHOWCASE_FIXTURE_REFERENCE_PATTERN.search(line)
            if literal_match is not None and _outside_external_href(
                line, literal_match.start(), literal_match.end()
            ):
                errors.append(
                    f"{relative_path}:{line_number}: active reference to retired "
                    f"{literal_match.group(0)}: {stripped!r}"
                )
                reported_line_numbers.add(line_number)
                continue

            # Pass 5: bounded Markdown/text prose path tokens ending in a
            # retired basename (bare same-directory, `./`, `../tools/`, and
            # bounded additional relative spellings), resolved exactly like a
            # Markdown link/front-matter path.
            for token_match in SHOWCASE_FIXTURE_PROSE_PATH_TOKEN_RE.finditer(line):
                if not _outside_external_href(line, token_match.start(1), token_match.end(1)):
                    continue
                raw_target = token_match.group(1)
                resolved = _mobile_dogfood_resolve(path, raw_target)
                if resolved in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
                    errors.append(
                        f"{relative_path}:{line_number}: active reference to retired "
                        f"{resolved}: prose path token {raw_target!r}: {stripped!r}"
                    )
                    reported_line_numbers.add(line_number)
                    break

        # Pass 6: every supported path-bearing front-matter key, resolved via
        # the actual parsed first-block YAML mapping.
        for key, raw_target in _mobile_dogfood_front_matter_path_values(text):
            resolved = _mobile_dogfood_resolve(path, raw_target)
            if resolved not in SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL:
                continue
            line_number, stripped = _mobile_dogfood_locate(lines, raw_target)
            if _is_allowed(stripped) or line_number in reported_line_numbers:
                continue
            errors.append(
                f"{relative_path}:{line_number}: active reference to retired "
                f"{resolved}: {key} entry {raw_target!r}"
            )


def check_showcase_fixture_family_types(errors: list[str]) -> None:
    for canonical_path in sorted(SHOWCASE_FIXTURE_CANONICAL_PATHS):
        meta, _ = parse_front_matter(canonical_path)
        if meta.get("relaylm_doc_type") != "operations":
            errors.append(
                f"{canonical_path}: must declare relaylm_doc_type: operations, not "
                f"{meta.get('relaylm_doc_type')!r} (never the retired runbook type)"
            )
        if meta.get("relaylm_status") != "current":
            errors.append(
                f"{canonical_path}: must declare relaylm_status: current, not "
                f"{meta.get('relaylm_status')!r}"
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


# ---------------------------------------------------------------------------
# Generic implementation-evidence completion-report validation.
#
# This family owns the continuing structural invariants for the completion
# reports that live in the canonical implementation-evidence directory:
# path boundary, the two accepted metadata profiles, shared and legacy-only
# metadata, required sections, the legacy exact-source snapshot, and
# unresolved placeholders. Exact source-PR number/URL agreement is owned
# independently by scripts/relaylm_mvp_completion_report_pr_link_smoke.py and
# is deliberately not duplicated or weakened here.
# ---------------------------------------------------------------------------
COMPLETION_REPORT_DIRECTORY = "docs/evidence/implementation"
COMPLETION_REPORT_SUFFIX = "_completion_report.md"

COMPLETION_REPORT_PROFILE_KEYS = (
    "relaylm_doc_type",
    "relaylm_status",
    "relaylm_volatility",
)
COMPLETION_REPORT_LEGACY_PROFILE = {
    "relaylm_doc_type": "implementation_completion_report",
    "relaylm_status": "historical_after_merge",
    "relaylm_volatility": "frozen",
}
COMPLETION_REPORT_CANONICAL_PROFILE = {
    "relaylm_doc_type": "evidence",
    "relaylm_status": "frozen",
    "relaylm_volatility": "low",
}

COMPLETION_REPORT_SHARED_METADATA = (
    "relaylm_current_status_source",
    "relaylm_source_pr",
    "relaylm_recorded_on",
)
COMPLETION_REPORT_LEGACY_METADATA = (
    "relaylm_source_commit",
    "relaylm_source_blob",
    "relaylm_source_content_sha256",
    "relaylm_exact_source_snapshot",
)

COMPLETION_REPORT_SECTIONS = (
    "Scope",
    "Implemented production boundary",
    "Preserved authorities and non-goals",
    "Changed files",
    "Validation evidence",
    "Known limitations",
    "Shared documentation update inputs",
    "Source pull request",
)
COMPLETION_REPORT_LEGACY_SECTIONS = ("Status and authority",)

COMPLETION_REPORT_PLACEHOLDERS = ("<slice>", "<number>", "TBD", "TO BE FILLED")


def _completion_report_paths() -> list[str]:
    directory = ROOT / COMPLETION_REPORT_DIRECTORY
    if not directory.is_dir():
        return []
    return [
        path.relative_to(ROOT).as_posix()
        for path in sorted(directory.glob("*" + COMPLETION_REPORT_SUFFIX))
    ]


def _completion_report_path_error(relative_path: str) -> str | None:
    """Reject anything outside the canonical evidence directory."""
    parts = Path(relative_path).parts
    if any(part in {".", ".."} for part in parts):
        return f"{relative_path}: completion-report path must not traverse directories"
    expected = Path(COMPLETION_REPORT_DIRECTORY).parts
    if len(parts) != len(expected) + 1 or parts[: len(expected)] != expected:
        return (
            f"{relative_path}: completion report must live directly under "
            f"{COMPLETION_REPORT_DIRECTORY}/"
        )
    if not parts[-1].endswith(COMPLETION_REPORT_SUFFIX):
        return f"{relative_path}: completion-report filename must end with {COMPLETION_REPORT_SUFFIX}"
    return None


def _completion_report_profile(relative_path: str, metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    candidate = {key: metadata.get(key) for key in COMPLETION_REPORT_PROFILE_KEYS}
    if candidate == COMPLETION_REPORT_LEGACY_PROFILE:
        return "legacy", None
    if candidate == COMPLETION_REPORT_CANONICAL_PROFILE:
        return "canonical", None
    return None, (
        f"{relative_path}: unrecognized or mixed completion-report profile "
        f"(doc_type={candidate['relaylm_doc_type']!r}, "
        f"status={candidate['relaylm_status']!r}, "
        f"volatility={candidate['relaylm_volatility']!r})"
    )


def check_implementation_evidence_completion_report(errors: list[str], relative_path: str) -> None:
    path_error = _completion_report_path_error(relative_path)
    if path_error is not None:
        errors.append(path_error)
        return

    try:
        metadata, body = parse_front_matter(relative_path)
    except (AssertionError, OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(str(exc))
        return

    profile, profile_error = _completion_report_profile(relative_path, metadata)
    if profile is None:
        errors.append(profile_error or f"{relative_path}: unusable completion-report profile")
        return

    required_metadata = COMPLETION_REPORT_SHARED_METADATA
    required_sections = COMPLETION_REPORT_SECTIONS
    if profile == "legacy":
        required_metadata += COMPLETION_REPORT_LEGACY_METADATA
        required_sections = COMPLETION_REPORT_LEGACY_SECTIONS + required_sections

    missing_metadata = [key for key in required_metadata if metadata.get(key) in (None, "")]
    if missing_metadata:
        errors.append(f"{relative_path}: missing completion-report metadata {missing_metadata!r}")

    missing_sections = [heading for heading in required_sections if f"## {heading}" not in body]
    if missing_sections:
        errors.append(f"{relative_path}: missing completion-report sections {missing_sections!r}")

    text = read_text(relative_path)
    for placeholder in COMPLETION_REPORT_PLACEHOLDERS:
        if placeholder in text:
            errors.append(f"{relative_path}: unresolved placeholder {placeholder!r}")

    current_source = metadata.get("relaylm_current_status_source")
    if isinstance(current_source, str) and current_source:
        target = ((ROOT / relative_path).parent / current_source).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{relative_path}: current-status source escapes repository")
        else:
            if not target.is_file():
                errors.append(
                    f"{relative_path}: missing relaylm_current_status_source {current_source}"
                )

    if profile != "legacy":
        return

    snapshot = metadata.get("relaylm_exact_source_snapshot")
    if not isinstance(snapshot, str) or not snapshot:
        return
    if "/" in snapshot or "\\" in snapshot or snapshot in {".", ".."}:
        errors.append(
            f"{relative_path}: relaylm_exact_source_snapshot must name a file beside the report"
        )
        return
    target = ((ROOT / relative_path).parent / snapshot).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"{relative_path}: exact source snapshot escapes repository")
        return
    if not target.is_file():
        errors.append(f"{relative_path}: missing exact source snapshot {snapshot}")


def check_implementation_evidence_completion_reports(errors: list[str]) -> None:
    for relative_path in _completion_report_paths():
        check_implementation_evidence_completion_report(errors, relative_path)


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

    maintenance_path = "docs/operations/consolidated-smoke-workflow-maintenance.md"
    maintenance = read_text(maintenance_path)
    inventory = read_text("docs/evidence/evaluations/scripts_inventory.md")
    for relative_path, text in (
        (maintenance_path, maintenance),
        ("docs/evidence/evaluations/scripts_inventory.md", inventory),
    ):
        if "generated/scripts_inventory.md" not in text:
            errors.append(f"{relative_path}: generated inventory output path missing")
        if "--output docs/evidence/evaluations/scripts_inventory.md" in text:
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
        "docs/operations/consolidated-smoke-workflow-maintenance.md",
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

    # 8. An exact -source.txt snapshot literal is allowlisted by filename pattern.
    def _source_snapshot_allowlisted() -> None:
        assert _mvp_reference_file_allowlisted(
            "docs/evidence/implementation/example_completion_report-source.txt"
        ), "-source.txt snapshot not allowlisted"

    check("exact -source.txt snapshot literal is allowlisted", _source_snapshot_allowlisted)

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

    # 17c. An unallowlisted occurrence in an active planning document is
    # rejected: no planning file is whole-file allowlisted for this literal.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/planning/example_planning_note.md",
            "---\nrelaylm_doc_type: planning\nrelaylm_status: current\n---\n\n"
            "stray unreviewed mention: lat1_retrieval_scaling_report\n",
        )
        check_rejects(
            "an unallowlisted occurrence in an active planning document is rejected",
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
            "docs/operations/lat1-retrieval-scaling.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_authority: lat1_method\n---\n\nBody.\n",
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
            "docs/operations/lat1-retrieval-scaling.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_authority: shared_key\n---\n\nBody.\n",
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
            "docs/operations/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/example_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            "- [method](mobile-dogfood-observation.md)\n",
        )
        check_silent(
            "a relative link to the canonical mobile-dogfood-observation.md target is allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # 74. A YAML mapping-key occurrence of the retired literal in an active
    # planning file is rejected: this family has no line allowlist entry, so
    # the plain-literal scan governs every such occurrence.
    override_key_line = f"  {mobile_dogfood_entry_retired}:\n    disposition: moved\n"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", override_key_line)
        check_rejects(
            "a YAML override key literal is rejected in an active planning file",
            check_no_live_mobile_dogfood_retired_paths,
            f"active reference to retired {mobile_dogfood_entry_retired}",
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
            "docs/operations/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/mobile-dogfood-entry.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/lat1-retrieval-scaling.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
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
            "docs/operations/mobile-dogfood-observation.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
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
        _mvp_write(base, "docs/operations/example_all_keys_relative.md", front_matter)
        check_silent(
            "relative canonical values for every supported path-bearing front-matter key are allowed",
            check_no_live_mobile_dogfood_retired_paths,
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Cutover 1C-42: Twin Extraction family retired-path guard self-tests.
    # ------------------------------------------------------------------
    # Derived at runtime from the constant, not hardcoded as Python source
    # text: this guard's literal-scan pass now covers its own .py source
    # file (every scanned suffix other than `.md`/`.txt`; see
    # check_no_live_twin_extraction_retired_paths above), so a hardcoded
    # retired-path fixture literal here would make this file fail its own
    # audit, exactly as the mobile-dogfood guard correction established.
    twin_prompts_retired = next(p for p in TWIN_EXTRACTION_RETIRED_PATHS if p.endswith("_prompts.md"))
    twin_runbook_retired = next(p for p in TWIN_EXTRACTION_RETIRED_PATHS if p.endswith("_runbook.md"))
    twin_workspace_retired = next(p for p in TWIN_EXTRACTION_RETIRED_PATHS if p.endswith("_candidates.md"))
    twin_prompts_canonical = TWIN_EXTRACTION_RETIRED_TO_CANONICAL[twin_prompts_retired]
    twin_runbook_canonical = TWIN_EXTRACTION_RETIRED_TO_CANONICAL[twin_runbook_retired]
    twin_workspace_canonical = TWIN_EXTRACTION_RETIRED_TO_CANONICAL[twin_workspace_retired]
    twin_anchor = "6-review-import-bridge-p1出力--cw-a4-governed-import-source"

    # 92. The real repository has no live reference to any retired
    # twin-extraction family path. Proves this file's own
    # TWIN_EXTRACTION_RETIRED_TO_CANONICAL dict-key entries and every
    # self-test fixture below are silent under the guard's real scan.
    check_silent(
        "real repository: no active reference to any retired twin-extraction path",
        check_no_live_twin_extraction_retired_paths,
    )

    # 93. Each of the three retired twin-extraction files being reintroduced
    # is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        for retired_path in TWIN_EXTRACTION_RETIRED_PATHS:
            _mvp_write(
                base,
                retired_path,
                "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
            )
        reintroduced_errors = []
        check_no_live_twin_extraction_retired_paths(reintroduced_errors)
        missing = [
            retired_path
            for retired_path in TWIN_EXTRACTION_RETIRED_PATHS
            if not any(retired_path in error and "reintroduced" in error for error in reintroduced_errors)
        ]
        results.append(
            (
                "each of the three reintroduced retired twin-extraction files is rejected",
                not missing,
                "" if not missing else f"missing rejection for: {missing!r}",
            )
        )
    ROOT = real_root

    # 94. A root-qualified Markdown link to a retired twin-extraction path is
    # rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_twin_extraction_root_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old runbook]({twin_runbook_retired}).\n",
        )
        check_rejects(
            "a root-qualified link to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 95. A same-directory bare-filename reference to a retired path (from
    # another file that was also under docs/tools/) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/tools/example_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old prompts]({twin_prompts_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a same-directory bare-filename reference resolving to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_prompts_retired}",
        )
    ROOT = real_root

    # 96. A "../tools/..." reference from a sibling directory resolving to a
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/operations/example_other.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old workspace flow](../tools/{twin_workspace_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../tools/... reference resolving to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_workspace_retired}",
        )
    ROOT = real_root

    # 97. A "../../tools/..." reference from a deeper directory resolving to a
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_other_twin.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n---\n\n"
            f"See [old prompts](../../tools/{twin_prompts_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../../tools/... reference resolving to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_prompts_retired}",
        )
    ROOT = real_root

    # 98. A Markdown link carrying the family's real Japanese-heading anchor
    # fragment still resolves (ignoring the anchor) to the retired runbook
    # path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_anchor_twin_extraction.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [bridge section]({twin_runbook_retired}#{twin_anchor}).\n",
        )
        check_rejects(
            "a Markdown link with the family's Japanese-heading anchor resolving to a retired path is rejected",
            check_no_live_twin_extraction_retired_paths,
            "markdown link target",
        )
    ROOT = real_root

    # 99. A relaylm_related_authority front-matter entry resolving to a
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/tools/example_related_authority.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {twin_runbook_retired.rsplit('/', 1)[-1]}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_authority entry resolving to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 100. A relaylm_current_status_source scalar front-matter entry
    # resolving to a retired path is rejected: proves the generic
    # multi-key front-matter coverage reused from the mobile-dogfood guard
    # (Cutover 1C-41) also applies to this guard, not only
    # relaylm_related_authority.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_current_status_source.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            f"relaylm_current_status_source: {twin_prompts_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_current_status_source scalar resolving to a retired twin-extraction path is rejected",
            check_no_live_twin_extraction_retired_paths,
            "relaylm_current_status_source entry",
        )
    ROOT = real_root

    # 101. A frozen/historical_after_merge document's own unallowlisted
    # mention of a retired twin-extraction path is REJECTED: this guard does
    # not fall back to a generic whole-document status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_twin_extraction_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            f"See [old runbook]({twin_runbook_retired}).\n",
        )
        check_rejects(
            "a frozen-status document's unallowlisted retired twin-extraction link is rejected without an exact line allowance",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 102. Root-qualified Markdown links to all three canonical
    # twin-extraction targets are allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        for canonical_path in TWIN_EXTRACTION_CANONICAL_PATHS:
            _mvp_write(
                base,
                canonical_path,
                "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
            )
        _mvp_write(
            base,
            "docs/example_root_qualified_twin_extraction_links.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            + "\n".join(
                f"- [target]({canonical_path})" for canonical_path in sorted(TWIN_EXTRACTION_CANONICAL_PATHS)
            )
            + "\n",
        )
        check_silent(
            "root-qualified links to all three canonical twin-extraction targets are allowed",
            check_no_live_twin_extraction_retired_paths,
        )
    ROOT = real_root

    # 103. A relative link to a canonical target from a sibling document in
    # the same (docs/operations/) directory is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_runbook_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/example_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            f"- [runbook]({twin_runbook_canonical.rsplit('/', 1)[-1]})\n",
        )
        check_silent(
            "a relative link to the canonical twin-extraction.md target is allowed",
            check_no_live_twin_extraction_retired_paths,
        )
    ROOT = real_root

    # 104/105. A YAML mapping-key occurrence of a retired twin-extraction
    # literal in an active planning file is rejected: this family has no line
    # allowlist entry, so the plain-literal scan governs every occurrence.
    twin_override_key_line = f"  {twin_runbook_retired}:\n    disposition: moved\n"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", twin_override_key_line)
        check_rejects(
            "a twin-extraction YAML override key literal is rejected in an active planning file",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 106. Zero duplicate live copies: a retired path coexisting with its
    # own already-created canonical target is still rejected for the
    # retired path.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_workspace_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            twin_workspace_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a retired twin-extraction file coexisting with its own canonical target (duplicate live copy) is rejected",
            check_no_live_twin_extraction_retired_paths,
            "retired twin-extraction family path reintroduced",
        )
    ROOT = real_root

    # 107. The real repository's twin-extraction family declares the correct
    # canonical operations doc type on all three targets.
    check_silent(
        "the real repository's twin-extraction family declares relaylm_doc_type: operations",
        check_twin_extraction_family_types,
    )

    # 108. A twin-extraction canonical target synthetically typed as the
    # retired runbook type is rejected: reject-then-allow pairing proving
    # check_twin_extraction_family_types actually fires.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_prompts_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            twin_runbook_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            twin_workspace_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a twin-extraction canonical target synthetically typed as the retired runbook type is rejected",
            check_twin_extraction_family_types,
            "must declare relaylm_doc_type: operations",
        )
    ROOT = real_root

    # 109. This guard's own implementation file: the retired-path mapping
    # constant's own dict-key entries remain narrowly allowed (exact-line
    # equality, not a whole-file exemption), mirroring
    # MOBILE_DOGFOOD_SELF_FILE_EXACT_LINES.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            TWIN_EXTRACTION_SELF_FILE,
            "TWIN_EXTRACTION_RETIRED_TO_CANONICAL: dict[str, str] = {\n"
            + "".join(
                f'    "{retired_path}": "{canonical_path}",\n'
                for retired_path, canonical_path in TWIN_EXTRACTION_RETIRED_TO_CANONICAL.items()
            )
            + "}\n",
        )
        check_silent(
            "the twin-extraction retired-path mapping constant's own dict-key entries remain allowed in the self-file",
            check_no_live_twin_extraction_retired_paths,
        )
    ROOT = real_root

    # 110. A retired twin-extraction literal appearing in an UNRELATED,
    # non-allowlisted Python constant inside this guard's own implementation
    # file is still rejected: the self-file allowance is exact-line, not
    # whole-file.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            TWIN_EXTRACTION_SELF_FILE,
            "SOME_OTHER_CONSTANT = (\n"
            f'    "{twin_prompts_retired}",\n'
            ")\n",
        )
        check_rejects(
            "a retired twin-extraction literal in an unrelated self-file constant is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_prompts_retired}",
        )
    ROOT = real_root

    # 111. A retired-path Markdown link written INSIDE one of the three
    # canonical Twin Extraction documents themselves is rejected: proves
    # there is no canonical-path scan bypass (Cutover 1C-42 correction).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_runbook_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\n"
            f"See [old prompts]({twin_prompts_retired}).\n",
        )
        check_rejects(
            "a retired-path Markdown link written inside a canonical twin-extraction document is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_prompts_retired}",
        )
    ROOT = real_root

    # 112. A retired-path front-matter path-bearing value written INSIDE a
    # canonical Twin Extraction document is rejected: same bypass-proof as
    # #111 but through the front-matter pass rather than the Markdown-link
    # pass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_workspace_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {twin_runbook_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a retired-path front-matter value written inside a canonical twin-extraction document is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 113. A valid link FROM one canonical Twin Extraction document TO
    # another canonical Twin Extraction document remains accepted: scanning
    # canonical documents (#111/#112) does not turn legitimate inter-family
    # links into false positives.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            twin_prompts_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\n"
            f"See [runbook]({twin_runbook_canonical}).\n",
        )
        _mvp_write(
            base,
            twin_runbook_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\n"
            f"See [workspace flow]({twin_workspace_canonical}).\n",
        )
        _mvp_write(
            base,
            twin_workspace_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_silent(
            "a valid link from one canonical twin-extraction document to another remains accepted",
            check_no_live_twin_extraction_retired_paths,
        )
    ROOT = real_root

    # 113b. The guard's own exact self-file line is silent: the surviving
    # exact-line allowance this family still carries, and the positive half
    # that makes the three exact-equality rejections below non-vacuous.
    twin_self_line = f'"{twin_runbook_retired}": "{twin_runbook_canonical}",'
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, TWIN_EXTRACTION_SELF_FILE, f"    {twin_self_line}\n")
        check_silent(
            "the guard's own exact self-file dict line is allowed",
            check_no_live_twin_extraction_retired_paths,
        )
    ROOT = real_root

    # 114. The exact self-file allowance line with an extra LEADING prefix on
    # the same physical line is rejected: proves the allowance match is exact
    # stripped-line equality, not substring containment (Cutover 1C-42
    # correction).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, TWIN_EXTRACTION_SELF_FILE, f"    # see also {twin_self_line}\n")
        check_rejects(
            "a self-file line with an extra leading prefix is rejected, not allowed by substring containment",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 115. The exact self-file allowance line with an extra TRAILING suffix on
    # the same physical line is rejected: same exact-equality proof as #114
    # from the other side.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, TWIN_EXTRACTION_SELF_FILE, f"    {twin_self_line}  # temporary note\n")
        check_rejects(
            "a self-file line with an extra trailing suffix is rejected, not allowed by substring containment",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_runbook_retired}",
        )
    ROOT = real_root

    # 116. A self-file line that names the allowed retired path plus a second,
    # unrelated retired-path reference on the same physical line is rejected:
    # the allowance covers only its own exact single-path line, not any line
    # that happens to contain it.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            TWIN_EXTRACTION_SELF_FILE,
            f"    {twin_self_line} {twin_prompts_retired}\n",
        )
        check_rejects(
            "a line combining the allowed retired path with an unrelated second retired-path reference is rejected",
            check_no_live_twin_extraction_retired_paths,
            "active reference to retired",
        )
    ROOT = real_root

    # 117. A retired twin-extraction path literal in pyproject.toml is
    # rejected: pyproject.toml is returned by the shared reference scanner
    # but carries no `.md`/`.txt` suffix, so it is only covered because the
    # literal-scan branch now applies to every non-`.md`/`.txt` suffix
    # rather than a fixed positive suffix allowlist (Cutover 1C-42
    # correction; previously `.toml` was silently excluded).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "pyproject.toml",
            "[tool.example]\n" f'note = "{twin_workspace_retired}"\n',
        )
        check_rejects(
            "a retired twin-extraction path literal in pyproject.toml is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_workspace_retired}",
        )
    ROOT = real_root

    # 118. A retired twin-extraction path literal in config.example.yaml (a
    # second root-scanned non-Markdown file, distinct from pyproject.toml)
    # is also rejected: confirms the restructured suffix branch generalizes
    # to every non-`.md`/`.txt` file the scanner returns, not only the one
    # previously-missing `.toml` case.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "config.example.yaml",
            f"# note: {twin_prompts_retired}\n",
        )
        check_rejects(
            "a retired twin-extraction path literal in config.example.yaml is rejected",
            check_no_live_twin_extraction_retired_paths,
            f"active reference to retired {twin_prompts_retired}",
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Cutover 1C-43: Consolidated Smoke Workflow Maintenance retired-path
    # guard self-tests, following the CORRECTED Cutover 1C-42 twin-extraction
    # pattern for a single-member family (no canonical-path scan bypass,
    # exact stripped-line allowlist equality, non-Markdown literal scan on
    # every non-`.md`/`.txt` suffix).
    # ------------------------------------------------------------------
    smoke_maintenance_retired = SMOKE_MAINTENANCE_RETIRED_PATHS[0]
    smoke_maintenance_canonical = SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL[smoke_maintenance_retired]
    smoke_maintenance_anchor = "validation"

    # 119. The real repository has no live reference to the retired
    # smoke-workflow-maintenance path.
    check_silent(
        "real repository: no active reference to the retired smoke-workflow-maintenance path",
        check_no_live_smoke_maintenance_retired_paths,
    )

    # 120. The retired smoke-workflow-maintenance file being reintroduced is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "the reintroduced retired smoke-workflow-maintenance file is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"{smoke_maintenance_retired}: retired smoke-workflow-maintenance path reintroduced",
        )
    ROOT = real_root

    # 121. A root-qualified Markdown link to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_smoke_maintenance_root_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old maintenance doc]({smoke_maintenance_retired}).\n",
        )
        check_rejects(
            "a root-qualified link to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 122. A same-directory bare-filename reference (from another file still
    # under docs/smoke/) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old maintenance doc]({smoke_maintenance_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a same-directory bare-filename reference resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 123. A "../smoke/..." reference from a sibling directory (docs/operations/)
    # resolving to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/operations/example_other.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old maintenance doc](../smoke/{smoke_maintenance_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../smoke/... reference resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 124. A "../../smoke/..." reference from a deeper directory resolving to
    # the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_other_smoke_maintenance.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n---\n\n"
            f"See [old maintenance doc](../../smoke/{smoke_maintenance_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../../smoke/... reference resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 125. A Markdown link carrying a heading anchor fragment still resolves
    # (ignoring the anchor) to the retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_anchor_smoke_maintenance.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [validation section]({smoke_maintenance_retired}#{smoke_maintenance_anchor}).\n",
        )
        check_rejects(
            "a Markdown link with a heading anchor resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            "markdown link target",
        )
    ROOT = real_root

    # 126. A relaylm_related_authority front-matter entry resolving to the
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_related_authority.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {smoke_maintenance_retired.rsplit('/', 1)[-1]}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_authority entry resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 127. A relaylm_current_status_source scalar front-matter entry
    # resolving to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_current_status_source_smoke_maintenance.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            f"relaylm_current_status_source: {smoke_maintenance_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_current_status_source scalar resolving to the retired smoke-workflow-maintenance path is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            "relaylm_current_status_source entry",
        )
    ROOT = real_root

    # 128. A frozen/historical_after_merge document's own unallowlisted
    # mention of the retired path is REJECTED: no generic whole-document
    # status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_smoke_maintenance_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            f"See [old maintenance doc]({smoke_maintenance_retired}).\n",
        )
        check_rejects(
            "a frozen-status document's unallowlisted retired smoke-workflow-maintenance link is rejected without an exact line allowance",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 129. A root-qualified Markdown link to the canonical target is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/example_root_qualified_smoke_maintenance_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"- [target]({smoke_maintenance_canonical})\n",
        )
        check_silent(
            "a root-qualified link to the canonical smoke-workflow-maintenance target is allowed",
            check_no_live_smoke_maintenance_retired_paths,
        )
    ROOT = real_root

    # 130. A relative link to the canonical target from a sibling document in
    # the same (docs/operations/) directory is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/example_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            f"- [maintenance]({smoke_maintenance_canonical.rsplit('/', 1)[-1]})\n",
        )
        check_silent(
            "a relative link to the canonical smoke-workflow-maintenance target is allowed",
            check_no_live_smoke_maintenance_retired_paths,
        )
    ROOT = real_root

    # 131/132. A YAML mapping-key occurrence of the retired
    # smoke-workflow-maintenance literal in an active planning file is
    # rejected: this family has no line allowlist entry, so the plain-literal
    # scan governs every occurrence.
    smoke_maintenance_override_key_line = f"  {smoke_maintenance_retired}:\n    disposition: moved\n"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", smoke_maintenance_override_key_line)
        check_rejects(
            "a smoke-workflow-maintenance YAML override key literal is rejected in an active planning file",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 133. Zero duplicate live copies: the retired path coexisting with its
    # own already-created canonical target is still rejected for the retired
    # path.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "the retired smoke-workflow-maintenance file coexisting with its own canonical target (duplicate live copy) is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            "retired smoke-workflow-maintenance path reintroduced",
        )
    ROOT = real_root

    # 134. The real repository's canonical smoke-workflow-maintenance target
    # declares both the correct operations doc type AND relaylm_status: current.
    check_silent(
        "the real repository's smoke-workflow-maintenance canonical target declares relaylm_doc_type: operations and relaylm_status: current",
        check_smoke_maintenance_family_types,
    )

    # 135a. Wrong doc type + correct status ("runbook" + "current") is rejected
    # for the doc-type mismatch: reject-then-allow pairing proving
    # check_smoke_maintenance_family_types actually fires on relaylm_doc_type.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a smoke-workflow-maintenance canonical target synthetically typed as the retired runbook type (correct status) is rejected",
            check_smoke_maintenance_family_types,
            "must declare relaylm_doc_type: operations",
        )
    ROOT = real_root

    # 135b. Correct doc type + wrong status ("operations" + "target") is
    # rejected for the status mismatch: proves check_smoke_maintenance_family_types
    # also fires on relaylm_status independently of relaylm_doc_type.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_rejects(
            "a smoke-workflow-maintenance canonical target with the correct doc type but a wrong relaylm_status is rejected",
            check_smoke_maintenance_family_types,
            "must declare relaylm_status: current",
        )
    ROOT = real_root

    # 135c. Wrong doc type AND wrong status ("runbook" + "target") produces
    # both independent diagnostics in the same run: proves the two checks are
    # independent, not short-circuiting on the first mismatch.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: target\n---\n\nBody.\n",
        )
        both_errors: list[str] = []
        check_smoke_maintenance_family_types(both_errors)
        has_type_error = any("must declare relaylm_doc_type: operations" in error for error in both_errors)
        has_status_error = any("must declare relaylm_status: current" in error for error in both_errors)
        ok = has_type_error and has_status_error
        results.append(
            (
                "a smoke-workflow-maintenance canonical target with both a wrong doc type and a wrong status produces both independent diagnostics",
                ok,
                "" if ok else f"errors: {both_errors!r}",
            )
        )
    ROOT = real_root

    # 135d. The correct operations/current profile is accepted (reject-then-allow
    # completion: 135a-c proved rejection, this proves acceptance at the exact
    # correct profile).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_silent(
            "a smoke-workflow-maintenance canonical target with the correct operations/current profile is accepted",
            check_smoke_maintenance_family_types,
        )
    ROOT = real_root

    # 136. This guard's own implementation file: the retired-path mapping
    # constant's own dict-key entry remains narrowly allowed (exact-line
    # equality, not a whole-file exemption).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            SMOKE_MAINTENANCE_SELF_FILE,
            "SMOKE_MAINTENANCE_RETIRED_TO_CANONICAL: dict[str, str] = {\n"
            f'    "{smoke_maintenance_retired}": "{smoke_maintenance_canonical}",\n'
            "}\n",
        )
        check_silent(
            "the smoke-workflow-maintenance retired-path mapping constant's own dict-key entry remains allowed in the self-file",
            check_no_live_smoke_maintenance_retired_paths,
        )
    ROOT = real_root

    # 137. A retired smoke-workflow-maintenance literal appearing in an
    # UNRELATED, non-allowlisted Python constant inside this guard's own
    # implementation file is still rejected: the self-file allowance is
    # exact-line, not whole-file.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            SMOKE_MAINTENANCE_SELF_FILE,
            "SOME_OTHER_CONSTANT = (\n" f'    "{smoke_maintenance_retired}",\n' ")\n",
        )
        check_rejects(
            "a retired smoke-workflow-maintenance literal in an unrelated self-file constant is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 138. A retired-path Markdown link written INSIDE the canonical
    # smoke-workflow-maintenance document itself is rejected: proves there is
    # no canonical-path scan bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\n"
            f"See [old self-link]({smoke_maintenance_retired}).\n",
        )
        check_rejects(
            "a retired-path Markdown link written inside the canonical smoke-workflow-maintenance document is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 139. A retired-path front-matter path-bearing value written INSIDE the
    # canonical document is rejected: same bypass-proof as #138 through the
    # front-matter pass rather than the Markdown-link pass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {smoke_maintenance_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a retired-path front-matter value written inside the canonical smoke-workflow-maintenance document is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 140. A valid link FROM the canonical smoke-workflow-maintenance document
    # TO an unrelated canonical document (mobile-dogfood-entry.md) remains
    # accepted: scanning the canonical document (#138/#139) does not turn a
    # legitimate, unrelated link into a false positive.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            smoke_maintenance_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\n"
            "See [mobile dogfood entry](mobile-dogfood-entry.md).\n",
        )
        _mvp_write(
            base,
            "docs/operations/mobile-dogfood-entry.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_silent(
            "a valid link from the canonical smoke-workflow-maintenance document to an unrelated document remains accepted",
            check_no_live_smoke_maintenance_retired_paths,
        )
    ROOT = real_root

    # 140b. The guard's own exact self-file line is silent: the surviving
    # exact-line allowance this family still carries, and the positive half
    # that makes the two exact-equality rejections below non-vacuous.
    smoke_maintenance_self_line = (
        f'"{smoke_maintenance_retired}": "{smoke_maintenance_canonical}",'
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, SMOKE_MAINTENANCE_SELF_FILE, f"    {smoke_maintenance_self_line}\n")
        check_silent(
            "the guard's own exact self-file dict line is allowed",
            check_no_live_smoke_maintenance_retired_paths,
        )
    ROOT = real_root

    # 141. The exact self-file allowance line with an extra LEADING prefix on
    # the same physical line is rejected: proves the allowance match is exact
    # stripped-line equality, not substring containment.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            SMOKE_MAINTENANCE_SELF_FILE,
            f"    # see also {smoke_maintenance_self_line}\n",
        )
        check_rejects(
            "a self-file line with an extra leading prefix is rejected, not allowed by substring containment",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 142. The exact self-file allowance line with an extra TRAILING suffix on
    # the same physical line is rejected: same exact-equality proof as #141
    # from the other side.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            SMOKE_MAINTENANCE_SELF_FILE,
            f"    {smoke_maintenance_self_line}  # temporary note\n",
        )
        check_rejects(
            "a self-file line with an extra trailing suffix is rejected, not allowed by substring containment",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 144. A retired smoke-workflow-maintenance path literal in
    # pyproject.toml is rejected: pyproject.toml is returned by the shared
    # reference scanner but carries no `.md`/`.txt` suffix, so it is only
    # covered because the literal-scan branch applies to every
    # non-`.md`/`.txt` suffix rather than a fixed positive suffix allowlist.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "pyproject.toml",
            "[tool.example]\n" f'note = "{smoke_maintenance_retired}"\n',
        )
        check_rejects(
            "a retired smoke-workflow-maintenance path literal in pyproject.toml is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # 145. A retired smoke-workflow-maintenance path literal in
    # config.example.yaml (a second root-scanned non-Markdown file, distinct
    # from pyproject.toml) is also rejected: confirms the suffix branch
    # generalizes to every non-`.md`/`.txt` file the scanner returns.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "config.example.yaml",
            f"# note: {smoke_maintenance_retired}\n",
        )
        check_rejects(
            "a retired smoke-workflow-maintenance path literal in config.example.yaml is rejected",
            check_no_live_smoke_maintenance_retired_paths,
            f"active reference to retired {smoke_maintenance_retired}",
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Cutover 1C-44: O1 Manual One-Round retired-path guard self-tests,
    # following the CORRECTED Cutover 1C-43 smoke-maintenance pattern for a
    # single-member family (no canonical-path scan bypass, exact
    # stripped-line allowlist equality, non-Markdown literal scan on every
    # non-`.md`/`.txt` suffix), adapted for this family's canonical
    # `relaylm_status: compatibility` profile (not `current`).
    # ------------------------------------------------------------------
    o1_retired = O1_MANUAL_ONE_ROUND_RETIRED_PATHS[0]
    o1_canonical = O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL[o1_retired]
    o1_anchor = "purpose"

    # 158. The real repository has no live reference to the retired
    # o1-manual-one-round path.
    check_silent(
        "real repository: no active reference to the retired o1-manual-one-round path",
        check_no_live_o1_manual_one_round_retired_paths,
    )

    # 159. The retired o1-manual-one-round file being reintroduced is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        check_rejects(
            "the reintroduced retired o1-manual-one-round file is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"{o1_retired}: retired o1-manual-one-round path reintroduced",
        )
    ROOT = real_root

    # 160. A root-qualified Markdown link to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_o1_root_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old O1 runbook]({o1_retired}).\n",
        )
        check_rejects(
            "a root-qualified link to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 161. A same-directory bare-filename reference (from another file still
    # under docs/smoke/) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_o1_sibling.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old O1 runbook]({o1_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a same-directory bare-filename reference resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 162. A "./..." same-directory reference (explicit current-directory
    # prefix, distinct from the bare-filename form in #161) resolving to the
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_o1_dot_slash.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old O1 runbook](./{o1_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ./... same-directory reference resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 163. A "../smoke/..." reference from a sibling directory
    # (docs/operations/) resolving to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/operations/example_o1_other.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old O1 runbook](../smoke/{o1_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../smoke/... reference resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 164. A "../../smoke/..." reference from a deeper directory resolving to
    # the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_other_o1.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: current\n---\n\n"
            f"See [old O1 runbook](../../smoke/{o1_retired.rsplit('/', 1)[-1]}).\n",
        )
        check_rejects(
            "a ../../smoke/... reference resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 165. A Markdown link carrying a heading anchor fragment still resolves
    # (ignoring the anchor) to the retired path and is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_anchor_o1.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [purpose section]({o1_retired}#{o1_anchor}).\n",
        )
        check_rejects(
            "a Markdown link with a heading anchor resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "markdown link target",
        )
    ROOT = real_root

    # 166. A relaylm_related_authority front-matter entry resolving to the
    # retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_o1_related_authority.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {o1_retired.rsplit('/', 1)[-1]}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_related_authority entry resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "relaylm_related_authority entry",
        )
    ROOT = real_root

    # 167. A relaylm_current_status_source scalar front-matter entry
    # resolving to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_current_status_source_o1.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n"
            f"relaylm_current_status_source: {o1_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a relaylm_current_status_source scalar resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "relaylm_current_status_source entry",
        )
    ROOT = real_root

    # 168. A frozen/historical_after_merge document's own unallowlisted
    # mention of the retired path is REJECTED: no generic whole-document
    # status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_o1_report.md",
            "---\nrelaylm_doc_type: implementation_completion_report\nrelaylm_status: historical_after_merge\n---\n\n"
            f"See [old O1 runbook]({o1_retired}).\n",
        )
        check_rejects(
            "a frozen-status document's unallowlisted retired o1-manual-one-round link is rejected without an exact line allowance",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 169. A root-qualified Markdown link to the canonical target is allowed.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/example_root_qualified_o1_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"- [target]({o1_canonical})\n",
        )
        check_silent(
            "a root-qualified link to the canonical o1-manual-one-round target is allowed",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 170. A relative link to the canonical target from a sibling document in
    # the same (docs/operations/) directory is allowed: also proves the
    # canonical name (o1-manual-one-round.md) is distinguished from the
    # retired name (o1_manual_one_round_runbook.md) rather than fuzzy-matched.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            "docs/operations/example_o1_index.md",
            "---\nrelaylm_doc_type: documentation_index\nrelaylm_status: current\n---\n\n"
            f"- [o1 runbook]({o1_canonical.rsplit('/', 1)[-1]})\n",
        )
        check_silent(
            "a relative link to the canonical o1-manual-one-round target is allowed",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 171/172. A YAML mapping-key occurrence of the retired o1-manual-one-round
    # literal in an active planning file is rejected: this family has no line
    # allowlist entry, so the plain-literal scan governs every occurrence.
    o1_override_key_line = f"  {o1_retired}:\n    disposition: moved\n"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", o1_override_key_line)
        check_rejects(
            "an o1-manual-one-round YAML override key literal is rejected in an active planning file",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 173. Zero duplicate live copies: the retired path coexisting with its
    # own already-created canonical target is still rejected for the retired
    # path.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        check_rejects(
            "the retired o1-manual-one-round file coexisting with its own canonical target (duplicate live copy) is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "retired o1-manual-one-round path reintroduced",
        )
    ROOT = real_root

    # 174. The real repository's canonical o1-manual-one-round target
    # declares both the correct operations doc type AND
    # relaylm_status: compatibility.
    check_silent(
        "the real repository's o1-manual-one-round canonical target declares relaylm_doc_type: operations and relaylm_status: compatibility",
        check_o1_manual_one_round_family_types,
    )

    # 175a. Wrong doc type + correct status ("runbook" + "compatibility") is
    # rejected for the doc-type mismatch: reject-then-allow pairing proving
    # check_o1_manual_one_round_family_types actually fires on
    # relaylm_doc_type.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        check_rejects(
            "an o1-manual-one-round canonical target synthetically typed as the retired runbook type (correct status) is rejected",
            check_o1_manual_one_round_family_types,
            "must declare relaylm_doc_type: operations",
        )
    ROOT = real_root

    # 175b. Correct doc type + wrong status ("operations" + "current") is
    # rejected for the status mismatch: proves
    # check_o1_manual_one_round_family_types also fires on relaylm_status
    # independently of relaylm_doc_type.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "an o1-manual-one-round canonical target with the correct doc type but a wrong relaylm_status is rejected",
            check_o1_manual_one_round_family_types,
            "must declare relaylm_status: compatibility",
        )
    ROOT = real_root

    # 175c. Wrong doc type AND wrong status ("runbook" + "current") produces
    # both independent diagnostics in the same run: proves the two checks are
    # independent, not short-circuiting on the first mismatch.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        both_o1_errors: list[str] = []
        check_o1_manual_one_round_family_types(both_o1_errors)
        has_o1_type_error = any("must declare relaylm_doc_type: operations" in error for error in both_o1_errors)
        has_o1_status_error = any("must declare relaylm_status: compatibility" in error for error in both_o1_errors)
        ok = has_o1_type_error and has_o1_status_error
        results.append(
            (
                "an o1-manual-one-round canonical target with both a wrong doc type and a wrong status produces both independent diagnostics",
                ok,
                "" if ok else f"errors: {both_o1_errors!r}",
            )
        )
    ROOT = real_root

    # 175d. The correct operations/compatibility profile is accepted
    # (reject-then-allow completion: 175a-c proved rejection, this proves
    # acceptance at the exact correct profile).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\nBody.\n",
        )
        check_silent(
            "an o1-manual-one-round canonical target with the correct operations/compatibility profile is accepted",
            check_o1_manual_one_round_family_types,
        )
    ROOT = real_root

    # 176. This guard's own implementation file: the retired-path mapping
    # constant's own dict-key entry remains narrowly allowed (exact-line
    # equality, not a whole-file exemption).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            O1_MANUAL_ONE_ROUND_SELF_FILE,
            "O1_MANUAL_ONE_ROUND_RETIRED_TO_CANONICAL: dict[str, str] = {\n"
            f'    "{o1_retired}": "{o1_canonical}",\n'
            "}\n",
        )
        check_silent(
            "the o1-manual-one-round retired-path mapping constant's own dict-key entry remains allowed in the self-file",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 177. A retired o1-manual-one-round literal appearing in an UNRELATED,
    # non-allowlisted Python constant inside this guard's own implementation
    # file is still rejected: the self-file allowance is exact-line, not
    # whole-file.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            O1_MANUAL_ONE_ROUND_SELF_FILE,
            "SOME_OTHER_O1_CONSTANT = (\n" f'    "{o1_retired}",\n' ")\n",
        )
        check_rejects(
            "a retired o1-manual-one-round literal in an unrelated self-file constant is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 178. A retired-path Markdown link written INSIDE the canonical
    # o1-manual-one-round document itself is rejected: proves there is no
    # canonical-path scan bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\n"
            f"See [old self-link]({o1_retired}).\n",
        )
        check_rejects(
            "a retired-path Markdown link written inside the canonical o1-manual-one-round document is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 179. A retired-path front-matter path-bearing value written INSIDE the
    # canonical document is rejected: same bypass-proof as #178 through the
    # front-matter pass rather than the Markdown-link pass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n"
            "relaylm_related_authority:\n"
            f"  - {o1_retired}\n"
            "---\n\nBody.\n",
        )
        check_rejects(
            "a retired-path front-matter value written inside the canonical o1-manual-one-round document is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 180. A valid link FROM the canonical o1-manual-one-round document TO an
    # unrelated canonical document (mobile-dogfood-entry.md) remains
    # accepted: scanning the canonical document (#178/#179) does not turn a
    # legitimate, unrelated link into a false positive.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            o1_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: compatibility\n---\n\n"
            "See [mobile dogfood entry](mobile-dogfood-entry.md).\n",
        )
        _mvp_write(
            base,
            "docs/operations/mobile-dogfood-entry.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_silent(
            "a valid link from the canonical o1-manual-one-round document to an unrelated document remains accepted",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 180b. The guard's own exact self-file line is silent: the surviving
    # exact-line allowance this family still carries, and the positive half
    # that makes the two exact-equality rejections below non-vacuous.
    o1_self_line = f'"{o1_retired}": "{o1_canonical}",'
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, O1_MANUAL_ONE_ROUND_SELF_FILE, f"    {o1_self_line}\n")
        check_silent(
            "the guard's own exact self-file dict line is allowed",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 181. The exact self-file allowance line with an extra LEADING prefix on
    # the same physical line is rejected: proves the allowance match is exact
    # stripped-line equality, not substring containment.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, O1_MANUAL_ONE_ROUND_SELF_FILE, f"    # see also {o1_self_line}\n")
        check_rejects(
            "a self-file line with an extra leading prefix is rejected, not allowed by substring containment",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 182. The exact self-file allowance line with an extra TRAILING suffix on
    # the same physical line is rejected: same exact-equality proof as #181
    # from the other side.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, O1_MANUAL_ONE_ROUND_SELF_FILE, f"    {o1_self_line}  # temporary note\n")
        check_rejects(
            "a self-file line with an extra trailing suffix is rejected, not allowed by substring containment",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 184. A retired o1-manual-one-round path literal in pyproject.toml is
    # rejected: pyproject.toml is returned by the shared reference scanner
    # but carries no `.md`/`.txt` suffix, so it is only covered because the
    # literal-scan branch applies to every non-`.md`/`.txt` suffix rather
    # than a fixed positive suffix allowlist.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "pyproject.toml",
            "[tool.example]\n" f'note = "{o1_retired}"\n',
        )
        check_rejects(
            "a retired o1-manual-one-round path literal in pyproject.toml is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 185. A retired o1-manual-one-round path literal in config.example.yaml
    # (a second root-scanned non-Markdown file, distinct from
    # pyproject.toml's `.toml` suffix used in #184) is also rejected:
    # confirms the suffix branch generalizes to every non-`.md`/`.txt` file
    # the scanner returns, not just one fixture suffix.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "config.example.yaml",
            f"# note: {o1_retired}\n",
        )
        check_rejects(
            "a retired o1-manual-one-round path literal in config.example.yaml is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Codex review correction (PR #610, commit 8426a0d): the Markdown-link
    # and front-matter passes alone were silent on a plain-prose or
    # backtick-quoted mention of the retired path inside an active `.md`
    # document (not expressed as a Markdown link or front-matter value).
    # These assertions cover the added Pass 3 literal scan for `.md`/`.txt`
    # files.
    # ------------------------------------------------------------------

    # 186. A prose/backtick mention of the root-qualified retired path in a
    # non-allowlisted .md file (no Markdown link syntax) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_o1_prose_mention.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See the retired `{o1_retired}` path for historical context.\n",
        )
        check_rejects(
            "a prose/backtick mention of the retired o1-manual-one-round path in a non-allowlisted .md file is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 187. A backtick mention of the retired path in a frozen-status .md
    # document is still rejected: no generic frozen/historical bypass for
    # prose mentions, matching the existing no-generic-status-bypass proof
    # for the link form (test #168).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_o1_frozen_prose.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n\n"
            f"Historical note mentioning `{o1_retired}` in passing.\n",
        )
        check_rejects(
            "a backtick mention of the retired o1-manual-one-round path in a frozen-status .md document is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 189. A .txt file carrying the literal (not covered by the shared
    # scanner's suffix list, so scanned only via this guard's own
    # docs/**/*.txt extension) is rejected when not allowlisted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_o1_mention-source.txt",
            f"Frozen source text mentioning {o1_retired} verbatim.\n",
        )
        check_rejects(
            "a .txt file carrying the retired o1-manual-one-round literal is rejected when not allowlisted",
            check_no_live_o1_manual_one_round_retired_paths,
            f"active reference to retired {o1_retired}",
        )
    ROOT = real_root

    # 190. The canonical target path literal in prose is accepted: the
    # literal scan distinguishes the canonical hyphenated path from the
    # retired underscored path rather than flagging any O1-related mention.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_o1_canonical_prose_mention.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See the canonical `{o1_canonical}` path for current guidance.\n",
        )
        check_silent(
            "the canonical o1-manual-one-round target path literal in prose is accepted, distinguished from the retired path",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Second Codex review round (PR #610, reviewed head 78715d3): bare
    # retired-basename detection in docs/smoke/ prose/backticks (Pass 4).
    # ------------------------------------------------------------------

    # 192. Codex's exact repro: a synthetic docs/smoke/ document mentioning
    # only the bare backtick basename (no directory prefix, not a Markdown
    # link) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See `{o1_retired.rsplit('/', 1)[-1]}` for background.\n",
        )
        check_rejects(
            "a bare retired o1-manual-one-round basename in docs/smoke/ backtick prose is rejected (Codex second-round repro)",
            check_no_live_o1_manual_one_round_retired_paths,
            "prose path token",
        )
    ROOT = real_root

    # 193. A bare retired basename in plain prose under docs/smoke/ is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_plain.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See {o1_retired.rsplit('/', 1)[-1]} for background.\n",
        )
        check_rejects(
            "a bare retired o1-manual-one-round basename in docs/smoke/ plain prose is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "prose path token",
        )
    ROOT = real_root

    # 194. A ./ retired basename in plain prose under docs/smoke/ is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example_dot_plain.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See ./{o1_retired.rsplit('/', 1)[-1]} for background.\n",
        )
        check_rejects(
            "a ./ retired o1-manual-one-round basename in docs/smoke/ plain prose is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "prose path token",
        )
    ROOT = real_root

    # 195. A ../smoke/ retired path token in prose from docs/operations/ is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/operations/example_plain.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See ../smoke/{o1_retired.rsplit('/', 1)[-1]} for background.\n",
        )
        check_rejects(
            "a ../smoke/ retired o1-manual-one-round prose token from another docs collection is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "prose path token",
        )
    ROOT = real_root

    # 196. A bounded additional relative spelling resolving to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_plain.md",
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: current\n---\n\n"
            f"See ../../smoke/{o1_retired.rsplit('/', 1)[-1]} for background.\n",
        )
        check_rejects(
            "a bounded additional relative retired o1-manual-one-round prose token is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "prose path token",
        )
    ROOT = real_root

    # 197. A double-quoted relative HTML href from docs/README.md resolving
    # to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"<a href=\"smoke/{o1_retired.rsplit('/', 1)[-1]}\">old authority</a>\n",
        )
        check_rejects(
            "a double-quoted relative HTML href resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "HTML href",
        )
    ROOT = real_root

    # 198. A single-quoted relative HTML href from docs/README.md resolving
    # to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"<a href='smoke/{o1_retired.rsplit('/', 1)[-1]}'>old authority</a>\n",
        )
        check_rejects(
            "a single-quoted relative HTML href resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "HTML href",
        )
    ROOT = real_root

    # 199. A Markdown reference-style definition from docs/README.md resolving
    # to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"[old]: smoke/{o1_retired.rsplit('/', 1)[-1]}\n\n[old O1][old]\n",
        )
        check_rejects(
            "a Markdown reference definition resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "reference definition",
        )
    ROOT = real_root

    # 200. A Markdown reference-style definition using angle brackets is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"[old]: <smoke/{o1_retired.rsplit('/', 1)[-1]}> \"old title\"\n",
        )
        check_rejects(
            "an angle-bracket Markdown reference definition resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "reference definition",
        )
    ROOT = real_root

    # 201. Query/fragment normalization still resolves to and rejects the retired path.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"<a href=\"smoke/{o1_retired.rsplit('/', 1)[-1]}?old=1#purpose\">old authority</a>\n",
        )
        check_rejects(
            "an HTML href with query and fragment still resolving to the retired o1-manual-one-round path is rejected",
            check_no_live_o1_manual_one_round_retired_paths,
            "HTML href",
        )
    ROOT = real_root

    # 202. A canonical target HTML href is accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"<a href=\"{o1_canonical}\">current authority</a>\n",
        )
        check_silent(
            "a canonical o1-manual-one-round HTML href is accepted",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 203. A canonical target reference-style definition is accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"[current]: {o1_canonical} \"current title\"\n",
        )
        check_silent(
            "a canonical o1-manual-one-round reference definition is accepted",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 204. An external HTML href is ignored by the shared resolver and accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"<a href=\"https://example.invalid/{o1_retired}\">external</a>\n",
        )
        check_silent(
            "an external HTML href mentioning the retired o1-manual-one-round path is accepted",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 205. Unrelated relative HTML/reference targets are accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            "<a href=\"smoke/unrelated.md\">unrelated</a>\n"
            "[unrelated]: smoke/unrelated.md\n",
        )
        check_silent(
            "unrelated relative HTML href and reference-definition targets are accepted",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 206. A line already caught by an existing pass is not double-reported by
    # the HTML/reference/prose passes.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/README.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old]({o1_retired}) and <a href=\"{o1_retired}\">old</a>.\n",
        )
        errors_no_duplicates: list[str] = []
        check_no_live_o1_manual_one_round_retired_paths(errors_no_duplicates)
        ok = len(errors_no_duplicates) == 1 and "markdown link target" in errors_no_duplicates[0]
        results.append(
            (
                "a line already reported by the Markdown-link pass is not double-reported by later O1 passes",
                ok,
                "" if ok else f"unexpected diagnostics: {errors_no_duplicates!r}",
            )
        )
    ROOT = real_root

    # 193. The canonical target's hyphenated basename mentioned the same way,
    # in the same docs/smoke/ location, is accepted: proves the bare-basename
    # pattern is underscore-only and never collides with the canonical
    # hyphenated name.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/smoke/example2.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See `{o1_canonical.rsplit('/', 1)[-1]}` for background.\n",
        )
        check_silent(
            "the canonical o1-manual-one-round hyphenated basename in docs/smoke/ backtick prose is accepted, distinguished from the retired underscored basename",
            check_no_live_o1_manual_one_round_retired_paths,
        )
    ROOT = real_root

    # 199. The same basename in a directory where it does not resolve to the
    # retired path is accepted. This proves the prose scanner resolves bounded
    # path tokens relative to the referring file rather than using a global
    # basename substring check.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_outside_smoke.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"Unrelated mention of `{o1_retired.rsplit('/', 1)[-1]}` outside docs/smoke/.\n",
        )
        errors_outside_scope: list[str] = []
        check_no_live_o1_manual_one_round_retired_paths(errors_outside_scope)
        ok = not errors_outside_scope
        results.append(
            (
                "the same retired basename in a directory where it does not resolve to the retired path is accepted",
                ok,
                "" if ok else f"unexpected errors: {errors_outside_scope!r}",
            )
        )
    ROOT = real_root

    # 196. The real repository passes the corrected guard (including the new
    # Pass 3 literal scan, the docs/**/*.txt extension, and the new Pass 4
    # bare-basename scan) with zero errors.
    check_silent(
        "real repository: no active reference to the retired o1-manual-one-round path after both Codex review correction rounds",
        check_no_live_o1_manual_one_round_retired_paths,
    )



    # Cutover 1C-45: OpenWebUI / LM Studio manual-validation retired-path guard self-tests.
    openwebui_pairs = OPENWEBUI_MANUAL_VALIDATION_RETIRED_TO_CANONICAL
    openwebui_retired = "docs/smoke/" + "openwebui_lmstudio_manual_smoke.md"
    openwebui_canonical = openwebui_pairs[openwebui_retired]
    check_silent(
        "real repository: no active reference to the retired OpenWebUI manual-validation paths",
        check_no_live_openwebui_manual_validation_retired_paths,
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, openwebui_retired, "# old\n")
        check_rejects("a reintroduced retired OpenWebUI source file is rejected", check_no_live_openwebui_manual_validation_retired_paths, "retired OpenWebUI manual-validation path reintroduced")
    ROOT = real_root
    carriers = [
        ("root-qualified markdown link", f"[old]({openwebui_retired})"),
        ("relative markdown link with query and fragment", "[old](../smoke/openwebui_lmstudio_manual_smoke.md?x=1#scope)"),
        ("same-directory bare basename", "See `openwebui_lmstudio_manual_smoke.md`"),
        ("HTML href", "<a href='../smoke/openwebui_lmstudio_manual_smoke.md#scope'>old</a>"),
        ("HTML src", "<img src='../smoke/openwebui_lmstudio_manual_smoke.md?x=1' />"),
        ("reference definition", "[old]: ../smoke/openwebui_lmstudio_manual_smoke.md#scope"),
        ("front matter path", f"---\nrelaylm_source_path: {openwebui_retired}\n---\n"),
        ("non-Markdown literal", f"note: {openwebui_retired}\n"),
    ]
    for name, body in carriers:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); ROOT = base
            file_path = "docs/smoke/carrier.md" if name != "non-Markdown literal" else "config.example.yaml"
            _mvp_write(base, file_path, body + "\n")
            check_rejects(f"OpenWebUI retired path in {name} is rejected", check_no_live_openwebui_manual_validation_retired_paths, f"active reference to retired {openwebui_retired}")
        ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, "docs/planning/example_not_allowlisted_rules.yaml", f"{openwebui_retired}:\n")
        check_rejects("OpenWebUI retired path YAML key in an active planning file is rejected", check_no_live_openwebui_manual_validation_retired_paths, f"active reference to retired {openwebui_retired}")
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, "docs/example.md", f"[canonical](../operations/{Path(openwebui_canonical).name})\n")
        check_silent("OpenWebUI canonical target link is accepted", check_no_live_openwebui_manual_validation_retired_paths)
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, "docs/example.md", "[external](https://example.com/docs/smoke/" + "openwebui_lmstudio_manual_smoke.md)\n")
        check_silent("OpenWebUI external URL containing retired literal is accepted", check_no_live_openwebui_manual_validation_retired_paths)
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, "docs/other/openwebui_lmstudio_manual_smoke.md", "# unrelated\n")
        _mvp_write(base, "docs/example.md", "See [unrelated](other/openwebui_lmstudio_manual_smoke.md).\n")
        check_silent("OpenWebUI unrelated same basename in different directory is accepted", check_no_live_openwebui_manual_validation_retired_paths)
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); ROOT = base
        _mvp_write(base, "docs/smoke/dup.md", f"[old]({openwebui_retired}) and {openwebui_retired}\n")
        errors: list[str] = []
        check_no_live_openwebui_manual_validation_retired_paths(errors)
        check("OpenWebUI duplicate diagnostics on one line are suppressed", lambda: len(errors) == 1)
    ROOT = real_root



    # Cutover 1C-45 production-registry coverage: direct helper tests above are
    # insufficient unless the default semantic-audit path also runs the checks.
    check(
        "OpenWebUI retired-path guard is registered in the production semantic-audit tuple",
        lambda: check_no_live_openwebui_manual_validation_retired_paths
        in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS,
    )
    check(
        "OpenWebUI family type guard is registered in the production semantic-audit tuple",
        lambda: check_openwebui_manual_validation_family_types
        in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS,
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, openwebui_retired, "# reintroduced retired source\n")
        errors: list[str] = []
        if check_no_live_openwebui_manual_validation_retired_paths in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS:
            check_no_live_openwebui_manual_validation_retired_paths(errors)
        check(
            "production semantic-audit tuple rejects a reintroduced OpenWebUI retired source",
            lambda: any("retired OpenWebUI manual-validation path reintroduced" in error for error in errors),
        )
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        for canonical_path, (doc_type, status) in OPENWEBUI_MANUAL_VALIDATION_CANONICAL_TYPES.items():
            wrong_type = "guide" if doc_type != "guide" else "operations"
            _mvp_write(
                base,
                canonical_path,
                f"---\nrelaylm_doc_type: {wrong_type}\nrelaylm_status: {status}\n---\n# bad metadata\n",
            )
        errors: list[str] = []
        if check_openwebui_manual_validation_family_types in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS:
            check_openwebui_manual_validation_family_types(errors)
        check(
            "production semantic-audit tuple rejects incorrect OpenWebUI canonical metadata",
            lambda: any("must declare relaylm_doc_type" in error for error in errors),
        )
    ROOT = real_root

    # ------------------------------------------------------------------
    # Cutover 1C-46: ReLM Showcase Fixture Authoring retired-path guard
    # self-tests, following the CORRECTED Cutover 1C-43 smoke-maintenance
    # pattern for a single-member family (no canonical-path scan bypass,
    # exact stripped-line allowlist equality, non-Markdown literal scan on
    # every non-`.md`/`.txt` suffix).
    # ------------------------------------------------------------------
    showcase_fixture_retired = SHOWCASE_FIXTURE_RETIRED_PATHS[0]
    showcase_fixture_canonical = SHOWCASE_FIXTURE_RETIRED_TO_CANONICAL[showcase_fixture_retired]

    # The real repository has no live reference to the retired
    # showcase-fixture-authoring path.
    check_silent(
        "real repository: no active reference to the retired showcase-fixture-authoring path",
        check_no_live_showcase_fixture_retired_paths,
    )

    # The retired showcase-fixture file being reintroduced is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            showcase_fixture_retired,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "the reintroduced retired showcase-fixture-authoring file is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"{showcase_fixture_retired}: retired showcase-fixture-authoring path reintroduced",
        )
    ROOT = real_root

    # A root-qualified Markdown link to the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_showcase_fixture_root_link.md",
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n\n"
            f"See [old fixture template]({showcase_fixture_retired}).\n",
        )
        check_rejects(
            "a root-qualified link to the retired showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A path-bearing front-matter entry (e.g. relaylm_related_authority)
    # referencing the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/operations/example_showcase_fixture_related_authority.md",
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n"
            "relaylm_related_authority:\n"
            f"  - {showcase_fixture_retired}\n---\n\nBody.\n",
        )
        check_rejects(
            "a front-matter relaylm_related_authority entry resolving to the retired "
            "showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # An unrelated file with the same basename in a different directory is
    # accepted (no false positive from bare-filename resolution).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/other/relm_showcase_fixture_template.md", "# unrelated\n")
        _mvp_write(
            base,
            "docs/example.md",
            "See [unrelated](other/relm_showcase_fixture_template.md).\n",
        )
        check_silent(
            "showcase-fixture-authoring unrelated same basename in a different directory is accepted",
            check_no_live_showcase_fixture_retired_paths,
        )
    ROOT = real_root

    # Duplicate references to the retired path on one line produce exactly
    # one diagnostic, not one per occurrence.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_showcase_fixture_dup.md",
            f"[old]({showcase_fixture_retired}) and {showcase_fixture_retired}\n",
        )
        errors: list[str] = []
        check_no_live_showcase_fixture_retired_paths(errors)
        check(
            "showcase-fixture-authoring duplicate diagnostics on one line are suppressed",
            lambda: len(errors) == 1,
        )
    ROOT = real_root

    # A plain-prose mention of the retired path (not a Markdown link, HTML
    # attribute, reference definition, or front-matter value) is rejected --
    # the exact P2 gap the Cutover 1C-44 correction round fixed for the O1
    # guard, now covered from the start for this family.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_showcase_fixture_prose.md",
            f"See {showcase_fixture_retired} for the old schema.\n",
        )
        check_rejects(
            "a plain-prose mention of the retired showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A backtick-quoted inline-code mention of the retired path is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_showcase_fixture_backtick.md",
            f"The old file was `{showcase_fixture_retired}`.\n",
        )
        check_rejects(
            "a backtick-quoted mention of the retired showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A bounded same-directory prose path token (bare basename, no directory
    # prefix, not a Markdown link, resolved from a sibling file in the same
    # directory as the retired path) is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/tools/example_sibling.md",
            f"formerly {showcase_fixture_retired.rsplit('/', 1)[-1]} in this directory\n",
        )
        check_rejects(
            "a bounded prose path token resolving to the retired showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A frozen/historical Markdown document (not the receipt, not
    # allowlisted) mentioning the retired path in prose is still rejected --
    # no generic frozen/historical status bypass.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/implementation/example_frozen_showcase_fixture.md",
            "---\nrelaylm_doc_type: implementation_completion_report\n"
            "relaylm_status: historical_after_merge\n---\n\n"
            f"Historically the fixture lived at {showcase_fixture_retired}.\n",
        )
        check_rejects(
            "a frozen/historical document's unallowlisted mention of the retired "
            "showcase-fixture-authoring path is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A retired-path literal inside a `docs/**/*.txt` file is rejected,
    # proving the guard-local `.txt` scan-universe extension actually runs
    # (the shared `_mobile_dogfood_scanned_files()` set excludes `.txt`).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/evidence/example_showcase_fixture_note.txt",
            f"source: {showcase_fixture_retired}\n",
        )
        check_rejects(
            "a retired showcase-fixture-authoring path literal inside a docs/**/*.txt file is rejected",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # A Markdown link to the canonical (moved) path is accepted, while a
    # Markdown link to the retired path in the same file is rejected --
    # proving the retired-basename match is resolved, not a global substring
    # ban that would also flag the canonical destination.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            "docs/example_showcase_fixture_canonical_vs_retired.md",
            f"[canonical]({showcase_fixture_canonical}) and [retired]({showcase_fixture_retired})\n",
        )
        errors: list[str] = []
        check_no_live_showcase_fixture_retired_paths(errors)
        check(
            "a link to the canonical showcase-fixture-authoring path is accepted while the "
            "retired path in the same file is rejected",
            lambda: len(errors) == 1 and f"retired {showcase_fixture_retired}" in errors[0],
        )
    ROOT = real_root

    # The guard's own exact self-file dict line is silent, while the same
    # line carrying extra trailing text is still rejected -- proving the
    # surviving exact-line allowance is stripped-line equality, not substring
    # containment.
    showcase_fixture_self_line = (
        f'"{showcase_fixture_retired}": "{showcase_fixture_canonical}",'
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, SHOWCASE_FIXTURE_SELF_FILE, f"    {showcase_fixture_self_line}\n")
        check_silent(
            "the guard's own exact self-file dict line is allowed",
            check_no_live_showcase_fixture_retired_paths,
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            SHOWCASE_FIXTURE_SELF_FILE,
            f"    {showcase_fixture_self_line}  # trailing comment\n",
        )
        check_rejects(
            "a self-file line with extra trailing text beyond the allowed line is "
            "rejected (exact-line, not substring)",
            check_no_live_showcase_fixture_retired_paths,
            f"active reference to retired {showcase_fixture_retired}",
        )
    ROOT = real_root

    # The real canonical destination document declares the correct profile.
    check_silent(
        "real repository: canonical showcase-fixture-authoring document has the correct profile",
        check_showcase_fixture_family_types,
    )

    # A canonical path carrying the retired runbook doc type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            showcase_fixture_canonical,
            "---\nrelaylm_doc_type: runbook\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_rejects(
            "a canonical showcase-fixture-authoring document with the retired runbook doc type is rejected",
            check_showcase_fixture_family_types,
            "must declare relaylm_doc_type: operations",
        )
    ROOT = real_root

    # A canonical path with the wrong status is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            showcase_fixture_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: target\n---\n\nBody.\n",
        )
        check_rejects(
            "a canonical showcase-fixture-authoring document with the wrong status is rejected",
            check_showcase_fixture_family_types,
            "must declare relaylm_status: current",
        )
    ROOT = real_root

    # A canonical path with the correct profile is accepted.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            showcase_fixture_canonical,
            "---\nrelaylm_doc_type: operations\nrelaylm_status: current\n---\n\nBody.\n",
        )
        check_silent(
            "a canonical showcase-fixture-authoring document with the correct profile is accepted",
            check_showcase_fixture_family_types,
        )
    ROOT = real_root

    # Cutover 1C-46 production-registry coverage: direct helper tests above
    # are insufficient unless the default semantic-audit path also runs the
    # checks (this is exactly the class of defect the C1C45 correction round
    # found and fixed for the OpenWebUI family).
    check(
        "showcase-fixture-authoring retired-path guard is registered in the production semantic-audit tuple",
        lambda: check_no_live_showcase_fixture_retired_paths
        in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS,
    )
    check(
        "showcase-fixture-authoring family type guard is registered in the production semantic-audit tuple",
        lambda: check_showcase_fixture_family_types
        in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS,
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, showcase_fixture_retired, "# reintroduced retired source\n")
        errors: list[str] = []
        if check_no_live_showcase_fixture_retired_paths in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS:
            check_no_live_showcase_fixture_retired_paths(errors)
        check(
            "production semantic-audit tuple rejects a reintroduced showcase-fixture-authoring retired source",
            lambda: any("retired showcase-fixture-authoring path reintroduced" in error for error in errors),
        )
    ROOT = real_root
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(
            base,
            showcase_fixture_canonical,
            "---\nrelaylm_doc_type: guide\nrelaylm_status: current\n---\n# bad metadata\n",
        )
        errors: list[str] = []
        if check_showcase_fixture_family_types in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS:
            check_showcase_fixture_family_types(errors)
        check(
            "production semantic-audit tuple rejects incorrect showcase-fixture-authoring canonical metadata",
            lambda: any("must declare relaylm_doc_type" in error for error in errors),
        )
    ROOT = real_root

    # -----------------------------------------------------------------------
    # Generic implementation-evidence completion-report validation. Coverage
    # migrated here from the retired dedicated completion-report validator.
    # -----------------------------------------------------------------------
    completion_report_relative = (
        f"{COMPLETION_REPORT_DIRECTORY}/example_slice{COMPLETION_REPORT_SUFFIX}"
    )
    completion_report_canonical = """---
relaylm_doc_type: evidence
relaylm_authority: example_slice_implementation_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_pr: 999999
relaylm_recorded_on: 2026-07-15
---
# Example Slice Completion Report

## Scope
Example scope.
## Implemented production boundary
Example boundary.
## Preserved authorities and non-goals
Example non-goals.
## Changed files
Example files.
## Validation evidence
Example evidence.
## Known limitations
Example limitations.
## Shared documentation update inputs
Example inputs.
## Source pull request
- PR: #999999
- URL: https://github.com/rinsakamo/relay-lm/pull/999999
"""
    completion_report_legacy = """---
relaylm_doc_type: implementation_completion_report
relaylm_authority: example_slice_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 000000000000000000000000000000000000000a
relaylm_source_pr: 999998
relaylm_recorded_on: 2026-07-15
relaylm_source_blob: 000000000000000000000000000000000000000b
relaylm_source_content_sha256: 000000000000000000000000000000000000000000000000000000000000000c
relaylm_exact_source_snapshot: example_slice_completion_report-source.txt
---
# Example Slice Completion Report

## Status and authority
Example status.
## Scope
Example scope.
## Implemented production boundary
Example boundary.
## Preserved authorities and non-goals
Example non-goals.
## Changed files
Example files.
## Validation evidence
Example evidence.
## Known limitations
Example limitations.
## Shared documentation update inputs
Example inputs.
## Source pull request
- PR: #999998
- URL: https://github.com/rinsakamo/relay-lm/pull/999998
"""

    def _write_completion_report(base: Path, text: str, *, snapshot: bool = False) -> None:
        _mvp_write(base, "docs/PROJECT_STATUS.md", "# Status\n")
        _mvp_write(base, completion_report_relative, text)
        if snapshot:
            _mvp_write(
                base,
                f"{COMPLETION_REPORT_DIRECTORY}/example_slice_completion_report-source.txt",
                "snapshot\n",
            )

    # Every real repository completion report satisfies the generic family.
    real_report_errors: list[str] = []
    check_implementation_evidence_completion_reports(real_report_errors)
    results.append(
        (
            "real repository completion reports pass generic evidence validation",
            not real_report_errors,
            "" if not real_report_errors else repr(real_report_errors),
        )
    )
    check(
        "the generic completion-report family scans every current report",
        lambda: len(_completion_report_paths())
        == len(tuple((real_root / COMPLETION_REPORT_DIRECTORY).glob("*" + COMPLETION_REPORT_SUFFIX)))
        and len(_completion_report_paths()) > 0,
    )

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(base, completion_report_canonical)
        check_silent(
            "a canonical-profile completion report is accepted",
            check_implementation_evidence_completion_reports,
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(base, completion_report_legacy, snapshot=True)
        check_silent(
            "a legacy-profile completion report is accepted",
            check_implementation_evidence_completion_reports,
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(
            base,
            completion_report_canonical.replace(
                "relaylm_status: frozen", "relaylm_status: historical_after_merge", 1
            ),
        )
        check_rejects(
            "a mixed completion-report profile is rejected",
            check_implementation_evidence_completion_reports,
            "unrecognized or mixed completion-report profile",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(
            base, completion_report_canonical.replace("Example limitations.", "TBD", 1)
        )
        check_rejects(
            "an unresolved completion-report placeholder is rejected",
            check_implementation_evidence_completion_reports,
            "unresolved placeholder",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(
            base,
            completion_report_canonical.replace(
                "## Known limitations\nExample limitations.\n", "", 1
            ),
        )
        check_rejects(
            "a completion report missing a required section is rejected",
            check_implementation_evidence_completion_reports,
            "missing completion-report sections",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(
            base,
            completion_report_legacy.replace(
                "relaylm_exact_source_snapshot: example_slice_completion_report-source.txt\n", "", 1
            ),
        )
        check_rejects(
            "a legacy completion report missing its exact-source metadata is rejected",
            check_implementation_evidence_completion_reports,
            "missing completion-report metadata",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _write_completion_report(base, completion_report_legacy, snapshot=False)
        check_rejects(
            "a legacy completion report with an absent exact-source snapshot is rejected",
            check_implementation_evidence_completion_reports,
            "missing exact source snapshot",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        _mvp_write(base, "docs/PROJECT_STATUS.md", "# Status\n")
        _mvp_write(base, "docs/elsewhere/example_slice_completion_report.md", completion_report_canonical)
        check_rejects(
            "a completion report outside the canonical evidence directory is rejected",
            lambda errors: check_implementation_evidence_completion_report(
                errors, "docs/elsewhere/example_slice_completion_report.md"
            ),
            "must live directly under",
        )
        check_rejects(
            "a traversing completion-report path is rejected",
            lambda errors: check_implementation_evidence_completion_report(
                errors, f"{COMPLETION_REPORT_DIRECTORY}/../example_slice_completion_report.md"
            ),
            "must not traverse directories",
        )
    ROOT = real_root

    check(
        "the generic completion-report family is registered in the production semantic-audit tuple",
        lambda: check_implementation_evidence_completion_reports
        in DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS,
    )

    failed = [(name, message) for name, ok, message in results if not ok]
    for name, ok, message in results:
        status = "PASS" if ok else "FAIL"
        suffix = f" ({message})" if message and not ok else ""
        print(f"{status}: {name}{suffix}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)}/{len(results)} assertions failed", file=sys.stderr)
        raise SystemExit(1)
    print(f"\nRelayLM docs semantic audit self-test passed: {len(results)} assertions")



DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS = (
    check_metadata,
    check_e2_boundary,
    check_client_instruction_boundary,
    check_release_assessment,
    check_implementation_evidence_index,
    check_implementation_evidence_completion_reports,
    check_no_live_mvp_tree,
    check_no_live_lat1_scaffold,
    check_lat1_evaluation_split,
    check_lat1_evaluation_evidence_records,
    check_no_live_e1_local_runtime_architecture_path,
    check_no_live_mobile_dogfood_retired_paths,
    check_mobile_dogfood_family_types,
    check_no_live_twin_extraction_retired_paths,
    check_twin_extraction_family_types,
    check_no_live_smoke_maintenance_retired_paths,
    check_smoke_maintenance_family_types,
    check_no_live_o1_manual_one_round_retired_paths,
    check_o1_manual_one_round_family_types,
    check_no_live_openwebui_manual_validation_retired_paths,
    check_openwebui_manual_validation_family_types,
    check_no_live_showcase_fixture_retired_paths,
    check_showcase_fixture_family_types,
    check_operations_docs,
    check_referenced_repository_paths,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    errors: list[str] = []
    checks = DOCUMENTATION_SEMANTIC_AUDIT_PRODUCTION_CHECKS
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
