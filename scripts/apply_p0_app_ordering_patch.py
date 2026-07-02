#!/usr/bin/env python3
"""Apply the P0 RelayREL / RelaySCN / RelayEMO app.py ordering patch.

This helper is intentionally a one-shot local patch tool for the draft PR. It
rewires the FastAPI request path so RelaySCN is built before input-side RelayEMO
and removes the deprecated RelayEMO artifact argument from RelaySCN.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "relaylm" / "app.py"


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one {label} occurrence, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    source = APP_PATH.read_text(encoding="utf-8")

    source = _replace_once(
        source,
        "from relaylm.relayscn import build_relayscn_scene_policy_artifact\n",
        "from relaylm.relayscn import build_relayscn_scene_policy_artifact\n"
        "from relaylm.relayrel import build_relayrel_relationship_projection\n",
        "RelayREL import insertion point",
    )

    old_block = '''        forwarded_payload = pipeline_context.forwarded_payload
        token_budget_truncation: dict[str, Any] | None = None
        relayemo_artifact: dict[str, Any] | None = None
        if config.relayemo_enabled:
            session_key, session_key_source = _resolve_relayemo_session_key(
                route=route,
                payload=payload,
                request=request,
                request_scope_identity=request_scope_identity,
                scope_resolution_diagnostics=scope_resolution_diagnostics,
            )
            previous_assistant_state = None
            previous_state_found = False
            state_updated = True
            fallback_reason: str | None = None
            can_use_session_state = (
                config.relayemo_session_state_enabled and session_key is not None
            )
            if config.relayemo_session_state_enabled and session_key is None:
                state_updated = False
                fallback_reason = "session_key_unavailable"
            if can_use_session_state and session_key is not None:
                previous_assistant_state = load_session_assistant_state(
                    session_key,
                    ttl_seconds=config.relayemo_session_state_ttl_seconds,
                )
                previous_state_found = previous_assistant_state is not None
            relayemo_result = run_relayemo(
                config=config,
                messages=_extract_trace_messages(forwarded_payload),
                previous_assistant_state=previous_assistant_state,
            )
            relayemo_artifact = relayemo_result.artifact
            relayemo_artifact["session_state_enabled"] = config.relayemo_session_state_enabled
            relayemo_artifact["session_key_source"] = session_key_source
            relayemo_artifact["previous_state_found"] = previous_state_found
            relayemo_artifact["state_updated"] = state_updated
            relayemo_artifact["state_persisted"] = False
            relayemo_artifact["state_storage"] = "process_memory"
            if fallback_reason is not None:
                relayemo_artifact["fallback_reason"] = fallback_reason
            if can_use_session_state and session_key is not None:
                save_session_assistant_state(
                    session_key,
                    relayemo_result.assistant_state,
                    max_entries=config.relayemo_session_state_max_entries,
                )

        relayscn_scene_policy_artifact = build_relayscn_scene_policy_artifact(
            payload=payload,
            relayemo_artifact=relayemo_artifact,
        )
'''
    new_block = '''        forwarded_payload = pipeline_context.forwarded_payload
        token_budget_truncation: dict[str, Any] | None = None
        relayrel_relationship_projection = build_relayrel_relationship_projection(
            route=route,
            request_scope_identity=request_scope_identity,
        )
        _ = relayrel_relationship_projection
        relayscn_scene_policy_artifact = build_relayscn_scene_policy_artifact(
            payload=payload,
        )
        relayemo_artifact: dict[str, Any] | None = None
        if config.relayemo_enabled:
            session_key, session_key_source = _resolve_relayemo_session_key(
                route=route,
                payload=payload,
                request=request,
                request_scope_identity=request_scope_identity,
                scope_resolution_diagnostics=scope_resolution_diagnostics,
            )
            previous_assistant_state = None
            previous_state_found = False
            state_updated = True
            fallback_reason: str | None = None
            can_use_session_state = (
                config.relayemo_session_state_enabled and session_key is not None
            )
            if config.relayemo_session_state_enabled and session_key is None:
                state_updated = False
                fallback_reason = "session_key_unavailable"
            if can_use_session_state and session_key is not None:
                previous_assistant_state = load_session_assistant_state(
                    session_key,
                    ttl_seconds=config.relayemo_session_state_ttl_seconds,
                )
                previous_state_found = previous_assistant_state is not None
            relayemo_result = run_relayemo(
                config=config,
                messages=_extract_trace_messages(forwarded_payload),
                previous_assistant_state=previous_assistant_state,
            )
            relayemo_artifact = relayemo_result.artifact
            relayemo_artifact["session_state_enabled"] = config.relayemo_session_state_enabled
            relayemo_artifact["session_key_source"] = session_key_source
            relayemo_artifact["previous_state_found"] = previous_state_found
            relayemo_artifact["state_updated"] = state_updated
            relayemo_artifact["state_persisted"] = False
            relayemo_artifact["state_storage"] = "process_memory"
            if fallback_reason is not None:
                relayemo_artifact["fallback_reason"] = fallback_reason
            if can_use_session_state and session_key is not None:
                save_session_assistant_state(
                    session_key,
                    relayemo_result.assistant_state,
                    max_entries=config.relayemo_session_state_max_entries,
                )

'''
    source = _replace_once(source, old_block, new_block, "RelayEMO/RelaySCN request-path block")

    APP_PATH.write_text(source, encoding="utf-8")
    print("Applied P0 app.py ordering patch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
