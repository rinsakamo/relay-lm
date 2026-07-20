---
relaylm_doc_type: contract
relaylm_authority: relayctx_session_evidence_overlay_bounded_working_state_admission_catch_up_partition_and_reflex_snapshot_boundary
relaylm_status: target
relaylm_volatility: high
relaylm_owner: relayctx
relaylm_update_trigger:
  - a Contract 1 family member changes source/change coverage or authorization-watermark shape
  - the RelayATN pre-request authority separation ADR changes
  - ADR 0003 or ADR 0004 changes a fixed boundary this contract depends on
  - scene-epoch issuance or rotation ownership changes
  - the validated-sidecar or candidate-artifact owner changes
  - the RelayCTX short-term runtime or context-compiler boundary changes
relaylm_not_authoritative_for:
  - Shared Assessment or Subjective MEM schema, lifecycle, formation, consolidation, relation, retrieval, or persistence
  - Markdown or SQLite storage authority and commit protocol
  - RelaySLP scheduling, episode coverage, or acknowledgement
  - RelayREF model, prompt, or output semantics
  - RelayATN architecture, verbs, tiers, or implementation
  - Contract 1 source capture, admission, governance, lineage, feed, or response-binding schemas
  - semantic subject, predicate, polarity, relationship, scene, emotion, or intent content
  - runtime database, cache, migration, compatibility bridge, alias, redirect, dual-read, or dual-write mechanics
  - project sequencing or implementation approval
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - ../adr/relayatn_pre_request_authority_separation.md
relaylm_related_contracts:
  - governed-evidence-contract-family.md
  - governed-source-capture-admission.md
  - evidence-governance-access.md
  - source-metadata-lineage-derived-artifacts.md
  - evidence-streams-change-feed.md
  - assistant-response-evidence-binding.md
  - relayctx_short_term_runtime_contract.md
  - context_compiler_contract.md
relaylm_verified_by:
  - ../../scripts/relaylm_ctx_ovl_v1_validate.py
  - ../../scripts/relaylm_ctx_ovl_v1_equivalence.py
  - ../../scripts/relaylm_ctx_ovl_v1_fixture_registry_guard.py
---

# RelayCTX Session Evidence Overlay (CTX-OVL) Contract

**Status:** Target contract. It fixes the adopted CTX-OVL boundary but does not claim runtime, storage, migration, or deployment completion.

## 1. Purpose

CTX-OVL is RelayCTX-owned, bounded, rebuildable, non-durable current-session working state. It preserves provisional continuity between requests without becoming Protected Source Evidence, Shared Assessment, Subjective MEM, durable MEM, RelayREL authority, RelaySCN authority, RelayEMO authority, or RelayINT authority.

The four independent decisions remain:

```text
turn admission            RelayATN
protected evidence        Contract 1
provisional continuity    RelayCTX / CTX-OVL
subjective durable memory RelaySLP / RelayMEM
```

RelayATN rejection never deletes or rewrites governed evidence. RelayATN never writes CTX-OVL and may read only the bounded content-free `ReflexSnapshot`.

## 2. Fixed boundaries

- CTX-OVL admits only validated candidate artifacts produced by an owning pipeline stage or explicit deterministic operation.
- RelayCTX does not infer relationship, scene, emotion, intent, Shared Assessment, or Subjective MEM semantics from raw text.
- Every overlay record has one explicit Contract 1 binding.
- Every candidate envelope has one resolvable producer-artifact reference.
- Every selection, projection, catch-up application, and rebuild evaluates TTL from an operation timestamp; no stored status flag can override time.
- Every cross-record identifier used by an operation resolves strictly or the operation fails closed.
- Every top-level identifier is unique within its own schema namespace in one bounded validation state; references are typed, so different schema namespaces may reuse a textual token without ambiguity.
- Every catch-up and rebuild operation references the contract-owned `ctx_ovl_budget_policy_v1`; operation records may choose lower budgets but cannot enlarge the schema-fixed policy caps.
- Every partition epoch is scoped by `session_id + partition_kind + partition_id`.
- Every group-visible projection proves same-session, current-epoch, current-authorization disclosure for every included record.
- Unknown or conflicting participant identity is quarantined and non-shadowing.
- CTX-OVL never writes durable memory, SOUL, relationship files, scene files, product knowledge, or governed evidence.

## 3. Authority and visibility partitions

CTX-OVL has exactly four authority/visibility partition kinds:

```text
participant
shared_scene
relationship
quarantine
```

This closed authority set does not prohibit additional non-authoritative implementation indexes or shards.

Partition visibility is fixed:

```text
participant  -> participant_private
shared_scene -> shared_scene_visible
relationship -> relationship_scoped
quarantine   -> quarantined
```

Private-to-group visibility is never obtained by mutating an existing record's visibility field. It is obtained only through a valid `SharedSceneProjection`.

## 4. Partition epochs

A `PartitionEpochDescriptor` identifies one partition instance by:

```text
session_id + partition_kind + partition_id
```

At most one descriptor for that key may be `active`. The same `partition_id` may be active in different sessions. A record or projection is current only when its `partition_epoch_ref` resolves to the active descriptor with matching session, partition kind, partition ID, and epoch sequence.

A missing, cross-session, mismatched, or superseded descriptor fails closed.

## 5. Candidate artifacts and envelopes

### 5.1 CandidateArtifact

`relaylm.ctx_ovl_candidate_artifact.v1` is immutable metadata for one bounded candidate body owned by the CTX-OVL candidate-artifact namespace. It contains:

```text
artifact_id
artifact_kind
producer_component
authority_domain
session_id
source_event_id
evidence_space_id
content_kind
content_digest
actual_bytes
immutable
```

`authority_domain` is fixed to `relayctx_candidate_artifact`. The record is not the semantic body and grants no Shared Assessment, Subjective MEM, relationship, scene, emotion, or intent authority.

### 5.2 CandidateEnvelope

Every `OverlayRecord` contains a `candidate_envelope` with:

```text
envelope_kind
content_kind
envelope_version
producer_artifact_ref
content_address_space
content_digest
raw_source_content_present
size_bound
```

`content_address_space` is fixed to `ctx_ovl_candidate_artifact`. `producer_artifact_ref` must resolve to a `CandidateArtifact` whose artifact ID, artifact kind, authority domain, producer component, session, source event, evidence space, content kind, digest, and byte count all match. A sidecar envelope resolves only a `validated_sidecar` artifact; a deterministic-operation envelope resolves only a `deterministic_operation_result` artifact.

Failure cases are explicit:

- unresolved artifact: omit from packing;
- artifact-kind mismatch: omit from packing;
- session or source-lineage mismatch: omit from packing;
- digest or byte-count mismatch: omit from packing;
- forbidden authority domain: reject the record;
- unknown future envelope or content kind: fail closed.

`candidate_basis` and `envelope_kind` are coupled:

```text
validated_sidecar                -> validated_sidecar_envelope
explicit_deterministic_operation -> deterministic_operation_envelope
```

A digest alone is not a resolvable reference.

## 6. Explicit Contract 1 binding

Every `OverlayRecord` contains `contract1_binding`:

```text
evidence_space_id
source_event_id
change_partition_id
partition_epoch_id
authority_snapshot_digest
```

The binding must match all of:

- `source_provenance.source_event_id`;
- `source_provenance.evidence_space_id`;
- `last_validated_authorization.change_partition_id`;
- `last_validated_authorization.partition_epoch_id`;
- `last_validated_authorization.authority_snapshot_digest`.

No relationship is inferred from string prefixes or naming conventions. In particular, a Contract 1 change partition is never mapped to a CTX-OVL partition by stripping or adding a prefix.

A `SharedSceneProjection`, `CatchUpAttempt`, or `RebuildEvent` may include or produce an overlay only when its own coverage and authorization references exactly match the overlay's Contract 1 binding.

## 7. OverlayRecord lifecycle

`relaylm.ctx_ovl_overlay_record.v1` contains:

```text
schema
overlay_record_id
session_id
partition_kind
partition_id
partition_epoch_ref
participant_ref
source_provenance
contract1_binding
last_validated_authorization
candidate_envelope
admission_origin
created_by_actor
candidate_basis
visibility_scope
lifecycle_state
superseded_by_overlay_record_id_or_null
non_shadowing
quarantine_shadow_target_overlay_record_id_or_null
rebuildable
durable
ttl_expires_at
```

`rebuildable` is always `true`; `durable` is always `false`.

Lifecycle coupling is strict:

- `superseded` requires a non-null successor ID;
- a non-`superseded` record must not carry a successor ID;
- an `active` record requires current, admitted authorization;
- an unresolved participant is quarantined, has a null participant ID, and is non-shadowing;
- `rebuild_pipeline` records are created by `ctx_ovl_rebuild_process`;
- other admitted records are created by `relayctx_pipeline`;
- partition kind and visibility scope always follow the fixed mapping in Section 3;
- supersession targets resolve in the same session, never self-reference, and form an acyclic graph;
- quarantine shadow targets never dangle or cross sessions, and any resolved shadow attempt remains forbidden.

## 8. Operation-time TTL authority

`ttl_expires_at` is record metadata. Whether a record is usable is derived only by comparing it with the operation's required `evaluated_at` timestamp.

The strict rule is:

```text
evaluated_at < ttl_expires_at
```

Equality is expired. The comparison uses parsed RFC 3339 timestamps, not lexical ordering. CTX-OVL has no authoritative persisted `ttl_status` field.

The following operations carry `evaluated_at` and enforce the rule for every selected or produced overlay:

- `ContextSelection`;
- `SharedSceneProjection`;
- `CatchUpAttempt`;
- `RebuildEvent`.

## 9. ContextSelection

`relaylm.ctx_ovl_context_selection.v1` records one Context Compiler selection operation. It strictly resolves every selected overlay and every producer artifact before creating a transient rendered hint.

The rendered hint is not stored back into CTX-OVL. The selected overlay IDs, resolved artifact IDs, and rendered-hint count must agree exactly. An unresolved, non-active, stale, unauthorized, expired, or epoch-mismatched record is omitted rather than replaced by a stale fallback.

## 10. Catch-up

Catch-up occurs only on a later admitted request:

```text
governed source retained
 -> later admitted request
 -> Contract 1 coverage and authorization check
 -> bounded eligible selection
 -> normal owning pipeline
 -> validated candidate artifact
 -> optional CTX-OVL overlay
```

`CatchUpAttempt` requires `evaluated_at`, a Contract 1 coverage checkpoint, an authorization watermark, `budget_policy_ref: ctx_ovl_budget_policy_v1`, a positive event bound, a positive total-candidate-byte bound, an outcome, and produced IDs. The contract-owned policy caps `max_events` at 64 and `max_total_candidate_bytes` at 65,536; an operation may select lower values but cannot self-authorize larger values. The produced record count and candidate bytes must remain within the selected values.

Every produced ID must resolve to an overlay that:

- is in the same session;
- has `admission_origin: catch_up_pipeline`;
- matches the attempt's change partition, Contract 1 epoch, and authority snapshot;
- is not expired at `evaluated_at`.

A dangling, cross-session, wrong-origin, non-active, unauthorized, expired, or out-of-scope output fails closed. `bounded_catch_up_applied` has at least one produced ID; every fail-closed or no-op outcome has no produced IDs. The coverage checkpoint and authorization watermark name the same Contract 1 partition and epoch. Timestamps alone never establish source coverage completeness.

## 11. Rebuild

`RebuildEvent` reconstructs bounded overlay state after restart, cache loss, or explicit operator action. It never makes CTX-OVL durable. Every rebuild references `ctx_ovl_budget_policy_v1` and declares positive `max_overlay_records` and `max_total_candidate_bytes` values. The contract-owned policy caps them at 256 records and 262,144 bytes; an operation may select lower values but cannot self-authorize larger values.

Every produced ID must resolve to an overlay that:

- is in the same session;
- has `admission_origin: rebuild_pipeline`;
- matches the rebuild coverage and authorization partition, epoch, and snapshot;
- is active, currently admitted, and not expired at `evaluated_at`.

The rebuild coverage checkpoint and authorization reference must agree exactly.

## 12. SharedSceneProjection

`SharedSceneProjection` is the only group-visible projection. Its own authorization reference must be `current` and `admitted`. It requires `evaluated_at` and proves for every included record:

- identifier resolution;
- same session;
- `shared_scene` partition and `shared_scene_visible` visibility;
- active lifecycle;
- the same shared-scene partition and partition epoch as the projection, with the current scene epoch;
- unexpired TTL;
- Contract 1 change partition, epoch, and authority snapshot equal to the projection authorization;
- visible participants are a non-empty unique subset of authorized participants.

Private, relationship-scoped, or quarantined records are never group-visible. Projection records expose no private-partition count, existence, identifier, source, or sequence gap.

## 13. Invalidation

`OverlayInvalidationEvent` records deterministic removal after restriction, redaction, purge, correction/supersession, or authorization-watermark advancement. It carries an explicit `invalidation_scope_binding` containing evidence space, source event, change partition, Contract 1 epoch, and authority snapshot. Every affected ID resolves in the same session and its complete Contract 1 binding equals that scope; dangling or cross-scope targets fail closed.

Reason and access state are coupled:

```text
restricted            -> restricted
redacted              -> redacted
purged                 -> purged
corrected_superseded   -> corrected_superseded
```

`watermark_advanced` requires the new observed sequence to be strictly greater than the recorded prior sequence. Every affected overlay present in the bounded state is `removed`.

## 14. Write authority

`WriteAttempt` separates the attempted actor from the authorization decision. Only `relayctx_pipeline` and `ctx_ovl_rebuild_process` may be authorized. RelayATN may appear only as an unauthorized attempted actor and can never be paired with `authorized_actor: true` or `authorized: true`.

## 15. ReflexSnapshot

`ReflexSnapshot` is the only CTX-derived structure RelayATN may read. It contains bounded counts and content-free freshness or scope-change signals. It contains no raw content and no reversible identifier.

## 16. Validation discipline

The machine-readable suite uses:

- one Draft 2020-12 schema bundle;
- one direct-reference catalog;
- one or more bounded-state valid matrix files;
- one or more bounded-state invalid matrix files;
- stable machine-readable error IDs;
- exact produced-error-ID equality for every invalid case;
- a registry guard locking the exact case names and expected IDs across all matrix files;
- defect-substitution self-tests.

The bounded-state matrices replace the earlier one-file-per-case fixtures so that cross-record operations can be reviewed as complete bounded states rather than disconnected fragments.

## 17. Relationship to PR #586

PR #586 remains non-authoritative design evidence. This contract retains only the CTX-OVL boundary that is consistent with accepted ADRs and Contract 1. It narrows or rejects any material that would:

- let RelayATN write CTX-OVL;
- make turn rejection delete governed evidence;
- make CTX-OVL durable memory;
- grant CTX-OVL relationship, scene, emotion, intent, Shared Assessment, or Subjective MEM authority;
- infer Contract 1 bindings from naming conventions;
- disclose private partition state to a group projection.

Shared Assessment, Subjective MEM, storage authority, and implementation sequencing remain deferred to their own atomic contracts or ADRs.
