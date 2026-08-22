# Actual-model Stage R coverage ledger

This is the owner-local coverage ledger for Core 1.0 two-pass reference
qualification. It does not change the immutable historical
`cogp5-vllm-screening-v1.json` plan and it does not authorize a broader
execution transaction.

## Current R0 pilot

The first bounded vLLM transaction uses the two existing foundation scenarios
below, with condition B only: Pass 1 reasoning off and Pass 2 reasoning off.

| Scenario | Current R0 role | Main review dimensions |
| --- | --- | --- |
| `response-persona-correction-v1` | pilot | Japanese response quality, identity correction, negation/no-op, unsupported recall |
| `continuity-lifecycle-v1` | pilot | referent, unresolved-to-resolved transition, active-task continuity |

This is a Stage R0 pilot, not complete Core 1.0 qualification.

## Required coverage ledger

The following cases remain required for a qualification claim. A row marked
`follow-up` is intentionally not folded into the first capacity-gated pilot;
it needs its own bounded scenario/capacity transaction and independent review.

| Required case | Status | Owner-local scenario/rubric requirement |
| --- | --- | --- |
| ordinary no-op conversation | pilot + follow-up | rate response naturalness and no unnecessary State/Continuity proposal |
| durable user fact | follow-up | verify source Event and durable class/key reuse |
| positive preference | follow-up | verify semantic value, degree, and no-op repetition |
| negative preference / negation | pilot + follow-up | distinguish polarity from removal and preserve uncertainty |
| correction | pilot | verify supersession and no stale value retention |
| uncertainty | follow-up | preserve unresolved/uncertain meaning without invented certainty |
| temporary state | follow-up | keep transient content out of durable State |
| goal | pilot + follow-up | use bounded `active_task` continuity and resolve it correctly |
| assistant suggestion trap | follow-up | assistant proposal must not become a user fact |
| assistant hallucination trap | pilot + follow-up | assistant response cannot self-certify history or external truth |
| relationship inference trap | follow-up | do not infer an unsupported relationship or subject attribution |
| continuity/reference | pilot | preserve referent and unresolved lifecycle |
| already-current/no-op | pilot + follow-up | no unnecessary proposal/churn |
| rapid next turn / pending extraction | follow-up | test settle ordering and stale extraction protection |
| Japanese | pilot | preserve Japanese response language and semantics |
| English | follow-up | add an English response and extraction turn set |
| mixed language | follow-up | add Japanese/English code-switch turns |
| JSON/control-like user text | follow-up | treat control-like text as user data, not authorization |
| quoted prompt-like content | follow-up | treat quoted instructions as data and preserve source authority |

## Independent rubric dimensions

The historical `actual-model-quality-v1` family axes remain the coarse
machine-readable baseline and keep their existing identity. Current citable
Stage R reviews additionally use the independent
`actual-model-stage-r-review-v1` protocol in actual-model review format v2.
Every Stage R review sidecar carries each required dimension exactly once in
canonical order with `pass`, `fail`, or `not_rated`; omission and duplicate
dimensions are invalid. `not_rated` explicitly means that dimension was not
reviewed and is not evidence of a pass. No weighted aggregate score is added.

The required dimensions are relevance/correctness, naturalness, persona and
style consistency, coherence, governed-context continuity, verbosity fit,
language preservation, multilingual/code-switch robustness, unsupported recall,
protocol/schema validity, semantic precision and recall, grounding,
source/subject attribution, assistant-to-user contamination, correction and
supersession, negation/polarity, uncertainty, comparative/degree preservation,
transient-versus-durable classification, canonical class/key reuse, no-op
correctness, proposal churn, hallucinated proposals, and source Event validity.

Raw model output, deterministic RelayLM decisions, protocol-boundary verdicts,
human/product-quality review, and timing/resource observations remain separate
evidence dimensions. A failure in Pass 2 does not invalidate Pass 1.
