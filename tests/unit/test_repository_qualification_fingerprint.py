from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.repository_authority import (
    AUTHORITY_DIRECTORY,
    DECLARATION_SCHEMA_VERSION,
    AuthorityError,
    load_declarations,
    qualification_fingerprint,
    qualification_manifest,
    qualification_owner_closure,
    validate_repository,
)


def _touch(root: Path, relative: str, content: bytes = b"surface\n") -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative


def _write(root: Path, declaration: dict[str, object]) -> None:
    directory = root / AUTHORITY_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{declaration['id']}.yaml"
    path.write_text(yaml.safe_dump(declaration, sort_keys=True), encoding="utf-8")


def _owner(
    root: Path,
    identifier: str,
    *,
    depends_on: tuple[str, ...] = (),
    qualification_inputs: tuple[str, ...] = (),
) -> dict[str, object]:
    semantic = _touch(root, f"docs/contracts/{identifier}.md")
    implementation = _touch(root, f"src/{identifier}.py")
    declaration: dict[str, object] = {
        "schema_version": DECLARATION_SCHEMA_VERSION,
        "id": identifier,
        "summary": f"Authority for {identifier}.",
        "canonical_surfaces": [semantic],
        "implementation": [implementation],
    }
    if depends_on:
        declaration["depends_on"] = list(depends_on)
    if qualification_inputs:
        declaration["qualification_inputs"] = list(qualification_inputs)
    return declaration


def test_qualification_inputs_are_optional_owner_local_selectors(tmp_path: Path) -> None:
    declaration = _owner(tmp_path, "context_compiler")
    declaration["qualification_inputs"] = list(declaration["implementation"])  # type: ignore[arg-type]
    _write(tmp_path, declaration)

    assert validate_repository(tmp_path) == ()
    loaded = load_declarations(tmp_path)[0]
    assert loaded.qualification_inputs == ("src/context_compiler.py",)


def test_qualification_input_must_already_belong_to_declaring_owner(tmp_path: Path) -> None:
    declaration = _owner(tmp_path, "context_compiler")
    declaration["qualification_inputs"] = [_touch(tmp_path, "src/unowned.py")]
    _write(tmp_path, declaration)

    assert validate_repository(tmp_path) == (
        ".ai/authority/context_compiler.yaml: qualification input 'src/unowned.py'"
        " must already be declared by context_compiler",
    )


def test_qualification_input_cannot_restate_another_owners_reference(tmp_path: Path) -> None:
    provider = _owner(tmp_path, "provider_and_api")
    provider_doc = provider["canonical_surfaces"][0]  # type: ignore[index]
    _write(tmp_path, provider)

    consumer = _owner(tmp_path, "cognitive_turn", depends_on=("provider_and_api",))
    consumer["references"] = [provider_doc]
    consumer["qualification_inputs"] = [provider_doc]
    _write(tmp_path, consumer)

    errors = validate_repository(tmp_path)
    assert errors == (
        f".ai/authority/cognitive_turn.yaml: qualification input '{provider_doc}'"
        " must already be declared by cognitive_turn",
    )


def test_qualification_input_must_be_a_file(tmp_path: Path) -> None:
    declaration = _owner(tmp_path, "context_compiler")
    directory = tmp_path / "src/generated"
    directory.mkdir(parents=True)
    declaration["implementation"] = ["src/generated"]
    declaration["qualification_inputs"] = ["src/generated"]
    _write(tmp_path, declaration)

    assert validate_repository(tmp_path) == (
        ".ai/authority/context_compiler.yaml: qualification input 'src/generated' must be a file",
    )


def test_qualification_owner_closure_is_transitive_and_deterministic(tmp_path: Path) -> None:
    _write(tmp_path, _owner(tmp_path, "state_and_validation"))
    _write(
        tmp_path,
        _owner(
            tmp_path,
            "cognitive_turn",
            depends_on=("state_and_validation",),
        ),
    )
    _write(
        tmp_path,
        _owner(
            tmp_path,
            "actual_model_evaluation",
            depends_on=("cognitive_turn",),
        ),
    )

    declarations = load_declarations(tmp_path)
    assert qualification_owner_closure(
        declarations, roots=("actual_model_evaluation",)
    ) == (
        "actual_model_evaluation",
        "cognitive_turn",
        "state_and_validation",
    )


def test_qualification_owner_closure_rejects_unknown_root(tmp_path: Path) -> None:
    _write(tmp_path, _owner(tmp_path, "cognitive_turn"))

    with pytest.raises(AuthorityError, match="unknown qualification root 'missing'"):
        qualification_owner_closure(load_declarations(tmp_path), roots=("missing",))


def test_manifest_is_derived_from_closure_without_central_path_list(tmp_path: Path) -> None:
    provider = _owner(tmp_path, "provider_and_api")
    provider["qualification_inputs"] = list(provider["implementation"])  # type: ignore[arg-type]
    _write(tmp_path, provider)

    runtime = _owner(
        tmp_path,
        "cognitive_turn",
        depends_on=("provider_and_api",),
    )
    runtime["qualification_inputs"] = list(runtime["canonical_surfaces"])  # type: ignore[arg-type]
    _write(tmp_path, runtime)

    manifest = qualification_manifest(
        tmp_path,
        load_declarations(tmp_path),
        roots=("cognitive_turn",),
    )

    assert manifest == {
        "format_version": 1,
        "roots": ["cognitive_turn"],
        "owners": [
            {
                "id": "cognitive_turn",
                "qualification_inputs": ["docs/contracts/cognitive_turn.md"],
            },
            {
                "id": "provider_and_api",
                "qualification_inputs": ["src/provider_and_api.py"],
            },
        ],
    }


def test_fingerprint_changes_with_exact_selected_file_bytes(tmp_path: Path) -> None:
    declaration = _owner(tmp_path, "context_compiler")
    selected = declaration["implementation"][0]  # type: ignore[index]
    declaration["qualification_inputs"] = [selected]
    _write(tmp_path, declaration)
    declarations = load_declarations(tmp_path)

    first = qualification_fingerprint(
        tmp_path,
        declarations,
        roots=("context_compiler",),
    )
    (tmp_path / selected).write_bytes(b"surface\r\n")
    second = qualification_fingerprint(
        tmp_path,
        declarations,
        roots=("context_compiler",),
    )

    assert first.startswith("sha256:")
    assert second.startswith("sha256:")
    assert first != second


def test_fingerprint_changes_when_owner_path_association_changes(tmp_path: Path) -> None:
    shared = _touch(tmp_path, "src/shared.py")
    first = _owner(tmp_path, "cognitive_turn")
    first["implementation"] = [shared]
    first["qualification_inputs"] = [shared]
    second = _owner(tmp_path, "provider_and_api")
    second["implementation"] = [shared]
    _write(tmp_path, first)
    _write(tmp_path, second)

    before = qualification_fingerprint(
        tmp_path,
        load_declarations(tmp_path),
        roots=("cognitive_turn", "provider_and_api"),
    )

    first["qualification_inputs"] = []
    second["qualification_inputs"] = [shared]
    _write(tmp_path, first)
    _write(tmp_path, second)
    after = qualification_fingerprint(
        tmp_path,
        load_declarations(tmp_path),
        roots=("cognitive_turn", "provider_and_api"),
    )

    assert before != after
