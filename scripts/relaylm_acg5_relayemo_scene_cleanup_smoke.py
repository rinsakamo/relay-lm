#!/usr/bin/env python3
"""Smoke coverage for ACG-5 RelayEMO scene ownership cleanup."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from relaylm.analyzer_governance import can_open_runtime_policy
from relaylm.config import load_config
from relaylm.relayemo import build_scene_hint_candidate, parse_llm_affect_probe_output, run_relayemo
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relayscn import build_relayscn_scene_policy_artifact


REPO_ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assert_content_free(value: object) -> None:
    serialized = _serialized(value)
    for token in ("secret scene body", "private user text", "keyword:private body"):
        _assert(token not in serialized, serialized)


def _app_order_is_preserved(app_source: str) -> None:
    tree = ast.parse(app_source)
    call_lines: dict[str, list[int]] = {
        "build_relayrel_relationship_projection": [],
        "build_relayscn_scene_policy_artifact": [],
        "run_relayemo": [],
        "build_relayint_reference_repair_dry_run": [],
        "build_relaymem_retrieval_dry_run_artifact": [],
        "apply_relaymem_runtime_injection_phase": [],
    }
    relayscn_has_relayemo_kwarg = False
    relaymem_has_relayemo_kwarg = False

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
        if func_name == "build_relaymem_retrieval_dry_run_artifact":
            relaymem_has_relayemo_kwarg = any(
                keyword.arg == "relayemo_artifact" for keyword in node.keywords
            )

    for func_name, lines in call_lines.items():
        _assert(lines, f"app.py must call {func_name}")
    _assert(not relayscn_has_relayemo_kwarg, "RelaySCN must not receive RelayEMO artifact input")
    _assert(not relaymem_has_relayemo_kwarg, "RelayMEM must not receive RelayEMO artifact policy input")

    order = [min(call_lines[name]) for name in call_lines]
    _assert(order == sorted(order), {"unexpected_order": call_lines})


def main() -> None:
    config = load_config(REPO_ROOT / "config.example.yaml")
    artifact = run_relayemo(
        config=config,
        messages=[{"role": "user", "content": "実装を進めたい！"}],
    ).artifact

    _assert("scene_hint_candidate" in artifact, artifact)
    _assert("scene_state" in artifact, artifact)
    _assert(artifact["scene_state"].get("deprecated") is True, artifact["scene_state"])
    _assert(artifact["scene_state"].get("source_authoritative") is False, artifact["scene_state"])
    _assert(artifact["scene_state"].get("policy_authority") == "none", artifact["scene_state"])
    _assert(artifact["scene_state"].get("restrictive_only") is True, artifact["scene_state"])

    scene_hint = artifact["scene_hint_candidate"]
    _assert(scene_hint["source_authoritative"] is False, scene_hint)
    _assert(scene_hint["policy_authority"] == "none", scene_hint)
    _assert(scene_hint["restrictive_only"] is True, scene_hint)
    _assert(scene_hint["candidate_applied"] is False, scene_hint)
    _assert(scene_hint["can_open_runtime_policy"] is False, scene_hint)
    _assert(scene_hint["content_free"] is True, scene_hint)
    _assert(can_open_runtime_policy(scene_hint["governance"]) is False, scene_hint)
    _assert_content_free(artifact["scene_hint_candidate_public"])

    relayscn_signature = inspect.signature(build_relayscn_scene_policy_artifact)
    _assert("relayemo_artifact" not in relayscn_signature.parameters, relayscn_signature)
    try:
        build_relayscn_scene_policy_artifact(
            payload={"messages": [{"role": "user", "content": "Please review this PR."}]},
            **{"relayemo_artifact": artifact},
        )
    except TypeError as exc:
        _assert("relayemo_artifact" in str(exc), exc)
    else:
        raise AssertionError("RelaySCN must reject RelayEMO scene-hint artifacts")

    app_source = (REPO_ROOT / "relaylm" / "app.py").read_text(encoding="utf-8")
    _app_order_is_preserved(app_source)

    relaymem_signature = inspect.signature(build_relaymem_retrieval_dry_run_artifact)
    _assert("relayscn_scene_policy_artifact" in relaymem_signature.parameters, relaymem_signature)
    _assert("relayemo_artifact" not in relaymem_signature.parameters, relaymem_signature)

    relayscn_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]}
    )
    retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=relayscn_artifact,
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
    _assert(
        retrieval_artifact["scene_type"] == relayscn_artifact["scene_state"]["scene_type"],
        retrieval_artifact,
    )
    _assert(
        retrieval_artifact["retrieval_scope"]
        == relayscn_artifact["scene_policy"]["relaymem_retrieval_scope"],
        retrieval_artifact,
    )
    _assert("relayemo" not in _serialized(retrieval_artifact).lower(), retrieval_artifact)

    positive = run_relayemo(
        config=config,
        messages=[{"role": "user", "content": "今日は嬉しい!"}],
    ).artifact
    _assert(positive["user_affect_estimate"]["valence"] > 0, positive)
    _assert("assistant_emotion_state" in positive, positive)

    invalid_hint = build_scene_hint_candidate(
        scene_hint_type="secret scene body",
        source="llm_candidate",
        confidence=0.9,
    )
    _assert(invalid_hint["scene_type"] == "unknown", invalid_hint)
    _assert(invalid_hint["can_open_runtime_policy"] is False, invalid_hint)
    _assert_content_free(invalid_hint)

    parsed = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {
                    "valence": 0.1,
                    "arousal": 0.2,
                    "dominance": 0.1,
                    "intensity": 0.2,
                    "confidence": 0.2,
                    "mode": "x",
                },
                "scene_hint_candidate": {"scene_type": "keyword:private body", "confidence": 0.9},
            }
        )
    )
    _assert(parsed["scene_hint_candidate"]["scene_type"] == "unknown", parsed)
    _assert(parsed["scene_hint_candidate"]["can_open_runtime_policy"] is False, parsed)
    _assert_content_free(parsed["scene_hint_candidate"])

    relayscn_source = (REPO_ROOT / "relaylm" / "relayscn.py").read_text(encoding="utf-8")
    _assert("_extract_relayemo_scene_state" not in relayscn_source, "RelayEMO -> RelaySCN fallback helper must not exist")
    _assert('source = "relayemo_artifact"' not in relayscn_source, "RelaySCN must not emit relayemo_artifact source")

    print("ok acg5 relayemo scene cleanup smoke")


if __name__ == "__main__":
    main()
