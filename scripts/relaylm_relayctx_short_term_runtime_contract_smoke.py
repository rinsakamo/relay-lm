#!/usr/bin/env python3
"""Pin the code-derived RelayCTX short-term runtime contract and pipeline order."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/contracts/relayctx_short_term_runtime_contract.md"
MANAGED_RUNTIME_PATH = ROOT / "relaylm/managed_chat_runtime.py"
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


def _function_slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    _require(start >= 0, f"missing function marker: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    _require(end >= 0, f"missing function end marker: {end_marker}")
    return text[start:end]


def main() -> int:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    managed_runtime = MANAGED_RUNTIME_PATH.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS_PATH.read_text(encoding="utf-8")
    repack = REPACK_PATH.read_text(encoding="utf-8")

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

    _ordered_positions(
        managed_runtime,
        (
            '"relaymem_runtime_ctx",',
            "relayctx_short_term_extraction_dry_run = (",
            "relayctx_short_term_block_assembly_dry_run = (",
            "relayctx_short_term_runtime_injection_preflight = (",
            '"relayctx_short_term_injection",',
            '"token_budget_truncation",',
        ),
        label="managed runtime order",
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
