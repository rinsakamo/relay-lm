from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_tts_adapter_handoff import (  # noqa: E402
    RelayCTXTTSAdapterHandoffPlan,
    build_relayctx_tts_adapter_handoff_node_result,
    build_tts_adapter_handoff_plan,
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


def ready_hint_result():
    return build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT,),
        enabled=True,
        dry_run_only=False,
        max_segment_chars=120,
        min_segment_chars=1,
    )


def dry_run_hint_result():
    return build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT,),
        enabled=True,
        dry_run_only=True,
        max_segment_chars=120,
        min_segment_chars=1,
    )


def blocked_hint_result():
    return build_tts_safe_segmentation_hints(
        (VISIBLE_TEXT + RELAYCTX_UPDATE_OPEN + INTERNAL_BODY,),
        enabled=True,
        dry_run_only=False,
    )


def invalid_hint_result():
    return build_tts_safe_segmentation_hints(
        (object(),),
        enabled=True,
        dry_run_only=False,
    )


def empty_hint_result():
    return build_tts_safe_segmentation_hints(
        ("",),
        enabled=True,
        dry_run_only=False,
    )


def assert_non_execution(plan: RelayCTXTTSAdapterHandoffPlan) -> None:
    require(plan.tts_execution_requested is False, plan)
    require(plan.audio_generation_requested is False, plan)
    require(plan.avatar_control_requested is False, plan)
    require(plan.persistence_allowed is False, plan)


def assert_content_free_projection(plan: RelayCTXTTSAdapterHandoffPlan) -> None:
    log = plan.to_log_dict()
    encoded = json.dumps(log, ensure_ascii=False)
    require(VISIBLE_TEXT not in encoded, encoded)
    require("これは表示" not in encoded, encoded)
    require(RELAYCTX_UPDATE_OPEN not in encoded, encoded)
    require(INTERNAL_BODY not in encoded, encoded)
    require("handoff_items" not in log, log)
    require("hints" not in log, log)
    require(log["visible_text_omitted"] is True, log)
    require(log["hint_array_omitted"] is True, log)
    require(log["handoff_items_omitted"] is True, log)
    node = build_relayctx_tts_adapter_handoff_node_result(plan)
    node_log = node.to_log_dict()
    node_encoded = json.dumps(node_log, ensure_ascii=False)
    require(VISIBLE_TEXT not in node_encoded, node_encoded)
    require(RELAYCTX_UPDATE_OPEN not in node_encoded, node_encoded)
    require(INTERNAL_BODY not in node_encoded, node_encoded)
    require("handoff_items" not in node_log["diagnostics"], node_log)
    require("hints" not in node_log["diagnostics"], node_log)


def assert_disabled_gate() -> None:
    plan = build_tts_adapter_handoff_plan(
        ready_hint_result(),
        enabled=False,
        dry_run_only=True,
    )
    require(plan.status == "disabled", plan)
    require(plan.handoff_candidate_count == 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    require(plan.handoff_items == (), plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok disabled gate emits no handoff")


def assert_dry_run_ready_from_ready_hints() -> None:
    plan = build_tts_adapter_handoff_plan(
        ready_hint_result(),
        enabled=True,
        dry_run_only=True,
    )
    require(plan.status == "dry_run_ready", plan)
    require(plan.handoff_candidate_count > 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    require(plan.handoff_items == (), plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok dry-run adapter handoff plans candidates without emission")


def assert_ready_from_ready_hints() -> None:
    plan = build_tts_adapter_handoff_plan(
        ready_hint_result(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "ready", plan)
    require(plan.handoff_candidate_count > 0, plan)
    require(plan.emitted_handoff_count == plan.handoff_candidate_count, plan)
    require(len(plan.handoff_items) == plan.emitted_handoff_count, plan)
    first_item = plan.handoff_items[0]
    require(first_item.content_free is True, first_item)
    require(first_item.char_count == first_item.end_char - first_item.start_char, first_item)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok ready adapter handoff emits runtime-private content-free items")


def assert_source_dry_run_stays_dry_run() -> None:
    plan = build_tts_adapter_handoff_plan(
        dry_run_hint_result(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "dry_run_ready", plan)
    require(plan.handoff_candidate_count > 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    require(plan.handoff_items == (), plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok source dry-run result cannot emit adapter handoff")


def assert_blocked_source_blocks_handoff() -> None:
    plan = build_tts_adapter_handoff_plan(
        blocked_hint_result(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "blocked", plan)
    require("source_blocked" in plan.blocked_reasons, plan)
    require(plan.handoff_candidate_count == 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok blocked source blocks adapter handoff")


def assert_invalid_source_fails_closed() -> None:
    plan = build_tts_adapter_handoff_plan(
        invalid_hint_result(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "invalid_input", plan)
    require("source_invalid_input" in plan.blocked_reasons, plan)
    require(plan.handoff_candidate_count == 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok invalid source fails closed")


def assert_empty_source_stays_empty() -> None:
    plan = build_tts_adapter_handoff_plan(
        empty_hint_result(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "empty_input", plan)
    require(plan.handoff_candidate_count == 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok empty source emits no handoff")


def assert_invalid_object_fails_closed() -> None:
    plan = build_tts_adapter_handoff_plan(
        object(),
        enabled=True,
        dry_run_only=False,
    )
    require(plan.status == "invalid_input", plan)
    require("invalid_hint_result" in plan.blocked_reasons, plan)
    require(plan.handoff_candidate_count == 0, plan)
    require(plan.emitted_handoff_count == 0, plan)
    assert_non_execution(plan)
    assert_content_free_projection(plan)
    print("ok non-hint-result input fails closed")


def main() -> None:
    assert_disabled_gate()
    assert_dry_run_ready_from_ready_hints()
    assert_ready_from_ready_hints()
    assert_source_dry_run_stays_dry_run()
    assert_blocked_source_blocks_handoff()
    assert_invalid_source_fails_closed()
    assert_empty_source_stays_empty()
    assert_invalid_object_fails_closed()


if __name__ == "__main__":
    main()
