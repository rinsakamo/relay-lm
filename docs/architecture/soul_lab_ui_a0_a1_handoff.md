---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - SOUL Lab frontend foundation changes
  - Home or Lab Observation mock boundary changes
  - SOUL Lab Runtime API integration begins
relaylm_not_authoritative_for:
  - RelayLM Core runtime behavior
  - SOUL or MEM mutation semantics
  - SOUL Lab Runtime TTS, audio, or avatar execution
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - memory_lifecycle_design.md
---
# SOUL Lab UI-A0 / UI-A1 Foundation and Mock Home

## Status

SOUL Lab UI-A0 and UI-A1 are implemented as an independent, mock-driven browser frontend under `apps/soul-lab/`.

```text
TypeScript domain contracts
  -> React presentation and local interaction state
  -> Vite development/build boundary
  -> later dedicated /lab/api runtime integration
```

The current slice is UI-only. It does not invoke RelayLM runtime APIs or perform SOUL, MEM, RelayRUN, RelaySLP, TTS, audio, or avatar side effects.

## Implemented boundary

UI-A0 provides:

- TypeScript, React, and Vite project foundation,
- `/lab/` production asset base,
- Japanese-default message catalog with an English preview catalog,
- responsive AppShell,
- light and dark themes,
- hash-based local navigation,
- persisted active-character and theme selection,
- frontend type-check and production-build CI.

UI-A1 provides:

- a Home daily-living surface rather than a generic settings dashboard,
- mock visible-session conversation,
- character identity, scene, SOUL version, and stability display,
- content-free runtime component status projection,
- recent content-free event summaries,
- entry points to Communication and Lab Observation,
- a read-only Lab Observation preview for formed, held, and blocked memory outcomes,
- reserved route shells for Communication, Pod / SOUL Intervention, and Adoption.

## Browser authority boundary

The browser owns only presentation and ephemeral interaction state in this slice.

It must not be treated as the authority for:

- character persistence,
- active runtime character selection across server sessions,
- SOUL or MEM state,
- memory formation decisions,
- RelayRUN or RelaySLP state,
- backend credentials,
- raw trace data,
- intervention proposals or decisions.

Mock conversation submission produces only browser-local React entries and a clearly labeled mock response. The UI does not forward text to RelayLM Core.

## Language and contract policy

User-facing text is Japanese by default and is separated into a message catalog. Code identifiers, TypeScript domain names, and future API contracts remain English.

The current English catalog is a preview of the localization boundary, not a claim that every mock content field is fully localized. Runtime-supplied display text will require explicit locale-aware projection or a documented source-language policy.

## Visual boundary

The implementation follows the approved light/dark research-lab direction without making the reference images pixel-perfect requirements.

- Home emphasizes character presence and relationship continuity.
- Lab Observation uses a more technical read-only surface.
- Pod remains reserved for a later, visually stronger intentional-intervention slice.
- Mobile navigation collapses to a bottom bar while preserving the same information architecture.

## Validation

The frontend workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

The build must remain independent from Python package installation. Runtime API integration will be a later bounded slice with dedicated Python/Pydantic contracts and server-side authority enforcement.

## Next bounded slice

The next UI slice should remain mock-driven and implement one product surface completely rather than connecting all management APIs at once.

Recommended sequence:

```text
UI-A2 Adoption / first-launch flow
  -> no-character state
  -> Lab Assistant entry point
  -> new character / RelaySOUL source-set / SOUL.md import presentation
  -> browser-local validation only
  -> no filesystem or SOUL mutation
```

Communication, Pod mutation actions, and real Runtime API wiring should remain separate slices.
