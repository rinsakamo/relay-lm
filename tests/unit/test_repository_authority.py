from __future__ import annotations

from pathlib import Path

from tools.repository_authority import (
    PROHIBITED_AGGREGATES,
    consumers_of,
    documentation_coverage_errors,
    load_declarations,
    validate_repository,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_repository_authority_declarations_are_valid() -> None:
    assert validate_repository(REPOSITORY_ROOT) == ()


def test_every_current_document_has_exactly_one_semantic_owner() -> None:
    assert documentation_coverage_errors(REPOSITORY_ROOT) == ()


def test_no_hand_maintained_authority_aggregate_remains() -> None:
    for aggregate in PROHIBITED_AGGREGATES:
        assert not (REPOSITORY_ROOT / aggregate).exists()


def test_the_global_authority_view_is_reconstructable_from_owner_local_facts() -> None:
    declarations = load_declarations(REPOSITORY_ROOT)
    owners = {declaration.id for declaration in declarations}

    assert {
        "actual_model_evaluation",
        "calibration",
        "cognitive_budget",
        "cognitive_turn",
        "context_compiler",
        "continuity_context",
        "crystallization",
        "evaluation",
        "memory_provenance",
        "persistence",
        "provider_and_api",
        "release_engineering",
        "runtime_configuration",
        "state_and_validation",
    } <= owners

    derived = consumers_of(declarations)
    assert "calibration" in derived["actual_model_evaluation"]
    assert derived["development_workflow"] == ("repository_authority",)


def test_each_owner_declaration_is_written_only_by_its_own_semantic_owner() -> None:
    declarations = load_declarations(REPOSITORY_ROOT)

    for declaration in declarations:
        assert declaration.path == f".ai/authority/{declaration.id}.yaml"
