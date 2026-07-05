"""Compatibility shim for the former ACG-5 RelayEMO implementation module.

The RelayEMO ACG-5 scene-hint cleanup helpers and ``run_relayemo(...)`` have
been folded into ``relaylm.relayemo``, which is now the canonical
implementation owner. This module re-exports the same public names so that
existing ``from relaylm.relayemo_acg5 import ...`` call sites keep working.
"""

from __future__ import annotations

from relaylm.relayemo import *  # noqa: F401,F403
from relaylm.relayemo import (
    RelayEmoRuntimeResult,
    SCENE_HINT_TYPES,
    build_llm_affect_probe_candidate,
    build_llm_affect_probe_prompt,
    build_scene_hint_candidate,
    estimate_user_affect,
    infer_scene_hint_type,
    latest_assistant_text,
    latest_user_text,
    load_session_assistant_state,
    parse_llm_affect_probe_output,
    run_relayemo,
    save_session_assistant_state,
)
