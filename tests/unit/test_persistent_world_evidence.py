from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from tools.persistent_world_evidence import (
    PersistentWorldEvidenceError,
    validate_packet,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(
    record_id: str,
    seq: int,
    kind: str,
    phase: str,
    channel: str,
    *,
    parent: str | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": record_id,
        "seq": seq,
        "kind": kind,
        "phase": phase,
        "provenance": {
            "channel": channel,
            "emitter": f"fixture:{channel}",
            "artifact_sha256": _sha(record_id),
        },
        "payload": {} if payload is None else payload,
        "causal_parent": parent,
    }


def _packet(*, public_text_transport: bool = False) -> dict[str, object]:
    records = [
        _record("d1obs", 1, "world_observation", "day1", "world_adapter"),
        _record("d1echo", 2, "external_text", "day1", "external_message"),
        _record("d1in", 3, "relay_input", "day1", "benchmark_harness"),
        _record("d1out", 4, "model_output", "day1", "relaylm"),
        _record("p1", 5, "action_proposal", "day1", "relaylm"),
        _record(
            "a1",
            6,
            "action_authorization",
            "day1",
            "benchmark_harness",
            parent="p1",
        ),
        _record(
            "e1",
            7,
            "action_execution",
            "day1",
            "world_adapter",
            parent="a1",
        ),
        _record(
            "o1",
            8,
            "world_outcome",
            "day1",
            "world_adapter",
            parent="e1",
        ),
        _record(
            "snap",
            9,
            "persistence_snapshot",
            "day1",
            "relaylm_runtime",
        ),
        _record("stop", 10, "process_stop", "boundary", "benchmark_harness"),
        _record("mut", 11, "world_mutation", "offline", "world_adapter"),
        _record("start", 12, "process_start", "boundary", "benchmark_harness"),
        _record("d2obs", 13, "world_observation", "day2", "world_adapter"),
        _record("d2echo", 14, "external_text", "day2", "external_message"),
        _record("d2in", 15, "relay_input", "day2", "benchmark_harness"),
        _record("d2out", 16, "model_output", "day2", "relaylm"),
    ]
    provenance_verdict = "INCONCLUSIVE" if public_text_transport else "PASS"
    provenance_evidence = [] if public_text_transport else ["d1obs", "d1echo", "d1out"]
    return {
        "schema_version": 1,
        "relaylm": {
            "id": "relaylm-rc",
            "artifact_sha256": _sha("relaylm"),
            "metadata": {"version": "1.0.0-rc"},
        },
        "profile": {
            "id": "rin",
            "artifact_sha256": _sha("profile"),
            "metadata": {},
        },
        "world": {
            "id": "home-world-epoch-1",
            "artifact_sha256": _sha("world"),
            "metadata": {"save": "home"},
        },
        "harness": {
            "id": "persistent-world-v0",
            "artifact_sha256": _sha("harness"),
            "metadata": {},
        },
        "transport": {
            "mode": "public_text_turn" if public_text_transport else "generic_event",
            "preserves_logical_origin": not public_text_transport,
        },
        "budget": {
            "max_model_calls": 10,
            "max_cognition_cycles": 10,
            "max_actions": 2,
            "max_reduced_events": 20,
        },
        "counts": {
            "model_calls": 4,
            "cognition_cycles": 4,
            "actions": 1,
            "raw_events": 100,
            "reduced_events": 8,
            "untriggered_cognition_cycles": 0,
            "transcript_replayed": False,
        },
        "records": records,
        "axes": {
            "restart_continuity": {
                "verdict": "PASS",
                "evidence_ids": ["snap", "stop", "start", "d2in", "d2out"],
            },
            "past_present_world_separation": {
                "verdict": "PASS",
                "evidence_ids": ["d1obs", "mut", "d2obs", "d2out"],
            },
            "provenance_separation": {
                "verdict": provenance_verdict,
                "evidence_ids": provenance_evidence,
            },
            "action_outcome_separation": {
                "verdict": "PASS",
                "evidence_ids": ["p1", "a1", "e1", "o1"],
            },
            "no_hidden_transcript_replay": {
                "verdict": "PASS",
                "evidence_ids": ["stop", "start", "d2in"],
            },
            "self_loop_bounded": {
                "verdict": "PASS",
                "evidence_ids": ["d1in", "d1out", "d2in", "d2out"],
            },
            "resource_budget_respected": {
                "verdict": "PASS",
                "evidence_ids": ["d1in", "d2in"],
            },
        },
    }


def test_valid_packet_normalizes_and_fingerprints() -> None:
    normalized = validate_packet(_packet())
    assert normalized["fingerprint"].startswith("sha256:")
    assert normalized["axes"]["provenance_separation"]["verdict"] == "PASS"


def test_public_text_transport_must_not_claim_provenance_pass() -> None:
    packet = _packet(public_text_transport=True)
    normalized = validate_packet(packet)
    assert normalized["axes"]["provenance_separation"]["verdict"] == "INCONCLUSIVE"

    packet["axes"]["provenance_separation"] = {
        "verdict": "PASS",
        "evidence_ids": ["d1obs", "d1echo", "d1out"],
    }
    with pytest.raises(PersistentWorldEvidenceError, match="logical origin"):
        validate_packet(packet)


def test_world_mutation_must_be_offline() -> None:
    packet = _packet()
    mutation = next(item for item in packet["records"] if item["id"] == "mut")
    mutation["seq"] = 9
    snapshot = next(item for item in packet["records"] if item["id"] == "snap")
    snapshot["seq"] = 11
    packet["records"].sort(key=lambda item: item["seq"])
    with pytest.raises(PersistentWorldEvidenceError, match="while cognition is stopped"):
        validate_packet(packet)


def test_day2_observation_must_follow_restart() -> None:
    packet = _packet()
    start = next(item for item in packet["records"] if item["id"] == "start")
    d2obs = next(item for item in packet["records"] if item["id"] == "d2obs")
    start["seq"], d2obs["seq"] = d2obs["seq"], start["seq"]
    packet["records"].sort(key=lambda item: item["seq"])
    with pytest.raises(PersistentWorldEvidenceError, match="follow process restart"):
        validate_packet(packet)


def test_endogenous_output_cannot_be_relabelled_as_world_observation() -> None:
    packet = _packet()
    output = next(item for item in packet["records"] if item["id"] == "d1out")
    output["kind"] = "world_observation"
    with pytest.raises(PersistentWorldEvidenceError, match="cannot be sourced"):
        validate_packet(packet)


def test_narrated_success_without_external_outcome_cannot_pass() -> None:
    packet = _packet()
    packet["records"] = [item for item in packet["records"] if item["id"] != "o1"]
    with pytest.raises(PersistentWorldEvidenceError, match="missing evidence"):
        validate_packet(packet)


def test_action_parent_chain_is_enforced() -> None:
    packet = _packet()
    execution = next(item for item in packet["records"] if item["id"] == "e1")
    execution["causal_parent"] = "p1"
    with pytest.raises(PersistentWorldEvidenceError, match="requires action_authorization"):
        validate_packet(packet)


def test_hidden_transcript_replay_cannot_pass() -> None:
    packet = _packet()
    packet["counts"]["transcript_replayed"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="transcript_replayed"):
        validate_packet(packet)


def test_untriggered_self_loop_cannot_pass() -> None:
    packet = _packet()
    packet["counts"]["untriggered_cognition_cycles"] = 1
    with pytest.raises(PersistentWorldEvidenceError, match="untriggered cognition"):
        validate_packet(packet)


def test_event_flood_over_budget_cannot_pass() -> None:
    packet = _packet()
    packet["counts"]["reduced_events"] = 21
    with pytest.raises(PersistentWorldEvidenceError, match="counts exceed budget"):
        validate_packet(packet)


def test_pass_axis_cannot_reference_missing_evidence() -> None:
    packet = _packet()
    packet["axes"]["restart_continuity"]["evidence_ids"].append("missing")
    with pytest.raises(PersistentWorldEvidenceError, match="missing evidence"):
        validate_packet(packet)


def test_fingerprint_is_stable_for_equivalent_input() -> None:
    first = validate_packet(_packet())["fingerprint"]
    second = validate_packet(deepcopy(_packet()))["fingerprint"]
    assert first == second
