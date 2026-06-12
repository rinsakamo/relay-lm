from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_unpack import (
    RELAYCTX_UPDATE_CLOSE,
    RELAYCTX_UPDATE_OPEN,
    unpack_relayctx_response_text,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _block(topic: str) -> str:
    envelope = {
        "schema_version": "relayctx_working_update.v0",
        "ctx_working_update": {"current_topic": topic},
    }
    return (
        f"{RELAYCTX_UPDATE_OPEN}\n"
        f"{json.dumps(envelope, ensure_ascii=False)}\n"
        f"{RELAYCTX_UPDATE_CLOSE}"
    )


def main() -> None:
    second_secret = "second internal update secret"
    text = f"可視本文。\n{_block('first')}\n{_block(second_secret)}"
    result = unpack_relayctx_response_text(text)
    require(result.status == "update_blocked", result)
    require(result.ctx_working_update is None, result)
    require("multiple_opening_markers" in result.blocked_reasons, result)
    require("embedded_closing_marker" in result.blocked_reasons, result)
    require(result.user_visible_text == "可視本文。", result)
    require(second_secret not in result.user_visible_text, result)
    require(RELAYCTX_UPDATE_OPEN not in result.user_visible_text, result)
    require(RELAYCTX_UPDATE_CLOSE not in result.user_visible_text, result)

    reversed_markers = (
        f"安全な本文。\n{RELAYCTX_UPDATE_CLOSE}\n"
        f"internal payload\n{RELAYCTX_UPDATE_OPEN}"
    )
    result = unpack_relayctx_response_text(reversed_markers)
    require(result.status == "update_blocked", result)
    require("closing_marker_before_opening" in result.blocked_reasons, result)
    require(result.user_visible_text == "安全な本文。", result)
    require("internal payload" not in result.user_visible_text, result)

    embedded_secret = "embedded close marker secret"
    result = unpack_relayctx_response_text(
        f"見える本文。\n{_block(f'safe {RELAYCTX_UPDATE_CLOSE} {embedded_secret}') }"
    )
    require(result.status == "update_blocked", result)
    require("embedded_closing_marker" in result.blocked_reasons, result)
    require(result.ctx_working_update is None, result)
    require(result.user_visible_text == "見える本文。", result)
    require(embedded_secret not in result.user_visible_text, result)

    unterminated_secret = "unterminated JSON tail secret"
    unterminated = (
        f"本文。\n{RELAYCTX_UPDATE_OPEN}\n"
        '{"schema_version":"relayctx_working_update.v0",'
        f'"ctx_working_update":{{"current_topic":"safe {RELAYCTX_UPDATE_CLOSE} '
        f'{unterminated_secret}"}}}}'
    )
    result = unpack_relayctx_response_text(unterminated)
    require(result.status == "update_blocked", result)
    require("update_json_invalid" in result.blocked_reasons, result)
    require(result.user_visible_text == "本文。", result)
    require(unterminated_secret not in result.user_visible_text, result)

    print(
        "ok RelayCTX Unpack suppresses repeated, reversed, and embedded internal markers"
    )


if __name__ == "__main__":
    main()
