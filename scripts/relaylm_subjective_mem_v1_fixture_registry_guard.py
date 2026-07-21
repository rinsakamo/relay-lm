#!/usr/bin/env python3
"""Fail closed when the Subjective MEM v1 invalid fixture registry drifts."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVALID_DIR = ROOT / "docs/contracts/fixtures/subjective-mem-v1/invalid"

EXPECTED_CASES = {
    "matrix-01.json": [
        "duplicate_top_level_id",
        "duplicate_assessment_current_state",
        "duplicate_memory_current_state",
        "assessment_digest_mismatch",
        "assessment_supersession_invalid",
    ],
    "matrix-02.json": [
        "assessment_current_dangling",
        "assessment_current_not_latest",
        "assessment_authorization_not_current",
        "schema_rejects_missing_lineage",
        "decision_assessment_dangling",
    ],
    "matrix-03.json": [
        "decision_assessment_receipt_invalid",
        "decision_target_required",
        "decision_target_forbidden",
        "decision_result_memory_required",
        "decision_result_relation_required",
    ],
    "matrix-04.json": [
        "decision_result_forbidden",
        "decision_hold_reason_required",
        "decision_hold_reason_forbidden",
        "decision_target_dangling",
        "decision_target_not_current_at_decision",
    ],
    "matrix-05.json": [
        "decision_target_character_mismatch",
        "decision_target_scope_mismatch",
        "decision_candidate_dangling",
        "decision_result_memory_dangling",
        "decision_result_memory_link_invalid",
    ],
    "matrix-06.json": [
        "decision_relation_link_invalid",
        "scope_identity_unknown",
        "scope_binding_inconsistent",
        "scope_snapshot_relationship_missing",
        "grounded_digest_mismatch",
    ],
    "matrix-07.json": [
        "mem_assessment_dangling",
        "mem_predecessor_invalid",
        "mem_authorization_invalid",
        "mem_visibility_invalid",
        "mem_current_mismatch",
    ],
    "matrix-08.json": [
        "mem_retrieval_eligibility_invalid",
        "relation_self_reference",
        "relation_scope_mismatch",
        "transition_payload_mutation",
        "transition_authority_invalid",
    ],
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check(directory: Path = INVALID_DIR) -> list[str]:
    failures: list[str] = []
    actual_files = sorted(path.name for path in directory.glob("*.json"))
    expected_files = sorted(EXPECTED_CASES)
    if actual_files != expected_files:
        failures.append(f"invalid fixture files mismatch: expected {expected_files}, got {actual_files}")

    all_names: set[str] = set()
    all_errors: set[str] = set()
    for filename, expected_names in EXPECTED_CASES.items():
        path = directory / filename
        if not path.is_file():
            continue
        try:
            payload = load(path)
        except Exception as exc:
            failures.append(f"unable to load {filename}: {exc}")
            continue
        if payload.get("contract") != "relaylm.subjective_mem.v1":
            failures.append(f"wrong contract marker: {filename}")
        if payload.get("base_fixture") != "../valid/matrix.json":
            failures.append(f"wrong base fixture: {filename}")
        cases = payload.get("cases")
        if not isinstance(cases, list):
            failures.append(f"cases is not a list: {filename}")
            continue
        actual_names = [case.get("name") for case in cases]
        if actual_names != expected_names:
            failures.append(f"case registry mismatch in {filename}: expected {expected_names}, got {actual_names}")
        for case in cases:
            name = case.get("name")
            if name in all_names:
                failures.append(f"duplicate case name across files: {name}")
            all_names.add(name)
            expected_ids = case.get("expected_error_ids")
            if not isinstance(expected_ids, list) or not expected_ids:
                failures.append(f"missing expected_error_ids: {filename}:{name}")
            elif expected_ids != sorted(set(expected_ids)):
                failures.append(f"expected_error_ids must be unique and sorted: {filename}:{name}")
            elif any(not isinstance(value, str) or not value.startswith("SUBJ_MEM_E_") for value in expected_ids):
                failures.append(f"malformed expected_error_ids: {filename}:{name}")
            else:
                all_errors.update(expected_ids)
            mutations = case.get("mutations")
            if not isinstance(mutations, list) or not mutations:
                failures.append(f"case lacks mutations: {filename}:{name}")
            elif any(mutation.get("op") not in {"set", "append_copy", "append_record", "delete"} for mutation in mutations):
                failures.append(f"case uses unsupported mutation op: {filename}:{name}")
    if len(all_names) != 40:
        failures.append(f"expected 40 unique invalid cases, found {len(all_names)}")
    if len(all_errors) < 50:
        failures.append(f"expected broad semantic error coverage, found {len(all_errors)} IDs")
    return failures


def run_self_test() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="subjective-mem-registry-") as tmp:
        root = Path(tmp)
        for path in INVALID_DIR.glob("*.json"):
            (root / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

        removed = root / "matrix-08.json"
        saved = removed.read_text(encoding="utf-8")
        removed.unlink()
        if not check(root):
            failures.append("self-test failed to detect removed invalid fixture")
        removed.write_text(saved, encoding="utf-8")

        path = root / "matrix-01.json"
        payload = load(path)
        payload["cases"][0]["name"] = "renamed_case"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if not check(root):
            failures.append("self-test failed to detect renamed invalid case")
        path.write_text((INVALID_DIR / path.name).read_text(encoding="utf-8"), encoding="utf-8")

        path = root / "matrix-02.json"
        payload = load(path)
        payload["cases"][0]["expected_error_ids"] = []
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if not check(root):
            failures.append("self-test failed to detect empty expected-error declaration")

        path.write_text((INVALID_DIR / path.name).read_text(encoding="utf-8"), encoding="utf-8")
        payload = load(path)
        payload["cases"][0]["mutations"][0]["op"] = "unknown"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if not check(root):
            failures.append("self-test failed to detect unsupported mutation op")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    failures = check()
    if args.self_test:
        failures.extend(run_self_test())
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    suffix = " + self-test" if args.self_test else ""
    print(f"subjective-mem v1 fixture registry{suffix}: PASS (8 files, 40 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
