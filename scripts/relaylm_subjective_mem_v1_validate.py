#!/usr/bin/env python3
"""Validate Shared Assessment / Subjective MEM v1 fixtures."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json"
CATALOG_PATH = ROOT / "docs/contracts/schemas/subjective-mem-v1/schema-catalog.json"
VALID_DIR = ROOT / "docs/contracts/fixtures/subjective-mem-v1/valid"
INVALID_DIR = ROOT / "docs/contracts/fixtures/subjective-mem-v1/invalid"

SCHEMA_TO_DEF = {
    "relaylm.shared_assessment_revision.v1": "SharedAssessmentRevision",
    "relaylm.shared_assessment_current_state.v1": "SharedAssessmentCurrentState",
    "relaylm.subjective_mem_decision.v1": "SubjectiveMemDecision",
    "relaylm.subjective_mem_revision.v1": "SubjectiveMemRevision",
    "relaylm.subjective_mem_current_state.v1": "SubjectiveMemCurrentState",
    "relaylm.subjective_mem_relation.v1": "SubjectiveMemRelation",
    "relaylm.subjective_mem_lifecycle_transition.v1": "SubjectiveMemLifecycleTransition",
}

ALL_ERROR_IDS = set(
    """
SUBJ_MEM_E_SCHEMA_INVALID
SUBJ_MEM_E_DUPLICATE_TOP_LEVEL_ID
SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE
SUBJ_MEM_E_DUPLICATE_MEMORY_CURRENT_STATE
SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH
SUBJ_MEM_E_ASSESSMENT_REVISION_DANGLING
SUBJ_MEM_E_ASSESSMENT_CURRENT_MISSING
SUBJ_MEM_E_ASSESSMENT_AUTHORIZATION_NOT_CURRENT
SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH
SUBJ_MEM_E_ASSESSMENT_SUPERSESSION_INVALID
SUBJ_MEM_E_DECISION_ASSESSMENT_DANGLING
SUBJ_MEM_E_DECISION_ASSESSMENT_RECEIPT_INVALID
SUBJ_MEM_E_DECISION_TARGET_REQUIRED
SUBJ_MEM_E_DECISION_TARGET_FORBIDDEN
SUBJ_MEM_E_DECISION_RESULT_MEMORY_REQUIRED
SUBJ_MEM_E_DECISION_RESULT_RELATION_REQUIRED
SUBJ_MEM_E_DECISION_RESULT_FORBIDDEN
SUBJ_MEM_E_DECISION_HOLD_REASON_REQUIRED
SUBJ_MEM_E_DECISION_HOLD_REASON_FORBIDDEN
SUBJ_MEM_E_DECISION_TARGET_DANGLING
SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT
SUBJ_MEM_E_DECISION_TARGET_CHARACTER_MISMATCH
SUBJ_MEM_E_DECISION_TARGET_SCOPE_MISMATCH
SUBJ_MEM_E_DECISION_TARGET_NOT_CANDIDATE
SUBJ_MEM_E_DECISION_CANDIDATE_DANGLING
SUBJ_MEM_E_DECISION_CANDIDATE_NOT_AVAILABLE
SUBJ_MEM_E_DECISION_CANDIDATE_CHARACTER_MISMATCH
SUBJ_MEM_E_DECISION_CANDIDATE_SCOPE_MISMATCH
SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING
SUBJ_MEM_E_DECISION_RESULT_CHARACTER_MISMATCH
SUBJ_MEM_E_DECISION_RESULT_SCOPE_MISMATCH
SUBJ_MEM_E_DECISION_RESULT_ASSESSMENT_MISMATCH
SUBJ_MEM_E_DECISION_RESULT_LINK_INVALID
SUBJ_MEM_E_DECISION_RELATION_LINK_INVALID
SUBJ_MEM_E_DECISION_RELATION_CANDIDATE_MISMATCH
SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED
SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT
SUBJ_MEM_E_SCOPE_SNAPSHOT_MISMATCH
SUBJ_MEM_E_MEM_ASSESSMENT_DANGLING
SUBJ_MEM_E_GROUNDED_DIGEST_MISMATCH
SUBJ_MEM_E_MEM_PREDECESSOR_INVALID
SUBJ_MEM_E_MEM_AUTHORIZATION_INVALID
SUBJ_MEM_E_MEM_RETRIEVAL_VISIBILITY_INVALID
SUBJ_MEM_E_MEM_CURRENT_MISSING
SUBJ_MEM_E_MEM_CURRENT_DANGLING
SUBJ_MEM_E_MEM_CURRENT_MISMATCH
SUBJ_MEM_E_MEM_RETRIEVAL_ELIGIBILITY_INVALID
SUBJ_MEM_E_RELATION_SOURCE_DANGLING
SUBJ_MEM_E_RELATION_TARGET_DANGLING
SUBJ_MEM_E_RELATION_SELF_REFERENCE
SUBJ_MEM_E_RELATION_CHARACTER_MISMATCH
SUBJ_MEM_E_RELATION_SCOPE_MISMATCH
SUBJ_MEM_E_RELATION_AUTHORIZATION_INVALID
SUBJ_MEM_E_RELATION_CYCLE
SUBJ_MEM_E_TRANSITION_FROM_DANGLING
SUBJ_MEM_E_TRANSITION_TO_DANGLING
SUBJ_MEM_E_TRANSITION_REVISION_INVALID
SUBJ_MEM_E_TRANSITION_CHARACTER_MISMATCH
SUBJ_MEM_E_TRANSITION_STATE_INVALID
SUBJ_MEM_E_TRANSITION_STAGE_INVALID
SUBJ_MEM_E_TRANSITION_AUTHORITY_INVALID
SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION
SUBJ_MEM_E_TIME_ORDER_INVALID
""".split()
)

TARGET_REQUIRED_OUTCOMES = {"reinforce", "refine", "reinterpret", "supersede", "contradict", "relate"}
TARGET_FORBIDDEN_OUTCOMES = {"create", "hold", "abstain", "leave_as_evidence"}
MEMORY_RESULT_OUTCOMES = {"create", "reinforce", "refine", "reinterpret", "supersede", "contradict"}
NO_RESULT_OUTCOMES = {"hold", "abstain", "leave_as_evidence"}
VISIBLE_LIFECYCLES = {"active", "pinned"}
SUCCESSOR_RELATIONS = {"supersedes", "reinterprets"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def memory_ref_key(ref: dict[str, Any] | None) -> tuple[Any, Any]:
    ref = ref or {}
    return ref.get("memory_id"), ref.get("memory_revision")


def set_path(value: Any, path: list[Any], replacement: Any) -> None:
    cursor = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


def apply_mutations(records: list[dict[str, Any]], mutations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = copy.deepcopy(records)
    for mutation in mutations:
        operation = mutation["op"]
        if operation == "set":
            set_path(result[mutation["record_index"]], mutation["path"], copy.deepcopy(mutation["value"]))
        elif operation == "append_copy":
            result.append(copy.deepcopy(result[mutation["record_index"]]))
        elif operation == "append_record":
            result.append(copy.deepcopy(mutation["record"]))
        elif operation == "delete":
            del result[mutation["record_index"]]
        else:
            raise ValueError(f"unsupported fixture mutation op: {operation}")
    return result


def fixture_base(payload: dict[str, Any], fixture_path: Path) -> list[dict[str, Any]]:
    if "base_records" in payload:
        return copy.deepcopy(payload["base_records"])
    referenced = load_json((fixture_path.parent / payload["base_fixture"]).resolve())
    return copy.deepcopy(referenced["base_records"])


def materialize_case(payload: dict[str, Any], case: dict[str, Any], fixture_path: Path) -> list[dict[str, Any]]:
    records = copy.deepcopy(case["records"]) if "records" in case else fixture_base(payload, fixture_path)
    if "record_indices" in case:
        records = [records[index] for index in case["record_indices"]]
    return apply_mutations(records, case.get("mutations", []))


def scope_consistent(scope: dict[str, Any]) -> bool:
    kind = scope.get("scope_kind")
    participant = scope.get("participant_id_or_null")
    relationship = scope.get("relationship_id_or_null")
    scene = scope.get("scene_id_or_null")
    audience = scope.get("audience_class")
    return (
        (kind == "character_private" and participant is None and relationship is None and scene is None and audience == "private")
        or (kind == "participant" and participant is not None and relationship is None and scene is None and audience == "trusted_participant")
        or (kind == "relationship" and participant is not None and relationship is not None and scene is None and audience == "relationship_bounded")
        or (kind == "scene" and relationship is None and scene is not None and audience == "scene_bounded")
    )


def scope_snapshot_consistent(memory: dict[str, Any]) -> bool:
    kind = memory["scope_binding"]["scope_kind"]
    snapshot = memory["formation_snapshot"]
    if kind == "relationship" and snapshot["relationship_revision_or_null"] is None:
        return False
    if kind == "scene" and snapshot["scene_policy_revision_or_null"] is None:
        return False
    return True


def record_identity(record: dict[str, Any]) -> tuple[Any, ...] | None:
    schema = record.get("schema")
    if schema == "relaylm.shared_assessment_revision.v1":
        return schema, record.get("assessment_id"), record.get("assessment_revision")
    if schema == "relaylm.shared_assessment_current_state.v1":
        return schema, record.get("assessment_state_id")
    if schema == "relaylm.subjective_mem_decision.v1":
        return schema, record.get("decision_id")
    if schema == "relaylm.subjective_mem_revision.v1":
        return schema, record.get("memory_id"), record.get("memory_revision")
    if schema == "relaylm.subjective_mem_current_state.v1":
        return schema, record.get("memory_state_id")
    if schema == "relaylm.subjective_mem_relation.v1":
        return schema, record.get("relation_id")
    if schema == "relaylm.subjective_mem_lifecycle_transition.v1":
        return schema, record.get("transition_id")
    return None


def has_cycle(edges: list[tuple[tuple[str, int], tuple[str, int]]]) -> bool:
    graph: dict[tuple[str, int], set[tuple[str, int]]] = {}
    for source, target in edges:
        graph.setdefault(source, set()).add(target)
    visited: set[tuple[str, int]] = set()
    active: set[tuple[str, int]] = set()

    def visit(node: tuple[str, int]) -> bool:
        if node in active:
            return True
        if node in visited:
            return False
        active.add(node)
        for target in graph.get(node, set()):
            if visit(target):
                return True
        active.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in list(graph))


def schema_invalid(records: list[dict[str, Any]], schema_bundle: dict[str, Any]) -> bool:
    checker = FormatChecker()
    for record in records:
        definition = SCHEMA_TO_DEF.get(record.get("schema"))
        if not definition:
            return True
        record_schema = {"$ref": f"#/$defs/{definition}", "$defs": schema_bundle["$defs"]}
        if next(Draft202012Validator(record_schema, format_checker=checker).iter_errors(record), None):
            return True
    return False


def validate_records(records: list[dict[str, Any]], schema_bundle: dict[str, Any] | None = None) -> set[str]:
    schema_bundle = schema_bundle or load_json(SCHEMA_PATH)
    if schema_invalid(records, schema_bundle):
        return {"SUBJ_MEM_E_SCHEMA_INVALID"}

    errors: set[str] = set()
    seen: set[tuple[Any, ...] | None] = set()
    assessment_current_counts: dict[str, int] = {}
    memory_current_counts: dict[tuple[str, str], int] = {}
    for record in records:
        identity = record_identity(record)
        if identity in seen:
            errors.add("SUBJ_MEM_E_DUPLICATE_TOP_LEVEL_ID")
        seen.add(identity)
        if record["schema"] == "relaylm.shared_assessment_current_state.v1":
            assessment_current_counts[record["assessment_id"]] = assessment_current_counts.get(record["assessment_id"], 0) + 1
        if record["schema"] == "relaylm.subjective_mem_current_state.v1":
            key = (record["character_id"], record["memory_id"])
            memory_current_counts[key] = memory_current_counts.get(key, 0) + 1
    if any(count > 1 for count in assessment_current_counts.values()):
        errors.add("SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE")
    if any(count > 1 for count in memory_current_counts.values()):
        errors.add("SUBJ_MEM_E_DUPLICATE_MEMORY_CURRENT_STATE")

    assessments: dict[tuple[str, int], dict[str, Any]] = {}
    assessment_states: dict[str, dict[str, Any]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    memories: dict[tuple[str, int], dict[str, Any]] = {}
    memory_states: dict[tuple[str, str], dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    transitions: dict[str, dict[str, Any]] = {}
    for record in records:
        schema = record["schema"]
        if schema == "relaylm.shared_assessment_revision.v1":
            assessments.setdefault((record["assessment_id"], record["assessment_revision"]), record)
        elif schema == "relaylm.shared_assessment_current_state.v1":
            assessment_states.setdefault(record["assessment_id"], record)
        elif schema == "relaylm.subjective_mem_decision.v1":
            decisions.setdefault(record["decision_id"], record)
        elif schema == "relaylm.subjective_mem_revision.v1":
            memories.setdefault((record["memory_id"], record["memory_revision"]), record)
        elif schema == "relaylm.subjective_mem_current_state.v1":
            memory_states.setdefault((record["character_id"], record["memory_id"]), record)
        elif schema == "relaylm.subjective_mem_relation.v1":
            relations.setdefault(record["relation_id"], record)
        elif schema == "relaylm.subjective_mem_lifecycle_transition.v1":
            transitions.setdefault(record["transition_id"], record)

    assessment_revisions: dict[str, list[int]] = {}
    for (assessment_id, revision), assessment in assessments.items():
        assessment_revisions.setdefault(assessment_id, []).append(revision)
        if sha256_text(assessment["supported_content"]) != assessment["supported_content_digest"]:
            errors.add("SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH")
        predecessor = assessment["supersedes_assessment_revision_or_null"]
        if revision == 1 and predecessor is not None:
            errors.add("SUBJ_MEM_E_ASSESSMENT_SUPERSESSION_INVALID")
        elif revision > 1 and (predecessor != revision - 1 or (assessment_id, predecessor) not in assessments):
            errors.add("SUBJ_MEM_E_ASSESSMENT_SUPERSESSION_INVALID")
        if predecessor and parse_time(assessment["created_at"]) <= parse_time(assessments[(assessment_id, predecessor)]["created_at"]):
            errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

    for assessment_id in assessment_revisions:
        if assessment_id not in assessment_states:
            errors.add("SUBJ_MEM_E_ASSESSMENT_CURRENT_MISSING")
    for assessment_id, state in assessment_states.items():
        assessment = assessments.get((assessment_id, state["current_revision"]))
        if not assessment:
            errors.add("SUBJ_MEM_E_ASSESSMENT_REVISION_DANGLING")
        expected_authorization = {
            "active": "current_admitted",
            "restricted": "restricted",
            "superseded": "restricted",
            "purged": "purged",
        }.get(state["lifecycle_state"])
        if state["authorization_state"] != expected_authorization:
            errors.add(
                "SUBJ_MEM_E_ASSESSMENT_AUTHORIZATION_NOT_CURRENT"
                if state["lifecycle_state"] == "active"
                else "SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH"
            )
        if assessment and state["current_revision"] != max(assessment_revisions.get(assessment_id, [])):
            errors.add("SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH")
        if assessment and parse_time(state["updated_at"]) < parse_time(assessment["created_at"]):
            errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

    def latest_assessment_revision_at(assessment_id: str, when: datetime) -> int | None:
        revisions = [
            revision
            for (candidate_id, revision), assessment in assessments.items()
            if candidate_id == assessment_id and parse_time(assessment["created_at"]) <= when
        ]
        return max(revisions) if revisions else None

    memory_revisions: dict[tuple[str, str], list[int]] = {}
    for (memory_id, revision), memory in memories.items():
        memory_revisions.setdefault((memory["character_id"], memory_id), []).append(revision)

    def latest_memory_revision_at(character_id: str, memory_id: str, when: datetime) -> int | None:
        revisions = [
            revision
            for (candidate_id, revision), memory in memories.items()
            if candidate_id == memory_id
            and memory["character_id"] == character_id
            and parse_time(memory["created_at"]) <= when
        ]
        return max(revisions) if revisions else None

    for decision in decisions.values():
        assessment_ref = decision["assessment_ref"]
        assessment = assessments.get((assessment_ref["assessment_id"], assessment_ref["assessment_revision"]))
        decided_at = parse_time(decision["decided_at"])
        if not assessment:
            errors.add("SUBJ_MEM_E_DECISION_ASSESSMENT_DANGLING")
        else:
            receipt = decision["assessment_authorization_receipt"]
            if (
                assessment_ref["supported_content_digest"] != assessment["supported_content_digest"]
                or receipt["current_revision_at_decision"] != assessment_ref["assessment_revision"]
                or latest_assessment_revision_at(assessment_ref["assessment_id"], decided_at) != assessment_ref["assessment_revision"]
            ):
                errors.add("SUBJ_MEM_E_DECISION_ASSESSMENT_RECEIPT_INVALID")
            if decided_at < parse_time(assessment["created_at"]):
                errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

        outcome = decision["outcome"]
        target_ref = decision["target_memory_ref_or_null"]
        result_ref = decision["result_memory_ref_or_null"]
        relation_id = decision["result_relation_id_or_null"]
        hold_reason = decision["hold_reason_or_null"]
        candidate_keys = {memory_ref_key(candidate) for candidate in decision["candidate_memory_refs"]}

        if outcome in TARGET_REQUIRED_OUTCOMES and target_ref is None:
            errors.add("SUBJ_MEM_E_DECISION_TARGET_REQUIRED")
        if outcome in TARGET_FORBIDDEN_OUTCOMES and target_ref is not None:
            errors.add("SUBJ_MEM_E_DECISION_TARGET_FORBIDDEN")
        if outcome in MEMORY_RESULT_OUTCOMES and result_ref is None:
            errors.add("SUBJ_MEM_E_DECISION_RESULT_MEMORY_REQUIRED")
        if outcome == "relate" and relation_id is None:
            errors.add("SUBJ_MEM_E_DECISION_RESULT_RELATION_REQUIRED")
        if (
            (outcome in MEMORY_RESULT_OUTCOMES and relation_id is not None)
            or (outcome == "relate" and result_ref is not None)
            or (outcome in NO_RESULT_OUTCOMES and (result_ref is not None or relation_id is not None))
        ):
            errors.add("SUBJ_MEM_E_DECISION_RESULT_FORBIDDEN")
        if outcome == "hold" and hold_reason is None:
            errors.add("SUBJ_MEM_E_DECISION_HOLD_REASON_REQUIRED")
        if outcome != "hold" and hold_reason is not None:
            errors.add("SUBJ_MEM_E_DECISION_HOLD_REASON_FORBIDDEN")

        target_memory = memories.get(memory_ref_key(target_ref)) if target_ref else None
        if target_ref:
            if memory_ref_key(target_ref) not in candidate_keys:
                errors.add("SUBJ_MEM_E_DECISION_TARGET_NOT_CANDIDATE")
            if not target_memory:
                errors.add("SUBJ_MEM_E_DECISION_TARGET_DANGLING")
            else:
                if (
                    latest_memory_revision_at(decision["character_id"], target_memory["memory_id"], decided_at)
                    != target_memory["memory_revision"]
                    or target_memory["lifecycle_state"] not in VISIBLE_LIFECYCLES
                ):
                    errors.add("SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT")
                if target_memory["character_id"] != decision["character_id"]:
                    errors.add("SUBJ_MEM_E_DECISION_TARGET_CHARACTER_MISMATCH")
                if target_memory["scope_binding"] != decision["scope_binding"]:
                    errors.add("SUBJ_MEM_E_DECISION_TARGET_SCOPE_MISMATCH")

        for candidate_ref in decision["candidate_memory_refs"]:
            candidate = memories.get(memory_ref_key(candidate_ref))
            if not candidate:
                errors.add("SUBJ_MEM_E_DECISION_CANDIDATE_DANGLING")
                continue
            if parse_time(candidate["created_at"]) > decided_at:
                errors.add("SUBJ_MEM_E_DECISION_CANDIDATE_NOT_AVAILABLE")
            if candidate["character_id"] != decision["character_id"]:
                errors.add("SUBJ_MEM_E_DECISION_CANDIDATE_CHARACTER_MISMATCH")
            if candidate["scope_binding"] != decision["scope_binding"]:
                errors.add("SUBJ_MEM_E_DECISION_CANDIDATE_SCOPE_MISMATCH")

        result_memory = memories.get(memory_ref_key(result_ref)) if result_ref else None
        if result_ref:
            if not result_memory:
                errors.add("SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING")
            else:
                if result_memory["character_id"] != decision["character_id"]:
                    errors.add("SUBJ_MEM_E_DECISION_RESULT_CHARACTER_MISMATCH")
                if result_memory["scope_binding"] != decision["scope_binding"]:
                    errors.add("SUBJ_MEM_E_DECISION_RESULT_SCOPE_MISMATCH")
                if result_memory["grounded_assessment_ref"] != decision["assessment_ref"]:
                    errors.add("SUBJ_MEM_E_DECISION_RESULT_ASSESSMENT_MISMATCH")
                linked = result_memory["authorization_ref"] == {
                    "authority_kind": "formation_decision",
                    "authority_id": decision["decision_id"],
                }
                if outcome == "create":
                    linked = linked and result_memory["memory_revision"] == 1 and result_memory["predecessor_revision_or_null"] is None
                elif target_memory:
                    linked = (
                        linked
                        and result_memory["memory_id"] == target_memory["memory_id"]
                        and result_memory["memory_revision"] == target_memory["memory_revision"] + 1
                        and result_memory["predecessor_revision_or_null"] == target_memory["memory_revision"]
                    )
                if not linked:
                    errors.add("SUBJ_MEM_E_DECISION_RESULT_LINK_INVALID")
                if decided_at > parse_time(result_memory["created_at"]):
                    errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

        if relation_id:
            relation = relations.get(relation_id)
            if (
                not relation
                or relation["authorizing_decision_id"] != decision["decision_id"]
                or memory_ref_key(target_ref)
                not in {memory_ref_key(relation["source_memory_ref"]), memory_ref_key(relation["target_memory_ref"])}
            ):
                errors.add("SUBJ_MEM_E_DECISION_RELATION_LINK_INVALID")
            if relation:
                endpoint_keys = {
                    memory_ref_key(relation["source_memory_ref"]),
                    memory_ref_key(relation["target_memory_ref"]),
                }
                if not endpoint_keys <= candidate_keys:
                    errors.add("SUBJ_MEM_E_DECISION_RELATION_CANDIDATE_MISMATCH")
                if decided_at > parse_time(relation["created_at"]):
                    errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

        if not scope_consistent(decision["scope_binding"]):
            errors.add("SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT")
        if decision["scope_binding"]["scope_kind"] in {"participant", "relationship"} and decision["scope_binding"]["identity_status"] != "known":
            errors.add("SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED")

    for (memory_id, revision), memory in memories.items():
        assessment_ref = memory["grounded_assessment_ref"]
        assessment = assessments.get((assessment_ref["assessment_id"], assessment_ref["assessment_revision"]))
        digest = assessment["supported_content_digest"] if assessment else None
        if not assessment:
            errors.add("SUBJ_MEM_E_MEM_ASSESSMENT_DANGLING")
        if (
            not assessment
            or assessment_ref["supported_content_digest"] != digest
            or memory["grounded_content_digest"] != digest
            or sha256_text(memory["grounded_content"]) != memory["grounded_content_digest"]
            or (assessment and memory["grounded_content"] != assessment["supported_content"])
        ):
            errors.add("SUBJ_MEM_E_GROUNDED_DIGEST_MISMATCH")

        predecessor = memory["predecessor_revision_or_null"]
        if revision == 1 and predecessor is not None:
            errors.add("SUBJ_MEM_E_MEM_PREDECESSOR_INVALID")
        elif revision > 1 and (predecessor != revision - 1 or (memory_id, predecessor) not in memories):
            errors.add("SUBJ_MEM_E_MEM_PREDECESSOR_INVALID")
        elif predecessor and parse_time(memory["created_at"]) <= parse_time(memories[(memory_id, predecessor)]["created_at"]):
            errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

        if memory["retrieval_visible"] != (memory["lifecycle_state"] in VISIBLE_LIFECYCLES):
            errors.add("SUBJ_MEM_E_MEM_RETRIEVAL_VISIBILITY_INVALID")
        if not scope_consistent(memory["scope_binding"]):
            errors.add("SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT")
        if memory["scope_binding"]["scope_kind"] in {"participant", "relationship"} and memory["scope_binding"]["identity_status"] != "known":
            errors.add("SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED")
        if not scope_snapshot_consistent(memory):
            errors.add("SUBJ_MEM_E_SCOPE_SNAPSHOT_MISMATCH")

        authorization = memory["authorization_ref"]
        authority = (
            decisions.get(authorization["authority_id"])
            if authorization["authority_kind"] == "formation_decision"
            else transitions.get(authorization["authority_id"])
        )
        invalid_authority = False
        if authorization["authority_kind"] == "formation_decision":
            invalid_authority = not authority or memory_ref_key(authority["result_memory_ref_or_null"]) != (memory_id, revision)
        else:
            invalid_authority = not authority or (authority["memory_id"], authority["to_revision"]) != (memory_id, revision)
        if invalid_authority:
            errors.add("SUBJ_MEM_E_MEM_AUTHORIZATION_INVALID")

    for key in memory_revisions:
        if key not in memory_states:
            errors.add("SUBJ_MEM_E_MEM_CURRENT_MISSING")
    for (character_id, memory_id), state in memory_states.items():
        memory = memories.get((memory_id, state["current_revision"]))
        if not memory:
            errors.add("SUBJ_MEM_E_MEM_CURRENT_DANGLING")
        elif (
            memory["character_id"] != character_id
            or memory["lifecycle_state"] != state["lifecycle_state"]
            or state["current_revision"] != max(memory_revisions.get((character_id, memory_id), []))
        ):
            errors.add("SUBJ_MEM_E_MEM_CURRENT_MISMATCH")
        if memory and parse_time(state["updated_at"]) < parse_time(memory["created_at"]):
            errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")
        expected_eligible = bool(memory and state["lifecycle_state"] in VISIBLE_LIFECYCLES and state["mutation_state"] == "none")
        if state["retrieval_eligible"] != expected_eligible:
            errors.add("SUBJ_MEM_E_MEM_RETRIEVAL_ELIGIBILITY_INVALID")

    successor_edges: list[tuple[tuple[str, int], tuple[str, int]]] = []
    for relation in relations.values():
        source_key = memory_ref_key(relation["source_memory_ref"])
        target_key = memory_ref_key(relation["target_memory_ref"])
        source = memories.get(source_key)
        target = memories.get(target_key)
        if not source:
            errors.add("SUBJ_MEM_E_RELATION_SOURCE_DANGLING")
        if not target:
            errors.add("SUBJ_MEM_E_RELATION_TARGET_DANGLING")
        if source_key == target_key:
            errors.add("SUBJ_MEM_E_RELATION_SELF_REFERENCE")
        if source and target:
            if relation["character_id"] != source["character_id"] or relation["character_id"] != target["character_id"]:
                errors.add("SUBJ_MEM_E_RELATION_CHARACTER_MISMATCH")
            if source["scope_binding"] != target["scope_binding"]:
                errors.add("SUBJ_MEM_E_RELATION_SCOPE_MISMATCH")
            if parse_time(relation["created_at"]) < max(parse_time(source["created_at"]), parse_time(target["created_at"])):
                errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")
            if relation["relation_type"] in SUCCESSOR_RELATIONS:
                successor_edges.append((source_key, target_key))
        decision = decisions.get(relation["authorizing_decision_id"])
        if not decision or decision["result_relation_id_or_null"] != relation["relation_id"]:
            errors.add("SUBJ_MEM_E_RELATION_AUTHORIZATION_INVALID")
    if has_cycle(successor_edges):
        errors.add("SUBJ_MEM_E_RELATION_CYCLE")

    operation_states = {
        "correct": ("active", "active"),
        "forget": ("active", "hidden"),
        "restore": ("hidden", "active"),
        "consolidate": ("active", "active"),
        "pin": ("active", "pinned"),
        "unpin": ("pinned", "active"),
    }
    operation_stages = {"consolidate": ("primary", "secondary")}
    operation_authorities = {
        "correct": {"user_management", "operator"},
        "forget": {"user_management", "operator"},
        "restore": {"user_management", "operator"},
        "pin": {"user_management", "operator"},
        "unpin": {"user_management", "operator"},
        "consolidate": {"user_management", "operator", "relaymem_policy"},
    }
    common_fields = {"memory_id", "character_id", "memory_kind", "scope_binding", "formation_snapshot"}
    frozen_fields = common_fields | {
        "grounded_assessment_ref",
        "grounded_content",
        "grounded_content_digest",
        "subjective_meaning",
        "strength",
    }
    for transition in transitions.values():
        source = memories.get((transition["memory_id"], transition["from_revision"]))
        target = memories.get((transition["memory_id"], transition["to_revision"]))
        if not source:
            errors.add("SUBJ_MEM_E_TRANSITION_FROM_DANGLING")
        if not target:
            errors.add("SUBJ_MEM_E_TRANSITION_TO_DANGLING")
        if transition["to_revision"] != transition["from_revision"] + 1:
            errors.add("SUBJ_MEM_E_TRANSITION_REVISION_INVALID")
        if not source or not target:
            continue
        if transition["character_id"] != source["character_id"] or transition["character_id"] != target["character_id"]:
            errors.add("SUBJ_MEM_E_TRANSITION_CHARACTER_MISMATCH")
        operation = transition["operation"]
        lifecycle_pair = (transition["from_lifecycle_state"], transition["to_lifecycle_state"])
        if lifecycle_pair != (source["lifecycle_state"], target["lifecycle_state"]) or lifecycle_pair != operation_states[operation]:
            errors.add("SUBJ_MEM_E_TRANSITION_STATE_INVALID")
        stage_pair = (transition["from_formation_stage"], transition["to_formation_stage"])
        actual_stage_pair = (source["formation_stage"], target["formation_stage"])
        expected_stage_pair = operation_stages.get(operation)
        if (
            stage_pair != actual_stage_pair
            or (expected_stage_pair and stage_pair != expected_stage_pair)
            or (not expected_stage_pair and stage_pair[0] != stage_pair[1])
        ):
            errors.add("SUBJ_MEM_E_TRANSITION_STAGE_INVALID")
        if transition["authorized_by"] not in operation_authorities[operation]:
            errors.add("SUBJ_MEM_E_TRANSITION_AUTHORITY_INVALID")
        compared_fields = common_fields if operation == "correct" else frozen_fields
        if any(source[field] != target[field] for field in compared_fields) or (
            operation != "consolidate" and source["formation_stage"] != target["formation_stage"]
        ):
            errors.add("SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION")
        if not (
            parse_time(source["created_at"])
            <= parse_time(transition["committed_at"])
            <= parse_time(target["created_at"])
        ):
            errors.add("SUBJ_MEM_E_TIME_ORDER_INVALID")

    return errors


def fixture_cases(directory: Path) -> Iterable[tuple[Path, dict[str, Any], dict[str, Any]]]:
    for path in sorted(directory.glob("*.json")):
        payload = load_json(path)
        for case in payload.get("cases", []):
            yield path, payload, case


def run_suite() -> tuple[int, int, list[str]]:
    schema = load_json(SCHEMA_PATH)
    failures: list[str] = []
    valid_count = 0
    invalid_count = 0
    for path, payload, case in fixture_cases(VALID_DIR):
        valid_count += 1
        actual = validate_records(materialize_case(payload, case, path), schema)
        if actual:
            failures.append(f"valid {path.name}:{case['name']} produced {sorted(actual)}")
    for path, payload, case in fixture_cases(INVALID_DIR):
        invalid_count += 1
        actual = validate_records(materialize_case(payload, case, path), schema)
        expected = set(case["expected_error_ids"])
        if actual != expected:
            failures.append(f"invalid {path.name}:{case['name']} expected {sorted(expected)} got {sorted(actual)}")
    return valid_count, invalid_count, failures


def run_self_test() -> list[str]:
    base_records = load_json(VALID_DIR / "matrix.json")["base_records"]
    schema = load_json(SCHEMA_PATH)
    probes = [
        ([{"op": "set", "record_index": 3, "path": ["result_memory_ref_or_null", "memory_id"], "value": "missing"}], "SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING"),
        ([{"op": "append_copy", "record_index": 2}, {"op": "set", "record_index": 15, "path": ["assessment_state_id"], "value": "other"}], "SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE"),
        ([{"op": "set", "record_index": 0, "path": ["supported_content_digest"], "value": "f" * 64}], "SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH"),
        ([{"op": "set", "record_index": 10, "path": ["subjective_meaning"], "value": "illicit"}], "SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION"),
        ([{"op": "set", "record_index": 11, "path": ["decided_at"], "value": "2026-07-21T00:13:00Z"}], "SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT"),
        ([{"op": "set", "record_index": 11, "path": ["candidate_memory_refs", 0, "memory_revision"], "value": 2}], "SUBJ_MEM_E_DECISION_CANDIDATE_NOT_AVAILABLE"),
        ([{"op": "set", "record_index": 12, "path": ["grounded_assessment_ref", "assessment_revision"], "value": 1}], "SUBJ_MEM_E_DECISION_RESULT_ASSESSMENT_MISMATCH"),
    ]
    failures: list[str] = []
    for mutations, expected in probes:
        if expected not in validate_records(apply_mutations(base_records, mutations), schema):
            failures.append(expected)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
        catalog_map = {entry["schema"]: entry["definition"] for entry in load_json(CATALOG_PATH)["schemas"]}
        if catalog_map != SCHEMA_TO_DEF:
            raise ValueError(catalog_map)
    except Exception as exc:
        print(f"ERROR: contract schema setup failed: {exc}", file=sys.stderr)
        return 1
    valid_count, invalid_count, failures = run_suite()
    if args.self_test:
        failures.extend(run_self_test())
    if failures:
        for failure in failures:
            print("ERROR:", failure, file=sys.stderr)
        return 1
    suffix = " + self-test" if args.self_test else ""
    print(f"subjective-mem v1 validation{suffix}: PASS ({valid_count} valid, {invalid_count} invalid)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
