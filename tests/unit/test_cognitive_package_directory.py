from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.runtime_preflight import prepare_runtime
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.cognitive_package import (
    CognitivePackageDataError,
    CognitivePackageDirectory,
)
from relaylm.turn import run_user_turn


def _write_package(
    root: Path,
    *,
    config: str,
    soul: str = "# Role\n\nPerform the configured cognitive role.\n",
) -> None:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(soul, encoding="utf-8")
    (root / "config.yaml").write_text(config, encoding="utf-8")
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )


class _EchoProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(response=f"processed: {cognitive_input.input.payload['content']}")


def test_generic_loader_accepts_existing_character_package_specialization(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        config=(
            "format_version: 1\n"
            "character:\n"
            "  id: relm\n"
            "  name: ReLM\n"
        ),
    )

    package = CognitivePackageDirectory(tmp_path)

    assert package.load_config().package_id == "relm"


def test_machine_like_package_completes_normal_turn_without_character_metadata(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        config="format_version: 1\npackage:\n  id: medical-soap\n",
        soul="# Medical SOAP\n\nStructure clinical facts as SOAP notes.\n",
    )
    package = CognitivePackageDirectory(tmp_path)

    result = asyncio.run(
        run_user_turn(
            character=package,
            provider=_EchoProvider(),
            content="fever for two days",
        )
    )

    assert result.response == "processed: fever for two days"
    assert [event.actor for event in package.iter_events()] == ["user", "assistant"]


def test_release_preflight_and_assembly_accept_machine_like_package(
    tmp_path: Path,
) -> None:
    root = tmp_path / "machines" / "medical-soap"
    _write_package(
        root,
        config="format_version: 1\npackage:\n  id: medical-soap\n",
        soul="# Medical SOAP\n\nStructure clinical facts as SOAP notes.\n",
    )
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_PROFILE_NAME": "medical-soap",
            "RELAYLM_PROFILE_ROOT": str(root),
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
        }
    )

    prepared = prepare_runtime(resolved)
    profile = prepared.assembly.profiles.resolve("medical-soap")

    assert profile is not None
    assert isinstance(profile.package, CognitivePackageDirectory)
    assert profile.package.load_config().package_id == "medical-soap"


def test_generic_package_config_rejects_null_identity_mapping(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        config="format_version: 1\npackage:\n",
    )
    package = CognitivePackageDirectory(tmp_path)

    with pytest.raises(CognitivePackageDataError, match="package must be a mapping"):
        package.load_config()


def test_generic_package_config_rejects_ambiguous_identity_authority(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        config=(
            "format_version: 1\n"
            "package:\n"
            "  id: machine\n"
            "character:\n"
            "  id: relm\n"
            "  name: ReLM\n"
        ),
    )
    package = CognitivePackageDirectory(tmp_path)

    with pytest.raises(CognitivePackageDataError, match="exactly one"):
        package.load_config()


def test_generic_package_config_preserves_duplicate_yaml_fail_closed(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        config=(
            "format_version: 1\n"
            "package:\n"
            "  id: medical-soap\n"
            "  id: other\n"
        ),
    )
    package = CognitivePackageDirectory(tmp_path)

    with pytest.raises(
        CognitivePackageDataError,
        match="duplicate YAML mapping key: id",
    ):
        package.load_config()


def test_cognitive_package_roots_keep_state_and_memory_isolated(tmp_path: Path) -> None:
    left_root = tmp_path / "characters" / "rin"
    right_root = tmp_path / "machines" / "medical-soap"
    _write_package(
        left_root,
        config=(
            "format_version: 1\n"
            "character:\n"
            "  id: rin\n"
            "  name: Rin\n"
        ),
    )
    _write_package(
        right_root,
        config="format_version: 1\npackage:\n  id: medical-soap\n",
    )
    left = CognitivePackageDirectory(left_root)
    right = CognitivePackageDirectory(right_root)

    left.save_state(
        CanonicalState(
            states=(
                StateRecord(
                    state_id="left-state",
                    state_class="user.fact",
                    key="root",
                    value="left",
                    sources=("left-source",),
                ),
            )
        )
    )
    right.save_state(
        CanonicalState(
            states=(
                StateRecord(
                    state_id="right-state",
                    state_class="user.fact",
                    key="root",
                    value="right",
                    sources=("right-source",),
                ),
            )
        )
    )
    left.save_memory_markdown("# Left memory\n")
    right.save_memory_markdown("# Right memory\n")

    assert left.load_state().states[0].value == "left"
    assert right.load_state().states[0].value == "right"
    assert left.load_memory_markdown() == "# Left memory\n"
    assert right.load_memory_markdown() == "# Right memory\n"


def test_invalid_cognitive_package_root_fails_closed(tmp_path: Path) -> None:
    package = CognitivePackageDirectory(tmp_path / "missing")

    with pytest.raises(CognitivePackageDataError):
        package.load_config()
