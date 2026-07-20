#!/usr/bin/env python3
"""Cross-check RelayLM Contract 1 v7 prose, schemas, catalog, and fixtures."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator



OWNER_FILES = {
    "EvidenceSpaceDescriptor":
        "governed-evidence-contract-family.md",

    "RouteCaptureGrantSnapshot":
        "governed-source-capture-admission.md",
    "CaptureAttemptEvent":
        "governed-source-capture-admission.md",
    "CanonicalSourceManifest":
        "governed-source-capture-admission.md",
    "ProtectedPayloadBindingAttestation":
        "governed-source-capture-admission.md",
    "SourceEvent":
        "governed-source-capture-admission.md",
    "ValidationBundleRevision":
        "governed-source-capture-admission.md",
    "AdmissionDecision":
        "governed-source-capture-admission.md",
    "AdmissionReviewDecision":
        "governed-source-capture-admission.md",

    "AccessGrant":
        "evidence-governance-access.md",
    "EvidenceGovernanceState":
        "evidence-governance-access.md",
    "EvidenceGovernanceEvent":
        "evidence-governance-access.md",
    "PurgedEvidenceTombstone":
        "evidence-governance-access.md",
    "QuarantineReviewAuthorizationProjection":
        "evidence-governance-access.md",
    "EvidenceAccessAuthorizationProjection":
        "evidence-governance-access.md",

    "SourceMetadataRevision":
        "source-metadata-lineage-derived-artifacts.md",
    "SourceLineageRelationEvent":
        "source-metadata-lineage-derived-artifacts.md",
    "SourceDerivedArtifactEvent":
        "source-metadata-lineage-derived-artifacts.md",

    "SourceCaptureStreamDescriptor":
        "evidence-streams-change-feed.md",
    "CaptureSequenceEvent":
        "evidence-streams-change-feed.md",
    "SourceCaptureCoverageCheckpoint":
        "evidence-streams-change-feed.md",
    "AuthorityChangeSetEvent":
        "evidence-streams-change-feed.md",
    "ChangePartitionDescriptor":
        "evidence-streams-change-feed.md",
    "SourceProjectionRegistryEvent":
        "evidence-streams-change-feed.md",
    "EvidenceAuthorityChangeProjectionEvent":
        "evidence-streams-change-feed.md",
    "EvidenceChangeCoverageCheckpoint":
        "evidence-streams-change-feed.md",

    "ResponseCaptureReservation":
        "assistant-response-evidence-binding.md",
    "ResponseCaptureEvent":
        "assistant-response-evidence-binding.md",
    "AssistantResponseBinding":
        "assistant-response-evidence-binding.md",
    "DeliveryObservationEvent":
        "assistant-response-evidence-binding.md",
}

REQUIRED_FRONT_MATTER = {
    "relaylm_doc_type",
    "relaylm_authority",
    "relaylm_status",
    "relaylm_volatility",
    "relaylm_owner",
    "relaylm_update_trigger",
    "relaylm_not_authoritative_for",
    "relaylm_current_status_source",
}

FORBIDDEN_STALE_TERMS = {
    "relaylm.protected_payload_binding.v1",
    "protected_payload_binding_ids",
    "source_event_id_or_pending_attempt_id",
    "assistant_default_ephemeral",
    "IngressCoverageCheckpoint",
    "current_session_read",
    "terminal_aborted",
    "PR-612-aligned design-complete review candidate",
}

REQUIRED_ANCHORS = {
    "ProtectedPayloadBindingAttestation v1",
    "ReplayResolution v1",
    "SourceProjectionRegistryEvent v1",
    "DeliveryObservationEvent v1",
    "authority_snapshot_digest",
    "change_partition_watermarks",
    "rejected_purged_exact_replay",
    "capture_attempt_mark_abandoned",
    "change_set_mark_complete",
    "source_projection_registry_retire_visibility",
}


def parse_front_matter(text: str) -> set[str]:
    if not text.startswith("---\n"):
        return set()
    end = text.find("\n---\n", 4)
    if end < 0:
        return set()
    keys: set[str] = set()
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_]+):", line)
        if match:
            keys.add(match.group(1))
    return keys


def exact_field_line_present(text: str, field: str) -> bool:
    return bool(re.search(rf"(?m)^{re.escape(field)}$", text))


def load_validator(root: Path):
    validator_path = root / "scripts" / "relaylm_contract1_v7_validate.py"
    spec = importlib.util.spec_from_file_location(
        "contract1_v7_validator",
        validator_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load fixture validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root: Path, verbose: bool = False) -> int:
    errors: list[str] = []

    contracts_dir = root / "docs" / "contracts"
    schemas_dir = root / "docs" / "contracts" / "schemas" / "contract1-v7"
    bundle_path = schemas_dir / "relaylm-contract1-v7.bundle.schema.json"
    catalog_path = schemas_dir / "schema-catalog.json"

    contract_files = sorted(contracts_dir / name for name in set(OWNER_FILES.values()))
    if len(contract_files) != 6:
        errors.append(
            f"expected 6 contract files, found {len(contract_files)}"
        )

    contract_texts = {
        path.name: path.read_text(encoding="utf-8")
        for path in contract_files
    }
    combined_text = "\n".join(contract_texts.values())

    for name, text in contract_texts.items():
        missing = REQUIRED_FRONT_MATTER - parse_front_matter(text)
        if missing:
            errors.append(
                f"{name}: missing front-matter fields {sorted(missing)}"
            )
        if "relaylm_status: target" not in text:
            errors.append(f"{name}: target status marker is missing")
        if "**Status:** Target contract." not in text:
            errors.append(f"{name}: target-contract opening status is missing")

    for term in sorted(FORBIDDEN_STALE_TERMS):
        if term in combined_text:
            errors.append(f"stale term remains in contract prose: {term}")

    for anchor in sorted(REQUIRED_ANCHORS):
        if anchor not in combined_text:
            errors.append(f"required architecture anchor missing: {anchor}")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(bundle)
    definitions: dict[str, dict] = {}
    part_paths = sorted(schemas_dir.glob("relaylm-contract1-v7.part-*.schema.json"))
    if not part_paths:
        errors.append("schema bundle parts are missing")
    for part_path in part_paths:
        part = json.loads(part_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(part)
        overlap = set(definitions) & set(part.get("$defs", {}))
        if overlap:
            errors.append(
                f"duplicate definitions across schema parts: {sorted(overlap)}"
            )
        definitions.update(part.get("$defs", {}))
    referenced_definitions = set(bundle.get("$defs", {}))
    if referenced_definitions != set(definitions):
        errors.append(
            "bundle/part definition mismatch: "
            f"missing={sorted(referenced_definitions - set(definitions))}, "
            f"extra={sorted(set(definitions) - referenced_definitions)}"
        )

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog.get("schemas", [])
    entry_names = [entry.get("definition") for entry in entries]
    if len(entry_names) != len(set(entry_names)):
        errors.append("schema catalog contains duplicate definitions")

    for definition, owner_file in OWNER_FILES.items():
        if definition not in definitions:
            errors.append(f"bundle is missing top-level definition {definition}")
            continue
        if definition not in entry_names:
            errors.append(f"catalog is missing top-level definition {definition}")
        if owner_file not in contract_texts:
            errors.append(
                f"owner contract {owner_file} for {definition} is missing"
            )
            continue

        schema = definitions[definition]
        schema_id = (
            schema.get("properties", {})
            .get("schema", {})
            .get("const")
        )
        if not schema_id:
            errors.append(
                f"{definition}: top-level definition has no schema const"
            )
            continue

        owner_text = contract_texts[owner_file]
        if schema_id not in owner_text:
            errors.append(
                f"{definition}: schema ID {schema_id} is absent from "
                f"{owner_file}"
            )

        for field in schema.get("required", []):
            if not exact_field_line_present(owner_text, field):
                errors.append(
                    f"{definition}: required field {field!r} is absent as an "
                    f"exact field line in {owner_file}"
                )

    expected_defs = set(OWNER_FILES)
    catalog_defs = set(entry_names)
    if catalog_defs != expected_defs:
        missing = expected_defs - catalog_defs
        extra = catalog_defs - expected_defs
        if missing:
            errors.append(f"catalog missing definitions: {sorted(missing)}")
        if extra:
            errors.append(f"catalog has unexpected top-level definitions: {sorted(extra)}")

    # Each catalog entry must resolve directly through the schema bundle: no
    # standalone per-artifact wrapper file is published. The catalog "id" is
    # a JSON-pointer fragment against the bundle's own $id, and that pointer
    # must land on a real $defs entry that the bundle re-exports from a part.
    bundle_id = bundle.get("$id")
    for entry in entries:
        definition = entry["definition"]
        expected_id = f"{bundle_id}#/$defs/{definition}"
        if entry.get("id") != expected_id:
            errors.append(
                f"{definition}: catalog id does not resolve directly through "
                f"the schema bundle (expected {expected_id!r}, "
                f"found {entry.get('id')!r})"
            )
        if definition not in bundle.get("$defs", {}):
            errors.append(
                f"{definition}: catalog entry has no matching bundle $defs entry"
            )
        if definition not in definitions:
            errors.append(
                f"{definition}: catalog entry has no matching schema-part definition"
            )

    # Every exact top-level schema mentioned by prose must exist in the bundle.
    prose_schema_ids = set(
        re.findall(r"(?m)^\s{4}(relaylm\.[a-z0-9_.-]+\.v1)\s*$", combined_text)
    )
    bundle_schema_ids = {
        schema.get("properties", {}).get("schema", {}).get("const")
        for schema in definitions.values()
        if isinstance(schema, dict)
    }
    bundle_schema_ids.discard(None)
    unknown_prose_ids = prose_schema_ids - bundle_schema_ids
    if unknown_prose_ids:
        errors.append(
            "prose names schema IDs absent from bundle: "
            f"{sorted(unknown_prose_ids)}"
        )

    validator_module = load_validator(root)
    fixture_result = validator_module.run(root, verbose=False)
    if fixture_result != 0:
        errors.append("fixture validator failed")

    if errors:
        print("Contract 1 v7 prose/schema equivalence FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Contract 1 v7 prose/schema equivalence PASS: "
        f"{len(contract_files)} contract files, "
        f"{len(definitions)} bundle definitions across {len(part_paths)} parts, "
        f"{len(entries)} catalog-resolved top-level definitions, "
        f"{len(prose_schema_ids)} prose schema IDs."
    )
    if verbose:
        for definition in sorted(OWNER_FILES):
            print(
                f"PASS {definition}: "
                f"{OWNER_FILES[definition]}"
            )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    return run(args.root, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
