from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
import yaml

from relaylm.cli import run_cli
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory


_EXPECTED_STARTERS = {
    "blank": "characters",
    "relm": "characters",
    "fact-summarizer": "machines",
    "relaylm-faq": "machines",
}


def _materialize(name: str, destination: Path) -> Path:
    from relaylm.starters import materialize_starter_package

    return materialize_starter_package(name, destination)


def _runtime_config(path: Path, root: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                f"  - name: {root.name}",
                f"    root: {root}",
                "provider:",
                "  adapter: openai_compatible",
                "  base_url: http://127.0.0.1:1234/v1",
                "  model: starter-test-model",
                "server:",
                "  host: 127.0.0.1",
                "  port: 8090",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_first_party_starter_catalog_has_required_roles() -> None:
    from relaylm.starters import list_starter_packages

    starters = list_starter_packages()

    assert {starter.name: starter.family for starter in starters} == _EXPECTED_STARTERS
    assert len({starter.name for starter in starters}) == len(starters)


def test_all_starters_are_valid_production_cognitive_packages(tmp_path: Path) -> None:
    for name in _EXPECTED_STARTERS:
        root = _materialize(name, tmp_path / name)
        package = CognitivePackageDirectory(root)

        assert package.load_config().package_id == name
        assert package.load_identity().content.strip()


def test_character_starters_preserve_character_specialization(tmp_path: Path) -> None:
    for name in ("blank", "relm"):
        root = _materialize(name, tmp_path / name)
        package = CharacterDirectory(root)

        config = package.load_config()
        identity = package.load_identity()

        assert config.character_id == name
        assert identity.content.strip()


def test_machine_starters_use_general_package_identity_without_character_metadata(
    tmp_path: Path,
) -> None:
    for name in ("fact-summarizer", "relaylm-faq"):
        root = _materialize(name, tmp_path / name)
        config = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))

        assert config["package"]["id"] == name
        assert "character" not in config


@pytest.mark.parametrize("name", tuple(_EXPECTED_STARTERS))
def test_each_starter_passes_production_doctor(name: str, tmp_path: Path) -> None:
    root = _materialize(name, tmp_path / name)
    config = _runtime_config(tmp_path / f"{name}.yaml", root)
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config), "--json"],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0, stderr.getvalue()
    assert json.loads(stdout.getvalue())["status"] == "ok"
    assert stderr.getvalue() == ""


@pytest.mark.parametrize("name", ("relm", "relaylm-faq"))
def test_character_and_machine_starters_reach_serve_startup(
    name: str, tmp_path: Path
) -> None:
    root = _materialize(name, tmp_path / name)
    config = _runtime_config(tmp_path / f"{name}.yaml", root)
    stdout = StringIO()
    stderr = StringIO()
    calls: list[tuple[object, str, int]] = []

    def serve_runner(app: object, *, host: str, port: int) -> None:
        calls.append((app, host, port))

    code = run_cli(
        ["serve", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
        serve_runner=serve_runner,
    )

    assert code == 0, stderr.getvalue()
    assert len(calls) == 1
    assert calls[0][1:] == ("127.0.0.1", 8090)
    assert stderr.getvalue() == ""


def test_starters_exclude_runtime_provider_and_secret_configuration(tmp_path: Path) -> None:
    forbidden_fragments = (
        "api_key",
        "base_url",
        "provider:",
        "model:",
        "http://",
        "https://",
        "127.0.0.1",
        "localhost",
    )

    for name in _EXPECTED_STARTERS:
        root = _materialize(name, tmp_path / name)
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ).lower()

        for fragment in forbidden_fragments:
            assert fragment not in text, (name, fragment)


def test_relaylm_faq_uses_bounded_package_knowledge_not_fake_memory(tmp_path: Path) -> None:
    root = _materialize("relaylm-faq", tmp_path / "relaylm-faq")
    package = CognitivePackageDirectory(root)

    knowledge = package.load_knowledge()
    assert 1 <= len(knowledge) <= 4
    assert all(item.location.startswith("knowledge/") for item in knowledge)
    assert tuple(item.location for item in knowledge) == tuple(
        sorted(item.location for item in knowledge)
    )

    combined = "\n".join(item.content for item in knowledge)
    for required in (
        "RelayLM",
        "Pass 1",
        "Pass 2",
        "SOUL.md",
        "Cognitive Profile",
        "MEMORY",
        "Continuity",
        "Starter",
    ):
        assert required in combined

    soul = (root / "SOUL.md").read_text(encoding="utf-8").lower()
    assert "only" in soul and "knowledge" in soul
    assert "model prior" in soul
    assert "not supported" in soul
    assert not (root / "memory" / "MEMORY.md").exists()


def test_removed_medical_soap_is_not_materializable(tmp_path: Path) -> None:
    from relaylm.starters import materialize_starter_package

    with pytest.raises(ValueError, match="unknown starter package"):
        materialize_starter_package("medical-soap", tmp_path / "medical-soap")


def test_materialization_rejects_unknown_or_existing_destination(tmp_path: Path) -> None:
    from relaylm.starters import materialize_starter_package

    with pytest.raises(ValueError, match="unknown starter package"):
        materialize_starter_package("missing", tmp_path / "missing")

    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        materialize_starter_package("blank", destination)
