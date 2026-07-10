from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import relaylm.app as relay_app
import relaylm.managed_chat_runtime as managed_chat_runtime
from relaylm.managed_chat_runtime import (
    _apply_relayemo_marker_to_response,
    _build_relayemo_text_marker_preview,
)
from relaylm.config import load_config
from relaylm.relayemo import (
    parse_llm_affect_probe_output,
    run_relayemo,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    require(config.relayemo_enabled is False, "default relayemo_enabled must be false")

    msgs = [{"role": "user", "content": "今日は嬉しい!"}]
    artifact = run_relayemo(config=config, messages=msgs).artifact
    require(artifact["user_affect_estimate_is_estimate"] is True, artifact)
    require(artifact["text_marker_apply"]["applied_to_soul"] is False, artifact)
    require(artifact["text_marker_apply"]["applied_to_mem"] is False, artifact)
    require(artifact["text_marker_apply"]["applied_to_tts"] is False, artifact)
    require(artifact["text_marker_apply"]["persisted_user_affect"] is False, artifact)

    cfg_preview = config.model_copy(update={"relayemo_enabled": True, "relayemo_text_marker_enabled": True, "relayemo_text_marker_apply_mode": "preview"})
    preview = _build_relayemo_text_marker_preview(cfg_preview, artifact)
    require("gate_open" in preview, preview)

    cfg_apply = config.model_copy(update={"relayemo_enabled": True, "relayemo_text_marker_enabled": True, "relayemo_text_marker_apply_mode": "apply"})
    hi = run_relayemo(config=cfg_apply, messages=msgs).artifact
    hi["user_affect_estimate"]["confidence"] = 0.9
    hi["scene_state"]["scene_type"] = "casual_chat"
    p = _build_relayemo_text_marker_preview(cfg_apply, hi)
    require(p["gate_open"] is True, p)
    body = {"choices": [{"message": {"content": "了解しました。"}}]}
    out = _apply_relayemo_marker_to_response(body, p)
    require(out["choices"][0]["message"]["content"].endswith("✨"), out)

    design = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "設計の方向性、嬉しい!"}]).artifact
    design["user_affect_estimate"]["confidence"] = 0.9
    design["scene_state"]["scene_type"] = "design_talk"
    design_p = _build_relayemo_text_marker_preview(cfg_apply, design)
    require(design_p["gate_open"] is True, design_p)

    formal = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "formal report を作成"}]).artifact
    formal_p = _build_relayemo_text_marker_preview(cfg_apply, formal)
    require(formal_p["suppression_reason"] == "scene_suppressed", formal_p)

    low = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "..."}]).artifact
    low["assistant_emotion_state"]["intensity"] = 0.9
    low_p = _build_relayemo_text_marker_preview(cfg_apply, low)
    require(low_p["suppression_reason"] == "low_confidence", low_p)

    off_marker = config.model_copy(update={"relayemo_enabled": True, "relayemo_text_marker_enabled": False})
    off_artifact = run_relayemo(config=off_marker, messages=msgs).artifact
    require("assistant_emotion_state" in off_artifact, off_artifact)
    require(off_artifact["text_marker_apply"]["applied_to_text"] is False, off_artifact)
    require(off_artifact.get("session_state_enabled") is None, off_artifact)
    require(off_artifact.get("heuristic_user_affect_estimate") is not None, off_artifact)

    llm_cfg = config.model_copy(
        update={
            "relayemo_affect_probe_mode": "llm_structured_dry_run",
            "relayemo_llm_affect_probe_enabled": True,
        }
    )
    llm_artifact = run_relayemo(config=llm_cfg, messages=msgs).artifact
    require(llm_artifact["llm_candidate_applied"] is False, llm_artifact)
    require(isinstance(llm_artifact["llm_affect_probe_meta"], dict), llm_artifact)

    bad = parse_llm_affect_probe_output("{bad json")
    require(bad["classifier_meta"]["parse_ok"] is False, bad)
    clamp = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {
                    "valence": 9,
                    "arousal": -1,
                    "dominance": -9,
                    "intensity": 3,
                    "confidence": 2,
                    "mode": "x",
                },
                "scene_state_candidate": {"scene_type": "casual_chat", "confidence": 3},
            }
        )
    )
    cand = clamp["user_affect_estimate_candidate"]
    require(cand["valence"] == 1.0 and cand["arousal"] == 0.0 and cand["dominance"] == -1.0, clamp)
    require(cand["intensity"] == 1.0 and cand["confidence"] == 1.0, clamp)
    require(clamp["scene_state_candidate"]["scene_type"] == "casual_chat", clamp)
    unknown_scene = parse_llm_affect_probe_output(
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
                "scene_state_candidate": {"scene_type": "unknown_scene", "confidence": 0.8},
            }
        )
    )
    require("invalid_scene_type" in unknown_scene["classifier_meta"]["validation_errors"], unknown_scene)
    require(unknown_scene["scene_state_candidate"]["scene_type"] == "unknown", unknown_scene)
    null_cand = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": None,
                "scene_state_candidate": {"scene_type": "casual_chat", "confidence": 0.4},
            }
        )
    )
    require("user_affect_estimate_candidate_not_object" in null_cand["classifier_meta"]["validation_errors"], null_cand)
    null_scene = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1},
                "scene_state_candidate": None,
            }
        )
    )
    require("scene_state_candidate_not_object" in null_scene["classifier_meta"]["validation_errors"], null_scene)
    list_fields = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": [],
                "scene_state_candidate": "oops",
            }
        )
    )
    require(
        "user_affect_estimate_candidate_not_object" in list_fields["classifier_meta"]["validation_errors"]
        and "scene_state_candidate_not_object" in list_fields["classifier_meta"]["validation_errors"],
        list_fields,
    )
    missing_all = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require(missing_all["classifier_meta"]["parse_ok"] is False, missing_all)
    require("missing_numeric_field:valence" in missing_all["classifier_meta"]["validation_errors"], missing_all)
    require("missing_numeric_field:dominance" in missing_all["classifier_meta"]["validation_errors"], missing_all)
    missing_valence = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require("missing_numeric_field:valence" in missing_valence["classifier_meta"]["validation_errors"], missing_valence)
    missing_dom = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1, "arousal": 0.2, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require("missing_numeric_field:dominance" in missing_dom["classifier_meta"]["validation_errors"], missing_dom)
    bad_valence = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": "x", "arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require("invalid_numeric_field:valence" in bad_valence["classifier_meta"]["validation_errors"], bad_valence)
    bad_dom = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1, "arousal": 0.2, "dominance": None, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require("invalid_numeric_field:dominance" in bad_dom["classifier_meta"]["validation_errors"], bad_dom)
    bad_bool = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": True, "arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require("invalid_numeric_field:valence" in bad_bool["classifier_meta"]["validation_errors"], bad_bool)
    nan_valence = parse_llm_affect_probe_output(
        '{"user_affect_estimate_candidate":{"valence":NaN,"arousal":0.2,"dominance":0.1,"intensity":0.2,"confidence":0.2},"scene_state_candidate":{"scene_type":"casual_chat"}}'
    )
    require("invalid_numeric_field:valence" in nan_valence["classifier_meta"]["validation_errors"], nan_valence)
    inf_intensity = parse_llm_affect_probe_output(
        '{"user_affect_estimate_candidate":{"valence":0.1,"arousal":0.2,"dominance":0.1,"intensity":Infinity,"confidence":0.2},"scene_state_candidate":{"scene_type":"casual_chat"}}'
    )
    require("invalid_numeric_field:intensity" in inf_intensity["classifier_meta"]["validation_errors"], inf_intensity)
    neginf_conf = parse_llm_affect_probe_output(
        '{"user_affect_estimate_candidate":{"valence":0.1,"arousal":0.2,"dominance":0.1,"intensity":0.2,"confidence":-Infinity},"scene_state_candidate":{"scene_type":"casual_chat"}}'
    )
    require("invalid_numeric_field:confidence" in neginf_conf["classifier_meta"]["validation_errors"], neginf_conf)
    miss_scene_conf = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1, "arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat"},
            }
        )
    )
    require(
        "missing_numeric_field:scene_state_candidate.confidence"
        in miss_scene_conf["classifier_meta"]["validation_errors"],
        miss_scene_conf,
    )
    bad_scene_conf_str = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1, "arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat", "confidence": "high"},
            }
        )
    )
    require(
        "invalid_numeric_field:scene_state_candidate.confidence"
        in bad_scene_conf_str["classifier_meta"]["validation_errors"],
        bad_scene_conf_str,
    )
    bad_scene_conf_bool = parse_llm_affect_probe_output(
        json.dumps(
            {
                "user_affect_estimate_candidate": {"valence": 0.1, "arousal": 0.2, "dominance": 0.1, "intensity": 0.2, "confidence": 0.2},
                "scene_state_candidate": {"scene_type": "casual_chat", "confidence": True},
            }
        )
    )
    require(
        "invalid_numeric_field:scene_state_candidate.confidence"
        in bad_scene_conf_bool["classifier_meta"]["validation_errors"],
        bad_scene_conf_bool,
    )
    bad_scene_conf_nan = parse_llm_affect_probe_output(
        '{"user_affect_estimate_candidate":{"valence":0.1,"arousal":0.2,"dominance":0.1,"intensity":0.2,"confidence":0.2},"scene_state_candidate":{"scene_type":"casual_chat","confidence":NaN}}'
    )
    require(
        "invalid_numeric_field:scene_state_candidate.confidence"
        in bad_scene_conf_nan["classifier_meta"]["validation_errors"],
        bad_scene_conf_nan,
    )
    bad_scene_conf_inf = parse_llm_affect_probe_output(
        '{"user_affect_estimate_candidate":{"valence":0.1,"arousal":0.2,"dominance":0.1,"intensity":0.2,"confidence":0.2},"scene_state_candidate":{"scene_type":"casual_chat","confidence":Infinity}}'
    )
    require(
        "invalid_numeric_field:scene_state_candidate.confidence"
        in bad_scene_conf_inf["classifier_meta"]["validation_errors"],
        bad_scene_conf_inf,
    )

    jp = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "RelayEMOめちゃくちゃ良いね！"}]).artifact
    jp["scene_state"]["scene_type"] = "casual_chat"
    jp_p = _build_relayemo_text_marker_preview(cfg_apply, jp)
    require(jp_p["gate_open"] is True, jp_p)

    zenkaku = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "！"}]).artifact
    zenkaku["scene_state"]["scene_type"] = "casual_chat"
    zenkaku_p = _build_relayemo_text_marker_preview(cfg_apply, zenkaku)
    require(zenkaku_p["gate_open"] is True, zenkaku_p)

    saiko = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "最高!"}]).artifact
    saiko["scene_state"]["scene_type"] = "casual_chat"
    saiko_p = _build_relayemo_text_marker_preview(cfg_apply, saiko)
    require(saiko_p["gate_open"] is True, saiko_p)

    impl = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "実装を進めたい！"}]).artifact
    impl_p = _build_relayemo_text_marker_preview(cfg_apply, impl)
    require(impl_p["suppression_reason"] == "preview_only_scene", impl_p)

    async def _fake_open_chat_completion_stream(
        payload: dict[str, Any], route: Any, client: Any = None
    ) -> tuple[int, str, Any]:
        async def _iter() -> Any:
            yield b"data: [DONE]\n\n"
        return 200, "text/event-stream", _iter()

    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "config.yaml"
        cfg_path.write_text(
            "\n".join(
                [
                    "mode: pass_through",
                    "relayemo_enabled: true",
                    "relayemo_text_marker_enabled: false",
                    "relayemo_session_state_enabled: true",
                    "relayemo_session_state_ttl_seconds: 1800",
                    "relayemo_session_state_max_entries: 256",
                    "trace:",
                    "  enabled: true",
                    f"  path: {trace_path}",
                    "backends:",
                    "  local_backend:",
                    "    type: openai_compatible",
                    "    base_url: http://127.0.0.1:8000/v1",
                    "    api_key: dummy",
                    "model_routes:",
                    "  relaylm-default:",
                    "    backend: local_backend",
                    "    backend_model: local-model",
                    "    mode: pass_through",
                ]
            ),
            encoding="utf-8",
        )
        from fastapi.testclient import TestClient
        original = managed_chat_runtime.open_chat_completion_stream
        managed_chat_runtime.open_chat_completion_stream = _fake_open_chat_completion_stream
        try:
            app = relay_app.create_app(str(cfg_path))
            client = TestClient(app)
            with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": "relaylm-default",
                    "stream": True,
                    "messages": [{"role": "user", "content": "今日は嬉しい!"}],
                },
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
            lines = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            require(bool(lines), "trace should be written for stream success")
            record = json.loads(lines[-1])
            metadata = record.get("metadata") or {}
            require(metadata.get("event") == "backend_stream_response", metadata)
            require(isinstance(metadata.get("relayemo_artifact"), dict), metadata)
            artifact_meta = metadata.get("relayemo_artifact") or {}
            require(artifact_meta.get("session_state_enabled") is True, artifact_meta)
            require(artifact_meta.get("state_storage") == "process_memory", artifact_meta)
            require(artifact_meta.get("session_key_source") == "unavailable", artifact_meta)
            require(artifact_meta.get("state_updated") is False, artifact_meta)
            require(artifact_meta.get("fallback_reason") == "session_key_unavailable", artifact_meta)
            with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": "relaylm-default",
                    "stream": True,
                    "user": "session-a",
                    "metadata": {"session_id": "session-a"},
                    "messages": [{"role": "user", "content": "最高!"}],
                },
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
            with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": "relaylm-default",
                    "stream": True,
                    "user": "session-a",
                    "metadata": {"session_id": "session-a"},
                    "messages": [{"role": "user", "content": "..."}],
                },
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
            lines2 = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            record2 = json.loads(lines2[-1])
            artifact2 = (record2.get("metadata") or {}).get("relayemo_artifact") or {}
            require(artifact2.get("previous_state_found") is True, artifact2)
            with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": "relaylm-default",
                    "stream": True,
                    "user": "session-a",
                    "metadata": {"session_id": "session-b"},
                    "messages": [{"role": "user", "content": "..." }],
                },
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
            lines3 = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            record3 = json.loads(lines3[-1])
            artifact3 = (record3.get("metadata") or {}).get("relayemo_artifact") or {}
            require(artifact3.get("previous_state_found") is False, artifact3)
        finally:
            managed_chat_runtime.open_chat_completion_stream = original
    with tempfile.TemporaryDirectory() as td2:
        trace_path2 = Path(td2) / "trace_route_session.jsonl"
        cfg_path2 = Path(td2) / "config.yaml"
        cfg_path2.write_text(
            "\n".join(
                [
                    "mode: pass_through",
                    "relayemo_enabled: true",
                    "relayemo_text_marker_enabled: false",
                    "relayemo_session_state_enabled: true",
                    "trace:",
                    "  enabled: true",
                    f"  path: {trace_path2}",
                    "backends:",
                    "  local_backend:",
                    "    type: openai_compatible",
                    "    base_url: http://127.0.0.1:8000/v1",
                    "    api_key: dummy",
                    "model_routes:",
                    "  relaylm-default:",
                    "    backend: local_backend",
                    "    backend_model: local-model",
                    "    mode: pass_through",
                    "    session_id: route-session-1",
                ]
            ),
            encoding="utf-8",
        )
        from fastapi.testclient import TestClient
        original2 = managed_chat_runtime.open_chat_completion_stream
        managed_chat_runtime.open_chat_completion_stream = _fake_open_chat_completion_stream
        try:
            app2 = relay_app.create_app(str(cfg_path2))
            client2 = TestClient(app2)
            with client2.stream(
                "POST",
                "/v1/chat/completions",
                json={"model": "relaylm-default", "stream": True, "messages": [{"role": "user", "content": "最高!"}]},
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
            with client2.stream(
                "POST",
                "/v1/chat/completions",
                json={"model": "relaylm-default", "stream": True, "messages": [{"role": "user", "content": "..."}]},
            ) as response:
                require(response.status_code == 200, f"bad stream status: {response.status_code}")
                _ = b"".join(response.iter_bytes())
        finally:
            managed_chat_runtime.open_chat_completion_stream = original2
        lines_route = [line for line in trace_path2.read_text(encoding="utf-8").splitlines() if line.strip()]
        artifact_route = (json.loads(lines_route[-1]).get("metadata") or {}).get("relayemo_artifact") or {}
        require(artifact_route.get("previous_state_found") is True, artifact_route)
        require(artifact_route.get("session_key_source") == "resolved_session_id", artifact_route)
    s_cfg = config.model_copy(update={"relayemo_session_state_enabled": True})
    first = run_relayemo(config=s_cfg, messages=[{"role": "user", "content": "最高!"}], previous_assistant_state=None).artifact
    second = run_relayemo(
        config=s_cfg,
        messages=[{"role": "user", "content": "..."}],
        previous_assistant_state=first["assistant_emotion_state"],
    ).artifact
    require(
        float(second["assistant_emotion_state"]["intensity"]) < float(first["assistant_emotion_state"]["intensity"]),
        {"first": first, "second": second},
    )

    print("ok relayemo smoke")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
