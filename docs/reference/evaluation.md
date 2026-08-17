# RelayLM Native Evaluation

RelayLM evaluation distinguishes visible response quality from State, authority, continuity, and persistence correctness.

```text
response correctness
  != State correctness
  != authority correctness
  != continuity correctness
  != persistence correctness
```

The current repository includes a small native evaluation foundation. It is intentionally not a leaderboard or composite quality score.

## Current command

After installing the package:

```bash
relaylm-eval
```

The command runs the currently registered deterministic native scenarios and prints a machine-readable JSON report. The process exits successfully when every scenario passes and non-zero when the report status is `fail`.

## Report shape

The current report uses `format_version: 1` and suite identity `relaylm-native`.

Conceptually:

```json
{
  "format_version": 1,
  "suite": "relaylm-native",
  "status": "pass",
  "scenarios": [
    {
      "id": "provider_failure_safety",
      "status": "pass",
      "checks": [
        {
          "id": "provider_called_once",
          "boundary": "provider",
          "passed": true,
          "expected": 1,
          "observed": 1
        }
      ],
      "metrics": {"provider_calls": 1}
    }
  ]
}
```

Each scenario contains explicit invariant checks. A failed check makes its scenario fail, and a failed scenario makes the report fail. There is deliberately no weighted score, composite ranking, or severity arithmetic in the current format.

## Boundary attribution

Each check carries a short `boundary` label identifying where the invariant is observed:

```text
Event / provenance
  -> State
  -> Context selection
  -> provider output
  -> Validator decision
  -> persistence
  -> visible response
```

The labels are diagnostic metadata, not new runtime authorities.

## Current native scenarios

### `provider_failure_safety`

Creates an isolated Character Package and runs one ordinary turn against a provider that intentionally fails. It verifies one provider call, persistence of the Current User Event, absence of an Assistant Event, and unchanged Canonical State.

### `restart_continuity`

Uses two separately constructed RelayLM applications against the same Character Package. The first establishes accepted State and a user/assistant Event pair; the second receives only the new follow-up. It verifies persisted State/Events, Event-derived Working Context, source IDs, and the new Current Input. This is deterministic runtime evidence and does not replace #1259 actual local-model restart proof.

### `assistant_self_certification_prevention`

Preserves assistant-authored dialogue in Working Context for continuity while verifying that an assistant-only source cannot establish a user fact in Canonical State.

### `comparative_preference_preservation`

Starts with `tea = likes`, applies additive `coffee = likes` and `preferred_beverage = coffee`, and verifies the weaker positive tea preference is preserved rather than implicitly removed.

### `degree_hint_integrity`

Verifies that valid preference weakening remains a `set` replacement and that invalid degree-hint envelopes or reserved confidence fields are rejected.

### `working_context_budget_atomicity`

Verifies that Working Context event/character pressure retains complete user→assistant exchanges, drops orphan assistants, preserves exact Event sources, and does not duplicate Current Input.

### `persistence_integrity`

Exercises filesystem Event/State round-trip, atomic State replacement residue, and fail-closed malformed State/Event data without silent repair.

### `correction_remove_semantics`

Separates explicit current-State removal from weaker-but-still-positive replacement while preserving source Events.

### `crystallization_integrity`

Exercises deterministic off-turn crystallization authority/idempotence: user-sourced State may be accepted, assistant-only user claims remain rejected even when readable synthesis contains them, and identical reruns do not rewrite unchanged Markdown.

### `streaming_safety`

Measures successful streamed commit ordering, truncated-stream fail-closed behavior, and downstream cancellation without premature Assistant/State persistence.

### `state_selection_diagnostics`

Measures content-free active-State selection diagnostics under lexical matches and deterministic fallback and verifies semantic identifiers/content do not leak into diagnostics.

### `memory_heading_retrieval`

Measures complete-section positive lexical MEMORY retrieval, unrelated suppression, and skip-not-truncate character-budget behavior.

### `memory_cognitive_projection`

Measures distinct crystallized-memory projection, provider serialization, and separation of Markdown locations from Event provenance.

### `ordinary_turn_memory_retrieval`

Measures explicit ordinary-turn `MemoryRetrievalBudget`, exactly one provider call, omitted-budget no-read behavior, and fail-closed MEMORY read failure ordering after Current User Event persistence.

### `state_memory_authority_filter`

Measures the deterministic explicit-key State-shadow subset: stale same-key MEMORY is suppressed, compatible current-value memory retained, active State authority is independent of State residency caps, unrelated history is not over-classified, exact token boundaries are preserved, and comparative preference semantics are not collapsed.

### `targeted_event_retrieval`

Measures the retrieval-only targeted Event primitive: positive-only lexical selection, no irrelevant fallback, explicit Current Event exclusion, whole-Event budgeting, relevance-ranked admission with chronological output, newer tie-breaks, and exact-token boundaries.

### `event_evidence_cognitive_projection`

Measures distinct Event-evidence projection/provider semantics: real Event ID/type/actor/timestamp/content survive, Current Input is not duplicated, provider serialization is separate, and real Event IDs remain provenance while MEMORY locations do not.

### `ordinary_turn_event_retrieval`

This deterministic #1267 scenario evaluates PR #1320's opt-in ordinary-turn targeted Event retrieval against isolated Character Packages.

It checks that:

- an explicit `EventRetrievalBudget` can re-admit an older relevant persisted Event that has already fallen outside recent Working Context;
- the Current User Event is excluded from Event evidence and remains Current Input;
- the successful ordinary turn calls the cognitive provider exactly once;
- when Event retrieval is enabled, the pre-generation Event Journal snapshot is shared with Working Context selection rather than causing an extra retrieval-only scan;
- omitting the Event budget preserves the previous empty Event-evidence behavior.

This scenario evaluates deterministic runtime wiring and one-generation behavior only. It does not claim retrieval-scaled Event Journal indexing, default Event budgets, cross-layer redundancy suppression, semantic/multilingual/temporal retrieval, or actual-model response benefit. Buffered/streaming path parity remains directly covered by unit contracts using the same preparation owner.

Current scenario implementations may use deterministic synthetic providers or direct deterministic core contracts so failures can be attributed to RelayLM-owned boundaries instead of model variance.

## Deferred evaluation work

Still owned by #1247:

- #1267 retrieval-scaled Event Journal access, evidence-backed default MEMORY/State/Event budgeting, broader State-vs-memory authority semantics beyond explicit-key lexical filtering, cross-layer redundancy/retention policy, and cross-layer/token-aware diagnostics as those runtime slices land;
- future privacy/lifecycle evaluation from #1270;
- response/persona and actual local-model quality measurements;
- external benchmark adapters after current benchmark availability/version suitability is re-verified.

External benchmark names and versions are not frozen by the current native report format.

## Principle

> Evaluate the earliest RelayLM-owned boundary that became incorrect, rather than collapsing every failure into generic memory or response quality.
