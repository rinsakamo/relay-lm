#!/usr/bin/env python3
"""Check prose/schema/catalog/fixture equivalence for Subjective MEM v1."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/contracts/shared-assessment-subjective-mem.md"
SCHEMA = ROOT / "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json"
CATALOG = ROOT / "docs/contracts/schemas/subjective-mem-v1/schema-catalog.json"
VALID_DIR = ROOT / "docs/contracts/fixtures/subjective-mem-v1/valid"
INVALID_DIR = ROOT / "docs/contracts/fixtures/subjective-mem-v1/invalid"
VALIDATOR = ROOT / "scripts/relaylm_subjective_mem_v1_validate.py"

EXPECTED_TOP_LEVEL = {
    "relaylm.shared_assessment_revision.v1": "SharedAssessmentRevision",
    "relaylm.shared_assessment_current_state.v1": "SharedAssessmentCurrentState",
    "relaylm.subjective_mem_decision.v1": "SubjectiveMemDecision",
    "relaylm.subjective_mem_revision.v1": "SubjectiveMemRevision",
    "relaylm.subjective_mem_current_state.v1": "SubjectiveMemCurrentState",
    "relaylm.subjective_mem_relation.v1": "SubjectiveMemRelation",
    "relaylm.subjective_mem_lifecycle_transition.v1": "SubjectiveMemLifecycleTransition",
}
EXPECTED_DEFINITION_COUNT = 16

REQUIRED_ANCHORS = [
    "Shared Assessment remains character-independent",
    "Subjective MEM separates grounded content from subjective meaning",
    "supported_content_digest = sha256(UTF-8 supported_content)",
    "formation-time authorization receipt",
    "similarity_granted_authority: false",
    "The false merge cost is treated as higher than temporary duplication",
    "Decision output linkage is exact and bidirectional",
    "Primary/Secondary and Semantic/Episodic are orthogonal",
    "Strong relationship does not imply disclosure permission",
    "Exactly one `SubjectiveMemCurrentState` may exist",
    "A lifecycle operation cannot conceal an unrelated payload rewrite",
    "Only the exact current revision may enter ordinary Retrieval",
    "Official RelayLM product knowledge is outside this contract",
    "seven valid cases and forty invalid exact-error cases",
]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator_module():
    spec = importlib.util.spec_from_file_location("relaylm_subjective_mem_v1_validate", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load validator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_fields(defs: dict[str, Any], definition: str, fields: set[str], failures: list[str]) -> None:
    actual = set(defs[definition].get("required", []))
    missing = fields - actual
    if missing:
        failures.append(f"{definition} missing required fields: {sorted(missing)}")


def main() -> int:
    failures: list[str] = []
    prose = CONTRACT.read_text(encoding="utf-8")
    schema = load(SCHEMA)
    catalog = load(CATALOG)
    validator = load_validator_module()

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        failures.append(f"Draft 2020-12 meta-schema failure: {exc}")

    for anchor in REQUIRED_ANCHORS:
        if anchor not in prose:
            failures.append(f"contract missing anchor: {anchor}")

    if "../architecture/memory/formation.md" not in prose or "../architecture/subjective-memory/subjective-memory-formation.md" in prose:
        failures.append("contract related-authority path is not canonical")
    if schema.get("$id") != catalog.get("bundle"):
        failures.append("schema/catalog bundle ID mismatch")
    catalog_map = {entry.get("schema"): entry.get("definition") for entry in catalog.get("schemas", [])}
    if catalog_map != EXPECTED_TOP_LEVEL:
        failures.append(f"catalog exact mapping mismatch: {catalog_map}")
    if validator.SCHEMA_TO_DEF != EXPECTED_TOP_LEVEL:
        failures.append("validator schema mapping differs from catalog authority")

    defs = schema.get("$defs", {})
    if len(defs) != EXPECTED_DEFINITION_COUNT:
        failures.append(f"expected {EXPECTED_DEFINITION_COUNT} schema definitions, found {len(defs)}")
    missing_defs = set(EXPECTED_TOP_LEVEL.values()) - set(defs)
    if missing_defs:
        failures.append(f"schema missing top-level definitions: {sorted(missing_defs)}")
    one_of = schema.get("properties", {}).get("records", {}).get("items", {}).get("oneOf", [])
    refs = {item.get("$ref", "").split("/")[-1] for item in one_of}
    if refs != set(EXPECTED_TOP_LEVEL.values()):
        failures.append(f"bundle oneOf coverage mismatch: {sorted(refs)}")

    require_fields(defs, "EvidenceRef", {"lineage_revision"}, failures)
    require_fields(defs, "SubjectiveMemDecision", {"assessment_authorization_receipt", "target_memory_ref_or_null", "result_memory_ref_or_null", "result_relation_id_or_null"}, failures)
    require_fields(defs, "SubjectiveMemRevision", {"authorization_ref"}, failures)
    require_fields(defs, "SubjectiveMemRelation", {"authorizing_decision_id"}, failures)

    taxonomy_paths = [
        ("SubjectiveMemDecision", "outcome"),
        ("SubjectiveMemRevision", "formation_stage"),
        ("SubjectiveMemRevision", "memory_kind"),
        ("SubjectiveMemRevision", "lifecycle_state"),
        ("SubjectiveMemRelation", "relation_type"),
        ("SubjectiveMemLifecycleTransition", "operation"),
    ]
    for definition, property_name in taxonomy_paths:
        values = defs[definition]["properties"][property_name].get("enum", [])
        for value in values:
            if f"`{value}`" not in prose and value not in prose:
                failures.append(f"contract missing taxonomy token: {definition}.{property_name}={value}")

    valid_cases = []
    observed_schemas: set[str] = set()
    for path in sorted(VALID_DIR.glob("*.json")):
        payload = load(path)
        valid_cases.extend(payload.get("cases", []))
        for record in payload.get("base_records", []):
            observed_schemas.add(record.get("schema"))
        for case in payload.get("cases", []):
            for record in case.get("records", []):
                observed_schemas.add(record.get("schema"))

    invalid_cases = []
    represented_errors: set[str] = set()
    seen_case_names: set[str] = set()
    for path in sorted(INVALID_DIR.glob("*.json")):
        payload = load(path)
        for case in payload.get("cases", []):
            name = case.get("name")
            if name in seen_case_names:
                failures.append(f"duplicate invalid case name: {name}")
            seen_case_names.add(name)
            invalid_cases.append(case)
            expected = case.get("expected_error_ids")
            if not isinstance(expected, list) or not expected or len(expected) != len(set(expected)):
                failures.append(f"invalid exact error declaration: {path.name}:{name}")
            else:
                represented_errors.update(expected)

    if len(valid_cases) != 7:
        failures.append(f"expected 7 valid cases, found {len(valid_cases)}")
    if len(invalid_cases) != 40:
        failures.append(f"expected 40 invalid cases, found {len(invalid_cases)}")
    if observed_schemas != set(EXPECTED_TOP_LEVEL):
        failures.append(f"valid fixture schema coverage mismatch: {sorted(observed_schemas)}")
    unknown = represented_errors - validator.ALL_ERROR_IDS
    if unknown:
        failures.append(f"fixtures use unknown error IDs: {sorted(unknown)}")
    uncovered = validator.ALL_ERROR_IDS - represented_errors
    if uncovered:
        failures.append(f"validator error IDs lack intended-failure coverage: {sorted(uncovered)}")

    required_valid_names = {
        "historical_assessment_remains_valid",
        "create_decision_has_exact_result",
        "relation_is_decision_linked",
        "pin_transition_preserves_payload",
        "reinforcement_targets_historical_current",
    }
    valid_names = {case.get("name") for case in valid_cases}
    if not required_valid_names <= valid_names:
        failures.append(f"valid fixture semantics missing: {sorted(required_valid_names - valid_names)}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(
        "subjective-mem v1 equivalence: PASS "
        f"({len(EXPECTED_TOP_LEVEL)} top-level schemas, {len(defs)} definitions, "
        f"{len(valid_cases)} valid, {len(invalid_cases)} invalid, {len(represented_errors)} error IDs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
