#!/usr/bin/env python3
"""Lock Contract 1 v7 negative fixtures to their reviewed failure intents."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXPECTED = {
    'artifact_revalidate_after_supersede.json': 'custom: revalidate allowed only after invalidate',
    'assistant_source_missing_binding.json': 'schema: assistant_response requires non-null binding',
    'authority_scope_missing_operation.json': 'custom: AuthorityScope does not allow initialize_admitted',
    'authorization_duplicate_partition_watermark.json': 'custom: duplicate partition watermark key',
    'change_set_counts_abort_projection.json': 'custom: abort cannot satisfy projection plan',
    'delivery_cohort_not_subset.json': 'custom: delivery cohort must be configured-audience subset',
    'delivery_observation_outside_cohort.json': 'custom: recipient selector must be a subset of delivery cohort',
    'delivery_revision1_has_previous.json': 'schema: revision 1 requires null expected previous',
    'duplicate_managed_response_source_events.json': 'custom: one managed response identity has one SourceEvent',
    'evidence_space_bootstrap_change_set.json': 'schema: bootstrap descriptor requires null change-set ref',
    'export_grant_wrong_destination.json': 'schema: export purpose allows only local export/encrypted backup',
    'failed_integrity_grant_still_granted.json': 'custom: failed integrity cannot keep granted content lifecycle',
    'full_audit_mixed_metadata_projection.json': 'custom: full_authorized_audit must be the only selector',
    'metadata_revision_forbidden_field.json': 'custom: metadata corrected_fields allowlist violation',
    'omitted_secret_with_digest.json': 'schema: omitted part requires null content digest/length',
    'payload_attestation_digest_mismatch.json': 'custom: payload binding digest mismatch',
    'projection_abort_leaks_source.json': 'schema: aborted projection requires empty refs',
    'protected_part_missing_payload_attestation.json': 'custom: protected part binding coverage mismatch',
    'quarantined_source_normal_projection.json': 'custom: quarantined admission may not project normal candidate availability',
    'rejected_with_source_event.json': 'schema: rejected outcome requires null source/governance/change-set refs',
    'response_binding_bad_digest.json': 'custom: canonical binding digest mismatch',
    'response_ranges_overlap.json': 'custom: accepted ranges overlap',
    'retained_until_revoked_with_deadline.json': 'schema: retained_until_revoked requires null access/purge deadlines',
    'source_manifest_bad_digest.json': 'custom: canonical source manifest digest mismatch',
}


def validate(root: Path) -> list[str]:
    invalid_dir = root / 'docs/contracts/fixtures/contract1-v7/invalid'
    actual_files = {path.name for path in invalid_dir.glob('*.json')}
    errors: list[str] = []
    if actual_files != set(EXPECTED):
        errors.append(
            f"fixture filename set mismatch: missing={sorted(set(EXPECTED)-actual_files)}, "
            f"extra={sorted(actual_files-set(EXPECTED))}"
        )
    for name, expected in EXPECTED.items():
        path = invalid_dir / name
        if not path.is_file():
            continue
        actual = json.loads(path.read_text(encoding='utf-8')).get('expected_failure')
        if actual != expected:
            errors.append(f"{name}: expected_failure must be {expected!r}, found {actual!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    errors = validate(args.root)
    if len(EXPECTED) != 24:
        errors.append(f"registry must contain exactly 24 fixtures, found {len(EXPECTED)}")
    if errors:
        print('Contract 1 v7 fixture registry guard FAILED', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1
    label = 'self-test ' if args.self_test else ''
    print(f'Contract 1 v7 fixture registry guard {label}PASS: 24 reviewed failure intents locked.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
