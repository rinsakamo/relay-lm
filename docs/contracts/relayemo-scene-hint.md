---
relaylm_doc_type: contract
relaylm_authority: current_relayemo_scene_hint_non_authority_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: emotion
relaylm_update_trigger:
  - RelayEMO scene-hint schema or scene-hint enum changes
  - RelayEMO scene-hint governance or public projection changes
  - deprecated RelayEMO scene-state compatibility fields change
  - RelaySCN or RelayMEM begins or ceases consuming RelayEMO scene artifacts
  - structured affect-probe scene-candidate handling changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - full RelayEMO affect-estimate, assistant-state, session-state, marker, or expression schema
  - shared Analyzer Candidate Governance fields or thresholds
  - RelaySCN normalized scene-state or scene-policy schema
  - RelayMEM retrieval authority, ranking, eligibility, or mutation
  - ACG-6 scene-wiki classifier behavior
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/emotion/affect-modulation.md
  - ../architecture/scene/scene-model.md
  - ../architecture/acg5_relayemo_scene_cleanup.md
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/pipeline-responsibilities.md
relaylm_related_contracts:
  - analyzer-candidate.md
relaylm_verified_by:
  - ../../scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
  - ../../scripts/relaylm_p0_pipeline_ordering_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayEMO and RelaySCN maintainers
  - RelayMEM retrieval and request-pipeline maintainers
  - analyzer-governance, privacy, safety, expression, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelayEMO Scene Hint Non-Authority Contract

## Authority summary

This contract owns the exact current boundary by which RelayEMO may produce a scene-like **hint candidate** while remaining non-authoritative for normalized scene state and policy.

The current implementation is anchored in:

```text
relaylm/relayemo.py
```

The permanent responsibility split is:

```text
RelaySCN
  -> owns normalized scene_state and scene_policy
  -> supplies scene/policy constraints to downstream components

RelayEMO
  -> owns affect/expression estimation and modulation
  -> may emit a content-free scene_hint_candidate
  -> must not feed that hint back into RelaySCN as scene authority
  -> must not feed it into RelayMEM as retrieval/update policy
```

The scene hint is an Analyzer Candidate Governance artifact for conservative expression-side interpretation only. It cannot open runtime policy, choose a memory reader, widen retrieval, create durable scene truth, or restore the historical RelayEMO-to-RelaySCN fallback.

## Current implementation anchors

The current scene-hint producer is:

```text
relaylm.relayemo.build_scene_hint_candidate(...)
```

Current heuristic scene-hint selection is:

```text
relaylm.relayemo.infer_scene_hint_type(...)
```

Current RelayEMO request-local assembly occurs through:

```text
relaylm.relayemo.run_relayemo(...)
relaylm.relayemo.run_relayemo_stage(...)
```

Structured affect-probe output also reuses the same scene-hint builder through:

```text
relaylm.relayemo.parse_llm_affect_probe_output(...)
```

The exact ACG-5 integration and no-backflow invariants are verified by:

```text
scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
```

## Scene-hint type vocabulary

The current accepted `SCENE_HINT_TYPES` set is exactly:

```text
casual_chat
design_talk
implementation_work
review_work
formal_document
medical_or_safety
vtuber_roleplay
unknown
```

This vocabulary belongs to RelayEMO's hint boundary only. It is not a second normalized RelaySCN scene schema.

A `scene_hint_type` outside this set normalizes to:

```text
unknown
```

and contributes the bounded validation error:

```text
unknown_enum_value
```

Unknown input is not echoed into the public candidate.

## Heuristic hint selection

`infer_scene_hint_type(text)` currently applies a bounded heuristic selection in this order:

```text
仕様 | 設計 | design
  -> design_talk

実装 | コード | fix | bug | implement
  -> implementation_work

レビュー | review | pr
  -> review_work

医療 | 安全 | safety | medical
  -> medical_or_safety

文書 | formal | proposal | report
  -> formal_document

vtuber | 配信 | roleplay
  -> vtuber_roleplay

non-empty text
  -> casual_chat

empty text
  -> unknown
```

These lexical rules are heuristics for RelayEMO expression gating. They do not become scene authority simply because one branch matches.

Exact marker literals may change with the implementation; the invariant owned here is that their result remains a non-authoritative hint unless another separately reviewed architecture transition changes ownership.

## Scene-hint candidate schema

`build_scene_hint_candidate(...)` currently returns an object with exactly these responsibility-level fields:

```text
schema_version
candidate_present
scene_type
source_class
source_authoritative
policy_authority
restrictive_only
candidate_applied
can_open_runtime_policy
reason_ids
validation_error_ids
content_free
governance
public_governance
```

The exact current schema identifier is:

```text
relayemo.scene_hint_candidate.v0
```

`candidate_present` is:

```text
scene_type != unknown
```

after scene-type normalization.

## Fixed non-authority values

Every current `build_scene_hint_candidate(...)` result forces:

```text
source_authoritative = false
policy_authority = none
restrictive_only = true
candidate_applied = false
content_free = true
```

The shared governance artifact is built with:

```text
analyzer_kind = scene_policy_candidate
source = caller source
source_language = und
is_estimate = true
source_authoritative = false
candidate_applied = false
policy_authority = none
restrictive_only = true
confidence = caller confidence
stability = 0.0
content_free = true
enum_values = [normalized scene_type]
```

The builder's default source is:

```text
heuristic
```

The default reason ID is:

```text
fail_closed_candidate_source
```

unless an explicit bounded `reason_ids` list is supplied.

## Runtime-policy-open invariant

The candidate reports:

```text
can_open_runtime_policy = can_open_runtime_policy(governance)
```

Under the current construction above, this is false.

ACG-5 verification explicitly requires the heuristic scene hint to satisfy:

```text
source_authoritative == false
policy_authority == none
restrictive_only == true
candidate_applied == false
can_open_runtime_policy == false
content_free == true
```

A consumer must not reinterpret the scene type itself as permission to bypass those authority fields.

## Public governance projection

The builder stores both:

```text
governance
public_governance
```

`governance` is the internal shared Analyzer Candidate Governance artifact.

`public_governance` is the content-free projection returned by the shared governance helper.

RelayEMO's assembled artifact additionally exposes:

```text
scene_hint_candidate_public
```

as:

```text
candidate_present = scene_hint_candidate.candidate_present
+ all public_governance fields
```

This public projection must remain content-free. It is not authority to log or publish raw request text, matched marker bodies, scene prose, memory content, relationship content, protected source bodies, paths, queue payloads, or free-form rationale.

## RelayEMO assembled artifact boundary

`run_relayemo(...)` currently computes:

```text
text = latest_user_text(messages)
affect = estimate_user_affect(text)
scene_hint_type = infer_scene_hint_type(text)
scene_hint_candidate = build_scene_hint_candidate(
    scene_hint_type=scene_hint_type,
    source=heuristic,
    confidence=affect.confidence,
)
```

The result artifact carries both the canonical hint candidate and a deprecated compatibility scene-state field.

This contract does not own the full RelayEMO artifact. It owns only the exact authority meaning of the scene-like fields described here.

## Deprecated compatibility scene_state

The current RelayEMO artifact retains:

```text
scene_state
```

with exactly this authority meaning:

```text
scene_type = current RelayEMO scene_hint_type
deprecated = true
non_authoritative = true
source_authoritative = false
policy_authority = none
restrictive_only = true
content_free = true
```

This compatibility field is not normalized RelaySCN state.

Its presence does not authorize:

```text
RelayEMO scene_state -> RelaySCN scene_state
RelayEMO scene_state -> RelaySCN scene_policy
RelayEMO scene_state -> RelayMEM retrieval policy
```

It exists for compatibility consumers while the current code still carries historical RelayEMO-shaped preview/state fields.

## Deprecated compatibility aliases

`relaylm/relayemo.py` currently retains these aliases:

```text
SCENE_TYPES = SCENE_HINT_TYPES
infer_scene_type = infer_scene_hint_type
```

They are explicitly compatibility aliases for non-authoritative hints.

They do not restore scene ownership to RelayEMO.

## Structured affect-probe scene candidate

`parse_llm_affect_probe_output(raw_text)` accepts either of these input keys for scene-candidate compatibility:

```text
scene_hint_candidate
scene_state_candidate
```

The canonical parsed hint is still rebuilt through:

```text
build_scene_hint_candidate(
    scene_hint_type=normalized scene_type,
    source=llm_candidate,
    confidence=normalized scene confidence,
    reason_ids=[llm_candidate_restrictive_only],
)
```

Therefore an LLM-produced scene guess does not escape the same non-authoritative ACG gate.

## Structured-probe scene validation

The structured probe accepts a scene type only when it belongs to `SCENE_HINT_TYPES`.

Otherwise it records:

```text
invalid_scene_type
```

and normalizes the scene type to:

```text
unknown
```

Scene confidence must be a finite numeric value when present.

Missing scene confidence records:

```text
missing_numeric_field:scene_state_candidate.confidence
```

A non-numeric, boolean, null, NaN, or infinite scene confidence records:

```text
invalid_numeric_field:scene_state_candidate.confidence
```

and uses:

```text
0.0
```

Valid scene confidence is clamped to `[0.0, 1.0]` before the hint candidate is built.

## Structured-probe deprecated scene_state_candidate

The parsed structured-probe result also returns a deprecated compatibility object:

```text
scene_state_candidate
```

with:

```text
scene_type
confidence
deprecated = true
non_authoritative = true
source_authoritative = false
policy_authority = none
restrictive_only = true
content_free = true
```

Like the ordinary RelayEMO `scene_state` compatibility field, this object is not RelaySCN state and must not become RelaySCN or RelayMEM policy input.

## Invalid structured-probe example

ACG-5 verification explicitly checks a structured candidate whose scene type contains private/unrecognized text.

Current behavior is:

```text
invalid scene type
  -> scene_type = unknown
  -> can_open_runtime_policy = false
  -> public candidate remains content-free
```

Malformed content is not converted into a permissive scene policy and is not echoed as a public enum.

## RelaySCN no-backflow boundary

RelaySCN remains the sole owner of normalized scene state and policy.

The current `build_relayscn_scene_policy_artifact(...)` signature does **not** accept:

```text
relayemo_artifact
```

Passing such a keyword is expected to fail as an unsupported argument rather than silently restoring the historical dependency.

ACG-5 verification also requires current RelaySCN source code not to contain the retired fallback helper:

```text
_extract_relayemo_scene_state
```

and not to mint scene source authority using:

```text
source = relayemo_artifact
```

These absence checks are semantic authority guards, not merely implementation style preferences.

## RelayMEM no-backflow boundary

Current RelayMEM retrieval consumes the RelaySCN scene-policy artifact through its own input:

```text
relayscn_scene_policy_artifact
```

It does not accept:

```text
relayemo_artifact
```

as policy input.

ACG-5 verification asserts both the retrieval builder signature and the active request-path stage wiring preserve this separation.

The resulting retrieval artifact derives its scene type and retrieval scope from RelaySCN, not RelayEMO.

## Request-path ordering

The current managed request path preserves the relevant stage order:

```text
RelayREL
  -> RelaySCN
  -> RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayMEM runtime context apply/repack
```

The exact request-runtime orchestration remains owned by runtime architecture/contracts. For ACG-5, the important invariant is directional authority: RelaySCN has already established the scene boundary before RelayEMO runs, and later RelayMEM does not accept RelayEMO scene policy input.

## Affect remains separate from scene authority

RelayEMO may use the same request text to estimate affect and produce a scene hint.

The fact that affect confidence is passed into the hint governance artifact does not turn affect confidence into scene provenance.

Current heuristic affect confidence therefore remains only candidate confidence.

It is not:

```text
trusted scene source
RelaySCN policy authority
memory disclosure permission
retrieval scope
mutation permission
durable scene fact
```

## Relationship to scene-policy candidate governance

The shared analyzer kind used by the RelayEMO hint is:

```text
scene_policy_candidate
```

That name does not mean the artifact **is** scene policy.

The shared Analyzer Candidate Governance contract distinguishes candidate production from source authority, candidate application, and runtime-open permission.

RelayEMO's current construction deliberately fixes the candidate to non-authoritative, non-applied, restrictive-only, policy-authority-none state.

## Failure direction

ACG-5 failures always close toward less scene authority:

```text
unknown heuristic scene value
  -> unknown
  -> validation error
  -> no runtime policy open

unknown LLM scene value
  -> unknown
  -> invalid_scene_type
  -> no runtime policy open

malformed scene confidence
  -> 0.0
  -> validation error
  -> no authority gain

RelaySCN given RelayEMO artifact input
  -> rejected by interface
  -> no fallback scene authority

RelayMEM path
  -> scene policy comes from RelaySCN
  -> no RelayEMO policy input
```

There is no fallback path in which invalid RelaySCN state is repaired by accepting RelayEMO's hint as authoritative scene state.

## Stable invariants

- RelaySCN is the sole normalized `scene_state` / `scene_policy` owner.
- RelayEMO may emit `relayemo.scene_hint_candidate.v0` only as a candidate hint.
- RelayEMO's current scene-hint vocabulary is bounded to `SCENE_HINT_TYPES`.
- Unknown scene types normalize to `unknown`; raw unknown values do not become public enums.
- RelayEMO scene hints are `source_authoritative=false`.
- RelayEMO scene hints are `policy_authority=none`.
- RelayEMO scene hints are `restrictive_only=true`.
- RelayEMO scene hints are `candidate_applied=false`.
- Current RelayEMO scene hints cannot open runtime policy.
- Public scene-hint diagnostics remain content-free.
- Deprecated RelayEMO `scene_state` and structured-probe `scene_state_candidate` remain explicitly non-authoritative.
- RelaySCN does not accept RelayEMO artifact input as a scene fallback.
- RelayMEM derives scene constraints from RelaySCN, not RelayEMO.
- Structured LLM scene guesses are rebuilt through the same restrictive scene-hint builder.
- No ACG-5 scene hint creates memory retrieval/update or durable scene authority.

## Non-goals

This contract does not define:

- the full RelayEMO affect vector or assistant expression-state schema;
- session-state persistence/TTL details;
- LLM affect probe routing, backend, timeout, or complete affect-candidate schema;
- display-marker placement or visible apply;
- TTS/avatar execution or expression adapters;
- normalized RelaySCN scene-policy schema;
- ACG-6 scene-wiki classification;
- RelayMEM reader selection, ranking, eligibility, or mutation;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [RelayEMO Affect Modulation](../architecture/emotion/affect-modulation.md)
- [Scene Model](../architecture/scene/scene-model.md)
- [ACG-5 RelayEMO Scene Ownership Cleanup](../architecture/acg5_relayemo_scene_cleanup.md)
- [Analyzer Candidate Governance Contract](analyzer-candidate.md)
