#!/usr/bin/env python3
"""Validate retired documentation paths from the generic retirement manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "records/documentation/retirement-manifest.json"

SCANNED_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
HISTORICAL_PREFIXES = (
    "docs/evidence/",
)
HISTORICAL_EXACT_PATHS = {
    "docs/planning/documentation-architecture-inventory.md",
    "docs/planning/documentation-cutover-rules.yaml",
    "docs/planning/documentation-cutover-tooling.md",
    "docs/planning/documentation-placement-decisions.md",
    "docs/planning/documentation-target-architecture-graph.md",
    MANIFEST_PATH,
    "scripts/relaylm_retirement_manifest_reference_guard.py",
}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data"}
URL_RE = re.compile(r"https?://[^\s)>\]}'\"]+")
# Basenames that do not identify a retired file on their own: the repository
# carries one of these in almost every directory, so matching a relative
# reference by basename alone would fire on unrelated routers. For these the
# relative-reference pattern additionally requires the retired file's own
# parent directory -- the shortest path-specific suffix that distinguishes
# it. Exact full-path detection is unaffected.
GENERIC_BASENAMES = frozenset({"README.md"})


class GuardError(RuntimeError):
    """Raised when the manifest or a replacement cannot be read safely."""


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_manifest(root: Path) -> list[dict[str, object]]:
    path = root / MANIFEST_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"{MANIFEST_PATH}: cannot read valid JSON: {exc}") from exc
    entries = value.get("entries") if isinstance(value, dict) else None
    if not isinstance(entries, list):
        raise GuardError(f"{MANIFEST_PATH}: entries must be a list")
    return [item for item in entries if isinstance(item, dict)]


def _front_matter(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GuardError(f"{path.as_posix()}: cannot read UTF-8 Markdown: {exc}") from exc
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    metadata: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if not line or line[:1].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata


def _is_historical_carrier(relative: str) -> bool:
    return relative in HISTORICAL_EXACT_PATHS or relative.startswith(HISTORICAL_PREFIXES)


def _scanned_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        files.append(path)
    return files


def _url_spans(line: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in URL_RE.finditer(line)]


def _outside_external_url(line: str, start: int, end: int) -> bool:
    for url_start, url_end in _url_spans(line):
        if url_start <= start and end <= url_end:
            parsed = urlsplit(line[url_start:url_end])
            if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
                return False
    return True


def _relative_suffix(old_path: str) -> str:
    """Shortest trailing path fragment that identifies the retired file."""
    path = Path(old_path)
    if path.name not in GENERIC_BASENAMES:
        return path.name
    parent = path.parent.name
    return f"{parent}/{path.name}" if parent else path.name


def _reference_pattern(old_path: str) -> re.Pattern[str]:
    suffix = re.escape(_relative_suffix(old_path))
    return re.compile(
        r"(?<![A-Za-z0-9_.-])"
        r"((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,20})"
        + suffix
        + r")(?:[?#][A-Za-z0-9_.~/%=&:-]+)?"
        r"(?![A-Za-z0-9_-])"
    )


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        entries = _read_manifest(root)
    except GuardError as exc:
        return [str(exc)]

    patterns: list[tuple[str, re.Pattern[str]]] = []
    for item in entries:
        old_path = item.get("old_path")
        if not isinstance(old_path, str) or not old_path:
            continue
        if (root / old_path).exists():
            errors.append(f"{old_path}: retired path is present")
        patterns.append((old_path, _reference_pattern(old_path)))

        replacements = item.get("replacement_paths", [])
        if not isinstance(replacements, list):
            continue
        for replacement in replacements:
            if not isinstance(replacement, str):
                continue
            target = root / replacement
            if not target.is_file():
                errors.append(f"{old_path}: replacement path is missing: {replacement}")
                continue
            if replacement.startswith("docs/evidence/") and replacement.endswith(".md"):
                try:
                    metadata = _front_matter(target)
                except GuardError as exc:
                    errors.append(str(exc))
                    continue
                if metadata.get("relaylm_doc_type") != "evidence":
                    errors.append(f"{replacement}: evidence replacement must declare relaylm_doc_type evidence")
                if metadata.get("relaylm_status") != "frozen":
                    errors.append(f"{replacement}: evidence replacement must declare relaylm_status frozen")

    for path in _scanned_files(root):
        relative = _relative(path, root)
        if _is_historical_carrier(relative):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, 1):
            for old_path, pattern in patterns:
                literal_start = line.find(old_path)
                if literal_start >= 0 and _outside_external_url(
                    line, literal_start, literal_start + len(old_path)
                ):
                    errors.append(
                        f"{relative}:{line_number}: active reference to retired {old_path}"
                    )
                    break
                for match in pattern.finditer(line):
                    if _outside_external_url(line, match.start(1), match.end(1)):
                        errors.append(
                            f"{relative}:{line_number}: active reference to retired {old_path}"
                        )
                        break
                else:
                    continue
                break
    return sorted(set(errors))


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def self_test() -> int:
    failures: list[str] = []

    def run(label: str, setup, expected: str | None) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_path = "docs/architecture/old_handoff.md"
            replacement = "docs/evidence/implementation/new-handoff.md"
            _write(
                root,
                MANIFEST_PATH,
                json.dumps(
                    {
                        "schema_version": "relaylm.documentation.retirement-manifest.v1",
                        "entries": [
                            {
                                "old_path": old_path,
                                "last_live_commit": "0" * 40,
                                "old_blob_sha": "1" * 40,
                                "removed_by_pr": 1,
                                "replacement_paths": [replacement],
                                "disposition": "replaced",
                                "retention_reason": "self-test",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
            )
            _write(
                root,
                replacement,
                "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n# Evidence\n",
            )
            setup(root, old_path, replacement)
            errors = validate(root)
            passed = not errors if expected is None else any(expected in item for item in errors)
            if passed:
                print(f"PASS: {label}")
            else:
                print(f"FAIL: {label}: {errors!r}")
                failures.append(label)

    run("valid manifest-backed retirement passes", lambda *_: None, None)
    run(
        "retired path reintroduction is rejected",
        lambda root, old, _new: _write(root, old, "# Old\n"),
        "retired path is present",
    )
    run(
        "missing replacement is rejected",
        lambda root, _old, new: (root / new).unlink(),
        "replacement path is missing",
    )
    run(
        "non-frozen evidence replacement is rejected",
        lambda root, _old, new: _write(
            root,
            new,
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: current\n---\n# Evidence\n",
        ),
        "relaylm_status frozen",
    )
    run(
        "active full-path reference is rejected",
        lambda root, old, _new: _write(root, "docs/architecture/current.md", f"See {old}.\n"),
        "active reference",
    )
    run(
        "active relative basename reference is rejected",
        lambda root, old, _new: _write(
            root,
            "docs/architecture/current.md",
            f"[old]({Path(old).name})\n",
        ),
        "active reference",
    )
    run(
        "historical evidence may name retired paths",
        lambda root, old, _new: _write(root, "docs/evidence/migrations/receipt.md", f"source: {old}\n"),
        None,
    )
    run(
        "cutover rules may name retired paths",
        lambda root, old, _new: _write(
            root,
            "docs/planning/documentation-cutover-rules.yaml",
            f"{old}:\n  disposition: replaced\n",
        ),
        None,
    )
    run(
        "target architecture graph may name retired source paths",
        lambda root, old, _new: _write(
            root,
            "docs/planning/documentation-target-architecture-graph.md",
            f"source: {old}\n",
        ),
        None,
    )
    run(
        "external URL may contain retired basename",
        lambda root, old, _new: _write(
            root,
            "docs/architecture/current.md",
            f"https://example.invalid/archive/{Path(old).name}\n",
        ),
        None,
    )

    # A retired path whose basename is generic ("README.md"): the relative
    # pattern must key on "migrations/README.md", never on the bare basename
    # every other router in the repository also uses.
    def run_generic(label: str, reference: str, expected: str | None) -> None:
        old_path = "docs/evidence/migrations/README.md"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(
                root,
                MANIFEST_PATH,
                json.dumps(
                    {
                        "schema_version": "relaylm.documentation.retirement-manifest.v1",
                        "entries": [
                            {
                                "old_path": old_path,
                                "last_live_commit": "0" * 40,
                                "old_blob_sha": "1" * 40,
                                "removed_by_pr": 1,
                                "replacement_paths": [],
                                "disposition": "retired_git_history_only",
                                "retention_reason": "self-test",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
            )
            _write(root, "docs/architecture/current.md", f"See {reference} for details.\n")
            errors = validate(root)
            passed = not errors if expected is None else any(expected in item for item in errors)
            if passed:
                print(f"PASS: {label}")
            else:
                print(f"FAIL: {label}: {errors!r}")
                failures.append(label)

    for unrelated in (
        "README.md",
        "docs/README.md",
        "apps/soul-lab/README.md",
        "docs/evidence/README.md",
    ):
        run_generic(
            f"generic-basename retirement does not reject unrelated {unrelated}",
            unrelated,
            None,
        )

    for retired in (
        "docs/evidence/migrations/README.md",
        "migrations/README.md",
        "../migrations/README.md",
        "../../evidence/migrations/README.md",
    ):
        run_generic(
            f"generic-basename retirement rejects {retired}",
            retired,
            "active reference",
        )

    run_generic(
        "external URL containing the generic retired suffix is permitted",
        "https://example.invalid/archive/migrations/README.md",
        None,
    )

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Retirement manifest reference guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
