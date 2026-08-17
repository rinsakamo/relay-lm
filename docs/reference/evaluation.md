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
      "metrics": {
        "provider_calls": 1
      }
    }
  ]
}
```

Each scenario contains explicit invariant checks. A failed check makes its scenario fail, and a failed scenario makes the report fail.

There is deliberately no weighted score, composite ranking, or severity arithmetic in the current format. Boundary violations remain inspectable individually until real failure distributions justify stronger aggregation policy.

## Boundary attribution

Each check carries a short `boundary` label identifying where the invariant is observed. This supports the white-box evaluation direction:

```text
Event / provenance
  -> State
  -> Context selection
  -> provider output
  -> Validator decision
  -> persistence
  -> visible response
```

The current labels are diagnostic metadata, not new runtime authorities.

## Current native scenarios

### `provider_failure_safety`

This deterministic scenario creates an isolated synthetic Character Package and runs one ordinary turn against a provider that intentionally fails on its first `generate` call.

It checks independently that the provider fails after exactly one call, the current User Event remains persisted, no Assistant Event is persisted, and Canonical State remains unchanged.

### `restart_continuity`

This deterministic scenario uses the OpenAI-compatible client boundary across two separately constructed RelayLM applications that point to the same Character Package. The restarted request contains only the new follow-up user message while persisted State and RelayLM-owned Event-derived Working Context provide continuity.

This is deterministic runtime evidence. It does not replace #1259's required actual local-model restart product proof or make a naturalness/persona-quality claim.

### `assistant_self_certification_prevention`

A prior assistant statement may remain in Working Context with `actor=assistant` and exact Event provenance, but an assistant-only `user.fact` candidate is rejected as `user_state_requires_user_source`. Continuity evidence therefore does not become user truth merely through prompt placement.

### `comparative_preference_preservation`

With existing `user.preference / tea = likes`, additive `coffee = likes` and `preferred_beverage = coffee` candidates are accepted while the weaker positive tea preference remains unchanged. This evaluates RelayLM-side preservation after candidate proposal, not actual-model comparative-language extraction quality.

### `degree_hint_integrity`

A valid weakening from degree `0.9` to `0.6` remains a `set` replacement, not an implicit remove. Boolean degree values and reserved envelopes containing `confidence` are rejected. The scenario does not calibrate what degree an actual model should assign to arbitrary language.

### `working_context_budget_atomicity`

Event-count and character-budget pressure preserve complete prior `user → assistant` exchanges, do not admit an orphan assistant Event, preserve exact source provenance, and keep the current user Event solely as current Input. Future relevance ranking/retrieval remains #1267 work.

### `persistence_integrity`

Event and State round-trip exactly across reopen. Successful State replacement leaves no temporary-file residue. Deliberately malformed State/Event persistence fails closed with `CharacterDataError` and is not silently repaired or rewritten.

### `correction_remove_semantics`

Explicit current user-sourced `remove` closes the current State slot while retaining Event history. A weaker-but-still-positive preference supplied as `set` remains `replace`, not `remove`. This evaluates deterministic behavior after candidate operation selection, not model-side correction classification.

### `crystallization_integrity`

The current #1260 off-turn core materializes readable `MEMORY.md`, while State write-back still passes through the existing Validator. A user-supported tea preference can be accepted; an assistant-only Hokkaido user fact remains rejected even when similar prose appears in Markdown. An unchanged second explicit pass avoids Markdown churn and yields a State noop for the already-accepted preference.

This evaluates RelayLM-owned authority and rerun stability only. It does not claim actual local-model crystallization quality, semantic note splitting, or retrieval behavior.

### `streaming_safety`

This deterministic #1269 scenario evaluates the RelayLM-owned streamed completion boundary in three cases.

For a successful stream, user-visible text is emitted while persistence still contains only the User Event and no State mutation. After the complete structured cognitive result returns, the Assistant Event and accepted State are committed and the stream ends with `[DONE]`.

For a truncated provider stream, already-safe visible text may be delivered, but no `[DONE]` marker is emitted and persistence remains User-only with no State mutation.

For downstream client closure, closing the RelayLM stream after the first visible chunk cancels the in-flight producer. Persistence again remains User-only with no State mutation.

This scenario evaluates delivery/commit/cancellation semantics already implemented under #1269. Provider-wire incremental JSON parsing remains covered by its dedicated unit contracts rather than duplicated in the native report.

Current scenario implementations may use deterministic synthetic providers or direct deterministic core contracts so failures can be attributed to RelayLM-owned boundaries instead of model variance.

## Deferred evaluation work

Still owned by #1247:

- relevance/retrieval evaluation from #1267;
- future privacy/lifecycle evaluation from #1270;
- response/persona and actual local-model quality measurements;
- external benchmark adapters after current benchmark availability/version suitability is re-verified.

External benchmark names and versions are not frozen by the current native report format.

## Principle

> Evaluate the earliest RelayLM-owned boundary that became incorrect, rather than collapsing every failure into generic memory or response quality.
