# Validator Contract

Validator is deterministic authority/state machinery, not a second semantic language model.

For each StateCandidate it may verify or derive:

- schema validity;
- allowed `state_class`;
- key/value policy;
- source Event existence;
- source authority/provenance eligibility;
- scope/disclosure constraints when those policies are enabled;
- existing exact `state_class + key`;
- `set`/`remove` preconditions;
- deterministic normalization and transition outcome.

The current state engine maps an accepted proposal to create/no-op/replace/remove behavior. Richer close/tombstone/forget/restore lifecycle remains deferred to #1270.

The Validator must not re-read natural language and reproduce semantic interpretation that belongs to the cognitive model.

> **LLM understands meaning. Registry defines State grammar. Validator enforces authority. State engine preserves continuity.**

## MVP synchronous authority

M2 applies precision-first checks before current-State mutation:

- state class must be in the bounded registry;
- bounded key-policy exclusions are deterministic; for `user.preference`, the known generic keys `likes`, `dislikes`, and `preference` are rejected;
- every candidate must cite persisted Event IDs;
- ordinary-turn candidates must cite the current user Event as current evidence;
- `user.*` candidates require a cited user-authored Event;
- `set` values must be JSON-serializable with non-finite JSON numbers rejected;
- exact `state_class + key` controls create/no-op/replace/remove transitions.

The key-policy check does not infer semantic aliases or merge alternate spellings. Specific preference subjects/dimensions remain model-chosen grammar under the registry guidance.

## Degree-hint validation

The optional reserved structured value remains a semantic hint inside `value`, not a new authority field:

```json
{
  "semantic": "likes",
  "degree_hint": 0.85
}
```

When a mapping uses either reserved key (`semantic` or `degree_hint`), the Validator requires the exact closed envelope:

- exactly `semantic` and `degree_hint` are present;
- `semantic` is a non-empty string;
- `degree_hint` is numeric but not boolean;
- the number is finite;
- the number is in inclusive range `0.0..1.0`.

Malformed reserved envelopes fail deterministically with `invalid_degree_hint_value`. The Validator does not infer what the degree should be, compare unrelated axes, calibrate values, or use degree as confidence, authority, relevance, salience, or a removal threshold.

The semantic Validator remains slightly broader than the current OpenAI-compatible provider wire: arbitrary non-reserved State values may pass when they are JSON-serializable and satisfy other authority checks, while the provider adapter deliberately exposes only its stricter documented wire grammar.

## Current transition semantics

For one exact `state_class + key`:

```text
set + no existing slot        -> create
set + same value              -> noop
set + changed value           -> replace
remove + existing slot        -> remove
remove + no existing slot     -> noop
invalid / unauthorized        -> reject
```

Current `remove` deletes the slot from the Canonical State current view. It does not create a closed tombstone or materialize `valid_to`, and it never deletes source Event history.

Invalid candidates are rejected while the already-valid user-visible response may still be returned. Incomplete/malformed provider wire output remains an adapter-level fail-closed concern for M3.
