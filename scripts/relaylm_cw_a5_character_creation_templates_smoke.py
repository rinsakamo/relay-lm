"""CW-A5 Character Creation / Template Import smoke tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from relaylm.character_creation import (
    commit_character_from_template,
    list_character_templates,
    stage_advanced_character,
    stage_quick_character,
    validate_no_character_startup,
    validate_template_directory,
    validate_template_zip,
)
from relaylm.character_workspace import EXPECTED_ARTIFACTS, REQUIRED_SOURCE_FILENAMES, validate_character_workspace


def main() -> None:
    registry = list_character_templates()
    assert registry["content_free"] is True
    assert registry["remote_registry_supported"] is False
    assert registry["safety"]["auto_create_default_character"] is False
    assert any(item["template_id"] == "friendly-companion" for item in registry["starter"])
    assert any(item["template_id"] == "showcase-friendly-companion" for item in registry["showcase"])
    developer = next(item for item in registry["advanced"] if item["template_id"] == "developer-design-partner")
    assert developer["primary_default"] is False

    quick = stage_quick_character(
        template_id="friendly-companion",
        name="Koyomi",
        tone="calm",
        intended_use="AI companion",
    )
    assert quick.validation.is_valid
    assert all(filename in quick.source_files for filename in REQUIRED_SOURCE_FILENAMES)
    assert "memory/topics/relaylm.md" in quick.source_files
    assert quick.relaylm_onboarding_memory_included is True
    assert quick.to_public_dict()["source_content_included"] is False
    assert quick.compile_projection["is_valid"] is True

    advanced = stage_advanced_character(name="Manual Character", source_sections={"SOUL": "# Identity\n\nstatus:: source\n"})
    assert advanced.validation.is_valid
    assert "memory/topics/relaylm.md" not in advanced.source_files
    assert advanced.relaylm_onboarding_memory_included is False

    as_starter = stage_quick_character(
        template_id="showcase-friendly-companion",
        name="Starter Showcase",
        showcase_mode="starter",
    )
    as_is = stage_quick_character(
        template_id="showcase-friendly-companion",
        name="As Is Showcase",
        showcase_mode="as_is",
    )
    assert as_starter.validation.is_valid
    assert as_is.validation.is_valid
    assert "memory/people/demo_user.md" not in as_starter.source_files
    assert "memory/people/demo_user.md" in as_is.source_files
    assert "status:: template_example" in as_is.source_files["memory/people/demo_user.md"]

    with tempfile.TemporaryDirectory(prefix="relaylm-cw-a5-") as temp:
        temp_root = Path(temp)
        no_character = validate_no_character_startup(temp_root / "characters")
        assert no_character["creation_flow_required"] is True
        assert no_character["auto_created_default_character"] is False
        assert not (temp_root / "characters" / "default").exists()

        approval_required = commit_character_from_template(
            characters_root=temp_root / "characters",
            template_id="friendly-companion",
            name="Koyomi",
            approval=False,
        )
        assert approval_required.status == "approval_required"
        assert approval_required.committed is False
        assert not (temp_root / "characters" / "koyomi").exists()

        committed = commit_character_from_template(
            characters_root=temp_root / "characters",
            template_id="friendly-companion",
            name="Koyomi",
            approval=True,
        )
        assert committed.status == "committed"
        assert committed.committed is True
        assert committed.active_character_set is False
        workspace = temp_root / "characters" / "koyomi"
        assert validate_character_workspace(workspace, character_id="koyomi").is_valid
        for artifact in EXPECTED_ARTIFACTS:
            assert (workspace / ".relaylm" / "build" / artifact).is_file()
        manifest = json.loads((workspace / ".relaylm" / "build" / "character_manifest.json").read_text(encoding="utf-8"))
        assert manifest["character_id"] == "koyomi"

        duplicate = commit_character_from_template(
            characters_root=temp_root / "characters",
            template_id="friendly-companion",
            name="Koyomi",
            approval=True,
        )
        assert duplicate.status == "target_exists"
        assert duplicate.committed is False

        third_party = temp_root / "third_party"
        _write_valid_template(third_party, include_relaylm=False)
        valid_import = validate_template_directory(third_party)
        assert valid_import.is_valid
        assert valid_import.relaylm_onboarding_memory_included is False

        unsafe_cases = {
            ".relaylm/build/context_projection.json": "relaylm_runtime_artifact_rejected",
            ".relaylm/state/scene_state.json": "relaylm_runtime_artifact_rejected",
            "tools/install.sh": "script_or_executable_rejected",
            ".env": "runtime_config_or_env_rejected",
        }
        for relative_path, reason in unsafe_cases.items():
            unsafe = temp_root / ("unsafe_" + reason)
            _write_valid_template(unsafe, include_relaylm=False)
            target = unsafe / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("SECRET_DO_NOT_LEAK", encoding="utf-8")
            if target.suffix == ".sh":
                target.chmod(target.stat().st_mode | stat.S_IXUSR)
            result = validate_template_directory(unsafe)
            public_text = json.dumps(result.to_public_dict(), sort_keys=True)
            assert not result.is_valid
            assert reason in result.reason_ids
            assert "SECRET_DO_NOT_LEAK" not in public_text

        symlink_root = temp_root / "unsafe_symlink"
        _write_valid_template(symlink_root, include_relaylm=False)
        try:
            (symlink_root / "linked.md").symlink_to(symlink_root / "SOUL.md")
            symlink_result = validate_template_directory(symlink_root)
            assert not symlink_result.is_valid
            assert "symlink_rejected" in symlink_result.reason_ids
        except (OSError, NotImplementedError):
            pass

        traversal_zip = temp_root / "traversal.zip"
        with zipfile.ZipFile(traversal_zip, "w") as archive:
            archive.writestr("manifest.json", "{}")
            for filename in REQUIRED_SOURCE_FILENAMES:
                archive.writestr(filename, f"# {filename}\n\nstatus:: source\n")
            archive.writestr("../escape.md", "SECRET_DO_NOT_LEAK")
        zip_result = validate_template_zip(traversal_zip)
        zip_text = json.dumps(zip_result.to_public_dict(), sort_keys=True)
        assert not zip_result.is_valid
        assert "path_traversal_rejected" in zip_result.reason_ids
        assert "SECRET_DO_NOT_LEAK" not in zip_text

    print("CW-A5 character creation / template import smoke passed")


def _write_valid_template(root: Path, *, include_relaylm: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text("{}\n", encoding="utf-8")
    for filename in REQUIRED_SOURCE_FILENAMES:
        (root / filename).write_text(f"# {filename}\n\nstatus:: source\n", encoding="utf-8")
    if include_relaylm:
        target = root / "memory" / "topics" / "relaylm.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# RelayLM\n\nstatus:: template_knowledge\n", encoding="utf-8")


if __name__ == "__main__":
    main()
