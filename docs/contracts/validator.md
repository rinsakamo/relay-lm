# Validator Contract

Validator is deterministic authority/state machinery, not a second semantic language model.

For each StateCandidate it may verify or derive:

- schema validity;
- allowed `state_class`;
- key/value policy;
- source Event existence;
- source authority/provenance eligibility;
- scope/disclosure constraints;
- existing exact `state_class + key`;
- `set`/`remove` preconditions;
- deterministic normalization.

Then the state engine maps the proposal to create/no-op/replace/reject/close behavior.

The Validator must not re-read natural language and reproduce semantic interpretation that belongs to the cognitive model.

> **LLM understands meaning. Registry defines State grammar. Validator enforces authority. State engine preserves continuity.**

## MVP synchronous authority

M2 applies precision-first checks before current-State mutation:

- state class must be in the bounded registry;
- every candidate must cite persisted Event IDs;
- ordinary-turn candidates must cite the current user Event as current evidence;
- `user.*` candidates require a cited user-authored Event;
- `set` values must be JSON-serializable;
- exact `state_class + key` controls create/no-op/replace/remove transitions.

Invalid candidates are rejected while the already-valid user-visible response may still be returned. Incomplete/malformed provider wire output remains an adapter-level fail-closed concern for M3.
