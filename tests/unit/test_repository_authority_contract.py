from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.repository_authority import (
    AUTHORITY_DIRECTORY,
    DECLARATION_SCHEMA_VERSION,
    AuthorityError,
    consumers_of,
    documentation_coverage_errors,
    load_declarations,
    validate_repository,
)


def _write(root: Path, declaration: dict[str, object], *, name: str | None = None) -> Path:
    directory = root / AUTHORITY_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stem = name if name is not None else str(declaration["id"])
    path = directory / f"{stem}.yaml"
    path.write_text(yaml.safe_dump(declaration, sort_keys=True), encoding="utf-8")
    return path


def _touch(root: Path, relative: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("surface\n", encoding="utf-8")
    return relative


def _minimal(root: Path, identifier: str) -> dict[str, object]:
    return {
        "schema_version": DECLARATION_SCHEMA_VERSION,
        "id": identifier,
        "summary": f"Canonical authority for {identifier}.",
        "canonical_surfaces": [_touch(root, f"docs/contracts/{identifier}.md")],
    }


def test_a_minimal_declaration_set_is_valid(tmp_path: Path) -> None:
    _write(tmp_path, _minimal(tmp_path, "context_compiler"))

    assert validate_repository(tmp_path) == ()


def test_declarations_load_in_deterministic_identifier_order(tmp_path: Path) -> None:
    for identifier in ("release_engineering", "calibration", "context_compiler"):
        _write(tmp_path, _minimal(tmp_path, identifier))

    declarations = load_declarations(tmp_path)

    assert [declaration.id for declaration in declarations] == [
        "calibration",
        "context_compiler",
        "release_engineering",
    ]


def test_an_empty_authority_directory_is_not_a_valid_repository(tmp_path: Path) -> None:
    (tmp_path / AUTHORITY_DIRECTORY).mkdir(parents=True)

    assert validate_repository(tmp_path) == ("no semantic owner declaration exists",)


def test_a_declaration_file_name_must_equal_its_owner_identifier(tmp_path: Path) -> None:
    _write(tmp_path, _minimal(tmp_path, "context_compiler"), name="context-compiler")

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context-compiler.yaml: file stem must equal owner id 'context_compiler'",
    )


def test_owner_identifiers_use_a_stable_lowercase_grammar(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["id"] = "Context-Compiler"
    _write(tmp_path, declaration, name="Context-Compiler")

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/Context-Compiler.yaml: id 'Context-Compiler' must match '^[a-z][a-z0-9_]*$'",
    )


def test_a_declaration_must_carry_the_current_schema_version(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["schema_version"] = 2
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: schema_version must be 1",
    )


def test_a_declaration_must_state_a_summary(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["summary"] = "  "
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: summary must be a non-empty string",
    )


def test_unknown_declaration_fields_are_rejected(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["consumed_by"] = ["cognitive_turn"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: unknown field 'consumed_by'",
    )


def test_an_owning_issue_must_be_a_positive_integer(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["owner_issue"] = "1267"
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: owner_issue must be a positive integer",
    )


def test_a_declared_surface_must_exist_in_the_repository(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["implementation"] = ["src/relaylm/context.py"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: implementation path"
        " 'src/relaylm/context.py' does not exist",
    )


def test_declared_surfaces_must_be_repository_relative(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["implementation"] = ["/etc/passwd", "../outside.md"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: implementation path"
        " '../outside.md' must be repository-relative",
        ".ai/authority/context_compiler.yaml: implementation path"
        " '/etc/passwd' must be repository-relative",
    )


def test_a_declaration_must_not_repeat_the_same_surface(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    surface = _touch(tmp_path, "src/relaylm/context.py")
    declaration["implementation"] = [surface, surface]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: implementation repeats"
        " 'src/relaylm/context.py'",
    )


def test_one_canonical_surface_has_exactly_one_writer(tmp_path: Path) -> None:
    shared = _touch(tmp_path, "docs/architecture/cognitive-runtime.md")
    first = _minimal(tmp_path, "cognitive_turn")
    first["canonical_surfaces"] = [shared]
    second = _minimal(tmp_path, "cognitive_budget")
    second["canonical_surfaces"] = [shared]
    _write(tmp_path, first)
    _write(tmp_path, second)

    errors = validate_repository(tmp_path)

    assert errors == (
        "docs/architecture/cognitive-runtime.md: canonical surface is claimed by"
        " cognitive_budget, cognitive_turn",
    )


def test_implementation_and_test_surfaces_may_be_shared_between_owners(tmp_path: Path) -> None:
    shared_runtime = _touch(tmp_path, "src/relaylm/turn.py")
    shared_test = _touch(tmp_path, "tests/unit/test_cognitive_turn.py")
    for identifier in ("cognitive_turn", "cognitive_budget"):
        declaration = _minimal(tmp_path, identifier)
        declaration["implementation"] = [shared_runtime]
        declaration["tests"] = [shared_test]
        _write(tmp_path, declaration)

    assert validate_repository(tmp_path) == ()


def test_a_reference_must_resolve_to_another_owners_canonical_surface(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "cognitive_budget")
    declaration["references"] = [_touch(tmp_path, "docs/architecture/core.md")]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/cognitive_budget.yaml: reference 'docs/architecture/core.md'"
        " is not a canonical surface of any semantic owner",
    )


def test_a_reference_must_not_restate_the_owners_own_canonical_surface(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "cognitive_budget")
    declaration["references"] = list(declaration["canonical_surfaces"])  # type: ignore[arg-type]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/cognitive_budget.yaml: reference"
        " 'docs/contracts/cognitive_budget.md' is already owned by cognitive_budget",
    )


def test_a_dependency_must_name_a_declared_semantic_owner(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "calibration")
    declaration["depends_on"] = ["actual_model_evaluation"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/calibration.yaml: depends_on 'actual_model_evaluation'"
        " is not a declared semantic owner",
    )


def test_an_owner_must_not_depend_on_itself(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "calibration")
    declaration["depends_on"] = ["calibration"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/calibration.yaml: depends_on must not include the owner itself",
    )


def test_reverse_dependencies_are_derived_rather_than_declared(tmp_path: Path) -> None:
    _write(tmp_path, _minimal(tmp_path, "actual_model_evaluation"))
    consumer = _minimal(tmp_path, "calibration")
    consumer["depends_on"] = ["actual_model_evaluation"]
    _write(tmp_path, consumer)

    declarations = load_declarations(tmp_path)
    producer = next(item for item in declarations if item.id == "actual_model_evaluation")

    assert producer.depends_on == ()
    assert not hasattr(producer, "consumed_by")


def test_evidence_identity_is_unique_across_producers(tmp_path: Path) -> None:
    surface = _touch(tmp_path, "docs/reference/evidence.md")
    for identifier in ("actual_model_evaluation", "calibration"):
        declaration = _minimal(tmp_path, identifier)
        declaration["evidence"] = [
            {
                "id": "crystallization-quality-v1",
                "summary": "Crystallization quality evidence.",
                "surfaces": [surface],
            }
        ]
        _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        "crystallization-quality-v1: evidence is produced by"
        " actual_model_evaluation, calibration",
    )


def test_an_evidence_record_must_declare_an_existing_surface(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "actual_model_evaluation")
    declaration["evidence"] = [
        {
            "id": "crystallization-quality-v1",
            "summary": "Crystallization quality evidence.",
            "surfaces": ["docs/reference/missing.md"],
        }
    ]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/actual_model_evaluation.yaml: evidence"
        " 'crystallization-quality-v1' surfaces path 'docs/reference/missing.md'"
        " does not exist",
    )


def test_an_evidence_reference_must_resolve_to_a_produced_record(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "calibration")
    declaration["evidence_refs"] = ["crystallization-quality-v1"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/calibration.yaml: evidence_refs 'crystallization-quality-v1'"
        " is not produced by any semantic owner",
    )


def test_an_evidence_producer_does_not_reference_its_own_record(tmp_path: Path) -> None:
    surface = _touch(tmp_path, "docs/reference/evidence.md")
    declaration = _minimal(tmp_path, "actual_model_evaluation")
    declaration["evidence"] = [
        {
            "id": "crystallization-quality-v1",
            "summary": "Crystallization quality evidence.",
            "surfaces": [surface],
        }
    ]
    declaration["evidence_refs"] = ["crystallization-quality-v1"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/actual_model_evaluation.yaml: evidence_refs"
        " 'crystallization-quality-v1' is already produced by this owner",
    )


def test_annotation_surfaces_are_declared_separately_from_canonical_authority(
    tmp_path: Path,
) -> None:
    declaration = _minimal(tmp_path, "development_workflow")
    declaration["annotations"] = [
        _touch(tmp_path, "docs/decisions/0003-direct-canonical-convergence.md")
    ]
    _write(tmp_path, declaration)

    assert validate_repository(tmp_path) == ()
    declaration = load_declarations(tmp_path)[0]
    assert declaration.annotations == (
        "docs/decisions/0003-direct-canonical-convergence.md",
    )
    assert "docs/decisions/0003-direct-canonical-convergence.md" not in (
        declaration.canonical_surfaces
    )


def test_reported_errors_are_deterministic_and_sorted(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["depends_on"] = ["zzz_owner", "aaa_owner"]
    _write(tmp_path, declaration)

    errors = validate_repository(tmp_path)

    assert errors == tuple(sorted(errors))
    assert len(errors) == 2


def test_loading_an_invalid_repository_is_refused(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    declaration["depends_on"] = ["missing_owner"]
    _write(tmp_path, declaration)

    with pytest.raises(AuthorityError):
        load_declarations(tmp_path)


def test_a_malformed_declaration_document_is_reported_rather_than_raised(
    tmp_path: Path,
) -> None:
    directory = tmp_path / AUTHORITY_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "context_compiler.yaml").write_text("- not: a mapping\n", encoding="utf-8")

    errors = validate_repository(tmp_path)

    assert errors == (
        ".ai/authority/context_compiler.yaml: declaration must be a YAML mapping",
    )


def test_a_dependency_cycle_is_rejected(tmp_path: Path) -> None:
    first = _minimal(tmp_path, "context_compiler")
    first["depends_on"] = ["persistence"]
    second = _minimal(tmp_path, "persistence")
    second["depends_on"] = ["context_compiler"]
    _write(tmp_path, first)
    _write(tmp_path, second)

    errors = validate_repository(tmp_path)

    assert errors == (
        "depends_on cycle: context_compiler -> persistence -> context_compiler",
    )


def test_derived_consumers_replace_declared_reverse_dependencies(tmp_path: Path) -> None:
    _write(tmp_path, _minimal(tmp_path, "actual_model_evaluation"))
    _write(tmp_path, _minimal(tmp_path, "cognitive_budget"))
    consumer = _minimal(tmp_path, "calibration")
    consumer["depends_on"] = ["actual_model_evaluation", "cognitive_budget"]
    _write(tmp_path, consumer)

    derived = consumers_of(load_declarations(tmp_path))

    assert derived == {
        "actual_model_evaluation": ("calibration",),
        "calibration": (),
        "cognitive_budget": ("calibration",),
    }


def test_documentation_coverage_reports_unowned_documents(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "context_compiler")
    _touch(tmp_path, "docs/reference/orphan.md")
    _write(tmp_path, declaration)

    assert documentation_coverage_errors(tmp_path) == (
        "docs/reference/orphan.md: document has no semantic owner",
    )


def test_annotation_surfaces_satisfy_documentation_coverage(tmp_path: Path) -> None:
    declaration = _minimal(tmp_path, "development_workflow")
    declaration["annotations"] = [_touch(tmp_path, "docs/decisions/0003-example.md")]
    _write(tmp_path, declaration)

    assert documentation_coverage_errors(tmp_path) == ()


def test_a_reintroduced_central_authority_aggregate_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, _minimal(tmp_path, "context_compiler"))
    (tmp_path / "docs" / "authority-map.yaml").write_text("domains: {}\n", encoding="utf-8")

    assert documentation_coverage_errors(tmp_path) == (
        "docs/authority-map.yaml: hand-maintained authority aggregates are prohibited;"
        " owner-local declarations under .ai/authority/ are the canonical writer",
    )
