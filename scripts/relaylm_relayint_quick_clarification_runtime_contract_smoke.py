#!/usr/bin/env python3
"""Pin docs/contracts/relayint_quick_clarification_runtime_contract.md against code.

Recomputes the RelayINT fast-path/preflight/apply-plan candidate-action enum,
scene-gate vocabulary, the 18-name request-compatibility-gate vocabulary, and
the 29-name complete apply-plan block-reason vocabulary directly from
relaylm/relayint.py (AST + regex + actual builder calls), rather than
trusting the contract's own prose or a bare reason count.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CONTRACT_PATH = REPO_ROOT / "docs/contracts/relayint_quick_clarification_runtime_contract.md"
RELAYINT_PATH = REPO_ROOT / "relaylm/relayint.py"
MANAGED_RUNTIME_PATH = REPO_ROOT / "relaylm/managed_chat_runtime.py"
RELAYRUN_PATH = REPO_ROOT / "relaylm/relayrun.py"

import relaylm.relayint as relayint


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _source() -> str:
    return RELAYINT_PATH.read_text(encoding="utf-8")


def _function_slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    require(start >= 0, f"missing function marker: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    require(end >= 0, f"missing function end marker: {end_marker}")
    return text[start:end]


def _literal_values(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        target = node.targets[0] if isinstance(node, ast.Assign) else getattr(node, "target", None)
        if getattr(target, "id", None) == name:
            subscript = node.value
            require(isinstance(subscript, ast.Subscript), f"{name} is not a Literal[...] subscript")
            elt = subscript.slice
            values = elt.elts if isinstance(elt, ast.Tuple) else [elt]
            return {value.value for value in values}
    raise AssertionError(f"{name} definition not found")


def _quoted_strings(text: str) -> set[str]:
    return set(re.findall(r'"([a-z0-9_]+)"', text))


# --- Fixture helpers -------------------------------------------------------


def _base_payload() -> dict[str, object]:
    return {"model": "relaylm-default", "messages": [{"role": "user", "content": "hi"}], "stream": False}


def _open_scene_policy_artifact() -> dict[str, object]:
    return {
        "scene_state": {"scene_type": "design_talk", "recovery_mode": False},
        "scene_policy": {"user_confirmation_required": False},
    }


def _applicable_preflight() -> dict[str, object]:
    fast_path = relayint.build_relayint_fast_path_dry_run(
        messages=[{"role": "user", "content": "それってどういうこと？"}],
        ctx_hints={},
        enabled=True,
    )
    preflight = relayint.build_relayint_quick_clarification_preflight(
        relayint_fast_path_dry_run=fast_path,
        relayscn_scene_policy_artifact=_open_scene_policy_artifact(),
        enabled=True,
        dry_run_only=True,
    )
    require(preflight is not None, "fixture preflight unexpectedly None")
    return preflight


# --- Stage 1: candidate-action enum ----------------------------------------


def _assert_candidate_action_enum() -> None:
    expected = {
        "continue_without_clarification",
        "ask_clarification",
        "current_context_only",
        "recall_then_answer_candidate",
    }
    actual = _literal_values(_source(), "CandidateAction")
    require(actual == expected, f"CandidateAction drift: {sorted(actual)}")

    prior_memory_artifact = relayint.build_relayint_fast_path_dry_run(
        messages=[{"role": "user", "content": "前に話したMEMのやつを思い出して"}],
        ctx_hints={},
        enabled=True,
    )
    require(
        prior_memory_artifact["candidate_action"] == "recall_then_answer_candidate",
        prior_memory_artifact,
    )

    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    for action in expected:
        require(action in contract, f"contract omits candidate action: {action}")
    print(f"ok Stage 1 candidate-action enum matches exactly ({len(expected)} names, one reachable by real call)")


# --- Stage enablement / None conditions -------------------------------------


def _assert_stage_enablement_none_conditions() -> None:
    messages = [{"role": "user", "content": "hi"}]

    require(
        relayint.build_relayint_fast_path_dry_run(messages=messages, ctx_hints={}, enabled=False) is None,
        "Stage 1 must return None when disabled",
    )
    require(
        relayint.build_relayint_fast_path_dry_run(messages=messages, ctx_hints={}, enabled=True) is not None,
        "Stage 1 must return an artifact when enabled",
    )

    fast_path = relayint.build_relayint_fast_path_dry_run(messages=messages, ctx_hints={}, enabled=True)

    require(
        relayint.build_relayint_quick_clarification_preflight(
            relayint_fast_path_dry_run=fast_path, enabled=False
        )
        is None,
        "Stage 2 must return None when disabled",
    )
    require(
        relayint.build_relayint_quick_clarification_preflight(
            relayint_fast_path_dry_run=fast_path, enabled=True
        )
        is not None,
        "Stage 2 must return an artifact when enabled with a present Stage 1 artifact",
    )

    require(
        relayint.build_relayint_quick_clarification_apply_plan(
            relayint_quick_clarification_preflight=_applicable_preflight(), enabled=False
        )
        is None,
        "Stage 3 must return None when disabled",
    )
    require(
        relayint.build_relayint_quick_clarification_apply_plan(
            relayint_quick_clarification_preflight=_applicable_preflight(), enabled=True
        )
        is not None,
        "Stage 3 must return an artifact when enabled",
    )
    print("ok Stage 1/2/3 enablement None-return conditions match the contract")


def _assert_stage2_returns_none_on_missing_upstream() -> None:
    require(
        relayint.build_relayint_quick_clarification_preflight(
            relayint_fast_path_dry_run=None, enabled=True
        )
        is None,
        "Stage 2 must return None (not a blocked artifact) when the Stage 1 artifact is missing",
    )
    require(
        relayint.build_relayint_quick_clarification_preflight(
            relayint_fast_path_dry_run="not-a-mapping", enabled=True
        )
        is None,
        "Stage 2 must return None when the Stage 1 artifact is not a Mapping at all"
        " and, more importantly, must not synthesize a missing-input blocked artifact",
    )
    require(
        relayint.build_relayint_quick_clarification_preflight(
            relayint_fast_path_dry_run={"unrelated": "mapping"}, enabled=True
        )
        is not None,
        "Stage 2 only checks isinstance(..., Mapping) for presence, not artifact validity -- "
        "a mapping lacking candidate_action still produces a (non-applicable) artifact, not None",
    )
    print("ok Stage 2 returns None (no artifact at all) only when the Stage 1 artifact is missing/not a Mapping")


def _assert_stage3_records_preflight_missing_without_upstream() -> None:
    plan = relayint.build_relayint_quick_clarification_apply_plan(
        relayint_quick_clarification_preflight=None, enabled=True
    )
    require(plan is not None, "Stage 3 must still produce an artifact when the Stage 2 artifact is missing")
    require("preflight_missing" in plan["apply_block_reasons"], plan["apply_block_reasons"])
    require("phase4_plan_only" in plan["apply_block_reasons"], plan["apply_block_reasons"])
    require(plan["apply_allowed"] is False, plan)
    print(
        "ok Stage 3 produces an artifact with 'preflight_missing' (unlike Stage 2's bare None) "
        "when enabled without an upstream Stage 2 artifact"
    )


# --- Scene-gate vocabulary ---------------------------------------------------


def _assert_scene_gate_vocabulary() -> None:
    expected = {"scene_type_is_recovery", "recovery_mode_enabled", "user_confirmation_required"}
    slice_ = _function_slice(
        _source(), "def _quick_clarification_scene_gate(", "def _modalities_constraint("
    )
    extracted = set(re.findall(r'block_reasons\.append\("([^"]+)"\)', slice_))
    require(extracted == expected, f"scene gate reason vocabulary drift: {sorted(extracted)}")

    recovery_gate = relayint._quick_clarification_scene_gate(
        {"scene_state": {"scene_type": "recovery"}, "scene_policy": {}}
    )
    require(recovery_gate["block_reasons"] == ["scene_type_is_recovery", "recovery_mode_enabled"], recovery_gate)

    confirmation_gate = relayint._quick_clarification_scene_gate(
        {"scene_state": {"scene_type": "design_talk"}, "scene_policy": {"user_confirmation_required": True}}
    )
    require(confirmation_gate["block_reasons"] == ["user_confirmation_required"], confirmation_gate)

    open_gate = relayint._quick_clarification_scene_gate(_open_scene_policy_artifact())
    require(open_gate == {
        "scene_type": "design_talk",
        "recovery_mode": False,
        "user_confirmation_required": False,
        "quick_clarification_allowed": True,
        "block_reasons": [],
    }, open_gate)

    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    for reason in expected:
        require(reason in contract, f"contract omits scene-gate reason: {reason}")
    print(f"ok scene-gate block-reason vocabulary matches exactly ({len(expected)} names, static + runtime)")


# --- Request compatibility gate: 18-name vocabulary -------------------------

_EXPECTED_COMPATIBILITY_GATE_REASONS = {
    "response_format_requested",
    "tools_requested",
    "tool_choice_requested",
    "functions_requested",
    "function_call_requested",
    "multiple_choices_requested",
    "unsupported_n_value",
    "logprobs_requested",
    "top_logprobs_requested",
    "stop_sequence_requested",
    "unsupported_token_limit",
    "token_limit_requested",
    "max_completion_tokens_too_small",
    "max_tokens_too_small",
    "unsupported_modalities_value",
    "audio_modality_requested",
    "non_text_modality_requested",
    "audio_options_requested",
}


def _assert_compatibility_gate_18_names_statically() -> None:
    source = _source()
    gate_slice = _function_slice(
        source, "def build_relayint_request_compatibility_gate(", "def _relayint_projection("
    )
    modalities_slice = _function_slice(source, "def _modalities_constraint(", "def _token_limit_constraint(")
    token_slice = _function_slice(source, "def _token_limit_constraint(", "def _quick_clarification_response_token_floor(")
    n_slice = _function_slice(source, "def _n_request_constraint(", "def _request_choice_present(")

    extracted: set[str] = set()
    extracted |= set(re.findall(r'"([a-z0-9_]+_requested)"', gate_slice))
    extracted |= set(re.findall(r'block_reasons\.append\("([^"]+)"\)', modalities_slice))
    extracted |= set(re.findall(r'"(unsupported_token_limit|token_limit_requested)"', token_slice))
    extracted |= set(re.findall(r'"([a-z0-9_]+)"', n_slice))
    # too_small_reason values are passed in by the two call sites, not literals inside
    # _token_limit_constraint itself -- pull them from the call sites in the gate slice.
    extracted |= set(re.findall(r'too_small_reason="([^"]+)"', gate_slice))

    require(
        extracted == _EXPECTED_COMPATIBILITY_GATE_REASONS,
        f"statically extracted compatibility-gate vocabulary drift: {sorted(extracted)}",
    )
    print(f"ok request-compatibility-gate vocabulary matches exactly by static extraction ({len(extracted)} names)")


def _assert_compatibility_gate_18_names_reachable_by_call() -> None:
    reached: set[str] = set()

    empty = relayint.build_relayint_request_compatibility_gate(None)
    require(empty["compatible"] is True and empty["block_reasons"] == [], empty)

    combo_one = relayint.build_relayint_request_compatibility_gate(
        {
            "response_format": {"type": "json_object"},
            "tools": [{"type": "function"}],
            "tool_choice": "auto",
            "functions": [{"name": "f"}],
            "function_call": "auto",
            "n": 2,
            "logprobs": True,
            "top_logprobs": 3,
            "stop": ["\n"],
            "max_completion_tokens": -1,
            "max_tokens": 1,
            "modalities": ["audio"],
            "audio": {"voice": "x"},
        }
    )
    reached |= set(combo_one["block_reasons"])
    require(combo_one["compatible"] is False, combo_one)

    combo_two = relayint.build_relayint_request_compatibility_gate(
        {"n": True, "modalities": [], "max_completion_tokens": 1}
    )
    reached |= set(combo_two["block_reasons"])

    combo_three = relayint.build_relayint_request_compatibility_gate({"modalities": ["video"]})
    reached |= set(combo_three["block_reasons"])

    require(
        reached == _EXPECTED_COMPATIBILITY_GATE_REASONS,
        f"not every statically-extracted reason is actually reachable by a real call: "
        f"missing={sorted(_EXPECTED_COMPATIBILITY_GATE_REASONS - reached)} extra={sorted(reached - _EXPECTED_COMPATIBILITY_GATE_REASONS)}",
    )
    require(
        "token_limit_requested" in combo_two["block_reasons"]
        and "max_completion_tokens_too_small" in combo_two["block_reasons"],
        "token_limit_requested must co-occur with max_completion_tokens_too_small for a too-small valid limit",
    )
    print(
        f"ok all {len(_EXPECTED_COMPATIBILITY_GATE_REASONS)} request-compatibility-gate reasons "
        "are reachable by actual builder calls"
    )


# --- Apply-plan: 29-name complete vocabulary --------------------------------

_EXPECTED_APPLY_PLAN_DIRECT_REASONS = {
    "preflight_missing",
    "preflight_not_applicable",
    "scene_gate_blocked",
    "dry_run_only",
    "streaming_not_supported",
    "response_template_missing",
    "response_max_chars_exceeded",
    "phase4_plan_only",
}


def _assert_apply_plan_29_name_union_statically() -> None:
    source = _source()
    apply_slice = _function_slice(
        source,
        "def build_relayint_quick_clarification_apply_plan(",
        "def build_relayint_request_compatibility_gate(",
    )
    direct = set(re.findall(r'block_reasons\.append\("([^"]+)"\)', apply_slice))
    require(
        direct == _EXPECTED_APPLY_PLAN_DIRECT_REASONS,
        f"apply-plan direct reason vocabulary drift: {sorted(direct)}",
    )

    scene_gate_reasons = {"scene_type_is_recovery", "recovery_mode_enabled", "user_confirmation_required"}
    full_union = direct | scene_gate_reasons | _EXPECTED_COMPATIBILITY_GATE_REASONS
    require(len(full_union) == 29, f"combined apply-plan vocabulary is not 29: {len(full_union)} -> {sorted(full_union)}")

    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    for reason in full_union:
        require(reason in contract, f"contract omits apply-plan reason: {reason}")
    require("13 " not in contract.split("29", 1)[0][-200:], "stale '13 reasons' phrasing may remain near the vocabulary section")
    print(f"ok complete apply-plan block-reason vocabulary is exactly 29 names ({len(full_union)} computed)")


def _assert_phase4_plan_only_unconditional_and_apply_allowed_always_false() -> None:
    permissive_compatibility_gate = relayint.build_relayint_request_compatibility_gate({})
    require(permissive_compatibility_gate["compatible"] is True, permissive_compatibility_gate)

    plan = relayint.build_relayint_quick_clarification_apply_plan(
        relayint_quick_clarification_preflight=_applicable_preflight(),
        enabled=True,
        dry_run_only=False,
        stream_enabled=False,
        response_max_chars=120,
        request_compatibility_gate=permissive_compatibility_gate,
    )
    require(plan is not None, plan)
    require(plan["apply_block_reasons"] == ["phase4_plan_only"], plan["apply_block_reasons"])
    require(plan["apply_allowed"] is False, plan)
    require(plan["response_short_circuit_allowed"] is False, plan)
    require(plan["short_circuit_applied"] is False, plan)
    print(
        "ok in the most permissive reachable scenario, apply_block_reasons is exactly "
        "['phase4_plan_only'] and apply_allowed is still False"
    )


def _assert_final_metadata_is_none_none_zero_despite_nonzero_candidate() -> None:
    candidate_kind = relayint._quick_clarification_response_kind("reference_confirmation")
    candidate_template_id = relayint._quick_clarification_response_template_id(candidate_kind)
    candidate_chars = relayint._quick_clarification_response_template_chars(candidate_template_id)
    require(candidate_kind != "none" and candidate_chars > 0, "fixture no longer produces a non-trivial candidate")

    preflight = _applicable_preflight()
    require(preflight["clarification_type"] != "none", preflight)

    plan = relayint.build_relayint_quick_clarification_apply_plan(
        relayint_quick_clarification_preflight=preflight,
        enabled=True,
        dry_run_only=False,
        request_compatibility_gate=relayint.build_relayint_request_compatibility_gate({}),
    )
    require(plan["generated_response_kind"] == "none", plan)
    require(plan["response_template_id"] == "none", plan)
    require(plan["response_chars"] == 0, plan)
    print(
        f"ok final artifact response metadata is always ('none', 'none', 0) even though the internal "
        f"candidate for this clarification_type was ({candidate_kind!r}, {candidate_template_id!r}, {candidate_chars})"
    )


# --- Safety / non-authority --------------------------------------------------


def _assert_no_side_effect_literals() -> None:
    fast_path = relayint.build_relayint_fast_path_dry_run(
        messages=[{"role": "user", "content": "それで進めよう"}], ctx_hints={}, enabled=True
    )
    require(fast_path["llm_called"] is False and fast_path["mem_lookup_executed"] is False, fast_path)
    require(
        fast_path["backend_payload_mutation_allowed"] is False
        and fast_path["response_mutation_allowed"] is False,
        fast_path,
    )

    preflight = _applicable_preflight()
    require(preflight["llm_called"] is False and preflight["mem_lookup_executed"] is False, preflight)
    require(preflight["user_visible_apply_allowed"] is False, preflight)

    plan = relayint.build_relayint_quick_clarification_apply_plan(
        relayint_quick_clarification_preflight=preflight, enabled=True
    )
    require(plan["llm_called"] is False and plan["mem_lookup_executed"] is False, plan)
    require(
        plan["backend_payload_mutation_allowed"] is False and plan["backend_payload_mutation_applied"] is False,
        plan,
    )
    require(plan["response_mutation_allowed"] is False and plan["user_visible_apply_allowed"] is False, plan)
    print("ok no stage's safety literals ever claim an LLM call, MEM lookup, or payload/response mutation")


def _assert_actual_apply_remains_unimplemented() -> None:
    for path in (MANAGED_RUNTIME_PATH, RELAYRUN_PATH):
        text = path.read_text(encoding="utf-8")
        require(
            "response_short_circuit_allowed" not in text,
            f"{path.name} now reads response_short_circuit_allowed -- actual apply may have shipped; "
            "update the contract's 'Actual user-visible apply' section if so",
        )
        require(
            "short_circuit_applied" not in text,
            f"{path.name} now reads short_circuit_applied -- actual apply may have shipped",
        )
    print("ok no runtime module reads the apply-plan short-circuit fields to change request handling")


def _assert_no_relayref_dependency_reintroduced() -> None:
    source = _source()
    require("import relayref" not in source and "relaylm.relayref" not in source, source)
    require("relayref_artifact" not in source, "relayint.py reintroduced a relayref_artifact dependency")
    print("ok relaylm/relayint.py has no import of or dependency on relaylm.relayref / relayref_artifact")


def main() -> None:
    _assert_candidate_action_enum()
    _assert_stage_enablement_none_conditions()
    _assert_stage2_returns_none_on_missing_upstream()
    _assert_stage3_records_preflight_missing_without_upstream()
    _assert_scene_gate_vocabulary()
    _assert_compatibility_gate_18_names_statically()
    _assert_compatibility_gate_18_names_reachable_by_call()
    _assert_apply_plan_29_name_union_statically()
    _assert_phase4_plan_only_unconditional_and_apply_allowed_always_false()
    _assert_final_metadata_is_none_none_zero_despite_nonzero_candidate()
    _assert_no_side_effect_literals()
    _assert_actual_apply_remains_unimplemented()
    _assert_no_relayref_dependency_reintroduced()
    print("RelayINT quick-clarification runtime contract smoke passed")


if __name__ == "__main__":
    main()
