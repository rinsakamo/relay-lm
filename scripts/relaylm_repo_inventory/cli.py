"""CLI for the RelayLM repository/storage inventory tool.

Non-destructive by construction: every code path here only reads repository
source text and writes the requested report to stdout or --output. It never
edits, deletes, moves, or renames anything in the repository, and it never
marks a storage artifact as safe to remove or migrate.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import TOOL_VERSION
from . import (
    config_deps,
    invocations,
    repo,
    storage,
    storage_root_links,
    subprocess_aliases,
    toml_dependencies,
)
from .report import build_payload, render_json, render_markdown


def _run_scan(modes: set[str]) -> dict:
    invocation_roots = None
    if modes & {"invocations", "storage"}:
        invocation_roots = invocations.collect_all()
        invocation_roots.extend(subprocess_aliases.scan_subprocess_aliases())
        invocation_roots.sort(key=lambda record: record.sort_key())

    storage_records = None
    if "storage" in modes:
        raw_storage_records = storage.scan_storage_artifacts(invocation_roots)
        storage_root_links.attach_direct_roots(raw_storage_records, invocation_roots)
        storage_records = [record.to_dict() for record in raw_storage_records]

    invocation_dicts = None
    if "invocations" in modes:
        invocation_dicts = [r.to_dict() for r in invocation_roots]

    config_records = None
    if "config" in modes:
        raw_config_records = [
            record
            for record in config_deps.collect_all()
            if record.key_kind not in {"python_dependency", "extra_or_mode"}
        ]
        raw_config_records.extend(toml_dependencies.scan_python_dependencies())
        raw_config_records.sort(key=lambda record: record.sort_key())
        config_records = [record.to_dict() for record in raw_config_records]

    return build_payload(
        tool_version=TOOL_VERSION,
        source_commit_sha=repo.commit_sha(),
        modes=sorted(modes),
        storage=storage_records,
        invocations=invocation_dicts,
        config=config_records,
    )


def _render(payload: dict, fmt: str) -> str:
    if fmt == "json":
        return render_json(payload)
    if fmt == "markdown":
        return render_markdown(payload)
    raise ValueError(f"unknown format: {fmt}")


def _write_output(content: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def self_test() -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    payload_a = _run_scan({"storage", "invocations", "config"})
    payload_b = _run_scan({"storage", "invocations", "config"})
    json_a = render_json(payload_a)
    json_b = render_json(payload_b)
    if json_a != json_b:
        ok = False
        messages.append("FAIL: two consecutive scans produced different JSON output (non-deterministic).")
    else:
        messages.append("PASS: two consecutive scans produced byte-identical JSON output.")

    import json as _json

    try:
        _json.loads(json_a)
        messages.append("PASS: JSON output parses.")
    except _json.JSONDecodeError as exc:
        ok = False
        messages.append(f"FAIL: JSON output does not parse: {exc}")

    storage_records = payload_a.get("storage", [])
    invocation_records = payload_a.get("invocations", [])
    config_records = payload_a.get("config", [])

    if not storage_records:
        ok = False
        messages.append("FAIL: storage scan produced zero records.")
    else:
        messages.append(f"PASS: storage scan produced {len(storage_records)} record(s).")
        bad = [r for r in storage_records if r["classification_state"] != "unclassified"]
        if bad:
            ok = False
            messages.append(f"FAIL: {len(bad)} storage record(s) have classification_state != 'unclassified'.")
        else:
            messages.append("PASS: all storage records default to classification_state='unclassified'.")

        unanchored = []
        for record in storage_records:
            persistent_readers = [
                value for value in record["readers"] if value != "json.loads()"
            ]
            persistent_writers = [
                value for value in record["writers"] if value != "json.dumps()"
            ]
            if not (
                persistent_readers
                or persistent_writers
                or record["locking_or_atomicity_signals"]
                or record["durability_signals"]
                or not record["artifact_pattern"].startswith("module:")
            ):
                unanchored.append(record)
        if unanchored:
            ok = False
            messages.append(f"FAIL: {len(unanchored)} storage record(s) lack a concrete path or I/O anchor.")
        else:
            messages.append("PASS: every storage record has a concrete path or I/O/locking/durability anchor.")

        self_noise = [
            r
            for r in storage_records
            if r["source_path"].startswith("scripts/relaylm_repo_inventory/")
        ]
        if self_noise:
            ok = False
            messages.append(f"FAIL: {len(self_noise)} inventory implementation file(s) were self-reported as storage.")
        else:
            messages.append("PASS: inventory implementation files are excluded from storage self-noise.")

    o3_root = next(
        (r for r in invocation_records if r["source_path"] == "scripts/relaylm_o3_always_on_local_scheduler.py"),
        None,
    )
    if o3_root is None:
        ok = False
        messages.append("FAIL: O3 always-on local scheduler CLI was not discovered as an invocation root.")
    elif o3_root["root_kind"] != "operator_cli":
        ok = False
        messages.append(
            f"FAIL: O3 scheduler root_kind is '{o3_root['root_kind']}', expected 'operator_cli' (not smoke-only)."
        )
    else:
        messages.append("PASS: O3 always-on local scheduler CLI is classified as operator_cli, not smoke-only or dead.")

    kinds_present = {r["root_kind"] for r in invocation_records}
    for expected_kind in (
        "github_actions_step",
        "npm_script",
        "operator_cli",
        "pytest_root",
        "frontend_route",
        "subprocess_child",
        "fastapi_route",
    ):
        if expected_kind not in kinds_present:
            ok = False
            messages.append(f"FAIL: no invocation record of kind '{expected_kind}' was found.")
        else:
            messages.append(f"PASS: found at least one invocation record of kind '{expected_kind}'.")

    if not any(
        r["source_path"] == "relaylm/soul_lab_memory_forget_routes.py"
        and r["root_kind"] == "fastapi_route"
        and r["command_or_symbol"].endswith("/forget/preflight")
        for r in invocation_records
    ):
        ok = False
        messages.append("FAIL: multi-line SOUL Lab Forget FastAPI route was not discovered.")
    else:
        messages.append("PASS: multi-line SOUL Lab Forget FastAPI route was discovered.")

    if not any(
        r["source_path"] == "apps/soul-lab/src/app/RootApp.tsx"
        and r["root_kind"] == "frontend_route"
        and r["command_or_symbol"] == "#/memory"
        for r in invocation_records
    ):
        ok = False
        messages.append("FAIL: canonical hash-based SOUL Lab memory route was not discovered.")
    else:
        messages.append("PASS: canonical hash-based SOUL Lab memory route was discovered.")

    if not any(
        r["source_path"] == "scripts/relaylm_phase_i4b_ci_runner.py"
        and r["root_kind"] == "subprocess_child"
        for r in invocation_records
    ):
        ok = False
        messages.append("FAIL: tuple-driven multi-line subprocess children were not discovered.")
    else:
        messages.append("PASS: tuple-driven multi-line subprocess children were discovered.")

    if not any(
        r["source_path"] == "scripts/relaylm_mvp_eval_runner_impl.py"
        and r["root_kind"] == "subprocess_child"
        for r in invocation_records
    ):
        ok = False
        messages.append("FAIL: subprocess module aliases were not discovered.")
    else:
        messages.append("PASS: subprocess module aliases were discovered.")

    if not any(
        r["source_path"] == "scripts/relaylm_trace_success_smoke.py"
        and any(root.startswith("smoke_only_root:scripts/relaylm_trace_success_smoke.py") for root in r["invocation_roots"])
        for r in storage_records
    ):
        ok = False
        messages.append("FAIL: directly invoked storage scripts were not linked to their own roots.")
    else:
        messages.append("PASS: directly invoked storage scripts are linked to their own roots.")

    config_keys = {(record["key_kind"], record["name"], record["source_context"]) for record in config_records}
    if ("python_dependency", "uvicorn", "runtime") not in config_keys:
        ok = False
        messages.append("FAIL: uvicorn[standard] was truncated from runtime dependencies.")
    else:
        messages.append("PASS: runtime dependency extras are parsed without truncation.")
    if ("extra_or_mode", "relay-lm", "optional-dependencies.dev") not in config_keys:
        ok = False
        messages.append("FAIL: relay-lm[test] was truncated from optional dependencies.")
    else:
        messages.append("PASS: optional dependency extras are parsed without truncation.")

    if not any("json.load" in ",".join(r["readers"]) or "json.loads" in ",".join(r["readers"]) for r in storage_records):
        ok = False
        messages.append("FAIL: no storage record shows a JSON reader signal.")
    else:
        messages.append("PASS: at least one storage record shows a JSON reader signal.")
    if not any(r["writers"] for r in storage_records if "json.dump" in ",".join(r["writers"])):
        ok = False
        messages.append("FAIL: no storage record shows a JSON writer signal.")
    else:
        messages.append("PASS: at least one storage record shows a JSON writer signal.")
    if not any(r["locking_or_atomicity_signals"] for r in storage_records):
        ok = False
        messages.append("FAIL: no storage record shows a locking/atomicity signal.")
    else:
        messages.append("PASS: at least one storage record shows a locking/atomicity signal.")

    if not any(r["key_kind"] == "env_var" for r in config_records):
        ok = False
        messages.append("FAIL: no env_var config record was found.")
    else:
        messages.append("PASS: at least one env_var config record was found.")

    return ok, messages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="relaylm_repo_inventory",
        description=(
            "Deterministic, non-destructive repository and storage inventory. "
            "Produces evidence for human review; makes no removal/migration/dead-code decisions."
        ),
    )
    parser.add_argument("--storage", action="store_true", help="Include Part A: storage artifact inventory.")
    parser.add_argument("--invocations", action="store_true", help="Include Part B: invocation-root inventory.")
    parser.add_argument("--config", action="store_true", help="Include Part C: config/feature/dependency inventory.")
    parser.add_argument("--all", action="store_true", help="Include all three inventory parts.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format.")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path instead of stdout.")
    parser.add_argument("--self-test", action="store_true", help="Run internal self-checks and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        ok, messages = self_test()
        for message in messages:
            print(message)
        print("SELF-TEST " + ("PASSED" if ok else "FAILED"))
        return 0 if ok else 1

    modes: set[str] = set()
    if args.all:
        modes = {"storage", "invocations", "config"}
    else:
        if args.storage:
            modes.add("storage")
        if args.invocations:
            modes.add("invocations")
        if args.config:
            modes.add("config")

    if not modes:
        parser.error("at least one of --storage, --invocations, --config, --all, or --self-test is required")

    payload = _run_scan(modes)
    content = _render(payload, args.format)
    _write_output(content, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
