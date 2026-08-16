# StateCandidate Contract

MVP candidate fields:

```text
state_class
key
op = set | remove
value      # semantic requirement for set only
sources
```

## `set`

Proposes that the named State should currently exist with the supplied value. Create/update/no-op/supersede decisions remain runtime-owned.

## `remove`

Proposes that an existing State should no longer be active/current. It does not delete Event history.

Use `remove` only for clear revocation, cancellation, denial, or correction. Do not remove for mere weakening, uncertainty, hesitation, or temporary variation.

## Sources

`sources` contains real runtime-issued Event IDs. The model must never invent canonical Event IDs.

## MVP state classes

```text
user.identity
user.fact
user.preference
user.goal
user.condition
user.experience
self.belief
self.goal
self.condition
relationship.state
relationship.commitment
```

Each class presented to the model must have a short semantic definition.

When an exact relevant State exists, reuse its exact `state_class + key`; the synchronous Validator is not a semantic alias-merging LLM.

The model does not generate state IDs, confidence, validation status, validity intervals, supersedes IDs, lifecycle decisions, privacy/delete decisions, or commit status.
