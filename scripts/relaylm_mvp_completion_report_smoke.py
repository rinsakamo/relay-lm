#!/usr/bin/env python3
"""Validate the completion-report model and concrete report files."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 131072

OLD_TEMPLATE_PATH = "docs/mvp/IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md"
CANONICAL_TEMPLATE_PATH = "docs/templates/implementation-completion-report.md"

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

# Anchors required of every completion report regardless of profile.
SHARED_REPORT_ANCHORS = (
    "relaylm_current_status_source: ../../PROJECT_STATUS.md",
    "relaylm_source_pr:",
    "relaylm_recorded_on:",
) + SECTION_ANCHORS

# `implementation_completion_report` / `historical_after_merge` / `frozen`: the profile used by
# reports already migrated into canonical placement by a documentation hard-cutover PR. Existing
# migrated reports may retain this profile until a separate family-normalization cutover; do not
# assign it to a newly created report (see docs/DOCUMENTATION_MODEL.md's Stage-1 clarification).
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

# `evidence` / `frozen` / `low`: the profile a new Stage-1 completion report must use when created
# directly by an implementation PR. It carries no migration-only provenance (no source blob, no
# source-origin commit, no exact snapshot) because it is not the product of a hard-cutover move.
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
# Retired generated-report profile and migration-only provenance fields must never appear as the
# template's own generated-report example: a natively canonical Stage-1 report cannot
# self-referentially record its own not-yet-created commit or blob.
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

MODEL_ANCHORS = {
    "docs/DOCUMENTATION_MODEL.md": (
        "## Two-stage parallel implementation documentation",
        "### Stage 1: implementation PR",
        "### Stage 2: convergence and shared-documentation PR",
    ),
    "docs/README.md": (
        "## Parallel implementation documentation rule",
        "The next wave and release/evaluation gate remain closed",
    ),
    "docs/evidence/implementation/README.md": (
        "## Creating a new completion report",
        "docs/evidence/implementation/<slice>_completion_report.md",
        "../../templates/implementation-completion-report.md",
        "O1D2 completion report",
        "I-4E completion report",
        "UI-B1A completion report",
        "I-5A completion report",
        "I-7A/B completion report",
    ),
    "docs/evidence/waves/README.md": (
        "Wave 4 cross-slice convergence audit",
    ),
}


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


def forbid_anchors(relative_path: str, anchors: tuple[str, ...]) -> None:
    body = read_text(relative_path)
    present = [anchor for anchor in anchors if anchor in body]
    if present:
        raise AssertionError(f"{relative_path}: forbidden anchors present: {present!r}")


def _parse_flat_front_matter(relative_path: str, raw: str) -> dict:
    """Parse the flat `key: value` / `key:` + `- item` front matter used throughout this
    repository's documents. Deliberately dependency-free (no PyYAML): this script is invoked
    directly by several CI workflows that install no project dependencies, and every front
    matter block in this repository is a flat mapping of plain scalars and one-level lists,
    never nested mappings, anchors, or multi-line scalars.
    """
    metadata: dict = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") and line.strip().startswith("- "):
            if current_list_key is None:
                raise AssertionError(f"{relative_path}: list item with no preceding key: {line!r}")
            metadata[current_list_key].append(line.strip()[2:].strip())
            continue
        if ":" not in line:
            raise AssertionError(f"{relative_path}: unparseable front matter line: {line!r}")
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


def parse_front_matter(relative_path: str) -> tuple[dict, str]:
    text = read_text(relative_path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{relative_path}: missing YAML front matter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise AssertionError(f"{relative_path}: unterminated YAML front matter") from exc
    raw = "\n".join(lines[1:end])
    metadata = _parse_flat_front_matter(relative_path, raw)
    body = "\n".join(lines[end + 1 :])
    return metadata, body


def validate_model() -> None:
    for relative_path, anchors in MODEL_ANCHORS.items():
        require_anchors(relative_path, anchors)
    validate_template_front_matter()


def validate_template_front_matter() -> None:
    metadata, body = parse_front_matter(CANONICAL_TEMPLATE_PATH)
    for key, value in TEMPLATE_FRONT_MATTER.items():
        if metadata.get(key) != value:
            raise AssertionError(
                f"{CANONICAL_TEMPLATE_PATH}: {key} must be {value!r}, got {metadata.get(key)!r}"
            )
    update_trigger = metadata.get("relaylm_update_trigger")
    if not isinstance(update_trigger, list) or not update_trigger:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: relaylm_update_trigger must be a non-empty list"
        )
    not_authoritative_for = metadata.get("relaylm_not_authoritative_for")
    if not isinstance(not_authoritative_for, list) or set(not_authoritative_for) != TEMPLATE_NOT_AUTHORITATIVE_FOR:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: relaylm_not_authoritative_for must be exactly "
            f"{sorted(TEMPLATE_NOT_AUTHORITATIVE_FOR)!r}"
        )

    missing = [anchor for anchor in TEMPLATE_REQUIRED_BODY_ANCHORS if anchor not in body]
    if missing:
        raise AssertionError(f"{CANONICAL_TEMPLATE_PATH}: missing anchors: {missing!r}")

    present_forbidden = [anchor for anchor in TEMPLATE_FORBIDDEN_ANCHORS if anchor in body]
    if present_forbidden:
        raise AssertionError(
            f"{CANONICAL_TEMPLATE_PATH}: forbidden retired/migration-only anchors present: "
            f"{present_forbidden!r}"
        )


def determine_profile(relative_path: str, metadata: dict) -> str:
    doc_type = metadata.get("relaylm_doc_type")
    status = metadata.get("relaylm_status")
    volatility = metadata.get("relaylm_volatility")
    candidate = {
        "relaylm_doc_type": doc_type,
        "relaylm_status": status,
        "relaylm_volatility": volatility,
    }
    if candidate == LEGACY_PROFILE:
        return "legacy"
    if candidate == CANONICAL_PROFILE:
        return "canonical"
    raise AssertionError(
        f"{relative_path}: unrecognized or mixed completion-report profile "
        f"(doc_type={doc_type!r}, status={status!r}, volatility={volatility!r})"
    )


def validate_report(relative_path: str) -> None:
    parts = Path(relative_path).parts
    filename = parts[-1] if parts else ""
    canonical_implementation_evidence = (
        len(parts) == 4
        and parts[0:3] == ("docs", "evidence", "implementation")
    )
    if not canonical_implementation_evidence:
        raise AssertionError(
            f"{relative_path}: report must be under canonical docs/evidence/implementation/"
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
            raise AssertionError(f"{relative_path}: unresolved placeholder {placeholder!r}")


def all_report_paths() -> tuple[str, ...]:
    reports = (ROOT / "docs" / "evidence" / "implementation").glob("*_completion_report.md")
    return tuple(path.relative_to(ROOT).as_posix() for path in sorted(reports))


def assert_no_legacy_wave_reports() -> None:
    legacy = sorted((ROOT / "docs" / "mvp").glob("wave*/*_completion_report.md"))
    if legacy:
        paths = ", ".join(path.relative_to(ROOT).as_posix() for path in legacy)
        raise AssertionError(
            "legacy docs/mvp/wave<N>/*_completion_report.md path(s) reintroduced "
            f"(retired by Cutover 1C-36; move to docs/evidence/implementation/ instead): {paths}"
        )


def assert_old_template_path_absent() -> None:
    if (ROOT / OLD_TEMPLATE_PATH).exists():
        raise AssertionError(
            f"retired template path reintroduced (moved to {CANONICAL_TEMPLATE_PATH} by "
            f"Cutover 1C-37): {OLD_TEMPLATE_PATH}"
        )


def assert_no_mvp_tree() -> None:
    mvp_root = ROOT / "docs" / "mvp"
    if mvp_root.exists():
        offenders = sorted(
            path.relative_to(ROOT).as_posix() for path in mvp_root.rglob("*") if path.is_file()
        )
        raise AssertionError(
            "retired docs/mvp/ tree reintroduced (retired by Cutover 1C-38; canonical "
            f"routers are docs/evidence/implementation/README.md and docs/evidence/waves/README.md): "
            f"{offenders or [str(mvp_root.relative_to(ROOT))]}"
        )


# ---------------------------------------------------------------------------
# Self-test: bounded, deterministic, committed. Builds synthetic temp trees and
# monkeypatches ROOT rather than touching the real repository tree. Run with
# `--self-test`; wired into the documentation-completion-report-model workflow.
# ---------------------------------------------------------------------------

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

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

Example scope.

## Implemented production boundary

Example boundary.

## Preserved authorities and non-goals

Example non-goals.

## Changed files

Example changed files.

## Validation evidence

Example validation evidence.

## Known limitations

Example known limitations.

## Shared documentation update inputs

Example shared inputs.

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
relaylm_source_commit: 0000000000000000000000000000000000000a
relaylm_source_origin_commit: 0000000000000000000000000000000000000a
relaylm_source_pr: 999998
relaylm_recorded_on: 2026-07-15
relaylm_source_blob: 0000000000000000000000000000000000000b
relaylm_source_content_sha256: 00000000000000000000000000000000000000000000000000000000000c
relaylm_pre_cutover_blob: 0000000000000000000000000000000000000b
relaylm_pre_cutover_content_sha256: 00000000000000000000000000000000000000000000000000000000000c
relaylm_exact_source_snapshot: example_slice_completion_report-source.txt
---
# Example Slice Completion Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Status and authority

Example status and authority.

## Scope

Example scope.

## Implemented production boundary

Example boundary.

## Preserved authorities and non-goals

Example non-goals.

## Changed files

Example changed files.

## Validation evidence

Example validation evidence.

## Known limitations

Example known limitations.

## Shared documentation update inputs

Example shared inputs.

## Source pull request

- PR: #999998
- URL: https://github.com/rinsakamo/relay-lm/pull/999998
"""


def _write_report(base: Path, name: str, text: str) -> str:
    target_dir = base / "docs" / "evidence" / "implementation"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    target.write_text(text, encoding="utf-8")
    return str(Path("docs") / "evidence" / "implementation" / name)


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
        try:
            fn()
            results.append((name, False, "expected AssertionError, none raised"))
        except AssertionError as exc:
            ok = expected_substring in str(exc)
            results.append((name, ok, "" if ok else f"wrong error: {exc}"))

    # 1. Every existing migrated (real repository) completion report still passes.
    # ROOT is already real_root at this point; no monkeypatching needed for this check.
    def _real_reports_pass():
        assert_no_legacy_wave_reports()
        assert_old_template_path_absent()
        assert_no_mvp_tree()
        validate_template_front_matter()
        for report_path in all_report_paths():
            validate_report(report_path)

    check("real repository: all migrated reports and template pass", _real_reports_pass)
    check("real repository: docs/mvp/ tree is absent", assert_no_mvp_tree)

    # 2 & 5. A synthetic canonical evidence/frozen report passes and requires no snapshot fields.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        rel = _write_report(base, "example_slice_completion_report.md", _CANONICAL_REPORT_TEXT)

        migration_only_fields = (
            "relaylm_source_commit:",
            "relaylm_source_origin_commit:",
            "relaylm_source_blob:",
            "relaylm_source_content_sha256:",
            "relaylm_pre_cutover_blob:",
            "relaylm_pre_cutover_content_sha256:",
            "relaylm_exact_source_snapshot:",
        )

        def _canonical_passes():
            assert not any(field in _CANONICAL_REPORT_TEXT for field in migration_only_fields), (
                "fixture unexpectedly contains a migration-only field"
            )
            validate_report(rel)

        check("canonical evidence/frozen/low report passes with no migration snapshot fields", _canonical_passes)
    ROOT = real_root

    # 1b (legacy). A synthetic legacy-profile report still passes under the legacy branch.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        rel = _write_report(base, "example_slice_completion_report.md", _LEGACY_REPORT_TEXT)

        def _legacy_passes():
            validate_report(rel)

        check("legacy implementation_completion_report/historical_after_merge report still passes", _legacy_passes)
    ROOT = real_root

    # 3. A report using historical_after_merge under the canonical doc_type is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        mixed = _CANONICAL_REPORT_TEXT.replace("relaylm_status: frozen", "relaylm_status: historical_after_merge", 1)
        rel = _write_report(base, "example_slice_completion_report.md", mixed)

        def _rejects_evidence_with_historical_after_merge():
            validate_report(rel)

        check_rejects(
            "evidence doc_type with historical_after_merge status is rejected",
            _rejects_evidence_with_historical_after_merge,
            "unrecognized or mixed completion-report profile",
        )
    ROOT = real_root

    # 4. A mixed legacy/canonical profile is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        mixed = _LEGACY_REPORT_TEXT.replace("relaylm_volatility: frozen", "relaylm_volatility: low", 1)
        rel = _write_report(base, "example_slice_completion_report.md", mixed)

        def _rejects_mixed_profile():
            validate_report(rel)

        check_rejects(
            "legacy doc_type with canonical (low) volatility is rejected as mixed",
            _rejects_mixed_profile,
            "unrecognized or mixed completion-report profile",
        )
    ROOT = real_root

    # 6. Unresolved placeholders elsewhere in an otherwise-valid report are rejected (with a
    # concrete, digits-only PR number/URL so the digit check does not mask the placeholder check).
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        placeholder_text = _CANONICAL_REPORT_TEXT.replace(
            "Example known limitations.", "TBD", 1
        )
        rel = _write_report(base, "example_slice_completion_report.md", placeholder_text)

        def _rejects_unresolved_placeholder():
            validate_report(rel)

        check_rejects(
            "unresolved TBD placeholder is rejected",
            _rejects_unresolved_placeholder,
            "unresolved placeholder",
        )
    ROOT = real_root

    # 7. Old template path reintroduction is rejected; clean tree is silent.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs" / "mvp").mkdir(parents=True)
        (base / "docs" / "mvp" / "IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md").write_text("legacy")

        def _rejects_reintroduced_old_template():
            assert_old_template_path_absent()

        check_rejects(
            "reintroduced old template path is rejected",
            _rejects_reintroduced_old_template,
            "retired template path reintroduced",
        )
    ROOT = real_root

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs" / "mvp").mkdir(parents=True)

        def _clean_tree_silent():
            assert_old_template_path_absent()

        check("clean synthetic tree has no old template path", _clean_tree_silent)
    ROOT = real_root

    # A synthetic reintroduced docs/mvp/README.md is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs" / "mvp").mkdir(parents=True)
        (base / "docs" / "mvp" / "README.md").write_text("reintroduced index", encoding="utf-8")

        def _rejects_reintroduced_mvp_readme():
            assert_no_mvp_tree()

        check_rejects(
            "reintroduced docs/mvp/README.md is rejected",
            _rejects_reintroduced_mvp_readme,
            "retired docs/mvp/ tree reintroduced",
        )
    ROOT = real_root

    # A synthetic file anywhere below docs/mvp/ is rejected.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs" / "mvp" / "wave9").mkdir(parents=True)
        (base / "docs" / "mvp" / "wave9" / "example_completion_report.md").write_text(
            "reintroduced report", encoding="utf-8"
        )

        def _rejects_reintroduced_mvp_subtree_file():
            assert_no_mvp_tree()

        check_rejects(
            "reintroduced file anywhere below docs/mvp/ is rejected",
            _rejects_reintroduced_mvp_subtree_file,
            "retired docs/mvp/ tree reintroduced",
        )
    ROOT = real_root

    # A clean synthetic tree with no docs/mvp/ directory at all is silent.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs").mkdir(parents=True)

        def _no_mvp_dir_silent():
            assert_no_mvp_tree()

        check("clean synthetic tree with no docs/mvp/ directory is silent", _no_mvp_dir_silent)
    ROOT = real_root

    # 8. A canonical template reintroducing the retired generated-report profile is rejected.
    real_template_text = (real_root / CANONICAL_TEMPLATE_PATH).read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ROOT = base
        (base / "docs" / "templates").mkdir(parents=True)
        corrupted = real_template_text.replace(
            "relaylm_doc_type: evidence", "relaylm_doc_type: implementation_completion_report", 1
        ).replace("relaylm_status: frozen", "relaylm_status: historical_after_merge", 1)
        (base / CANONICAL_TEMPLATE_PATH).write_text(corrupted, encoding="utf-8")

        def _rejects_retired_profile_in_template():
            validate_template_front_matter()

        check_rejects(
            "template reintroducing the retired generated-report profile is rejected",
            _rejects_retired_profile_in_template,
            "forbidden retired/migration-only anchors present",
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
    print(f"\nRelayLM completion report validator self-test passed: {len(results)} assertions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--check-model", action="store_true")
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if not args.check_model and not args.check_all and not args.paths:
        args.check_model = True
        args.check_all = True

    assert_no_legacy_wave_reports()
    assert_old_template_path_absent()
    assert_no_mvp_tree()
    if args.check_model:
        validate_model()
    paths = list(args.paths)
    if args.check_all:
        paths.extend(all_report_paths())
    for relative_path in dict.fromkeys(paths):
        validate_report(relative_path)
    print("RelayLM MVP completion report smoke passed")


if __name__ == "__main__":
    main()
