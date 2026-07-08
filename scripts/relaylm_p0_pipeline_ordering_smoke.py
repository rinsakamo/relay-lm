#!/usr/bin/env python3
"""Smoke coverage for P0 RelayREL / RelaySCN / RelayEMO ordering."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from relaylm.pipeline_ordering import build_p0_pipeline_order_projection
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relayrel import build_relayrel_relationship_projection
from relaylm.relayscn import build_relayscn_scene_policy_artifact


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


_APP_CALL_TO_ORDER_NODE: dict[str, str] = {
    "build_relayrel_relationship_projection": "relayrel_relationship_projection",
    "build_relayscn_scene_policy_artifact": "relayscn_scene_policy",
    "run_relayemo": "relayemo_input",
}


def _app_request_path_call_lines(app_source: str) -> dict[str, list[int]]:
    tree = ast.parse(app_source)
    call_lines: dict[str, list[int]] = {name: [] for name in _APP_CALL_TO_ORDER_NODE}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        func_name = node.func.id
        if func_name not in call_lines:
            continue
        call_lines[func_name].append(node.lineno)

    for func_name, lines in call_lines.items():
        _assert(lines, f"app.py must call {func_name}")
    return call_lines


def _app_request_path_relayscn_has_relayemo_kwarg(app_source: str) -> bool:
    tree = ast.parse(app_source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_relayscn_scene_policy_artifact"
            and any(keyword.arg == "relayemo_artifact" for keyword in node.keywords)
        ):
            return True
    return False


def _app_request_path_measured_order(app_source: str) -> list[str]:
    """Return the actual RelayREL/RelaySCN/RelayEMO call order measured from app.py.

    This reads real AST call line numbers from the current app.py source instead
    of declaring the order as a constant, so callers can prove precedence rather
    than assert it.
    """

    call_lines = _app_request_path_call_lines(app_source)
    ordered_func_names = sorted(call_lines, key=lambda name: min(call_lines[name]))
    return [_APP_CALL_TO_ORDER_NODE[name] for name in ordered_func_names]


def _app_request_path_order_is_rewired(app_source: str) -> bool:
    call_lines = _app_request_path_call_lines(app_source)
    if _app_request_path_relayscn_has_relayemo_kwarg(app_source):
        return False

    relayrel_line = min(call_lines["build_relayrel_relationship_projection"])
    relayscn_line = min(call_lines["build_relayscn_scene_policy_artifact"])
    relayemo_line = min(call_lines["run_relayemo"])
    return relayrel_line < relayscn_line < relayemo_line


def _assert_policy_closed_for_non_authoritative_heuristic(artifact: dict[str, object], label: str) -> None:
    scene_state = artifact["scene_state"]
    scene_policy = artifact["scene_policy"]
    _assert(scene_state["is_estimate"] is True, f"{label} should remain a heuristic estimate")
    _assert(
        scene_policy["policy_authority"] == "heuristic_non_authoritative",
        f"{label} should not receive authoritative policy",
    )
    _assert(
        scene_policy["relaymem_retrieval_scope"] == "current_context_only",
        f"{label} should not open broad RelayMEM retrieval",
    )
    _assert(
        scene_policy["relaymem_update_gate"] == "blocked",
        f"{label} should not open RelayMEM updates",
    )


def _assert_safety_policy_restrictive(artifact: dict[str, object], label: str) -> None:
    scene_state = artifact["scene_state"]
    scene_policy = artifact["scene_policy"]
    _assert(scene_state["is_estimate"] is True, f"{label} should remain a heuristic estimate")
    _assert(
        scene_policy["policy_authority"] == "heuristic_restrictive",
        f"{label} should only receive restrictive heuristic policy",
    )
    _assert(
        scene_policy["relayctx_mode"] == "safety_cautious",
        f"{label} should use safety-cautious RelayCTX mode",
    )
    _assert(
        scene_policy["relaymem_retrieval_scope"] == "minimal_or_evidence_only",
        f"{label} should restrict RelayMEM retrieval to minimal/evidence scope",
    )
    _assert(
        scene_policy["relaymem_update_gate"] == "blocked",
        f"{label} should block RelayMEM updates",
    )


def main() -> None:
    signature = inspect.signature(build_relayscn_scene_policy_artifact)
    _assert("relayemo_artifact" not in signature.parameters, "RelaySCN public API must not expose relayemo_artifact")

    source = Path("relaylm/relayscn.py").read_text(encoding="utf-8")
    _assert("_extract_relayemo_scene_state" not in source, "RelayEMO scene-state extractor must be removed")
    _assert('source = "relayemo_artifact"' not in source, "RelaySCN must not emit relayemo_artifact scene source")

    app_source = Path("relaylm/managed_chat_runtime.py").read_text(encoding="utf-8")
    actual_app_rewired = _app_request_path_order_is_rewired(app_source)
    measured_node_order = _app_request_path_measured_order(app_source)

    explicit_artifact = build_relayscn_scene_policy_artifact(
        payload={
            "metadata": {
                "relayscn": {
                    "scene_state": {
                        "schema_version": "secret schema version",
                        "scene_type": "review_work",
                        "confidence": 0.91,
                        "stability": 0.86,
                        "signals": [
                            "private signal body",
                            "keyword:secret implementation note",
                            "heuristic_fallback:secret fallback note",
                        ],
                    }
                }
            },
            "messages": [{"role": "user", "content": "casual fallback text"}],
        }
    )
    _assert(explicit_artifact["scene_state_source"] == "request_metadata", "explicit metadata should win")
    _assert(explicit_artifact["scene_state"]["scene_type"] == "review_work", "explicit scene type should be preserved")
    _assert(explicit_artifact["scene_state"]["source_authoritative"] is True, "explicit metadata should be authoritative")
    _assert(explicit_artifact["scene_policy"]["policy_authority"] == "authoritative", "explicit metadata may open authoritative policy")
    _assert(explicit_artifact["scene_policy"]["relaymem_retrieval_scope"] == "current_project_only", "explicit review may use review retrieval scope")
    _assert(explicit_artifact["scene_policy"]["relaymem_update_gate"] == "allowed_dry_run", "explicit review may use dry-run update gate")
    explicit_artifact_json = json.dumps(explicit_artifact)
    for forbidden_signal_text in (
        "private signal body",
        "secret implementation note",
        "secret fallback note",
        "secret schema version",
    ):
        _assert(
            forbidden_signal_text not in explicit_artifact_json,
            f"explicit signals must be content-free: {forbidden_signal_text!r}",
        )
    _assert(
        explicit_artifact["scene_state"]["signals"] == ["redacted_signal"],
        "external request metadata signals should be redacted to a fixed token",
    )
    _assert(
        explicit_artifact["scene_state"]["schema_version"] == "relayscn.scene_state.v0",
        "external request metadata schema_version should be normalized",
    )

    heuristic_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]}
    )
    _assert(heuristic_artifact["scene_state_source"] == "heuristic", "missing metadata should use heuristic")
    _assert(heuristic_artifact["scene_state"]["scene_type"] == "review_work", "heuristic should classify review text")
    _assert_policy_closed_for_non_authoritative_heuristic(heuristic_artifact, "heuristic review text")

    for code_task_text in (
        "please fix this bug",
        "fix this error",
        "implement this",
        "コードを修正して",
        "修正して",
        "実装して",
        "バグを直して",
    ):
        code_task_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": code_task_text}]}
        )
        _assert(
            code_task_artifact["scene_state"]["scene_type"] == "implementation_work",
            f"code-task text should classify as implementation_work: {code_task_text!r}",
        )
        _assert_policy_closed_for_non_authoritative_heuristic(code_task_artifact, code_task_text)

    relayemo_like_scene = {"scene_state": {"scene_type": "vtuber_roleplay", "confidence": 1.0}}
    try:
        build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]},
            **{"relayemo_artifact": relayemo_like_scene},
        )
    except TypeError as exc:
        _assert("relayemo_artifact" in str(exc), "RelaySCN should reject relayemo_artifact explicitly")
    else:
        raise AssertionError("RelaySCN must reject relayemo_artifact as an unexpected keyword")

    vtuber_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "配信してください"}]}
    )
    _assert(
        vtuber_artifact["scene_state"]["scene_type"] == "vtuber_roleplay",
        "Japanese streaming cue should classify as vtuber_roleplay",
    )
    _assert_policy_closed_for_non_authoritative_heuristic(vtuber_artifact, "配信してください")

    for pr_review_text in ("PR#123を確認して", "PRを確認して", "PR", "please check pr"):
        pr_review_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": pr_review_text}]}
        )
        _assert(
            pr_review_artifact["scene_state"]["scene_type"] == "review_work",
            f"PR confirmation cue should classify as review_work: {pr_review_text!r}",
        )
        _assert_policy_closed_for_non_authoritative_heuristic(pr_review_artifact, pr_review_text)

    for non_review_text in ("please check prices", "check profile"):
        non_review_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": non_review_text}]}
        )
        _assert(
            non_review_artifact["scene_state"]["scene_type"] != "review_work",
            f"non-PR text should not classify as review_work: {non_review_text!r}",
        )

    for safety_file_text in (
        "medical file",
        "legal file",
        "safety file",
        "医療ファイル",
        "安全ファイル",
        "medical PR",
        "legal PR",
        "医療 PR",
        "safety review",
    ):
        safety_file_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": safety_file_text}]}
        )
        _assert(
            safety_file_artifact["scene_state"]["scene_type"] == "medical_or_safety",
            f"medical/safety file text should classify as medical_or_safety: {safety_file_text!r}",
        )
        _assert_safety_policy_restrictive(safety_file_artifact, safety_file_text)

    for file_task_text in ("file", "edit file", "this file"):
        file_task_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": file_task_text}]}
        )
        _assert(
            file_task_artifact["scene_state"]["scene_type"] == "implementation_work",
            f"file task text should classify as implementation_work: {file_task_text!r}",
        )
        _assert_policy_closed_for_non_authoritative_heuristic(file_task_artifact, file_task_text)

    for non_file_task_text in ("profile", "update my profile"):
        non_file_task_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": non_file_task_text}]}
        )
        _assert(
            non_file_task_artifact["scene_state"]["scene_type"] != "implementation_work",
            f"non-file text should not classify as implementation_work: {non_file_task_text!r}",
        )

    formal_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "文書を作成して"}]}
    )
    _assert(
        formal_artifact["scene_state"]["scene_type"] == "formal_document",
        "Japanese document task should classify as formal_document",
    )
    _assert(formal_artifact["scene_policy"]["policy_authority"] == "heuristic_restrictive", "formal heuristic should only restrict policy")
    _assert(formal_artifact["scene_policy"]["relaymem_update_gate"] == "blocked", "formal heuristic should block updates")

    for medical_task_text in ("医療について相談したい", "医療安全について確認したい"):
        medical_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": medical_task_text}]}
        )
        _assert(
            medical_artifact["scene_state"]["scene_type"] == "medical_or_safety",
            f"medical/safety text should classify as medical_or_safety: {medical_task_text!r}",
        )
        _assert_safety_policy_restrictive(medical_artifact, medical_task_text)

    unknown_artifact = build_relayscn_scene_policy_artifact(payload={"messages": []})
    _assert(unknown_artifact["scene_state_source"] == "heuristic", "empty request should remain heuristic")
    _assert(unknown_artifact["scene_state"]["scene_type"] == "unknown", "empty request should fail closed to unknown")

    relayrel_projection = build_relayrel_relationship_projection(route=None, request_scope_identity={"session_id": "s"})
    retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayint_intent_artifact={"unresolved_reference_detected": False, "mode_reasons": []},
        messages=[{"role": "user", "content": "diagnostic smoke text"}],
        token_budget=256,
        store_diagnostics={"store_enabled": False, "readiness": "disabled"},
        max_candidates=4,
        ctx_block_apply_enabled=False,
        snippet_extraction_enabled=False,
        snippet_dry_run_only=True,
        snippet_apply_enabled=False,
        snippet_budget=128,
        max_snippet_chars=128,
        max_snippet_candidates=2,
    )
    order_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=retrieval_artifact,
        actual_app_rewired=actual_app_rewired,
        measured_node_order=measured_node_order,
    )
    order = order_projection["request_path_order"]
    _assert(order.index("relayrel_relationship_projection") < order.index("relayscn_scene_policy"), "RelayREL must precede RelaySCN")
    _assert(order.index("relayscn_scene_policy") < order.index("relayemo_input"), "RelaySCN must precede input RelayEMO")
    _assert(order.index("relaymem_retrieval") > order.index("relayscn_scene_policy"), "RelayMEM must consume RelaySCN policy after SCN")
    _assert(order_projection["relaymem_consumes_relayscn_policy"] is True, "RelayMEM should consume RelaySCN")
    _assert(
        order_projection["measured_node_order"] == measured_node_order,
        "order projection must report the measured node order it was given",
    )
    _assert(
        order_projection["relayrel_precedes_relayscn"] == actual_app_rewired,
        "relayrel_precedes_relayscn must be derived from the measured app.py call order",
    )
    _assert(
        order_projection["relayscn_precedes_relayemo"] == actual_app_rewired,
        "relayscn_precedes_relayemo must be derived from the measured app.py call order",
    )

    missing_retrieval_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=None,
        actual_app_rewired=actual_app_rewired,
        measured_node_order=measured_node_order,
    )
    _assert(
        missing_retrieval_projection["relaymem_consumes_relayscn_policy"] is False,
        "RelayMEM consumption must require RelayMEM retrieval artifact evidence",
    )

    reversed_order_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=retrieval_artifact,
        actual_app_rewired=True,
        measured_node_order=["relayemo_input", "relayscn_scene_policy", "relayrel_relationship_projection"],
    )
    _assert(
        reversed_order_projection["relayscn_precedes_relayemo"] is False,
        "a reversed measured order must not report relayscn_precedes_relayemo as True",
    )
    _assert(
        reversed_order_projection["relayrel_precedes_relayscn"] is False,
        "a reversed measured order must not report relayrel_precedes_relayscn as True",
    )

    unmeasured_order_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=retrieval_artifact,
        actual_app_rewired=False,
    )
    _assert(
        unmeasured_order_projection["relayscn_precedes_relayemo"] is False,
        "without a measured order, precedence must fall back to actual_app_rewired rather than a hardcoded True",
    )
    _assert(
        unmeasured_order_projection["measured_node_order"] is None,
        "measured_node_order must be None when the caller supplies no measurement",
    )

    if actual_app_rewired:
        _assert(order_projection["merge_ready"] is True, order_projection)
        _assert(order_projection["remaining_work"] == [], order_projection)
    else:
        _assert(order_projection["merge_ready"] is False, order_projection)
        _assert("app.py_request_path_not_yet_rewired" in order_projection["remaining_work"], order_projection)

    public_json = json.dumps(order_projection, ensure_ascii=False)
    for forbidden in ("diagnostic smoke text", "relationship body", "memory body"):
        _assert(forbidden not in public_json, f"diagnostics leaked forbidden content: {forbidden}")

    print("relaylm_p0_pipeline_ordering_smoke: PASS")


if __name__ == "__main__":
    main()
