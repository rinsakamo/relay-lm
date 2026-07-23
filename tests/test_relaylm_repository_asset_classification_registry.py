from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "relaylm_repository_asset_classification_registry.py"
)
SPEC = importlib.util.spec_from_file_location(
    "relaylm_repository_asset_classification_registry",
    SCRIPT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


def _base_record() -> dict:
    return {
        "asset_id": "example.asset",
        "paths": ["existing.py"],
        "responsibility": "repository_validation",
        "lifecycle": "active",
        "owner": "repository_maintenance",
        "protected_boundary": "example validation boundary",
        "current_callers": ["example caller"],
        "invocation_roots": ["operator_cli"],
        "evidence": ["existing.py"],
        "removal_gate": None,
        "replacement_validation": None,
        "confidence": "confirmed",
    }


def _payload(record: dict) -> dict:
    return {
        "registry_version": 1,
        "generated_from": registry.DOC_PATH.as_posix(),
        "source_commit": "a" * 40,
        "classification_version": 1,
        "canonical_entrypoints": [
            {
                "group": "example",
                "command": "python existing.py",
                "asset_id": record["asset_id"],
            }
        ],
        "records": [record],
    }


def test_current_registry_matches_reviewed_document_and_validates() -> None:
    root = registry.repository_root()
    payload = registry.load_yaml(root / registry.REGISTRY_PATH)
    document = registry.extract_document_registry((root / registry.DOC_PATH).read_text(encoding="utf-8"))

    assert registry.mirrored_payload(payload) == registry.mirrored_payload(document)
    assert registry.validate_registry(payload, root=root) == []


def test_current_registry_rendering_is_deterministic() -> None:
    payload = registry.load_yaml(registry.repository_root() / registry.REGISTRY_PATH)

    assert registry.render_json(payload) == registry.render_json(payload)
    assert registry.render_markdown(payload) == registry.render_markdown(payload)
    assert "does not authorize retirement" in registry.render_markdown(payload)


def test_loader_rejects_duplicate_yaml_mapping_keys() -> None:
    with pytest.raises(ValueError, match="duplicate YAML mapping key: 'registry_version'"):
        registry.load_yaml_text(
            "registry_version: 1\n"
            "registry_version: 2\n"
        )


def test_source_commit_is_part_of_the_mirrored_authority() -> None:
    left = {
        "classification_version": 1,
        "source_commit": "a" * 40,
        "records": [],
    }
    right = deepcopy(left)
    right["source_commit"] = "b" * 40

    assert registry.mirrored_payload(left) != registry.mirrored_payload(right)


def test_validator_rejects_duplicate_asset_ids_and_canonical_groups(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("pass\n", encoding="utf-8")
    record = _base_record()
    payload = _payload(record)
    payload["records"].append(deepcopy(record))
    payload["canonical_entrypoints"].append(
        {
            "group": "example",
            "command": "python other.py",
            "asset_id": record["asset_id"],
        }
    )

    errors = registry.validate_registry(payload, root=tmp_path)

    assert "duplicate asset_id: example.asset" in errors
    assert "competing canonical entrypoint group: example" in errors
    assert "asset has multiple canonical entrypoint claims: example.asset" in errors


def test_validator_rejects_unexpanded_paths_and_unknown_enums(tmp_path: Path) -> None:
    record = _base_record()
    record["paths"] = ["*.py"]
    record["responsibility"] = "dead_code"
    record["invocation_roots"] = ["unknown_root"]

    errors = registry.validate_registry(_payload(record), root=tmp_path)

    assert "example.asset.paths contains an unexpanded glob: *.py" in errors
    assert "example.asset.responsibility is unknown: 'dead_code'" in errors
    assert "example.asset.invocation_roots contains unknown values: unknown_root" in errors


def test_validator_requires_transitional_gate_and_replacement_validation(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("pass\n", encoding="utf-8")
    record = _base_record()
    record["lifecycle"] = "transitional"

    errors = registry.validate_registry(_payload(record), root=tmp_path)

    assert "example.asset.removal_gate must be non-empty for transitional assets" in errors
    assert "example.asset.replacement_validation must be non-empty for transitional assets" in errors


def test_validator_rejects_retired_assets_with_live_responsibilities(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("pass\n", encoding="utf-8")
    record = _base_record()
    record["lifecycle"] = "retired"

    errors = registry.validate_registry(_payload(record), root=tmp_path)

    assert "example.asset.current_callers must be empty for retired assets" in errors
    assert "example.asset.protected_boundary must be null or 'none' for retired assets" in errors
    assert "example.asset.invocation_roots must be empty for retired assets" in errors
    assert "canonical entrypoint asset must be active: example.asset" in errors


def test_valid_retired_asset_needs_no_invocation_root_reason(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("pass\n", encoding="utf-8")
    active = _base_record()
    retired = {
        **_base_record(),
        "asset_id": "example.retired",
        "lifecycle": "retired",
        "protected_boundary": None,
        "current_callers": [],
        "invocation_roots": [],
    }
    payload = _payload(active)
    payload["records"].append(retired)

    errors = registry.validate_registry(payload, root=tmp_path)

    assert errors == []


def test_active_operator_root_requires_one_canonical_claim(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("pass\n", encoding="utf-8")
    first = _base_record()
    second = {
        **_base_record(),
        "asset_id": "example.second",
    }
    payload = _payload(first)
    payload["records"].append(second)

    errors = registry.validate_registry(payload, root=tmp_path)

    assert "active operator-root asset must have exactly one canonical entrypoint claim: example.second" in errors
