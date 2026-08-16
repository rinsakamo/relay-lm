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

## `user.preference` key grammar

For `user.preference`, `key` names the specific preference subject or dimension and `value` carries the relation or current dimension value.

Canonical examples:

```text
tea = likes
coffee = likes
preferred_beverage = coffee
spicy_food = dislikes
```

Generic predicate keys such as `likes`, `dislikes`, and `preference` are invalid because they collapse multiple subjects into one State slot.

Comparative preference preserves its stated direction and degree. For example, preferring coffee over tea does not by itself mean tea became disliked and does not justify removing `tea = likes` without explicit revocation, denial, or correction.

If the weaker subject already has an accepted positive preference State, that exact State remains current unless the current Input explicitly denies or revokes it. The cognitive model should represent the stronger subject and any supported category-level preference as separate specific keys instead of treating comparison as replacement. For example, an existing `tea = likes` plus a new statement that coffee is preferred over tea may yield `coffee = likes` and `preferred_beverage = coffee` while preserving `tea = likes`.

This retention rule is cognitive grammar, not Validator natural-language interpretation. The Validator continues to apply candidates deterministically and still accepts an explicit `remove` proposal when the model identifies genuine revocation from current evidence.

The model does not generate state IDs, confidence, validation status, validity intervals, supersedes IDs, lifecycle decisions, privacy/delete decisions, or commit status.
