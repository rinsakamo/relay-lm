#!/usr/bin/env python3
"""Pin the code-derived RelayCTX short-term runtime contract and pipeline order."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/contracts/relayctx_short_term_runtime_contract.md"
MANAGED_RUNTIME_PATH = ROOT / "relaylm/managed_chat_runtime.py"
MANAGED_PIPELINE_PATH = ROOT / "relaylm/managed_chat_pipeline_runtime.py"
DIAGNOSTICS_PATH = ROOT / "relaylm/diagnostics.py"
REPACK_PATH = ROOT / "relaylm/relayctx_repack.py"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _ordered_positions(text: str, markers: tuple[str, ...], *, label: str) -> None:
    positions: list[int] = []
    for marker in markers:
        position = text.find(marker)
        _require(position >= 0, f"{label}: missing marker: {marker}")
        positions.append(position)
    _require(positions == sorted(positions), f"{label}: markers are out of order")


def _unique_ordered_positions(text: str, markers: tuple[str, ...], *, label: str) -> None:
    for marker in markers:
        _require(text.count(marker) == 1, f"{label}: marker must occur exactly once: {marker}")
    _ordered_positions(text, markers, label=label)


def _named_function(tree: ast.Module, name: str, *, label: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    _require(len(matches) == 1, f"{label}: expected exactly one function {name}")
    return matches[0]


def _function_slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    _require(start >= 0, f"missing function marker: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    _require(end >= 0, f"missing function end marker: {end_marker}")
    return text[start:end]


def main() -> int:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    managed_runtime = MANAGED_RUNTIME_PATH.read_text(encoding="utf-8")
    managed_pipeline = MANAGED_PIPELINE_PATH.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    repack = REPACK_PATH.read_text(encoding="utf-8")

    facade_tree = ast.parse(managed_runtime, filename=str(MANAGED_RUNTIME_PATH))
    pipeline_tree = ast.parse(managed_pipeline, filename=str(MANAGED_PIPELINE_PATH))
    facade_imports = [
        alias
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "relaylm.managed_chat_pipeline_runtime"
        for alias in node.names
        if alias.name == "run_managed_chat_pipeline"
    ]
    _require(
        len(facade_imports) == 1,
        "managed facade must import run_managed_chat_pipeline exactly once from its owner",
    )
    facade_handler = _named_function(
        facade_tree, "handle_managed_chat_completion", label="managed facade"
    )
    facade_calls = [
        node
        for node in ast.walk(facade_handler)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_managed_chat_pipeline"
    ]
    _require(
        len(facade_calls) == 1,
        "managed facade must delegate exactly once to run_managed_chat_pipeline",
    )
    _named_function(pipeline_tree, "run_managed_chat_pipeline", label="managed pipeline owner")
    backward_imports = [
        node
        for node in ast.walk(pipeline_tree)
        if isinstance(node, ast.ImportFrom) and node.module == "relaylm.managed_chat_runtime"
    ] + [
        alias
        for node in ast.walk(pipeline_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "relaylm.managed_chat_runtime"
    ]
    _require(not backward_imports, "managed pipeline owner must not import its facade")

    runtime_section = contract.split("## Current runtime position and stage ordering", 1)[1].split(
        "## Enablement and artifact presence", 1
    )[0]
    _ordered_positions(
        runtime_section,
        (
            "RelayMEM retrieval",
            "RelayMEM runtime CTX / snippet injection",
            "RelayCTX extraction dry-run",
            "RelayCTX block assembly dry-run",
            "RelayCTX injection preflight",
            "RelayCTX injection apply gate",
            "token_budget_truncation",
        ),
        label="contract runtime order",
    )
    _require(
        "preflight\n  -> [ RelayMEM runtime CTX / snippet injection stage runs here ]" not in contract,
        "contract retains the retired incorrect preflight-before-RelayMEM diagram",
    )

    executable_markers = (
        '"relaymem_runtime_ctx",',
        "extraction = build_relayctx_short_term_extraction_dry_run(",
        "assembly = build_relayctx_short_term_block_assembly_dry_run(",
        "preflight = build_relayctx_short_term_runtime_injection_preflight(",
        '"relayctx_short_term_injection",',
        '"token_budget_truncation",',
    )
    _require(
        not any(marker in managed_runtime for marker in executable_markers),
        "managed facade ambiguously duplicates executable stage-order markers",
    )
    _unique_ordered_positions(
        managed_pipeline,
        (
            '"relaymem_runtime_ctx",',
            "extraction = build_relayctx_short_term_extraction_dry_run(",
            "assembly = build_relayctx_short_term_block_assembly_dry_run(",
            "preflight = build_relayctx_short_term_runtime_injection_preflight(",
            '"relayctx_short_term_injection",',
            '"token_budget_truncation",',
        ),
        label="managed pipeline executable order",
    )

    for expected in (
        "each diagnostics builder returns `None` while its enable flag is `False`",
        "Stage 4 consumes both the Stage 3 preflight artifact and `PipelineContext.forwarded_payload`",
        "already includes any RelayMEM runtime CTX/snippet mutation",
        "the `not apply_enabled` branch is unreachable",
        "13 distinct strings across their union",
    ):
        _require(expected in contract, f"contract missing precision statement: {expected}")

    apply_slice = _function_slice(
        repack,
        "def _maybe_apply_relayctx_short_term_runtime_injection(",
        "def _relayctx_before_latest_user_index(",
    )
    early_return = apply_slice.find("if not apply_enabled:\n        return forwarded_payload, None")
    blocked_setup = apply_slice.find("preflight_present = isinstance(preflight_artifact, Mapping)")
    _require(early_return >= 0, "apply gate no longer has the documented disabled early return")
    _require(
        early_return < blocked_setup,
        "disabled apply no longer returns before blocked-reason evaluation",
    )

    apply_reasons = set(re.findall(r'blocked_reasons\.append\("([^"]+)"\)', apply_slice))
    if 'blocked_reasons=["messages_contain_non_object_items"]' in apply_slice:
        apply_reasons.add("messages_contain_non_object_items")
    expected_apply_reasons = {
        "dry_run_only",
        "preflight_missing",
        "injection_plan_missing",
        "assembled_block_missing",
        "no_short_term_candidates",
        "preflight_not_content_free",
        "messages_not_list",
        "latest_user_message_not_found",
        "inserted_content_empty",
        "token_budget_exceeded",
        "payload_mutation_disabled",
        "messages_contain_non_object_items",
    }
    _require(
        apply_reasons == expected_apply_reasons,
        f"apply blocked-reason taxonomy drift: {sorted(apply_reasons)}",
    )

    preflight_slice = _function_slice(
        diagnostics,
        "def build_relayctx_short_term_runtime_injection_preflight(",
        "def _positive_int(",
    )
    preflight_reasons = set(
        re.findall(r'blocked_reasons\.append\("([^"]+)"\)', preflight_slice)
    )
    expected_preflight_reasons = {
        "dry_run_only",
        "assembly_missing",
        "assembled_block_missing",
        "no_short_term_candidates",
        "payload_mutation_disabled",
    }
    _require(
        preflight_reasons == expected_preflight_reasons,
        f"preflight blocked-reason taxonomy drift: {sorted(preflight_reasons)}",
    )

    distinct_reasons = apply_reasons | preflight_reasons
    _require(len(distinct_reasons) == 13, "combined blocked-reason taxonomy is no longer 13")
    for reason in sorted(distinct_reasons):
        _require(reason in contract, f"contract omits blocked reason: {reason}")

    print("RelayCTX short-term runtime contract smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
