#!/usr/bin/env python3
"""Inventory relative Markdown links to documentation at a frozen Git commit.

Preparation C originally scanned only literal ``docs/...md`` strings. This
companion scanner resolves relative Markdown links such as
``[MVP-10](mvp10_summary.md)`` against the referrer's directory so cutover PRs
cannot mistake a linked document for a dependency-free source.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "generated" / "documentation-cutover"
MAX_TEXT_BYTES = 2 * 1024 * 1024

INLINE_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]\n]+\]:\s*(\S+)", re.MULTILINE)
AUTOLINK_RE = re.compile(r"<([^<>\s]+\.md(?:[?#][^<>\s]*)?)>", re.IGNORECASE)
HTML_LINK_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class RelativeLinkError(RuntimeError):
    """Raised when the frozen relative-link inventory cannot be trusted."""


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        raise RelativeLinkError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result


def validate_baseline(commit: str) -> None:
    run_git("cat-file", "-e", f"{commit}^{{commit}}")


def list_markdown_paths(commit: str) -> list[str]:
    result = run_git("ls-tree", "-r", "--name-only", commit, "--", "docs")
    return sorted(
        path for path in result.stdout.splitlines() if path.endswith(".md")
    )


def read_blob(commit: str, path: str) -> str:
    result = run_git("show", f"{commit}:{path}")
    text = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise RelativeLinkError(f"{path}: exceeds {MAX_TEXT_BYTES} byte bound")
    return text


def destination_from_inline(raw: str) -> str:
    """Return the destination portion of an inline Markdown link payload."""
    value = raw.strip()
    if value.startswith("<"):
        end = value.find(">")
        return value[1:end] if end >= 0 else value[1:]
    # A destination containing spaces should be angle-bracketed. For ordinary
    # Markdown links the first whitespace-delimited token is the destination;
    # the remainder is an optional title.
    return value.split(None, 1)[0] if value else ""


def extracted_destinations(text: str) -> list[tuple[str, int, str]]:
    """Extract link destinations with one-based line numbers and syntax kind."""
    matches: list[tuple[int, int, str, str]] = []
    for matcher, kind in (
        (INLINE_LINK_RE, "inline_markdown"),
        (REFERENCE_LINK_RE, "reference_definition"),
        (AUTOLINK_RE, "autolink"),
        (HTML_LINK_RE, "html_attribute"),
    ):
        for match in matcher.finditer(text):
            group_index = 2 if matcher is HTML_LINK_RE else 1
            raw = match.group(group_index)
            destination = (
                destination_from_inline(raw)
                if matcher is INLINE_LINK_RE
                else raw.strip().strip("<>")
            )
            line = text.count("\n", 0, match.start()) + 1
            matches.append((match.start(), line, destination, kind))
    matches.sort(key=lambda item: (item[0], item[3], item[2]))
    return [(destination, line, kind) for _, line, destination, kind in matches]


def normalize_posix(path: PurePosixPath) -> str | None:
    parts: list[str] = []
    for part in path.parts:
        if part in {"", ".", "/"}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def resolve_document_target(referrer: str, destination: str) -> str | None:
    value = unquote(destination.strip())
    if not value or value.startswith("#") or value.startswith("//"):
        return None
    if SCHEME_RE.match(value):
        return None

    value = value.split("#", 1)[0].split("?", 1)[0]
    if not value:
        return None

    if value.startswith("/"):
        candidate = PurePosixPath(value.lstrip("/"))
    elif value.startswith("docs/"):
        candidate = PurePosixPath(value)
    else:
        candidate = PurePosixPath(referrer).parent / value

    normalized = normalize_posix(candidate)
    if normalized is None or not normalized.startswith("docs/"):
        return None
    if not normalized.lower().endswith(".md"):
        return None
    return normalized


def referrer_kind(path: str) -> str:
    if path.startswith(".github/workflows/"):
        return "workflow"
    if path.startswith("scripts/"):
        return "script"
    if path.startswith("docs/"):
        return "documentation"
    if path in {"README.md", "README_ja.md"}:
        return "root_router"
    return "repository"


def relative_dependencies(
    commit: str,
    markdown_paths: Iterable[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    known_docs = set(markdown_paths)
    output: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    unresolved: list[dict[str, Any]] = []

    for referrer in sorted(known_docs):
        text = read_blob(commit, referrer)
        lines = text.splitlines()
        seen: set[tuple[str, int, str]] = set()
        for destination, line_number, syntax in extracted_destinations(text):
            target = resolve_document_target(referrer, destination)
            if target is None:
                continue
            key = (target, line_number, syntax)
            if key in seen:
                continue
            seen.add(key)
            source_line = lines[line_number - 1] if line_number <= len(lines) else ""
            record = {
                "referrer": referrer,
                "line": line_number,
                "kind": referrer_kind(referrer),
                "syntax": syntax,
                "destination": destination,
                "text_sha256": hashlib.sha256(
                    source_line.strip().encode("utf-8")
                ).hexdigest(),
            }
            if target in known_docs:
                output[target].append(record)
            else:
                unresolved.append({"resolved_target": target, **record})

    normalized = {
        target: sorted(
            records,
            key=lambda item: (
                item["kind"],
                item["referrer"],
                item["line"],
                item["syntax"],
                item["destination"],
            ),
        )
        for target, records in sorted(output.items())
    }
    unresolved.sort(
        key=lambda item: (
            item["resolved_target"],
            item["referrer"],
            item["line"],
            item["syntax"],
        )
    )
    return normalized, unresolved


def parse_assertion(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise RelativeLinkError(
            "--assert-dependency must use TARGET=REFERRER syntax"
        )
    target, referrer = raw.split("=", 1)
    if not target or not referrer:
        raise RelativeLinkError(
            "--assert-dependency requires non-empty target and referrer"
        )
    return target, referrer


def validate_assertions(
    dependencies: dict[str, list[dict[str, Any]]],
    assertions: Iterable[str],
) -> list[str]:
    errors: list[str] = []
    for raw in assertions:
        target, referrer = parse_assertion(raw)
        if not any(
            item["referrer"] == referrer
            for item in dependencies.get(target, [])
        ):
            errors.append(f"missing expected dependency {target} <- {referrer}")
    return errors


def markdown_summary(
    baseline: str,
    dependencies: dict[str, list[dict[str, Any]]],
    unresolved: list[dict[str, Any]],
    errors: list[str],
) -> str:
    reference_count = sum(len(items) for items in dependencies.values())
    lines = [
        "# Relative Documentation Link Inventory",
        "",
        f"- Baseline commit: `{baseline}`",
        f"- Existing Markdown targets with incoming relative links: **{len(dependencies)}**",
        f"- Resolved incoming references: **{reference_count}**",
        f"- Relative Markdown links resolving to absent targets: **{len(unresolved)}**",
        f"- Strict assertion errors: **{len(errors)}**",
        "",
        "| Documentation target | Incoming references |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{target}` | {len(items)} |"
        for target, items in dependencies.items()
    )
    lines.extend(["", "## Strict assertion errors", ""])
    lines.extend([f"- {error}" for error in errors] or ["- None"])
    lines.extend(["", "## Unresolved relative Markdown targets", ""])
    if unresolved:
        lines.extend(
            f"- `{item['referrer']}:{item['line']}` -> `{item['resolved_target']}`"
            for item in unresolved
        )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "This companion inventory must be reviewed together with `path-dependencies.json`, which records literal repository-root `docs/...md` references in workflows, scripts, routers, and other files.",
            "",
        ]
    )
    return "\n".join(lines)


def self_test() -> None:
    sample = (
        "[local](mvp10_summary.md)\n"
        "[parent](../architecture/example.md#section)\n"
        "[root](docs/PROJECT_STATUS.md)\n"
        "[external](https://example.com/x.md)\n"
        "[ref]: <wave3/report.md>\n"
    )
    extracted = extracted_destinations(sample)
    assert ("mvp10_summary.md", 1, "inline_markdown") in extracted
    assert resolve_document_target(
        "docs/mvp/README.md", "mvp10_summary.md"
    ) == "docs/mvp/mvp10_summary.md"
    assert resolve_document_target(
        "docs/mvp/README.md", "../architecture/example.md#section"
    ) == "docs/architecture/example.md"
    assert resolve_document_target(
        "docs/mvp/README.md", "docs/PROJECT_STATUS.md"
    ) == "docs/PROJECT_STATUS.md"
    assert resolve_document_target(
        "docs/mvp/README.md", "https://example.com/x.md"
    ) is None
    print("RelayLM relative documentation link inventory self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--assert-dependency", action="append", default=[])
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    try:
        baseline = str(args.baseline or "")
        if re.fullmatch(r"[0-9a-f]{40}", baseline) is None:
            raise RelativeLinkError(
                "baseline commit must be a full 40-character lowercase SHA"
            )
        validate_baseline(baseline)
        markdown_paths = list_markdown_paths(baseline)
        dependencies, unresolved = relative_dependencies(baseline, markdown_paths)
        errors = validate_assertions(dependencies, args.assert_dependency)

        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "relaylm.documentation_relative_link_inventory.v1",
            "baseline_commit": baseline,
            "target_count": len(dependencies),
            "reference_count": sum(len(items) for items in dependencies.values()),
            "dependencies": dependencies,
            "unresolved": unresolved,
            "strict_errors": errors,
        }
        (output_dir / "relative-path-dependencies.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "relative-path-dependencies.md").write_text(
            markdown_summary(baseline, dependencies, unresolved, errors),
            encoding="utf-8",
        )
        print(
            "RelayLM relative documentation link inventory generated "
            f"{payload['reference_count']} reference(s) to "
            f"{payload['target_count']} existing target(s)"
        )
        if args.strict and errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        return 0
    except RelativeLinkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
