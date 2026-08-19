#!/usr/bin/env python3
"""RelayLM v1 ephemeral projection recipes.

A projection recipe is a contract for reconstructing a developer-facing view
from owner-local authority plus live repository state. The recipe is stored;
the view is not.

    Store canonical facts and projection recipes, not transient views.

Rendering is deterministic and derives every fact from `.ai/authority/`. Facts
that cannot be derived from committed authority are named as live inputs the
agent must fetch, so a rendered projection never embeds a remembered HEAD, PR
list, or check result.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from tools.repository_authority import (
    AGENT_CONTRACT_PATH,
    AuthorityError,
    Declaration,
    consumers_of,
    load_declarations,
    read_agent_contract,
)

PROJECTION_DIRECTORY = ".ai/projections"
RECIPE_SCHEMA_VERSION = 1

#: Row and column selectors a recipe may request.
INCLUDE_SELECTORS = (
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

#: Inferences a recipe may forbid when the view is reconstructed.
PROHIBITED_INFERENCES = (
    "copy_live_state_into_authority",
    "infer_current_status_from_historical_snapshot",
    "invent_unowned_surface",
    "treat_stale_handoff_as_current_authority",
)

#: Output shapes the renderer supports.
OUTPUT_FORMATS = ("markdown", "mermaid", "table")

_RECIPE_ID_PATTERN = r"^[a-z][a-z0-9-]*$"
_RECIPE_ID_RE = re.compile(_RECIPE_ID_PATTERN)
_RECIPE_FIELDS = (
    "schema_version",
    "id",
    "summary",
    "inputs",
    "freshness_requirements",
    "include",
    "prohibit",
    "output_hint",
)
_OUTPUT_HINT_FIELDS = ("preferred", "note")
_RELATIONSHIP_SELECTORS = ("dependencies", "consumers")
_COLUMN_TITLES = {
    "annotations": "annotations",
    "canonical_surfaces": "canonical surfaces",
    "consumers": "consumed by",
    "dependencies": "depends on",
    "evidence": "evidence",
    "evidence_refs": "evidence refs",
    "implementation": "implementation",
    "owner_issue": "issue",
    "references": "references",
    "summary": "summary",
    "tests": "tests",
}

_DISCLAIMER = (
    "Ephemeral projection reconstructed from owner-local authority."
    " Not repository authority; do not commit this output."
)


class ProjectionError(ValueError):
    """Raised when a projection recipe is invalid or cannot be rendered."""


@dataclass(frozen=True, slots=True)
class Recipe:
    """One stored recipe for reconstructing a developer-facing view."""

    id: str
    summary: str
    path: str
    inputs: tuple[str, ...]
    freshness_requirements: tuple[str, ...]
    include: tuple[str, ...]
    prohibit: tuple[str, ...]
    preferred: str
    note: str | None = None


def recipe_paths(root: Path) -> tuple[Path, ...]:
    """Return recipe files under ``root`` in deterministic order."""

    directory = root / PROJECTION_DIRECTORY
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.yaml")))


def validate_recipes(root: Path) -> tuple[str, ...]:
    """Return sorted validation errors for the recipes under ``root``."""

    try:
        facts: tuple[str, ...] = tuple(read_agent_contract(root).facts)
        contract_available = True
    except AuthorityError:
        facts = ()
        contract_available = False

    errors: list[str] = []
    for path in recipe_paths(root):
        errors.extend(_recipe_errors(root, path, facts, contract_available))
    return tuple(sorted(errors))


def load_recipes(root: Path) -> tuple[Recipe, ...]:
    """Return validated recipes under ``root`` ordered by recipe id."""

    errors = validate_recipes(root)
    if errors:
        raise ProjectionError("\n".join(errors))

    recipes = []
    for path in recipe_paths(root):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        hint = document["output_hint"]
        recipes.append(
            Recipe(
                id=str(document["id"]),
                summary=str(document["summary"]).strip(),
                path=path.relative_to(root).as_posix(),
                inputs=tuple(document.get("inputs") or ()),
                freshness_requirements=tuple(document.get("freshness_requirements") or ()),
                include=tuple(document["include"]),
                prohibit=tuple(document["prohibit"]),
                preferred=str(hint["preferred"]),
                note=str(hint["note"]) if hint.get("note") else None,
            )
        )
    return tuple(sorted(recipes, key=lambda recipe: recipe.id))


def render_projection(root: Path, recipe_id: str) -> str:
    """Return the deterministic ephemeral projection named by ``recipe_id``."""

    recipes = {recipe.id: recipe for recipe in load_recipes(root)}
    try:
        recipe = recipes[recipe_id]
    except KeyError:
        known = ", ".join(sorted(recipes)) or "none"
        raise ProjectionError(
            f"unknown projection recipe '{recipe_id}'; declared recipes: {known}"
        ) from None

    declarations = load_declarations(root)
    contract = read_agent_contract(root)
    live = sorted(
        fact
        for fact in recipe.freshness_requirements
        if not contract.is_persistent_authority(fact)
    )

    lines = [f"# {recipe.id}", "", recipe.summary, "", _DISCLAIMER, ""]
    if live:
        lines.extend([f"Live inputs the agent must fetch: {', '.join(live)}", ""])
    lines.extend([f"Prohibited: {', '.join(sorted(recipe.prohibit))}", ""])

    if recipe.note:
        lines.extend([recipe.note, ""])

    if recipe.preferred == "mermaid":
        lines.extend(_render_mermaid(recipe, declarations))
    elif recipe.preferred == "table":
        lines.extend(_render_table(recipe, declarations))
    else:
        lines.extend(_render_markdown(recipe, declarations))

    return "\n".join(lines) + "\n"


def _render_mermaid(recipe: Recipe, declarations: Sequence[Declaration]) -> list[str]:
    edges: list[tuple[str, str]] = []
    if "dependencies" in recipe.include:
        for declaration in declarations:
            for dependency in sorted(declaration.depends_on):
                edges.append((declaration.id, dependency))
    else:
        derived = consumers_of(declarations)
        for owner in sorted(derived):
            for consumer in derived[owner]:
                edges.append((owner, consumer))

    sources = {source for source, _ in edges}
    lines = ["```mermaid", "graph LR"]
    for source, target in sorted(edges):
        lines.append(f"  {source} --> {target}")
    for declaration in declarations:
        if declaration.id not in sources:
            lines.append(f"  {declaration.id}")
    lines.append("```")
    return lines


def _render_table(recipe: Recipe, declarations: Sequence[Declaration]) -> list[str]:
    columns = [selector for selector in recipe.include if selector != "semantic_owners"]
    header = ["owner", *(_COLUMN_TITLES[selector] for selector in columns)]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    derived = consumers_of(declarations)
    for declaration in declarations:
        cells = [declaration.id]
        cells.extend(_cell(selector, declaration, derived) for selector in columns)
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _render_markdown(recipe: Recipe, declarations: Sequence[Declaration]) -> list[str]:
    selectors = [selector for selector in recipe.include if selector != "semantic_owners"]
    derived = consumers_of(declarations)
    lines: list[str] = []
    for declaration in declarations:
        lines.extend([f"## {declaration.id}", ""])
        for selector in selectors:
            value = _cell(selector, declaration, derived)
            lines.append(f"- {_COLUMN_TITLES[selector]}: {value or 'none'}")
        lines.append("")
    return lines[:-1] if lines else lines


def _cell(
    selector: str, declaration: Declaration, derived: Mapping[str, tuple[str, ...]]
) -> str:
    if selector == "owner_issue":
        return f"#{declaration.owner_issue}" if declaration.owner_issue else ""
    if selector == "summary":
        return declaration.summary
    if selector == "dependencies":
        return ", ".join(sorted(declaration.depends_on))
    if selector == "consumers":
        return ", ".join(derived.get(declaration.id, ()))
    if selector == "evidence":
        return ", ".join(sorted(record.id for record in declaration.evidence))
    if selector == "evidence_refs":
        return ", ".join(sorted(declaration.evidence_refs))
    return ", ".join(sorted(getattr(declaration, selector)))


def _recipe_errors(
    root: Path, path: Path, facts: Sequence[str], contract_available: bool
) -> list[str]:
    prefix = path.relative_to(root).as_posix()
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:  # pragma: no cover - defensive
        return [f"{prefix}: recipe is not readable YAML: {error}"]
    if not isinstance(document, Mapping):
        return [f"{prefix}: recipe must be a YAML mapping"]

    errors: list[str] = []
    for key in document:
        if key not in _RECIPE_FIELDS:
            errors.append(f"{prefix}: unknown field '{key}'")

    if document.get("schema_version") != RECIPE_SCHEMA_VERSION:
        errors.append(f"{prefix}: schema_version must be {RECIPE_SCHEMA_VERSION}")

    identifier = document.get("id")
    if not isinstance(identifier, str) or not _RECIPE_ID_RE.fullmatch(identifier):
        errors.append(f"{prefix}: id '{identifier}' must match '{_RECIPE_ID_PATTERN}'")
    elif identifier != path.stem:
        errors.append(f"{prefix}: file stem must equal recipe id '{identifier}'")

    summary = document.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append(f"{prefix}: summary must be a non-empty string")

    errors.extend(_input_errors(root, prefix, document.get("inputs")))

    requirements = _string_list(prefix, "freshness_requirements", document.get("freshness_requirements"), errors)
    if contract_available:
        for requirement in requirements:
            if requirement not in facts:
                errors.append(
                    f"{prefix}: freshness_requirements '{requirement}' is not classified"
                    f" by {AGENT_CONTRACT_PATH}"
                )

    include = _string_list(prefix, "include", document.get("include"), errors)
    for selector in include:
        if selector not in INCLUDE_SELECTORS:
            errors.append(f"{prefix}: include '{selector}' is not a declared selector")
    if include and "semantic_owners" not in include:
        errors.append(f"{prefix}: include must contain 'semantic_owners'")

    prohibit = _string_list(prefix, "prohibit", document.get("prohibit"), errors)
    for inference in prohibit:
        if inference not in PROHIBITED_INFERENCES:
            errors.append(
                f"{prefix}: prohibit '{inference}' is not a declared prohibited inference"
            )
    if not prohibit:
        errors.append(f"{prefix}: prohibit must declare at least one prohibited inference")

    errors.extend(_output_hint_errors(prefix, document.get("output_hint"), include))
    return errors


def _output_hint_errors(prefix: str, value: Any, include: Sequence[str]) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{prefix}: output_hint must be a mapping"]

    errors: list[str] = []
    for key in value:
        if key not in _OUTPUT_HINT_FIELDS:
            errors.append(f"{prefix}: unknown output_hint field '{key}'")

    preferred = value.get("preferred")
    if preferred not in OUTPUT_FORMATS:
        errors.append(
            f"{prefix}: output_hint.preferred '{preferred}' is not a supported format"
        )
    elif preferred == "mermaid" and not any(
        selector in include for selector in _RELATIONSHIP_SELECTORS
    ):
        errors.append(
            f"{prefix}: a mermaid projection must include 'dependencies' or 'consumers'"
        )
    return errors


def _input_errors(root: Path, prefix: str, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        return [f"{prefix}: inputs must be a list of repository paths or globs"]
    if not value:
        return [f"{prefix}: inputs must declare at least one authority surface"]

    errors: list[str] = []
    for entry in value:
        if (root / entry).exists():
            continue
        if any(True for _ in root.glob(entry)):
            continue
        errors.append(f"{prefix}: input '{entry}' matches nothing")
    return errors


def _string_list(prefix: str, name: str, value: Any, errors: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        errors.append(f"{prefix}: {name} must be a list of identifiers")
        return ()
    seen: list[str] = []
    for entry in value:
        if entry in seen:
            errors.append(f"{prefix}: {name} repeats '{entry}'")
            continue
        seen.append(entry)
    return tuple(seen)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate stored projection recipes")
    subparsers.add_parser("list", help="list stored projection recipes")
    render = subparsers.add_parser("render", help="render one ephemeral projection")
    render.add_argument("recipe", help="recipe id to render")

    arguments = parser.parse_args(argv)
    if arguments.command == "validate":
        errors = validate_recipes(arguments.root)
        for message in errors:
            print(message, file=sys.stderr)
        if errors:
            return 1
        print(f"projection recipes valid: {len(recipe_paths(arguments.root))} recipes")
        return 0

    try:
        if arguments.command == "list":
            for recipe in load_recipes(arguments.root):
                print(f"{recipe.id}\t{recipe.preferred}\t{recipe.summary}")
            return 0
        print(render_projection(arguments.root, arguments.recipe), end="")
    except (ProjectionError, AuthorityError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
