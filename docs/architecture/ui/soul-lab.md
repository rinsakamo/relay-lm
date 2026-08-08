---
relaylm_doc_type: subsystem_architecture
relaylm_authority: soul_lab_browser_server_authority_and_governance_ui_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - SOUL Lab browser/server authority changes
  - Home conversation, observation, lifecycle visibility, or governance action surfaces change
  - Character Workspace UI topology or character-scope behavior changes
  - UI privacy/content-free projection or loopback security boundary changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact React routes, component hierarchy, API fields, CSS, or UI copy
  - RelayMEM persistence/mutation semantics, RelaySLP scheduling, RelaySOUL apply, or runtime backend routing internals
  - voice/TTS/avatar execution, communication transport, or static-bundle packaging implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../cw_a3_character_workspace_ui_rebuild.md
  - ../soul_lab_ui_mvp.md
  - ../character-workspace/system.md
  - ../character-workspace/creation-and-import.md
  - ../character-workspace/maintenance-candidates.md
  - ../runtime/request-response-pipeline.md
  - ../memory/system.md
  - ../memory/mutation-governance.md
  - ../privacy/protected-source-and-disclosure.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - SOUL Lab browser/server maintainers
  - Character Workspace, memory-governance, runtime, privacy, and diagnostics maintainers
  - product, security, evaluation, and documentation reviewers
relaylm_authority_level: subsystem
---
# SOUL Lab UI Architecture

## Purpose

This page is the canonical subsystem architecture for the SOUL Lab browser product and its server-owned authority boundary.

SOUL Lab exposes conversation, Character Workspace visibility, observation, lifecycle state, and explicit governance operations without becoming a second runtime, memory, scene, relationship, or persona authority.

The stable model is:

```text
browser UI
  -> bounded same-origin / loopback APIs
  -> server-owned route, character, runtime, memory, and mutation authorities
  -> content-free or explicitly governed projections
  -> user-visible conversation / observation / governance surfaces
```

The browser may request an action. The server and owning subsystem decide whether that action is valid and durable.

## Browser is not runtime authority

SOUL Lab does not own:

- backend model or endpoint selection;
- trusted route policy;
- memory store roots/namespaces;
- ordinary-memory reader selection;
- compiled RelayCTX prompt authority;
- current scene truth;
- current relationship identity/state;
- current affect state;
- worker/queue/lease identity;
- credentials or secrets;
- durable SOUL/MEM/REL/SCN mutation semantics.

Browser-selected display state must never be accepted as a substitute for server-side scope/authority validation.

## Top-level product surfaces

The stable Character Workspace-oriented UI topology includes responsibility areas equivalent to:

```text
Home
Character
Scenes
Relationships
Memory Wiki
Runtime
Advanced
```

Exact route hashes, component names, and navigation placement remain implementation details.

The important architectural property is that daily conversation and human-facing workspace concepts stay separate from low-level governance/diagnostic internals.

## Home conversation boundary

Home is the daily conversation surface.

For managed RelayLM conversation, the browser sends only the bounded server-projected route/model identifier required by the API contract plus ordinary user/assistant message content.

The browser does not construct or send privileged runtime context such as:

- raw SOUL or other durable source bodies as a hidden system prompt;
- frontend-generated `system`/`developer` authority;
- memory namespaces/store paths;
- compiled RelayCTX;
- backend credentials/IDs beyond the bounded public route projection;
- queue/worker identities;
- raw internal diagnostics.

The existing RelayLM request/response pipeline remains the runtime authority.

## Real Runtime versus Local Preview

Real Runtime and Local Preview are distinct modes.

A Real Runtime failure must not silently switch the user to Local Preview while preserving the appearance of a successful real conversation.

Stable rules are:

- mode selection is explicit;
- real and preview result provenance remains distinguishable;
- preview data does not become server-owned durable state;
- a preview is not evidence that a runtime request succeeded;
- stale results from one mode are not merged into the other.

## Character surface

Character exposes human-facing status/editor/preview surfaces for durable character-source families under Character Workspace authority.

Without an accepted save/apply contract, UI edits remain draft/preview-only.

Browser editing controls do not acquire direct filesystem or RelaySOUL mutation authority merely because source text can be displayed or edited.

High-authority durable source changes remain subject to their explicit server-side commit/apply boundary.

## Scenes surface

Scenes distinguishes:

- durable scene policy source;
- accepted reusable scene pages;
- inbox/staging scene candidates;
- current request-local scene state where a safe projection exists.

The browser does not select or normalize the current scene as runtime authority.

Scene inbox/candidate visibility does not make a candidate active or prompt-injectable.

RelaySCN remains the current scene owner.

## Relationships surface

Relationships distinguishes relationship vocabulary/policy, target-specific relationship source/state, and candidate/inbox material.

The UI does not infer target identity from a display label, selected card, or recent chat text.

Important relationship role/permission changes remain proposal/approval/apply operations under RelayREL/Character Workspace authority rather than browser-local state changes.

## Memory Wiki surface

Memory Wiki presents human-facing memory concepts without reviving one-file-per-memory or internal-record-first UX as the product model.

It may distinguish:

- memory policy;
- pages and semantic blocks;
- current/archived/hidden/held/blocked lifecycle classes;
- inbox/staging material;
- retrieval/usage visibility where safely projected.

Default human-facing surfaces should not require users to reason about internal memory IDs, revisions, queue records, worker state, apply tokens, or audit internals.

Those details belong in explicit Advanced/governance surfaces only when an existing safe API exposes them.

## Observation and Runtime visibility

Runtime/Observation surfaces expose bounded information about what the system actually used or decided.

Examples include safe projections for:

- current/last scene class;
- affect/expression class;
- relationship projection status;
- memory retrieval/usage evidence;
- context assembly summary;
- Character Workspace compiler/source status;
- lifecycle/governance result classes.

The UI must not infer backend-bound memory/context from visible response text alone.

If the owning runtime exposes an explicit used-memory/selected-context evidence artifact, that artifact is authoritative for the UI representation of usage.

## Ordinary-memory authority is external

SOUL Lab does not choose Primary versus Subjective versus no ordinary-memory reader.

The current RT-1 reader decision and Retrieval path are server/runtime authority.

UI observation may display a bounded selected-reader/usage class if safely projected, but it cannot:

- restore a fenced/retired reader;
- search another memory family after an empty result;
- interpret browser-visible memory pages as current retrieval output;
- turn a memory page into backend context by selecting it visually.

## Advanced surface

Advanced is the explicit developer/governance/diagnostics surface.

It may expose safe low-level labels and content-free projections that are inappropriate for the default product surfaces, such as:

- bounded lifecycle state;
- revision/content hash classes;
- pin/held/correction/forget status;
- queue/worker/audit labels where existing safe APIs provide them;
- reason/validation IDs;
- raw content-free diagnostic objects.

Moving an operation into Advanced does not expand browser authority.

## Explicit governance actions

Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard, and future mutation actions remain governed by their owning server-side contracts.

The UI can present preflight, confirmation, result, and history surfaces, but it does not weaken:

- exact character/namespace/scope checks;
- revision fencing;
- confirmation-token rules;
- writer/reader/mutation fences;
- lifecycle eligibility;
- audit/receipt requirements;
- fail-closed security behavior.

A button click is an action request, not proof that a mutation was valid or committed.

## Preflight and confirmation separation

High-impact governance follows a stable interaction model:

```text
user requests operation
  -> server preflight
  -> bounded human-readable diff/status
  -> explicit confirmation
  -> server re-validates scope/revision/token/current authority
  -> apply or reject
  -> content-free durable result/receipt where contract requires
```

The browser must not cache a preflight indefinitely and later apply it to a different revision/character/scope.

## Character scope

SOUL Lab may keep a browser-local display preference for which character the user is viewing.

That preference is not a global server active-character authority.

Server projections and request APIs remain explicitly character scoped.

If the projected conversation route is absent or ambiguous, the browser fails closed rather than choosing a backend/route priority itself.

## Character switching and stale requests

Changing character/scope must invalidate or abort in-flight browser work whose result belongs to the prior scope.

Delayed responses, streaming chunks, errors, observation projections, preflight results, and finalizers from a prior character must not update the newly selected character UI.

Stable safeguards include:

- request scope identity;
- abort/cancel where supported;
- stale-response rejection;
- final scope validation before committing browser-visible result state.

## Creation/import UI boundary

When no valid Character Workspace exists, SOUL Lab may route the user to creation/import.

It must not silently create/restore/activate a default/sample character to preserve Home availability.

Template selection, preview, validation, approval, commit, and active-character selection remain separate as defined by Character Workspace Creation and Import.

## Maintenance candidate UI boundary

SOUL Lab may expose dry-run maintenance candidates/proposals for review where accepted.

Candidate/proposal visibility does not make them applied source or current runtime authority.

High-impact changes remain approval/apply gated, and candidate preview does not become a hidden source-write path.

## Default display is content-free/minimized

Default Runtime/Advanced status surfaces prefer bounded metadata rather than content-bearing internal artifacts.

Allowed default classes may include:

- present/absent;
- lifecycle/status enums;
- counts;
- hashes where safe;
- reader/source classes;
- confidence/intensity bands;
- reason IDs;
- operation availability;
- candidate/proposal counts;
- content-free receipt summaries.

They should not display by default:

- raw backend prompts;
- full compiled context;
- protected source bodies;
- raw memory/relationship/scene content unrelated to an explicit editor/governance action;
- raw traces;
- credentials/secrets;
- unrestricted filesystem paths;
- queue payloads;
- internal exception bodies.

## Content-bearing management surfaces

A Character/Memory/Relationship/Scene editor or governance preflight may legitimately show bounded content when the user explicitly entered an authorized content-management surface.

That is different from making content-bearing data part of generic Runtime diagnostics.

Content-bearing management views require explicit server-side access/scope authority and should expose only what the operation needs.

## Browser storage boundary

Browser-process state should remain minimal.

Conversation transcript and protected workspace/memory bodies must not become durable browser storage by default merely for convenience.

Storing raw source bodies, private memories, compiled prompts, credentials, or governance tokens in `localStorage` or equivalent persistent browser storage requires separately governed security/privacy authority and is not implied by the UI architecture.

## Same-origin and loopback security

SOUL Lab management/governance APIs remain bounded to their accepted loopback/local security contracts.

Browser claims such as Host, Origin, query parameters, display mode, or forwarded headers are not sufficient locality proof by themselves.

The browser must not receive backend credentials or connect directly to a configured backend merely to implement Home.

Security-sensitive API details remain in their exact contracts.

## Error handling and leakage

User-facing errors must preserve privacy and scope boundaries.

The UI should not surface raw:

- backend response bodies;
- malformed SSE chunks;
- stack traces/exceptions;
- prompt/context bodies;
- credentials;
- confirmation tokens;
- private paths;
- queue/worker payloads;
- protected source content.

Bounded reason IDs/status messages are preferred.

## Rendering boundary

Browser rendering treats server/user text as text unless a separately accepted rendering contract safely permits richer content.

UI display helpers must not turn untrusted content into executable browser authority.

Exact frontend framework/security implementation remains outside this page.

## UI does not own persistence semantics

Displaying an item, toggling a local control, navigating to another screen, or retaining browser state does not mutate durable source/memory/relationship/scene state.

Every durable change requires an explicit server-owned write/apply contract.

This includes:

- character source writes;
- creation/import commit;
- relationship changes;
- scene/wiki maintenance;
- memory Correct/Forget/Pin/Held actions;
- future SOUL changes.

## UI does not own worker/scheduler lifecycle

SOUL Lab is not the worker supervisor.

Observation of queue/worker status does not authorize:

- worker startup;
- queue claim/retry;
- always-on loops;
- lease recovery;
- memory writer restoration.

If operator controls for those services are added later, they require separately governed operations/security authority.

## Current versus target

This page is current as the canonical SOUL Lab responsibility map.

Current implementation already provides real Home conversation, Character Workspace-oriented read-only/product surfaces, real observation/lifecycle visibility, and several explicit loopback governance operations under their own contracts.

Some packaging/integration capabilities may remain pending or separately evolving, including static bundle serving from RelayLM, peer communication transport, full durable source editing/apply, RelaySOUL apply/rollback, and voice/TTS/avatar runtime execution.

Project Status remains authoritative for exact completion.

## Stable invariants

- SOUL Lab is a browser client of server-owned authorities, not a second runtime.
- Home sends bounded ordinary conversation input and does not manufacture privileged system/developer context.
- Real Runtime and Local Preview remain explicit and never silently substitute for each other.
- UI visibility does not make source/candidate/runtime data authoritative.
- Used-memory/context evidence comes from owning runtime artifacts, not inference from visible output.
- SOUL Lab does not choose or restore ordinary-memory reader families.
- Correct/Forget/Pin/Held actions remain governed by exact server-side preflight/confirmation/apply contracts.
- Character switching rejects stale in-flight results from the prior scope.
- Missing/ambiguous conversation route fails closed rather than browser-side backend selection.
- Creation/import does not auto-create/activate a default character.
- Maintenance candidate visibility is not source apply.
- Default Runtime/Advanced diagnostics remain content-free/minimized.
- Protected content/credentials/raw prompts/traces/queue payloads are not generic browser diagnostics.
- Browser storage remains minimal and does not persist protected content by default.
- Browser state/navigation does not mutate durable data.
- UI observation does not grant worker/scheduler/mutation authority.

## Non-goals

This architecture does not define:

- exact React routes/components/styles;
- exact API payload fields;
- backend transport/model selection internals;
- memory persistence/mutation implementation;
- RelaySLP worker/scheduler lifecycle;
- RelaySOUL apply/rollback;
- voice/TTS/avatar execution;
- communication transport;
- static bundle packaging details;
- repository-level project sequencing.

## Related architecture

- [CW-A3 Character Workspace UI Rebuild](../cw_a3_character_workspace_ui_rebuild.md)
- [AITuber SOUL Lab UI MVP](../soul_lab_ui_mvp.md)
- [Character Workspace Architecture](../character-workspace/system.md)
- [Character Workspace Creation and Import](../character-workspace/creation-and-import.md)
- [Character Workspace Maintenance Candidates](../character-workspace/maintenance-candidates.md)
- [Runtime Request/Response Pipeline](../runtime/request-response-pipeline.md)
- [RelayMEM System](../memory/system.md)
- [Memory Mutation Governance](../memory/mutation-governance.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
