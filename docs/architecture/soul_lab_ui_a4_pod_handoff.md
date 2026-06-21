---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - Pod intervention UI state machine changes
  - RelaySOUL candidate generation API integration begins
  - managed apply or rollback integration begins
relaylm_not_authoritative_for:
  - RelaySOUL mutation semantics
  - SOUL source parsing or durable history
  - managed apply authorization
  - rollback execution or recovery ownership
  - RelayLM Core runtime behavior
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a3_communication_handoff.md
  - memory_lifecycle_design.md
---
# SOUL Lab UI-A4 Pod / SOUL Intervention

## Status

SOUL Lab UI-A4 is implemented as a browser-local intentional-intervention workflow under `apps/soul-lab/`.

```text
select bounded intervention target
  -> enter intervention intent
  -> lock protected traits
  -> generate browser-local candidate projection
  -> inspect human-readable diff
  -> run one browser-local comparison
  -> hold or discard
  -> stop before managed apply or rollback
```

The current slice does not edit `SOUL.md`, create a durable RelaySOUL candidate, write history, apply a candidate, or execute rollback.

## Implemented boundary

UI-A4 provides:

- a dedicated `#/pod` route,
- a darker and more ritualized visual surface than Home and Lab Observation,
- active-character selection before candidate generation,
- character and sidebar navigation locking while a candidate is undecided,
- three bounded intervention targets:
  - response style,
  - bounded initiative,
  - recovery relationship tone,
- free-text intervention intent kept in browser memory,
- four locked protected-trait groups,
- browser-local candidate identifiers,
- human-readable candidate summary,
- projected SOUL diff without full source rendering,
- one bounded browser-local comparison,
- current rollback-point display,
- CTX Repack / Unpack projection,
- Hold and Discard final decisions,
- Apply and Rollback non-executing previews,
- content-free intervention timeline,
- Japanese-default and English-preview copy,
- responsive Pod presentation.

## Intervention targets

UI-A4 intentionally avoids arbitrary SOUL editing and personality sliders.

The mock target categories are narrow product projections:

```text
response_style
  reduce repeated confirmation while preserving material uncertainty

initiative
  offer one bounded next action only when context is clear

recovery_tone
  restore relationship continuity before technical recovery detail
```

These categories are UI examples, not authoritative RelaySOUL schema fields.

## Protected traits

The following groups are always projected as locked:

- identity continuity,
- approved relationship anchors,
- safety and non-deception boundaries,
- MEM formation, forgetting, and SOUL-promotion authority.

The browser cannot unlock or modify these groups in UI-A4.

A future server contract must independently validate protected-trait preservation. The UI lock is not an authorization or safety guarantee.

## Candidate boundary

Candidate generation produces only browser-local presentation state:

- candidate ID,
- bounded target category,
- generic summary,
- one before/after diff projection,
- protected-trait count,
- content-free event metadata.

The intervention intent is not copied into the event timeline. Timeline metadata uses `intent_content=omitted`.

The candidate is not:

- a RelaySOUL patch,
- a valid `SOUL.md` replacement,
- a durable history entry,
- an approved managed-apply request,
- a rollback checkpoint.

## Comparison boundary

The comparison is a fixed browser-local projection. It does not call a backend, generate sample responses, run a benchmark, or execute regression tests.

It shows only bounded qualitative fields:

- continuity,
- directness,
- boundedness,
- relationship tone.

The comparison result must not be interpreted as evidence that the candidate is safe or behaviorally superior.

## Decision state machine

```text
intent
  -> candidate
  -> compared
  -> held | discarded
```

### Hold

Hold ends the active browser lock and displays a local held state. It does not persist the candidate. Reloading the page loses it.

### Discard

Discard ends the active browser lock and confirms that SOUL, history, and rollback points remain unchanged.

### Apply preview

Apply preview explains the future managed boundary:

```text
server-side candidate validation
  -> protected-trait validation
  -> comparison evidence
  -> explicit confirmation
  -> managed apply
```

No step executes in UI-A4.

### Rollback preview

Rollback preview displays the previous approved checkpoint label and explains future server-side history validation. No restore candidate or rollback action is created.

## Content-free timeline

The timeline contains only:

- event code,
- candidate ID,
- target category,
- bounded boolean/count metadata,
- timestamp,
- severity.

It does not contain intervention text, SOUL source content, generated comparison text, or user-visible conversation content.

## Navigation and character lock

After candidate generation and before Hold or Discard:

- active-character switching is disabled,
- navigation away from Pod through the visible sidebar is disabled.

Browser history manipulation or reload can still discard the mock state because there is no durable intervention session in UI-A4.

## Validation

The existing SOUL Lab workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

## Next bounded slice

The next independent UI slice should deepen Lab Observation into a mock Memory Inspector without turning normal autonomous MEM formation into an approval queue.

Recommended sequence:

```text
UI-A5 Memory Inspector
  -> select formed / held / blocked memory outcome
  -> inspect source and provenance projection
  -> preview correct / forget / pin / unpin / merge operations
  -> require explicit confirmation for destructive previews
  -> keep all operations browser-local and non-persistent
```

Real RelaySOUL candidate generation, managed apply, rollback, durable history, memory mutation, and `/lab/api/*` integration remain separate bounded slices.
