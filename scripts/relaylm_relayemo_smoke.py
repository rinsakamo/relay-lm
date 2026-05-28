from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _apply_relayemo_marker_to_response, _build_relayemo_text_marker_preview
from relaylm.config import load_config
from relaylm.relayemo import run_relayemo


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    require(config.relayemo_enabled is False, "default relayemo_enabled must be false")

    msgs = [{"role": "user", "content": "今日はうれしい！"}]
    artifact = run_relayemo(config=config, messages=msgs).artifact
    require(artifact["user_affect_estimate_is_estimate"] is True, artifact)
    require(artifact["text_marker_apply"]["applied_to_soul"] is False, artifact)
    require(artifact["text_marker_apply"]["applied_to_mem"] is False, artifact)
    require(artifact["text_marker_apply"]["persisted_user_affect"] is False, artifact)

    cfg_preview = config.model_copy(update={"relayemo_enabled": True, "relayemo_text_marker_enabled": True, "relayemo_text_marker_apply_mode": "preview"})
    preview = _build_relayemo_text_marker_preview(cfg_preview, artifact)
    require("gate_open" in preview, preview)

    cfg_apply = config.model_copy(update={"relayemo_enabled": True, "relayemo_text_marker_enabled": True, "relayemo_text_marker_apply_mode": "apply", "relayemo_marker_open_threshold": 0.1})
    hi = run_relayemo(config=cfg_apply, messages=msgs).artifact
    hi["user_affect_estimate"]["confidence"] = 0.9
    hi["user_affect_estimate"]["intensity"] = 0.9
    hi["scene_state"]["scene_type"] = "casual_chat"
    p = _build_relayemo_text_marker_preview(cfg_apply, hi)
    body = {"choices": [{"message": {"content": "了解しました。"}}]}
    out = _apply_relayemo_marker_to_response(body, p)
    require(out["choices"][0]["message"]["content"].endswith("✨"), out)

    formal = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "formal report を作成"}]).artifact
    formal_p = _build_relayemo_text_marker_preview(cfg_apply, formal)
    require(formal_p["suppression_reason"] == "scene_suppressed", formal_p)

    low = run_relayemo(config=cfg_apply, messages=[{"role": "user", "content": "..."}]).artifact
    low_p = _build_relayemo_text_marker_preview(cfg_apply, low)
    require(low_p["suppression_reason"] == "low_confidence", low_p)

    print("ok relayemo smoke")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
