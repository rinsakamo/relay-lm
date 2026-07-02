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


def _app_request_path_order_is_rewired(app_source: str) -> bool:
    tree = ast.parse(app_source)
    call_lines: dict[str, list[int]] = {
        "build_relayrel_relationship_projection": [],
        "build_relayscn_scene_policy_artifact": [],
        "run_relayemo": [],
    }
    relayscn_has_relayemo_kwarg = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        func_name = node.func.id
        if func_name not in call_lines:
            continue
        call_lines[func_name].append(node.lineno)
        if func_name == "build_relayscn_scene_policy_artifact":
            relayscn_has_relayemo_kwarg = any(
                keyword.arg == "relayemo_artifact" for keyword in node.keywords
            )

    for func_name, lines in call_lines.items():
        _assert(lines, f"app.py must call {func_name}")
    if relayscn_has_relayemo_kwarg:
        return False

    relayrel_line = min(call_lines["build_relayrel_relationship_projection"])
    relayscn_line = min(call_lines["build_relayscn_scene_policy_artifact"])
    relayemo_line = min(call_lines["run_relayemo"])
    return relayrel_line < relayscn_line < relayemo_line


def main() -> None:
    signature = inspect.signature(build_relayscn_scene_policy_artifact)
    _assert("relayemo_artifact" not in signature.parameters, "RelaySCN public API must not expose relayemo_artifact")

    source = Path("relaylm/relayscn.py").read_text(encoding="utf-8")
    _assert("_extract_relayemo_scene_state" not in source, "RelayEMO scene-state extractor must be removed")
    _assert('source = "relayemo_artifact"' not in source, "RelaySCN must not emit relayemo_artifact scene source")

    app_source = Path("relaylm/app.py").read_text(encoding="utf-8")
    actual_app_rewired = _app_request_path_order_is_rewired(app_source)

    explicit_artifact = build_relayscn_scene_policy_artifact(
        payload={
            "metadata": {"relayscn": {"scene_state": {"scene_type": "review_work", "confidence": 0.91, "stability": 0.86}}},
            "messages": [{"role": "user", "content": "casual fallback text"}],
        }
    )
    _assert(explicit_artifact["scene_state_source"] == "request_metadata", "explicit metadata should win")
    _assert(explicit_artifact["scene_state"]["scene_type"] == "review_work", "explicit scene type should be preserved")

    heuristic_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]}
    )
    _assert(heuristic_artifact["scene_state_source"] == "heuristic", "missing metadata should use heuristic")
    _assert(heuristic_artifact["scene_state"]["scene_type"] == "review_work", "heuristic should classify review text")

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

    for pr_review_text in ("PR#123を確認して", "PRを確認して", "PR", "please check pr"):
        pr_review_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": pr_review_text}]}
        )
        _assert(
            pr_review_artifact["scene_state"]["scene_type"] == "review_work",
            f"PR confirmation cue should classify as review_work: {pr_review_text!r}",
        )

    formal_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "文書を作成して"}]}
    )
    _assert(
        formal_artifact["scene_state"]["scene_type"] == "formal_document",
        "Japanese document task should classify as formal_document",
    )

    for medical_task_text in ("医療について相談したい", "医療安全について確認したい"):
        medical_artifact = build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": medical_task_text}]}
        )
        _assert(
            medical_artifact["scene_state"]["scene_type"] == "medical_or_safety",
            f"medical/safety text should classify as medical_or_safety: {medical_task_text!r}",
        )
        scene_policy = medical_artifact["scene_policy"]
        _assert(
            scene_policy["relayctx_mode"] == "safety_cautious",
            "medical/safety policy should use safety-cautious RelayCTX mode",
        )
        _assert(
            scene_policy["relaymem_retrieval_scope"] == "minimal_or_evidence_only",
            "medical/safety policy should restrict RelayMEM retrieval to minimal/evidence scope",
        )
        _assert(
            scene_policy["relaymem_update_gate"] == "blocked",
            "medical/safety policy should block RelayMEM updates",
        )

    unknown_artifact = build_relayscn_scene_policy_artifact(payload={"messages": []})
    _assert(unknown_artifact["scene_state_source"] == "heuristic", "empty request should remain heuristic")
    _assert(unknown_artifact["scene_state"]["scene_type"] == "unknown", "empty request should fail closed to unknown")

    relayrel_projection = build_relayrel_relationship_projection(route=None, request_scope_identity={"session_id": "s"})
    retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayref_artifact={"unresolved_reference_detected": False, "mode_reasons": []},
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
    )
    order = order_projection["request_path_order"]
    _assert(order.index("relayrel_relationship_projection") < order.index("relayscn_scene_policy"), "RelayREL must precede RelaySCN")
    _assert(order.index("relayscn_scene_policy") < order.index("relayemo_input"), "RelaySCN must precede input RelayEMO")
    _assert(order.index("relaymem_retrieval") > order.index("relayscn_scene_policy"), "RelayMEM must consume RelaySCN policy after SCN")
    _assert(order_projection["relaymem_consumes_relayscn_policy"] is True, "RelayMEM should consume RelaySCN")

    missing_retrieval_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=None,
        actual_app_rewired=actual_app_rewired,
    )
    _assert(
        missing_retrieval_projection["relaymem_consumes_relayscn_policy"] is False,
        "RelayMEM consumption must require RelayMEM retrieval artifact evidence",
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
