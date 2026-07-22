#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import posixpath
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "docs/architecture/phase_i2_real_soul_lab_observation.md"
NEW = "docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md"
OLD_BASENAME = Path(OLD).name
NEW_BASENAME = Path(NEW).name
EXPECTED_SOURCE_BLOB = "496c29ad94558a4bb0e12921cf20ad5358ae1120"
BASE_MAIN = "f775581b8393522635b88f2d3178ef355330bc62"
SELF = "scripts/_cutover_1c55_builder.py"
WORKFLOW = ".github/workflows/documentation-current-boundary-smoke.yml"
GUARD = "scripts/relaylm_phase_i2_handoff_cutover_guard.py"
LOCAL_RECEIPT = "docs/evidence/migrations/cutover-1c55-phase-i2.md"
CENTRAL_LEDGER = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
RULES = "docs/planning/documentation-cutover-rules.yaml"

EXPECTED_REFERRERS = {
    "docs/README.md",
    "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
    "docs/architecture/soul_lab_runtime_mvp.md",
    "docs/architecture/soul_lab_ui_mvp.md",
    "scripts/relaylm_e1_evaluation_consolidation_smoke.py",
    "docs/architecture/README.md",
    "docs/architecture/soul_lab_ui_b0_real_home_conversation.md",
    "docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md",
    "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
    "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md",
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
    "docs/architecture/phase_i3_auditable_primary_mem_correct.md",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def relative_target(from_file: str, target: str) -> str:
    return posixpath.relpath(target, start=str(Path(from_file).parent).replace("\\", "/"))


def repair_reference_file(relative: str) -> None:
    text = read(relative)
    before = text
    old_relative = relative_target(relative, OLD)
    new_relative = relative_target(relative, NEW)
    for old, new in (
        (OLD, NEW),
        (OLD.removeprefix("docs/"), NEW.removeprefix("docs/")),
        (old_relative, new_relative),
        (OLD_BASENAME, new_relative),
    ):
        text = text.replace(old, new)
    if text == before:
        fail(f"{relative}: expected a Phase I-2 path repair")
    if OLD_BASENAME in text:
        fail(f"{relative}: retired basename remains after repair")
    write(relative, text)


def rewrite_phase_i2_boundary_smoke() -> None:
    write(
        "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
        '''"""Documentation boundary smoke for Phase I-2 after evidence cutover."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_text(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required boundary: {needle}")


def forbid_text(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        if needle in text:
            raise AssertionError(f"{path}: stale boundary remains: {needle}")


def main() -> None:
    evidence = "docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md"
    require_text(
        "docs/PROJECT_STATUS.md",
        "SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3",
        "I1-G overall: complete",
        "I1-GE full production crash validation: complete",
    )
    require_text(
        "docs/architecture/project_execution_plan.md",
        "read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence",
        "MVP completion criteria",
    )
    require_text(
        "docs/architecture/relaymem_slp_current_target.md",
        "I2 real SOUL Lab observation is complete",
        "cannot authorize repair or retrieval",
    )
    require_text(
        "docs/architecture/soul_lab_ui_mvp.md",
        "Phase I-2 provides real latest-run, formed/held/blocked, and used-memory evidence",
        "Real and preview data are never combined automatically",
        "AbortSignal",
    )
    require_text(
        "docs/architecture/soul_lab_runtime_mvp.md",
        "Phase I-2 does not implement the Runtime MVP adapter layer",
        "Observation receipt failure",
    )
    require_text(
        "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
        "UI-A7 settings or characters responses",
        "content-free schemas",
    )
    require_text(
        "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
        "Phase I-2 observes this path",
        "observation receipt",
    )
    require_text(
        evidence,
        "relaylm_doc_type: evidence",
        "relaylm_status: frozen",
        "**Historical implementation evidence.**",
        "Lab observation receipts are secondary read-only evidence only",
        "GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...",
    )
    require_text(
        "docs/evidence/implementation/README.md",
        "phase-i2-real-soul-lab-observation-handoff.md",
    )
    require_text("docs/README.md", "phase_i3_auditable_primary_mem_correct.md")
    require_text("docs/architecture/README.md", "phase_i3_auditable_primary_mem_correct.md")
    forbid_text("docs/README.md", "Phase I-2 real SOUL Lab observation")
    forbid_text("docs/architecture/README.md", "Phase I-2 Real SOUL Lab Observation")

    for path in (
        "docs/PROJECT_STATUS.md",
        "docs/README.md",
        "docs/architecture/README.md",
        "docs/architecture/project_execution_plan.md",
        "docs/architecture/pipeline_implementation_plan.md",
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "docs/architecture/relaymem_slp_current_target.md",
    ):
        forbid_text(
            path,
            "SOUL Lab real observation is next",
            "latest-run and memory-outcome reads: pending",
            "real SOUL Lab observation of formed and used memory",
        )

    print("Phase I-2 documentation boundary smoke passed")


if __name__ == "__main__":
    main()
''',
    )


def make_guard() -> str:
    template = read("scripts/relaylm_i4c2_handoff_cutover_guard.py")
    template = template.replace(
        '"""Fail-closed guard for Documentation Hard Cutover 1C-54."""',
        '"""Fail-closed guard for Documentation Hard Cutover 1C-55."""',
    )
    template = template.replace(
        'RETIRED = "docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md"',
        f'RETIRED = "{OLD}"',
    )
    template = template.replace(
        'CANONICAL = "docs/evidence/implementation/i4c2-primary-forget-recovery-finalization-handoff.md"',
        f'CANONICAL = "{NEW}"',
    )
    template = template.replace(
        'SELF_PATH = "scripts/relaylm_i4c2_handoff_cutover_guard.py"',
        f'SELF_PATH = "{GUARD}"',
    )
    template = template.replace(
        '    "docs/evidence/migrations/cutover-1c54-i4c2.md",',
        f'    "{LOCAL_RECEIPT}",',
    )
    template = "\n".join(
        line
        for line in template.splitlines()
        if "wave2_cross_slice_convergence_audit-source.txt" not in line
        and "cutover-1c53-i4c1.md" not in line
        and "Wave 2 source snapshot" not in line
        and "Cutover 1C-53 receipt" not in line
    ) + "\n"
    template = template.replace(
        "historical_phase_i4c2_primary_forget_recovery_finalization_handoff",
        "historical_phase_i2_real_soul_lab_observation_handoff",
    )
    template = template.replace(
        "canonical I-4C2 recovery/finalization evidence is missing",
        "canonical Phase I-2 observation evidence is missing",
    )
    template = template.replace("I-4C2", "Phase I-2")
    return template


def integrate_guard_into_workflow() -> None:
    restored = subprocess.run(
        ["git", "show", f"origin/main:{WORKFLOW}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    path_anchor = '      - "scripts/relaylm_i4c2_handoff_cutover_guard.py"\n'
    if restored.count(path_anchor) != 2:
        fail(f"workflow path anchor count mismatch: {restored.count(path_anchor)}")
    restored = restored.replace(path_anchor, path_anchor + f'      - "{GUARD}"\n')
    compile_anchor = "            scripts/relaylm_i4c2_handoff_cutover_guard.py \\\n"
    if restored.count(compile_anchor) != 1:
        fail(f"workflow compile anchor count mismatch: {restored.count(compile_anchor)}")
    restored = restored.replace(compile_anchor, compile_anchor + f"            {GUARD} \\\n", 1)
    run_anchor = """          python scripts/relaylm_i4c2_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log
          i4c2_cutover_guard_self_test_status=${PIPESTATUS[0]}
"""
    if restored.count(run_anchor) != 1:
        fail(f"workflow run anchor count mismatch: {restored.count(run_anchor)}")
    restored = restored.replace(
        run_anchor,
        run_anchor
        + f"""          python {GUARD} 2>&1 | tee -a documentation-current-boundary.log
          phase_i2_cutover_guard_status=${{PIPESTATUS[0]}}
          python {GUARD} --self-test 2>&1 | tee -a documentation-current-boundary.log
          phase_i2_cutover_guard_self_test_status=${{PIPESTATUS[0]}}
""",
        1,
    )
    condition_anchor = '|| [ "$i4c2_cutover_guard_self_test_status" -ne 0 ]'
    if restored.count(condition_anchor) != 1:
        fail(f"workflow condition anchor count mismatch: {restored.count(condition_anchor)}")
    restored = restored.replace(
        condition_anchor,
        condition_anchor
        + ' || [ "$phase_i2_cutover_guard_status" -ne 0 ]'
        + ' || [ "$phase_i2_cutover_guard_self_test_status" -ne 0 ]',
        1,
    )
    write(WORKFLOW, restored)


def main() -> None:
    cutover_pr = os.environ.get("CUTOVER_PR", "").strip()
    if not cutover_pr.isdigit():
        fail(f"CUTOVER_PR must be numeric, got {cutover_pr!r}")

    source_path = ROOT / OLD
    if not source_path.is_file() or (ROOT / NEW).exists():
        fail("source/target precondition failed")
    actual_blob = git("rev-parse", f"HEAD:{OLD}")
    if actual_blob != EXPECTED_SOURCE_BLOB:
        fail(f"{OLD}: expected blob {EXPECTED_SOURCE_BLOB}, got {actual_blob}")
    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    source_text = source_bytes.decode("utf-8")

    for relative in EXPECTED_REFERRERS:
        if OLD_BASENAME not in read(relative):
            fail(f"{relative}: expected Phase I-2 referrer token is missing")

    front_end = source_text.find("\n---\n", 4)
    if not source_text.startswith("---\n") or front_end < 0:
        fail(f"{OLD}: invalid front matter")
    body = source_text[front_end + 5 :]
    body = body.replace(
        "[Project Status](../PROJECT_STATUS.md)",
        "[Project Status](../../PROJECT_STATUS.md)",
    )
    title = "# Phase I-2 Real SOUL Lab Observation\n"
    if body.count(title) != 1:
        fail("source title anchor mismatch")
    historical = f'''{title}
> **Historical implementation evidence.** This frozen handoff records the bounded observe-only SOUL Lab integration delivered by PR #377. It is not current runtime, schema, API/UI, storage, product, compatibility, alias, redirect, dual-read, or dual-write authority.

## Current authority boundary

Current behavior is independently owned by:

- `docs/architecture/soul_lab_ui_mvp.md`, `soul_lab_runtime_mvp.md`, `soul_lab_ui_b0_real_home_conversation.md`, and `soul_lab_ui_b1a_lifecycle_visibility.md` for current SOUL Lab observation, Home, and lifecycle-visibility boundaries;
- `relaylm/soul_lab_observation.py` and `relaylm/soul_lab_app.py` for executable observation capture, projection, route, loopback, isolation, and response-finalization behavior;
- `apps/soul-lab/src/features/lab/observationApi.ts` and the current SOUL Lab frontend for exact browser validation and stale-response rejection;
- `scripts/relaylm_phase_i2_lab_observation_ci_runner.py` and `scripts/relaylm_phase_i2_documentation_boundary_smoke.py` for focused executable and documentation validation;
- `docs/PROJECT_STATUS.md` for repository-wide current implementation status.

'''
    body = body.replace(title, historical, 1)
    front = f'''---
relaylm_doc_type: evidence
relaylm_authority: historical_phase_i2_real_soul_lab_observation_handoff
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_pr: 377
relaylm_source_final_head: a891dc67a47afeaf074443c69682adb7a5aa9fbc
relaylm_source_merge_commit: 4a24bdc9e6614433675eaa54f97b40647010c007
relaylm_source_merged_at: 2026-06-24T12:34:06Z
relaylm_source_blob: {actual_blob}
relaylm_source_sha256: {source_sha256}
relaylm_recorded_on: 2026-06-24
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current SOUL Lab runtime behavior
  - current public schema or storage authority
  - current API or UI behavior
  - current product status
  - compatibility aliases redirects stubs dual-read or dual-write
relaylm_related_authority:
  - ../../architecture/integration_i1_primary_mem_two_turn_recall.md
  - ../../architecture/phase_i3_auditable_primary_mem_correct.md
  - ../../architecture/phase_i4d_primary_retrieval_exclusion.md
  - ../../architecture/soul_lab_ui_mvp.md
  - ../../architecture/soul_lab_runtime_mvp.md
  - ../../architecture/soul_lab_ui_b0_real_home_conversation.md
  - ../../architecture/soul_lab_ui_b1a_lifecycle_visibility.md
---
'''
    write(NEW, front + body)
    source_path.unlink()

    for relative, expected_count in (("docs/README.md", 1), ("docs/architecture/README.md", 2)):
        lines = read(relative).splitlines(keepends=True)
        removed = [line for line in lines if OLD_BASENAME in line]
        if len(removed) != expected_count:
            fail(f"{relative}: expected {expected_count} index lines, found {len(removed)}")
        write(relative, "".join(line for line in lines if OLD_BASENAME not in line))

    rewrite_phase_i2_boundary_smoke()
    for relative in sorted(
        EXPECTED_REFERRERS
        - {
            "docs/README.md",
            "docs/architecture/README.md",
            "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
        }
    ):
        repair_reference_file(relative)

    evidence_index = read("docs/evidence/implementation/README.md")
    anchor = "- [I-4C1 Primary Forget hidden-successor handoff](i4c1-primary-forget-hidden-successor-handoff.md)"
    bullet = "- [Phase I-2 Real SOUL Lab Observation handoff](phase-i2-real-soul-lab-observation-handoff.md) — frozen observe-only implementation evidence from PR #377; current behavior remains SOUL Lab architecture-, implementation-, and focused-smoke-owned.\n"
    if evidence_index.count(anchor) != 1 or NEW_BASENAME in evidence_index:
        fail("implementation evidence index anchor or duplicate mismatch")
    write("docs/evidence/implementation/README.md", evidence_index.replace(anchor, bullet + anchor, 1))

    rules = read(RULES)
    rules_anchor = "  docs/architecture/phase_i4c1_primary_forget_hidden_successor.md:\n"
    override = f'''  {OLD}:
    disposition: evidence_retained
    target_doc_type: evidence
    target_paths:
      - {NEW}
    deletion_reason: >-
      Cutover 1C-55: this completed Phase I-2 observe-only SOUL Lab integration
      handoff was frozen historical implementation evidence mislocated in the live
      architecture collection. The cutover preserves PR #377 provenance, removes
      the handoff from current/product-critical indexes, repairs every active
      path-bound reference, and leaves current SOUL Lab observation authority with
      current UI/runtime architecture, implementation, and focused smokes.

'''
    if rules.count(rules_anchor) != 1 or f"  {OLD}:\n" in rules:
        fail("cutover rules anchor or duplicate mismatch")
    write(RULES, rules.replace(rules_anchor, override + rules_anchor, 1))

    referrers = ", ".join(f"`{path}`" for path in sorted(EXPECTED_REFERRERS))
    receipt = f'''---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c55_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head merge attribution or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current SOUL Lab runtime behavior
  - current public schema or storage authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-55 Receipt

- Cutover PR: #{cutover_pr}
- Bookkeeping consolidation PR: pending after merge
- Base main: `{BASE_MAIN}`
- Validated content head: pending exact-head validation
- Merged commit: pending
- Merged at: pending
- Source: `{OLD}`
- Canonical target: `{NEW}`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source implementation PR: #377
- Source final head / merge / merged at: `a891dc67a47afeaf074443c69682adb7a5aa9fbc` / `4a24bdc9e6614433675eaa54f97b40647010c007` / `2026-06-24T12:34:06Z`
- Source and pre-cutover blob: `{actual_blob}`
- Source content SHA-256: `{source_sha256}`
- Source recorded on: `2026-06-24`
- Pre-cutover path-bound referrer files: {len(EXPECTED_REFERRERS)}
- Referrers observed: {referrers}
- Active path-bound references repaired: all {len(EXPECTED_REFERRERS)}
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Project-status preservation: `docs/PROJECT_STATUS.md` is unchanged; PR #645 remains separately owned.
- Parallel implementation: PR #646 overlaps only `docs/architecture/README.md`; no SM-1 content is imported.
- Fail-closed enforcement: `{GUARD}`, compiled and executed by `{WORKFLOW}`
- Guard self-test: 22 assertions
- Exact-head GitHub Actions: pending
- Unresolved review threads: pending final review

## Semantic coverage matrix

| # | Historical rule | Independent current owner |
|---:|---|---|
| 1 | loopback-only character/namespace-scoped observation routes | `relaylm/soul_lab_app.py`; current SOUL Lab architecture |
| 2 | exact versioned public observation schemas | `relaylm/soul_lab_observation.py`; browser schema validator |
| 3 | completed-run-only response-finalization observation | observation middleware and focused Phase I-2 smoke |
| 4 | validated recent Primary-memory projection | current Primary store implementation and SOUL Lab projection |
| 5 | held/blocked secondary outcome receipts | current observation implementation; worker result remains authoritative |
| 6 | used-memory evidence at RelayCTX injection boundary | current observation wrapper and RelayCTX implementation |
| 7 | bounded durable observation store safety | current observation store implementation and security smokes |
| 8 | read-only UI states and stale-response rejection | current SOUL Lab frontend and UI architecture |
| 9 | no repair, retrieval, mutation, scheduling, or adapter authority | current subsystem contracts and implementations |
| 10 | repository-wide completion/status | `docs/PROJECT_STATUS.md` |

## Conclusion

Every current normative behavior recorded by the old Phase I-2 handoff is independently owned by current SOUL Lab architecture, implementation, frontend validation, Project Status, and focused executable validation. The move therefore removes no unique current authority. The canonical document is frozen historical evidence only.
'''
    write(LOCAL_RECEIPT, receipt)

    ledger = read(CENTRAL_LEDGER)
    if "### C1C55-001" in ledger:
        fail("central ledger already contains C1C55-001")
    ledger_entry = f'''
### C1C55-001 — Phase I-2 Real SOUL Lab Observation handoff (pending merge attribution)

```yaml
cutover_pr: {cutover_pr}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {actual_blob}
old_content_sha256: {source_sha256}
source_pr: 377
source_final_head: a891dc67a47afeaf074443c69682adb7a5aa9fbc
source_merge_commit: 4a24bdc9e6614433675eaa54f97b40647010c007
source_merged_at: 2026-06-24T12:34:06Z
recorded_on: 2026-06-24
disposition: evidence_retained
new_canonical_path: {NEW}
verification:
  old_path_removed_in_pr_tree: true
  canonical_evidence_metadata_added: true
  historical_banner_added: true
  current_authority_independently_owned: true
  pre_cutover_referrer_files: {len(EXPECTED_REFERRERS)}
  active_path_references_repaired: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  runtime_files_changed: 0
  relaylm_files_changed: 0
  exact_head_actions: pending
  unresolved_review_threads: pending
```

Pending merge attribution only. The frozen record preserves PR #377 Phase I-2 provenance without becoming current runtime, schema, API/UI, storage, product, compatibility, alias, redirect, dual-read, or dual-write authority.
'''
    write(CENTRAL_LEDGER, ledger.rstrip() + "\n" + ledger_entry)

    write(GUARD, make_guard())
    integrate_guard_into_workflow()
    (ROOT / SELF).unlink()


if __name__ == "__main__":
    main()
