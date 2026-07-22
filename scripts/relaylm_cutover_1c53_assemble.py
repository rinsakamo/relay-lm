#!/usr/bin/env python3
"""Assemble Documentation Hard Cutover 1C-53 for the I-4C1 handoff."""
from __future__ import annotations

import hashlib
import os
import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "docs/architecture/phase_i4c1_primary_forget_hidden_successor.md"
TARGET = "docs/evidence/implementation/i4c1-primary-forget-hidden-successor-handoff.md"
LOCAL_RECEIPT = "docs/evidence/migrations/cutover-1c53-i4c1.md"
CENTRAL_LEDGER = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
RULES = "docs/planning/documentation-cutover-rules.yaml"
EVIDENCE_INDEX = "docs/evidence/implementation/README.md"
WORKFLOW = ".github/workflows/documentation-current-boundary-smoke.yml"
WORKFLOW_CARRIER = "scripts/relaylm_documentation_current_boundary_smoke_1c53.yml.txt"
GUARD = "scripts/relaylm_i4c1_handoff_cutover_guard.py"
PR_NUMBER = os.environ.get("PR_NUMBER", "pending")
BASE_SHA = os.environ.get("BASE_SHA", "pending")

SOURCE_PR = 396
SOURCE_FINAL_HEAD = "8977dd96fb0ed79fdd7d3d0646aa6e9067d8080e"
SOURCE_MERGE = "4c08a5d973ddcdc657b46e1ae83e3cc3eb6f1fe9"
SOURCE_MERGED_AT = "2026-06-26T03:17:05Z"
SOURCE_RECORDED_ON = "2026-06-26"
EXPECTED_SOURCE_BLOB = "5744dbd445582b28ab030c38e1a49b24e355b4ed"

EXPECTED_REFERRERS = {
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
    "docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md",
    "docs/architecture/phase_i4f_forget_validation.md",
    "docs/evidence/implementation/i4f_completion_report.md",
    "docs/adr/0005-subjective-mem-storage-authority.md",
    "docs/contracts/subjective-mem-storage-authority-and-commit-protocol.md",
}

TEXT_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
OLD_BASENAME = Path(OLD).name
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:(?:\.\.?/|[A-Za-z0-9_.-]+/){0,16})"
    + re.escape(OLD_BASENAME)
    + r")"
    r"(?![A-Za-z0-9_.-])"
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    file_path = ROOT / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def replace_count(text: str, old: str, new: str, count: int, label: str) -> str:
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{label}: expected {count} occurrences, found {actual}")
    return text.replace(old, new)


def resolve_token(relative_file: str, token: str) -> str:
    token = token.split("#", 1)[0].split("?", 1)[0]
    if token.startswith("docs/"):
        return posixpath.normpath(token)
    return posixpath.normpath(posixpath.join(str(Path(relative_file).parent), token))


def rewrite_referrer(path: str, text: str) -> str:
    if path in {"docs/README.md", "docs/architecture/README.md"}:
        lines = text.splitlines(keepends=True)
        kept = [line for line in lines if OLD_BASENAME not in line]
        if len(kept) == len(lines):
            raise RuntimeError(f"{path}: expected indexed I-4C1 line")
        return "".join(kept)

    relative_target = posixpath.relpath(TARGET, str(Path(path).parent))

    def replacement(match: re.Match[str]) -> str:
        token = match.group(1)
        if resolve_token(path, token) != OLD:
            return token
        if token.startswith("docs/"):
            return TARGET
        return relative_target

    rewritten, count = PATH_TOKEN_RE.subn(replacement, text)
    if count < 1 or OLD_BASENAME in rewritten:
        raise RuntimeError(f"{path}: failed to repair retired I-4C1 reference")
    return rewritten


def build_target(source: str) -> str:
    if not source.startswith("---\n"):
        raise RuntimeError("I-4C1 source lacks front matter")
    end = source.find("\n---\n", 4)
    if end < 0:
        raise RuntimeError("I-4C1 source front matter is unterminated")
    body = source[end + 5 :]
    title = "# Phase I-4C1 Primary Forget Hidden-Successor Commit"
    banner = (
        title
        + "\n\n> **Historical implementation evidence.** This frozen handoff records the bounded "
        "hidden-successor commit delivered by PR #396. Current Primary Forget behavior remains "
        "owned by the I-4 contract, I-4C2/I-4D/I-4E/I-4F authorities, implementation, and focused smokes."
    )
    body = replace_count(body, title, banner, 1, "I-4C1 title banner")
    front = """---
relaylm_doc_type: evidence
relaylm_authority: historical_phase_i4c1_primary_forget_hidden_successor_handoff
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_commit: 4c08a5d973ddcdc657b46e1ae83e3cc3eb6f1fe9
relaylm_source_pr: 396
relaylm_recorded_on: 2026-06-26
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current Primary Forget runtime behavior
  - I-4C2 recovery or tombstone finalization
  - I-4D ordinary retrieval exclusion
  - I-4E API or UI behavior
  - I-4F product validation
  - current Subjective MEM storage authority
relaylm_related_authority:
  - ../../architecture/phase_i4_primary_mem_forget_hide_contract.md
  - ../../architecture/phase_i4b_primary_current_state_shared_fence.md
  - ../../architecture/phase_i4c2_primary_forget_recovery_finalization.md
  - ../../architecture/phase_i4d_primary_retrieval_exclusion.md
  - ../../architecture/phase_i4e_forget_api_ui.md
  - ../../architecture/phase_i4f_forget_validation.md
---
"""
    return front + body


def add_evidence_index() -> None:
    text = read(EVIDENCE_INDEX)
    if "i4c1-primary-forget-hidden-successor-handoff.md" in text:
        raise RuntimeError("I-4C1 evidence index entry already exists")
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if "[I-4D completion report]" in line:
            entry = (
                "- [I-4C1 Primary Forget hidden-successor handoff]"
                "(i4c1-primary-forget-hidden-successor-handoff.md) — frozen bounded commit evidence "
                "from PR #396; current Forget behavior remains I-4-contract-, I-4C2/I-4D/I-4E/I-4F-, "
                "implementation-, and focused-smoke-owned.\n"
            )
            lines.insert(index, entry)
            write(EVIDENCE_INDEX, "".join(lines))
            return
    raise RuntimeError("I-4D completion report anchor not found in evidence index")


def add_cutover_rule() -> None:
    text = read(RULES)
    if f"  {OLD}:" in text:
        raise RuntimeError("I-4C1 cutover rule already exists")
    anchor = "\nfamily_rules:\n"
    entry = f"""
  {OLD}:
    disposition: evidence_retained
    target_doc_type: evidence
    target_paths:
      - {TARGET}
    deletion_reason: >-
      Cutover 1C-53: this completed I-4C1 hidden-successor implementation
      handoff was frozen historical evidence mislocated in the live architecture
      collection. The cutover preserves PR #396 provenance, removes it from
      current/product-critical indexes, repairs every active path-bound reference,
      and leaves current Primary Forget authority with the I-4 contract,
      I-4C2/I-4D/I-4E/I-4F, implementation, and focused smokes.
"""
    text = replace_count(text, anchor, entry + anchor, 1, "cutover rules family anchor")
    write(RULES, text)


def guard_source() -> str:
    template = r'''#!/usr/bin/env python3
"""Fail-closed guard for Documentation Hard Cutover 1C-53."""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RETIRED = "__OLD__"
CANONICAL = "__TARGET__"
RETIRED_BASENAME = Path(RETIRED).name
SELF_PATH = "scripts/relaylm_i4c1_handoff_cutover_guard.py"
SCANNED_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
EXCLUDED_DIR_NAMES = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
REFERENCE_ALLOWLISTED_FILES = {
    "docs/evidence/migrations/cutover-1c53-i4c1.md",
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
    r"(?![A-Za-z0-9_.-])"
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
        errors.append(f"{CANONICAL}: canonical I-4C1 evidence is missing")
        return
    text = path.read_text(encoding="utf-8")
    meta = _front_matter(text)
    expected = {
        "relaylm_doc_type": "evidence",
        "relaylm_status": "frozen",
        "relaylm_authority": "historical_phase_i4c1_primary_forget_hidden_successor_handoff",
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
    _write(root, CANONICAL, "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i4c1_primary_forget_hidden_successor_handoff\n---\n# Evidence\n\n> **Historical implementation evidence.**\n")


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
    run("local receipt may narrate retired source", lambda root: _write(root, "docs/evidence/migrations/cutover-1c53-i4c1.md", f"source: {RETIRED}\n"), None)
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
        ("wrong type is rejected", "---\nrelaylm_doc_type: guide\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i4c1_primary_forget_hidden_successor_handoff\n---\n> **Historical implementation evidence.**\n", "relaylm_doc_type"),
        ("wrong status is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: current\nrelaylm_authority: historical_phase_i4c1_primary_forget_hidden_successor_handoff\n---\n> **Historical implementation evidence.**\n", "relaylm_status"),
        ("wrong authority is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: wrong\n---\n> **Historical implementation evidence.**\n", "relaylm_authority"),
        ("missing banner is rejected", "---\nrelaylm_doc_type: evidence\nrelaylm_status: frozen\nrelaylm_authority: historical_phase_i4c1_primary_forget_hidden_successor_handoff\n---\n# Evidence\n", "banner"),
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root, CANONICAL, content)
            errors = validate(root)
            ok = any(expected in error for error in errors)
            cases.append((name, ok, "" if ok else repr(errors)))

    failed = [f"{name}: {detail}" for name, ok, detail in cases if not ok]
    if failed:
        print("I-4C1 cutover guard self-test FAILED", file=sys.stderr)
        for item in failed:
            print(f"- {item}", file=sys.stderr)
        raise SystemExit(1)
    print(f"I-4C1 cutover guard self-test passed: {len(cases)} assertions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    errors = validate()
    if errors:
        print("I-4C1 cutover guard FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("I-4C1 cutover guard passed")


if __name__ == "__main__":
    main()
'''
    return template.replace("__OLD__", OLD).replace("__TARGET__", TARGET)


def build_workflow_carrier() -> None:
    text = read(WORKFLOW)
    path_anchor = '      - "scripts/relaylm_i1ge_handoff_cutover_guard.py"\n'
    path_addition = path_anchor + '      - "scripts/relaylm_i4c1_handoff_cutover_guard.py"\n'
    text = replace_count(text, path_anchor, path_addition, 2, "workflow path filters")

    compile_anchor = "            scripts/relaylm_i1ge_handoff_cutover_guard.py \\\n"
    compile_addition = compile_anchor + "            scripts/relaylm_i4c1_handoff_cutover_guard.py \\\n"
    text = replace_count(text, compile_anchor, compile_addition, 1, "workflow compile list")

    run_anchor = (
        "          python scripts/relaylm_i1ge_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n"
        "          i1ge_cutover_guard_self_test_status=${PIPESTATUS[0]}\n"
    )
    run_addition = run_anchor + (
        "          python scripts/relaylm_i4c1_handoff_cutover_guard.py 2>&1 | tee -a documentation-current-boundary.log\n"
        "          i4c1_cutover_guard_status=${PIPESTATUS[0]}\n"
        "          python scripts/relaylm_i4c1_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n"
        "          i4c1_cutover_guard_self_test_status=${PIPESTATUS[0]}\n"
    )
    text = replace_count(text, run_anchor, run_addition, 1, "workflow guard execution")

    if_anchor = '|| [ "$i1ge_cutover_guard_self_test_status" -ne 0 ] || [ "$contract1_validation_status"'
    if_addition = '|| [ "$i1ge_cutover_guard_self_test_status" -ne 0 ] || [ "$i4c1_cutover_guard_status" -ne 0 ] || [ "$i4c1_cutover_guard_self_test_status" -ne 0 ] || [ "$contract1_validation_status"'
    text = replace_count(text, if_anchor, if_addition, 1, "workflow final status gate")
    write(WORKFLOW_CARRIER, text)


def write_receipts(source_blob: str, source_sha256: str, repaired: list[str]) -> None:
    repaired_text = ", ".join(f"`{path}`" for path in repaired)
    receipt = f"""---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c53_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head, merge attribution, or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current runtime behavior
  - Primary Forget production authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-53 Receipt

- Cutover PR: #{PR_NUMBER}
- Bookkeeping consolidation PR: pending
- Base main: `{BASE_SHA}`
- Validated content head: pending exact-head validation
- Merged commit: pending
- Source: `{OLD}`
- Canonical target: `{TARGET}`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source implementation PR: #{SOURCE_PR}
- Source final head: `{SOURCE_FINAL_HEAD}`
- Source merge commit: `{SOURCE_MERGE}`
- Source merged at: `{SOURCE_MERGED_AT}`
- Source and pre-cutover blob: `{source_blob}`
- Source content SHA-256: `{source_sha256}`
- Source recorded on: `{SOURCE_RECORDED_ON}`
- Current Primary Forget authority retained by: `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`, I-4C2/I-4D/I-4E/I-4F authorities, implementation, and focused smokes
- Active referrers repaired: {repaired_text}
- Fail-closed enforcement: `{GUARD}`, compiled and executed by `{WORKFLOW}`
- Guard self-test: 24 assertions
- Exact-head GitHub Actions: pending
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Open-PR content imported: none; PR #636 was open before branch creation, shared no planned cutover paths at selection time, and no content was imported
- Unresolved review threads: pending final review

This receipt records the in-review Cutover 1C-53 boundary. It does not make the historical I-4C1 handoff current authority and does not change runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior. Merge and exact-head observations remain pending until explicit final review and merge.
"""
    write(LOCAL_RECEIPT, receipt)

    ledger = read(CENTRAL_LEDGER).rstrip() + f"""


### C1C53-001 — I-4C1 hidden-successor implementation handoff

```yaml
cutover_pr: {PR_NUMBER}
merged_commit: pending
bookkeeping_pr: pending
base_main: {BASE_SHA}
validated_content_head: pending
head_at_merge: pending
merged_at: pending
old_path: {OLD}
old_blob_sha: {source_blob}
old_content_sha256: {source_sha256}
source_pr: {SOURCE_PR}
source_final_head: {SOURCE_FINAL_HEAD}
source_merge_commit: {SOURCE_MERGE}
source_merged_at: {SOURCE_MERGED_AT}
recorded_on: {SOURCE_RECORDED_ON}
disposition: evidence_retained
new_canonical_path: {TARGET}
local_receipt: {LOCAL_RECEIPT}
verification:
  old_path_removed: true
  canonical_evidence_metadata_added: true
  current_production_authority_retained_by: i4_contract_i4c2_i4d_i4e_i4f_implementation_and_focused_smokes
  active_referrers_repaired: {len(repaired)}
  current_architecture_indexes_removed: true
  implementation_evidence_index_updated: true
  fail_closed_guard: {GUARD}
  guard_integrated_into_existing_documentation_boundary_workflow: true
  guard_self_test_assertions: 24
  exact_head_workflow_runs: pending
  exact_head_workflow_success: pending
  exact_head_workflow_failure: pending
  unresolved_review_threads: pending
  runtime_files_changed: 0
  relaylm_changed_files: 0
  open_pr_content_imported: false
```

PR #{PR_NUMBER} preserves the completed I-4C1 hidden-successor commit handoff as frozen implementation evidence. Current Primary Forget behavior remains I-4-contract-, I-4C2/I-4D/I-4E/I-4F-, implementation-, and focused-smoke-owned. Merge attribution and exact-head validation remain pending until explicit final review and bookkeeping consolidation.
"""
    write(CENTRAL_LEDGER, ledger)


def main() -> None:
    old_path = ROOT / OLD
    target_path = ROOT / TARGET
    if not old_path.is_file():
        raise RuntimeError(f"missing source: {OLD}")
    if target_path.exists():
        raise RuntimeError(f"target already exists: {TARGET}")

    source_bytes = old_path.read_bytes()
    source_blob = subprocess.check_output(["git", "hash-object", OLD], cwd=ROOT, text=True).strip()
    if source_blob != EXPECTED_SOURCE_BLOB:
        raise RuntimeError(f"unexpected I-4C1 source blob: {source_blob}")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    source_text = source_bytes.decode("utf-8")

    write(TARGET, build_target(source_text))
    old_path.unlink()

    repaired: list[str] = []
    for path in sorted(EXPECTED_REFERRERS):
        original = read(path)
        updated = rewrite_referrer(path, original)
        if updated == original:
            raise RuntimeError(f"{path}: expected reference repair did not change file")
        write(path, updated)
        repaired.append(path)

    if set(repaired) != EXPECTED_REFERRERS:
        raise RuntimeError(f"unexpected repaired set: {repaired}")

    add_evidence_index()
    add_cutover_rule()
    write(GUARD, guard_source())
    build_workflow_carrier()
    write_receipts(source_blob, source_sha256, repaired)

    print(f"assembled Cutover 1C-53 for PR #{PR_NUMBER}")
    print(f"source blob: {source_blob}")
    print(f"source sha256: {source_sha256}")
    print(f"repaired referrers: {len(repaired)}")


if __name__ == "__main__":
    main()
