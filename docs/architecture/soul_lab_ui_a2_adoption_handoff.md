---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - first-launch or adoption UI behavior changes
  - server-side persona source inspection begins
  - character registration or persistence begins
relaylm_not_authoritative_for:
  - RelayLM Core runtime behavior
  - RelaySOUL source parsing or validation semantics
  - filesystem mutation or character persistence
  - SOUL Lab Runtime TTS, audio, or avatar execution
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a0_a1_handoff.md
  - memory_lifecycle_design.md
---
# SOUL Lab UI-A2 First Launch and Adoption Flow

## Status

SOUL Lab UI-A2 is implemented as a browser-local first-launch and character-adoption preview under `apps/soul-lab/`.

```text
No Active Character
  -> Lab Assistant guided entry
  -> choose new / source-set adoption / SOUL.md import
  -> validate required source composition in browser memory
  -> review draft
  -> stop before persistence or Core mutation
```

The current slice is UI-only. It does not inspect source locations, read selected file contents, create persona files, register a character, or invoke RelayLM management APIs.

## Implemented boundary

UI-A2 provides:

- a dedicated `#/adoption` route outside the active-character runtime surface,
- explicit `NO ACTIVE CHARACTER` first-launch state,
- Lab Assistant guidance without privileged access,
- a New Character draft flow,
- a RelaySOUL source-set adoption draft flow,
- a `SOUL.md` import composition flow,
- explicit `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md` requirements,
- safe-default companion-source options when only `SOUL.md` is supplied,
- browser-local validation and review,
- a final `NOT PERSISTED` state,
- Japanese-default and English-preview copy,
- responsive light and dark presentation.

## Lab Assistant boundary

The Lab Assistant in this slice is presentation content only. It explains the available entry paths and the browser authority boundary.

It does not:

- inspect the filesystem,
- read persona source contents,
- access API keys,
- inspect another character's SOUL or MEM,
- create or mutate RelaySOUL state,
- approve a character on behalf of the server.

A future runtime-backed Lab Assistant should remain a normal RelayLM character instance and use explicit management projections rather than privileged direct access.

## Adoption draft types

### New Character

The user supplies:

- display name,
- optional relationship starting note.

The UI previews initialization of:

- `SOUL.md`,
- `OUTPUT_POLICY.md`,
- `RELATIONSHIP_ANCHOR.md`.

No file is created in UI-A2.

### RelaySOUL source-set adoption

The user supplies a source-set location and confirms that the three required sources are expected.

The location is not read by the browser. The checkboxes model the future server-side inspection contract only.

### `SOUL.md` import

The user selects filenames for:

- required `SOUL.md`,
- optional supplied `OUTPUT_POLICY.md`,
- optional supplied `RELATIONSHIP_ANCHOR.md`.

If a companion source is not selected, the user must leave safe initialization enabled. The UI validates composition only; it does not read file bytes.

## Browser authority boundary

The final review object is an ephemeral browser-local draft.

It must not be interpreted as:

- a registered character,
- a validated RelaySOUL source set,
- an accepted SOUL candidate,
- durable persona state,
- filesystem state,
- an authorization decision.

The completion screen is explicitly marked `NOT PERSISTED`.

## Validation

The existing SOUL Lab UI workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

## Next bounded slice

The next independent UI slice should implement Communication as a mock-driven session surface before adding real management APIs.

Recommended sequence:

```text
UI-A3 Communication
  -> peer selection
  -> external OpenAI-compatible peer / RelayLM peer distinction
  -> start session
  -> Soft Stop as default
  -> emergency stop as explicit exception
  -> content-free session timeline
  -> no network call or RelayRUN mutation
```

Server-side source inspection, character persistence, and `/lab/api/*` integration remain separate bounded slices.
