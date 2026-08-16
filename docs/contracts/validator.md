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
