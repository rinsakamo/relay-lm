from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from relaylm.v2_transfer_actual_model import build_source_learning_messages
from tools.v2_transfer_r2_source_learning_forensic import (
    R2_FROZEN_PREREGISTRATION_COMMIT,
    R2SourceLearningForensicError,
    classify_request_evidence,
    classify_source_response,
    forensic_report,
)
from tools.v2_transfer_r2_prereg import generate_families


def test_frozen_r2_source_packets_are_uniquely_identifiable_after_four_examples() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert len(report.families) == 16
    assert all(item.source_candidate_counts[-1] == 1 for item in report.families)
    assert report.source_unique_after_four == 16
    assert report.source_max_candidates_after_four == 1


def test_frozen_r2_source_prefix_counts_match_the_exact_seed_set() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert [item.source_candidate_counts for item in report.families] == [
        (24, 4, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 2, 1, 1),
        (24, 2, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 2, 1, 1),
        (24, 2, 1, 1),
        (24, 6, 2, 1),
        (24, 2, 1, 1),
    ]


def test_frozen_r2_target_packets_are_uniquely_identifiable_at_three_examples() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert report.target_unique_after_three == 16
    assert all(item.target_candidate_counts[-1] == 1 for item in report.families)
    assert [item.target_candidate_counts for item in report.families] == [
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 2, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
    ]


def test_source_prompt_names_fields_but_not_the_permutation_direction_equation() -> None:
    family = generate_families(R2_FROZEN_PREREGISTRATION_COMMIT)[0]
    system = build_source_learning_messages(family)[0]["content"]

    # The frozen prompt names the fields and shapes, but never states the
    # evaluator convention y[i] = x[permutation[i]] + offsets[i] (mod modulus).
    assert "permutation" in system
    assert "offsets" in system
    assert "modulus" in system
    assert "y[" not in system
    assert "x[" not in system
    assert "permutation[i]" not in system


def _inverse(permutation: tuple[int, ...]) -> tuple[int, ...]:
    inverse = [0] * len(permutation)
    for output_index, input_index in enumerate(permutation):
        inverse[input_index] = output_index
    return tuple(inverse)


def _response_content(*, permutation: tuple[int, ...], offsets: tuple[int, ...], modulus: int) -> str:
    return json.dumps(
        {
            "permutation": list(permutation),
            "offsets": list(offsets),
            "modulus": modulus,
        },
        separators=(",", ":"),
    )


def _evidence_line(*, family_index: int, content: str) -> str:
    return json.dumps(
        {
            "format_version": 1,
            "run_id": "test-run",
            "identity_fingerprint": "sha256:test",
            "order": family_index * 13,
            "question_id": f"r2-call-{family_index * 13:03d}",
            "content_fingerprint": "sha256:test-content",
            "session_id": f"family-{family_index:02d}",
            "attempt": 1,
            "evidence": {
                "kind": "model_exchange",
                "authority": "instrumentation_only",
                "plan_entry": {
                    "call_index": family_index * 13,
                    "family_index": family_index,
                    "regime": "shared" if family_index % 2 == 0 else "null",
                    "seed": 0,
                    "phase": "source-learning",
                    "arm": None,
                    "examples_visible": None,
                    "step_index": None,
                    "schema_kind": "source_structure",
                },
                "messages": [],
                "response": {
                    "content": content,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "response_id": "test",
                },
            },
        },
        separators=(",", ":"),
    )


def test_classifier_recognizes_semantically_exact_reverse_permutation_convention() -> None:
    families = generate_families(R2_FROZEN_PREREGISTRATION_COMMIT)
    family_index, family = next(
        (index, item)
        for index, item in enumerate(families)
        if _inverse(item.source_rule.permutation) != item.source_rule.permutation
    )
    content = _response_content(
        permutation=_inverse(family.source_rule.permutation),
        offsets=family.source_rule.offsets,
        modulus=family.modulus,
    )

    result = classify_source_response(family_index=family_index, content=content)

    assert result.category == "SEMANTICALLY_EXACT_REVERSE_PERMUTATION_OUTPUT_OFFSETS"
    assert result.canonical_examples_matched < 4
    assert result.reverse_output_offset_examples_matched == 4


def test_request_evidence_classifier_is_offline_hash_bound_and_complete(tmp_path: Path) -> None:
    families = generate_families(R2_FROZEN_PREREGISTRATION_COMMIT)
    reverse_index, reverse_family = next(
        (index, item)
        for index, item in enumerate(families)
        if _inverse(item.source_rule.permutation) != item.source_rule.permutation
    )
    lines: list[str] = []
    for family_index, family in enumerate(families):
        if family_index == reverse_index:
            permutation = _inverse(reverse_family.source_rule.permutation)
            offsets = reverse_family.source_rule.offsets
        else:
            permutation = family.source_rule.permutation
            offsets = family.source_rule.offsets
        lines.append(
            _evidence_line(
                family_index=family_index,
                content=_response_content(
                    permutation=permutation,
                    offsets=offsets,
                    modulus=family.modulus,
                ),
            )
        )
    path = tmp_path / "request-evidence.jsonl"
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()

    report = classify_request_evidence(path, expected_sha256=digest)

    assert report.source_response_count == 16
    assert report.exact_canonical_count == 15
    assert report.reverse_convention_count == 1
    assert report.other_valid_count == 0
    assert report.request_evidence_sha256 == digest

    with pytest.raises(R2SourceLearningForensicError, match="SHA-256 mismatch"):
        classify_request_evidence(path, expected_sha256="sha256:" + "0" * 64)
