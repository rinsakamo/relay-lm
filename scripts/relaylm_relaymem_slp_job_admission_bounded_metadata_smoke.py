"""Regression smoke for bounded Phase 6-A1 lineage metadata validation."""

from __future__ import annotations

from typing import Any

from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)


def _lineage(**overrides: Any) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": "turn",
        "namespace": "default",
        "valid": True,
        "lineage_fingerprint": "a" * 64,
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": True,
            "session_id_present": True,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }
    artifact.update(overrides)
    return artifact


def _admit(artifact: dict[str, Any]) -> dict[str, Any]:
    return build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id="run-1",
        turn_index=1,
        session_id="session-1",
        namespace="default",
        source_event_kind="turn",
        source_lineage_artifact=artifact,
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status="allowed",
    )


def _deep_mapping(depth: int) -> dict[str, Any]:
    root: dict[str, Any] = {}
    cursor = root
    for _ in range(depth):
        child: dict[str, Any] = {}
        cursor["nested"] = child
        cursor = child
    return root


def _deep_list(depth: int) -> list[Any]:
    root: list[Any] = []
    cursor = root
    for _ in range(depth):
        child: list[Any] = []
        cursor.append(child)
        cursor = child
    return root


def main() -> None:
    deep_shape: dict[str, Any] = {
        "source_event_id_present": True,
        "run_id_present": _deep_mapping(5000),
        "session_id_present": False,
        "turn_index_present": True,
    }
    shape_result = _admit(_lineage(lineage_shape=deep_shape))
    assert shape_result["admission_status"] == "blocked"
    assert shape_result["source_reference_valid"] is False
    assert "source_lineage_shape_invalid" in shape_result["blocked_reasons"]

    reasons_result = _admit(_lineage(blocked_reasons=_deep_list(5000)))
    assert reasons_result["admission_status"] == "blocked"
    assert reasons_result["source_reference_valid"] is False
    assert "source_lineage_blocked_reasons_invalid" in reasons_result[
        "blocked_reasons"
    ]

    numeric_flags = (
        ("content_free", 1, "source_lineage_not_content_free"),
        ("content_included", 0, "source_lineage_content_included"),
        ("raw_text_included", 0, "source_lineage_raw_text_included"),
        ("valid", 1, "source_lineage_invalid"),
    )
    for field, value, expected_reason in numeric_flags:
        result = _admit(_lineage(**{field: value}))
        assert result["admission_status"] == "blocked"
        assert result["source_reference_valid"] is False
        assert expected_reason in result["blocked_reasons"]

    print("RelayMEM RelaySLP bounded-metadata smoke passed")


if __name__ == "__main__":
    main()
