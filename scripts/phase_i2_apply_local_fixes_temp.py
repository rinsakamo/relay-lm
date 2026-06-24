from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(args, cwd=cwd, env=merged, check=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_if_present(path: str, old: str, new: str, *, count: int = -1) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        return
    write(path, text.replace(old, new, count))


def append_if_missing(path: str, marker: str, block: str) -> None:
    text = read(path)
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + block.strip() + "\n")


def insert_before_if_missing(path: str, marker: str, anchor: str, block: str) -> None:
    text = read(path)
    if marker in text:
        return
    if anchor in text:
        write(path, text.replace(anchor, block.rstrip() + "\n\n" + anchor, 1))
    else:
        append_if_missing(path, marker, block)


def harden_observation_code() -> None:
    replace_if_present(
        "relaylm/soul_lab_observation.py",
        '"relayrun_status": "completed" if http_status < 500 else "failed",',
        '"relayrun_status": "completed" if 200 <= http_status < 400 else "failed",',
    )

    store_path = "relaylm/soul_lab_observation_store.py"
    store = read(store_path)
    if "def read_run_receipts_for_scope(" not in store:
        anchor = '''def read_run_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(store_root, "runs", RUN_RECEIPT_SCHEMA, _validate_run_payload)


'''
        addition = anchor + '''def read_run_receipts_for_scope(
    store_root: object, character_id: str, namespace: str
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return [], ["observation_character_id_invalid"]
    if not isinstance(namespace, str) or _TOKEN_RE.fullmatch(namespace) is None:
        return [], ["observation_namespace_invalid"]
    return _read_receipts(
        store_root,
        "runs",
        RUN_RECEIPT_SCHEMA,
        _validate_run_payload,
        predicate=lambda item: (
            item.get("character_id") == character_id
            and item.get("namespace") == namespace
        ),
    )


'''
        if anchor not in store:
            raise RuntimeError("run receipt helper anchor missing")
        store = store.replace(anchor, addition, 1)
    if "def read_outcome_receipts_for_namespace(" not in store:
        anchor = '''def read_outcome_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(
        store_root, "outcomes", OUTCOME_RECEIPT_SCHEMA, _validate_outcome_payload
    )


'''
        addition = anchor + '''def read_outcome_receipts_for_namespace(
    store_root: object, namespace: str
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(namespace, str) or _TOKEN_RE.fullmatch(namespace) is None:
        return [], ["observation_namespace_invalid"]
    return _read_receipts(
        store_root,
        "outcomes",
        OUTCOME_RECEIPT_SCHEMA,
        _validate_outcome_payload,
        predicate=lambda item: item.get("namespace") == namespace,
    )


'''
        if anchor not in store:
            raise RuntimeError("outcome namespace helper anchor missing")
        store = store.replace(anchor, addition, 1)
    store = store.replace(
        '"read_outcome_receipts", "read_outcome_receipts_for_run", "read_run_receipts",\n'
        '    "read_used_receipt_for_run", "read_used_receipts",',
        '"read_outcome_receipts", "read_outcome_receipts_for_namespace",\n'
        '    "read_outcome_receipts_for_run", "read_run_receipts",\n'
        '    "read_run_receipts_for_scope", "read_used_receipt_for_run",\n'
        '    "read_used_receipts",',
    )
    write(store_path, store)

    projection_path = "relaylm/soul_lab_observation_projection.py"
    projection = read(projection_path)
    projection = projection.replace(
        '''    read_outcome_receipts,
    read_outcome_receipts_for_run,
    read_run_receipts,
    read_used_receipt_for_run,
    read_used_receipts,
''',
        '''    read_outcome_receipts_for_namespace,
    read_outcome_receipts_for_run,
    read_run_receipts_for_scope,
    read_used_receipt_for_run,
''',
    )
    projection = projection.replace(
        "runs, run_reasons = read_run_receipts(scope.store_root)",
        "runs, run_reasons = read_run_receipts_for_scope(\n"
        "        scope.store_root, scope.character_id, scope.namespace\n"
        "    )",
    )
    projection = projection.replace(
        "receipts, reasons = read_outcome_receipts(scope.store_root)",
        "receipts, reasons = read_outcome_receipts_for_namespace(\n"
        "        scope.store_root, scope.namespace\n"
        "    )",
    )
    if "def _outcome_order_key(" not in projection:
        anchor = '''def _run_order_key(item: dict[str, object]) -> tuple[datetime, str]:
    completed = datetime.fromisoformat(str(item["completed_at"]).replace("Z", "+00:00"))
    return completed.astimezone(timezone.utc), str(item["run_id"])


'''
        addition = anchor + '''def _outcome_order_key(item: dict[str, object]) -> tuple[datetime, str, str]:
    observed = datetime.fromisoformat(str(item["observed_at"]).replace("Z", "+00:00"))
    return (
        observed.astimezone(timezone.utc),
        str(item.get("run_id", "")),
        str(item.get("job_correlation_id", "")),
    )


'''
        if anchor not in projection:
            raise RuntimeError("outcome order helper anchor missing")
        projection = projection.replace(anchor, addition, 1)
    projection = projection.replace(
        'selected.sort(key=lambda item: (str(item.get("observed_at", "")), str(item.get("run_id", "")), str(item.get("job_correlation_id", ""))), reverse=True)',
        "selected.sort(key=_outcome_order_key, reverse=True)",
    )
    write(projection_path, projection)

    security_path = "scripts/relaylm_phase_i2_lab_observation_security_smoke.py"
    security = read(security_path)
    if "other-namespace-flood" not in security:
        anchor = '''        outcome_dir = scoped / ".relaylm-lab-observation-v0" / "outcomes"
'''
        addition = '''        # Newer records from another namespace must not starve this scope.
        for index in range(3):
            write_outcome_receipt(
                str(scoped),
                {
                    "schema": OUTCOME_RECEIPT_SCHEMA,
                    "runtime_private": True,
                    "read_model_only": True,
                    "run_id": "other-namespace-flood",
                    "job_correlation_id": stable_correlation(f"other-job-{index}"),
                    "namespace": OTHER_NAMESPACE,
                    "turn_index": index,
                    "outcome_status": "held",
                    "worker_status": "pipeline_held",
                    "pipeline_status": "held",
                    "title": "other namespace",
                    "bounded_summary": "must not hide the requested namespace",
                    "observed_at": f"2099-01-01T00:0{index}:00+00:00",
                    "reason_ids": ["other_namespace_flood"],
                },
            )

''' + anchor
        if anchor not in security:
            raise RuntimeError("security outcome insertion anchor missing")
        security = security.replace(anchor, addition, 1)
    security = security.replace(
        '''        try:
            latest = build_lab_last_run_projection(scope)
            used = build_lab_memory_used_projection(scope)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
''',
        '''        try:
            latest = build_lab_last_run_projection(scope)
            used = build_lab_memory_used_projection(scope)
            held_scoped = build_lab_memory_held_projection(scope, limit=2)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
''',
    )
    security = security.replace(
        '''        require(len(used.items) == 16, used.model_dump())
        held = build_lab_memory_held_projection(scope, limit=50)
''',
        '''        require(len(used.items) == 16, used.model_dump())
        require(len(held_scoped.items) == 2, held_scoped.model_dump())
        require(all(item.run_id == "run-b" for item in held_scoped.items), held_scoped.model_dump())
        held = build_lab_memory_held_projection(scope, limit=50)
''',
    )
    write(security_path, security)


def reconcile_documents() -> None:
    replace_if_present(
        "docs/PROJECT_STATUS.md",
        "Next boundary: Phase I-3 auditable Correct operation",
        "I1-G pre-enqueue background-finalizer durability: unresolved\n"
        "Next product boundary: Phase I-3 auditable Correct operation",
    )
    replace_if_present(
        "docs/PROJECT_STATUS.md",
        "- I2 real SOUL Lab observation: complete\n- auditable Correct operation: next as Phase I-3",
        "- I2 real SOUL Lab observation: complete\n"
        "- I1-G pre-enqueue background-finalizer durability: unresolved\n"
        "- auditable Correct operation: next as Phase I-3",
    )
    append_if_missing(
        "docs/PROJECT_STATUS.md",
        "## Phase I-2 and I1-G cross-boundary status",
        '''## Phase I-2 and I1-G cross-boundary status

- Phase 6-C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I1-G pre-enqueue background-finalizer durability: unresolved
- auditable Correct operation: next as Phase I-3

I1-G tracks the process-exit window after visible response delivery but before protected-source and B2 queue publication. Phase I-2 observation receipts do not repair or reclassify that durability gap.''',
    )

    insert_before_if_missing(
        "docs/architecture/pipeline_implementation_plan.md",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved",
        "## Active priority: Phase I-3 auditable Correct",
        '''### I1-D: next-turn recall validation — complete

Phase I-1 completes next-turn recall and character/namespace isolation.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 exposes bounded, loopback-only latest-run, formed, held/blocked, and actually injected memory evidence without changing RelayMEM, RelaySLP, RelayRUN, or RelayCTX authority.

### I1-G: pre-enqueue background-finalizer durability — unresolved

I1-G tracks termination after visible response delivery but before durable source and B2 queue publication. C1-5, C2, Phase I-1, and Phase I-2 do not close this boundary. `docs/config_schema.md`, the Current/Target matrix, and status smokes must move together; stale TODO or future-tense text in related documents is rejected.''',
    )
    append_if_missing(
        "docs/README.md",
        "Current/Target Boundary Matrix",
        '''## Phase I-2 / I1-G alignment

The [Current/Target Boundary Matrix](architecture/current_target_migration_guide.md) and [`config_schema.md`](config_schema.md) remain part of the boundary audit. Phase I-2 real observation is complete; I1-G pre-enqueue durability remains unresolved. Documentation review rejects stale TODO/future-tense text in related plans.''',
    )
    append_if_missing(
        "docs/architecture/README.md",
        "Phase I-1 completes next-turn recall with character/namespace isolation",
        '''## Phase I-2 / I1-G alignment

Phase I-1 completes next-turn recall with character/namespace isolation. Phase I-2 completes real read-only Lab observation. I1-G pre-enqueue background-finalizer durability remains unresolved and separate from queue scheduling and daemon lifecycle.''',
    )
    append_if_missing(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
        '''## I1-G boundary after Phase I-2

M3i-c next-turn recall and scope isolation: complete as Phase I-1.
M3i-d real read-only Lab observation: complete as Phase I-2.
I1-G pre-enqueue background-finalizer durability remains unresolved. Observation receipts cannot repair it.''',
    )
    append_if_missing(
        "docs/architecture/relaymem_slp_current_target.md",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
        '''## Phase I-2 / I1-G status

I1 next-turn Primary MEM recall: complete.
Character and namespace isolation: complete.
I2 real SOUL Lab observation: complete.
I1-G pre-enqueue background-finalizer durability remains unresolved.''',
    )
    append_if_missing(
        "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
        '''## I1-G boundary

I1-G pre-enqueue background-finalizer durability remains unresolved. Phase I-1 recall and Phase I-2 observation do not recover a turn that never reached durable source and B2 publication.''',
    )
    append_if_missing(
        "docs/architecture/phase_i2_real_soul_lab_observation.md",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
        '''## I1-G boundary

I1-G pre-enqueue background-finalizer durability remains unresolved. Lab observation receipts are secondary evidence and cannot repair, replay, or reclassify this gap.''',
    )

    current_smoke = '''#!/usr/bin/env python3
"""Validate current Phase 6, I1, I2, I1-G, and config documentation."""
from __future__ import annotations
import ast
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(path: str, *anchors: str) -> None:
    body = text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"

def forbid(path: str, *anchors: str) -> None:
    body = text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: stale anchors: {present!r}"

def config_fields() -> tuple[str, ...]:
    tree = ast.parse(text("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            return tuple(
                item.target.id for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            )
    raise AssertionError("RelayLMConfig not found")

def config_coverage(path: str) -> None:
    body = text(path)
    missing = [field for field in config_fields() if re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", body
    ) is None]
    assert not missing, f"{path}: missing config fields: {missing!r}"

def main() -> None:
    config_coverage("docs/config_schema.md")
    config_coverage("config.example.yaml")
    require("docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability: unresolved",
        "auditable Correct operation: next as Phase I-3")
    require("docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
        "### I1-D: next-turn recall validation — complete",
        "### I1-E / Phase I-2: real SOUL Lab observation — complete",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved",
        "`docs/config_schema.md`",
        "stale TODO or future-tense text in related documents")
    require("docs/architecture/current_target_migration_guide.md",
        "A1/A2/B0-B3, ordinary I1-B source-before-queue publication",
        "Phase I-1 verifies the later-turn retrieval path",
        "I1-G pre-enqueue durability",
        "relaymem_slp_runtime_enqueue_apply_enabled=false")
    require("docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: complete as Phase I-1",
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "I1-G pre-enqueue background-finalizer durability remains unresolved")
    require("docs/architecture/README.md",
        "Phase I-1 completes next-turn recall with character/namespace isolation",
        "Phase I-2 completes real read-only Lab observation",
        "I1-G pre-enqueue background-finalizer durability")
    require("docs/README.md",
        "`config_schema.md`", "Current/Target Boundary Matrix",
        "stale TODO/future-tense text in related plans",
        "phase_i2_real_soul_lab_observation.md", "I1-G")
    require("docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability")
    forbid("docs/PROJECT_STATUS.md", "SOUL Lab real observation: next")
    print("RelayLM documentation current-boundary smoke passed.")

if __name__ == "__main__":
    main()
'''
    write("scripts/relaylm_documentation_current_boundary_smoke.py", current_smoke)
    replace_if_present(
        "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
        '        "pre-enqueue background-finalizer crash window",\n',
        '        "I1-G",\n        "pre-enqueue background-finalizer",\n',
    )


def cleanup() -> None:
    run("git", "checkout", "origin/main", "--", ".github/workflows/soul-lab-ui.yml")
    for path in ROOT.glob("scripts/phase_i2_*_temp.py"):
        path.unlink(missing_ok=True)
    for path in (ROOT / ".github" / "workflows").glob("phase-i2-*-temp.yml"):
        path.unlink(missing_ok=True)


def validate() -> None:
    py = "python"
    env = {"PYTHONPATH": ".:scripts"}
    run(py, "-m", "compileall", "-q", "relaylm", "scripts")
    run(py, "scripts/relaylm_docs_link_check.py", env={"PYTHONPATH": "."})
    run(py, "scripts/relaylm_documentation_current_boundary_smoke.py", env={"PYTHONPATH": "."})
    run(py, "scripts/relaylm_phase_i2_documentation_boundary_smoke.py", env={"PYTHONPATH": "."})
    for script in (
        "scripts/relaylm_phase_i2_lab_observation_ci_runner.py",
        "scripts/relaylm_phase6c1_primary_worker_ci_runner.py",
        "scripts/relaylm_phase6c1_worker_integration_ci_runner.py",
        "scripts/relaylm_phase6c1_durable_protected_source_smoke.py",
        "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py",
        "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py",
    ):
        run(py, script, env=env)
    frontend = ROOT / "apps" / "soul-lab"
    run("npm", "install", "--no-audit", "--no-fund", cwd=frontend)
    run("npm", "run", "typecheck", cwd=frontend)
    shutil.rmtree(frontend / ".observation-smoke", ignore_errors=True)
    run("npx", "tsc", "src/features/lab/observationApi.ts",
        "--target", "ES2022", "--module", "ES2022",
        "--moduleResolution", "Bundler", "--outDir", ".observation-smoke",
        "--skipLibCheck", cwd=frontend)
    run("node", "scripts/observationApiSmoke.mjs", cwd=frontend)
    shutil.rmtree(frontend / ".observation-smoke", ignore_errors=True)
    run("npm", "run", "build", cwd=frontend)


def main() -> None:
    run("git", "config", "user.name", "github-actions")
    run("git", "config", "user.email", "actions@github.com")
    try:
        run("git", "fetch", "--unshallow", "origin")
    except subprocess.CalledProcessError:
        run("git", "fetch", "origin")
    run("git", "fetch", "origin", "main")
    run("git", "merge", "--no-ff", "--no-edit", "-X", "ours", "origin/main")
    harden_observation_code()
    reconcile_documents()
    cleanup()
    validate()
    run("git", "add", "-A")
    if subprocess.run(("git", "diff", "--cached", "--quiet"), cwd=ROOT).returncode != 0:
        run("git", "commit", "-m", "fix: finalize Phase I2 observation integration")
    run("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation")

if __name__ == "__main__":
    main()
