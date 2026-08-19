from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.repository_authority import AUTHORITY_DIRECTORY
from tools.repository_docs import (
    PERSISTENT_PROJECTIONS,
    PROJECTION_SCHEMA_VERSION,
    DocumentationProjectionError,
    generate,
    package_version,
    projection_drift,
    provenance_of,
    write_projections,
)

INPUT_COMMIT = "0123456789abcdef0123456789abcdef01234567"
OTHER_COMMIT = "89abcdef0123456789abcdef0123456789abcdef"


def _repository(tmp_path: Path) -> Path:
    version = tmp_path / "src" / "relaylm" / "_version.py"
    version.parent.mkdir(parents=True, exist_ok=True)
    version.write_text('__version__ = "1.0.0rc1"\n', encoding="utf-8")

    authority = tmp_path / AUTHORITY_DIRECTORY
    authority.mkdir(parents=True, exist_ok=True)
    for identifier, issue, depends in (
        ("core_architecture", None, []),
        ("persistence", None, ["core_architecture"]),
        ("context_compiler", 1267, ["persistence"]),
    ):
        surface = tmp_path / "docs" / "architecture" / f"{identifier}.md"
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text("surface\n", encoding="utf-8")
        declaration: dict[str, object] = {
            "schema_version": 1,
            "id": identifier,
            "summary": f"Authority for {identifier}.",
            "canonical_surfaces": [f"docs/architecture/{identifier}.md"],
        }
        if issue is not None:
            declaration["owner_issue"] = issue
        if depends:
            declaration["depends_on"] = depends
        (authority / f"{identifier}.yaml").write_text(
            yaml.safe_dump(declaration, sort_keys=False), encoding="utf-8"
        )
    return tmp_path


def test_the_package_version_is_read_from_release_owned_source(tmp_path: Path) -> None:
    _repository(tmp_path)

    assert package_version(tmp_path) == "1.0.0rc1"


def test_generation_produces_the_declared_persistent_projections(tmp_path: Path) -> None:
    _repository(tmp_path)

    generated = generate(tmp_path, source_commit=INPUT_COMMIT)

    assert tuple(sorted(generated)) == PERSISTENT_PROJECTIONS


def test_generation_is_deterministic_for_one_frozen_input(tmp_path: Path) -> None:
    _repository(tmp_path)

    first = generate(tmp_path, source_commit=INPUT_COMMIT)
    second = generate(tmp_path, source_commit=INPUT_COMMIT)

    assert first == second


def test_a_generated_projection_carries_machine_readable_provenance(tmp_path: Path) -> None:
    _repository(tmp_path)

    generated = generate(tmp_path, source_commit=INPUT_COMMIT)
    provenance = provenance_of(generated["ARCHITECTURE.md"])

    assert provenance == {
        "generated-by": "relaylm-architecture-projection",
        "projection-schema-version": str(PROJECTION_SCHEMA_VERSION),
        "source-commit": INPUT_COMMIT,
        "package-version": "1.0.0rc1",
    }


def test_provenance_is_invisible_in_rendered_markdown(tmp_path: Path) -> None:
    _repository(tmp_path)

    text = generate(tmp_path, source_commit=INPUT_COMMIT)["ARCHITECTURE.md"]

    for line in text.splitlines():
        if "source-commit" in line:
            assert line.startswith("<!--") and line.endswith("-->")


def test_a_generated_projection_derives_owners_from_owner_local_authority(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)

    text = generate(tmp_path, source_commit=INPUT_COMMIT)["ARCHITECTURE.md"]

    assert "### context_compiler" in text
    assert "docs/architecture/context-compiler.md" not in text
    assert "`docs/architecture/context_compiler.md`" in text
    assert "#1267" in text
    assert text.index("### context_compiler") < text.index("### core_architecture")
    assert "consumed by: context_compiler" in text


def test_a_generated_projection_includes_the_derived_dependency_graph(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)

    text = generate(tmp_path, source_commit=INPUT_COMMIT)["ARCHITECTURE.md"]

    assert "```mermaid" in text
    assert "  context_compiler --> persistence" in text
    assert "  persistence --> core_architecture" in text


def test_a_source_commit_must_be_an_exact_lowercase_commit_identity(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)

    with pytest.raises(DocumentationProjectionError):
        generate(tmp_path, source_commit="HEAD")


def test_generation_refuses_invalid_repository_authority(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / AUTHORITY_DIRECTORY / "context_compiler.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": "context_compiler",
                "summary": "Broken.",
                "depends_on": ["missing_owner"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(DocumentationProjectionError):
        generate(root, source_commit=INPUT_COMMIT)


def test_writing_projections_materializes_them_at_the_repository_root(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)

    written = write_projections(tmp_path, source_commit=INPUT_COMMIT)

    assert written == PERSISTENT_PROJECTIONS
    assert (tmp_path / "ARCHITECTURE.md").read_text(encoding="utf-8") == generate(
        tmp_path, source_commit=INPUT_COMMIT
    )["ARCHITECTURE.md"]


def test_no_drift_is_reported_for_a_freshly_materialized_projection(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    write_projections(tmp_path, source_commit=INPUT_COMMIT)

    assert projection_drift(tmp_path, source_commit=INPUT_COMMIT) == ()


def test_drift_is_reported_when_authority_moved_after_materialization(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    write_projections(root, source_commit=INPUT_COMMIT)
    surface = root / "docs" / "architecture" / "crystallization.md"
    surface.write_text("surface\n", encoding="utf-8")
    (root / AUTHORITY_DIRECTORY / "crystallization.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": "crystallization",
                "summary": "Authority for crystallization.",
                "canonical_surfaces": ["docs/architecture/crystallization.md"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert projection_drift(root, source_commit=INPUT_COMMIT) == (
        "ARCHITECTURE.md: committed projection does not match generation from"
        f" {INPUT_COMMIT}",
    )


def test_drift_is_reported_for_a_missing_projection(tmp_path: Path) -> None:
    _repository(tmp_path)

    assert projection_drift(tmp_path, source_commit=INPUT_COMMIT) == (
        "ARCHITECTURE.md: persistent projection has not been materialized",
    )


def test_a_projection_frozen_at_one_input_does_not_match_another_input(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)
    write_projections(tmp_path, source_commit=INPUT_COMMIT)

    assert projection_drift(tmp_path, source_commit=OTHER_COMMIT) == (
        "ARCHITECTURE.md: committed projection does not match generation from"
        f" {OTHER_COMMIT}",
    )
