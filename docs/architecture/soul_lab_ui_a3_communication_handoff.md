---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - Communication UI state machine changes
  - peer management API integration begins
  - RelayRUN communication orchestration begins
relaylm_not_authoritative_for:
  - RelayLM Core runtime behavior
  - network transport or endpoint authentication
  - RelayRUN or RelaySLP mutation semantics
  - communication transcript persistence
  - SOUL or MEM formation semantics
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a2_adoption_handoff.md
  - soul_lab_runtime_mvp.md
---
# SOUL Lab UI-A3 Mock Communication Session

## Status

SOUL Lab UI-A3 is implemented as a browser-local communication session surface under `apps/soul-lab/`.

```text
select active character
  -> classify peer boundary
  -> choose scene and maximum turns
  -> start browser-local autonomous mock loop
  -> Soft Stop or maximum-turn close
  -> content-free timeline
  -> stop before network, RelayRUN, or RelaySLP mutation
```

The current slice does not call another RelayLM endpoint, send an OpenAI-compatible request, persist transcript content, or create a real RelayRUN communication session.

## Implemented boundary

UI-A3 provides:

- a dedicated `#/communication` route,
- active-character selection before session start,
- active-character locking while a mock session is running or closing,
- explicit peer classification for:
  - another RelayLM character,
  - external OpenAI-compatible endpoint,
  - built-in Lab Assistant,
- peer readiness and configuration state,
- scene and maximum-turn controls,
- autonomous browser-local mock exchange progression,
- no per-message approval or editing loop,
- Soft Stop as the default close path,
- two-step emergency stop as an explicit exception,
- content-free communication event projection,
- responsive light and dark presentation,
- Japanese-default and English-preview copy.

## Peer boundary

### RelayLM peer

Represents another local RelayLM character or endpoint. The mock UI projects:

- peer type,
- peer identity,
- managed-route endpoint label,
- readiness state,
- SOUL version label.

It does not establish a network connection.

### External API peer

Represents an OpenAI-compatible endpoint. The initial mock peer is intentionally `unconfigured` and cannot start a session.

The browser does not collect or store an API key in UI-A3.

### Lab Assistant

Represents a built-in local RelayLM peer for first-run demonstrations. It remains a normal peer classification, not a privileged system authority.

## Session state machine

```text
idle
  -> active
  -> closing
  -> ended

active or closing
  -> emergency
```

### Active

The browser advances mock exchange events automatically. The user is not asked to approve or edit every message.

### Soft Stop

Soft Stop is the normal stop path:

```text
closing intent recorded
  -> no new topic gate projected
  -> natural closing projected
  -> RelaySLP handoff candidate projected
  -> ended
```

All of these are browser-local projections. No RelayRUN or RelaySLP state changes occur.

### Maximum-turn close

Reaching the configured maximum turn count ends the mock loop and projects an SLP handoff candidate.

### Emergency stop

Emergency stop requires a second explicit confirmation. It bypasses natural closing and projects an aborted-session event for manual review.

It remains a UI-only exception path with no runtime side effect.

## Content-free timeline

The timeline stores only:

- event code,
- safe bounded metadata,
- timestamp,
- severity.

It does not store or render message text. Exchange entries use `message_content=omitted`.

The timeline must not be interpreted as a communication transcript or durable runtime audit record.

## Navigation and character lock

While the session phase is `active` or `closing`:

- active-character switching is disabled,
- sidebar navigation away from Communication is disabled.

This protects the mock session from accidental participant reassignment. Browser history manipulation can still discard the mock component because there is no durable runtime session in this slice.

## Validation

The existing SOUL Lab workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

## Next bounded slice

The next independent UI slice should implement Pod / SOUL Intervention as a read-only-to-candidate mock workflow before any mutation API is introduced.

Recommended sequence:

```text
UI-A4 Pod / SOUL Intervention
  -> intervention intent
  -> protected traits
  -> candidate summary
  -> diff preview
  -> comparison state
  -> hold / discard mock decisions
  -> apply and rollback remain non-mutating previews
```

Real peer transport, credentials, RelayRUN orchestration, transcript handling, and RelaySLP persistence remain separate bounded slices.
