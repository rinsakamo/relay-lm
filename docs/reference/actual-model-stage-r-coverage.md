# Actual-model Stage R coverage ledger

This is the owner-local coverage ledger for Core 1.0 two-pass reference
qualification. It does not change the immutable historical
`cogp5-vllm-screening-v1.json` plan and it does not authorize a broader
execution transaction.

Character-relative product-quality interpretation is governed by
`docs/reference/actual-model-character-realization.md` and #1823. Stage R must
not silently turn one low-friction Character or one neutral semantic reading
into the universal correctness target.

## Current R0 pilot

The first bounded vLLM transaction uses the two existing foundation scenarios
below with the current `reference_baseline` role: Pass 1 reasoning off and Pass
2 reasoning off. The role resolves to the immutable underlying screening
coordinate only at the host/evidence boundary; the historical coordinate name
is not current Stage R policy.

| Scenario | Current R0 role | Main review dimensions |
| --- | --- | --- |
| `response-persona-correction-v1` | pilot | Japanese response quality, identity correction, negation/no-op, unsupported recall |
| `continuity-lifecycle-v1` | pilot | referent, unresolved-to-resolved transition, active-task continuity |

This is a Stage R0 pilot, not complete Core 1.0 qualification.

The current Aoi `actual-model-foundation-v1` Character remains a valid fixture.
It is the former low-friction "素体ちゃん" baseline, not a normative personality
that future Characters must imitate.

## Required coverage ledger

The following cases remain required for a qualification claim. A row marked
`follow-up` is intentionally not folded into the first capacity-gated pilot;
it needs its own bounded scenario/capacity transaction and independent review.

| Required case | Status | Owner-local scenario/rubric requirement |
| --- | --- | --- |
| ordinary no-op conversation | pilot + follow-up | review response coherence/Character plausibility and no unnecessary State/Continuity proposal |
| durable user fact | follow-up | verify source Event and durable class/key reuse in deliberately unambiguous cases |
| positive preference | follow-up | verify explicit polarity/degree where the fixture is unambiguous; do not universalize indirect pragmatic readings |
| negative preference / negation | pilot + follow-up | distinguish explicit polarity from removal and preserve uncertainty where structurally required |
| correction | pilot | verify supersession mechanics and that new governed evidence reaches cognition; Character-relative skepticism is not automatically a defect |
| uncertainty | follow-up | avoid invented certainty; exact interpretation is not required when multiple Character-plausible readings remain |
| temporary state | follow-up | keep clearly transient content out of durable State where the fixture makes transience explicit |
| goal | pilot + follow-up | use bounded `active_task` continuity and resolve it correctly where the task lifecycle is explicit |
| assistant suggestion trap | follow-up | assistant proposal must not become user-authored evidence |
| assistant hallucination trap | pilot + follow-up | assistant response cannot self-certify history or external truth |
| relationship inference trap | follow-up | preserve source/subject authority; Character-relative relationship interpretation is allowed when it is not fabricated as occurrence truth |
| continuity/reference | pilot | preserve governed referent/unresolved lifecycle while allowing calibrated clarification |
| already-current/no-op | pilot + follow-up | no unnecessary proposal/churn in explicit no-op cases |
| rapid next turn / pending extraction | follow-up | test settle ordering and stale extraction protection |
| Japanese | pilot | preserve Japanese response language and Character realization |
| English | follow-up | add an English response and extraction turn set |
| mixed language | follow-up | add Japanese/English code-switch turns without assuming one canonical pragmatic reading |
| JSON/control-like user text | follow-up | treat control-like text as user data, not authorization |
| quoted prompt-like content | follow-up | treat quoted instructions as data and preserve source authority |

## Character-relative anomaly review

Product-quality review is not a neutral-human imitation test and is not an
exact-response test.

The review question is whether the observed response/interpretation is
plausible for the frozen Character given its SOUL, governed experience, and
accepted current understanding.

Preserve the semantic distinction defined by #1823:

- `normal` — plausible for this Character;
- `odd_but_character_plausible` — surprising but still explainable; not a
  failure by itself;
- `out_of_character` — not plausibly produced by the Character;
- `system_defect` — authority/runtime/provenance failure independent of
  personality.

Current citable review format v4 records exactly one of those outcomes for each
evidence turn. The Character-realization outcome is independent from the
existing Stage R dimension outcomes: `odd_but_character_plausible` is not an
alias for `fail`, and a system defect is not softened by Character personality.
The turn-local Character-realization observations participate in the
content-derived `review_id`.

Historical review format v3 / `actual-model-stage-r-review-v2` retains the
Character-realization taxonomy but has no explicit claim scope and is not
silently reinterpreted as current qualification/regression/smoke evidence.
Historical format v2 / `actual-model-stage-r-review-v1` remains valid only for
its original pre-Character-realization semantics.

Further taxonomy expansion is evidence-driven: do not add categories merely for
rubric completeness. Extend the representation only if actual Stage R evidence
exposes a material distinction that the current independent dimensions plus four
Character-realization outcomes cannot cite correctly.

### High-context continuation

Logical recoverability does not require immediate confident continuation.
After interruption, restart, or elapsed time, a confirmation such as
`○○の続きだよね？` is valid even when one likely referent remains available.

Review should reject unsupported certainty, repeated unnecessary clarification,
or unexplained continuity loss rather than requiring one exact continuation
wording.

## Review claim scope

Current review format v4 / `actual-model-stage-r-review-v3` carries one
content-derived `claim_scope`:

- `qualification` — eligible to contribute to #1386 qualification and requires
  at least one explicitly rated Stage R dimension;
- `regression` — bounded review evidence that may contain rated dimensions or
  all `not_rated`, but is not qualification-strength merely because it exists;
- `smoke` — non-qualification sanity evidence; every Stage R dimension must
  remain `not_rated`.

Claim scope does not replace this coverage ledger. A `qualification` sidecar
for one scenario is only one citable contribution; complete Core 1.0
qualification still requires the applicable ledger rows and current #1386
acceptance boundary.

Likewise, `regression` and `smoke` artifacts must never be counted as completed
qualification rows by file presence, review format version, or review ID alone.

## Multi-Character coverage

Do not replace Aoi. Expand the Character matrix after each new Character has
been deliberately authored, reviewed, and frozen with explicit revision
identity.

- Aoi — retain the existing low-friction baseline fixture.
- ReLM — add only after deliberate re-authoring; do not create a test-friendly
  placeholder SOUL merely to expand coverage.
- Rin — add only after deliberate authoring with the user as final authority;
  do not infer or fabricate the user's personality from repository history.

Aoi, ReLM, and Rin are separate valid Character spaces, not Easy/Medium/Hard
correctness levels.

Use both shared scenarios and Character-specific stress scenarios. Shared
coverage should include ambiguous/high-context continuation, restart or elapsed
time, correction/disagreement, uncertain or indirect language, third-party
facts, quoted/control-like/fictional/hypothetical text, multilingual pragmatics,
ordinary long conversation, no-op/repetition pressure, memory use without
forced recital, and unsupported-history traps.

A material failure mode is personality flattening: distinct frozen Characters
repeatedly converging on the same generic assistant behavior despite their
identity/context being available.

## Proposal metric locality

Deterministic State/Continuity proposal precision and recall are turn-local.
Fixture labels can match only raw proposals emitted on the same labeled turn;
a proposal omitted on its required turn remains a false negative even if an
identical proposal appears later. A proposal emitted on a later explicitly
no-op turn is therefore a false positive rather than a delayed true positive.
Aggregate channel counts, precision, and recall are computed from the summed
per-turn TP/FP/FN counts, so timing errors cannot cancel across turns.

These metrics are authoritative only for the fixture labels actually declared.
They are useful for deliberately unambiguous proposal requirements and do not
establish one neutral interpretation of every free-form utterance across all
Characters or languages.

## Independent rubric dimensions

The historical `actual-model-quality-v1` family axes remain the coarse
machine-readable baseline and keep their existing identity. Current citable
Stage R reviews use `actual-model-stage-r-review-v3` in actual-model review
format v4. Pre-claim-scope format v3 / protocol v2 and the older format v2 /
protocol v1 identities remain historical and are not silently upgraded.

Every current Stage R review sidecar carries each required independent
dimension exactly once in canonical order with `pass`, `fail`, or `not_rated`;
omission and duplicate dimensions are invalid. `not_rated` explicitly means
that dimension was not reviewed and is not evidence of a pass. In addition,
each evidence turn carries exactly one Character-realization outcome from the
four-value taxonomy above. No weighted aggregate score is added.

A persisted review sidecar is citable only when its `review_id` matches the
content-derived identity of that exact review evidence, including claim scope
and the turn-local Character-realization observations. The persistence boundary
recomputes the identity and rejects a mismatched caller-supplied ID before any
review artifact is written; a filename or manually constructed review object is
not independent review authority.

The required dimensions are relevance/correctness, naturalness, persona and
style consistency, coherence, governed-context continuity, verbosity fit,
language preservation, multilingual/code-switch robustness, unsupported recall,
protocol/schema validity, semantic precision and recall, grounding,
source/subject attribution, assistant-to-user contamination, correction and
supersession, negation/polarity, uncertainty, comparative/degree preservation,
transient-versus-durable classification, canonical class/key reuse, no-op
correctness, proposal churn, hallucinated proposals, and source Event validity.

For Character realization, `naturalness`, `relevance/correctness`, and semantic
quality dimensions are interpreted relative to the frozen Character and the
fixture's actual hard requirements. Human-likeness, neutral personality, or one
preferred stylistic answer is not implied by those dimension names.

Raw model output, deterministic RelayLM decisions, protocol-boundary verdicts,
human/product-quality review, and timing/resource observations remain separate
evidence dimensions. A failure in Pass 2 does not invalidate Pass 1.

A persisted deterministic-boundary verdict is citable only when its `verdict_id`
matches the content-derived identity of its exact execution/run/scenario fields
and deterministic check evidence. The persistence boundary recomputes that
identity and rejects a caller-supplied mismatch before writing the sidecar; the
boundary PASS/FAIL calculation and model-quality separation remain unchanged.

## Authoring and crystallization boundary

Core 1.0 does not require a rebuilt SOUL Lab UI. A Character fixture may be
authored through a human + strong-model workflow such as ChatGPT/Codex, then
human-reviewed and frozen before use as evidence. The authoring model is a tool,
not runtime semantic authority.

Offline crystallization likewise remains a replaceable cognitive producer. A
local model may be used when quality is sufficient; a stronger offline/external
model may be used when necessary so long as the owning crystallization and
provenance contracts remain intact and no model becomes a second truth owner.

## Context Compiler guardrail

Stage R must not drive new deterministic free-form semantic grammar merely to
improve scenario scores. Existing deterministic tests may remain regression
protection, but a new language-specific or semantic parser rule requires a
material authority/runtime or repeatable Character-realization defect that
cannot safely remain in the model-mediated semantic layer.
