"""Regression coverage for canonical inventory generation across modes."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory.cli import _run_scan  # noqa: E402


def test_storage_cross_references_are_mode_stable_and_not_dangling() -> None:
    storage_only = _run_scan({"storage"})
    combined = _run_scan({"storage", "invocations"})

    assert storage_only["storage"] == combined["storage"]
    invocation_ids = {
        record["root_id"]
        for record in combined["invocations"]
    }
    dangling = {
        root_id
        for record in combined["storage"]
        for root_id in record["invocation_roots"]
        if root_id not in invocation_ids
    }
    assert dangling == set()


def test_package_internal_script_is_not_reported_as_direct_cli() -> None:
    payload = _run_scan({"invocations"})
    operator_paths = {
        record["source_path"]
        for record in payload["invocations"]
        if record["root_kind"] == "operator_cli"
    }

    assert "scripts/relaylm_repo_inventory/cli.py" not in operator_paths
    assert "scripts/relaylm_repo_inventory_cli.py" in operator_paths


def test_yaml_config_evidence_tracks_full_dotted_paths() -> None:
    payload = _run_scan({"config"})
    by_name = {
        record["name"]: record
        for record in payload["config"]
        if record["key_kind"] in {"config_key", "feature_flag"}
    }

    top_mode = by_name["mode"]["evidence"][0]
    route_mode = by_name[
        "model_routes.relaylm-default.mode"
    ]["evidence"][0]
    assert route_mode["line"] != top_mode["line"]
    assert route_mode["line"] > top_mode["line"]

    top_policy = by_name["common_runtime_policy"]["evidence"][0]
    character_policy = by_name[
        "characters.default.common_runtime_policy"
    ]["evidence"][0]
    assert character_policy["line"] != top_policy["line"]
    assert character_policy["line"] > top_policy["line"]
