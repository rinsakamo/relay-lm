from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from tools.persistent_world_evidence import (
    HARD_AXES,
    PersistentWorldEvidenceError,
    validate_packet,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _identity(name: str) -> dict[str, object]:
    return {"id": name, "artifact_sha256": _sha(name), "metadata": {}}


def _record(
    rid: str,
    seq: int,
    kind: str,
    phase: str,
    channel: str,
    authority_domain: str,
    *,
    parents: list[str] | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": rid,
        "seq": seq,
        "kind": kind,
        "phase": phase,
        "provenance": {
            "channel": channel,
            "authority_domain": authority_domain,
            "emitter": f"fixture:{channel}",
            "artifact_sha256": _sha(rid),
        },
        "payload": {} if payload is None else payload,
        "causal_parents": [] if parents is None else parents,
    }


def _records() -> list[dict[str, object]]:
    return [
        _record(
            "d1obs", 1, "world_observation", "day1", "world_adapter", "minecraft_server",
            payload={"world_id": "home-world", "world_epoch": "epoch-0", "fact_key": "home.door.block", "value": "oak_door"},
        ),
        _record("d1echo", 2, "external_text", "day1", "external_message", "external_actor", payload={"content": "外、見てきて"}),
        _record("d1in", 3, "relay_input", "day1", "benchmark_harness", "benchmark_harness", parents=["d1obs", "d1echo"]),
        _record("d1out", 4, "model_output", "day1", "relaylm", "relaylm_inference", parents=["d1in"]),
        _record("p1", 5, "action_proposal", "day1", "benchmark_harness", "relaylm_inference", parents=["d1out"], payload={"action": "move_to", "target": "home.porch"}),
        _record("a1", 6, "action_authorization", "day1", "benchmark_harness", "benchmark_policy", parents=["p1"], payload={"decision": "allowed"}),
        _record("e1", 7, "action_execution", "day1", "world_adapter", "world_adapter_execution", parents=["a1"], payload={"status": "attempted"}),
        _record("o1", 8, "world_outcome", "day1", "world_adapter", "minecraft_server", parents=["e1"], payload={"status": "executed", "position": "home.porch"}),
        _record("snap", 9, "persistence_snapshot", "day1", "relaylm_runtime", "relaylm_persistence", payload={"profile_id": "rin", "subject_lineage_id": "rin-lineage-1"}),
        _record("stop", 10, "process_stop", "boundary", "benchmark_harness", "process_owner", payload={"components": ["relaylm", "actor_runtime", "body_adapter"]}),
        _record(
            "mut", 11, "world_mutation", "offline", "world_fixture_operator", "minecraft_server",
            payload={
                "world_id": "home-world",
                "fact_key": "home.door.block",
                "before_value": "oak_door",
                "after_value": "air",
                "before_epoch": "epoch-0",
                "after_epoch": "epoch-1",
            },
        ),
        _record("start", 12, "process_start", "boundary", "benchmark_harness", "process_owner", payload={"components": ["relaylm", "actor_runtime", "body_adapter"]}),
        _record(
            "ctx", 13, "context_reconstruction", "day2", "benchmark_harness", "benchmark_harness", parents=["start"],
            payload={"profile_id": "rin", "subject_lineage_id": "rin-lineage-1", "transcript_replayed": False},
        ),
        _record(
            "d2obs", 14, "world_observation", "day2", "world_adapter", "minecraft_server",
            payload={"world_id": "home-world", "world_epoch": "epoch-1", "fact_key": "home.door.block", "value": "air"},
        ),
        _record("d2echo", 15, "external_text", "day2", "external_message", "external_actor", payload={"content": "今日はどう？"}),
        _record("d2in", 16, "relay_input", "day2", "benchmark_harness", "benchmark_harness", parents=["d2obs", "d2echo"]),
        _record("d2out", 17, "model_output", "day2", "relaylm", "relaylm_inference", parents=["d2in"]),
        _record(
            "receipt", 18, "resource_receipt", "day2", "benchmark_harness", "process_owner",
            payload={
                "model_calls": 2,
                "cognition_cycles": 2,
                "actions": 1,
                "reduced_events": 5,
                "total_tokens": 1000,
                "wall_clock_ms": 10000,
            },
        ),
    ]


def _axes(*, provenance: str = "PASS") -> dict[str, dict[str, object]]:
    return {
        "restart_continuity": {"verdict": "PASS", "evidence_ids": ["snap", "stop", "start", "ctx", "d2in", "d2out"]},
        "past_present_world_separation": {"verdict": "PASS", "evidence_ids": ["d1obs", "mut", "d2obs", "d2out"]},
        "provenance_separation": {"verdict": provenance, "evidence_ids": [] if provenance != "PASS" else ["d1obs", "d1out", "p1", "a1", "o1"]},
        "action_outcome_separation": {"verdict": "PASS", "evidence_ids": ["p1", "a1", "e1", "o1"]},
        "no_hidden_transcript_replay": {"verdict": "PASS", "evidence_ids": ["start", "ctx", "d2in"]},
        "self_loop_bounded": {"verdict": "PASS", "evidence_ids": ["d1in", "d2in"]},
        "resource_budget_respected": {"verdict": "PASS", "evidence_ids": ["d1in", "d2in", "receipt"]},
    }


def _packet(*, run_class: str = "QUALIFICATION", transport: str = "source_preserving_event") -> dict[str, object]:
    qualification = run_class == "QUALIFICATION"
    identities: dict[str, object] = {
        "relaylm": _identity("relaylm-rc") if qualification else None,
        "profile": _identity("rin") if qualification else None,
        "world_fixture": _identity("home-world"),
        "harness": _identity("persistent-world-v2"),
        "model": _identity("gemma-4-12b") if qualification else None,
        "provider": _identity("openai-compatible") if qualification else None,
        "model_runtime": _identity("llama.cpp") if qualification else None,
        "hardware": _identity("rtx3060-host") if qualification else None,
        "minecraft_server": _identity("minecraft-java-26.1.2"),
        "body_adapter": _identity("mineflayer-4.39.0"),
    }
    packet = {
        "schema_version": 2,
        "run": {
            "run_id": "qual-1" if qualification else "lab-r0-c0",
            "run_class": run_class,
            "citable": qualification,
            "qualification_authority": qualification,
            "owner_issue": 3000 if qualification else 2896,
            "attempt": 1,
            "condition_sha256": _sha("condition"),
            "evidence_manifest_sha256": _sha("manifest"),
            "execution_frozen": qualification,
        },
        "identities": identities,
        "transport": {
            "mode": transport,
            "preserves_logical_origin": transport == "source_preserving_event",
        },
        "budget": {
            "max_model_calls": 4,
            "max_cognition_cycles": 4,
            "max_actions": 2,
            "max_reduced_events": 10,
            "max_total_tokens": 2000,
            "max_wall_clock_ms": 20000,
        },
        "counts": {
            "model_calls": 2,
            "cognition_cycles": 2,
            "actions": 1,
            "raw_events": 100,
            "reduced_events": 5,
            "benchmark_opportunities": 0,
            "total_tokens": 1000,
            "wall_clock_ms": 10000,
            "transcript_replayed": False,
        },
        "records": _records(),
        "axes": _axes(provenance="PASS" if transport == "source_preserving_event" else "INCONCLUSIVE"),
    }
    if not qualification:
        packet["records"] = [
            r for r in packet["records"]
            if r["kind"] in {"world_observation", "world_mutation", "process_stop", "process_start"}
        ]
        for i, record in enumerate(packet["records"], start=1):
            record["seq"] = i
        packet["counts"] = {
            "model_calls": 0,
            "cognition_cycles": 0,
            "actions": 0,
            "raw_events": 10,
            "reduced_events": 2,
            "benchmark_opportunities": 0,
            "total_tokens": None,
            "wall_clock_ms": None,
            "transcript_replayed": False,
        }
        packet["axes"] = {axis: {"verdict": "INCONCLUSIVE", "evidence_ids": []} for axis in HARD_AXES}
    return packet


def _get(packet: dict[str, object], rid: str) -> dict[str, object]:
    return next(r for r in packet["records"] if r["id"] == rid)


def test_valid_qualification_is_eligible_and_fingerprinted() -> None:
    normalized = validate_packet(_packet())
    assert normalized["qualification_eligible"] is True
    assert normalized["fingerprint"].startswith("sha256:")


def test_valid_exploratory_r0_is_non_citable_and_ineligible() -> None:
    normalized = validate_packet(_packet(run_class="EXPLORATORY_NON_CITABLE", transport="public_text_turn"))
    assert normalized["qualification_eligible"] is False
    assert normalized["run"]["citable"] is False


def test_schema_v1_is_rejected_before_shape_migration() -> None:
    packet = _packet()
    packet["schema_version"] = 1
    with pytest.raises(PersistentWorldEvidenceError, match="schema_version"):
        validate_packet(packet)


def test_unknown_top_level_field_fails_closed() -> None:
    packet = _packet()
    packet["hidden"] = "not fingerprinted"
    with pytest.raises(PersistentWorldEvidenceError, match="extra=.*hidden"):
        validate_packet(packet)


def test_unknown_record_field_fails_closed() -> None:
    packet = _packet()
    _get(packet, "d1obs")["hidden"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="keys must match schema exactly"):
        validate_packet(packet)


def test_unknown_provenance_field_fails_closed() -> None:
    packet = _packet()
    _get(packet, "d1obs")["provenance"]["trusted"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="keys must match schema exactly"):
        validate_packet(packet)


def test_exploratory_run_cannot_claim_citable_or_frozen() -> None:
    packet = _packet(run_class="EXPLORATORY_NON_CITABLE", transport="public_text_turn")
    packet["run"]["citable"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="exploratory run"):
        validate_packet(packet)


def test_qualification_requires_all_physical_identities() -> None:
    packet = _packet()
    packet["identities"]["hardware"] = None
    with pytest.raises(PersistentWorldEvidenceError, match="requires non-null identities"):
        validate_packet(packet)


def test_arbitrary_transport_mode_is_rejected() -> None:
    packet = _packet()
    packet["transport"]["mode"] = "magic_tunnel"
    with pytest.raises(PersistentWorldEvidenceError, match="transport.mode"):
        validate_packet(packet)


def test_public_text_cannot_claim_origin_preservation() -> None:
    packet = _packet(transport="public_text_turn")
    packet["transport"]["preserves_logical_origin"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="public_text_turn"):
        validate_packet(packet)


def test_public_text_cannot_claim_provenance_pass() -> None:
    packet = _packet(transport="public_text_turn")
    packet["axes"]["provenance_separation"] = {
        "verdict": "PASS",
        "evidence_ids": ["d1obs", "d1out", "p1", "a1", "o1"],
    }
    with pytest.raises(PersistentWorldEvidenceError, match="logical origin"):
        validate_packet(packet)


def test_world_mutation_requires_operator_channel() -> None:
    packet = _packet()
    _get(packet, "mut")["provenance"]["channel"] = "world_adapter"
    with pytest.raises(PersistentWorldEvidenceError, match="cannot be sourced"):
        validate_packet(packet)


def test_world_mutation_must_be_offline() -> None:
    packet = _packet()
    _get(packet, "mut")["phase"] = "day1"
    with pytest.raises(PersistentWorldEvidenceError):
        validate_packet(packet)


def test_day1_record_after_stop_is_rejected() -> None:
    packet = _packet()
    _get(packet, "snap")["seq"] = 10_000
    packet["records"].sort(key=lambda r: r["seq"])
    with pytest.raises(PersistentWorldEvidenceError, match="Day-1 records"):
        validate_packet(packet)


def test_qualification_stop_must_cover_relaylm_actor_and_body() -> None:
    packet = _packet()
    _get(packet, "stop")["payload"]["components"] = ["relaylm", "body_adapter"]
    _get(packet, "start")["payload"]["components"] = ["relaylm", "body_adapter"]
    with pytest.raises(PersistentWorldEvidenceError, match="actor_runtime"):
        validate_packet(packet)


def test_restart_continuity_requires_day2_context_and_io() -> None:
    packet = _packet()
    packet["axes"]["restart_continuity"]["evidence_ids"] = ["snap", "stop", "start", "d1in", "d1out"]
    with pytest.raises(PersistentWorldEvidenceError, match="Day2"):
        validate_packet(packet)


def test_subject_lineage_must_survive_restart() -> None:
    packet = _packet()
    _get(packet, "ctx")["payload"]["subject_lineage_id"] = "other-lineage"
    with pytest.raises(PersistentWorldEvidenceError, match="subject_lineage_id"):
        validate_packet(packet)


def test_past_present_pass_requires_same_fact_and_changed_value() -> None:
    packet = _packet()
    _get(packet, "d2obs")["payload"]["fact_key"] = "home.weather"
    with pytest.raises(PersistentWorldEvidenceError, match="same-fact"):
        validate_packet(packet)


def test_world_mutation_must_change_value_and_epoch() -> None:
    packet = _packet()
    _get(packet, "mut")["payload"]["after_value"] = "oak_door"
    with pytest.raises(PersistentWorldEvidenceError, match="change the declared fact"):
        validate_packet(packet)


def test_world_id_must_match_frozen_fixture_identity() -> None:
    packet = _packet()
    _get(packet, "d2obs")["payload"]["world_id"] = "other-world"
    with pytest.raises(PersistentWorldEvidenceError, match="world_fixture"):
        validate_packet(packet)


def test_mixed_action_chains_cannot_satisfy_axis() -> None:
    packet = _packet()
    records = packet["records"]
    receipt = records.pop()
    records.extend([
        _record("p2", 18, "action_proposal", "day2", "benchmark_harness", "relaylm_inference", parents=["d2out"]),
        _record("a2", 19, "action_authorization", "day2", "benchmark_harness", "benchmark_policy", parents=["p2"], payload={"decision": "allowed"}),
        _record("e2", 20, "action_execution", "day2", "world_adapter", "world_adapter_execution", parents=["a2"]),
        _record("o2", 21, "world_outcome", "day2", "world_adapter", "minecraft_server", parents=["e2"]),
    ])
    receipt["seq"] = 22
    receipt["payload"]["actions"] = 2
    records.append(receipt)
    packet["counts"]["actions"] = 2
    packet["counts"]["reduced_events"] = 6
    receipt["payload"]["reduced_events"] = 6
    packet["axes"]["action_outcome_separation"]["evidence_ids"] = ["p1", "a2", "e1", "o2"]
    with pytest.raises(PersistentWorldEvidenceError, match="complete cited"):
        validate_packet(packet)


def test_rejected_authorization_cannot_execute() -> None:
    packet = _packet()
    _get(packet, "a1")["payload"]["decision"] = "rejected"
    with pytest.raises(PersistentWorldEvidenceError, match="allowed authorization"):
        validate_packet(packet)


def test_endogenous_output_cannot_be_relabelled_world_observation() -> None:
    packet = _packet()
    output = _get(packet, "d1out")
    output["kind"] = "world_observation"
    with pytest.raises(PersistentWorldEvidenceError, match="cannot be sourced"):
        validate_packet(packet)


def test_relay_input_without_exogenous_or_budgeted_trigger_is_rejected() -> None:
    packet = _packet()
    _get(packet, "d2in")["causal_parents"] = ["ctx"]
    with pytest.raises(PersistentWorldEvidenceError, match="new exogenous information"):
        validate_packet(packet)


def test_cognition_cycle_underreport_is_rejected() -> None:
    packet = _packet()
    packet["counts"]["cognition_cycles"] = 1
    with pytest.raises(PersistentWorldEvidenceError, match="relay_input count"):
        validate_packet(packet)


def test_action_underreport_is_rejected() -> None:
    packet = _packet()
    packet["counts"]["actions"] = 0
    with pytest.raises(PersistentWorldEvidenceError, match="action_execution count"):
        validate_packet(packet)


def test_model_calls_cannot_be_lower_than_model_outputs() -> None:
    packet = _packet()
    packet["counts"]["model_calls"] = 1
    with pytest.raises(PersistentWorldEvidenceError, match="model_output count"):
        validate_packet(packet)


def test_resource_receipt_must_match_counts() -> None:
    packet = _packet()
    _get(packet, "receipt")["payload"]["total_tokens"] = 999
    with pytest.raises(PersistentWorldEvidenceError, match="total_tokens"):
        validate_packet(packet)


def test_resource_budget_pass_requires_tokens_and_wallclock() -> None:
    packet = _packet()
    packet["counts"]["total_tokens"] = None
    with pytest.raises(PersistentWorldEvidenceError, match="non-null counts.total_tokens|unknown or exceeded"):
        validate_packet(packet)


def test_resource_budget_excess_is_rejected_for_pass() -> None:
    packet = _packet()
    packet["counts"]["wall_clock_ms"] = 30000
    _get(packet, "receipt")["payload"]["wall_clock_ms"] = 30000
    with pytest.raises(PersistentWorldEvidenceError, match="exceeded"):
        validate_packet(packet)


def test_resource_pass_requires_receipt() -> None:
    packet = _packet()
    packet["records"] = [r for r in packet["records"] if r["id"] != "receipt"]
    packet["axes"]["resource_budget_respected"]["evidence_ids"] = ["d1in", "d2in"]
    with pytest.raises(PersistentWorldEvidenceError, match="resource_receipt"):
        validate_packet(packet)


def test_hidden_transcript_replay_cannot_pass() -> None:
    packet = _packet()
    packet["counts"]["transcript_replayed"] = True
    _get(packet, "ctx")["payload"]["transcript_replayed"] = True
    with pytest.raises(PersistentWorldEvidenceError, match="transcript_replayed"):
        validate_packet(packet)


def test_self_loop_axis_must_cite_all_cognition_inputs() -> None:
    packet = _packet()
    packet["axes"]["self_loop_bounded"]["evidence_ids"] = ["d1in"]
    with pytest.raises(PersistentWorldEvidenceError, match="all relay_input"):
        validate_packet(packet)


def test_fingerprint_is_stable_for_equivalent_packet() -> None:
    first = validate_packet(_packet())["fingerprint"]
    second = validate_packet(deepcopy(_packet()))["fingerprint"]
    assert first == second


def test_run_class_is_fingerprint_bound() -> None:
    packet = _packet()
    baseline = validate_packet(packet)["fingerprint"]
    changed = deepcopy(packet)
    changed["run"]["run_id"] = "qual-2"
    changed["run"]["condition_sha256"] = _sha("condition-2")
    assert validate_packet(changed)["fingerprint"] != baseline
