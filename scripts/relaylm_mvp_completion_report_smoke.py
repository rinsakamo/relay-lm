#!/usr/bin/env python3
"""Validate the completion-report model and concrete report files."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 131072

REPORT_ANCHORS = (
    "relaylm_doc_type: implementation_completion_report",
    "relaylm_status: historical_after_merge",
    "relaylm_volatility: frozen",
    "relaylm_current_status_source: ../../PROJECT_STATUS.md",
    "## Scope",
    "## Implemented production boundary",
    "## Preserved authorities and non-goals",
    "## Changed files",
    "## Validation evidence",
    "## Known limitations",
    "## Shared documentation update inputs",
    "## Source pull request",
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
    "docs/mvp/README.md": (
        "## Implementation completion reports",
        "The wave convergence PR links the merged reports",
    ),
    "docs/mvp/IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md": REPORT_ANCHORS[4:],
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


def validate_model() -> None:
    for relative_path, anchors in MODEL_ANCHORS.items():
        require_anchors(relative_path, anchors)


def validate_report(relative_path: str) -> None:
    if not relative_path.startswith("docs/mvp/wave"):
        raise AssertionError(f"{relative_path}: report must be under docs/mvp/wave<N>/")
    if not relative_path.endswith("_completion_report.md"):
        raise AssertionError(f"{relative_path}: invalid completion report filename")
    if ".." in Path(relative_path).parts:
        raise AssertionError(f"{relative_path}: parent traversal is not allowed")

    require_anchors(relative_path, REPORT_ANCHORS)
    body = read_text(relative_path)
    if "- PR: #" not in body:
        raise AssertionError(f"{relative_path}: concrete source PR number required")
    if "- URL: https://github.com/" not in body:
        raise AssertionError(f"{relative_path}: concrete source PR URL required")
    for placeholder in ("<slice>", "<number>", "TBD", "TO BE FILLED"):
        if placeholder in body:
            raise AssertionError(f"{relative_path}: unresolved placeholder {placeholder!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--check-model", action="store_true")
    args = parser.parse_args()
    if not args.check_model and not args.paths:
        raise AssertionError("pass --check-model and/or one report path")
    if args.check_model:
        validate_model()
    for relative_path in args.paths:
        validate_report(relative_path)
    print("RelayLM MVP completion report smoke passed")


if __name__ == "__main__":
    main()
