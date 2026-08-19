from __future__ import annotations

from pathlib import Path

from tools.repository_authority import (
    PROHIBITED_AGGREGATES,
    REQUIRED_LIVE_FACTS,
    agent_contract_errors,
    consumers_of,
    documentation_coverage_errors,
    load_declarations,
    read_agent_contract,
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


def test_the_repository_agent_contract_is_valid() -> None:
    assert agent_contract_errors(REPOSITORY_ROOT) == ()


def test_the_bootstrap_read_order_reaches_workflow_owner_and_freshness() -> None:
    contract = read_agent_contract(REPOSITORY_ROOT)
    paths = [step.path for step in contract.bootstrap]

    assert paths[0] == ".ai/README.md"
    assert ".ai/agent-contract.yaml" in paths
    assert "docs/reference/development-workflow.md" in paths
    assert ".ai/authority" in paths
    for step in contract.bootstrap:
        assert (REPOSITORY_ROOT / step.path).exists()
        assert step.purpose.strip()


def test_live_repository_facts_are_never_persistent_authority() -> None:
    contract = read_agent_contract(REPOSITORY_ROOT)

    for fact in REQUIRED_LIVE_FACTS:
        assert contract.freshness_of(fact) == "live"
        assert contract.is_persistent_authority(fact) is False


def test_semantic_ownership_is_persistent_repository_authority() -> None:
    contract = read_agent_contract(REPOSITORY_ROOT)

    assert contract.freshness_of("semantic_ownership") == "repository"
    assert contract.is_persistent_authority("semantic_ownership") is True


def test_a_stale_handoff_is_classified_as_history_rather_than_authority() -> None:
    contract = read_agent_contract(REPOSITORY_ROOT)

    assert contract.freshness_of("handoff_prompt_state") == "historical"
    assert contract.is_persistent_authority("handoff_prompt_state") is False
    assert contract.is_persistent_authority("projection_output") is False


def test_evidence_is_referenced_rather_than_copied() -> None:
    contract = read_agent_contract(REPOSITORY_ROOT)

    assert contract.freshness_of("merged_evidence") == "evidence"
    assert contract.is_persistent_authority("merged_evidence") is True


def test_evidence_is_owned_by_its_producer() -> None:
    declarations = load_declarations(REPOSITORY_ROOT)
    producers = {
        record.id: declaration.id
        for declaration in declarations
        for record in declaration.evidence
    }

    assert producers, "no evidence record is declared"
    for declaration in declarations:
        for reference in declaration.evidence_refs:
            assert producers[reference] != declaration.id


def test_a_consumer_references_evidence_instead_of_copying_it() -> None:
    declarations = {
        declaration.id: declaration for declaration in load_declarations(REPOSITORY_ROOT)
    }
    calibration = declarations["calibration"]
    producer = declarations["actual_model_evaluation"]
    produced = {record.id for record in producer.evidence}

    assert calibration.evidence == ()
    assert set(calibration.evidence_refs) <= produced
    assert "actual_model_evaluation" in calibration.depends_on


def test_no_evidence_surface_is_claimed_outside_its_producer() -> None:
    declarations = load_declarations(REPOSITORY_ROOT)
    evidence_surfaces = {
        surface: declaration.id
        for declaration in declarations
        for record in declaration.evidence
        for surface in record.surfaces
    }

    for declaration in declarations:
        declared = {
            *declaration.canonical_surfaces,
            *declaration.references,
            *declaration.implementation,
            *declaration.tests,
            *declaration.annotations,
        }
        assert not (declared & set(evidence_surfaces))
