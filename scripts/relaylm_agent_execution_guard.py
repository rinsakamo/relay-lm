#!/usr/bin/env python3
"""Validate RelayLM PR execution epoch, receipt, stop state, and temporary surfaces."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_PATHS = (
    "AGENTS.md",
    "skills/relaylm-stable-implementation/SKILL.md",
    "docs/adr/0007-architecture-first-stable-implementation.md",
    "docs/adr/0008-lane-local-continuation-safety.md",
    "docs/adr/0009-execution-epoch-and-rebootstrap.md",
    "docs/contracts/agent-execution-safety.md",
    "docs/planning/workstream-orchestration.md",
)
RECEIPT_START = "<!-- relaylm-execution-receipt\n"
RECEIPT_END = "\n-->"
RECEIPT_KEYS = (
    "version",
    "lane",
    "bootstrap_main_sha",
    "governance_epoch",
    "writer_id",
    "writer_mode",
    "temporary_artifacts",
)
ALLOWED_LANES = {"C", "D", "R", "governance"}
STOP_LABEL = "relaylm:p6-stop"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WRITER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
GIT_PUSH = re.compile(r"\bgit\s+push\b")
TEMP_WORKFLOW_TOKENS = (
    "probe",
    "structural-refactor",
    "hardening-validate",
    "final-build",
    "build-transfer",
    "auto-correct",
)


class GuardError(RuntimeError):
    """Bounded execution-safety validation error."""


def git(*args: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def git_text(*args: str, root: Path = ROOT) -> str:
    result = git(*args, root=root)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise GuardError(f"git {' '.join(args)}: {detail}")
    return result.stdout.strip()


def governance_epoch(ref: str, root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    for path in GOVERNANCE_PATHS:
        blob = git_text("rev-parse", f"{ref}:{path}", root=root)
        if not HEX40.fullmatch(blob):
            raise GuardError(f"{ref}:{path}: invalid Git blob identity")
        digest.update(f"{path}\0{blob}\n".encode("utf-8"))
    return digest.hexdigest()


def parse_receipt(body: str) -> dict[str, str]:
    starts = [match.start() for match in re.finditer(re.escape(RECEIPT_START), body)]
    if len(starts) != 1:
        raise GuardError("PR body must contain exactly one relaylm-execution-receipt block")
    start = starts[0] + len(RECEIPT_START)
    end = body.find(RECEIPT_END, start)
    if end < 0:
        raise GuardError("relaylm-execution-receipt block is unterminated")

    receipt: dict[str, str] = {}
    for number, line in enumerate(body[start:end].splitlines(), 1):
        if not line.strip():
            continue
        if ":" not in line:
            raise GuardError(f"receipt line {number}: expected key: value")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise GuardError(f"receipt line {number}: empty key or value")
        if key in receipt:
            raise GuardError(f"receipt line {number}: duplicate key {key!r}")
        receipt[key] = value

    unknown = sorted(set(receipt) - set(RECEIPT_KEYS))
    missing = sorted(set(RECEIPT_KEYS) - set(receipt))
    if unknown:
        raise GuardError(f"receipt contains unknown keys: {unknown}")
    if missing:
        raise GuardError(f"receipt is missing keys: {missing}")
    return receipt


def receipt_errors(
    receipt: dict[str, str], expected_epoch: str, expected_main_sha: str
) -> list[str]:
    errors: list[str] = []
    if receipt["version"] != "1":
        errors.append("receipt version must be 1")
    if receipt["lane"] not in ALLOWED_LANES:
        errors.append(f"receipt lane must be one of {sorted(ALLOWED_LANES)}")
    if not HEX40.fullmatch(receipt["bootstrap_main_sha"]):
        errors.append("bootstrap_main_sha must be 40 lowercase hexadecimal characters")
    elif receipt["bootstrap_main_sha"] != expected_main_sha:
        errors.append("bootstrap_main_sha does not equal exact current main; re-bootstrap")
    if not HEX64.fullmatch(receipt["governance_epoch"]):
        errors.append("governance_epoch must be 64 lowercase hexadecimal characters")
    elif receipt["governance_epoch"] != expected_epoch:
        errors.append("governance_epoch is stale; stop writes and re-bootstrap")
    if not WRITER.fullmatch(receipt["writer_id"]):
        errors.append("writer_id must be a stable lowercase identifier")
    if receipt["writer_mode"] != "single":
        errors.append("writer_mode must be single")
    if receipt["temporary_artifacts"] != "none":
        errors.append("temporary_artifacts must be none")
    return errors


def load_event(event_path: Path) -> dict[str, Any]:
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"cannot read GitHub event JSON: {exc}") from exc
    if not isinstance(event, dict):
        raise GuardError("GitHub event must be a JSON object")
    return event


def event_pr(event: dict[str, Any]) -> dict[str, Any]:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        raise GuardError("GitHub event must contain a pull_request object")
    return pull_request


def event_body(event: dict[str, Any]) -> str:
    body = event_pr(event).get("body")
    if not isinstance(body, str):
        raise GuardError("pull_request.body must be text")
    return body


def event_labels(event: dict[str, Any]) -> set[str]:
    labels = event_pr(event).get("labels", [])
    if not isinstance(labels, list):
        raise GuardError("pull_request.labels must be a list")
    names: set[str] = set()
    for item in labels:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise GuardError("pull_request.labels contains an invalid entry")
        names.add(item["name"])
    return names


def changed_paths(base_ref: str, head_ref: str, root: Path = ROOT) -> tuple[str, ...]:
    output = git_text("diff", "--name-only", f"{base_ref}...{head_ref}", "--", root=root)
    return tuple(line for line in output.splitlines() if line)


def temporary_path_reason(path: str) -> str | None:
    pure = PurePosixPath(path)
    if len(pure.parts) == 1 and pure.name.startswith(".") and pure.suffix == ".py":
        return "root-level hidden Python construction artifact"
    if len(pure.parts) >= 3 and pure.parts[:2] == (".github", "workflows"):
        stem = pure.stem.lower()
        for token in TEMP_WORKFLOW_TOKENS:
            if token in stem:
                return f"temporary workflow responsibility {token!r}"
    return None


def changed_surface_errors(
    paths: tuple[str, ...], head_ref: str, root: Path = ROOT
) -> list[str]:
    errors: list[str] = []
    for path in paths:
        reason = temporary_path_reason(path)
        if reason:
            errors.append(f"{path}: {reason}")

        pure = PurePosixPath(path)
        if len(pure.parts) < 3 or pure.parts[:2] != (".github", "workflows"):
            continue
        result = git("show", f"{head_ref}:{path}", root=root)
        if result.returncode != 0:
            continue  # deleted workflow
        text = result.stdout
        if re.search(r"(?m)^\s*contents\s*:\s*write\s*$", text):
            errors.append(f"{path}: changed PR workflow must not grant contents: write")
        if GIT_PUSH.search(text):
            errors.append(f"{path}: changed PR workflow must not contain git push")
    return errors


def validate(
    *, event_path: Path, base_ref: str, head_ref: str, root: Path = ROOT
) -> list[str]:
    event = load_event(event_path)
    expected_main_sha = git_text("rev-parse", base_ref, root=root)
    if not HEX40.fullmatch(expected_main_sha):
        raise GuardError(f"{base_ref}: invalid current-main commit identity")
    expected_epoch = governance_epoch(base_ref, root)
    receipt = parse_receipt(event_body(event))
    errors = receipt_errors(receipt, expected_epoch, expected_main_sha)

    if STOP_LABEL in event_labels(event):
        errors.append("relaylm:p6-stop is active; branch writes and merge are prohibited")

    if HEX40.fullmatch(receipt["bootstrap_main_sha"]):
        ancestor = git(
            "merge-base",
            "--is-ancestor",
            receipt["bootstrap_main_sha"],
            head_ref,
            root=root,
        )
        if ancestor.returncode != 0:
            errors.append("exact current main is not an ancestor of the PR head")

    errors.extend(changed_surface_errors(changed_paths(base_ref, head_ref, root), head_ref, root))
    return sorted(set(errors))


def self_test() -> int:
    failures: list[str] = []

    def expect(label: str, condition: bool) -> None:
        print(f"{'PASS' if condition else 'FAIL'}: {label}")
        if not condition:
            failures.append(label)

    epoch = "a" * 64
    main_sha = "b" * 40
    body = f"""<!-- relaylm-execution-receipt
version: 1
lane: D
bootstrap_main_sha: {main_sha}
governance_epoch: {epoch}
writer_id: chatgpt-lane-d
writer_mode: single
temporary_artifacts: none
-->"""
    receipt = parse_receipt(body)
    expect("valid receipt", not receipt_errors(receipt, epoch, main_sha))

    stale_epoch = dict(receipt)
    stale_epoch["governance_epoch"] = "c" * 64
    expect(
        "stale epoch rejected",
        any("stale" in error for error in receipt_errors(stale_epoch, epoch, main_sha)),
    )

    stale_main = dict(receipt)
    stale_main["bootstrap_main_sha"] = "d" * 40
    expect(
        "stale main rejected",
        any("exact current main" in error for error in receipt_errors(stale_main, epoch, main_sha)),
    )

    expect("hidden patch rejected", temporary_path_reason(".d1_final_review_patch.py") is not None)
    expect("probe workflow rejected", temporary_path_reason(".github/workflows/d1-probe.yml") is not None)
    expect("permanent workflow accepted", temporary_path_reason(".github/workflows/documentation-governance.yml") is None)
    expect("indented git push detected", GIT_PUSH.search("  git push origin HEAD") is not None)
    expect("chained git push detected", GIT_PUSH.search("test -n x && git push origin HEAD") is not None)

    event = {"pull_request": {"body": body, "labels": [{"name": STOP_LABEL}]}}
    expect("stop label parsed", STOP_LABEL in event_labels(event))

    try:
        parse_receipt(body + "\n" + body)
    except GuardError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    expect("duplicate receipt rejected", duplicate_rejected)

    if failures:
        print(f"SELF-TEST FAILED: {len(failures)} assertion(s)")
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--print-epoch", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.print_epoch:
        try:
            print(governance_epoch(args.base_ref))
        except GuardError as exc:
            print(f"FAIL: {exc}")
            return 1
        return 0
    if args.event is None:
        parser.error("--event is required unless --self-test or --print-epoch is used")

    try:
        errors = validate(
            event_path=args.event,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
        )
    except GuardError as exc:
        print(f"FAIL: {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"FAIL: agent execution safety found {len(errors)} issue(s)")
        return 1

    print("PASS: exact main, current epoch, single writer, stop state, and temporary boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
