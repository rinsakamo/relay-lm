#!/usr/bin/env python3
"""Fail-closed guard for Documentation Hard Cutover 1C-52.

The validation-only I1-GE governance handoff moved from the live
architecture collection to frozen implementation evidence. This guard rejects
reintroduction of the retired path, rejects active references to it across the
repository's text-bearing surfaces, and verifies the canonical evidence
metadata.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

RETIRED = "docs/architecture/i1ge_durable_finalization_crash_validation.md"
CANONICAL = "docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md"
RETIRED_BASENAME = Path(RETIRED).name
SELF_PATH = "scripts/relaylm_i1ge_handoff_cutover_guard.py"

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
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data"}

REFERENCE_ALLOWLISTED_FILES = {
    "docs/evidence/migrations/cutover-1c52-i1ge.md",
    "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
    "docs/evidence/waves/wave2_cross_slice_convergence_audit-source.txt",
    "docs/evidence/waves/wave3_cross_slice_convergence_audit-source.txt",
}
SELF_ALLOWED_LINES = {
    f'RETIRED = "{RETIRED}"',
}
EXACT_ALLOWED_LINES_BY_FILE = {
    "docs/planning/documentation-cutover-rules.yaml": {f"{RETIRED}:"},
    SELF_PATH: SELF_ALLOWED_LINES,
}

MD_LINK_RE = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
HTML_LINK_RE = re.compile(
    r"\b(?:href|src)\s*=\s*([\"'])([^\"'<>]+)\1",
    re.IGNORECASE,
)
REFERENCE_DEF_RE = re.compile(
    r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^ \t\n]+))"
)
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,12})"
    + re.escape(RETIRED_BASENAME)
    + r")(?:[?#][A-Za-z0-9_.~/%=&:-]+)?"
    r"(?![A-Za-z0-9_.-])"
)


def _front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line or line[:1].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _scanned_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        if path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        files.append(path)
    return files


def _resolve(referrer: Path, raw: str, root: Path) -> str | None:
    target = raw.strip().strip("<>")
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
        return None
    target = parsed.path
    if not target:
        return None
    if target.startswith("/"):
        target = target.lstrip("/")
    if target.startswith("docs/"):
        candidate = root / target
    else:
        candidate = referrer.parent / target
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _outside_external_carrier(line: str, start: int, end: int) -> bool:
    for match in HTML_LINK_RE.finditer(line):
        if match.start(2) <= start and end <= match.end(2):
            parsed = urlsplit(match.group(2).strip())
            if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
                return False
    for match in MD_LINK_RE.finditer(line):
        if match.start(1) <= start and end <= match.end(1):
            parsed = urlsplit(match.group(1).strip())
            if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
                return False
    return True


def check_retired_path(errors: list[str], root: Path = ROOT) -> None:
    if (root / RETIRED).exists():
        errors.append(f"{RETIRED}: retired I1-GE handoff path reintroduced")

    for path in _scanned_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in REFERENCE_ALLOWLISTED_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        reported: set[int] = set()

        def allowed(line: str) -> bool:
            return line.strip() in EXACT_ALLOWED_LINES_BY_FILE.get(relative, set())

        for line_number, line in enumerate(text.splitlines(), 1):
            if allowed(line):
                continue

            for match in MD_LINK_RE.finditer(line):
                if _resolve(path, match.group(1), root) == RETIRED:
                    errors.append(
                        f"{relative}:{line_number}: active Markdown link to retired {RETIRED}"
                    )
                    reported.add(line_number)
                    break
            if line_number in reported:
                continue

            for match in HTML_LINK_RE.finditer(line):
                if _resolve(path, match.group(2), root) == RETIRED:
                    errors.append(
                        f"{relative}:{line_number}: active HTML link to retired {RETIRED}"
                    )
                    reported.add(line_number)
                    break
            if line_number in reported:
                continue

            match = REFERENCE_DEF_RE.match(line)
            if match and _resolve(
                path, match.group(1) or match.group(2) or "", root
            ) == RETIRED:
                errors.append(
                    f"{relative}:{line_number}: active reference-style link to retired {RETIRED}"
                )
                reported.add(line_number)
                continue

            literal_start = line.find(RETIRED)
            if literal_start >= 0 and _outside_external_carrier(
                line, literal_start, literal_start + len(RETIRED)
            ):
                errors.append(
                    f"{relative}:{line_number}: active literal reference to retired {RETIRED}"
                )
                reported.add(line_number)
                continue

            for match in PATH_TOKEN_RE.finditer(line):
                if not _outside_external_carrier(
                    line, match.start(1), match.end(1)
                ):
                    continue
                if _resolve(path, match.group(1), root) == RETIRED:
                    errors.append(
                        f"{relative}:{line_number}: active path token to retired {RETIRED}"
                    )
                    reported.add(line_number)
                    break


def check_canonical_metadata(errors: list[str], root: Path = ROOT) -> None:
    path = root / CANONICAL
    if not path.is_file():
        errors.append(f"{CANONICAL}: canonical I1-GE evidence is missing")
        return
    meta = _front_matter(path.read_text(encoding="utf-8"))
    if meta.get("relaylm_doc_type") != "evidence":
        errors.append(
            f"{CANONICAL}: relaylm_doc_type must be evidence, got "
            f"{meta.get('relaylm_doc_type')!r}"
        )
    if meta.get("relaylm_status") != "frozen":
        errors.append(
            f"{CANONICAL}: relaylm_status must be frozen, got "
            f"{meta.get('relaylm_status')!r}"
        )


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    check_retired_path(errors, root)
    check_canonical_metadata(errors, root)
    return errors


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _valid_canonical(root: Path) -> None:
    _write(
        root,
        CANONICAL,
        "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n# Evidence\n",
    )


def self_test() -> None:
    cases: list[tuple[str, bool, str]] = []

    def run(name: str, setup, expect_error: str | None) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _valid_canonical(root)
            setup(root)
            errors = validate(root)
            ok = not errors if expect_error is None else any(
                expect_error in error for error in errors
            )
            cases.append((name, ok, "" if ok else repr(errors)))

    run("canonical repository shape passes", lambda root: None, None)
    run(
        "cutover receipt may narrate the retired source",
        lambda root: _write(
            root,
            "docs/evidence/migrations/cutover-1c52-i1ge.md",
            f"source: {RETIRED}\n",
        ),
        None,
    )
    run(
        "central migration ledger may narrate the retired source",
        lambda root: _write(
            root,
            "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
            f"old_path: {RETIRED}\n",
        ),
        None,
    )
    run(
        "exact cutover-rules override key is accepted",
        lambda root: _write(
            root,
            "docs/planning/documentation-cutover-rules.yaml",
            f"  {RETIRED}:\n",
        ),
        None,
    )
    run(
        "cutover-rules near-match is rejected",
        lambda root: _write(
            root,
            "docs/planning/documentation-cutover-rules.yaml",
            f"  {RETIRED}: trailing\n",
        ),
        "literal reference",
    )
    run(
        "retired file is rejected",
        lambda root: _write(root, RETIRED, "# old\n"),
        "path reintroduced",
    )
    run(
        "root-qualified Markdown link is rejected",
        lambda root: _write(root, "docs/example.md", f"[old]({RETIRED})\n"),
        "Markdown link",
    )
    run(
        "relative parent link is rejected",
        lambda root: _write(
            root,
            "docs/architecture/example.md",
            f"[old]({RETIRED_BASENAME})\n",
        ),
        "Markdown link",
    )
    run(
        "plain prose is rejected",
        lambda root: _write(root, "docs/example.md", f"See {RETIRED}.\n"),
        "literal reference",
    )
    run(
        "backtick prose is rejected",
        lambda root: _write(root, "docs/example.md", f"`{RETIRED}`\n"),
        "literal reference",
    )
    run(
        "frozen Markdown has no generic bypass",
        lambda root: _write(
            root,
            "docs/evidence/example.md",
            f"---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n{RETIRED}\n",
        ),
        "literal reference",
    )
    run(
        "docs txt is scanned",
        lambda root: _write(root, "docs/example.txt", f"{RETIRED}\n"),
        "literal reference",
    )
    run(
        "tests are scanned",
        lambda root: _write(root, "tests/test_docs.py", f'OLD = "{RETIRED}"\n'),
        "literal reference",
    )
    run(
        "root config is scanned",
        lambda root: _write(root, "config.example.yaml", f"old: {RETIRED}\n"),
        "literal reference",
    )
    run(
        "front matter path is rejected",
        lambda root: _write(
            root,
            "docs/example.md",
            f"---\nrelaylm_related_authority: {RETIRED}\n---\n",
        ),
        "literal reference",
    )
    run(
        "HTML href is rejected",
        lambda root: _write(
            root, "docs/example.md", f'<a href="{RETIRED}">old</a>\n'
        ),
        "HTML link",
    )
    run(
        "reference definition is rejected",
        lambda root: _write(root, "docs/example.md", f"[old]: {RETIRED}\n"),
        "reference-style link",
    )
    run(
        "same basename in unrelated directory is accepted",
        lambda root: _write(
            root,
            "docs/example.md",
            f"[other](../other/{RETIRED_BASENAME})\n",
        ),
        None,
    )
    run(
        "canonical link is accepted",
        lambda root: _write(root, "docs/example.md", f"[new]({CANONICAL})\n"),
        None,
    )
    run(
        "external URL carrying the retired literal is accepted",
        lambda root: _write(
            root,
            "docs/example.md",
            f"[external](https://example.invalid/?path={RETIRED})\n",
        ),
        None,
    )
    run(
        "duplicate carriers yield one diagnostic per line",
        lambda root: _write(
            root,
            "docs/example.md",
            f"[old]({RETIRED}) and `{RETIRED}`\n",
        ),
        "Markdown link",
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(
            root,
            CANONICAL,
            "---\nrelaylm_doc_type: guide\nrelaylm_status: frozen\n---\n",
        )
        errors = validate(root)
        ok = any("doc_type must be evidence" in error for error in errors)
        cases.append(("wrong type is rejected", ok, "" if ok else repr(errors)))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(
            root,
            CANONICAL,
            "---\nrelaylm_doc_type: evidence\nrelaylm_status: current\n---\n",
        )
        errors = validate(root)
        ok = any("status must be frozen" in error for error in errors)
        cases.append(("wrong status is rejected", ok, "" if ok else repr(errors)))

    failed = [f"{name}: {detail}" for name, ok, detail in cases if not ok]
    if failed:
        print("I1-GE cutover guard self-test FAILED", file=sys.stderr)
        for item in failed:
            print(f"- {item}", file=sys.stderr)
        raise SystemExit(1)
    print(f"I1-GE cutover guard self-test passed: {len(cases)} assertions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return

    errors = validate()
    if errors:
        print("I1-GE cutover guard FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("I1-GE cutover guard passed")


if __name__ == "__main__":
    main()
