from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.repository_authority import AUTHORITY_DIRECTORY
from tools.repository_projection import (
    INCLUDE_SELECTORS,
    OUTPUT_FORMATS,
    PROHIBITED_INFERENCES,
    PROJECTION_DIRECTORY,
    ProjectionError,
    load_recipes,
    render_projection,
    validate_recipes,
)

CONTRACT = {
    "schema_version": 1,
    "bootstrap": [{"path": ".ai/README.md", "purpose": "Entry point."}],
    "freshness": {
        "classes": {
            "live": {"summary": "Re-fetch.", "persistent_authority": False},
            "repository": {"summary": "Committed.", "persistent_authority": True},
            "evidence": {"summary": "Merged evidence.", "persistent_authority": True},
            "historical": {"summary": "Past snapshot.", "persistent_authority": False},
        },
        "facts": {
            "repository_head": "live",
            "open_pull_requests": "live",
            "ci_check_state": "live",
            "issue_state": "live",
            "semantic_ownership": "repository",
        },
    },
}


def _repository(tmp_path: Path) -> Path:
    (tmp_path / ".ai").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai" / "README.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / ".ai" / "agent-contract.yaml").write_text(
        yaml.safe_dump(CONTRACT, sort_keys=False), encoding="utf-8"
    )

    authority = tmp_path / AUTHORITY_DIRECTORY
    authority.mkdir(parents=True, exist_ok=True)
    for identifier, issue, depends in (
        ("actual_model_evaluation", 1386, []),
        ("cognitive_budget", 1387, []),
        ("calibration", 1388, ["actual_model_evaluation", "cognitive_budget"]),
    ):
        surface = tmp_path / "docs" / "contracts" / f"{identifier}.md"
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text("surface\n", encoding="utf-8")
        declaration = {
            "schema_version": 1,
            "id": identifier,
            "summary": f"Authority for {identifier}.",
            "owner_issue": issue,
            "canonical_surfaces": [f"docs/contracts/{identifier}.md"],
        }
        if depends:
            declaration["depends_on"] = depends
        (authority / f"{identifier}.yaml").write_text(
            yaml.safe_dump(declaration, sort_keys=False), encoding="utf-8"
        )
    return tmp_path


def _recipe(tmp_path: Path, recipe: dict[str, object], *, name: str | None = None) -> Path:
    directory = tmp_path / PROJECTION_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stem = name if name is not None else str(recipe["id"])
    path = directory / f"{stem}.yaml"
    path.write_text(yaml.safe_dump(recipe, sort_keys=False), encoding="utf-8")
    return path


def _dependency_recipe() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "dependency-map",
        "summary": "Current dependency graph across semantic owners.",
        "inputs": [".ai/authority"],
        "freshness_requirements": ["repository_head", "open_pull_requests"],
        "include": ["semantic_owners", "dependencies"],
        "prohibit": ["infer_current_status_from_historical_snapshot"],
        "output_hint": {"preferred": "mermaid"},
    }


def test_a_minimal_recipe_set_is_valid(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())

    assert validate_recipes(tmp_path) == ()


def test_a_recipe_file_name_must_equal_its_recipe_id(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe(), name="dependency_map")

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency_map.yaml: file stem must equal recipe id"
        " 'dependency-map'",
    )


def test_a_recipe_input_must_exist(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["inputs"] = [".ai/missing"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: input '.ai/missing' matches nothing",
    )


def test_a_recipe_freshness_requirement_must_be_a_classified_fact(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["freshness_requirements"] = ["merge_queue_position"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: freshness_requirements"
        " 'merge_queue_position' is not classified by .ai/agent-contract.yaml",
    )


def test_a_recipe_does_not_restate_the_freshness_class_of_a_fact(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["freshness"] = {"repository_head": "live"}
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: unknown field 'freshness'",
    )


def test_an_include_selector_must_come_from_the_declared_vocabulary(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["include"] = ["semantic_owners", "dependencies", "current_status"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: include 'current_status' is not a"
        " declared selector",
    )


def test_a_recipe_must_select_semantic_owners_as_its_row_scope(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["include"] = ["dependencies"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: include must contain 'semantic_owners'",
    )


def test_a_recipe_summary_is_required(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["summary"] = ""
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: summary must be a non-empty string",
    )


def test_a_prohibited_inference_must_come_from_the_declared_vocabulary(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["prohibit"] = ["guessing"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: prohibit 'guessing' is not a declared"
        " prohibited inference",
    )


def test_a_recipe_must_prohibit_treating_stale_state_as_current_authority(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["prohibit"] = []
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: prohibit must declare at least one"
        " prohibited inference",
    )


def test_an_output_hint_must_name_a_supported_format(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["output_hint"] = {"preferred": "pdf"}
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: output_hint.preferred 'pdf' is not a"
        " supported format",
    )


def test_a_mermaid_projection_requires_a_relationship_selector(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["include"] = ["semantic_owners", "summary"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: a mermaid projection must include"
        " 'dependencies' or 'consumers'",
    )


def test_a_recipe_id_uses_a_stable_lowercase_grammar(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["id"] = "Dependency_Map"
    _recipe(tmp_path, recipe, name="Dependency_Map")

    assert validate_recipes(tmp_path) == (
        ".ai/projections/Dependency_Map.yaml: id 'Dependency_Map' must match"
        " '^[a-z][a-z0-9-]*$'",
    )


def test_an_include_selector_must_not_be_repeated(tmp_path: Path) -> None:
    _repository(tmp_path)
    recipe = _dependency_recipe()
    recipe["include"] = ["semantic_owners", "dependencies", "dependencies"]
    _recipe(tmp_path, recipe)

    assert validate_recipes(tmp_path) == (
        ".ai/projections/dependency-map.yaml: include repeats 'dependencies'",
    )


def test_the_declared_vocabularies_are_frozen() -> None:
    assert INCLUDE_SELECTORS == (
        "annotations",
        "canonical_surfaces",
        "consumers",
        "dependencies",
        "evidence",
        "evidence_refs",
        "implementation",
        "owner_issue",
        "references",
        "semantic_owners",
        "summary",
        "tests",
    )
    assert PROHIBITED_INFERENCES == (
        "copy_live_state_into_authority",
        "infer_current_status_from_historical_snapshot",
        "invent_unowned_surface",
        "treat_stale_handoff_as_current_authority",
    )
    assert OUTPUT_FORMATS == ("markdown", "mermaid", "table")


def test_a_mermaid_projection_renders_dependency_edges(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())

    output = render_projection(tmp_path, "dependency-map")

    assert output == (
        "# dependency-map\n"
        "\n"
        "Current dependency graph across semantic owners.\n"
        "\n"
        "Ephemeral projection reconstructed from owner-local authority."
        " Not repository authority; do not commit this output.\n"
        "\n"
        "Live inputs the agent must fetch: open_pull_requests, repository_head\n"
        "\n"
        "Prohibited: infer_current_status_from_historical_snapshot\n"
        "\n"
        "```mermaid\n"
        "graph LR\n"
        "  calibration --> actual_model_evaluation\n"
        "  calibration --> cognitive_budget\n"
        "  actual_model_evaluation\n"
        "  cognitive_budget\n"
        "```\n"
    )


def test_a_table_projection_renders_selected_columns(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(
        tmp_path,
        {
            "schema_version": 1,
            "id": "semantic-owner-map",
            "summary": "Semantic owners and their owning Issues.",
            "inputs": [".ai/authority"],
            "freshness_requirements": ["repository_head"],
            "include": ["semantic_owners", "owner_issue", "summary"],
            "prohibit": ["treat_stale_handoff_as_current_authority"],
            "output_hint": {"preferred": "table"},
        },
    )

    output = render_projection(tmp_path, "semantic-owner-map")

    assert "| owner | issue | summary |" in output
    assert "| --- | --- | --- |" in output
    assert "| calibration | #1388 | Authority for calibration. |" in output
    assert output.index("| actual_model_evaluation") < output.index("| calibration")


def test_a_projection_is_deterministic(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())

    assert render_projection(tmp_path, "dependency-map") == render_projection(
        tmp_path, "dependency-map"
    )


def test_a_projection_never_embeds_live_repository_state(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())

    output = render_projection(tmp_path, "dependency-map")

    assert "Live inputs the agent must fetch" in output
    assert not any(
        len(token) == 40 and all(character in "0123456789abcdef" for character in token)
        for token in output.split()
    )


def test_consumers_are_derived_rather_than_declared_in_a_projection(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(
        tmp_path,
        {
            "schema_version": 1,
            "id": "consumer-map",
            "summary": "Derived reverse dependencies.",
            "inputs": [".ai/authority"],
            "freshness_requirements": ["repository_head"],
            "include": ["semantic_owners", "consumers"],
            "prohibit": ["treat_stale_handoff_as_current_authority"],
            "output_hint": {"preferred": "table"},
        },
    )

    output = render_projection(tmp_path, "consumer-map")

    assert "| actual_model_evaluation | calibration |" in output
    assert "| calibration |  |" in output


def test_rendering_an_unknown_recipe_is_refused(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())

    with pytest.raises(ProjectionError):
        render_projection(tmp_path, "status-map")


def test_recipes_load_in_deterministic_identifier_order(tmp_path: Path) -> None:
    _repository(tmp_path)
    _recipe(tmp_path, _dependency_recipe())
    second = _dependency_recipe()
    second["id"] = "architecture-overview"
    second["output_hint"] = {"preferred": "markdown"}
    _recipe(tmp_path, second)

    assert [recipe.id for recipe in load_recipes(tmp_path)] == [
        "architecture-overview",
        "dependency-map",
    ]
