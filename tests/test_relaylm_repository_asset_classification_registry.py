from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts import relaylm_repository_asset_classification_registry as registry


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
