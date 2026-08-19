from __future__ import annotations

from pathlib import Path

from tools.repository_authority import load_declarations
from tools.repository_docs import (
    PERSISTENT_PROJECTIONS,
    PROJECTION_SCHEMA_VERSION,
    generate,
    package_version,
    provenance_of,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FROZEN_INPUT = "0" * 40


def test_every_persistent_projection_is_materialized() -> None:
    for name in PERSISTENT_PROJECTIONS:
        assert (REPOSITORY_ROOT / name).is_file()


def test_a_materialized_projection_records_the_input_it_was_generated_from() -> None:
    for name in PERSISTENT_PROJECTIONS:
        provenance = provenance_of((REPOSITORY_ROOT / name).read_text(encoding="utf-8"))

        assert provenance["projection-schema-version"] == str(PROJECTION_SCHEMA_VERSION)
        assert len(provenance["source-commit"]) == 40
        assert all(
            character in "0123456789abcdef" for character in provenance["source-commit"]
        )
        assert provenance["package-version"]


def test_generation_from_current_authority_is_deterministic() -> None:
    first = generate(REPOSITORY_ROOT, source_commit=FROZEN_INPUT)
    second = generate(REPOSITORY_ROOT, source_commit=FROZEN_INPUT)

    assert first == second


def test_a_generated_projection_covers_every_semantic_owner() -> None:
    text = generate(REPOSITORY_ROOT, source_commit=FROZEN_INPUT)["ARCHITECTURE.md"]

    for declaration in load_declarations(REPOSITORY_ROOT):
        assert f"### {declaration.id}" in text


def test_the_generated_projection_reports_the_release_owned_version() -> None:
    text = generate(REPOSITORY_ROOT, source_commit=FROZEN_INPUT)["ARCHITECTURE.md"]

    assert f"<!-- package-version: {package_version(REPOSITORY_ROOT)} -->" in text


def test_normal_transactions_are_not_required_to_regenerate_persistent_docs() -> None:
    committed = (REPOSITORY_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    provenance = provenance_of(committed)

    regenerated = generate(
        REPOSITORY_ROOT, source_commit=provenance["source-commit"]
    )["ARCHITECTURE.md"]

    # Drift against a past release input is expected between release boundaries and
    # is verified at the release boundary, not by every semantic transaction.
    assert provenance_of(regenerated)["source-commit"] == provenance["source-commit"]
