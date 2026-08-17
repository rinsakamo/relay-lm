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

It checks independently that:

- the provider failure is actually observed;
- the provider was called exactly once;
- the current User Event remains persisted;
- no Assistant Event is persisted;
- Canonical State remains unchanged.

The report also records bounded counts for provider calls, persisted Events, and persisted State records.

### `restart_continuity`

This deterministic scenario uses the OpenAI-compatible client boundary across two separately constructed RelayLM applications that point to the same Character Package.

The first session establishes an accepted `user.preference / tea = likes` State and a user/assistant Event pair. The second application then receives a request containing only the new follow-up user message.

It checks independently that:

- both client requests complete through the API;
- each cognitive provider is called exactly once;
- the pre-restart State and Events were persisted;
- the restarted CognitiveInput contains the accepted tea State;
- Working Context contains the pre-restart user/assistant exchange;
- Working Context sources are exactly the persisted pre-restart Event IDs;
- the current Input is only the new follow-up message.

This is deterministic runtime evidence. It does not replace #1259's required actual local-model restart product proof or make a naturalness/persona-quality claim.

### `assistant_self_certification_prevention`

This deterministic authority scenario separates conversational continuity from factual authority.

A prior user/assistant exchange is compiled into Working Context where the assistant says `あなたは北海道に住んでいる`. The scenario verifies that this utterance remains available for continuity with its `actor=assistant` and source Event ID intact.

It then proposes `user.fact / residence_location = Hokkaido` using only that assistant Event as provenance and checks that the existing Validator rejects the candidate as `user_state_requires_user_source`. Canonical State must remain unchanged.

The scenario therefore does **not** solve self-certification by deleting assistant dialogue from Context. It measures the intended separation:

```text
assistant dialogue
  may support continuity
  != authority to establish user truth
```

### `comparative_preference_preservation`

This deterministic State/Validator scenario starts with accepted `user.preference / tea = likes` and one current user Event expressing a stronger current preference for coffee.

It supplies only the two additive specific-key proposals expected from the frozen preference semantics:

```text
user.preference / coffee = likes
user.preference / preferred_beverage = coffee
```

It checks that:

- both proposals are accepted as creates;
- the existing weaker positive `tea = likes` State is preserved rather than implicitly removed or replaced;
- final preference State contains `tea`, `coffee`, and `preferred_beverage` simultaneously;
- both new States retain the current user Event as provenance.

This scenario evaluates RelayLM's deterministic preservation/State-transition behavior after candidate proposal. It does not claim that an actual model has correctly interpreted every comparative natural-language phrasing; model-side comparative extraction remains part of future actual-model quality evaluation.

### `degree_hint_integrity`

This deterministic Validator scenario starts with active `user.preference / coffee = {semantic: likes, degree_hint: 0.9}` and a current user Event supporting a weaker but still-positive coffee preference.

It checks that a valid replacement with degree `0.6` remains a `set` replacement rather than becoming an implicit remove. The final coffee State remains active and retains the current user Event as provenance.

The same pass also submits two invalid reserved envelopes: one with boolean `degree_hint: true`, and one adding a `confidence` field. Both must be rejected as `invalid_degree_hint_value` and neither may enter Canonical State.

This scenario verifies the current machine contract that degree is bounded semantic relative strength, not a removal threshold or confidence field. It does not infer or calibrate what a particular numeric degree should be for arbitrary natural language.

### `working_context_budget_atomicity`

This deterministic Context Compiler scenario uses two prior `user → assistant` exchanges plus the current user Event and applies the current Working Context budgets in two ways.

With an event-count limit that leaves the candidate window beginning on the older exchange's assistant Event, the unmatched assistant is dropped rather than admitted alone; only the newer complete user→assistant exchange remains.

With a character budget exactly large enough for the newer exchange but not both exchanges, the newer pair is again admitted together and the older pair is omitted together.

The scenario checks exact actor/source provenance for the admitted pair and verifies that the current user Event remains the current Input rather than being duplicated into Working Context.

This evaluates only the current bounded recent-dialogue behavior. Future relevance ranking, unresolved-task retention, MEMORY retrieval, targeted Event evidence retrieval, and token-aware selection remain #1267 work.

### `persistence_integrity`

This deterministic filesystem scenario exercises the current Character Package persistence boundary directly.

It writes one Event and one Canonical State record, reopens the same Character Package, and verifies exact round-trip equality. It also checks that the atomic State writer leaves no `.state.json.tmp` residue after a successful replacement.

The same scenario then corrupts `state.json` and `events.jsonl` deliberately. Malformed State must raise `CharacterDataError`; a malformed second Event line must likewise fail with line-location information. In both cases the malformed persisted file must remain unchanged rather than being silently repaired or rewritten.

This measures the current fail-closed filesystem contract. It does not claim crash-consistent multi-file transactions, backup/restore, migration, or multi-process writer safety.

### `correction_remove_semantics`

This deterministic State lifecycle scenario separates an explicit current-State removal from a weaker-but-still-positive update.

For explicit removal, it starts with accepted `user.preference / tea = likes`, records both the earlier supporting user Event and the later revocation Event, then applies a `remove` candidate sourced from the current revocation. The Validator must accept a `remove`, the persisted current State view must contain no tea slot, and both Events must remain in the Event Journal.

In a separate weakening case, active coffee preference degree `0.9` is updated to `0.6` using a `set` candidate. The action must remain `replace`, not `remove`, and the weakened positive State must remain current.

This evaluates deterministic behavior after the candidate operation has already been proposed. It does not claim that an actual model will classify every natural-language correction, hesitation, or weakening correctly.

Current scenario implementations may use deterministic synthetic providers or direct deterministic core contracts so failures can be attributed to RelayLM-owned boundaries instead of model variance.

## Deferred evaluation work

Still owned by #1247:

- crystallization quality and Markdown fidelity from #1260;
- relevance/retrieval evaluation from #1267;
- streaming/abort evaluation expansion beyond the existing deterministic contracts;
- future privacy/lifecycle evaluation from #1270;
- response/persona and actual local-model quality measurements;
- external benchmark adapters after current benchmark availability/version suitability is re-verified.

External benchmark names and versions are not frozen by the current native report format.

## Principle

> Evaluate the earliest RelayLM-owned boundary that became incorrect, rather than collapsing every failure into generic memory or response quality.
