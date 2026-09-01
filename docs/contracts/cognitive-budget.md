# Cognitive Budget Contract

This document is the canonical product authority for RelayLM `v1` cognitive-budget accounting, protection tiers, deterministic degradation, and final fit enforcement.

The cognitive-budget layer controls **how much room each semantic layer receives**. It does not redefine which State, Continuity, Working Context, MEMORY, or Event Evidence is semantically relevant inside that layer.

## Total-budget model

For an ordinary generation, the effective model context capacity is partitioned conceptually as:

```text
model_context_window
  = required_input_framing
  + cognitive_input_tokens
  + reserved_output_tokens
```

- `model_context_window` is the effective hard context capacity of the configured model/provider path.
- `reserved_output_tokens` is capacity intentionally unavailable to input assembly so generation has room to complete.
- `required_input_framing` covers provider/schema/message framing required by the actual serialized request.
- `cognitive_input_tokens` covers the serialized RelayLM cognitive payload admitted for the turn.

Final admission is based on the real serialized provider input. Where exact token counting is unavailable before generation, RelayLM may use only a conservative bounded estimator; optimistic silent under-counting is not valid budget enforcement.

## Protection tiers

### Tier 0 — protected anchors and reserve

Tier 0 contains:

- required provider/schema/framing overhead;
- Identity Core;
- the Current Event;
- reserved output capacity.

Identity and the Current Event are protected from silent eviction. If required framing plus these anchors and output reserve cannot fit, RelayLM fails before semantic generation rather than dropping or replacing them.

Budget enforcement does not introduce an automatic summarization-model call.

### Tier 1 — current semantic authority

Tier 1 contains:

- relevant active Canonical State;
- already accepted Continuity Context.

Global budgeting may reduce the envelope available to this tier only according to explicit policy and owner-defined deterministic selection. Prompt pressure does not mutate Canonical State and does not expire, resolve, or rewrite accepted Continuity.

### Tier 2 — recent conversational continuity

Tier 2 contains Working Context.

Working Context is degradable prompt residency. Removing an exchange from the current prompt is not forgetting and does not alter Event Journal authority. The Context Compiler remains responsible for within-layer exchange integrity and selection semantics.

### Tier 3 — optional retrieved evidence

Tier 3 contains:

- Retrieved MEMORY;
- targeted Event Evidence.

These are optional retrieval/projection layers and are the first broad tier eligible for reduction. The cognitive-budget owner does not flatten State, Continuity, Working Context, MEMORY, and Events into one global relevance score.

## Deterministic degradation

Budget pressure follows the product protection order:

```text
Tier 3 optional retrieved evidence
  -> Tier 2 Working Context
  -> Tier 1 current authority above explicit floors
  -> Tier 0 protected anchors/reserve
  -> fail before generation
```

Within a layer, the semantic owner decides what belongs inside the envelope. The budget layer decides only the envelope and the deterministic order in which envelopes may be reduced.

For identical inputs, configuration, provider-counting capability, and selected semantic inputs, budget degradation and terminal failure behavior are deterministic.

## Enforcement loop

The ordinary-turn enforcement boundary is:

1. resolve the effective model context window and configured output reserve;
2. account for required framing and protected anchors;
3. fail immediately if Tier 0 cannot fit;
4. construct the explicit budget plan and layer envelopes;
5. let each semantic owner select/project within its assigned envelope;
6. serialize the real provider request and count or conservatively estimate actual input tokens;
7. if over capacity, apply the next legal deterministic degradation step and recompile/recount;
8. stop when the request fits or no legal degradation remains;
9. fail before semantic generation when no legal fit exists;
10. otherwise perform the ordinary semantic generation exactly once for that generation boundary.

A provider error caused by knowingly sending an oversized request is not the normal budget mechanism.

Two-pass cognition carries explicit pass-local budget configuration while preserving the same protection and fit semantics for each actual provider request.

## Diagnostics

Budget diagnostics are aggregate and content-free. They may report values such as configured/effective capacity, output reserve, framing and serialized token counts, pressure/degradation counts, reduced layers or tiers, final outcome, failure reason, and exact-versus-conservative count mode.

They must not expose Identity text, State keys or values, Continuity values, MEMORY content or locations, Event content, or other semantic payload. Diagnostics observe budget execution; they do not become semantic authority.

## Numeric defaults

This contract defines semantics before calibration numbers. Numeric defaults for context profiles, layer envelopes, floors, or output reserve are calibration decisions and require the appropriate actual-model evidence. Convenience values do not become canonical merely because the mechanics permit them.

## Ownership boundaries

The cognitive-budget owner does **not** own:

- State relevance or State lifecycle;
- MEMORY or Event retrieval/ranking;
- State-versus-MEMORY contradiction semantics;
- Continuity acceptance or lifecycle;
- within-layer semantic ranking;
- provider-specific structured-output meaning;
- persistence, forgetting, or deletion;
- actual-model calibration evidence.

> Global budgeting chooses how much room a layer receives; the layer's semantic owner chooses what belongs in that room.
