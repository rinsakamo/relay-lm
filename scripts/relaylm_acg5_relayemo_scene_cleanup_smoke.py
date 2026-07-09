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


# Known identifiers per stage. A stage may be called directly
# (`build_x(...)`), indirected through the stage runner
# (`run_stage(node_timings, "x", build_x, ...)` / `run_stage(..., run_x_stage,
# ...)`), or -- for RelayMEM's retrieval builder -- offloaded to a worker
# thread via `asyncio.to_thread(_run_relaymem_retrieval_stage, ...)`. Tracking
# every known spelling keeps this smoke valid across branch shapes instead of
# hardcoding one call form.
_STAGE_IDENTIFIERS: dict[str, set[str]] = {
    "relayrel": {"build_relayrel_relationship_projection", "run_relayrel_stage"},
    "relayscn": {"build_relayscn_scene_policy_artifact", "run_relayscn_stage"},
    "relayemo": {"run_relayemo", "run_relayemo_stage"},
    "relayint": {"build_relayint_reference_repair_dry_run"},
    "relaymem": {"build_relaymem_retrieval_dry_run_artifact", "_run_relaymem_retrieval_stage"},
}
_NAME_TO_STAGE: dict[str, str] = {
    name: stage for stage, names in _STAGE_IDENTIFIERS.items() for name in names
}
# Not one of the five RelayEMO-adjacent stages above (and never indirected by
# any known branch shape), but still part of the original ordering guarantee.
_EXTRA_DIRECT_CALLS: tuple[str, ...] = ("apply_relaymem_runtime_injection_phase",)


def _handle_managed_chat_completion_body(tree: ast.AST) -> list[ast.stmt]:
    """Return the statement list making up handle_managed_chat_completion's body.

    Restricting the walk to this function's body keeps module-level helpers
    (e.g. ``_run_relaymem_retrieval_stage``, which is defined *before* the
    handler in source order) from polluting the line-number ordering used
    below.
    """

    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "handle_managed_chat_completion"
        ):
            return node.body
    raise AssertionError(
        "managed_chat_runtime.py must define handle_managed_chat_completion"
    )


def _stage_anchor_lines(body_stmts: list[ast.stmt]) -> dict[str, list[int]]:
    """Return each stage's anchor line numbers within the handler body.

    A stage's anchor line is any line where either (a) one of its known
    identifiers appears as an ``ast.Name`` -- as a call's func or as an
    argument, which covers direct calls, ``run_stage(..., build_x/run_x_stage,
    ...)`` indirection, and ``asyncio.to_thread(_run_relaymem_retrieval_stage,
    ...)`` -- or (b) a ``run_stage(...)`` call carries the stage's own name as
    a string constant argument.
    """

    anchors: dict[str, list[int]] = {stage: [] for stage in _STAGE_IDENTIFIERS}
    for stmt in body_stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                stage = _NAME_TO_STAGE.get(node.id)
                if stage is not None:
                    anchors[stage].append(node.lineno)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "run_stage"
            ):
                for arg in node.args:
                    if (
                        isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and arg.value in anchors
                    ):
                        anchors[arg.value].append(node.lineno)
    return anchors


def _stage_call_keyword_names(
    body_stmts: list[ast.stmt], stage_identifiers: set[str]
) -> set[str]:
    """Return keyword-argument names passed at any call site referencing a stage.

    A call "references" the stage when its func or one of its positional
    arguments is an ``ast.Name`` matching one of ``stage_identifiers``. This
    covers both a direct call (``build_x(payload=payload)``) and an
    indirected one (``run_stage(..., build_x, payload=payload)``, where
    ``run_stage`` forwards its own keyword arguments to the wrapped
    callable) or an offloaded one (``asyncio.to_thread(_run_x_stage,
    config=...)``).
    """

    keyword_names: set[str] = set()
    for stmt in body_stmts:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            references_stage = (
                isinstance(node.func, ast.Name) and node.func.id in stage_identifiers
            ) or any(
                isinstance(arg, ast.Name) and arg.id in stage_identifiers
                for arg in node.args
            )
            if references_stage:
                keyword_names.update(
                    keyword.arg for keyword in node.keywords if keyword.arg is not None
                )
    return keyword_names


def _relaymem_retrieval_stage_helper_has_relayemo_kwarg() -> bool:
    """Statically check the module-level RelayMEM retrieval helper's own body.

    On branch shapes where RelayMEM's retrieval builder call has moved out of
    ``handle_managed_chat_completion`` and into a module-level helper (offloaded
    via ``asyncio.to_thread``), the anchoring call site inside the handler no
    longer carries the retrieval builder's own keyword arguments. Inspect the
    helper's source directly so the "RelayMEM must not receive a RelayEMO
    artifact" guarantee survives that indirection too.
    """

    import relaylm.managed_chat_runtime as managed_chat_runtime

    helper = getattr(managed_chat_runtime, "_run_relaymem_retrieval_stage", None)
    if helper is None:
        return False
    helper_tree = ast.parse(inspect.getsource(helper))
    for node in ast.walk(helper_tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _STAGE_IDENTIFIERS["relaymem"]
            and any(keyword.arg == "relayemo_artifact" for keyword in node.keywords)
        ):
            return True
    return False


def _app_order_is_preserved(app_source: str) -> None:
    tree = ast.parse(app_source)
    body_stmts = _handle_managed_chat_completion_body(tree)

    stage_lines = _stage_anchor_lines(body_stmts)
    for stage, lines in stage_lines.items():
        _assert(lines, f"managed_chat_runtime.py must call the {stage} stage")

    direct_lines: dict[str, list[int]] = {name: [] for name in _EXTRA_DIRECT_CALLS}
    for stmt in body_stmts:
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in direct_lines
            ):
                direct_lines[node.func.id].append(node.lineno)
    for func_name, lines in direct_lines.items():
        _assert(lines, f"managed_chat_runtime.py must call {func_name}")

    relayscn_has_relayemo_kwarg = "relayemo_artifact" in _stage_call_keyword_names(
        body_stmts, _STAGE_IDENTIFIERS["relayscn"]
    )
    relaymem_has_relayemo_kwarg = "relayemo_artifact" in _stage_call_keyword_names(
        body_stmts, _STAGE_IDENTIFIERS["relaymem"]
    )
    relaymem_has_relayemo_kwarg = (
        relaymem_has_relayemo_kwarg or _relaymem_retrieval_stage_helper_has_relayemo_kwarg()
    )
    _assert(not relayscn_has_relayemo_kwarg, "RelaySCN must not receive RelayEMO artifact input")
    _assert(not relaymem_has_relayemo_kwarg, "RelayMEM must not receive RelayEMO artifact policy input")

    order = [min(stage_lines[stage]) for stage in ("relayrel", "relayscn", "relayemo", "relayint", "relaymem")]
    order.extend(min(direct_lines[name]) for name in _EXTRA_DIRECT_CALLS)
    _assert(
        order == sorted(order),
        {"unexpected_order": {**stage_lines, **direct_lines}},
    )


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

    app_source = (REPO_ROOT / "relaylm" / "managed_chat_runtime.py").read_text(encoding="utf-8")
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
