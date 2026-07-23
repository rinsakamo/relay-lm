#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("docs/architecture/relaymem_m3a_primary_formation_handoff.md")
TARGET = Path("docs/evidence/implementation/relaymem-m3a-primary-formation-handoff.md")
LOCAL_RECEIPT = Path("docs/evidence/migrations/cutover-1c57-relaymem-m3a.md")
LEDGER = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
RULES = Path("docs/planning/documentation-cutover-rules.yaml")
EVIDENCE_INDEX = Path("docs/evidence/implementation/README.md")
COMPOSE = Path("docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md")
GUARD = Path("scripts/relaylm_relaymem_m3a_handoff_cutover_guard.py")
BOUNDARY_WORKFLOW = Path(".github/workflows/documentation-current-boundary-smoke.yml")

BASE_MAIN = "1777ca0c0c4d1f64c650f9b3f559a178ad0aed20"
EXPECTED_SOURCE_BLOB = "fbb08beb9975e3a1b46d4a9f510753669297bc26"
HANDOFF_PR = 326
HANDOFF_HEAD = "9a95963c4a0c2a3d2e61e8e174d2e8f70280542f"
HANDOFF_MERGE = "f40d4190c04b116c6d3b2fc206df3534f30545c7"
HANDOFF_MERGED_AT = "2026-06-21T00:37:04Z"
IMPLEMENTATION_PR = 324
IMPLEMENTATION_HEAD = "cd551902c5ae093a90a29a37b1bfaf3a2c0f1eb3"
IMPLEMENTATION_MERGE = "b49727fb00bc5e38a11306dfa853b61e5ffe09d4"
IMPLEMENTATION_MERGED_AT = "2026-06-20T17:15:28Z"


def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    absolute = ROOT / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(content, encoding="utf-8")


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, found {count}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require_once(text, old, label)
    return text.replace(old, new, 1)


def source_body(text: str) -> str:
    if not text.startswith("---\n"):
        raise SystemExit("source front matter missing")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SystemExit("source front matter terminator missing")
    front = text[4:end]
    required = {
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: relaymem_mvp_independent_track",
        "relaylm_status: historical_after_merge",
    }
    missing = sorted(item for item in required if item not in front.splitlines())
    if missing:
        raise SystemExit(f"source metadata mismatch: {missing}")
    return text[end + len("\n---\n"):]


def build_target(body: str, source_sha256: str) -> str:
    return f'''---
relaylm_doc_type: evidence
relaylm_authority: historical_relaymem_m3a_primary_formation_handoff
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_pr: {HANDOFF_PR}
relaylm_source_final_head: {HANDOFF_HEAD}
relaylm_source_merge_commit: {HANDOFF_MERGE}
relaylm_source_merged_at: {HANDOFF_MERGED_AT}
relaylm_implementation_pr: {IMPLEMENTATION_PR}
relaylm_implementation_final_head: {IMPLEMENTATION_HEAD}
relaylm_implementation_merge_commit: {IMPLEMENTATION_MERGE}
relaylm_implementation_merged_at: {IMPLEMENTATION_MERGED_AT}
relaylm_source_blob: {EXPECTED_SOURCE_BLOB}
relaylm_source_sha256: {source_sha256}
relaylm_recorded_on: 2026-06-21
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current RelayMEM Primary formation behavior
  - current Primary pipeline stage composition
  - current RelaySCN RelayEMO or message-shape semantics
  - current repository-wide implementation status or sequencing
  - compatibility aliases redirects stubs dual-read or dual-write
relaylm_related_authority:
  - ../../architecture/relaymem_mvp_implementation_plan.md
  - ../../architecture/memory_lifecycle_design.md
  - ../../architecture/relaymem_mvp_design.md
  - ../../architecture/phase6c1_relaymem_primary_pipeline_compose.md
---
> **Historical implementation evidence.** This record preserves the completed helper-only RelayMEM-M3a boundary from PR #324 and its documentation handoff from PR #326. Current behavior remains implementation-, Primary-pipeline-, RelayMEM-design-, Project-Status-, and focused-smoke-owned.

{body}'''


def build_guard() -> str:
    template = read(Path("scripts/relaylm_phase_i3_handoff_cutover_guard.py"))
    replacements = [
        ('Documentation Hard Cutover 1C-56', 'Documentation Hard Cutover 1C-57'),
        ('docs/architecture/phase_i3_auditable_primary_mem_correct.md', SOURCE.as_posix()),
        ('docs/evidence/implementation/phase-i3-auditable-primary-mem-correct-handoff.md', TARGET.as_posix()),
        ('scripts/relaylm_phase_i3_handoff_cutover_guard.py', GUARD.as_posix()),
        ('docs/evidence/migrations/cutover-1c56-phase-i3.md', LOCAL_RECEIPT.as_posix()),
        ('historical_phase_i3_auditable_primary_mem_correct_handoff', 'historical_relaymem_m3a_primary_formation_handoff'),
        ('Phase I-3 correction', 'RelayMEM M3a formation'),
        ('Phase I-3 cutover guard', 'RelayMEM M3a cutover guard'),
        ('canonical Phase I-3 correction evidence', 'canonical RelayMEM M3a formation evidence'),
    ]
    for old, new in replacements:
        if old not in template:
            raise SystemExit(f"guard template token missing: {old}")
        template = template.replace(old, new)
    template = template.replace('    "docs/evidence/migrations/cutover-1c55-phase-i2.md",\n', '')
    return template


def update_boundary_workflow(text: str) -> str:
    old_path_line = '      - "scripts/relaylm_phase_i3_handoff_cutover_guard.py"\n'
    new_path_line = old_path_line + '      - "scripts/relaylm_relaymem_m3a_handoff_cutover_guard.py"\n'
    if text.count(old_path_line) != 2:
        raise SystemExit("boundary workflow path selector count mismatch")
    text = text.replace(old_path_line, new_path_line)

    compile_line = '            scripts/relaylm_phase_i3_handoff_cutover_guard.py \\\n'
    require_once(text, compile_line, "boundary compile line")
    text = text.replace(
        compile_line,
        compile_line + '            scripts/relaylm_relaymem_m3a_handoff_cutover_guard.py \\\n',
        1,
    )

    run_marker = (
        '          python scripts/relaylm_phase_i3_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n'
        '          phase_i3_cutover_guard_self_test_status=${PIPESTATUS[0]}\n'
    )
    require_once(text, run_marker, "boundary run marker")
    text = text.replace(
        run_marker,
        run_marker
        + '          python scripts/relaylm_relaymem_m3a_handoff_cutover_guard.py 2>&1 | tee -a documentation-current-boundary.log\n'
        + '          relaymem_m3a_cutover_guard_status=${PIPESTATUS[0]}\n'
        + '          python scripts/relaylm_relaymem_m3a_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n'
        + '          relaymem_m3a_cutover_guard_self_test_status=${PIPESTATUS[0]}\n',
        1,
    )

    condition_marker = '|| [ "$phase_i3_cutover_guard_self_test_status" -ne 0 ] ||'
    require_once(text, condition_marker, "boundary status condition")
    text = text.replace(
        condition_marker,
        condition_marker
        + ' [ "$relaymem_m3a_cutover_guard_status" -ne 0 ] ||'
        + ' [ "$relaymem_m3a_cutover_guard_self_test_status" -ne 0 ] ||',
        1,
    )
    return text


def main() -> None:
    source_text = read(SOURCE)
    blob = subprocess.check_output(
        ["git", "hash-object", SOURCE.as_posix()], cwd=ROOT, text=True
    ).strip()
    if blob != EXPECTED_SOURCE_BLOB:
        raise SystemExit(f"source blob mismatch: {blob}")
    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    body = source_body(source_text)

    target = build_target(body, source_sha256)
    write(TARGET, target)
    (ROOT / SOURCE).unlink()

    compose = read(COMPOSE)
    compose = replace_once(
        compose,
        "  - relaymem_m3a_primary_formation_handoff.md\n",
        "  - ../evidence/implementation/relaymem-m3a-primary-formation-handoff.md\n",
        "M3a compose authority link",
    )
    write(COMPOSE, compose)

    evidence_index = read(EVIDENCE_INDEX)
    phase_i3_line = "- [Phase I-3 Auditable Primary MEM Correct handoff](phase-i3-auditable-primary-mem-correct-handoff.md) — frozen correction-loop implementation evidence from PR #379 with later documentation/link maintenance in PR #415 and PR #647; current behavior remains memory-lifecycle-, SOUL-Lab-, implementation-, frontend-, and focused-smoke-owned.\n"
    require_once(evidence_index, phase_i3_line, "implementation evidence insertion point")
    m3a_line = "- [RelayMEM-M3a Primary Formation handoff](relaymem-m3a-primary-formation-handoff.md) — frozen helper-only Primary MEM formation-candidate evidence from implementation PR #324 and handoff PR #326; current behavior remains Primary-pipeline-, RelayMEM-design-, implementation-, and focused-smoke-owned.\n"
    evidence_index = evidence_index.replace(phase_i3_line, phase_i3_line + m3a_line, 1)
    write(EVIDENCE_INDEX, evidence_index)

    rules = read(RULES)
    marker = "  docs/mvp/README.md:\n"
    require_once(rules, marker, "cutover rules insertion point")
    rule_block = f'''  {SOURCE.as_posix()}:
    disposition: evidence_retained
    target_doc_type: evidence
    target_paths:
      - {TARGET.as_posix()}
    deletion_reason: >-
      Cutover 1C-57: this completed helper-only implementation handoff carried
      the legacy implementation_handoff / historical_after_merge profile under
      docs/architecture/. Moved to canonical frozen implementation evidence;
      current M3a behavior remains independently owned by implementation,
      RelayMEM design, the Primary pipeline compose boundary, Project Status,
      and focused smokes. No compatibility alias, redirect, stub, dual-read, or
      dual-write path is retained.
'''
    rules = rules.replace(marker, rule_block + marker, 1)
    write(RULES, rules)

    guard = build_guard()
    write(GUARD, guard)

    boundary = update_boundary_workflow(read(BOUNDARY_WORKFLOW))
    write(BOUNDARY_WORKFLOW, boundary)

    local_receipt = f'''---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c57_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head merge attribution or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current RelayMEM Primary formation runtime behavior
  - current Primary pipeline composition or storage authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-57 Receipt

- Cutover PR: #667
- Bookkeeping consolidation PR: pending after merge
- Base main: `{BASE_MAIN}`
- Validated content head: pending exact-head validation
- Merged commit: pending
- Merged at: pending
- Source: `{SOURCE.as_posix()}`
- Canonical target: `{TARGET.as_posix()}`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source handoff PR / final head / merge / merged at: #{HANDOFF_PR} / `{HANDOFF_HEAD}` / `{HANDOFF_MERGE}` / `{HANDOFF_MERGED_AT}`
- Implementation PR / final head / merge / merged at: #{IMPLEMENTATION_PR} / `{IMPLEMENTATION_HEAD}` / `{IMPLEMENTATION_MERGE}` / `{IMPLEMENTATION_MERGED_AT}`
- Source and pre-cutover blob: `{EXPECTED_SOURCE_BLOB}`
- Source content SHA-256: `{source_sha256}`
- Source recorded on: `2026-06-21`
- Active pre-cutover path-bound referrer files: 1
- Referrer observed: `docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md`
- Active path-bound references repaired: all 1
- Current architecture-index entries removed: none; the source was not listed in the active architecture routers
- Implementation-evidence index updated: yes
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- `docs/PROJECT_STATUS.md` changed: no
- Fail-closed enforcement: `{GUARD.as_posix()}`, compiled and executed by `{BOUNDARY_WORKFLOW.as_posix()}`
- Guard self-test: 23 assertions
- Exact-head GitHub Actions: pending
- Unresolved review threads: pending final review

## Semantic coverage matrix

| # | Historical rule | Independent current owner |
|---:|---|---|
| 1 | helper-only Primary MEM candidate construction | `relaylm/relaymem_primary_formation.py`; focused M3a smoke |
| 2 | M3a-to-M3b artifact handoff | `relaylm/relaymem_primary_pipeline.py`; current Primary pipeline compose handoff |
| 3 | RelaySCN persistence-policy and RelayEMO salience consumption | current implementation and RelayMEM design documents |
| 4 | blocked/held/free-to-update classification | current implementation and focused security/smoke validation |
| 5 | repository-wide completion and sequencing | `docs/PROJECT_STATUS.md`; RelayMEM MVP plan |

## Conclusion

Every current normative behavior recorded by the old M3a handoff is independently owned by current implementation, RelayMEM design, the Primary pipeline compose boundary, Project Status, and focused executable validation. The move therefore removes no unique current authority. The canonical document is frozen historical evidence only.
'''
    write(LOCAL_RECEIPT, local_receipt)

    ledger = read(LEDGER)
    heading = "### C1C57-001 — RelayMEM-M3a Primary Formation handoff (pending merge attribution)"
    if heading in ledger:
        raise SystemExit("central ledger entry already exists")
    ledger_entry = f'''\n\n{heading}

```yaml
cutover_pr: 667
merged_commit: pending
base_main: {BASE_MAIN}
old_path: {SOURCE.as_posix()}
old_blob_sha: {EXPECTED_SOURCE_BLOB}
old_content_sha256: {source_sha256}
source_handoff_pr: {HANDOFF_PR}
source_handoff_final_head: {HANDOFF_HEAD}
source_handoff_merge_commit: {HANDOFF_MERGE}
source_handoff_merged_at: {HANDOFF_MERGED_AT}
implementation_pr: {IMPLEMENTATION_PR}
implementation_final_head: {IMPLEMENTATION_HEAD}
implementation_merge_commit: {IMPLEMENTATION_MERGE}
implementation_merged_at: {IMPLEMENTATION_MERGED_AT}
recorded_on: 2026-06-21
disposition: evidence_retained
new_canonical_path: {TARGET.as_posix()}
local_receipt: {LOCAL_RECEIPT.as_posix()}
verification:
  old_path_removed_in_pr_tree: true
  canonical_evidence_metadata_added: true
  historical_banner_added: true
  current_authority_independently_owned: true
  active_pre_cutover_referrer_files: 1
  active_path_references_repaired: true
  implementation_evidence_index_updated: true
  fail_closed_guard: {GUARD.as_posix()}
  guard_integrated_into_existing_documentation_boundary_workflow: true
  guard_self_test_assertions: 23
  runtime_files_changed: 0
  relaylm_files_changed: 0
  project_status_changed: false
  exact_head_actions: pending
  unresolved_review_threads: pending
```

Pending merge attribution only. The frozen record preserves the helper-only RelayMEM-M3a formation-candidate boundary without becoming current runtime, schema, Primary-pipeline, storage, product, compatibility, alias, redirect, dual-read, or dual-write authority.
'''
    write(LEDGER, ledger.rstrip() + ledger_entry)

    for temporary in (
        Path(".github/cutover-1c57-bootstrap.txt"),
        Path(".github/cutover-1c57-apply.py"),
        Path(".github/workflows/cutover-1c57-apply.yml"),
    ):
        absolute = ROOT / temporary
        if absolute.exists():
            absolute.unlink()


if __name__ == "__main__":
    main()
