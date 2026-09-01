from __future__ import annotations

import pytest

from tools.repository_authority import AuthorityError, Declaration
from tools.repository_qualification_coverage import (
    QualificationCoverageGap,
    QualificationExclusion,
    qualification_coverage_gaps,
)


def _declaration(
    identifier: str,
    *,
    implementation: tuple[str, ...] = (),
    qualification_inputs: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
) -> Declaration:
    return Declaration(
        id=identifier,
        summary=f"Authority for {identifier}.",
        path=f".ai/authority/{identifier}.yaml",
        implementation=implementation,
        qualification_inputs=qualification_inputs,
        depends_on=depends_on,
    )


def test_audit_reports_only_unselected_implementation_in_the_root_closure() -> None:
    declarations = (
        _declaration(
            "runtime_configuration",
            implementation=(
                "src/relaylm/runtime_config_loader.py",
                "src/relaylm/api/openai.py",
            ),
            qualification_inputs=("src/relaylm/api/openai.py",),
            depends_on=("provider_and_api",),
        ),
        _declaration(
            "provider_and_api",
            implementation=("src/relaylm/providers/openai_compatible.py",),
            qualification_inputs=("src/relaylm/providers/openai_compatible.py",),
        ),
        _declaration(
            "crystallization",
            implementation=("src/relaylm/crystallization.py",),
        ),
    )

    assert qualification_coverage_gaps(
        declarations,
        roots=("runtime_configuration",),
    ) == (
        QualificationCoverageGap(
            owner="runtime_configuration",
            omitted_implementation=("src/relaylm/runtime_config_loader.py",),
        ),
    )


def test_audit_is_deterministic_for_multiple_roots_and_paths() -> None:
    declarations = (
        _declaration(
            "runtime_configuration",
            implementation=("z.py", "a.py"),
        ),
        _declaration(
            "crystallization",
            implementation=("memory.py",),
        ),
    )

    assert qualification_coverage_gaps(
        declarations,
        roots=("runtime_configuration", "crystallization", "runtime_configuration"),
    ) == (
        QualificationCoverageGap(
            owner="crystallization",
            omitted_implementation=("memory.py",),
        ),
        QualificationCoverageGap(
            owner="runtime_configuration",
            omitted_implementation=("a.py", "z.py"),
        ),
    )


def test_audit_is_empty_when_all_implementation_surfaces_are_selected() -> None:
    declarations = (
        _declaration(
            "runtime_configuration",
            implementation=("runtime.py",),
            qualification_inputs=("runtime.py",),
        ),
    )

    assert qualification_coverage_gaps(
        declarations,
        roots=("runtime_configuration",),
    ) == ()


def test_reasoned_exclusion_resolves_an_unselected_implementation_surface() -> None:
    declarations = (
        _declaration(
            "runtime_configuration",
            implementation=("runtime.py", "operator.py"),
            qualification_inputs=("runtime.py",),
        ),
    )

    assert qualification_coverage_gaps(
        declarations,
        roots=("runtime_configuration",),
        exclusions_by_owner={
            "runtime_configuration": (
                QualificationExclusion(
                    path="operator.py",
                    reason="Operator-only wrapper; semantic runtime inputs are selected separately.",
                ),
            )
        },
    ) == ()


def test_exclusion_requires_a_non_empty_reason() -> None:
    with pytest.raises(ValueError, match="reason must be non-empty"):
        QualificationExclusion(path="operator.py", reason="  ")


def test_exclusion_must_name_the_same_owners_implementation_surface() -> None:
    declarations = (
        _declaration("runtime_configuration", implementation=("runtime.py",)),
    )

    with pytest.raises(AuthorityError, match="is not an implementation surface"):
        qualification_coverage_gaps(
            declarations,
            roots=("runtime_configuration",),
            exclusions_by_owner={
                "runtime_configuration": (
                    QualificationExclusion(path="other.py", reason="Not selected."),
                )
            },
        )


def test_selected_input_cannot_also_be_excluded() -> None:
    declarations = (
        _declaration(
            "runtime_configuration",
            implementation=("runtime.py",),
            qualification_inputs=("runtime.py",),
        ),
    )

    with pytest.raises(AuthorityError, match="cannot also be excluded"):
        qualification_coverage_gaps(
            declarations,
            roots=("runtime_configuration",),
            exclusions_by_owner={
                "runtime_configuration": (
                    QualificationExclusion(path="runtime.py", reason="Contradiction."),
                )
            },
        )


def test_exclusion_owner_must_be_declared() -> None:
    declarations = (
        _declaration("runtime_configuration", implementation=("runtime.py",)),
    )

    with pytest.raises(AuthorityError, match="unknown owners: missing_owner"):
        qualification_coverage_gaps(
            declarations,
            roots=("runtime_configuration",),
            exclusions_by_owner={
                "missing_owner": (
                    QualificationExclusion(path="runtime.py", reason="Unknown owner."),
                )
            },
        )
