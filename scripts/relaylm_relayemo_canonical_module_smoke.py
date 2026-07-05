#!/usr/bin/env python3
"""Smoke coverage for the RelayEMO ACG-5 canonical module fold-in.

``relaylm.relayemo`` now owns the RelayEMO implementation directly; the
former ``relaylm.relayemo_acg5`` module is a compatibility shim only. This
smoke verifies both import paths keep working, expose the same canonical
callables, keep deprecated compatibility aliases available, and that
``run_relayemo(...)`` output shape is unchanged.
"""

from __future__ import annotations

from pathlib import Path

from relaylm.config import load_config
import relaylm.relayemo as relayemo
import relaylm.relayemo_acg5 as relayemo_acg5

REPO_ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    _assert(
        relayemo_acg5.run_relayemo is relayemo.run_relayemo,
        "relayemo_acg5.run_relayemo must be the same callable as relayemo.run_relayemo",
    )
    _assert(
        relayemo_acg5.build_scene_hint_candidate is relayemo.build_scene_hint_candidate,
        "relayemo_acg5.build_scene_hint_candidate must be the same callable as relayemo.build_scene_hint_candidate",
    )
    _assert(
        relayemo_acg5.parse_llm_affect_probe_output is relayemo.parse_llm_affect_probe_output,
        "relayemo_acg5.parse_llm_affect_probe_output must be the same callable as relayemo.parse_llm_affect_probe_output",
    )
    _assert(
        relayemo_acg5.SCENE_HINT_TYPES is relayemo.SCENE_HINT_TYPES,
        "relayemo_acg5.SCENE_HINT_TYPES must be the same object as relayemo.SCENE_HINT_TYPES",
    )
    print("ok relayemo and relayemo_acg5 expose the same canonical callables")

    _assert(hasattr(relayemo, "SCENE_TYPES"), "relayemo.SCENE_TYPES deprecated alias missing")
    _assert(
        relayemo.SCENE_TYPES is relayemo.SCENE_HINT_TYPES,
        "relayemo.SCENE_TYPES must alias SCENE_HINT_TYPES",
    )
    _assert(
        hasattr(relayemo, "infer_scene_type"),
        "relayemo.infer_scene_type deprecated alias missing",
    )
    _assert(
        relayemo.infer_scene_type is relayemo.infer_scene_hint_type,
        "relayemo.infer_scene_type must alias infer_scene_hint_type",
    )
    _assert(
        hasattr(relayemo_acg5, "SCENE_TYPES") and relayemo_acg5.SCENE_TYPES is relayemo.SCENE_TYPES,
        "relayemo_acg5.SCENE_TYPES deprecated alias must remain importable",
    )
    _assert(
        hasattr(relayemo_acg5, "infer_scene_type")
        and relayemo_acg5.infer_scene_type is relayemo.infer_scene_type,
        "relayemo_acg5.infer_scene_type deprecated alias must remain importable",
    )
    print("ok deprecated compatibility aliases remain available on both import paths")

    config = load_config(REPO_ROOT / "config.example.yaml")
    messages = [{"role": "user", "content": "実装を進めたい！"}]

    from_canonical = relayemo.run_relayemo(config=config, messages=messages)
    from_shim = relayemo_acg5.run_relayemo(config=config, messages=messages)

    expected_keys = {
        "user_affect_estimate",
        "affect_probe_mode",
        "heuristic_user_affect_estimate",
        "llm_user_affect_estimate_candidate",
        "llm_scene_hint_candidate",
        "llm_scene_state_candidate",
        "llm_affect_probe_meta",
        "llm_candidate_applied",
        "assistant_emotion_state",
        "scene_hint_candidate",
        "scene_state",
        "scene_hint_candidate_public",
        "text_marker_preview",
        "text_marker_apply",
        "user_affect_estimate_is_estimate",
    }
    _assert(
        set(from_canonical.artifact.keys()) == expected_keys,
        {"artifact_keys": sorted(from_canonical.artifact.keys())},
    )
    _assert(
        set(from_shim.artifact.keys()) == expected_keys,
        {"shim_artifact_keys": sorted(from_shim.artifact.keys())},
    )
    _assert(
        from_canonical.artifact == from_shim.artifact,
        "run_relayemo output must be identical via both import paths for the same input",
    )
    _assert(
        from_canonical.artifact["scene_state"]["scene_type"] == "implementation_work",
        from_canonical.artifact["scene_state"],
    )
    _assert(
        from_canonical.artifact["scene_state"].get("deprecated") is True,
        from_canonical.artifact["scene_state"],
    )
    _assert(
        "assistant_emotion_state" in from_canonical.artifact,
        from_canonical.artifact,
    )
    print("ok run_relayemo output shape is unchanged across both import paths")

    print("ok relaylm_relayemo_canonical_module_smoke")


if __name__ == "__main__":
    main()
