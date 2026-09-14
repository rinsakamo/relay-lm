"""Deterministic evidence validator for the Persistent WORLD Continuity Benchmark.

This module is repository-preparation support for #2888/#2894. It validates
machine-readable evidence only. It does not launch Minecraft, call a model,
judge natural-language quality, or grant product/Core authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

SCHEMA_VERSION = 1

HARD_AXES = (
    "restart_continuity",
    "past_present_world_separation",
    "provenance_separation",
    "action_outcome_separation",
    "no_hidden_transcript_replay",
    "self_loop_bounded",
    "resource_budget_respected",
)

VERDICTS = {"PASS", "FAIL", "INCONCLUSIVE"}

KIND_CHANNELS = {
    "world_observation": {"world_adapter"},
    "world_mutation": {"world_adapter"},
    "world_outcome": {"world_adapter"},
    "external_text": {"external_message"},
    "relay_input": {"benchmark_harness"},
    "model_output": {"relaylm"},
    "action_proposal": {"relaylm"},
    "action_authorization": {"benchmark_harness"},
    "action_execution": {"world_adapter"},
    "persistence_snapshot": {"relaylm_runtime"},
    "process_stop": {"benchmark_harness"},
    "process_start": {"benchmark_harness"},
}

KIND_PHASES = {
    "world_observation": {"day1", "day2"},
    "world_mutation": {"offline"},
    "world_outcome": {"day1", "day2"},
    "external_text": {"day1", "day2"},
    "relay_input": {"day1", "day2"},
    "model_output": {"day1", "day2"},
    "action_proposal": {"day1", "day2"},
    "action_authorization": {"day1", "day2"},
    "action_execution": {"day1", "day2"},
    "persistence_snapshot": {"day1"},
    "process_stop": {"boundary"},
    "process_start": {"boundary"},
}

SHA256_PREFIX = "sha256:"


class PersistentWorldEvidenceError(ValueError):
    """The retained benchmark evidence is malformed or causally inadmissible."""


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PersistentWorldEvidenceError(f"{name} must be an object")
    return value


def _require_nonempty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistentWorldEvidenceError(f"{name} must be a non-empty string")
    return value


def _require_sha256(value: object, name: str) -> str:
    text = _require_nonempty_string(value, name)
    if not text.startswith(SHA256_PREFIX) or len(text) != len(SHA256_PREFIX) + 64:
        raise PersistentWorldEvidenceError(
            f"{name} must be sha256:<64 lowercase hex chars>"
        )
    digest = text[len(SHA256_PREFIX) :]
    if digest.lower() != digest or any(
        ch not in "0123456789abcdef" for ch in digest
    ):
        raise PersistentWorldEvidenceError(
            f"{name} must be sha256:<64 lowercase hex chars>"
        )
    return text


def _require_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PersistentWorldEvidenceError(f"{name} must be a non-negative integer")
    return value


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return SHA256_PREFIX + hashlib.sha256(encoded).hexdigest()


def _normalize_identity(raw: object, name: str) -> dict[str, object]:
    value = _require_mapping(raw, name)
    result: dict[str, object] = {}
    for key in ("id", "artifact_sha256"):
        if key == "artifact_sha256":
            result[key] = _require_sha256(value.get(key), f"{name}.{key}")
        else:
            result[key] = _require_nonempty_string(value.get(key), f"{name}.{key}")
    metadata = value.get("metadata", {})
    result["metadata"] = dict(_require_mapping(metadata, f"{name}.metadata"))
    return result


def _normalize_transport(raw: object) -> dict[str, object]:
    value = _require_mapping(raw, "transport")
    mode = _require_nonempty_string(value.get("mode"), "transport.mode")
    preserves = value.get("preserves_logical_origin")
    if not isinstance(preserves, bool):
        raise PersistentWorldEvidenceError(
            "transport.preserves_logical_origin must be boolean"
        )
    if mode == "public_text_turn" and preserves:
        raise PersistentWorldEvidenceError(
            "public_text_turn cannot claim logical-origin preservation"
        )
    return {
        "mode": mode,
        "preserves_logical_origin": preserves,
    }


def _normalize_budget(raw: object) -> dict[str, int]:
    value = _require_mapping(raw, "budget")
    return {
        key: _require_nonnegative_int(value.get(key), f"budget.{key}")
        for key in (
            "max_model_calls",
            "max_cognition_cycles",
            "max_actions",
            "max_reduced_events",
        )
    }


def _normalize_counts(raw: object) -> dict[str, int | bool]:
    value = _require_mapping(raw, "counts")
    normalized: dict[str, int | bool] = {
        key: _require_nonnegative_int(value.get(key), f"counts.{key}")
        for key in (
            "model_calls",
            "cognition_cycles",
            "actions",
            "raw_events",
            "reduced_events",
            "untriggered_cognition_cycles",
        )
    }
    replayed = value.get("transcript_replayed")
    if not isinstance(replayed, bool):
        raise PersistentWorldEvidenceError("counts.transcript_replayed must be boolean")
    normalized["transcript_replayed"] = replayed
    if normalized["reduced_events"] > normalized["raw_events"]:
        raise PersistentWorldEvidenceError(
            "counts.reduced_events cannot exceed counts.raw_events"
        )
    return normalized


def _normalize_record(raw: object, index: int) -> dict[str, object]:
    value = _require_mapping(raw, f"records[{index}]")
    record_id = _require_nonempty_string(value.get("id"), f"records[{index}].id")
    seq = _require_nonnegative_int(value.get("seq"), f"records[{index}].seq")
    kind = _require_nonempty_string(value.get("kind"), f"records[{index}].kind")
    if kind not in KIND_CHANNELS:
        raise PersistentWorldEvidenceError(
            f"records[{index}].kind is unsupported: {kind}"
        )
    phase = _require_nonempty_string(value.get("phase"), f"records[{index}].phase")
    if phase not in KIND_PHASES[kind]:
        raise PersistentWorldEvidenceError(f"{kind} is not admissible in phase {phase}")
    provenance = _require_mapping(
        value.get("provenance"), f"records[{index}].provenance"
    )
    channel = _require_nonempty_string(
        provenance.get("channel"), f"records[{index}].provenance.channel"
    )
    if channel not in KIND_CHANNELS[kind]:
        raise PersistentWorldEvidenceError(
            f"{kind} cannot be sourced from provenance channel {channel}"
        )
    emitter = _require_nonempty_string(
        provenance.get("emitter"), f"records[{index}].provenance.emitter"
    )
    artifact_sha256 = _require_sha256(
        provenance.get("artifact_sha256"),
        f"records[{index}].provenance.artifact_sha256",
    )
    payload = dict(
        _require_mapping(value.get("payload", {}), f"records[{index}].payload")
    )
    parent = value.get("causal_parent")
    if parent is not None:
        parent = _require_nonempty_string(parent, f"records[{index}].causal_parent")
    return {
        "id": record_id,
        "seq": seq,
        "kind": kind,
        "phase": phase,
        "provenance": {
            "channel": channel,
            "emitter": emitter,
            "artifact_sha256": artifact_sha256,
        },
        "payload": payload,
        "causal_parent": parent,
    }


def _index_records(
    records: Sequence[dict[str, object]],
) -> dict[str, dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {}
    previous_seq = -1
    seen_seq: set[int] = set()
    for record in records:
        record_id = record["id"]
        assert isinstance(record_id, str)
        seq = record["seq"]
        assert isinstance(seq, int)
        if record_id in by_id:
            raise PersistentWorldEvidenceError(f"duplicate record id: {record_id}")
        if seq in seen_seq:
            raise PersistentWorldEvidenceError(f"duplicate record seq: {seq}")
        if seq <= previous_seq:
            raise PersistentWorldEvidenceError(
                "records must be strictly ordered by increasing seq"
            )
        by_id[record_id] = record
        seen_seq.add(seq)
        previous_seq = seq
    return by_id


def _require_kind(
    by_id: Mapping[str, dict[str, object]],
    record_id: str,
    expected: str,
    context: str,
) -> dict[str, object]:
    try:
        record = by_id[record_id]
    except KeyError as exc:
        raise PersistentWorldEvidenceError(
            f"{context} references missing record: {record_id}"
        ) from exc
    if record["kind"] != expected:
        raise PersistentWorldEvidenceError(
            f"{context} requires {expected}, got {record['kind']}"
        )
    return record


def _require_causal_parent(
    record: Mapping[str, object],
    by_id: Mapping[str, dict[str, object]],
    expected_kind: str,
) -> dict[str, object]:
    parent = record.get("causal_parent")
    record_id = str(record.get("id"))
    if not isinstance(parent, str):
        raise PersistentWorldEvidenceError(f"{record_id} must reference a causal_parent")
    parent_record = _require_kind(by_id, parent, expected_kind, record_id)
    parent_seq = parent_record["seq"]
    seq = record["seq"]
    assert isinstance(parent_seq, int) and isinstance(seq, int)
    if parent_seq >= seq:
        raise PersistentWorldEvidenceError(f"{record_id} causal_parent must precede child")
    return parent_record


def _validate_lifecycle(
    records: Sequence[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    stops = [record for record in records if record["kind"] == "process_stop"]
    starts = [record for record in records if record["kind"] == "process_start"]
    mutations = [record for record in records if record["kind"] == "world_mutation"]
    if len(stops) != 1 or len(starts) != 1 or not mutations:
        raise PersistentWorldEvidenceError(
            "packet requires exactly one process_stop, exactly one process_start, "
            "and at least one offline world_mutation"
        )
    stop = stops[0]
    start = starts[0]
    stop_seq = stop["seq"]
    start_seq = start["seq"]
    assert isinstance(stop_seq, int) and isinstance(start_seq, int)
    if stop_seq >= start_seq:
        raise PersistentWorldEvidenceError("process_stop must precede process_start")
    for mutation in mutations:
        seq = mutation["seq"]
        assert isinstance(seq, int)
        if not stop_seq < seq < start_seq:
            raise PersistentWorldEvidenceError(
                "WORLD mutation must occur while cognition is stopped"
            )
    day2_obs = [
        record
        for record in records
        if record["kind"] == "world_observation" and record["phase"] == "day2"
    ]
    if not day2_obs:
        raise PersistentWorldEvidenceError(
            "packet requires at least one fresh Day-2 WORLD observation"
        )
    first_day2_seq = day2_obs[0]["seq"]
    assert isinstance(first_day2_seq, int)
    if first_day2_seq <= start_seq:
        raise PersistentWorldEvidenceError(
            "Day-2 WORLD observation must follow process restart"
        )
    latest_mutation = max(int(record["seq"]) for record in mutations)
    if first_day2_seq <= latest_mutation:
        raise PersistentWorldEvidenceError(
            "Day-2 WORLD observation must follow offline WORLD mutation"
        )
    return stop, start, day2_obs[0]


def _validate_action_chains(
    records: Sequence[dict[str, object]],
    by_id: Mapping[str, dict[str, object]],
) -> None:
    for record in records:
        kind = record["kind"]
        if kind == "action_authorization":
            _require_causal_parent(record, by_id, "action_proposal")
        elif kind == "action_execution":
            _require_causal_parent(record, by_id, "action_authorization")
        elif kind == "world_outcome":
            _require_causal_parent(record, by_id, "action_execution")


def _normalize_axes(
    raw: object,
    by_id: Mapping[str, dict[str, object]],
    *,
    transport_preserves_origin: bool,
    counts: Mapping[str, int | bool],
    budget: Mapping[str, int],
) -> dict[str, dict[str, object]]:
    value = _require_mapping(raw, "axes")
    if set(value) != set(HARD_AXES):
        missing = sorted(set(HARD_AXES) - set(value))
        extra = sorted(set(value) - set(HARD_AXES))
        raise PersistentWorldEvidenceError(
            f"axes must exactly match hard axes; missing={missing}, extra={extra}"
        )
    normalized: dict[str, dict[str, object]] = {}
    for axis in HARD_AXES:
        raw_axis = _require_mapping(value[axis], f"axes.{axis}")
        verdict = _require_nonempty_string(
            raw_axis.get("verdict"), f"axes.{axis}.verdict"
        )
        if verdict not in VERDICTS:
            raise PersistentWorldEvidenceError(
                f"axes.{axis}.verdict must be one of {sorted(VERDICTS)}"
            )
        evidence = raw_axis.get("evidence_ids")
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item for item in evidence
        ):
            raise PersistentWorldEvidenceError(
                f"axes.{axis}.evidence_ids must be a list of record ids"
            )
        if verdict == "PASS" and not evidence:
            raise PersistentWorldEvidenceError(
                f"axes.{axis} cannot PASS without evidence"
            )
        for record_id in evidence:
            if record_id not in by_id:
                raise PersistentWorldEvidenceError(
                    f"axes.{axis} references missing evidence: {record_id}"
                )
        normalized[axis] = {
            "verdict": verdict,
            "evidence_ids": list(evidence),
        }

    if (
        normalized["provenance_separation"]["verdict"] == "PASS"
        and not transport_preserves_origin
    ):
        raise PersistentWorldEvidenceError(
            "provenance_separation cannot PASS when transport does not preserve logical origin"
        )
    if (
        normalized["no_hidden_transcript_replay"]["verdict"] == "PASS"
        and counts["transcript_replayed"] is not False
    ):
        raise PersistentWorldEvidenceError(
            "no_hidden_transcript_replay cannot PASS when transcript_replayed=true"
        )
    if (
        normalized["self_loop_bounded"]["verdict"] == "PASS"
        and counts["untriggered_cognition_cycles"] != 0
    ):
        raise PersistentWorldEvidenceError(
            "self_loop_bounded cannot PASS with untriggered cognition cycles"
        )

    within_budget = (
        int(counts["model_calls"]) <= budget["max_model_calls"]
        and int(counts["cognition_cycles"]) <= budget["max_cognition_cycles"]
        and int(counts["actions"]) <= budget["max_actions"]
        and int(counts["reduced_events"]) <= budget["max_reduced_events"]
    )
    if normalized["resource_budget_respected"]["verdict"] == "PASS" and not within_budget:
        raise PersistentWorldEvidenceError(
            "resource_budget_respected cannot PASS when declared counts exceed budget"
        )
    return normalized


def _require_axis_evidence_shapes(
    axes: Mapping[str, Mapping[str, object]],
    by_id: Mapping[str, dict[str, object]],
) -> None:
    def kinds(axis: str) -> set[str]:
        evidence = axes[axis]["evidence_ids"]
        assert isinstance(evidence, list)
        return {str(by_id[record_id]["kind"]) for record_id in evidence}

    if axes["restart_continuity"]["verdict"] == "PASS":
        required = {
            "persistence_snapshot",
            "process_stop",
            "process_start",
            "relay_input",
            "model_output",
        }
        if not required.issubset(kinds("restart_continuity")):
            raise PersistentWorldEvidenceError(
                "restart_continuity PASS requires persistence/stop/start/input/output evidence"
            )
    if axes["past_present_world_separation"]["verdict"] == "PASS":
        required = {"world_observation", "world_mutation", "model_output"}
        if not required.issubset(kinds("past_present_world_separation")):
            raise PersistentWorldEvidenceError(
                "past_present_world_separation PASS requires observation/mutation/model-output evidence"
            )
    if axes["provenance_separation"]["verdict"] == "PASS":
        required = {"world_observation", "external_text", "model_output"}
        if not required.issubset(kinds("provenance_separation")):
            raise PersistentWorldEvidenceError(
                "provenance_separation PASS requires WORLD/external/model evidence"
            )
    if axes["action_outcome_separation"]["verdict"] == "PASS":
        required = {
            "action_proposal",
            "action_authorization",
            "action_execution",
            "world_outcome",
        }
        if not required.issubset(kinds("action_outcome_separation")):
            raise PersistentWorldEvidenceError(
                "action_outcome_separation PASS requires proposal/authorization/execution/outcome evidence"
            )


def validate_packet(raw: Mapping[str, object]) -> dict[str, object]:
    """Validate and normalize one retained Persistent WORLD evidence packet."""

    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise PersistentWorldEvidenceError(
            f"schema_version must be exactly {SCHEMA_VERSION}"
        )

    relaylm = _normalize_identity(raw.get("relaylm"), "relaylm")
    profile = _normalize_identity(raw.get("profile"), "profile")
    world = _normalize_identity(raw.get("world"), "world")
    harness = _normalize_identity(raw.get("harness"), "harness")
    transport = _normalize_transport(raw.get("transport"))
    budget = _normalize_budget(raw.get("budget"))
    counts = _normalize_counts(raw.get("counts"))

    raw_records = raw.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise PersistentWorldEvidenceError("records must be a non-empty list")
    records = [
        _normalize_record(item, index) for index, item in enumerate(raw_records)
    ]
    by_id = _index_records(records)
    _validate_lifecycle(records)
    _validate_action_chains(records, by_id)

    axes = _normalize_axes(
        raw.get("axes"),
        by_id,
        transport_preserves_origin=bool(transport["preserves_logical_origin"]),
        counts=counts,
        budget=budget,
    )
    _require_axis_evidence_shapes(axes, by_id)

    normalized: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "relaylm": relaylm,
        "profile": profile,
        "world": world,
        "harness": harness,
        "transport": transport,
        "budget": budget,
        "counts": counts,
        "records": records,
        "axes": axes,
    }
    normalized["fingerprint"] = _canonical_sha256(normalized)
    return normalized


def _load_packet(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PersistentWorldEvidenceError(f"cannot load evidence packet: {exc}") from exc
    return _require_mapping(value, "packet")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Persistent WORLD Continuity Benchmark evidence packet."
    )
    parser.add_argument("--packet", required=True, type=Path)
    return parser.parse_args(list(sys.argv[1:] if argv is None else argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        normalized = validate_packet(_load_packet(args.packet))
    except PersistentWorldEvidenceError as exc:
        print(f"persistent WORLD evidence blocked: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "status": "VALID",
                "schema_version": normalized["schema_version"],
                "fingerprint": normalized["fingerprint"],
                "axes": normalized["axes"],
            },
            sort_keys=True,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
