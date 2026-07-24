"""Focused coverage for the non-destructive repository/storage inventory tool.

scripts/ is a flat directory of operator tooling, not an installed package,
so it is added to sys.path the same way the tool's own scripts do (see
scripts/relaylm_repo_inventory_cli.py) before importing.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory import config_deps, invocations, repo, storage  # noqa: E402
from relaylm_repo_inventory.cli import _run_scan, self_test  # noqa: E402
from relaylm_repo_inventory.report import render_json  # noqa: E402


def _find_storage(records, source_path):
    return next((r for r in records if r.source_path == source_path), None)


def _find_invocation(records, source_path, root_kind=None):
    for record in records:
        if record.source_path == source_path and (
            root_kind is None or record.root_kind == root_kind
        ):
            return record
    return None


def test_o3_scheduler_operator_cli_not_reachable_from_app_py():
    """The O3 always-on local scheduler is a real, load-bearing operator CLI."""
    records = invocations.collect_all()
    record = _find_invocation(records, "scripts/relaylm_o3_always_on_local_scheduler.py")
    assert record is not None, "O3 scheduler CLI must be discovered as an invocation root"
    assert record.root_kind == "operator_cli"
    assert "python scripts/relaylm_o3_always_on_local_scheduler.py" == record.command_or_symbol
    joined_notes = " ".join(record.notes).lower()
    assert "dead" not in joined_notes
    assert "smoke-only" not in joined_notes
    assert "safe to delete" not in joined_notes
    assert "remove" not in joined_notes

    smoke_record = _find_invocation(
        records,
        "scripts/relaylm_o3_always_on_local_scheduler_smoke.py",
        "smoke_only_root",
    )
    assert smoke_record is not None
    assert smoke_record.root_id != record.root_id


def test_workflow_command_discovered():
    records = invocations.collect_all()
    matches = [
        record
        for record in records
        if record.root_kind == "github_actions_step"
        and record.source_path == ".github/workflows/scripts-inventory.yml"
    ]
    assert matches, "expected at least one github_actions_step root from scripts-inventory.yml"
    assert any("relaylm_generate_scripts_inventory.py" in record.command_or_symbol for record in matches)


def test_multiline_workflow_command_preserves_actual_invocation():
    records = invocations.collect_all()
    matches = [
        record
        for record in records
        if record.root_kind == "github_actions_step"
        and record.source_path == ".github/workflows/smoke-relaymem.yml"
    ]
    assert matches
    command = next(
        record.command_or_symbol
        for record in matches
        if "run --workflow relaymem --group primary_memory" in record.command_or_symbol
    )
    assert command.splitlines()[0] == "set -o pipefail"
    assert "python scripts/relaylm_ci_consolidated_smoke.py" in command


def test_frontend_npm_script_discovered():
    records = invocations.collect_all()
    dev_script = next(
        (
            record
            for record in records
            if record.root_kind == "npm_script"
            and record.source_path == "apps/soul-lab/package.json"
            and "npm run dev" in record.command_or_symbol
        ),
        None,
    )
    assert dev_script is not None
    assert "vite" in dev_script.command_or_symbol


def test_hash_based_frontend_routes_discovered():
    records = invocations.collect_all()
    routes = {
        record.command_or_symbol
        for record in records
        if record.root_kind == "frontend_route"
        and record.source_path == "apps/soul-lab/src/app/RootApp.tsx"
    }
    assert {"#/home", "#/create", "#/memory", "#/advanced"} <= routes


def test_multiline_fastapi_routes_discovered_with_entrypoint_reachability():
    records = invocations.collect_all()
    forget_routes = [
        record
        for record in records
        if record.root_kind == "fastapi_route"
        and record.source_path == "relaylm/soul_lab_memory_forget_routes.py"
    ]
    symbols = {record.command_or_symbol for record in forget_routes}
    assert (
        "POST /lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight"
        in symbols
    )
    assert "GET /lab/api/characters/{character_id}/memory/{memory_id}/forget-history" in symbols
    assert all(record.reachable_from_fastapi_import_graph is False for record in forget_routes)
    assert all("SOUL Lab entry point" in " ".join(record.notes) for record in forget_routes)

    core_health = next(
        record
        for record in records
        if record.root_kind == "fastapi_route"
        and record.source_path == "relaylm/app.py"
        and record.command_or_symbol == "GET /healthz"
    )
    assert core_health.reachable_from_fastapi_import_graph is True


def test_multiline_and_tuple_driven_subprocess_children_discovered():
    records = invocations.collect_all()
    children = [
        record
        for record in records
        if record.root_kind == "subprocess_child"
        and record.source_path == "scripts/relaylm_phase_i4b_ci_runner.py"
    ]
    assert children
    commands = {record.command_or_symbol for record in children}
    assert "python relaylm_phase_i4b_primary_current_state_resolver_smoke.py" in commands
    assert "python relaylm_phase_i4b_final_review_regression_smoke.py" in commands


def test_subprocess_module_alias_dispatcher_discovered():
    payload = _run_scan({"invocations"})
    matches = [
        record
        for record in payload["invocations"]
        if record["root_kind"] == "subprocess_child"
        and record["source_path"] == "scripts/relaylm_mvp_eval_runner_impl.py"
    ]
    assert matches
    assert any(
        record["command_or_symbol"] == "unresolved subprocess invocation"
        for record in matches
    )


def test_dependency_arrays_with_extras_are_not_truncated():
    payload = _run_scan({"config"})
    records = {
        (record["key_kind"], record["name"], record["source_context"])
        for record in payload["config"]
    }
    assert ("python_dependency", "uvicorn", "runtime") in records
    assert ("extra_or_mode", "relay-lm", "optional-dependencies.dev") in records


def test_storage_script_links_to_its_direct_invocation_root():
    payload = _run_scan({"storage"})
    record = next(
        record
        for record in payload["storage"]
        if record["source_path"] == "scripts/relaylm_trace_success_smoke.py"
    )
    assert (
        "smoke_only_root:scripts/relaylm_trace_success_smoke.py"
        in record["invocation_roots"]
    )


def test_excluded_directories_are_pruned_before_walk(tmp_path, monkeypatch):
    kept = tmp_path / "kept"
    kept.mkdir()
    expected = kept / "x.py"
    expected.write_text("pass\n", encoding="utf-8")
    observed: dict[str, list[str]] = {}

    def fake_walk(root_arg, *, topdown, followlinks):
        assert Path(root_arg) == tmp_path
        assert topdown is True
        assert followlinks is False
        dirnames = ["node_modules", ".venv", "kept"]
        yield str(tmp_path), dirnames, []
        observed["after_prune"] = list(dirnames)
        yield str(kept), [], ["x.py"]

    monkeypatch.setattr(repo.os, "walk", fake_walk)
    assert repo.iter_repo_files(root=tmp_path, suffixes=(".py",)) == [expected]
    assert observed["after_prune"] == ["kept"]


def test_json_writer_and_reader_discovered():
    records = storage.scan_storage_artifacts()
    writer = _find_storage(records, "relaylm/runtime_install_cli.py")
    assert writer is not None
    assert any("json.dump" in value for value in writer.writers)
    assert writer.classification_state == "unclassified"

    reader = _find_storage(records, "relaylm/client_instruction_cache_reader.py")
    assert reader is not None
    assert any("json.loads" in value for value in reader.readers)
    assert reader.classification_state == "unclassified"


def test_lock_and_atomic_write_signal_discovered():
    records = storage.scan_storage_artifacts()
    lock_module = _find_storage(records, "relaylm/portable_lock.py")
    assert lock_module is not None
    assert lock_module.locking_or_atomicity_signals
    assert any(
        "fcntl.flock" in value or "msvcrt.locking" in value
        for value in lock_module.locking_or_atomicity_signals
    )

    queue_module = _find_storage(records, "relaylm/relaymem_slp_queue_storage.py")
    assert queue_module is not None
    assert any("os.replace" in value for value in queue_module.locking_or_atomicity_signals)
    assert any("fsync" in value for value in queue_module.durability_signals)


def test_env_var_config_key_discovered():
    records = config_deps.scan_env_vars()
    env_names = {record.name for record in records}
    assert "RELAYLM_CONFIG" in env_names
    record = next(record for record in records if record.name == "RELAYLM_CONFIG")
    assert "relaylm/config.py" in record.referenced_in


def test_deterministic_output_across_runs():
    payload_a = _run_scan({"storage", "invocations", "config"})
    payload_b = _run_scan({"storage", "invocations", "config"})
    assert render_json(payload_a) == render_json(payload_b)
    assert payload_a["source_commit_sha"] == payload_b["source_commit_sha"]
    assert payload_a["tool_version"] == payload_b["tool_version"]


def test_storage_records_require_concrete_anchor_and_exclude_scanner_self_noise():
    records = storage.scan_storage_artifacts()
    assert records
    for record in records:
        has_literal_path = not record.artifact_pattern.startswith("module:")
        persistent_readers = [
            value for value in record.readers if value != "json.loads()"
        ]
        persistent_writers = [
            value for value in record.writers if value != "json.dumps()"
        ]
        assert (
            has_literal_path
            or persistent_readers
            or persistent_writers
            or record.locking_or_atomicity_signals
            or record.durability_signals
        )
        assert not record.source_path.startswith("scripts/relaylm_repo_inventory/")


def test_false_positive_resistance():
    records = storage.scan_storage_artifacts()
    by_path = {record.source_path for record in records}

    assert "relaylm/__init__.py" not in by_path
    assert not any(path.startswith("docs/") for path in by_path)
    assert "README.md" not in by_path

    # These UI/API files contain memory/cache/queue vocabulary or display file
    # names, but do not bind durable paths or perform storage I/O.
    assert "apps/soul-lab/src/features/workspace/CharacterWorkspacePages.tsx" not in by_path
    assert "relaylm/audit_projection.py" not in by_path
    assert "relaylm/soul_lab_memory_forget_routes.py" not in by_path


def test_classification_state_never_decided():
    records = storage.scan_storage_artifacts()
    assert records, "expected at least one storage record from the live repository"
    assert all(record.classification_state == "unclassified" for record in records)
    assert all("classification_state" not in record.heuristic_fields for record in records)


def test_self_test_passes_on_current_tree():
    ok, messages = self_test()
    assert ok, "\n".join(messages)


def test_json_output_round_trips():
    payload = _run_scan({"storage", "invocations", "config"})
    rendered = render_json(payload)
    reloaded = json.loads(rendered)
    assert reloaded["storage_count"] == len(reloaded["storage"])
    assert reloaded["invocations_count"] == len(reloaded["invocations"])
    assert reloaded["config_count"] == len(reloaded["config"])


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


def test_runtime_install_uses_only_canonical_installed_entrypoint() -> None:
    payload = _run_scan({"invocations"})
    records = payload["invocations"]
    console_records = [
        record
        for record in records
        if record["root_id"] == "console_script:relaylm-runtime-install"
    ]

    assert len(console_records) == 1
    assert (
        console_records[0]["command_or_symbol"]
        == "relaylm-runtime-install -> relaylm.runtime_install_cli:main"
    )
    assert not any(
        record["root_kind"] == "python_dash_m"
        and record["source_path"] == "relaylm/runtime_install_cli.py"
        for record in records
    )


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


def test_literal_tuple_subprocess_loop_is_expanded() -> None:
    payload = _run_scan({"invocations"})
    commands = {
        record["command_or_symbol"]
        for record in payload["invocations"]
        if record["root_kind"] == "subprocess_child"
        and record["source_path"]
        == "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py"
    }
    assert {
        "python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py",
        "python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py",
        "python scripts/relaylm_documentation_current_boundary_smoke.py",
    } <= commands
    assert "unresolved subprocess invocation" not in commands


def test_dynamic_import_inventory_uses_ast_calls_only() -> None:
    payload = _run_scan({"invocations"})
    dynamic = [
        record
        for record in payload["invocations"]
        if record["root_kind"] == "dynamic_import"
    ]
    assert dynamic
    assert all(
        record["source_path"] != "scripts/relaylm_repo_inventory/invocations.py"
        for record in dynamic
    )
    assert all("_DYNAMIC_IMPORT_RE" not in record["command_or_symbol"] for record in dynamic)
    assert any(
        record["source_path"] == "scripts/relaylm_package_import_purity_smoke.py"
        for record in dynamic
    )


def test_literal_children_relink_storage_roots() -> None:
    payload = _run_scan({"storage", "invocations"})
    record = next(
        item
        for item in payload["storage"]
        if item["source_path"]
        == "scripts/relaylm_documentation_current_boundary_smoke.py"
    )
    assert any(
        root.startswith(
            "subprocess_child:scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py"
        )
        for root in record["invocation_roots"]
    )
