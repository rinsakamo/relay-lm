#!/usr/bin/env python3
"""Validate transitional RelayLM completion-report files and their template.

This validator deliberately does not inspect ``docs/DOCUMENTATION_MODEL.md``
and does not own retired-path detection. Documentation semantics and retired
path absence are governed by the generic documentation validators. This script
owns only the bounded, removal-gated file shape of existing completion reports
and their template.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 131072

CANONICAL_TEMPLATE_PATH = "docs/templates/implementation-completion-report.md"
REPORT_DIRECTORY = Path("docs/evidence/implementation")

SECTION_ANCHORS = (
    "## Scope",
    "## Implemented production boundary",
    "## Preserved authorities and non-goals",
    "## Changed files",
    "## Validation evidence",
    "## Known limitations",
    "## Shared documentation update inputs",
    "## Source pull request",
)
SHARED_REPORT_ANCHORS = (
    "relaylm_current_status_source: ../../PROJECT_STATUS.md",
    "relaylm_source_pr:",
    "relaylm_recorded_on:",
) + SECTION_ANCHORS

LEGACY_PROFILE = {
    "relaylm_doc_type": "implementation_completion_report",
    "relaylm_status": "historical_after_merge",
    "relaylm_volatility": "frozen",
}
LEGACY_ONLY_ANCHORS = (
    "relaylm_doc_type: implementation_completion_report",
    "relaylm_status: historical_after_merge",
    "relaylm_volatility: frozen",
    "## Status and authority",
    "relaylm_source_commit:",
    "relaylm_source_blob:",
    "relaylm_source_content_sha256:",
    "relaylm_exact_source_snapshot:",
)

CANONICAL_PROFILE = {
    "relaylm_doc_type": "evidence",
    "relaylm_status": "frozen",
    "relaylm_volatility": "low",
}
CANONICAL_ONLY_ANCHORS = (
    "relaylm_doc_type: evidence",
    "relaylm_status: frozen",
    "relaylm_volatility: low",
)

TEMPLATE_FRONT_MATTER = {
    "relaylm_doc_type": "template",
    "relaylm_authority": "non_authoritative_implementation_completion_report_template",
    "relaylm_status": "target",
    "relaylm_volatility": "medium",
    "relaylm_owner": "documentation",
    "relaylm_decision_source": "../adr/0002-documentation-information-architecture.md",
}
TEMPLATE_NOT_AUTHORITATIVE_FOR = {
    "any implementation result",
    "current runtime behavior",
    "repository-wide implementation status",
    "cross-slice sequencing",
    "release or evaluation readiness",
}
TEMPLATE_REQUIRED_BODY_ANCHORS = (
    "docs/evidence/implementation/",
    "relaylm_doc_type: evidence",
    "relaylm_status: frozen",
    "relaylm_volatility: low",
) + SECTION_ANCHORS
TEMPLATE_FORBIDDEN_ANCHORS = (
    "relaylm_doc_type: implementation_completion_report",
    "relaylm_status: historical_after_merge",
    "relaylm_source_origin_commit:",
    "relaylm_source_blob:",
    "relaylm_source_content_sha256:",
    "relaylm_pre_cutover_blob:",
    "relaylm_pre_cutover_content_sha256:",
    "relaylm_exact_source_snapshot:",
)


def read_text(relative_path: str) -> str:
    path = ROOT / relative_path
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise AssertionError(f"{relative_path}: file exceeds size bound")
    return data.decode("utf-8")


def require_anchors(relative_path: str, anchors: tuple[str, ...]) -> None:
    body = read_text(relative_path)
    missing = [anchor for anchor in anchors if anchor not in body]
    if missing:
        raise AssertionError(f"{relative_path}: missing anchors: {missing!r}")


def parse_flat_front_matter(relative_path: str, raw: str) -> dict[str, object]:
    metadata: dict[str, object] = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") and line.strip().startswith("- "):
            if current_list_key is None:
                raise AssertionError(
                    f"{relative_path}: list item with no preceding key: {line!r}"
                )
            value = metadata[current_list_key]
            if not isinstance(value, list):
                raise AssertionError(
                    f"{relative_path}: list item follows non-list key {current_list_key!r}"
                )
            value.append(line.strip()[2:].strip())
            continue
        if ":" not in line:
            raise AssertionError(
                f"{relative_path}: unparseable front matter line: {line!r}"
            )
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            metadata[key] = value
            current_list_key = None
        else:
            metadata[key] = []
            current_list_key = key
    return metadata


def parse_front_matter(relative_path: str) -> tuple[dict[str, object], str]:
    text = read_text(relative_path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{relative_path}: missing YAML front matter")
    try:
        end = next(
            index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise AssertionError(f"{relative_path}: unterminated YAML front matter") from exc
    raw = "\n".join(lines[1:end])
    metadata = parse_flat_front_matter(relative_path, raw)
    body = "\n".join(lines[end + 1 :])
    return metadata, body


def validate_template_front_matter() -> None:
    metadata, body = parse_front_matter(CANONICAL_TEMPLATE_PATH)
    for key, value in TEMPLATE_FRONT_MATTER.items():
        if metadata.get(key) != value:
            raise AssertionError(
                f"{CANONICAL_TEMPLATE_PATH}: {key} must be {value!r}, "
                f"got {metadata.get(key)!r}"
            )

    update_trigger = metadata.get("relaylm_update_trigger")
    if not isinstance(update_trigger, list) or not update_trigger:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: relaylm_update_trigger must be a non-empty list"
        )

    not_authoritative_for = metadata.get("relaylm_not_authoritative_for")
    if (
        not isinstance(not_authoritative_for, list)
        or set(not_authoritative_for) != TEMPLATE_NOT_AUTHORITATIVE_FOR
    ):
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: relaylm_not_authoritative_for must be exactly "
            f"{sorted(TEMPLATE_NOT_AUTHORITATIVE_FOR)!r}"
        )

    missing = [anchor for anchor in TEMPLATE_REQUIRED_BODY_ANCHORS if anchor not in body]
    if missing:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: missing anchors: {missing!r}"
        )
    present = [anchor for anchor in TEMPLATE_FORBIDDEN_ANCHORS if anchor in body]
    if present:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: forbidden retired/migration-only anchors present: "
            f"{present!r}"
        )


def determine_profile(relative_path: str, metadata: dict[str, object]) -> str:
    candidate = {
        "relaylm_doc_type": metadata.get("relaylm_doc_type"),
        "relaylm_status": metadata.get("relaylm_status"),
        "relaylm_volatility": metadata.get("relaylm_volatility"),
    }
    if candidate == LEGACY_PROFILE:
        return "legacy"
    if candidate == CANONICAL_PROFILE:
        return "canonical"
    raise AssertionError(
        f"{relative_path}: unrecognized or mixed completion-report profile "
        f"(doc_type={candidate['relaylm_doc_type']!r}, "
        f"status={candidate['relaylm_status']!r}, "
        f"volatility={candidate['relaylm_volatility']!r})"
    )


def validate_report(relative_path: str) -> None:
    path = Path(relative_path)
    parts = path.parts
    filename = path.name
    if len(parts) != 4 or parts[:3] != REPORT_DIRECTORY.parts:
        raise AssertionError(
            f"{relative_path}: report must be under canonical {REPORT_DIRECTORY.as_posix()}/"
        )
    if not filename.endswith("_completion_report.md"):
        raise AssertionError(f"{relative_path}: invalid completion report filename")
    if ".." in parts:
        raise AssertionError(f"{relative_path}: parent traversal is not allowed")

    metadata, _ = parse_front_matter(relative_path)
    profile = determine_profile(relative_path, metadata)
    require_anchors(relative_path, SHARED_REPORT_ANCHORS)
    if profile == "legacy":
        require_anchors(relative_path, LEGACY_ONLY_ANCHORS)
    else:
        require_anchors(relative_path, CANONICAL_ONLY_ANCHORS)

    body = read_text(relative_path)
    pr_lines = [line for line in body.splitlines() if line.startswith("- PR: #")]
    if len(pr_lines) != 1:
        raise AssertionError(f"{relative_path}: one source PR line required")
    pr_value = pr_lines[0].split("#", 1)[1].strip()
    if not pr_value.isdigit() or pr_value.startswith("0"):
        raise AssertionError(f"{relative_path}: source PR must be positive digits")
    if "- URL: https://github.com/" not in body:
        raise AssertionError(f"{relative_path}: concrete source PR URL required")
    for placeholder in ("<slice>", "<number>", "TBD", "TO BE FILLED"):
        if placeholder in body:
            raise AssertionError(
                f"{relative_path}: unresolved placeholder {placeholder!r}"
            )


def all_report_paths() -> tuple[str, ...]:
    reports = (ROOT / REPORT_DIRECTORY).glob("*_completion_report.md")
    return tuple(path.relative_to(ROOT).as_posix() for path in sorted(reports))


def validate_repository_files(paths: list[str], check_all: bool) -> None:
    if check_all:
        validate_template_front_matter()
        paths.extend(all_report_paths())
    for relative_path in dict.fromkeys(paths):
        validate_report(relative_path)


_CANONICAL_REPORT_TEXT = """---
relaylm_doc_type: evidence
relaylm_authority: example_slice_implementation_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP dependency sequencing
  - other slice completion
  - next-wave readiness
  - release or evaluation readiness
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

_LEGACY_REPORT_TEXT = """---
relaylm_doc_type: implementation_completion_report
relaylm_authority: example_slice_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP dependency sequencing
  - other slice completion
  - next-wave readiness
  - release or evaluation readiness
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


def write_report(base: Path, name: str, text: str) -> str:
    target_dir = base / REPORT_DIRECTORY
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    target.write_text(text, encoding="utf-8")
    return target.relative_to(base).as_posix()


def self_test() -> None:
    global ROOT
    real_root = ROOT
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            results.append((name, True, ""))
        except AssertionError as exc:
            results.append((name, False, str(exc)))

    def check_rejects(
        name: str, fn: Callable[[], None], expected_substring: str
    ) -> None:
        try:
            fn()
            results.append((name, False, "expected AssertionError, none raised"))
        except AssertionError as exc:
            message = str(exc)
            results.append(
                (
                    name,
                    expected_substring in message,
                    "" if expected_substring in message else f"wrong error: {message}",
                )
            )

    check(
        "real repository completion-report files and template pass",
        lambda: validate_repository_files([], True),
    )

    with tempfile.TemporaryDirectory() as directory:
        ROOT = Path(directory)
        relative_path = write_report(
            ROOT, "example_slice_completion_report.md", _CANONICAL_REPORT_TEXT
        )
        check("canonical report passes", lambda: validate_report(relative_path))
    ROOT = real_root

    with tempfile.TemporaryDirectory() as directory:
        ROOT = Path(directory)
        relative_path = write_report(
            ROOT, "example_slice_completion_report.md", _LEGACY_REPORT_TEXT
        )
        check("legacy report passes", lambda: validate_report(relative_path))
    ROOT = real_root

    with tempfile.TemporaryDirectory() as directory:
        ROOT = Path(directory)
        mixed = _CANONICAL_REPORT_TEXT.replace(
            "relaylm_status: frozen", "relaylm_status: historical_after_merge", 1
        )
        relative_path = write_report(
            ROOT, "example_slice_completion_report.md", mixed
        )
        check_rejects(
            "mixed profile is rejected",
            lambda: validate_report(relative_path),
            "unrecognized or mixed completion-report profile",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as directory:
        ROOT = Path(directory)
        unresolved = _CANONICAL_REPORT_TEXT.replace("Example limitations.", "TBD", 1)
        relative_path = write_report(
            ROOT, "example_slice_completion_report.md", unresolved
        )
        check_rejects(
            "unresolved placeholder is rejected",
            lambda: validate_report(relative_path),
            "unresolved placeholder",
        )
    ROOT = real_root

    real_template = (real_root / CANONICAL_TEMPLATE_PATH).read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as directory:
        ROOT = Path(directory)
        target = ROOT / CANONICAL_TEMPLATE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            real_template.replace(
                "relaylm_doc_type: evidence",
                "relaylm_doc_type: implementation_completion_report",
                1,
            ),
            encoding="utf-8",
        )
        check_rejects(
            "template cannot reintroduce the legacy generated-report profile",
            validate_template_front_matter,
            "forbidden retired/migration-only anchors present",
        )
    ROOT = real_root

    failed = [(name, message) for name, ok, message in results if not ok]
    for name, ok, message in results:
        status = "PASS" if ok else "FAIL"
        suffix = f" ({message})" if message and not ok else ""
        print(f"{status}: {name}{suffix}")
    if failed:
        print(
            f"\nSELF-TEST FAILED: {len(failed)}/{len(results)} assertions failed",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(
        f"\nRelayLM completion-report file validator self-test passed: "
        f"{len(results)} assertions"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    check_all = args.check_all or not args.paths
    validate_repository_files(list(args.paths), check_all)
    print("RelayLM completion-report file smoke passed")


if __name__ == "__main__":
    main()
