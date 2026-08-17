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

This evaluates only the current bounded recent-dialogue behavior. Future semantic retention, Event-evidence projection/runtime wiring, and token-aware cross-layer selection remain #1267 work.

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

### `crystallization_integrity`

This deterministic off-turn scenario exercises the current #1260 crystallization core without an actual model.

A user Event states that Rin likes tea, while a separate assistant Event claims that Rin lives in Hokkaido. The crystallizer emits readable `MEMORY.md` containing both pieces of prose and proposes two StateCandidates: a user preference sourced from the user Event and a user fact sourced only from the assistant Event.

The scenario verifies that:

- readable Markdown is materialized as crystallized synthesis even when it includes explicitly unverified assistant continuity;
- the user-sourced tea preference passes the existing Validator and becomes Canonical State;
- the assistant-only Hokkaido user fact is rejected as `user_state_requires_user_source`;
- the presence of that Hokkaido sentence in `MEMORY.md` does not promote it into Canonical State;
- a second identical explicit crystallization pass does not rewrite unchanged Markdown and produces a State noop for the already-accepted tea preference while continuing to reject the assistant-only fact;
- each explicit crystallization pass invokes the crystallizer once, and the second pass receives prior `MEMORY.md` as input.

This evaluates RelayLM-owned authority and rerun stability only. It does not claim actual local-model crystallization quality, semantic note splitting, or retrieval behavior.

### `streaming_safety`

This deterministic #1269 scenario evaluates the RelayLM-owned streamed completion boundary in three cases.

For a successful stream, user-visible text is emitted while persistence still contains only the User Event and no State mutation. After the complete structured cognitive result returns, the Assistant Event and accepted State are committed and the stream ends with `[DONE]`.

For a truncated provider stream, already-safe visible text may be delivered, but no `[DONE]` marker is emitted and persistence remains User-only with no State mutation.

For downstream client closure, closing the RelayLM stream after the first visible chunk cancels the in-flight producer. Persistence again remains User-only with no State mutation.

This scenario evaluates delivery/commit/cancellation semantics already implemented under #1269. Provider-wire incremental JSON parsing remains covered by its dedicated unit contracts rather than duplicated in the native report.

### `state_selection_diagnostics`

This deterministic #1267 scenario evaluates the content-free diagnostics surface for explicit bounded active-State selection.

It runs the same four-record active State set under two `max_state_records=2` queries. A coffee-related Current Event must report two lexical-match selections; an unrelated weather query must report two deterministic fallback selections. Both runs must report four eligible records, two selected records, two evicted records, and two budget-limit evictions.

The scenario also serializes the diagnostics objects and verifies that known State IDs, keys, semantic values, source Event IDs, and Current Event IDs are absent. This tests the diagnostics contract itself rather than assuming that aggregate metadata is safe because it is labeled diagnostic.

The scenario does not choose a runtime State cap, expose content, or evaluate future cross-layer token budgets.

### `memory_heading_retrieval`

This deterministic #1267 scenario evaluates the first bounded retrieval primitive over crystallized `MEMORY.md` content.

It checks three independent behaviors: a coffee-related query selects the complete Coffee heading section; an unrelated astronomy query selects no optional memory rather than falling back to irrelevant prose; and a relevant section that exceeds the character budget is skipped without truncation while a later complete relevant summary may still fit.

The scenario evaluates retrieval and local budget semantics only. It does not evaluate CognitiveInput projection, durable Markdown identity/Event provenance, State-vs-memory conflict suppression, multilingual semantic retrieval, or actual-model response benefit.

### `memory_cognitive_projection`

This deterministic #1267 scenario evaluates the distinct crystallized-memory projection boundary introduced by PR #1305.

Given one already-selected Coffee `MemoryChunk`, it verifies that:

- exactly one item is projected into `CognitiveInput.memory`;
- the selected memory does not become Event-backed Working Context;
- provider serialization emits the memory content and Markdown location in the separate `memory` array;
- the Markdown location does not appear in any serialized State/Context `sources` array;
- the current Input retains its real current Event ID;
- compiling without retrieved memory produces an empty memory layer.

This evaluates projection and provenance separation only. It does not claim ordinary-turn automatic retrieval, deterministic stale/conflict suppression, durable logical-memory identity, runtime MEMORY budget quality, or actual-model response benefit.

### `ordinary_turn_memory_retrieval`

This deterministic #1267 scenario evaluates the opt-in ordinary-turn retrieval boundary introduced by PR #1307 against isolated Character Packages.

It checks that:

- an explicit `MemoryRetrievalBudget` selects the relevant Coffee heading into the provider's `CognitiveInput.memory`;
- the successful ordinary turn calls the provider exactly once;
- omitting the budget preserves the previous no-retrieval behavior, verified with a CharacterDirectory variant that would fail if `MEMORY.md` were read;
- a deliberate `MEMORY.md` read failure prevents provider generation;
- the failed retrieval still leaves the Current User Event persisted while no Assistant Event or State mutation is created.

This evaluates deterministic runtime wiring and failure ordering only. It does not choose or validate a default runtime budget, expose a client/API retrieval control, solve State-vs-memory conflict suppression, or claim actual-model response benefit. Streaming uses the same retrieval preparation helper and remains directly covered by unit contracts; this native scenario does not duplicate the streaming-delivery matrix.

### `state_memory_authority_filter`

This deterministic #1267 scenario evaluates the explicit-key State-shadow authority boundary introduced by PR #1312.

It verifies that:

- active `residence_location=Fukuoka` suppresses a `Residence Location` MEMORY chunk that says Hokkaido;
- a same-key chunk containing Fukuoka remains available;
- the full active State set still governs authority when `max_state_records=0` removes State from the projected residency set;
- an unrelated `Trip History` heading mentioning Hokkaido remains available instead of being reclassified as a current-state conflict;
- exact lexical matching rejects the false equivalence of active `coffee=likes` with a Coffee chunk saying `dislikes`;
- stale `preferred_beverage=tea` memory is suppressed while separate positive `tea=likes` State and its compatible Tea memory remain preserved.

This scenario measures only the deterministic explicit-key lexical subset implemented today. It does not claim arbitrary natural-language contradiction understanding, historical/current interpretation under ambiguous headings, degree-level conflict handling, non-lexical value comparison, or actual-model quality.

### `targeted_event_retrieval`

This deterministic #1267 scenario evaluates the retrieval-only targeted Event evidence primitive introduced by PR #1316.

It verifies that:

- a coffee-related query selects the relevant persisted coffee message Event and unrelated Event content is not used as fallback;
- an explicitly excluded Current Event is not returned, allowing later projection to avoid duplicating Current Input as Event evidence;
- a relevant Event that exceeds the character budget is skipped whole while a later complete relevant Event may still fit;
- relevance controls admission, while selected results are restored to original Event Journal chronology;
- equal-relevance cutoff prefers the newer occurrence deterministically;
- exact lexical tokens prevent `likes` from matching inside `dislikes`.

This scenario evaluates only the current retrieval primitive over caller-supplied Events. It does not claim Event-evidence `CognitiveInput` projection, provider serialization/instructions, ordinary-turn retrieval wiring, retrieval-scaled filesystem indexing, semantic/multilingual or temporal retrieval, conflict resolution, or actual-model response quality.

Current scenario implementations may use deterministic synthetic providers or direct deterministic core contracts so failures can be attributed to RelayLM-owned boundaries instead of model variance.

## Deferred evaluation work

Still owned by #1247:

- #1267 evidence-backed default MEMORY/State/Event budgeting, broader State-vs-memory authority semantics beyond explicit-key lexical filtering, Event-evidence CognitiveInput/runtime wiring, retrieval-scaled Event Journal access, and cross-layer/token-aware diagnostics as those runtime slices land;
- future privacy/lifecycle evaluation from #1270;
- response/persona and actual local-model quality measurements;
- external benchmark adapters after current benchmark availability/version suitability is re-verified.

External benchmark names and versions are not frozen by the current native report format.

## Principle

> Evaluate the earliest RelayLM-owned boundary that became incorrect, rather than collapsing every failure into generic memory or response quality.
