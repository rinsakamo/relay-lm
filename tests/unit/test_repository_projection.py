from __future__ import annotations

from pathlib import Path

from tools.repository_authority import load_declarations
from tools.repository_projection import (
    PROJECTION_DIRECTORY,
    load_recipes,
    render_projection,
    validate_recipes,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_projection_recipes_are_valid() -> None:
    assert validate_recipes(REPOSITORY_ROOT) == ()


def test_the_high_value_developer_views_have_stored_recipes() -> None:
    identifiers = {recipe.id for recipe in load_recipes(REPOSITORY_ROOT)}

    assert {
        "architecture-overview",
        "consumer-map",
        "dependency-map",
        "evidence-map",
        "repository-status",
        "semantic-owner-map",
    } <= identifiers


def test_every_recipe_renders_deterministically_from_current_authority() -> None:
    for recipe in load_recipes(REPOSITORY_ROOT):
        first = render_projection(REPOSITORY_ROOT, recipe.id)
        second = render_projection(REPOSITORY_ROOT, recipe.id)

        assert first == second
        assert first.startswith(f"# {recipe.id}\n")
        assert "do not commit this output" in first


def test_no_rendered_projection_is_committed() -> None:
    stored = sorted(
        path.name for path in (REPOSITORY_ROOT / PROJECTION_DIRECTORY).iterdir()
    )

    assert stored == [f"{name}.yaml" for name in sorted(
        recipe.id for recipe in load_recipes(REPOSITORY_ROOT)
    )]


def test_a_rendered_projection_never_embeds_live_repository_state() -> None:
    for recipe in load_recipes(REPOSITORY_ROOT):
        output = render_projection(REPOSITORY_ROOT, recipe.id)

        for token in output.replace("`", " ").split():
            assert not (
                len(token) == 40
                and all(character in "0123456789abcdef" for character in token)
            )


def test_the_dependency_view_is_reconstructed_from_owner_local_facts() -> None:
    output = render_projection(REPOSITORY_ROOT, "dependency-map")

    assert "calibration --> actual_model_evaluation" in output
    assert "cognitive_turn --> context_compiler" in output
    assert "consumed_by" not in output


def test_a_status_view_names_the_live_facts_it_cannot_derive() -> None:
    output = render_projection(REPOSITORY_ROOT, "repository-status")

    assert (
        "Live inputs the agent must fetch: ci_check_state, issue_comments,"
        " issue_state, open_pull_requests, repository_head" in output
    )


def test_projection_recipes_are_owned_by_the_repository_authority_owner() -> None:
    owner = next(
        declaration
        for declaration in load_declarations(REPOSITORY_ROOT)
        if declaration.id == "repository_authority"
    )
    recipes = {f"{PROJECTION_DIRECTORY}/{recipe.id}.yaml" for recipe in load_recipes(REPOSITORY_ROOT)}

    assert recipes <= set(owner.canonical_surfaces)
