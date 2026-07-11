#!/usr/bin/env python3
"""Extract deterministic candidate normative blocks from baseline documentation.

The output is a preparation artifact. It deliberately errs on the side of
including extra source text: preserving an additional paragraph is safer than
silently paraphrasing an exact boundary during the documentation cutover.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "docs" / "planning" / "documentation-cutover-rules.yaml"
DEFAULT_INVENTORY = ROOT / "generated" / "documentation-cutover" / "inventory.json"
DEFAULT_OUTPUT = ROOT / "generated" / "documentation-cutover"
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class DigestError(RuntimeError):
    """Raised when normative candidate extraction is incomplete."""


@dataclasses.dataclass(frozen=True)
class Section:
    heading: str
    level: int
    start_line: int
    end_line: int
    text: str


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
        raise DigestError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise DigestError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DigestError(f"{path}: expected a mapping")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DigestError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DigestError(f"{path}: expected a mapping")
    return value


def read_blob(commit: str, path: str) -> str:
    return run_git("show", f"{commit}:{path}").stdout.replace("\r\n", "\n").replace("\r", "\n")


def split_front_matter(text: str) -> tuple[dict[str, Any], str, int]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text, 1
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    first_body_line = text[: match.end()].count("\n") + 1
    return metadata, text[match.end() :], first_body_line


def sections(body: str, first_body_line: int) -> list[Section]:
    lines = body.splitlines(keepends=True)
    heading_positions: list[tuple[int, int, str]] = []
    for index, raw in enumerate(lines):
        match = HEADING_RE.match(raw.rstrip("\n"))
        if match:
            heading_positions.append((index, len(match.group(1)), match.group(2).strip()))

    if not heading_positions:
        normalized = "".join(lines)
        if normalized and not normalized.endswith("\n"):
            normalized += "\n"
        return [
            Section(
                heading="<document body>",
                level=0,
                start_line=first_body_line,
                end_line=first_body_line + max(len(lines) - 1, 0),
                text=normalized,
            )
        ]

    output: list[Section] = []
    for position, (start_index, level, heading) in enumerate(heading_positions):
        end_index = heading_positions[position + 1][0] if position + 1 < len(heading_positions) else len(lines)
        text = "".join(lines[start_index:end_index])
        if text and not text.endswith("\n"):
            text += "\n"
        output.append(
            Section(
                heading=heading,
                level=level,
                start_line=first_body_line + start_index,
                end_line=first_body_line + max(end_index - 1, start_index),
                text=text,
            )
        )
    return output


def compile_patterns(values: Iterable[Any]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for value in values:
        try:
            patterns.append(re.compile(str(value)))
        except re.error as exc:
            raise DigestError(f"invalid normative regex {value!r}: {exc}") from exc
    return patterns


def is_normative_section(
    section: Section,
    heading_keywords: list[str],
    line_patterns: list[re.Pattern[str]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    heading_lower = section.heading.lower()
    for keyword in heading_keywords:
        if keyword in heading_lower:
            reasons.append(f"heading:{keyword}")
    for pattern in line_patterns:
        if pattern.search(section.text):
            reasons.append(f"content:{pattern.pattern}")
    return bool(reasons), sorted(dict.fromkeys(reasons))


def digest(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def whole_body_block(body: str, first_body_line: int) -> Section:
    text = body if body.endswith("\n") or not body else body + "\n"
    line_count = len(body.splitlines())
    return Section(
        heading="<entire normative body>",
        level=0,
        start_line=first_body_line,
        end_line=first_body_line + max(line_count - 1, 0),
        text=text,
    )


def extract_blocks(
    path: str,
    text: str,
    rules: dict[str, Any],
    force_contract: bool,
) -> list[dict[str, Any]]:
    metadata, body, first_body_line = split_front_matter(text)
    heading_keywords = [str(value).lower() for value in rules.get("normative_heading_keywords", [])]
    line_patterns = compile_patterns(rules.get("normative_line_patterns", []))
    candidates: list[tuple[Section, list[str]]] = []

    for section in sections(body, first_body_line):
        selected, reasons = is_normative_section(section, heading_keywords, line_patterns)
        if selected:
            candidates.append((section, reasons))

    doc_type = str(metadata.get("relaylm_doc_type") or "")
    if not candidates and (force_contract or doc_type in {"contract", "implementation_contract"}):
        candidates.append((whole_body_block(body, first_body_line), ["contract-whole-body-fallback"]))

    seen_ranges: set[tuple[int, int]] = set()
    output: list[dict[str, Any]] = []
    for section, reasons in candidates:
        key = (section.start_line, section.end_line)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        output.append(
            {
                "block_id": f"{path}#L{section.start_line}-L{section.end_line}",
                "heading": section.heading,
                "heading_level": section.level,
                "start_line": section.start_line,
                "end_line": section.end_line,
                "byte_count": len(section.text.encode("utf-8")),
                "line_count": section.end_line - section.start_line + 1,
                "sha256": digest(section.text),
                "selection_reasons": reasons,
            }
        )
    return output


def markdown_summary(
    baseline: str,
    documents: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> str:
    block_count = sum(len(document["blocks"]) for document in documents)
    lines = [
        "# Normative Block Digest Dry Run",
        "",
        f"- Baseline commit: `{baseline}`",
        f"- Candidate documents: **{len(documents)}**",
        f"- Candidate blocks: **{block_count}**",
        f"- Strict errors: **{len(errors)}**",
        f"- Warnings: **{len(warnings)}**",
        "",
        "## Candidate documents",
        "",
        "| Source | Blob | Blocks | Migration decision |",
        "|---|---|---:|---|",
    ]
    for document in documents:
        lines.append(
            f"| `{document['source_path']}` | `{document['source_blob_sha'][:12]}` | "
            f"{len(document['blocks'])} | `{document.get('normative_decision') or 'review'}` |"
        )
    lines.extend(["", "## Strict errors", ""])
    lines.extend([f"- {error}" for error in errors] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
    lines.extend(
        [
            "",
            "## Cutover use",
            "",
            "Each block digest identifies exact source text at the frozen baseline. A cutover PR must record the destination block and verify an equal digest after newline normalization. A wording change requires a separate contract-change PR; it must not be hidden inside documentation migration.",
            "",
        ]
    )
    return "\n".join(lines)


def validate(
    documents: list[dict[str, Any]],
    inventory_by_path: dict[str, dict[str, Any]],
    known_normative: set[str],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    docs_by_path = {document["source_path"]: document for document in documents}

    for path in sorted(known_normative):
        if path not in inventory_by_path:
            errors.append(f"known normative source absent from inventory: {path}")
            continue
        document = docs_by_path.get(path)
        if document is None or not document["blocks"]:
            errors.append(f"known normative source has no extracted block: {path}")

    for path, record in sorted(inventory_by_path.items()):
        decision = record.get("normative_decision")
        if decision == "rebuild_verbatim":
            document = docs_by_path.get(path)
            if document is None or not document["blocks"]:
                errors.append(f"rebuild_verbatim source has no extracted block: {path}")
        elif record.get("contains_normative_signals") and path not in docs_by_path:
            warnings.append(f"normative-signal document not selected for digest output: {path}")

    return errors, warnings


def self_test() -> None:
    sample = "---\nrelaylm_doc_type: contract\n---\n# Sample\n\n## Required behavior\n\nThe producer MUST emit one value.\n"
    rules = {
        "normative_heading_keywords": ["required"],
        "normative_line_patterns": [r"(?i)\bmust\b"],
    }
    blocks = extract_blocks("docs/contracts/sample.md", sample, rules, True)
    assert len(blocks) >= 1
    assert blocks[0]["sha256"]
    print("RelayLM normative digest self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--baseline")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    try:
        rules = load_yaml(args.rules)
        inventory = load_json(args.inventory)
        baseline = str(args.baseline or inventory.get("baseline_commit") or rules.get("baseline_commit") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", baseline):
            raise DigestError("baseline commit must be a full 40-character lowercase SHA")
        run_git("cat-file", "-e", f"{baseline}^{{commit}}")

        raw_records = inventory.get("records")
        if not isinstance(raw_records, list):
            raise DigestError("inventory records must be a list")
        inventory_by_path = {
            str(record["old_path"]): record
            for record in raw_records
            if isinstance(record, dict) and isinstance(record.get("old_path"), str)
        }
        known_normative = set(str(value) for value in rules.get("known_normative_sources", []))
        selected_paths = sorted(
            path
            for path, record in inventory_by_path.items()
            if path in known_normative
            or bool(record.get("contains_normative_signals"))
            or record.get("normative_decision") == "rebuild_verbatim"
        )

        documents: list[dict[str, Any]] = []
        for path in selected_paths:
            record = inventory_by_path[path]
            text = read_blob(baseline, path)
            force_contract = path in known_normative or record.get("normative_decision") == "rebuild_verbatim"
            blocks = extract_blocks(path, text, rules, force_contract)
            if not blocks:
                continue
            documents.append(
                {
                    "source_path": path,
                    "source_blob_sha": record["old_blob_sha"],
                    "source_content_sha256": record["content_sha256"],
                    "current_doc_type": record.get("current_doc_type"),
                    "disposition": record.get("disposition"),
                    "target_paths": record.get("target_paths", []),
                    "normative_decision": record.get("normative_decision"),
                    "blocks": blocks,
                }
            )

        errors, warnings = validate(documents, inventory_by_path, known_normative)
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "relaylm.documentation_normative_digest.v1",
            "baseline_commit": baseline,
            "document_count": len(documents),
            "block_count": sum(len(document["blocks"]) for document in documents),
            "documents": documents,
            "strict_errors": errors,
            "warnings": warnings,
        }
        (output_dir / "normative-digests.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "normative-digests.md").write_text(
            markdown_summary(baseline, documents, errors, warnings),
            encoding="utf-8",
        )
        print(
            "RelayLM normative digest dry run generated "
            f"{len(documents)} document(s) and {payload['block_count']} block(s)"
        )
        if args.strict and errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        return 0
    except DigestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
