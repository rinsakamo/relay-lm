#!/usr/bin/env python3
"""Build the commit-fixed RelayLM documentation cutover dry-run inventory.

The command reads Markdown blobs from a selected Git commit rather than from the
working tree. It produces deterministic inventory, provenance, migration receipt
preview, and path-dependency artifacts without moving or rewriting documents.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "docs" / "planning" / "documentation-cutover-rules.yaml"
DEFAULT_OUTPUT = ROOT / "generated" / "documentation-cutover"
MAX_TEXT_BYTES = 2 * 1024 * 1024
PR_RE = re.compile(r"(?:\bPR\s*#|\(#|(?<![A-Za-z0-9])#)([1-9][0-9]*)", re.IGNORECASE)
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
SIMPLE_PATH_GREP_RE = r"docs/[A-Za-z0-9_./-]+\.md"


class CutoverError(RuntimeError):
    """Raised when the dry run cannot produce trustworthy output."""


@dataclasses.dataclass(frozen=True)
class GitBlob:
    path: str
    sha: str


@dataclasses.dataclass
class Classification:
    disposition: str
    target_doc_type: str
    target_paths: list[str]
    rule_id: str
    requires_manual_section_map: bool = False
    deletion_reason: str | None = None
    normative_decision: str | None = None
    # Maps every entry in target_paths to its own declared relaylm_doc_type.
    # Populated for every classification (single-type family rules and
    # overrides map every target to the same type; a `target_records`
    # override may map different targets to different types). This is the
    # structurally authoritative source for per-target type checking --
    # `target_doc_type` above is retained only as a human-readable display
    # field and must never be treated as the one true type when a source
    # splits into targets of different document types.
    target_doc_types: dict[str, str] = dataclasses.field(default_factory=dict)


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
        command = "git " + " ".join(args)
        raise CutoverError(f"{command} failed: {result.stderr.strip()}")
    return result


def load_rules(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CutoverError(f"cannot read rules {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CutoverError(f"{path}: rules must be a mapping")
    return value


def validate_baseline(commit: str) -> None:
    run_git("cat-file", "-e", f"{commit}^{{commit}}")


def list_blobs(commit: str, prefix: str = "docs") -> list[GitBlob]:
    output = run_git("ls-tree", "-r", commit, "--", prefix).stdout
    blobs: list[GitBlob] = []
    for line in output.splitlines():
        if "\t" not in line:
            continue
        metadata, path = line.split("\t", 1)
        parts = metadata.split()
        if len(parts) != 3 or parts[1] != "blob":
            continue
        if path.endswith(".md"):
            blobs.append(GitBlob(path=path, sha=parts[2]))
    return sorted(blobs, key=lambda item: item.path)


def read_blob(commit: str, path: str) -> str:
    result = run_git("show", f"{commit}:{path}")
    data = result.stdout
    if len(data.encode("utf-8")) > MAX_TEXT_BYTES:
        raise CutoverError(f"{path}: exceeds {MAX_TEXT_BYTES} byte text bound")
    return data.replace("\r\n", "\n").replace("\r", "\n")


def parse_front_matter(text: str) -> tuple[dict[str, Any], str, bool]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text, False
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text[match.end() :], True
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, text[match.end() :], True


def content_digest(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def first_introduction(commit: str, path: str) -> tuple[str, str | None]:
    result = run_git(
        "log",
        "--follow",
        "--diff-filter=A",
        "--format=%H%x09%aI",
        commit,
        "--",
        path,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return commit, None
    raw = lines[-1].split("\t", 1)
    return raw[0], raw[1] if len(raw) == 2 else None


def commit_message(commit: str, cache: dict[str, str]) -> str:
    if commit not in cache:
        cache[commit] = run_git("show", "-s", "--format=%B", commit).stdout
    return cache[commit]


def source_pr_number(message: str) -> int | None:
    matches = PR_RE.findall(message)
    return int(matches[-1]) if matches else None


def stable_stem(path: str) -> str:
    stem = PurePosixPath(path).stem.lower().replace("_", "-")
    stem = re.sub(
        r"^(?:phase-?[0-9a-z]+-|phase|wave-?[0-9]+-|acg-?[0-9]+-|cw-a[0-9]+-|"
        r"pm-d[0-9]+-|o[0-9][a-z0-9]*-|i[0-9][a-z0-9]*-|e[0-9]-r[0-9]+-|"
        r"ui-[ab][0-9a-z]*-|relaymem-m3[a-z]*-)+",
        "",
        stem,
    )
    stem = re.sub(r"(?:-handoff|-completion-report|-validation-receipt)$", "", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    return stem or "document"


def template_values(path: str) -> dict[str, str]:
    posix = PurePosixPath(path)
    basename = posix.name
    values = {
        "basename": basename,
        "basename_lower": basename.lower(),
        "stem": posix.stem,
        "stable_stem": stable_stem(path),
        "relative_after_docs": path.removeprefix("docs/"),
        "relative_after_mvp": path.removeprefix("docs/mvp/"),
        "relative_after_smoke": path.removeprefix("docs/smoke/"),
        "relative_after_tools": path.removeprefix("docs/tools/"),
    }
    return values


def render_template(template: str, path: str) -> str:
    return template.format_map(template_values(path))


def inferred_target_type(target_path: str, metadata: dict[str, Any]) -> str:
    if target_path == "docs/README.md" or target_path.endswith("/README.md"):
        return "documentation_index"
    mapping = {
        "adr": "adr",
        "architecture": "subsystem_architecture",
        "contracts": "contract",
        "evaluation": "evaluation_method",
        "evidence": "evidence",
        "guides": "guide",
        "operations": "operations",
        "planning": "planning",
        "proposals": "proposal",
        "reference": "reference",
        "release": "release",
        "strategy": "strategy",
        "templates": "template",
    }
    parts = PurePosixPath(target_path).parts
    if len(parts) > 1 and parts[0] == "docs":
        return mapping.get(parts[1], str(metadata.get("relaylm_doc_type") or "guide"))
    return str(metadata.get("relaylm_doc_type") or "guide")


def architecture_keyword_target(path: str, body: str, rule: dict[str, Any]) -> list[str]:
    haystack = f"{path}\n{body[:12000]}".lower()
    mapping = rule.get("keyword_targets") or rule.get("target_by_keyword") or {}
    targets: list[str] = []
    if isinstance(mapping, dict):
        for keyword, target in mapping.items():
            if str(keyword).lower() in haystack and isinstance(target, str):
                targets.append(target)
    if not targets and isinstance(rule.get("fallback_target"), str):
        targets.append(rule["fallback_target"])
    return targets


def normalize_targets(values: Iterable[str]) -> list[str]:
    return sorted(dict.fromkeys(value for value in values if value))


def classify(
    path: str,
    metadata: dict[str, Any],
    body: str,
    rules: dict[str, Any],
) -> Classification:
    overrides = rules.get("path_overrides", {})
    if path in overrides:
        raw = overrides[path]
        has_target_records = "target_records" in raw
        has_legacy_shape = "target_paths" in raw or "target_doc_type" in raw
        if has_target_records:
            if has_legacy_shape:
                raise CutoverError(
                    f"path_overrides[{path!r}] mixes target_records with legacy "
                    "target_paths/target_doc_type; use exactly one shape"
                )
            target_records = raw["target_records"]
            if not isinstance(target_records, list) or not target_records:
                raise CutoverError(f"path_overrides[{path!r}].target_records must be a non-empty list")

            target_doc_types: dict[str, str] = {}
            for record in target_records:
                if not isinstance(record, dict):
                    raise CutoverError(
                        f"path_overrides[{path!r}].target_records has a non-mapping entry: {record!r}"
                    )
                target_path = record.get("target_path")
                target_type = record.get("target_doc_type")
                if not isinstance(target_path, str) or not target_path:
                    raise CutoverError(
                        f"path_overrides[{path!r}].target_records entry is missing a non-empty "
                        f"target_path: {record!r}"
                    )
                if not isinstance(target_type, str) or not target_type:
                    raise CutoverError(
                        f"path_overrides[{path!r}].target_records entry is missing a non-empty "
                        f"target_doc_type: {record!r}"
                    )
                if target_path in target_doc_types:
                    if target_doc_types[target_path] != target_type:
                        raise CutoverError(
                            f"path_overrides[{path!r}].target_records has conflicting document types "
                            f"for target_path {target_path!r}: {target_doc_types[target_path]!r} vs "
                            f"{target_type!r}"
                        )
                    raise CutoverError(
                        f"path_overrides[{path!r}].target_records has a duplicate target_path: "
                        f"{target_path!r}"
                    )
                target_doc_types[target_path] = target_type

            targets = normalize_targets(target_doc_types.keys())
            if set(targets) != set(target_doc_types.keys()):
                raise CutoverError(
                    f"path_overrides[{path!r}].target_records mapping does not exactly cover the "
                    "normalized target list"
                )
            # Deterministic display-only summary; never treated downstream as
            # the one authoritative type for every target.
            display_type = "+".join(sorted(set(target_doc_types.values())))
            return Classification(
                disposition=str(raw["disposition"]),
                target_doc_type=display_type,
                target_paths=targets,
                rule_id=f"override:{path}",
                requires_manual_section_map=bool(raw.get("requires_manual_section_map", False)),
                deletion_reason=raw.get("deletion_reason"),
                normative_decision=raw.get("normative_decision"),
                target_doc_types=target_doc_types,
            )

        if "target_doc_type" not in raw:
            raise CutoverError(
                f"path_overrides[{path!r}] must declare either target_records or target_doc_type"
            )
        targets = normalize_targets(raw.get("target_paths", []))
        single_type = str(raw["target_doc_type"])
        return Classification(
            disposition=str(raw["disposition"]),
            target_doc_type=single_type,
            target_paths=targets,
            rule_id=f"override:{path}",
            requires_manual_section_map=bool(raw.get("requires_manual_section_map", False)),
            deletion_reason=raw.get("deletion_reason"),
            normative_decision=raw.get("normative_decision"),
            target_doc_types={target: single_type for target in targets},
        )

    if path in set(rules.get("compatibility_stub_paths", [])):
        return Classification(
            disposition="deleted_git_history_only",
            target_doc_type="evidence",
            target_paths=[],
            rule_id="compatibility-stub",
            deletion_reason="compatibility stub removed by hard cutover",
            target_doc_types={},
        )

    known_normative = path in set(rules.get("known_normative_sources", []))
    for raw in rules.get("family_rules", []):
        pattern = raw.get("path_regex")
        if not isinstance(pattern, str) or re.search(pattern, path) is None:
            continue

        if raw.get("target_same_path"):
            targets = [path]
        elif isinstance(raw.get("target_template"), str):
            targets = [render_template(raw["target_template"], path)]
        else:
            targets = [str(value) for value in raw.get("target_paths", [])]

        targets.extend(architecture_keyword_target(path, body, raw))
        if isinstance(raw.get("evidence_template"), str):
            targets.append(render_template(raw["evidence_template"], path))
        targets = normalize_targets(targets)

        if raw.get("target_doc_type_from_metadata"):
            target_type = str(metadata.get("relaylm_doc_type") or "guide")
        elif isinstance(raw.get("target_doc_type"), str):
            target_type = raw["target_doc_type"]
        elif targets:
            target_type = inferred_target_type(targets[0], metadata)
        else:
            target_type = str(metadata.get("relaylm_doc_type") or "evidence")

        normative_decision = raw.get("normative_decision")
        if known_normative and normative_decision is None:
            normative_decision = "rebuild_verbatim"

        return Classification(
            disposition=str(raw["disposition"]),
            target_doc_type=target_type,
            target_paths=targets,
            rule_id=str(raw["id"]),
            requires_manual_section_map=bool(raw.get("requires_manual_section_map", False)),
            deletion_reason=raw.get("deletion_reason"),
            normative_decision=normative_decision,
            target_doc_types={target: target_type for target in targets},
        )

    # This should be unreachable because docs-generic is the final configured rule.
    return Classification(
        disposition="",
        target_doc_type="",
        target_paths=[],
        rule_id="unclassified",
        target_doc_types={},
    )


def normative_signal(text: str, metadata: dict[str, Any], rules: dict[str, Any]) -> bool:
    doc_type = str(metadata.get("relaylm_doc_type") or "")
    if doc_type in {"contract", "implementation_contract"}:
        return True
    for pattern in rules.get("normative_line_patterns", []):
        if re.search(str(pattern), text):
            return True
    headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)
    keywords = [str(value).lower() for value in rules.get("normative_heading_keywords", [])]
    return any(keyword in heading.lower() for heading in headings for keyword in keywords)


def baseline_commit_time(commit: str) -> str:
    return run_git("show", "-s", "--format=%cI", commit).stdout.strip()


def path_dependencies(commit: str, path_regex: str, known_docs: set[str]) -> dict[str, list[dict[str, Any]]]:
    result = run_git(
        "grep",
        "-n",
        "-I",
        "-E",
        SIMPLE_PATH_GREP_RE,
        commit,
        "--",
        ".",
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise CutoverError(f"git grep failed: {result.stderr.strip()}")

    matcher = re.compile(path_regex)
    output: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    prefix = f"{commit}:"
    for raw_line in result.stdout.splitlines():
        line = raw_line[len(prefix) :] if raw_line.startswith(prefix) else raw_line
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        referrer, line_number, source_line = parts
        try:
            number = int(line_number)
        except ValueError:
            continue
        for match in matcher.finditer(source_line):
            target = match.group(1)
            if target not in known_docs:
                continue
            if referrer.startswith(".github/workflows/"):
                kind = "workflow"
            elif referrer.startswith("scripts/"):
                kind = "script"
            elif referrer.startswith("docs/"):
                kind = "documentation"
            elif referrer in {"README.md", "README_ja.md"}:
                kind = "root_router"
            else:
                kind = "repository"
            output[target].append(
                {
                    "referrer": referrer,
                    "line": number,
                    "kind": kind,
                    "text_sha256": hashlib.sha256(source_line.strip().encode("utf-8")).hexdigest(),
                }
            )
    return {key: sorted(value, key=lambda item: (item["kind"], item["referrer"], item["line"])) for key, value in sorted(output.items())}


def validate_records(
    records: list[dict[str, Any]],
    rules: dict[str, Any],
    dependencies: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    supported = set(rules.get("supported_dispositions", []))
    graph_nodes = set(rules.get("canonical_graph_nodes", []))
    known_normative = set(rules.get("known_normative_sources", []))
    records_by_path = {record["old_path"]: record for record in records}

    for record in records:
        path = record["old_path"]
        disposition = record["disposition"]
        targets = record["target_paths"]
        if not disposition or record["classification_rule"] == "unclassified":
            errors.append(f"{path}: unclassified")
            continue
        if disposition not in supported:
            errors.append(f"{path}: unsupported disposition {disposition!r}")
        if disposition == "deleted_git_history_only" and not record.get("deletion_reason"):
            errors.append(f"{path}: deletion lacks Git-history-only reason")
        if disposition != "deleted_git_history_only" and not targets:
            errors.append(f"{path}: disposition {disposition} has no target path")
        if len(targets) > 1 and disposition not in {"split", "synthesized"}:
            errors.append(f"{path}: multiple targets require split or synthesized disposition")
        distinct_target_types = set((record.get("target_doc_types") or {}).values())
        if len(distinct_target_types) > 1 and disposition != "split":
            errors.append(
                f"{path}: targets with different document types ({sorted(distinct_target_types)!r}) require split disposition"
            )
        for target in targets:
            if not target.startswith("docs/"):
                errors.append(f"{path}: target escapes docs tree: {target}")
            if target.startswith("docs/architecture/"):
                if target == path and disposition == "retained":
                    continue
                if target == "docs/architecture/README.md":
                    continue
                if target not in graph_nodes:
                    errors.append(f"{path}: target is outside approved architecture graph: {target}")
        if path in known_normative and not record.get("normative_decision"):
            errors.append(f"{path}: known normative source lacks migration decision")
        if record["contains_normative_signals"] and disposition in {"moved", "synthesized", "absorbed"}:
            warnings.append(f"{path}: normative signals require Preparation C block review")
        if record["requires_manual_section_map"]:
            warnings.append(f"{path}: manual section map required before deletion")
        live_dependencies = [
            item for item in dependencies.get(path, []) if item["kind"] in {"workflow", "script", "root_router"}
        ]
        if disposition != "retained" and live_dependencies:
            warnings.append(f"{path}: {len(live_dependencies)} path-bound workflow/script/router references")

    for path in sorted(known_normative):
        if path not in records_by_path:
            errors.append(f"known normative source missing from baseline: {path}")

    exact_targets: dict[str, list[str]] = collections.defaultdict(list)
    for record in records:
        if record["disposition"] in {"retained", "moved", "rebuilt_verbatim"}:
            for target in record["target_paths"]:
                exact_targets[target].append(record["old_path"])
    for target, sources in sorted(exact_targets.items()):
        if len(sources) > 1:
            errors.append(f"duplicate exclusive target {target}: {sources!r}")

    return errors, sorted(dict.fromkeys(warnings))


def markdown_summary(
    baseline: str,
    baseline_time: str,
    records: list[dict[str, Any]],
    dependencies: dict[str, list[dict[str, Any]]],
    errors: list[str],
    warnings: list[str],
) -> str:
    dispositions = collections.Counter(record["disposition"] for record in records)
    doc_types = collections.Counter(str(record.get("current_doc_type") or "missing") for record in records)
    statuses = collections.Counter(str(record.get("current_status") or "missing") for record in records)
    missing_front_matter = sum(not record["has_front_matter"] for record in records)
    normative = sum(record["contains_normative_signals"] for record in records)
    manual = sum(record["requires_manual_section_map"] for record in records)
    path_bound = sum(
        1
        for record in records
        if any(item["kind"] in {"workflow", "script", "root_router"} for item in dependencies.get(record["old_path"], []))
    )

    lines = [
        "# Documentation Cutover Dry-Run Summary",
        "",
        f"- Baseline commit: `{baseline}`",
        f"- Baseline committed at: `{baseline_time}`",
        f"- Markdown records: **{len(records)}**",
        f"- Missing front matter: **{missing_front_matter}**",
        f"- Normative-signal candidates: **{normative}**",
        f"- Manual section maps required: **{manual}**",
        f"- Documents with workflow/script/root-router path dependencies: **{path_bound}**",
        f"- Strict errors: **{len(errors)}**",
        f"- Warnings: **{len(warnings)}**",
        "",
        "## Dispositions",
        "",
        "| Disposition | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| `{name}` | {count} |" for name, count in sorted(dispositions.items()))
    lines.extend(["", "## Current document types", "", "| Type | Count |", "|---|---:|"])
    lines.extend(f"| `{name}` | {count} |" for name, count in sorted(doc_types.items()))
    lines.extend(["", "## Current statuses", "", "| Status | Count |", "|---|---:|"])
    lines.extend(f"| `{name}` | {count} |" for name, count in sorted(statuses.items()))
    lines.extend(["", "## Strict errors", ""])
    lines.extend([f"- {error}" for error in errors] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This artifact is planning evidence only. A target path in the inventory does not mean that the file exists or that its behavior is current. No source may be deleted until its durable content, normative blocks, evidence disposition, path dependencies, and incoming links are accounted for in the same cutover PR.",
            "",
        ]
    )
    return "\n".join(lines)


def dependency_markdown(dependencies: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "# Documentation Path Dependency Inventory",
        "",
        "This file lists literal references to baseline documentation paths. Workflow, script, and root-router references must be updated atomically with each path move or deletion.",
        "",
        "| Documentation path | Workflow | Script | Root router | Other docs | Repository |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for path, refs in dependencies.items():
        counts = collections.Counter(item["kind"] for item in refs)
        lines.append(
            f"| `{path}` | {counts['workflow']} | {counts['script']} | {counts['root_router']} | "
            f"{counts['documentation']} | {counts['repository']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test() -> None:
    assert stable_stem("docs/architecture/phase_i5_pin_unpin_contract.md") == "pin-unpin-contract"
    values = template_values("docs/mvp/wave9/example_completion_report.md")
    assert values["relative_after_mvp"] == "wave9/example_completion_report.md"
    metadata, body, present = parse_front_matter("---\nrelaylm_doc_type: contract\n---\n# X\n")
    assert present and metadata["relaylm_doc_type"] == "contract" and body.startswith("# X")
    assert source_pr_number("docs: example (#551)") == 551

    split_rules = {
        "path_overrides": {
            "docs/example/mixed.md": {
                "disposition": "split",
                "target_records": [
                    {"target_path": "docs/example/method.md", "target_doc_type": "evaluation_method"},
                    {"target_path": "docs/templates/example/report.md", "target_doc_type": "template"},
                ],
            }
        },
        "family_rules": [
            {
                "id": "docs-generic",
                "path_regex": "^docs/",
                "disposition": "moved",
                "target_doc_type": "guide",
                "target_same_path": True,
            }
        ],
    }
    split_classification = classify("docs/example/mixed.md", {}, "", split_rules)
    assert split_classification.target_doc_types == {
        "docs/example/method.md": "evaluation_method",
        "docs/templates/example/report.md": "template",
    }
    assert split_classification.target_doc_type == "evaluation_method+template"
    assert sorted(split_classification.target_paths) == ["docs/example/method.md", "docs/templates/example/report.md"]

    single_type_classification = classify("docs/other.md", {}, "", split_rules)
    assert single_type_classification.target_doc_types == {"docs/other.md": "guide"}

    def expect_cutover_error(path: str, override: dict[str, Any], expected_substring: str) -> None:
        rules = {
            "path_overrides": {path: override},
            "family_rules": [{"id": "docs-generic", "path_regex": "^docs/", "disposition": "moved", "target_doc_type": "guide"}],
        }
        try:
            classify(path, {}, "", rules)
        except CutoverError as exc:
            assert expected_substring in str(exc), f"expected {expected_substring!r} in {exc}"
        else:
            raise AssertionError(f"classify() did not raise CutoverError for {override!r}")

    # Empty target_records list.
    expect_cutover_error(
        "docs/bad/empty.md",
        {"disposition": "split", "target_records": []},
        "must be a non-empty list",
    )
    # Non-list target_records.
    expect_cutover_error(
        "docs/bad/nonlist.md",
        {"disposition": "split", "target_records": {"target_path": "docs/x.md", "target_doc_type": "guide"}},
        "must be a non-empty list",
    )
    # Duplicate target_path entries (same type).
    expect_cutover_error(
        "docs/bad/dup_same.md",
        {
            "disposition": "split",
            "target_records": [
                {"target_path": "docs/x.md", "target_doc_type": "guide"},
                {"target_path": "docs/x.md", "target_doc_type": "guide"},
            ],
        },
        "duplicate target_path",
    )
    # Duplicate target paths with conflicting document types.
    expect_cutover_error(
        "docs/bad/dup_conflict.md",
        {
            "disposition": "split",
            "target_records": [
                {"target_path": "docs/x.md", "target_doc_type": "guide"},
                {"target_path": "docs/x.md", "target_doc_type": "evidence"},
            ],
        },
        "conflicting document types",
    )
    # Entry mixing target_records with legacy target_paths.
    expect_cutover_error(
        "docs/bad/mixed_paths.md",
        {
            "disposition": "split",
            "target_records": [{"target_path": "docs/x.md", "target_doc_type": "guide"}],
            "target_paths": ["docs/x.md"],
        },
        "mixes target_records with legacy",
    )
    # Entry mixing target_records with legacy target_doc_type.
    expect_cutover_error(
        "docs/bad/mixed_type.md",
        {
            "disposition": "split",
            "target_records": [{"target_path": "docs/x.md", "target_doc_type": "guide"}],
            "target_doc_type": "guide",
        },
        "mixes target_records with legacy",
    )
    # A target path without a document type.
    expect_cutover_error(
        "docs/bad/no_type.md",
        {"disposition": "split", "target_records": [{"target_path": "docs/x.md"}]},
        "missing a non-empty target_doc_type",
    )
    # A document type without a target path.
    expect_cutover_error(
        "docs/bad/no_path.md",
        {"disposition": "split", "target_records": [{"target_doc_type": "guide"}]},
        "missing a non-empty target_path",
    )
    # An entry that is not a mapping at all.
    expect_cutover_error(
        "docs/bad/non_mapping_entry.md",
        {"disposition": "split", "target_records": ["docs/x.md"]},
        "non-mapping entry",
    )
    # Neither target_records nor target_doc_type declared.
    expect_cutover_error(
        "docs/bad/no_shape.md",
        {"disposition": "split"},
        "must declare either target_records or target_doc_type",
    )

    print("RelayLM documentation cutover preparation self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--baseline")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    try:
        rules = load_rules(args.rules)
        baseline = str(args.baseline or rules.get("baseline_commit") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", baseline):
            raise CutoverError("baseline commit must be a full 40-character lowercase SHA")
        validate_baseline(baseline)
        baseline_time = baseline_commit_time(baseline)
        blobs = list_blobs(baseline)
        known_docs = {blob.path for blob in blobs}
        dependency_map = path_dependencies(
            baseline,
            str(rules.get("path_reference_regex") or r"(docs/[A-Za-z0-9_./-]+\.md)"),
            known_docs,
        )

        message_cache: dict[str, str] = {}
        records: list[dict[str, Any]] = []
        for blob in blobs:
            text = read_blob(baseline, blob.path)
            metadata, body, has_front_matter = parse_front_matter(text)
            classification = classify(blob.path, metadata, body, rules)
            introduced_commit, introduced_on = first_introduction(baseline, blob.path)
            source_pr = source_pr_number(commit_message(introduced_commit, message_cache))
            targets = classification.target_paths
            record = {
                "old_path": blob.path,
                "old_blob_sha": blob.sha,
                "content_sha256": content_digest(text),
                "has_front_matter": has_front_matter,
                "current_doc_type": metadata.get("relaylm_doc_type"),
                "current_status": metadata.get("relaylm_status"),
                "current_authority": metadata.get("relaylm_authority"),
                "primary_authority": metadata.get("relaylm_authority") or (targets[0] if targets else None),
                "target_doc_type": classification.target_doc_type,
                "target_doc_types": dict(classification.target_doc_types),
                "target_paths": targets,
                "disposition": classification.disposition,
                "classification_rule": classification.rule_id,
                "contains_normative_signals": normative_signal(body, metadata, rules),
                "normative_decision": classification.normative_decision,
                "requires_manual_section_map": classification.requires_manual_section_map,
                "deletion_reason": classification.deletion_reason,
                "source_commit": introduced_commit,
                "source_pr": source_pr,
                "recorded_on": introduced_on,
                "path_dependency_count": len(dependency_map.get(blob.path, [])),
            }
            records.append(record)

        errors, warnings = validate_records(records, rules, dependency_map)
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        inventory = {
            "schema": "relaylm.documentation_cutover_inventory.v1",
            "baseline_commit": baseline,
            "baseline_committed_at": baseline_time,
            "record_count": len(records),
            "records": records,
            "strict_errors": errors,
            "warnings": warnings,
        }
        receipt_preview = {
            "schema": "relaylm.documentation_cutover_receipt_preview.v1",
            "baseline_commit": baseline,
            "records": [
                {
                    "old_path": record["old_path"],
                    "old_blob_sha": record["old_blob_sha"],
                    "disposition": record["disposition"],
                    "new_paths": record["target_paths"],
                    "source_commit": record["source_commit"],
                    "source_pr": record["source_pr"],
                    "verification": "pending_cutover",
                }
                for record in records
            ],
        }
        write_json(output_dir / "inventory.json", inventory)
        write_json(output_dir / "migration-receipt-preview.json", receipt_preview)
        write_json(output_dir / "path-dependencies.json", dependency_map)
        (output_dir / "summary.md").write_text(
            markdown_summary(baseline, baseline_time, records, dependency_map, errors, warnings),
            encoding="utf-8",
        )
        (output_dir / "path-dependencies.md").write_text(
            dependency_markdown(dependency_map), encoding="utf-8"
        )

        print(
            "RelayLM documentation cutover dry run generated "
            f"{len(records)} records, {len(errors)} error(s), and {len(warnings)} warning(s)"
        )
        if args.strict and errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        return 0
    except CutoverError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
