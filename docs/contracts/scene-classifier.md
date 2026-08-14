---
relaylm_doc_type: contract
relaylm_authority: current_relayscn_scene_classifier_and_scene_wiki_match_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: scene
relaylm_update_trigger:
  - RelaySCN scene-classifier schema, scene enum, source admission, or policy-open semantics change
  - scene-wiki structured match schema or ranking changes
  - scene classifier public diagnostics change
  - RelaySCN classifier precedence or restrictive-admission behavior changes
  - scene-wiki definition matching begins to parse or mutate source pages
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - shared Analyzer Candidate Governance common fields or thresholds
  - full RelaySCN scene-state or scene-policy schema and policy table
  - Character Workspace parser, compiler, UI, or scene-wiki source mutation
  - RelayEMO affect/expression or scene-hint ownership
  - RelayMEM reader selection, retrieval ranking, evidence eligibility, or mutation
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/scene/scene-model.md
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/emotion/affect-modulation.md
relaylm_related_contracts:
  - analyzer-candidate.md
  - relayemo-scene-hint.md
relaylm_verified_by:
  - ../../scripts/relaylm_acg6_scene_wiki_classifier_smoke.py
  - ../../scripts/relaylm_p0_pipeline_ordering_smoke.py
  - ../../scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelaySCN classifier and scene-policy maintainers
  - scene-wiki and Character Workspace integration maintainers
  - RelayMEM, RelayCTX, analyzer-governance, privacy, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelaySCN Scene Classifier Contract

## Authority summary

This contract owns the exact current **structured scene-classifier candidate**, **structured scene-wiki matcher**, and the bounded **RelaySCN admission rule** that decides whether classifier evidence remains restrictive or may become an authoritative scene-state source.

The current implementation anchors are:

```text
relaylm/scene_classifier.py
relaylm/scene_wiki_matcher.py
relaylm/relayscn.py
```

The stable responsibility chain is:

```text
request-local payload / optional structured classifier candidate
  + optional already-structured scene-wiki definitions
  -> scene classifier candidate
  -> Analyzer Candidate Governance
  -> content-free scene-wiki match evidence
  -> RelaySCN source/admission decision
  -> normalized RelaySCN scene state/policy
```

The classifier and matcher are candidate/evidence producers. They do not become scene authority merely because they return a scene label or a strong wiki match.

## Current classifier schema

The exact current classifier schema identifier is:

```text
relaylm.scene_classifier_candidate.v0
```

The exact analyzer kind is:

```text
scene_policy_candidate
```

The current classifier result exposes:

```text
schema_version
analyzer_kind
source
source_language
candidate_scene_type
candidate_scene_id
candidate_scene_family
matched_scene_wiki_id
match_strength
confidence
stability
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
can_open_runtime_policy
content_free
reason_ids
validation_errors
scene_wiki_match
governance
```

The artifact is content-free. Raw user text, scene Markdown, free-form rationale, protected source bodies, filesystem paths, queue payloads, or arbitrary unvalidated labels are not public classifier fields.

## Scene type enum

The current classifier and scene-wiki scene-type vocabulary is exactly:

```text
unknown
casual_chat
implementation_work
review_work
design_talk
formal_document
medical_or_safety
system_ops
recovery
vtuber_roleplay
memory_management
character_workspace
```

The current restrictive scene-type set is exactly:

```text
medical_or_safety
formal_document
recovery
```

An unrecognized scene type normalizes to:

```text
unknown
```

and contributes:

```text
unrecognized_scene_type
```

as bounded validation/reason evidence.

Free-form scene labels never become new scene enum values.

## Safe token boundary

Classifier scene IDs, scene families, wiki IDs, aliases, and similar structured tokens are bounded by the current token grammar:

```text
^[a-z0-9][a-z0-9_-]{0,63}$
```

Inputs outside that shape normalize to:

```text
unknown
```

A private or free-form candidate ID that does not resolve through a safe structured wiki match is not exposed as `candidate_scene_id` or `matched_scene_wiki_id`.

## Match-strength vocabulary

The exact current match-strength vocabulary is:

```text
none
weak
medium
strong
```

Unknown match-strength values normalize to `none` in public projections.

## Candidate construction modes

`build_scene_classifier_candidate(...)` accepts:

```text
candidate
payload
scene_wiki_definitions
```

When `candidate` is not a mapping, the classifier uses its bounded current-message heuristic path.

When `candidate` is a mapping, the classifier normalizes only bounded structured fields and subjects source/authority claims to shared Analyzer Candidate Governance.

Neither mode is authority merely because a candidate exists.

## Heuristic classifier defaults

When no structured candidate is supplied, current defaults are:

```text
source = heuristic
source_language = und
is_estimate = true
source_authoritative request = false
```

The heuristic candidate sets `candidate_applied` only for restrictive scene types and requests `policy_authority=restrictive` only for those restrictive types.

Other heuristic scene types start with non-opening policy authority.

The classifier records:

```text
heuristic_scene_candidate
```

as bounded reason evidence.

## Current heuristic scene estimation

The current heuristic reads the latest user text from the request payload and emits these responsibility-level outcomes:

```text
empty
  -> unknown

medical / safety / legal class markers
  -> medical_or_safety

formal / report / document class markers
  -> formal_document

review / PR / diff class markers
  -> review_work

implementation / code / repo / bug / fix class markers
  -> implementation_work

Git / GitHub / remote / branch / environment class markers
  -> system_ops

design / architecture / policy / MVP class markers
  -> design_talk

VTuber / Live2D / TTS / roleplay class markers
  -> vtuber_roleplay

confusion / context-repair class markers
  -> recovery

otherwise
  -> casual_chat
```

Exact lexical marker literals remain implementation detail. The contract owns the bounded output classes, source authority, and conservative direction rather than promising a permanent keyword list.

## Heuristic confidence and stability

The current estimator supplies bounded confidence/stability pairs. Current branch values include:

```text
unknown/empty          -> 0.35 / 0.35
medical_or_safety      -> 0.82 / 0.78
formal_document        -> 0.80 / 0.76
review_work            -> 0.78 / 0.72
implementation_work    -> 0.78 / 0.72
system_ops             -> 0.76 / 0.70
design_talk            -> 0.74 / 0.70
vtuber_roleplay        -> 0.74 / 0.70
recovery               -> 0.82 / 0.78
casual_chat            -> 0.62 / 0.60
```

These are candidate certainty values, not source provenance or scene admission permission.

## Structured candidate source normalization

Structured candidates may request:

```text
source
source_authoritative
candidate_applied
policy_authority
restrictive_only
confidence
stability
is_estimate
```

The classifier does not accept those claims blindly.

A source is authoritative only when both are true:

```text
source belongs to shared trusted source classes
AND
requested source_authoritative == true
```

Non-authoritative source classes remain non-authoritative regardless of candidate confidence.

## Non-authoritative source rule

For a source in the shared non-authoritative source-class set, current classifier behavior is conservative:

```text
source_authoritative = false
restrictive_only = true
```

If the candidate scene is one of the restrictive scene types, the classifier may retain or strengthen:

```text
policy_authority = restrictive
candidate_applied = true
```

This permits conservative scene restriction without granting broader scene authority.

A non-authoritative source that requests broader/open authority is rejected and records bounded evidence including:

```text
policy_authority_not_permitted
classifier_policy_open_rejected
```

The candidate cannot open runtime policy.

## Trusted-source bounded-open rule

A trusted/confirmed source may open bounded runtime scene policy only after all relevant current gates agree.

Current successful evidence requires the normalized candidate to carry a trusted source, source-authoritative true, candidate-applied true, a non-unknown scene type, and policy authority eligible under shared Analyzer Candidate Governance.

The ACG-6 smoke verifies a current confirmed path using:

```text
source = confirmed_user_action
source_authoritative = true
candidate_applied = true
policy_authority = bounded
restrictive_only = false
```

with adequate confidence/stability.

That candidate may report:

```text
can_open_runtime_policy = true
```

and RelaySCN may then adopt the confirmed source as scene-state authority.

This does not create memory-reader or mutation authority outside the resulting RelaySCN policy.

## Unknown-scene fail closed

When the normalized classifier scene type is `unknown`, current classifier behavior forces:

```text
candidate_applied = false
restrictive_only = true
```

and appends:

```text
unknown_scene_fail_closed
```

Policy authority cannot become a permissive runtime-open path from an unknown scene.

## Classifier reason vocabulary

The classifier's public reason projection is bounded to the current safe reason identifiers, including:

```text
classifier_candidate_non_authoritative
classifier_candidate_restrictive_only
classifier_policy_open_rejected
heuristic_scene_candidate
scene_wiki_candidate_match
trusted_scene_candidate
unrecognized_scene_type
unknown_scene_fail_closed
```

Raw candidate strings are not converted into public reason IDs.

## Scene-wiki matcher schema

The exact current scene-wiki match schema identifier is:

```text
relaylm.scene_wiki_match.v0
```

`match_scene_wiki_definition(...)` consumes already-structured scene definitions and returns:

```text
schema_version
content_free
candidate_scene_type
candidate_scene_family
matched_scene_wiki_id
matched_scene_type
matched_scene_family
match_strength
scene_wiki_authority
safe_definition_count
enabled_definition_count
reason_ids
```

The matcher is read-only and content-free.

It does not parse Character Workspace Markdown and does not expose definition body text.

## Accepted structured scene-wiki authorities

The current matcher recognizes these structured authority tokens:

```text
explicit_scene_definition
trusted_explicit
trusted_route
confirmed_user_action
```

An unrecognized authority token normalizes to:

```text
unknown
```

A recognized definition authority is metadata about the definition; a match does not by itself make an untrusted classifier source authoritative.

## Definition eligibility

The matcher examines only mapping definitions.

A mapping counts toward `safe_definition_count` before later structural filtering.

A definition with:

```text
enabled == false
```

is skipped.

A definition can participate in matching only when its normalized `scene_id` and `scene_type` are both non-unknown.

Participating definitions increment `enabled_definition_count`.

The matcher does not mutate the supplied definitions.

## Alias handling

Aliases may be supplied as a string or sequence.

Each alias passes through the safe token grammar, and invalid aliases are discarded.

Aliases are used only for structured matching. Alias text does not become executable scene prose or policy language.

## Match ranking

For each eligible definition, current matching is:

```text
candidate id matches scene_id or alias
  + candidate type is unknown or equals definition type
    -> strong, rank 3

candidate id matches scene_id or alias
  + candidate type conflicts with definition type
    -> medium, rank 2

candidate type equals definition type
  + candidate family is known and equals definition family
    -> medium, rank 2

candidate type equals definition type
    -> weak, rank 1

otherwise
    -> none, rank 0
```

The first candidate reaching a strictly greater rank than the current best becomes the best match. Equal-rank later definitions do not replace an earlier best match.

## No-match result

When no eligible definition matches, the matcher returns:

```text
matched_scene_wiki_id = null
matched_scene_type = unknown
matched_scene_family = unknown
match_strength = none
scene_wiki_authority = unknown
```

If the input candidate scene type is unknown, matcher reason evidence includes:

```text
unknown_candidate_scene_type
```

A non-none match contributes:

```text
scene_wiki_candidate_match
```

## Match effect on classifier confidence

A medium or strong scene-wiki match may raise candidate confidence/stability floors.

Current floors are:

```text
strong
  confidence >= 0.82
  stability  >= 0.78

medium
  confidence >= 0.72
  stability  >= 0.70
```

A weak match does not apply those floors.

Raising candidate confidence does not change an untrusted source into a trusted source.

## Match effect on scene type

For a medium or strong match:

- the matched scene family may become the exposed candidate scene family;
- the matched wiki ID may become the exposed `candidate_scene_id` / `matched_scene_wiki_id`;
- when the incoming scene type is unknown and the matched scene type is known, the classifier may adopt the matched type.

The `unrecognized_scene_type` validation/reason may be removed for that adopted type **only when the classifier source is already authoritative**.

Wiki matching therefore helps normalize a trusted structured candidate without upgrading an untrusted candidate's provenance.

## Public scene-wiki match projection

`scene_wiki_match_public_projection(...)` exposes only:

```text
schema_version
content_free
candidate_scene_type
candidate_scene_family
matched_scene_wiki_id
match_strength
safe_definition_count
enabled_definition_count
reason_ids
```

It does not expose definition body text, aliases, raw source data, or free-form authority text.

## Classifier public projection

`scene_classifier_public_projection(...)` exposes current content-free fields:

```text
schema_version
candidate_present
candidate_scene_type
candidate_scene_family
matched_scene_wiki_id
match_strength
confidence_bucket
stability_bucket
source_class
source_authoritative
policy_authority
restrictive_only
candidate_applied
can_open_runtime_policy
reason_ids
validation_error_ids
content_free
```

The public projection independently re-normalizes bounded enum/token/count values rather than copying arbitrary candidate strings.

## RelaySCN explicit-state precedence

`build_relayscn_scene_policy_artifact(...)` first extracts explicit scene-state input.

If a usable explicit scene state is present, current behavior is:

```text
scene_state = explicit scene state
scene_state_source = request_metadata
```

The classifier candidate is still built for diagnostics, but it does not override explicit state.

ACG-6 verification requires an explicit `review_work` request metadata scene to remain `review_work` even when an LLM candidate proposes `medical_or_safety` with high confidence.

## Classifier-derived RelaySCN source

When no explicit scene state is available, RelaySCN derives a provisional scene state from the classifier candidate.

Its source becomes authoritative only when:

```text
classifier_candidate.can_open_runtime_policy == true
AND
classifier_candidate.source is one of:
  request_metadata
  trusted_explicit
  trusted_route
  trusted_tool_signal
  confirmed_user_action
```

Otherwise RelaySCN labels the derived source:

```text
heuristic
```

A strong wiki match alone does not satisfy this source transition.

## Restrictive heuristic admission

RelaySCN permits an important one-way conservative exception.

A heuristic/non-authoritative scene state whose scene type is one of:

```text
medical_or_safety
formal_document
recovery
```

may select the corresponding restrictive scene policy.

RelaySCN labels that policy:

```text
policy_authority = heuristic_restrictive
```

This may narrow memory scope, block updates, require confirmation, or otherwise close behavior.

It does not grant broad/open retrieval authority.

## Non-restrictive heuristic admission

A non-authoritative heuristic scene outside the restrictive set does **not** select its normal permissive scene policy.

RelaySCN instead uses the fail-closed unknown policy and labels:

```text
policy_authority = heuristic_non_authoritative
```

Current fail-closed direction includes:

```text
relaymem_retrieval_scope = current_context_only
relaymem_update_gate = blocked
relaysoul_update_gate = blocked
user_confirmation_required = true
```

The full RelaySCN scene-policy table is separately owned; these fields are stated here only because they prove the classifier admission boundary.

## Confirmed/trusted admission

When a classifier candidate passes the bounded runtime-open gate with a trusted/confirmed source, RelaySCN marks its normalized scene state authoritative and may select the ordinary policy for that accepted scene type.

ACG-6 verification demonstrates:

```text
confirmed_user_action + bounded + valid review_work
  -> can_open_runtime_policy true
  -> scene_state_source confirmed_user_action
  -> source_authoritative true
  -> review_work policy may use current_project_only retrieval scope
```

The downstream memory reader and memory mutation gates remain separate authorities.

## Strong wiki match remains subordinate to source authority

The smoke verifies an LLM candidate with a strong scene-wiki match.

Even though:

```text
matched_scene_wiki_id = repo_review
match_strength = strong
```

an `llm_candidate` source remains non-authoritative, and RelaySCN keeps fail-closed non-authoritative policy rather than opening `review_work` retrieval policy.

This is a core provenance invariant:

```text
match quality != source authority
```

## Trusted ID-only normalization

The current structured matcher permits a trusted candidate to supply a safe scene ID/alias without a scene type.

When a trusted, authoritative, applied, bounded candidate matches a structured definition strongly, the matched scene type/family/ID may complete the candidate.

ACG-6 verification demonstrates:

```text
confirmed_user_action
+ candidate_scene_id = code_review
+ strong match to repo_review/review_work
+ bounded authority
  -> candidate_scene_type = review_work
  -> candidate_scene_id = repo_review
  -> can_open_runtime_policy = true
```

This behavior depends on the source already satisfying trusted authority requirements; it is not an ID-based authority minting shortcut.

## Scene-wiki source immutability

The matcher does not modify the passed definition sequence or its mappings.

ACG-6 smoke compares the definitions before and after matching and requires byte/structure-equivalent values.

No current ACG-6 path:

```text
creates a scene-wiki page
edits a scene-wiki page
parses scene Markdown into executable policy
writes Character Workspace source
promotes arbitrary body text into an alias or scene ID
```

## Content-free diagnostics invariant

Current classifier/matcher/public projections are designed so these values do not appear in public diagnostics merely because they were present in inputs:

```text
raw user text
raw assistant text
scene Markdown
scene-wiki body text
relationship or memory bodies
free-form classifier rationale
private scene-family strings that fail safe-token normalization
private candidate IDs that do not resolve through a safe match
protected source bodies
filesystem paths
queue payloads
```

The classifier may inspect request-local text to generate a heuristic candidate, but the resulting public artifact contains only bounded labels, buckets, counts, booleans, safe IDs, and reason/error IDs.

## RelayEMO separation

RelaySCN's classifier boundary does not accept RelayEMO as a scene authority fallback.

The current RelaySCN builder signature does not take `relayemo_artifact`.

RelayEMO's separate `scene_hint_candidate` remains governed by the RelayEMO Scene Hint Non-Authority Contract and cannot restore same-turn scene ownership to RelayEMO.

## Failure direction

Current failures close conservatively:

```text
free-form/unrecognized scene label
  -> unknown
  -> validation reason
  -> no runtime-open policy

untrusted source requests broad/open authority
  -> authority rejected
  -> restrictive/non-opening candidate

unknown scene
  -> candidate_applied false
  -> restrictive_only true

untrusted strong wiki match
  -> confidence/stability may increase
  -> source remains untrusted
  -> RelaySCN remains heuristic/non-authoritative

restrictive heuristic scene
  -> corresponding restrictive policy may apply
  -> update/open permissions do not expand
```

There is no fallback from classifier failure to RelayEMO scene authority or arbitrary scene-wiki body interpretation.

## Stable invariants

- `relaylm.scene_classifier_candidate.v0` is the current classifier schema.
- `relaylm.scene_wiki_match.v0` is the current matcher schema.
- `scene_policy_candidate` is the current classifier analyzer kind.
- Scene types and match strengths use bounded English enums.
- Free-form scene labels normalize to `unknown` without public raw-label leakage.
- Scene IDs/families/aliases are bounded safe tokens.
- Matcher input is already-structured data; Markdown parsing is out of scope.
- Matcher operation is read-only and content-free.
- Match quality does not create source authority.
- Non-authoritative sources may restrict but cannot open broader scene policy.
- Explicit request scene state precedes classifier candidates.
- Trusted/confirmed classifier candidates open bounded runtime policy only through Analyzer Candidate Governance.
- Non-restrictive heuristic classifier output fails toward the RelaySCN conservative policy.
- Restrictive heuristic scene types may narrow behavior without becoming broad scene authority.
- RelaySCN remains the sole normalized scene-state/policy owner.
- RelayEMO scene hints do not become classifier/source fallback authority.
- ACG-6 does not mutate scene-wiki or Character Workspace sources.

## Non-goals

This contract does not define:

- the full RelaySCN scene-state or scene-policy exact schema/table;
- a live LLM scene-classifier call;
- scene-wiki Markdown parsing;
- Character Workspace parser/compiler/UI behavior;
- scene-wiki page generation or mutation;
- RelayMEM reader selection, ranking, evidence eligibility, or mutation;
- RelayEMO affect/expression behavior beyond authority separation;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [RelaySCN Scene Model](../architecture/scene/scene-model.md)
- [Analyzer Candidate Governance Contract](analyzer-candidate.md)
- [RelayEMO Scene Hint Non-Authority Contract](relayemo-scene-hint.md)
