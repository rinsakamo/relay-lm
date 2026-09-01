from __future__ import annotations

from tools.repository_authority import Declaration
from tools.repository_qualification_coverage import (
    QualificationCoverageGap,
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
