from __future__ import annotations

import json
import re
from pathlib import Path

from tools.repository_authority import load_declarations, qualification_fingerprint
from tools.repository_qualification_coverage import qualification_coverage_gaps


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FREEZE_SPEC_PATH = (
    REPOSITORY_ROOT
    / "evaluation"
    / "actual_model"
    / "qualifications"
    / "core-semantic-v1.json"
)
_EXPECTED_KEYS = {
    "format_version",
    "id",
    "roots",
    "expected_fingerprint",
}
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _reject_duplicate_object_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _load_freeze_spec() -> dict[str, object]:
    document = json.loads(
        FREEZE_SPEC_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_object_members,
    )
    assert isinstance(document, dict)
    assert set(document) == _EXPECTED_KEYS
    assert document["format_version"] == 1
    assert document["id"] == "core-semantic-v1"
    assert document["roots"] == ["crystallization", "runtime_configuration"]
    expected = document["expected_fingerprint"]
    assert isinstance(expected, str)
    assert _FINGERPRINT_RE.fullmatch(expected)
    return document


def test_core_semantic_qualification_coverage_has_no_silent_implementation_omissions() -> None:
    spec = _load_freeze_spec()
    declarations = load_declarations(REPOSITORY_ROOT)
    assert qualification_coverage_gaps(
        declarations,
        roots=tuple(spec["roots"]),
    ) == ()


def test_core_semantic_qualification_fingerprint_matches_freeze() -> None:
    spec = _load_freeze_spec()
    expected = spec["expected_fingerprint"]
    roots = tuple(spec["roots"])
    actual = qualification_fingerprint(
        REPOSITORY_ROOT,
        load_declarations(REPOSITORY_ROOT),
        roots=roots,
    )

    assert actual == expected, (
        "core semantic qualification fingerprint mismatch:\n"
        f"expected: {expected}\n"
        f"actual:   {actual}"
    )
