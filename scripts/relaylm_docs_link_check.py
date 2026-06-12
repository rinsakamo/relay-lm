from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]

INLINE_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)")
EXTERNAL_SCHEMES = {
    "data",
    "file",
    "ftp",
    "http",
    "https",
    "javascript",
    "mailto",
    "sandbox",
    "tel",
}


def _extract_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")].strip()

    # Markdown allows an optional quoted title after the destination.
    # RelayLM docs do not use unescaped spaces in local paths, so the first
    # whitespace-delimited token is the destination for this lightweight check.
    return target.split(maxsplit=1)[0] if target else ""


def _resolve_local_target(source: Path, target: str) -> Path | None:
    if not target or target.startswith("#"):
        return None

    parsed = urlsplit(target)
    if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
        return None

    path_text = unquote(parsed.path)
    if not path_text:
        return None

    if path_text.startswith("/"):
        # Root-relative web links are outside the repository-file contract.
        return None

    return (source.parent / path_text).resolve()


def _iter_markdown_links(source: Path) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    in_fence = False
    fence_marker: str | None = None

    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            continue

        if in_fence:
            continue

        for match in INLINE_LINK_RE.finditer(line):
            links.append((line_number, _extract_target(match.group(1))))

        reference_match = REFERENCE_LINK_RE.match(line)
        if reference_match:
            links.append((line_number, _extract_target(reference_match.group(1))))

    return links


def check_links(repo_root: Path) -> tuple[int, int, list[str]]:
    root = repo_root.resolve()
    markdown_files = [root / "README.md"]
    markdown_files.extend(sorted((root / "docs").rglob("*.md")))

    checked_links = 0
    broken_links: list[str] = []

    for source in markdown_files:
        if not source.is_file():
            continue

        for line_number, target in _iter_markdown_links(source):
            resolved = _resolve_local_target(source, target)
            if resolved is None:
                continue

            checked_links += 1
            try:
                resolved.relative_to(root)
            except ValueError:
                broken_links.append(
                    f"{source.relative_to(root)}:{line_number}: "
                    f"link escapes repository: {target}"
                )
                continue

            if not resolved.exists():
                broken_links.append(
                    f"{source.relative_to(root)}:{line_number}: "
                    f"missing target {target} -> {resolved.relative_to(root)}"
                )

    return len(markdown_files), checked_links, broken_links


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check local Markdown links in README.md and docs/**/*.md."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="repository root to check (defaults to this script's repository)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    markdown_file_count, checked_links, broken_links = check_links(args.repo_root)

    if broken_links:
        for message in broken_links:
            print(f"error: {message}", file=sys.stderr)
        print(
            f"error: {len(broken_links)} broken local Markdown link(s) found",
            file=sys.stderr,
        )
        return 1

    print(
        "ok documentation links "
        f"({markdown_file_count} Markdown files, {checked_links} local links)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
