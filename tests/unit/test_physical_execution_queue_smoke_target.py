from __future__ import annotations

import json
from pathlib import Path

import tools.physical_execution_queue_smoke_target as target


def test_smoke_target_writes_create_once_non_scientific_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "smoke.json"

    assert target.main(["--artifact", str(artifact)]) == 0

    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["format_version"] == target.FORMAT_VERSION
    assert payload["kind"] == "physical_queue_smoke_child"
    assert payload["provider_calls"] == 0
    assert payload["semantic_calls"] == 0
    assert payload["scientific_transaction_consumed"] is False


def test_smoke_target_refuses_artifact_overwrite(tmp_path: Path) -> None:
    artifact = tmp_path / "smoke.json"

    assert target.main(["--artifact", str(artifact)]) == 0
    first = artifact.read_bytes()
    assert target.main(["--artifact", str(artifact)]) == 2
    assert artifact.read_bytes() == first
