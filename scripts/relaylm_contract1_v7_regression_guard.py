#!/usr/bin/env python3
"""Guard Contract 1 v7 package topology and negative-fixture intent."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# expected_failure -> (schema id, JSON pointer, jsonschema keyword)
SCHEMA_FAILURES = {
    "schema: assistant_response requires non-null binding": ("relaylm.source_event.v1", "/assistant_response_binding_ref_or_null", "type"),
    "schema: revision 1 requires null expected previous": ("relaylm.assistant_delivery_observation_event.v1", "/expected_previous_observation_revision_or_null", "type"),
    "schema: bootstrap descriptor requires null change-set ref": ("relaylm.evidence_space_descriptor.v1", "/authority_change_set_ref_or_null", "type"),
    "schema: export purpose allows only local export/encrypted backup": ("relaylm.evidence_access_grant.v1", "/destination_class_constraint", "enum"),
    "schema: omitted part requires null content digest/length": ("relaylm.canonical_source_manifest.v1", "/parts/0/content_digest_or_null", "type"),
    "schema: aborted projection requires empty refs": ("relaylm.evidence_authority_change_projection_event.v1", "/authorized_source_event_refs", "maxItems"),
    "schema: rejected outcome requires null source/governance/change-set refs": ("relaylm.evidence_admission_decision.v1", "/source_event_id_or_null", "type"),
    "schema: retained_until_revoked requires null access/purge deadlines": ("relaylm.evidence_governance_state.v1", "/retention_state/access_until_or_null", "type"),
}
# Only expected labels whose stable diagnostic differs materially need aliases.
CUSTOM_ALIASES = {
    "custom: AuthorityScope does not allow initialize_admitted": "AuthorityScope does not allow operation initialize_admitted",
    "custom: abort cannot satisfy projection plan": "abort counted as planned projection",
    "custom: delivery cohort must be configured-audience subset": "delivery cohort is not a configured-audience subset",
    "custom: recipient selector must be a subset of delivery cohort": "recipient selector is outside the delivery cohort",
    "custom: one managed response identity has one SourceEvent": "multiple SourceEvents",
    "custom: failed integrity cannot keep granted content lifecycle": "integrity failed while grants remain granted",
    "custom: metadata corrected_fields allowlist violation": "forbidden corrected fields",
    "custom: payload binding digest mismatch": "payload binding attestation coverage/digest mismatch",
    "custom: protected part binding coverage mismatch": "payload binding attestation coverage/digest mismatch",
    "custom: quarantined admission may not project normal candidate availability": "quarantined source projected to a normal consumer",
    "custom: accepted ranges overlap": "accepted ranges overlap or are unsorted",
}


def load_validator(root: Path):
    path = root / "scripts/relaylm_contract1_v7_validate.py"
    spec = importlib.util.spec_from_file_location("contract1_v7_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Contract 1 v7 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema_diagnostics(validator: Any, fixture: dict[str, Any]) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for record in fixture.get("records", []):
        if not isinstance(record, dict):
            continue
        schema_id = record.get("schema")
        definition = validator.schema_map.get(schema_id)
        if definition is None:
            continue
        for error in validator.schema_validator(definition).iter_errors(record):
            pointer = "/" + "/".join(str(part) for part in error.absolute_path)
            found.add((schema_id, pointer, error.validator))
    return found


def check_fixture_intent(root: Path, errors: list[str]) -> int:
    module = load_validator(root)
    schema_dir = root / "docs/contracts/schemas/contract1-v7"
    validator = module.ContractValidator(schema_dir / "relaylm-contract1-v7.bundle.schema.json")
    invalid_dir = root / "docs/contracts/fixtures/contract1-v7/invalid"
    seen: set[str] = set()
    for path in sorted(invalid_dir.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        expected = fixture.get("expected_failure")
        if not isinstance(expected, str) or not expected:
            errors.append(f"{path.name}: expected_failure is required")
            continue
        if expected in seen:
            errors.append(f"{path.name}: duplicate expected_failure {expected!r}")
        seen.add(expected)
        if not validator.validate_fixture(fixture):
            errors.append(f"{path.name}: invalid fixture unexpectedly passed")
            continue
        if expected.startswith("schema: "):
            target = SCHEMA_FAILURES.get(expected)
            if target is None:
                errors.append(f"{path.name}: unregistered schema expected_failure {expected!r}")
            elif target not in schema_diagnostics(validator, fixture):
                errors.append(f"{path.name}: did not trigger intended schema failure {target!r}")
            continue
        if not expected.startswith("custom: "):
            errors.append(f"{path.name}: unregistered expected_failure {expected!r}")
            continue
        needle = CUSTOM_ALIASES.get(expected, expected.removeprefix("custom: "))
        if not any(needle in item for item in validator._custom_checks(fixture)):
            errors.append(f"{path.name}: did not trigger intended custom failure {needle!r}")
    if len(seen) != 24:
        errors.append(f"expected 24 unique negative-fixture intents, found {len(seen)}")
    return len(seen)


def topology_errors(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "docs/contracts/schemas/contract1-v7"
    bundle_path = schema_dir / "relaylm-contract1-v7.bundle.schema.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_defs = bundle.get("$defs", {})
    part_defs: dict[str, Any] = {}
    owner_ids: dict[str, str] = {}
    part_paths = sorted(schema_dir.glob("relaylm-contract1-v7.part-*.schema.json"))
    for path in part_paths:
        part = json.loads(path.read_text(encoding="utf-8"))
        part_id = part.get("$id")
        if not isinstance(part_id, str) or not part_id:
            errors.append(f"{path.name}: missing non-empty $id")
            continue
        for name, definition in part.get("$defs", {}).items():
            if name in part_defs:
                errors.append(f"duplicate part definition {name}")
            part_defs[name] = definition
            owner_ids[name] = part_id
    if set(bundle_defs) != set(part_defs):
        errors.append("bundle/part definition-key mismatch")
    for name, part_id in owner_ids.items():
        expected = {"$ref": f"{part_id}#/$defs/{name}"}
        if bundle_defs.get(name) != expected:
            errors.append(f"{name}: bundle export mismatch")
    allowed = {bundle_path.name, *(path.name for path in part_paths)}
    wrappers = sorted(path.name for path in schema_dir.glob("*.schema.json") if path.name not in allowed)
    if wrappers:
        errors.append(f"standalone wrapper schemas are forbidden: {wrappers}")

    catalog = json.loads((schema_dir / "schema-catalog.json").read_text(encoding="utf-8"))
    if set(catalog) != {"bundle", "schemas"}:
        errors.append("catalog top-level keys must be exactly bundle and schemas")
    bundle_id = bundle.get("$id")
    if catalog.get("bundle") != bundle_id:
        errors.append("catalog bundle ID does not match bundle $id")
    entries = catalog.get("schemas", [])
    module = load_validator(root)
    expected_names = set(module.ContractValidator(bundle_path).schema_map.values())
    seen: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or set(entry) != {"definition", "id"}:
            errors.append(f"catalog entry keys are not exact: {entry!r}")
            continue
        name = entry.get("definition")
        if not isinstance(name, str):
            errors.append("catalog definition must be a string")
            continue
        if name in seen:
            errors.append(f"duplicate catalog definition {name}")
        seen.add(name)
        if entry.get("id") != f"{bundle_id}#/$defs/{name}":
            errors.append(f"{name}: catalog id mismatch")
    if seen != expected_names:
        errors.append(f"catalog definition mismatch: missing={sorted(expected_names-seen)}, extra={sorted(seen-expected_names)}")
    return errors


def execute(root: Path, self_test: bool) -> int:
    errors = [] if self_test else topology_errors(root)
    count = check_fixture_intent(root, errors)
    if errors:
        print("Contract 1 v7 regression guard FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if self_test:
        print(f"Contract 1 v7 regression guard self-test PASS: {count} assertions.")
    else:
        print(f"Contract 1 v7 regression guard PASS: exact bundle exports, wrapperless catalog topology, and {count} intended negative-fixture failures verified.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return execute(args.root, args.self_test)


if __name__ == "__main__":
    raise SystemExit(main())
