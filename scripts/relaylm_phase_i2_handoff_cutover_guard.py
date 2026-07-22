#!/usr/bin/env python3
"""Fail-closed guard for Documentation Hard Cutover 1C-55."""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RETIRED = "docs/architecture/phase_i2_real_soul_lab_observation.md"
CANONICAL = "docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md"
RETIRED_BASENAME = Path(RETIRED).name
SELF_PATH = "scripts/relaylm_phase_i2_handoff_cutover_guard.py"
SCANNED_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
EXCLUDED_DIR_NAMES = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
REFERENCE_ALLOWLISTED_FILES = {
    "docs/evidence/migrations/cutover-1c55-phase-i2.md",
    "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
}
EXACT_ALLOWED_LINES_BY_FILE = {
    "docs/planning/documentation-cutover-rules.yaml": {f"{RETIRED}:"},
    SELF_PATH: {f'RETIRED = "{RETIRED}"'},
}
MD_LINK_RE = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
HTML_LINK_RE = re.compile(r"\b(?:href|src)\s*=\s*([\"'])([^\"'<>]+)\1", re.IGNORECASE)
REFERENCE_DEF_RE = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^ \t\n]+))")
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,16})"
    + re.escape(RETIRED_BASENAME)
    + r")(?:[?#][A-Za-z0-9_.~/%=&:-]+)?"
    r"(?![A-Za-z0-9_-])"
)
URL_RE = re.compile(r"https?://[^\s)>\]}'\"]+")


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
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _external(token: str) -> bool:
    return urlsplit(token).scheme.lower() in {"http", "https", "mailto", "tel", "data"}


def _resolved(relative: str, token: str) -> str:
    token = token.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
    if token.startswith("docs/"):
        return posixpath.normpath(token)
    return posixpath.normpath(posixpath.join(str(Path(relative).parent), token))


def _inside_external_url(line: str, start: int, end: int) -> bool:
    return any(match.start() <= start and end <= match.end() for match in URL_RE.finditer(line))


def check_retired_path(errors: list[str], root: Path = ROOT) -> None:
    retired = root / RETIRED
    if retired.exists():
        errors.append(f"{RETIRED}: retired path reintroduced")
    for path in _scanned_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in REFERENCE_ALLOWLISTED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        allowed = EXACT_ALLOWED_LINES_BY_FILE.get(relative, set())
        for line_number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped in allowed:
                continue
            for match in MD_LINK_RE.finditer(line):
                token = match.group(1).split()[0].strip("<>")
                if not _external(token) and _resolved(relative, token) == RETIRED:
                    errors.append(f"{relative}:{line_number}: Markdown link to retired {RETIRED}")
                    break
            for match in HTML_LINK_RE.finditer(line):
                token = match.group(2)
                if not _external(token) and _resolved(relative, token) == RETIRED:
                    errors.append(f"{relative}:{line_number}: HTML link to retired {RETIRED}")
                    break
            ref = REFERENCE_DEF_RE.match(line)
            if ref:
                token = ref.group(1) or ref.group(2) or ""
                if not _external(token) and _resolved(relative, token) == RETIRED:
                    errors.append(f"{relative}:{line_number}: reference-style link to retired {RETIRED}")
            for match in PATH_TOKEN_RE.finditer(line):
                if _inside_external_url(line, match.start(), match.end()):
                    continue
                if _resolved(relative, match.group(1)) == RETIRED:
                    errors.append(f"{relative}:{line_number}: active path token to retired {RETIRED}")
                    break


def check_canonical_metadata(errors: list[str], root: Path = ROOT) -> None:
    path = root / CANONICAL
    if not path.is_file():
        errors.append(f"{CANONICAL}: canonical Phase I-2 observation evidence is missing")
        return
    text = path.read_text(encoding="utf-8")
    meta = _front_matter(text)
    expected = {
        "relaylm_doc_type": "evidence",
        "relaylm_status": "frozen",
        "relaylm_authority": "historical_phase_i2_real_soul_lab_observation_handoff",
    }
    for key, value in expected.items():
        if meta.get(key) != value:
            errors.append(f"{CANONICAL}: {key} must be {value}, got {meta.get(key)!r}")
    if "**Historical implementation evidence.**" not in text:
        errors.append(f"{CANONICAL}: historical evidence banner is missing")


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
    _write(root, CANONICAL, "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i2_real_soul_lab_observation_handoff\n---\n# Evidence\n\n> **Historical implementation evidence.**\n")


def self_test() -> None:
    cases: list[tuple[str, bool, str]] = []

    def run(name: str, setup, expect_error: str | None) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _valid_canonical(root)
            setup(root)
            errors = validate(root)
            ok = not errors if expect_error is None else any(expect_error in error for error in errors)
            cases.append((name, ok, "" if ok else repr(errors)))

    run("canonical repository shape passes", lambda root: None, None)
    run("local receipt may narrate retired source", lambda root: _write(root, "docs/evidence/migrations/cutover-1c55-phase-i2.md", f"source: {RETIRED}\n"), None)
    run("central ledger may narrate retired source", lambda root: _write(root, "docs/evidence/migrations/documentation-hard-cutover-receipt.md", f"old_path: {RETIRED}\n"), None)
    run("exact cutover-rules key is accepted", lambda root: _write(root, "docs/planning/documentation-cutover-rules.yaml", f"  {RETIRED}:\n"), None)
    run("cutover-rules near-match is rejected", lambda root: _write(root, "docs/planning/documentation-cutover-rules.yaml", f"  {RETIRED}: trailing\n"), "active path token")
    run("retired file is rejected", lambda root: _write(root, RETIRED, "# old\n"), "path reintroduced")
    run("root-qualified Markdown link is rejected", lambda root: _write(root, "docs/example.md", f"[old]({RETIRED})\n"), "Markdown link")
    run("relative Markdown link is rejected", lambda root: _write(root, "docs/architecture/example.md", f"[old]({RETIRED_BASENAME})\n"), "Markdown link")
    run("plain prose is rejected", lambda root: _write(root, "docs/example.md", f"See {RETIRED}.\n"), "active path token")
    run("backtick prose is rejected", lambda root: _write(root, "docs/example.md", f"`{RETIRED}`\n"), "active path token")
    run("frozen evidence has no generic bypass", lambda root: _write(root, "docs/evidence/example.md", f"---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\n---\n{RETIRED}\n"), "active path token")
    run("docs txt is scanned", lambda root: _write(root, "docs/example.txt", f"{RETIRED}\n"), "active path token")
    run("tests are scanned", lambda root: _write(root, "tests/test_docs.py", f'OLD = "{RETIRED}"\n'), "active path token")
    run("root config is scanned", lambda root: _write(root, "config.example.yaml", f"old: {RETIRED}\n"), "active path token")
    run("front matter path is rejected", lambda root: _write(root, "docs/example.md", f"---\nrelaylm_related_authority: {RETIRED}\n---\n"), "active path token")
    run("HTML href is rejected", lambda root: _write(root, "docs/example.md", f'<a href="{RETIRED}">old</a>\n'), "HTML link")
    run("reference definition is rejected", lambda root: _write(root, "docs/example.md", f"[old]: {RETIRED}\n"), "reference-style link")
    run("same basename in unrelated directory is accepted", lambda root: _write(root, "docs/example.md", f"[other](other/{RETIRED_BASENAME})\n"), None)
    run("canonical link is accepted", lambda root: _write(root, "docs/example.md", f"[new]({CANONICAL})\n"), None)
    run("external URL carrying retired literal is accepted", lambda root: _write(root, "docs/example.md", f"[external](https://example.invalid/?path={RETIRED})\n"), None)

    for name, content, expected in (
        ("wrong type is rejected", "---\nrelaylm_doc_type: guide\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i2_real_soul_lab_observation_handoff\n---\n> **Historical implementation evidence.**\n", "relaylm_doc_type"),
        ("wrong status is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: current\nrelaylm_authority: historical_phase_i2_real_soul_lab_observation_handoff\n---\n> **Historical implementation evidence.**\n", "relaylm_status"),
        ("wrong authority is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: wrong\n---\n> **Historical implementation evidence.**\n", "relaylm_authority"),
        ("missing banner is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i2_real_soul_lab_observation_handoff\n---\n# Evidence\n", "banner"),
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root, CANONICAL, content)
            errors = validate(root)
            ok = any(expected in error for error in errors)
            cases.append((name, ok, "" if ok else repr(errors)))

    failed = [f"{name}: {detail}" for name, ok, detail in cases if not ok]
    if failed:
        print("Phase I-2 cutover guard self-test FAILED", file=sys.stderr)
        for item in failed:
            print(f"- {item}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Phase I-2 cutover guard self-test passed: {len(cases)} assertions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    errors = validate()
    if errors:
        print("Phase I-2 cutover guard FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Phase I-2 cutover guard passed")


if __name__ == "__main__":
    main()
