---
relaylm_doc_type: contract
relaylm_authority: governed_evidence_contract_family_common_identity_authority_and_cross_contract_invariants
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evidence
relaylm_update_trigger:
  - evidence-space identity or isolation changes
  - common principal, participation, authority-scope, or policy-reference rules change
  - a Contract 1 family member changes a shared invariant
  - PR 612 request-response evidence boundaries change
relaylm_not_authoritative_for:
  - exact route lifecycle or runtime scheduler behavior
  - exact source capture, admission, governance, lineage, feed, or assistant-response schemas owned by family members
  - exact RelayCTX, RelayREF, RelaySLP, Shared Assessment, or Subjective MEM schemas
  - physical storage, encryption, transaction, cache, backup, migration, or erasure mechanics
  - current implementation status or implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - ../adr/relayatn_pre_request_authority_separation.md
relaylm_related_contracts:
  - governed-source-capture-admission.md
  - evidence-governance-access.md
  - source-metadata-lineage-derived-artifacts.md
  - evidence-streams-change-feed.md
  - assistant-response-evidence-binding.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1 v7: Governed Evidence Contract Family

This document is authoritative for the shared identity, authority primitives, vocabulary, and cross-contract invariants of the governed-evidence contract family.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This umbrella contract owns only the common vocabulary, identity domains,
authority primitives, and cross-contract invariants used by the governed
evidence contract family.

The family is deliberately split because route capture, source admission,
evidence governance, metadata/lineage, ordered feeds, and response finalization
have different owners, lifecycles, failure costs, and independent consumers.

## Contract family

1. Contract 1A — Governed Source Capture and Admission
   - path: docs/contracts/governed-source-capture-admission.md
   - owner: evidence admission
   - owns SourceEvent creation, canonical source identity, admission,
     quarantine disposition, replay, and validation-bundle binding.

2. Contract 1B — Evidence Governance and Access
   - path: docs/contracts/evidence-governance-access.md
   - owner: evidence governance
   - owns retention, restriction, grants, redaction, purge, review access,
     normal access authorization, export eligibility, and replication eligibility.

3. Contract 1C — Source Metadata, Lineage, and Derived Artifacts
   - path: docs/contracts/source-metadata-lineage-derived-artifacts.md
   - owner: evidence provenance
   - owns effective metadata correction, source lineage, RelayREF/advisory
     artifacts, integrity/security artifact lifecycle, and governance inheritance.

4. Contract 1D — Evidence Streams, Coverage, and Authority-Change Feed
   - path: docs/contracts/evidence-streams-change-feed.md
   - owner: evidence operations
   - owns source-capture stream sequencing, terminal coverage, privacy-partitioned
     authority-change delivery, and coverage checkpoints.

5. Contract 1E — Assistant-Response Evidence Binding
   - path: docs/contracts/assistant-response-evidence-binding.md
   - owner: runtime/evidence boundary
   - owns pre-emission response capture reservation, emitted-range binding,
     delivery-cohort representation, response finalization, and recovery handoff.

No family member may silently redefine another member's record or state.

## Normative language

MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY, and
OPTIONAL are normative.

## Stable terminology

Source occurrence
    A message, finalized emitted assistant response, action, tool result, sensor
    result, import record, setting change, lifecycle request, or governed system
    occurrence before evidence admission.

SourceEvent
    The immutable governed source representation created only by Contract 1A.

Protected Source Evidence
    A SourceEvent whose current admission disposition is admitted. Origin remains
    explicit: user, assistant, tool, sensor, system, import, or external.

Assistant-origin Evidence
    Protected Source Evidence for canonical assistant output accepted at the
    Contract 1E output-observation boundary. It is never user-origin fact.

RelayREF observation
    A bounded advisory derived artifact about a finalized assistant response.
    It is not response-content authority.

Shared Assessment
    Character-independent semantic assessment of currently eligible Protected
    Source Evidence under a later owning contract.

Subjective MEM
    Character-scoped durable personal memory formed only from a governance- and
    schema-valid Shared Assessment under its owning contract.

Conversational suppression
    Session-local RelayINT/RelayCTX prompt-selection behavior. It is not durable
    MEM Forget and not Evidence Governance.

Durable MEM Forget
    A RelayMEM/canonical-memory lifecycle operation outside Contract 1.

Evidence purge
    A terminal Contract 1B governance operation.

Authority mutation
    One durable admission, review, governance, metadata, lineage, authoritative
    artifact, redaction, or purge change that later consumers may need to observe.

## EvidenceSpaceDescriptor v1

Schema:

    relaylm.evidence_space_descriptor.v1

Fields:

schema
evidence_space_id
descriptor_revision
expected_previous_descriptor_revision_or_null
workspace_or_tenant_ref
isolation_mode
controller_principal_ref
participant_domain_ref
policy_snapshot_ref
created_at
retired_at_or_null
authority_principal_ref
authority_scope
authority_change_set_ref_or_null

isolation_mode:
    single_principal
    private_conversation
    shared_scene
    imported_collection
    system_control

Rules:

- evidence-space identity is character-independent;
- descriptor revision starts at 1 and is gap-free;
- expected previous revision is null only at revision 1;
- revision 1 MAY use null authority_change_set_ref because evidence/change
  partitions do not yet exist;
- every revision after 1 requires a complete AuthorityChangeSetRef;
- workspace/tenant, participant domain, and isolation mode cannot be changed in
  place after revision 1;
- retirement is terminal for new capture;
- retirement does not rewrite or purge existing SourceEvents;
- a new isolation domain requires a new evidence_space_id;
- every family record MUST resolve one complete non-conflicting descriptor chain;
- cross-space references are forbidden unless an owning migration/import contract
  explicitly creates a new SourceEvent in the destination space;
- workspace administrator status alone does not grant content access.

## Common references

### Internal ID

Every internal ID:

- is opaque;
- is globally unique within its record kind;
- is never derived from source content;
- is not a display label;
- MUST NOT encode participant identity, private audience, or semantic content.

### PrincipalRef

Fields:

principal_kind
principal_id
authority_domain_ref

principal_kind:
    account
    participant
    assistant
    service
    tool
    sensor
    system
    external

Rules:

- principal_id is opaque;
- display names are projections, not identity;
- assistant and participant identities are never interchangeable;
- unknown identity uses an explicit unresolved record outside normal grants.

### ParticipationRef

Fields:

principal_ref
participation_kind
room_ref_or_null
participation_epoch_ref_or_null
verification_state

participation_kind:
    sender
    recipient
    room_member
    room_moderator
    observer
    unknown

verification_state:
    verified
    asserted
    unresolved
    conflicting

Cross-field rules:

- room_member and room_moderator require room_ref;
- sender and recipient MAY omit room_ref for a direct private conversation;
- unknown cannot be used to grant participant-, relationship-, export-, or
  replication-scoped content access;
- conflicting participation fails closed.

### PolicySnapshotRef

Fields:

policy_id
policy_revision
policy_digest

Rules:

- policy digest uses SHA-256 over the owning policy's canonical representation;
- policy references are immutable;
- later policy change does not rewrite historical decisions;
- current eligibility MAY require a newer policy revalidation.

### ResourceScope

Fields:

evidence_space_id
whole_evidence_space
source_event_ids
participant_refs
room_refs
capture_stream_refs
route_refs
response_refs

Rules:

- all lists are sorted unique arrays;
- whole_evidence_space=true requires every list empty;
- whole_evidence_space=false requires at least one non-empty list;
- non-empty dimensions are intersected, never unioned;
- a broader operation requires a separately issued broader scope;
- cross-space terms are forbidden.

### AuthorityScope

Fields:

scope_id
scope_kind
resource_scope
allowed_operations
issued_at
expires_at_or_null
issuer_principal_ref
issuer_authority_scope_ref_or_null

scope_kind:
    own_source
    represented_subject
    room_moderator
    workspace_admin
    evidence_operator
    security_operator
    retention_service
    recovery_service
    migration_authority
    route_configuration_authority
    runtime_finalization_authority
    capture_stream_authority
    change_feed_authority

Rules:

- allowed_operations is a sorted unique non-empty list from the closed enum owned
  by the applicable family member;
- expiry is evaluated fail-closed at operation time;
- scope kind alone grants nothing outside allowed_operations and ResourceScope;
- workspace_admin is never implicit content-read authority;
- room_moderator does not automatically gain private participant content;
- route configuration and runtime finalization scopes do not admit evidence;
- capture-stream and change-feed scopes do not gain semantic content access.

### AuthorityChangeSetRef

Fields:

change_set_id
change_projection_plan_digest

Rules:

- the owning mutation reserves one immutable change_set_id;
- Contract 1D validates and emits all required privacy-partition projections;
- no family record embeds a global consumer sequence;
- one mutation may produce several partition-specific events;
- consumers never infer completeness from a sequence in another partition.

## Common digest rules

- SHA-256 is the family default content/hash algorithm.
- Digests are lowercase hexadecimal.
- A digest field MUST identify its canonical input schema/version.
- Content digests never double as user-visible identifiers.
- Secret-bearing bytes MUST NOT be retained merely to compute a personal-evidence
  fingerprint.
- Replay-suppression tombstones use keyed HMAC under Contract 1B, not raw content
  digest.

## Cross-contract invariants

C1-1. Source occurrence, evidence admission, turn admission, response success,
RelayCTX continuity, RelayREF observation, RelaySLP scheduling, Shared
Assessment, and Subjective MEM formation are orthogonal.

C1-2. RelayATN owns pre-request turn admission only and never mutates Contract 1
records, RelayCTX working state, or durable memory.

C1-3. SourceEvent admitted content and provenance are never rewritten.
Correction uses metadata revision, lineage, successor, restriction, redaction,
or purge.

C1-4. Evidence space does not imply universal participant access.

C1-5. A purpose label alone grants nothing. Content access requires Contract 1B
authorization bound to exact grantee, resource, parts, metadata projection,
policy, and current revisions.

C1-6. Assistant-origin Evidence never becomes user-origin fact through retention,
lineage, RelayREF, Shared Assessment, or Subjective MEM.

C1-7. RelayREF observation cannot replace response content, completion state, or
runtime finalization authority.

C1-8. Conversational suppression does not revoke evidence access, mutate
canonical MEM, or purge evidence.

C1-9. Explicit pass-through creates no Contract 1 capture by default. Opt-in
requires an external route contract snapshot accepted by Contract 1A/1E.

C1-10. Product knowledge corpus authority remains separate. An assistant response
derived from product knowledge may be recorded as an occurrence, but the corpus
itself is not copied into personal evidence authority.

C1-11. Shared Assessment is character-independent and receives no SOUL semantic
conditioning.

C1-12. Subjective MEM receives no direct raw SourceEvent shortcut.

C1-13. Similarity, embedding proximity, model confidence, RelayATN score, and
RelayREF classification are never admission, merge, lineage, grant, or purge
authority.

C1-14. Storage location, cache row, queue row, and transport envelope are not
source identity.

C1-15. Historical source-capture terminality is not retracted by later
restriction, redaction, purge, or validation invalidation. Current eligibility
travels through Contract 1D.

C1-16. Every durable authority mutation after evidence-space bootstrap has
exactly one complete AuthorityChangeSetRef and all required partition
projections. EvidenceSpaceDescriptor revision 1 is the sole bootstrap exception.

C1-17. Missing, conflicting, stale, expired, or cross-space authority fails
closed.

C1-18. Every implementation MUST validate exact schemas and cross-field rules
before accepting a family record.

## Cross-contract logical state

One currently usable source requires all of the following:

1. complete EvidenceSpaceDescriptor;
2. complete Contract 1A SourceEvent and admitted disposition;
3. current valid Contract 1A validation bundle;
4. complete Contract 1B governance chain;
5. complete Contract 1C effective metadata and required lineage/artifact state;
6. one Contract 1B access authorization for the exact purpose;
7. no later Contract 1D authority mutation invalidating the consumed snapshot.

No one record is a substitute for this resolver.

## Contract precedence

- The umbrella owns shared definitions and invariants.
- A family member owns its exact schema and lifecycle.
- Accepted ADRs own architecture decisions outside exact schemas.
- Runtime/storage implementation cannot weaken a contract invariant.
- Machine-readable schema and normative prose MUST agree.
- When schema and prose conflict before acceptance, the conflict blocks adoption.
- After acceptance, authority precedence MUST be explicitly recorded in the
  canonical contract family index; no silent precedence is permitted.

## Implementation boundary

This family does not authorize implementation. Before production code relies on
a family member:

- that member and all prerequisites MUST be accepted;
- machine-readable schemas MUST exist;
- deterministic validators and crash/race fixtures MUST pass;
- current implementation status MUST separately approve execution;
- no permanent dual authority, dual write, or compatibility alias may remain.
