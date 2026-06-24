"""Temporary documentation authority update for Phase I-3."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/memory_lifecycle_design.md",
    "docs/architecture/soul_lab_ui_mvp.md",
    "docs/architecture/soul_lab_runtime_mvp.md",
)
MARKER = "<!-- phase-i3-auditable-primary-mem-correct -->"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    (ROOT / path).write_text(body, encoding="utf-8")


def replace_required(body: str, old: str, new: str, *, path: str) -> str:
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one occurrence of {old!r}, found {count}")
    return body.replace(old, new, 1)


status_path = "docs/PROJECT_STATUS.md"
status = read(status_path)
status = replace_required(
    status,
    "  - docs/architecture/phase_i2_real_soul_lab_observation.md\n",
    "  - docs/architecture/phase_i2_real_soul_lab_observation.md\n  - docs/architecture/phase_i3_auditable_primary_mem_correct.md\n",
    path=status_path,
)
status = replace_required(
    status,
    "- Phase I-2 real SOUL Lab latest-run and memory observation integration.\n",
    "- Phase I-2 real SOUL Lab latest-run and memory observation integration,\n- Phase I-3 auditable Primary MEM Correct and later retrieval convergence.\n",
    path=status_path,
)
status = replace_required(
    status,
    "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected\nI1-G pre-enqueue background-finalizer durability: unresolved\nNext product boundary: Phase I-3 auditable Correct operation",
    "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 observation and Phase I-3 token-gated Correct connected\nI1 observe/correct/retrieve product loop: complete\nI1-G pre-enqueue background-finalizer durability: unresolved",
    path=status_path,
)
status = replace_required(
    status,
    "- durable Correct/forget/pin/merge mutation is not implemented.",
    "- auditable formed-Primary-MEM Correct is implemented; forget/pin/unpin/merge remain unimplemented.",
    path=status_path,
)
status = replace_required(
    status,
    "- disabled Correct/forget/pin/merge/apply/discard controls pending I-3.",
    "- token-gated Correct for real formed Primary MEM; forget/pin/merge and held apply/discard remain disabled.",
    path=status_path,
)
status = replace_required(
    status,
    "- no Correct/forget/pin/unpin/merge or held apply/discard operation,",
    "- no forget/pin/unpin/merge or held apply/discard operation,",
    path=status_path,
)
old_priority = '''### Phase I-3: auditable Correct operation

The next bounded product path is one auditable correction whose result changes later retrieval behavior without bypassing existing RelayMEM authority.

Required boundary:

```text
real Lab Observation item
  -> explicit Correct request
  -> exact character/namespace/current-memory validation
  -> bounded mutation preflight
  -> atomic authoritative memory update and audit evidence
  -> later M2 retrieval observes the corrected representation
```

Phase I-3 must not be widened into general memory administration, RelaySOUL mutation, queue scheduling, or daemon lifecycle.
'''
new_priority = '''### Phase I-3: auditable Primary MEM Correct — complete

The bounded product path is implemented:

```text
real formed Primary MEM observation
  -> read-only correction preflight and bounded semantic diff
  -> explicit short-lived-token apply
  -> immutable successor page through M3e
  -> M3f/M3g index/log convergence and bounded recovery
  -> immutable correction receipt
  -> existing M2 and RelayCTX select the corrected current revision
```

The stable logical memory identity remains unchanged, prior pages remain auditable, superseded or prepared-only pages are excluded from ordinary retrieval, and past used-memory evidence is not rewritten.

The next implementation priority must be selected independently from the architecture plan. I1-G still owns the unresolved process-exit window after visible response delivery but before background-finalizer source/queue publication.
'''
status = replace_required(status, old_priority, new_priority, path=status_path)
status = replace_required(
    status,
    "- auditable Correct operation: next as Phase I-3",
    "- I3 auditable Primary MEM Correct: complete\n- I1 observe/correct/retrieve product loop: complete",
    path=status_path,
)
status = replace_required(
    status,
    "- all SOUL Lab management and observation routes remain local-only read surfaces.",
    "- SOUL Lab management and observation reads remain local-only; Correct additionally requires exact JSON, exact schema, expected revision, and a preflight-issued token.",
    path=status_path,
)
status = replace_required(
    status,
    "- durable correction/forget/pin/merge or held apply/discard operations,",
    "- durable forget/pin/merge or held apply/discard operations,",
    path=status_path,
)
status = replace_required(
    status,
    "The memory write path remains explicitly gated. C1-5 and C2 provide restart-safe protected-source recovery and one exact queued-job execution; Phase I-1 provides ordinary scoped recall; Phase I-2 provides bounded read-only observation. Queue scheduling and the pre-enqueue background-finalizer crash window remain separate unresolved operational boundaries.",
    "The memory write path remains explicitly gated. C1-5 and C2 provide restart-safe protected-source recovery and one exact queued-job execution; Phase I-1 provides ordinary scoped recall; Phase I-2 provides bounded read-only observation; Phase I-3 provides token-gated audited Correct with later M2 convergence. Queue scheduling and the pre-enqueue background-finalizer crash window remain separate unresolved operational boundaries.",
    path=status_path,
)
status = replace_required(
    status,
    "- auditable Correct operation: next as Phase I-3",
    "- I3 auditable Primary MEM Correct: complete\n- I1 observe/correct/retrieve product loop: complete",
    path=status_path,
)
write(status_path, status)

shared = '''

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.
'''

for path in REQUIRED_DOCS:
    body = read(path)
    if MARKER not in body:
        body = body.rstrip() + shared + "\n"
    body = body.replace(
        "auditable Correct operation: next as Phase I-3",
        "I3 auditable Primary MEM Correct: complete",
    )
    body = body.replace(
        "auditable Correct operation: next",
        "I3 auditable Primary MEM Correct: complete",
    )
    write(path, body)

for path in (
    "docs/architecture/phase_i2_real_soul_lab_observation.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
):
    body = read(path)
    if MARKER not in body:
        body = body.rstrip() + shared + "\n"
    write(path, body)

# Add the new handoff to the two document indexes without depending on section order.
for path, anchor, insertion in (
    (
        "docs/README.md",
        "- [Phase I-2 Real SOUL Lab Observation](architecture/phase_i2_real_soul_lab_observation.md)",
        "- [Phase I-2 Real SOUL Lab Observation](architecture/phase_i2_real_soul_lab_observation.md)\n- [Phase I-3 Auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)",
    ),
    (
        "docs/architecture/README.md",
        "- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)",
        "- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)\n- [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md)",
    ),
):
    body = read(path)
    if "phase_i3_auditable_primary_mem_correct.md)" not in body:
        body = replace_required(body, anchor, insertion, path=path)
    write(path, body)

current_smoke = read("scripts/relaylm_documentation_current_boundary_smoke.py")
current_smoke = current_smoke.replace(
    '"""Validate current Phase 6, I1, I2, I1-G, and config documentation."""',
    '"""Validate current Phase 6, I1-I3, I1-G, and config documentation."""',
)
current_smoke = replace_required(
    current_smoke,
    '        "auditable Correct operation: next as Phase I-3")',
    '        "I3 auditable Primary MEM Correct: complete",\n        "I1 observe/correct/retrieve product loop: complete")',
    path="scripts/relaylm_documentation_current_boundary_smoke.py",
)
current_smoke = replace_required(
    current_smoke,
    '        "Phase I-2 completes real read-only Lab observation",\n        "I1-G pre-enqueue background-finalizer durability")',
    '        "Phase I-2 completes real read-only Lab observation",\n        "Phase I-3 auditable Primary MEM Correct",\n        "I1-G pre-enqueue background-finalizer durability")',
    path="scripts/relaylm_documentation_current_boundary_smoke.py",
)
current_smoke = replace_required(
    current_smoke,
    '        "phase_i2_real_soul_lab_observation.md", "I1-G")',
    '        "phase_i2_real_soul_lab_observation.md",\n        "phase_i3_auditable_primary_mem_correct.md", "I1-G")',
    path="scripts/relaylm_documentation_current_boundary_smoke.py",
)
current_smoke = replace_required(
    current_smoke,
    '    forbid("docs/PROJECT_STATUS.md", "SOUL Lab real observation: next")',
    '    forbid("docs/PROJECT_STATUS.md",\n        "SOUL Lab real observation: next",\n        "auditable Correct operation: next")',
    path="scripts/relaylm_documentation_current_boundary_smoke.py",
)
write("scripts/relaylm_documentation_current_boundary_smoke.py", current_smoke)

i2_smoke = read("scripts/relaylm_phase_i2_documentation_boundary_smoke.py")
i2_smoke = replace_required(
    i2_smoke,
    '        "auditable Correct operation: next",',
    '        "I3 auditable Primary MEM Correct: complete",',
    path="scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
)
i2_smoke = replace_required(
    i2_smoke,
    '    require_text("docs/README.md", handoff)\n    require_text("docs/architecture/README.md", handoff)',
    '    require_text("docs/README.md", handoff, "phase_i3_auditable_primary_mem_correct.md")\n    require_text("docs/architecture/README.md", handoff, "phase_i3_auditable_primary_mem_correct.md")',
    path="scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
)
write("scripts/relaylm_phase_i2_documentation_boundary_smoke.py", i2_smoke)

print("Phase I-3 documentation authority patch applied")
