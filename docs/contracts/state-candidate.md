# StateCandidate Contract

MVP candidate fields:

```text
state_class
key
op = set | remove
value      # semantic requirement for set only
sources
```

The top-level StateCandidate shape is intentionally small and frozen. Semantic refinements such as optional degree hints live inside `value`; they do not become new authority fields.

## `set`

Proposes that the named State should currently exist with the supplied value. Create/update/no-op/supersede decisions remain runtime-owned.

A plain string value remains the normal form:

```text
tea = likes
residence_location = Fukuoka
```

When the current Input materially expresses a useful comparative or intensity relation, `value` may instead use the reserved structured degree-hint form:

```json
{
  "semantic": "likes",
  "degree_hint": 0.85
}
```

The object is optional. Existing string values remain valid and should not be migrated merely for uniformity.

### `degree_hint`

`degree_hint` is a soft semantic reconstruction hint in the inclusive range `0.0..1.0`.

It is useful primarily as a relative/intensity cue on a compatible semantic axis. For example:

```text
tea     = { semantic: likes, degree_hint: 0.65 }
coffee  = { semantic: likes, degree_hint: 0.85 }
```

Both States still say that the user likes the item; the hint preserves that the coffee preference is currently stronger on that comparison axis.

`degree_hint` is **not**:

- confidence or probability;
- evidence strength;
- authority;
- retrieval relevance;
- salience or importance;
- a lifecycle or removal threshold;
- a globally calibrated score across unrelated State dimensions.

Degree values should not be compared across incompatible semantic axes. The cognitive model should avoid false precision and should not re-estimate an already adequate accepted hint unless the current Input materially changes the expressed strength or comparison.

The deterministic Validator checks only the reserved envelope shape and numeric bounds. It does not infer, calibrate, normalize, or semantically reinterpret the degree.

## `remove`

Proposes that an existing State should no longer be active/current. It does not delete Event history.

Use `remove` only for clear revocation, cancellation, denial, or correction. Do not remove for mere weakening, uncertainty, hesitation, temporary variation, or a lower degree hint.

A degree change therefore remains a `set` replacement when the State still applies:

```text
likes@0.75 → likes@0.60
```

is weakening, not removal.

## Sources

`sources` contains real runtime-issued Event IDs. The model must never invent canonical Event IDs.

Degree never upgrades provenance or authority. A user State still requires valid user-origin evidence regardless of how high its degree hint is.

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

### Epistemic strength and durability

Preference intensity and epistemic certainty are different semantic axes. RelayLM must not encode uncertainty about whether a preference is established by lowering `degree_hint`; `degree_hint` remains preference intensity only.

The cognitive model should preserve the strength of the user's evidence when deciding whether a durable preference State is justified:

```text
tentative: "might prefer tea; not sure"
  -> no durable preference State is required

resolved: "prefer tea to coffee"
  -> a durable preference State may be proposed

temporary: "not in the mood for tea today; usual preference unchanged"
  -> do not remove the established durable preference
```

Tentative, hedged, speculative, or explicitly uncertain preference language does not by itself establish a durable preference. Leaving the evidence uncommitted is correct when that is more faithful than silently upgrading it into certainty.

A later sufficiently resolved statement may establish or update the durable preference using the ordinary `set` path. Conversely, a transient mood or situational variation does not revoke durable preference unless the user actually denies, corrects, cancels, or otherwise terminates it.

This is model-facing semantic grammar, not Validator natural-language interpretation. The deterministic Validator remains language-agnostic and accepts or rejects the typed proposal according to structural/source/current-State rules; it does not inspect hedging words or repair model semantics.

Comparative preference preserves its stated direction and degree. For example, preferring coffee over tea does not by itself mean tea became disliked and does not justify removing `tea = likes` without explicit revocation, denial, or correction.

If the weaker subject already has an accepted positive preference State, that exact State remains current unless the current Input explicitly denies or revokes it. The cognitive model should represent the stronger subject and any supported category-level preference as separate specific keys instead of treating comparison as replacement. For example, an existing `tea = likes` plus a new statement that coffee is preferred over tea may yield `coffee = likes` or structured degree-hint values while preserving `tea = likes`.

This retention rule is cognitive grammar, not Validator natural-language interpretation. The Validator continues to apply candidates deterministically and still accepts an explicit `remove` proposal when the model identifies genuine revocation from current evidence.

The model does not generate state IDs, confidence, validation status, validity intervals, supersedes IDs, lifecycle decisions, privacy/delete decisions, or commit status.

## Deferred semantic hints

Temporal and salience hints remain separate deferred concerns. They must not be smuggled into `degree_hint`, because time, importance, and intensity are distinct dimensions.
