from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    merged_env = None
    if env is not None:
        import os

        merged_env = os.environ.copy()
        merged_env.update(env)
    subprocess.run(args, cwd=cwd, env=merged_env, check=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor in {path}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def ensure_before(path: str, anchor: str, addition: str) -> None:
    text = read(path)
    if addition.strip() in text:
        return
    if anchor not in text:
        raise RuntimeError(f"missing insertion anchor in {path}: {anchor[:100]!r}")
    write(path, text.replace(anchor, addition + anchor, 1))


def replace_phrase(path: str, old: str, new: str) -> None:
    text = read(path)
    if old in text:
        write(path, text.replace(old, new))


def reconcile_documents() -> None:
    replace_once(
        "docs/PROJECT_STATUS.md",
        "- Phase I-2 real SOUL Lab latest-run and memory observation integration.\n",
        "- Phase I-2 real SOUL Lab latest-run and memory observation integration,\n"
        "- explicit I1-G tracking for the unresolved pre-enqueue background-finalizer durability boundary.\n",
    )
    replace_once(
        "docs/PROJECT_STATUS.md",
        "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected\n"
        "Next boundary: Phase I-3 auditable Correct operation\n",
        "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected\n"
        "I1-G pre-enqueue background-finalizer durability: unresolved\n"
        "Next product boundary: Phase I-3 auditable Correct operation\n",
    )
    replace_phrase(
        "docs/PROJECT_STATUS.md",
        "- the pre-enqueue background-finalizer crash window remains unresolved:",
        "- I1-G, the pre-enqueue background-finalizer crash window, remains unresolved:",
    )
    replace_once(
        "docs/PROJECT_STATUS.md",
        "- I2 real SOUL Lab observation: complete\n"
        "- auditable Correct operation: next as Phase I-3\n",
        "- I2 real SOUL Lab observation: complete\n"
        "- I1-G pre-enqueue background-finalizer durability: unresolved\n"
        "- auditable Correct operation: next as Phase I-3\n",
    )
    replace_phrase(
        "docs/PROJECT_STATUS.md",
        "restart completion for the pre-enqueue background-finalizer crash window",
        "restart completion for I1-G's pre-enqueue background-finalizer crash window",
    )

    replace_once(
        "docs/architecture/pipeline_implementation_plan.md",
        "  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete\n\n"
        "RelayMEM Primary integration:\n",
        "  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete\n"
        "  I1-G pre-enqueue background-finalizer durability: unresolved\n\n"
        "RelayMEM Primary integration:\n",
    )
    replace_once(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase I-1 next-turn recall and scope isolation are complete. Phase I-2 real SOUL Lab observation is complete. Phase I-3 auditable Correct is the next product boundary.\n",
        "Phase I-1 next-turn recall and scope isolation are complete. Phase I-2 real SOUL Lab observation is complete. Phase I-3 auditable Correct is the next product boundary; I1-G remains a separate unresolved durability boundary.\n",
    )
    replace_once(
        "docs/architecture/pipeline_implementation_plan.md",
        "### I1-D: next-turn recall and isolation — complete\n\nPhase I-1 proves:\n",
        "### I1-D: next-turn recall validation — complete\n\n"
        "Phase I-1 completes next-turn recall and character/namespace isolation.\n\n"
        "Phase I-1 proves:\n",
    )
    ensure_before(
        "docs/architecture/pipeline_implementation_plan.md",
        "## Active priority: Phase I-3 auditable Correct\n",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved\n\n"
        "I1-G tracks the process-exit window after visible response delivery but before the protected source and B2 queue record are durably published. C1-5, C2, Phase I-1, and Phase I-2 do not claim to close this boundary. Its future contract must preserve visible-response independence, content-free queue records, protected-source confidentiality, and idempotent replay without introducing queue scanning or daemon lifecycle.\n\n",
    )
    replace_phrase(
        "docs/architecture/pipeline_implementation_plan.md",
        "The pre-enqueue background-finalizer crash window remains explicitly outside this completion claim.",
        "I1-G, the pre-enqueue background-finalizer crash window, remains explicitly outside this completion claim.",
    )
    replace_phrase(
        "docs/architecture/pipeline_implementation_plan.md",
        "the pre-enqueue process-exit window is not restart-complete",
        "I1-G's pre-enqueue process-exit window is not restart-complete",
    )
    ensure_before(
        "docs/architecture/pipeline_implementation_plan.md",
        "## Deferred after the current boundary\n",
        "Documentation and configuration alignment remains part of every boundary move: `docs/config_schema.md`, the Current/Target matrix, and status smokes must be updated together, and stale TODO or future-tense text in related documents must be rejected.\n\n",
    )

    ensure_before(
        "docs/README.md",
        "## Canonical precedence\n",
        "The [Current/Target Boundary Matrix](architecture/current_target_migration_guide.md) and [`config_schema.md`](config_schema.md) remain part of the current-boundary audit. Documentation review must reject stale TODO/future-tense text in related plans. I1-G explicitly tracks the unresolved pre-enqueue background-finalizer durability gap; Phase I-2 does not close it.\n\n",
    )
    ensure_before(
        "docs/architecture/README.md",
        "## Completed Core streaming boundary\n",
        "Phase I-1 completes next-turn recall with character/namespace isolation. Phase I-2 completes real read-only Lab observation. I1-G pre-enqueue background-finalizer durability remains unresolved and is separate from both observation and queue scheduling.\n\n",
    )

    replace_phrase(
        "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
        "visible-response-to-background-publication pre-enqueue crash recovery",
        "I1-G pre-enqueue background-finalizer durability recovery",
    )
    replace_phrase(
        "docs/architecture/phase_i2_real_soul_lab_observation.md",
        "pre-enqueue background-finalizer crash recovery",
        "I1-G pre-enqueue background-finalizer durability recovery",
    )
    replace_phrase(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "pre-enqueue background-finalizer crash window",
        "I1-G pre-enqueue background-finalizer durability gap",
    )
    replace_phrase(
        "docs/architecture/relaymem_slp_current_target.md",
        "pre-enqueue background-finalizer crash window",
        "I1-G pre-enqueue background-finalizer durability gap",
    )
    replace_phrase(
        "docs/architecture/soul_lab_runtime_mvp.md",
        "pre-enqueue background-finalizer crash window",
        "I1-G pre-enqueue background-finalizer durability gap",
    )
    replace_phrase(
        "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
        "pre-enqueue background-finalizer crash window",
        "I1-G pre-enqueue background-finalizer durability gap",
    )
    replace_phrase(
        "docs/architecture/soul_lab_ui_mvp.md",
        "pre-enqueue background-finalizer crash window",
        "I1-G pre-enqueue background-finalizer durability gap",
    )

    for path, anchor in (
        ("docs/architecture/relaymem_mvp_implementation_plan.md", "## Non-goals for the current memory-operation boundary\n"),
        ("docs/architecture/relaymem_slp_current_target.md", "## Current limitations\n"),
        ("docs/architecture/integration_i1_primary_mem_two_turn_recall.md", "## Explicitly unresolved\n"),
        ("docs/architecture/phase_i2_real_soul_lab_observation.md", "## Completion boundary\n"),
    ):
        ensure_before(
            path,
            anchor,
            "I1-G pre-enqueue background-finalizer durability remains unresolved. It is not repaired or reclassified by Phase I-2 observation receipts.\n\n",
        )

    current_boundary_smoke = '''#!/usr/bin/env python3
"""Validate current Phase 6, I1, I2, I1-G, and config documentation."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read_text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read_text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: superseded boundary remains: {present!r}"


def relaylm_config_fields() -> tuple[str, ...]:
    tree = ast.parse(read_text("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            fields = tuple(
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            )
            assert fields
            return fields
    raise AssertionError("RelayLMConfig class not found")


def require_config_coverage(path: str) -> None:
    body = read_text(path)
    missing = [
        field for field in relaylm_config_fields()
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", body) is None
    ]
    assert not missing, f"{path}: missing RelayLMConfig fields: {missing!r}"


def main() -> None:
    require_config_coverage("docs/config_schema.md")
    require_config_coverage("config.example.yaml")
    require(
        "docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability: unresolved",
        "auditable Correct operation: next as Phase I-3",
    )
    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
        "### I1-D: next-turn recall validation — complete",
        "### I1-E / Phase I-2: real SOUL Lab observation — complete",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved",
        "Phase I-3 auditable Correct is the next product boundary",
        "`docs/config_schema.md`",
        "stale TODO or future-tense text in related documents",
    )
    require(
        "docs/architecture/current_target_migration_guide.md",
        "A1/A2/B0-B3, ordinary I1-B source-before-queue publication",
        "Phase I-1 verifies the later-turn retrieval path",
        "I1-G pre-enqueue durability",
        "relaymem_slp_runtime_enqueue_apply_enabled=false",
    )
    require(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: complete as Phase I-1",
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
    )
    require(
        "docs/architecture/README.md",
        "Phase I-1 completes next-turn recall with character/namespace isolation",
        "Phase I-2 completes real read-only Lab observation",
        "I1-G pre-enqueue background-finalizer durability",
    )
    require(
        "docs/README.md",
        "`config_schema.md`",
        "Current/Target Boundary Matrix",
        "stale TODO/future-tense text in related plans",
        "phase_i2_real_soul_lab_observation.md",
        "I1-G",
    )
    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability",
    )
    require(
        "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
        "exact queued B3 record",
        "canonical B3 claim",
        "C1-5 protected-source lookup / rehydrate",
        "unchanged C1-2 one-claimed worker",
        "Queue scanning/scheduling",
        "Phase I-1 is complete",
    )
    forbid(
        "docs/PROJECT_STATUS.md",
        "SOUL Lab real observation: next",
        "latest-run and real memory-outcome reads remain unimplemented",
    )
    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
'''
    write("scripts/relaylm_documentation_current_boundary_smoke.py", current_boundary_smoke)

    replace_once(
        "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
        '        "pre-enqueue background-finalizer crash window",\n',
        '        "I1-G",\n        "pre-enqueue background-finalizer",\n',
    )


def cleanup_temporary_files() -> None:
    run("git", "checkout", "origin/main", "--", ".github/workflows/soul-lab-ui.yml")
    for path in ROOT.glob("scripts/phase_i2_*_temp.py"):
        path.unlink(missing_ok=True)
    for path in (ROOT / ".github" / "workflows").glob("phase-i2-*-temp.yml"):
        path.unlink(missing_ok=True)


def run_validation() -> None:
    python = "python"
    env = {"PYTHONPATH": ".:scripts"}
    run(python, "-m", "compileall", "-q", "relaylm", "scripts")
    run(python, "scripts/relaylm_docs_link_check.py", env={"PYTHONPATH": "."})
    run(python, "scripts/relaylm_documentation_current_boundary_smoke.py", env={"PYTHONPATH": "."})
    run(python, "scripts/relaylm_phase_i2_documentation_boundary_smoke.py", env={"PYTHONPATH": "."})
    for script in (
        "scripts/relaylm_phase_i2_lab_observation_ci_runner.py",
        "scripts/relaylm_phase6c1_primary_worker_ci_runner.py",
        "scripts/relaylm_phase6c1_worker_integration_ci_runner.py",
        "scripts/relaylm_phase6c1_durable_protected_source_smoke.py",
        "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py",
        "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py",
    ):
        run(python, script, env=env)

    frontend = ROOT / "apps" / "soul-lab"
    run("npm", "install", "--no-audit", "--no-fund", cwd=frontend)
    run("npm", "run", "typecheck", cwd=frontend)
    smoke_dir = frontend / ".observation-smoke"
    shutil.rmtree(smoke_dir, ignore_errors=True)
    run(
        "npx", "tsc", "src/features/lab/observationApi.ts",
        "--target", "ES2022", "--module", "ES2022",
        "--moduleResolution", "Bundler", "--outDir", ".observation-smoke",
        "--skipLibCheck", cwd=frontend,
    )
    run("node", "scripts/observationApiSmoke.mjs", cwd=frontend)
    shutil.rmtree(smoke_dir, ignore_errors=True)
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
    reconcile_documents()
    cleanup_temporary_files()
    run_validation()
    run("git", "add", "-A")
    staged = subprocess.run(
        ("git", "diff", "--cached", "--quiet"), cwd=ROOT
    ).returncode != 0
    if staged:
        run("git", "commit", "-m", "docs: reconcile Phase I2 with I1-G boundary")
    run("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation")


if __name__ == "__main__":
    main()
