---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - Memory Inspector UI state machine changes
  - RelayMEM inspection API integration begins
  - memory correction, forgetting, pinning, or merge integration begins
relaylm_not_authoritative_for:
  - RelayMEM durable mutation semantics
  - autonomous memory-formation gates
  - RelaySLP execution or persistence
  - memory correction or forgetting authorization
  - SOUL promotion semantics
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - memory_lifecycle_design.md
  - relaymem_mvp_implementation_plan.md
  - soul_lab_ui_a4_pod_handoff.md
---
# SOUL Lab UI-A5 Memory Inspector

## Status

SOUL Lab UI-A5 is implemented as a browser-local Memory Inspector under `apps/soul-lab/`.

```text
select character
  -> inspect formed / held / blocked outcome
  -> read bounded provenance projection
  -> open operation candidate preview
  -> explicitly confirm or cancel preview
  -> stop before RelayMEM mutation
```

The current slice does not write to RelayMEM, invoke RelaySLP, update SOUL, or persist an operation decision.

## Product boundary

Lab Observation is not a mandatory approval queue for ordinary memory formation.

```text
ordinary experience
  -> RelaySLP gates
  -> formed / held / blocked outcome
  -> Memory Inspector observes afterward
```

A `formed` outcome is presented as an already autonomous result. The user does not approve each ordinary memory before formation.

`held` and `blocked` outcomes remain exception evidence rather than a queue that must be cleared before normal conversation continues.

## Implemented boundary

UI-A5 provides:

- a dedicated `#/observation` Memory Inspector route,
- active-character selection before opening an operation preview,
- character-scoped mock memory records,
- formed, held, and blocked filters,
- memory source and source-session projection,
- confidence, layer, scope, pin, and latest-use fields,
- bounded source / gate / store provenance steps,
- optional related-perspective projection for RelayLM peer communication,
- held and blocked reasons,
- read-only blocked outcomes,
- browser-local Correct preview,
- browser-local Forget preview with explicit destructive confirmation,
- browser-local Pin / Unpin preview for formed memory,
- browser-local Merge preview for formed or held memory,
- content-free operation timeline,
- character and visible navigation lock while an operation preview is open,
- Japanese-default and English-preview copy,
- responsive light and dark presentation.

## Outcome classes

### Formed

A formed record projects an autonomous Primary MEM result.

Available previews:

- Correct,
- Forget,
- Pin or Unpin,
- Merge.

### Held

A held record represents an uncertain candidate that was not promoted.

Available previews:

- Correct,
- Forget,
- Merge.

Pin and Unpin are unavailable because the record is not projected as formed memory.

### Blocked

A blocked record is boundary evidence only.

No operation preview can be created from a blocked record in UI-A5.

## Provenance projection

The Inspector shows a bounded human-readable chain:

```text
Experience source
  -> formation or boundary gate
  -> store outcome
```

It does not expose:

- raw traces,
- raw prompts,
- backend credentials,
- full conversation transcripts,
- internal RelaySLP work payloads,
- other-character raw MEM.

For peer communication, a related perspective may be displayed as a human-readable comparison. This does not imply shared memory or a shared transcript.

## Operation state machine

```text
idle
  -> operation preview open
  -> confirmed preview | cancelled preview
  -> idle
```

The operation preview locks visible character switching and sidebar navigation to avoid relabeling a draft as another character's memory operation.

Browser history manipulation or page reload can still discard the mock state because there is no durable operation session.

## Correct preview

Correct requires a replacement summary that:

- contains at least 12 characters,
- differs from the current summary.

The correction content remains in browser state and is omitted from the content-free timeline.

Confirmation creates only a local result marker:

```text
NOT PERSISTED
mutation=false
```

## Forget preview

Forget is treated as destructive even though UI-A5 does not execute it.

The user must:

1. open Forget preview,
2. read the destructive-operation warning,
3. press an explicit confirmation button.

The confirmed event records `destructive=true` and `persisted=false` without changing the source memory.

A future implementation must perform server-side ownership, dependency, retention, and recovery checks before any real forgetting action.

## Pin / Unpin preview

Pin and Unpin are available only for formed records.

The preview describes the intended retention change but does not change the displayed `pinned` value or a durable store record.

## Merge preview

Merge requires another formed or held record from the same active character.

The timeline records only source and target memory identifiers. It does not include either memory summary.

A future merge API must validate:

- character ownership,
- scope compatibility,
- provenance retention,
- source-memory disposition,
- idempotency and recovery behavior.

## Content-free timeline

The timeline contains only:

- event code,
- memory identifier,
- operation type,
- merge target identifier when relevant,
- destructive boolean,
- persisted boolean,
- timestamp and severity.

It does not contain:

- memory summary text,
- correction text,
- merge result text,
- conversation content.

## Validation

The existing SOUL Lab workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

## Next bounded slice

The next independent UI slice should consolidate the shared application shell and add a mock Settings / Runtime Boundary surface before real `/lab/api/*` integration.

Recommended sequence:

```text
UI-A6 Shared Shell / Settings
  -> single route and language owner
  -> character registry projection
  -> runtime endpoint status
  -> external peer configuration preview
  -> credential fields remain server-owned
  -> no network test or configuration persistence
```

Real RelayMEM inspection, correction, forgetting, pinning, merge, RelaySLP persistence, and `/lab/api/*` integration remain separate bounded slices.
