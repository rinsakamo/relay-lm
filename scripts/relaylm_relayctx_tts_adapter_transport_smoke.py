from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_tts_adapter_handoff import (  # noqa: E402
    build_tts_adapter_handoff_plan,
)
from relaylm.relayctx_tts_adapter_transport import (  # noqa: E402
    RelayCTXTTSAdapterTransportEnvelope,
    build_relayctx_tts_adapter_transport_node_result,
    build_tts_adapter_transport_envelope,
)
from relaylm.relayctx_tts_segmentation import (  # noqa: E402
    build_tts_safe_segmentation_hints,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN  # noqa: E402

VISIBLE_TEXT = "これは表示文です。次の文です！"
INTERNAL_BODY = '{"ctx_working_update":"private"}'


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def ready_handoff_plan():
    hint_result = build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT,),
        enabled=True,
        dry_run_only=False,
        max_segment_chars=120,
        min_segment_chars=1,
    )
    return build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=False,
    )


def dry_run_handoff_plan():
    hint_result = build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT,),
        enabled=True,
        dry_run_only=False,
        max_segment_chars=120,
        min_segment_chars=1,
    )
    return build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=True,
    )


def blocked_handoff_plan():
    hint_result = build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT + RELAYCTX_UPDATE_OPEN + INTERNAL_BODY,),
        enabled=True,
        dry_run_only=False,
    )
    return build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=False,
    )


def invalid_handoff_plan():
    hint_result = build_tts_safe_segmentation_hints(
        (object(),),
        enabled=True,
        dry_run_only=False,
    )
    return build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=False,
    )


def empty_handoff_plan():
    hint_result = build_tts_safe_segmentation_hints(
        ("",),
        enabled=True,
        dry_run_only=False,
    )
    return build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=False,
    )


def assert_non_execution(envelope: RelayCTXTTSAdapterTransportEnvelope) -> None:
    require(envelope.transport_delivery_requested is False, envelope)
    require(envelope.tts_execution_requested is False, envelope)
    require(envelope.audio_generation_requested is False, envelope)
    require(envelope.avatar_control_requested is False, envelope)
    require(envelope.persistence_allowed is False, envelope)


def assert_content_free_projection(envelope: RelayCTXTTSAdapterTransportEnvelope) -> None:
    log = envelope.to_log_dict()
    encoded = json.dumps(log, ensure_ascii=False)
    require(VISIBLE_TEXT not in encoded, encoded)
    require("これは表示" not in encoded, encoded)
    require(RELAYCTX_UPDATE_OPEN not in encoded, encoded)
    require(INTERNAL_BODY not in encoded, encoded)
    require("transport_items" not in log, log)
    require("handoff_items" not in log, log)
    require(log["visible_text_omitted"] is True, log)
    require(log["handoff_items_omitted"] is True, log)
    require(log["transport_items_omitted"] is True, log)
    require(log["external_io_performed"] is False, log)
    node = build_relayctx_tts_adapter_transport_node_result(envelope)
    node_log = node.to_log_dict()
    node_encoded = json.dumps(node_log, ensure_ascii=False)
    require(VISIBLE_TEXT not in node_encoded, node_encoded)
    require(RELAYCTX_UPDATE_OPEN not in node_encoded, node_encoded)
    require(INTERNAL_BODY not in node_encoded, node_encoded)
    require("transport_items" not in node_log["diagnostics"], node_log)
    require("handoff_items" not in node_log["diagnostics"], node_log)


def assert_disabled_gate() -> None:
    envelope = build_tts_adapter_transport_envelope(
        ready_handoff_plan(),
        enabled=False,
        dry_run_only=True,
    )
    require(envelope.status == "disabled", envelope)
    require(envelope.transport_candidate_count == 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    require(envelope.transport_items == (), envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok disabled transport gate emits no envelope items")


def assert_dry_run_ready_from_ready_handoff() -> None:
    envelope = build_tts_adapter_transport_envelope(
        ready_handoff_plan(),
        enabled=True,
        dry_run_only=True,
    )
    require(envelope.status == "dry_run_ready", envelope)
    require(envelope.transport_candidate_count > 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    require(envelope.transport_items == (), envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok dry-run transport plans candidates without emission")


def assert_ready_from_ready_handoff() -> None:
    envelope = build_tts_adapter_transport_envelope(
        ready_handoff_plan(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "ready", envelope)
    require(envelope.transport_candidate_count > 0, envelope)
    require(envelope.emitted_transport_count == envelope.transport_candidate_count, envelope)
    require(len(envelope.transport_items) == envelope.emitted_transport_count, envelope)
    first_item = envelope.transport_items[0]
    require(first_item.content_free is True, first_item)
    require(first_item.char_count == first_item.end_char - first_item.start_char, first_item)
    runtime_item = first_item.to_runtime_dict()
    runtime_encoded = json.dumps(runtime_item, ensure_ascii=False)
    require(VISIBLE_TEXT not in runtime_encoded, runtime_encoded)
    require("audio" not in runtime_item, runtime_item)
    require("avatar" not in runtime_item, runtime_item)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok ready transport emits runtime-private content-free items")


def assert_source_dry_run_stays_dry_run() -> None:
    envelope = build_tts_adapter_transport_envelope(
        dry_run_handoff_plan(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "dry_run_ready", envelope)
    require(envelope.transport_candidate_count > 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    require(envelope.transport_items == (), envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok source dry-run handoff cannot emit transport envelope items")


def assert_blocked_source_blocks_transport() -> None:
    envelope = build_tts_adapter_transport_envelope(
        blocked_handoff_plan(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "blocked", envelope)
    require("source_handoff_blocked" in envelope.blocked_reasons, envelope)
    require(envelope.transport_candidate_count == 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok blocked source blocks transport")


def assert_invalid_source_fails_closed() -> None:
    envelope = build_tts_adapter_transport_envelope(
        invalid_handoff_plan(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "invalid_input", envelope)
    require("source_handoff_invalid_input" in envelope.blocked_reasons, envelope)
    require(envelope.transport_candidate_count == 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok invalid source fails closed")


def assert_empty_source_stays_empty() -> None:
    envelope = build_tts_adapter_transport_envelope(
        empty_handoff_plan(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "empty_input", envelope)
    require(envelope.transport_candidate_count == 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok empty source emits no transport")


def assert_invalid_object_fails_closed() -> None:
    envelope = build_tts_adapter_transport_envelope(
        object(),
        enabled=True,
        dry_run_only=False,
    )
    require(envelope.status == "invalid_input", envelope)
    require("invalid_handoff_plan" in envelope.blocked_reasons, envelope)
    require(envelope.transport_candidate_count == 0, envelope)
    require(envelope.emitted_transport_count == 0, envelope)
    assert_non_execution(envelope)
    assert_content_free_projection(envelope)
    print("ok non-handoff input fails closed")


def main() -> None:
    assert_disabled_gate()
    assert_dry_run_ready_from_ready_handoff()
    assert_ready_from_ready_handoff()
    assert_source_dry_run_stays_dry_run()
    assert_blocked_source_blocks_transport()
    assert_invalid_source_fails_closed()
    assert_empty_source_stays_empty()
    assert_invalid_object_fails_closed()


if __name__ == "__main__":
    main()
