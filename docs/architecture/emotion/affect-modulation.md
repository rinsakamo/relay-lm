---
relaylm_doc_type: subsystem_architecture
relaylm_authority: relayemo_affect_estimation_expression_and_modulation_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: emotion
relaylm_update_trigger:
  - RelayEMO affect or expression responsibility changes
  - relationship-conditioned affect gain changes
  - RelaySCN expression gating or scene-hint boundary changes
  - return-side display, TTS, avatar, or output-expression hint ownership changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact affect vectors, enums, thresholds, parser, model, session-state, or projection schemas
  - exact TTS, avatar, display-marker, output-rendering, or adapter implementation
  - exact relationship, scene, memory, SOUL, or safety policy
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../acg5_relayemo_scene_cleanup.md
  - ../../relayemo_mvp_initial_design.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../memory/observation-and-character-belief.md
  - ../privacy/protected-source-and-disclosure.md
  - ../pipeline-responsibilities.md
  - ../safe_soul_scene_ctx_compile_chain.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayEMO and runtime maintainers
  - RelayREL, RelaySCN, RelayCTX, voice, avatar, and UI integration maintainers
  - privacy, social-expression, and evaluation reviewers
relaylm_authority_level: subsystem
---
# RelayEMO Affect Modulation

## Purpose

This page is the canonical subsystem architecture for RelayEMO affect estimation, assistant expression state, and bounded expression modulation.

RelayEMO owns temporary affect/expression signals. It does not own normalized scene state, relationship state, durable memory truth, portable character identity, or final rendering engines.

The stable component boundary is:

```text
validated request evidence
  + RelayREL relationship-conditioned gain/limits
  + RelaySCN current scene/expression policy
  -> RelayEMO affect estimate
  -> bounded assistant expression state
  -> expression/display/TTS/avatar hints
```

Exact implementation completion remains owned by Project Status. Exact affect schemas, thresholds, model choices, session-state representation, and adapters remain with their owning contracts and implementation handoffs.

## Current authority after scene cleanup

ACG-5 removed the remaining same-turn scene-authority ambiguity.

RelaySCN is the sole normalized owner of `scene_state` and `scene_policy`.

RelayEMO owns:

- user-affect estimate as an estimate;
- assistant expression/emotion-control state;
- bounded affect-probe candidates;
- expression intensity/modulation hints;
- optional content-free, restrictive scene-hint candidate for its own gating/diagnostics;
- return-side display/TTS/avatar style hints after safe visible output exists.

RelayEMO does not open RelayMEM retrieval or mutation policy and does not feed a scene fallback back into RelaySCN as authority.

## Affect is an estimate, not observed truth

Affect inference is uncertain interpretation of bounded evidence.

Stable rules are:

- estimates remain explicitly marked as estimates;
- confidence/uncertainty is retained;
- low-confidence input degrades toward neutral/unknown or conservative handling;
- the system avoids mental-state diagnosis or sensitive-attribute inference outside explicit accepted authority;
- model or heuristic confidence is not source provenance;
- one affect estimate cannot prove a user fact;
- one affect estimate cannot directly update SOUL, MEM, or relationship state.

Strong feeling is not strong evidence.

## Relationship-conditioned modulation

RelayREL may provide target-specific gain and permissions that influence how affect is expressed or acted upon.

Examples of bounded relationship-conditioned effects include:

- warmth/intensity gain;
- repair tone;
- attachment-sensitive salience;
- unsolicited-probe limits;
- familiarity-dependent expression range;
- disagreement or teasing bounds.

RelayEMO consumes these as modulation/constraint inputs. It does not own the relationship state that produced them.

A high relationship gain cannot override privacy, scene, BOUNDARY, safety, or explicit interaction limits.

## Scene-conditioned expression

RelaySCN owns the current situation and expression allowance.

Scene policy may clamp, suppress, or otherwise narrow RelayEMO expression.

Examples:

- formal-document scene suppresses decorative markers;
- public group scene narrows intimate expression;
- medical/safety scene may require conservative tone;
- recovery scene may suppress nonessential modulation;
- roleplay scene may allow bounded expressive style while still respecting privacy and identity boundaries.

RelayEMO does not infer or normalize the current scene merely because affect evidence suggests one.

Any retained scene-hint candidate is non-authoritative, restrictive-only, and unable to open runtime policy.

## Assistant expression state

Assistant expression state is runtime control, not a claim about consciousness or durable persona.

It may represent bounded state such as:

- expression class;
- intensity;
- confidence;
- stability;
- maximum per-turn delta;
- decay behavior;
- suppression/clamp state.

Exact fields remain implementation details.

Stable behavior is:

- update slowly enough to avoid erratic oscillation;
- bound per-turn change;
- decay or neutralize when evidence becomes weak;
- use resolved session scope when session-local reuse is allowed;
- otherwise use stateless/fail-safe initialization;
- remain process/request/session-local unless a separate authority explicitly permits persistence;
- never become canonical RelaySOUL or RelayMEM state.

## Durable voice boundary

Approved SOUL/STYLE/OUTPUT policy and the Main LLM own ordinary durable character voice.

RelayEMO modulates that voice within accepted bounds. It should not redefine durable identity or replace the main response with a separate meaning-changing rewrite path.

Affect can influence tone, emphasis, pacing, warmth, or engine-neutral hints while preserving semantic responsibility.

If modulation would materially change meaning, factual content, privacy, safety, or instruction compliance, it must fail closed rather than apply as a cosmetic post-process.

## Input-side versus return-side responsibilities

### Input-side RelayEMO

Input-side RelayEMO may estimate current affect/expression pressure after RelayREL and RelaySCN have established their applicable policy boundaries.

Its output can inform response/context policy only within the authority granted by those downstream consumers.

### Return-side RelayEMO

Return-side RelayEMO may produce bounded expression hints after safe visible output or validated response observations exist.

It may emit engine-neutral classes for:

- display expression;
- TTS style;
- optional non-semantic marker;
- avatar expression;
- avatar motion.

External adapters remain responsible for mapping these classes to concrete engines after the applicable runtime/safety gate.

Return-side RelayEMO is not a general output rewriter.

## Display marker boundary

Optional visual markers are presentation hints, not semantic content authority.

Stable rules are:

- default-off unless the owning output policy allows them;
- preserve terminal punctuation and visible sentence meaning;
- TTS normally omits purely visual markers;
- markers do not become memory, Evidence, or SOUL state;
- marker failure preserves the approved text unchanged;
- scene/output policy may suppress markers independently of affect intensity.

Exact marker placement and rendering remain implementation details.

## TTS and avatar boundary

RelayEMO may produce engine-neutral hints but does not execute TTS or avatar control directly.

```text
RelayEMO hint
  -> current-response safety / emission gate
  -> voice/avatar adapter
  -> external engine
```

The adapter may ignore unsupported hints without changing semantic output.

Failure in TTS/avatar mapping must not trigger memory, SOUL, relationship, or scene mutation.

## Affect probe candidates

A structured model or heuristic may generate an affect candidate under bounded governance.

Such a candidate is evidence for RelayEMO, not direct state authority.

Stable requirements include:

- bounded input/output;
- strict validation;
- finite numeric values where numeric fields exist;
- timeout/busy-skip behavior that does not block the main response indefinitely;
- invalid candidates fall back to safe heuristic/neutral behavior;
- dry-run/candidate output does not automatically become active state;
- semantic candidate content does not enter generic diagnostics.

Exact model, backend route, schema, and thresholds remain separately governed.

## Scene hint is non-authoritative

RelayEMO may sometimes infer that affect pressure suggests a safety, recovery, or scene-related concern.

This produces at most a bounded `scene_hint_candidate` or equivalent evidence class.

It cannot:

- create normalized `scene_state`;
- replace RelaySCN policy;
- override trusted/confirmed scene state;
- open broad memory retrieval or update policy;
- restore the old RelayEMO-to-RelaySCN fallback;
- become durable scene source automatically.

RelaySCN remains the sole scene authority.

## Relationship and affect remain separate

Relationship state is durable/target-specific interaction policy; affect is transient request/session-local estimation and expression pressure.

```text
RelayREL
  how this character may interact with this target

RelayEMO
  what transient affect/expression pressure is estimated now
```

A positive affect turn does not raise durable trust automatically. A negative turn does not lower relationship state automatically.

Any durable relationship update must follow the out-of-band relationship candidate/proposal authority.

## Memory and Evidence boundary

RelayEMO may contribute bounded non-authoritative formation evidence if an owning memory contract accepts it.

It cannot by itself:

- prove a user fact;
- increase Shared Assessment confidence merely because intensity is high;
- write grounded memory content;
- determine durable subjective meaning;
- authorize persistence;
- Correct, Forget, Pin, Consolidate, or otherwise mutate memory.

Transient reaction is not durable memory truth.

## SOUL boundary

RelaySOUL owns durable portable character identity and approved expression policy.

RelayEMO may use approved EMOTION/STYLE policy and current runtime context, but it does not directly mutate SOUL from one affect estimate or expression outcome.

Repeated experiences may become governed Evidence for a future separately authorized proposal. They are not automatic persona edits.

## Privacy and disclosure

Affect estimation may itself be sensitive semantic processing.

Internal affect artifacts are purpose-bounded runtime-private state. They do not become public merely because they are useful to rendering or response generation.

Expression does not disclose protected facts that privacy, scene, relationship, or memory policy forbids.

Affect must not leak private inference indirectly through overly specific markers, captions, avatar actions, or explanatory diagnostics.

## Content-free diagnostics

Default trace/audit projection is content-free.

It may expose bounded values such as:

- affect-estimate present/absent;
- source class;
- confidence/intensity bands;
- expression-state class;
- expression gate allowed/suppressed;
- display/TTS/avatar hint presence;
- candidate applied/refused boolean;
- restrictive-only scene-hint status;
- reason/validation IDs;
- assertions that MEM/SOUL persistence did not occur.

It does not expose by default:

- raw user/assistant text;
- numeric affect vectors when not explicitly allowlisted;
- semantic affect candidate bodies;
- relationship or scene bodies;
- memory or protected Evidence text;
- visible response text;
- display/TTS/caption strings;
- session-local assistant-state values;
- unbounded model rationale or exception text.

A runtime-private affect object must not be serialized wholesale into a generic trace.

## Failure behavior

RelayEMO failure degrades expression, not semantic authority.

```text
affect candidate invalid/unavailable
  -> safe heuristic / neutral / no modulation
  -> main response continues when otherwise valid

return-side hint generation fails
  -> preserve approved visible text
  -> omit hints

scene hint uncertain
  -> restrictive/no-op evidence only
  -> never open policy

privacy or scene gate blocks expression
  -> suppress/clamp modulation
  -> do not search for a bypass path
```

No failure path writes MEM, SOUL, relationship state, or normalized scene state.

## Current versus target

This page is current as the canonical RelayEMO responsibility map.

Some richer runtime-private/projection schemas, marker improvements, or adapter integrations may remain target or partially implemented. The old broad RelayEMO MVP artifact is implementation/compatibility history; it is not the permanent ownership model.

The current authority already reflects ACG-5: RelaySCN owns scene state/policy; RelayEMO scene hints are non-authoritative and restrictive-only.

Project Status remains authoritative for exact implementation completion.

## Stable invariants

- RelayEMO owns transient affect estimation, assistant expression state, and bounded expression hints.
- Affect remains explicitly estimated and uncertainty-preserving.
- Strong affect is not strong Evidence.
- RelayREL may modulate affect/expression but remains the relationship owner.
- RelaySCN may clamp/suppress expression and remains the sole scene-state/policy owner.
- RelayEMO scene hints are non-authoritative, restrictive-only, and cannot open runtime policy.
- RelayEMO does not write MEM, SOUL, relationship state, or normalized scene state.
- Ordinary durable character voice remains owned by approved character/output policy plus the Main LLM.
- Return-side expression hints do not become a meaning-changing output rewrite path.
- TTS/avatar adapters execute engine mapping; RelayEMO only supplies bounded hints.
- Runtime-private affect content remains separate from content-free diagnostics.
- Failure preserves semantic output and closes toward less modulation.

## Non-goals

This architecture does not define:

- exact VAD/vector/enumeration fields or thresholds;
- a specific affect model or backend;
- mental-health diagnosis or sensitive-attribute inference;
- durable user-affect storage;
- relationship, scene, memory, or SOUL mutation;
- exact TTS/avatar/display implementation;
- general output rewriting;
- current implementation completion or project sequencing.

## Related architecture

- [ACG-5 RelayEMO Scene Ownership Cleanup](../acg5_relayemo_scene_cleanup.md)
- [RelayEMO MVP Initial Design](../../relayemo_mvp_initial_design.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Observation and Character-Conditioned Belief](../memory/observation-and-character-belief.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
- [Safe REL / SOUL / Scene / CTX Compile Chain](../safe_soul_scene_ctx_compile_chain.md)
