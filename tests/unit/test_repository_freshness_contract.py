from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.repository_authority import (
    AGENT_CONTRACT_PATH,
    REQUIRED_FRESHNESS_CLASSES,
    REQUIRED_LIVE_FACTS,
    AuthorityError,
    agent_contract_errors,
    read_agent_contract,
)


def _classes() -> dict[str, object]:
    return {
        "live": {
            "summary": "Re-fetch from the live repository or host before use.",
            "persistent_authority": False,
        },
        "repository": {
            "summary": "Owned by committed repository authority at current HEAD.",
            "persistent_authority": True,
        },
        "evidence": {
            "summary": "Immutable merged evidence identified by evidence id.",
            "persistent_authority": True,
        },
        "historical": {
            "summary": "A past snapshot, never current authority.",
            "persistent_authority": False,
        },
    }


def _facts() -> dict[str, str]:
    return {
        "repository_head": "live",
        "open_pull_requests": "live",
        "ci_check_state": "live",
        "issue_state": "live",
        "semantic_ownership": "repository",
        "merged_evidence": "evidence",
        "handoff_prompt_state": "historical",
    }


def _write(root: Path, contract: dict[str, object]) -> Path:
    path = root / AGENT_CONTRACT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return path


def _bootstrap(root: Path) -> list[dict[str, str]]:
    entry = root / ".ai" / "README.md"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("# root\n", encoding="utf-8")
    workflow = root / "docs" / "reference" / "development-workflow.md"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("# workflow\n", encoding="utf-8")
    return [
        {"path": ".ai/README.md", "purpose": "Authority root entry point."},
        {"path": "docs/reference/development-workflow.md", "purpose": "Transaction workflow."},
    ]


def _contract(root: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "bootstrap": _bootstrap(root),
        "freshness": {"classes": _classes(), "facts": _facts()},
    }


def test_a_complete_agent_contract_is_valid(tmp_path: Path) -> None:
    _write(tmp_path, _contract(tmp_path))

    assert agent_contract_errors(tmp_path) == ()


def test_the_bootstrap_read_order_is_repository_authority(tmp_path: Path) -> None:
    _write(tmp_path, _contract(tmp_path))

    contract = read_agent_contract(tmp_path)

    assert [step.path for step in contract.bootstrap] == [
        ".ai/README.md",
        "docs/reference/development-workflow.md",
    ]
    assert contract.bootstrap[0].purpose == "Authority root entry point."


def test_a_missing_agent_contract_is_reported(tmp_path: Path) -> None:
    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: agent contract is missing",
    )


def test_freshness_of_a_fact_resolves_to_its_declared_class(tmp_path: Path) -> None:
    _write(tmp_path, _contract(tmp_path))

    contract = read_agent_contract(tmp_path)

    assert contract.freshness_of("repository_head") == "live"
    assert contract.freshness_of("semantic_ownership") == "repository"
    assert contract.is_persistent_authority("semantic_ownership") is True
    assert contract.is_persistent_authority("repository_head") is False


def test_an_unclassified_fact_is_refused_rather_than_guessed(tmp_path: Path) -> None:
    _write(tmp_path, _contract(tmp_path))

    contract = read_agent_contract(tmp_path)

    with pytest.raises(AuthorityError):
        contract.freshness_of("merge_queue_position")


def test_every_required_live_fact_must_be_classified(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    facts = dict(_facts())
    del facts["ci_check_state"]
    contract["freshness"]["facts"] = facts  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: freshness.facts must classify 'ci_check_state'",
    )


def test_a_required_live_fact_must_not_be_persistent_authority(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    facts = dict(_facts())
    facts["repository_head"] = "repository"
    contract["freshness"]["facts"] = facts  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: freshness fact 'repository_head' must be classified"
        " as a non-persistent class that is re-fetched live",
    )


def test_a_fact_must_name_a_declared_freshness_class(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    facts = dict(_facts())
    facts["semantic_ownership"] = "durable"
    contract["freshness"]["facts"] = facts  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: freshness fact 'semantic_ownership' names undeclared"
        " class 'durable'",
    )


def test_the_required_freshness_classes_must_be_declared(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    classes = _classes()
    del classes["historical"]
    contract["freshness"]["classes"] = classes  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: freshness.classes must declare 'historical'",
    )


def test_a_freshness_class_must_declare_whether_it_is_persistent_authority(
    tmp_path: Path,
) -> None:
    contract = _contract(tmp_path)
    classes = _classes()
    classes["historical"] = {"summary": "A past snapshot."}
    contract["freshness"]["classes"] = classes  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: freshness class 'historical' persistent_authority"
        " must be a boolean",
    )


def test_a_bootstrap_step_must_point_at_an_existing_surface(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    contract["bootstrap"] = [  # type: ignore[index]
        {"path": ".ai/missing.md", "purpose": "Nothing."}
    ]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: bootstrap path '.ai/missing.md' does not exist",
    )


def test_the_bootstrap_read_order_must_not_repeat_a_surface(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    steps = _bootstrap(tmp_path)
    contract["bootstrap"] = [*steps, steps[0]]  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: bootstrap repeats '.ai/README.md'",
    )


def test_the_bootstrap_read_order_must_not_be_empty(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    contract["bootstrap"] = []  # type: ignore[index]
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: bootstrap must declare at least one read step",
    )


def test_unknown_agent_contract_fields_are_rejected(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    contract["current_head"] = "61113e759498208716d85b3aca6db57e9c455195"
    _write(tmp_path, contract)

    assert agent_contract_errors(tmp_path) == (
        ".ai/agent-contract.yaml: unknown field 'current_head'",
    )


def test_the_required_contract_constants_are_frozen() -> None:
    assert REQUIRED_FRESHNESS_CLASSES == ("evidence", "historical", "live", "repository")
    assert REQUIRED_LIVE_FACTS == (
        "ci_check_state",
        "issue_state",
        "open_pull_requests",
        "repository_head",
    )


def test_reading_an_invalid_agent_contract_is_refused(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    contract["schema_version"] = 7
    _write(tmp_path, contract)

    with pytest.raises(AuthorityError):
        read_agent_contract(tmp_path)
