---
relaylm_doc_type: contract
relaylm_authority: evidence_governance_retention_access_quarantine_review_redaction_purge_export_and_replication_eligibility
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evidence_governance
relaylm_update_trigger:
  - evidence governance state or operation changes
  - access-grant or authorization rules change
  - retention, quarantine deadline, redaction, purge, export, or replication policy changes
  - validation, metadata, or change-feed interface changes
relaylm_not_authoritative_for:
  - SourceEvent creation or admission outcome
  - metadata correction, source lineage, or derived-artifact lifecycle
  - source-capture sequencing or authority-change partition delivery
  - route lifecycle, runtime response finalization, RelayCTX state, RelayREF semantics, or RelaySLP formation
  - physical erasure, storage, export file creation, or replication transport
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_contracts:
  - governed-evidence-contract-family.md
  - governed-source-capture-admission.md
  - source-metadata-lineage-derived-artifacts.md
  - evidence-streams-change-feed.md
  - assistant-response-evidence-binding.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1B v7: Evidence Governance and Access

This document is authoritative for evidence governance, retention, access grants and authorizations, quarantine review access, redaction, purge, export eligibility, and replication eligibility.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This contract owns mutable evidence governance after SourceEvent creation:

- record and part access state;
- integrity and retention state;
- independent holds;
- exact AccessGrant schema and lifecycle;
- quarantine-review authorization;
- normal access authorization;
- restriction, redaction, expiry, recovery, and purge;
- keyed replay-suppression tombstones;
- export and replication eligibility.

It does not own SourceEvent identity, semantic truth, metadata correction,
lineage, RelayCTX state, RelayREF observation fields, RelaySLP jobs, or physical
storage/transport execution.

## Governance operation authority enum

Contract 1B AuthorityScope.allowed_operations uses only:

initialize_admitted
initialize_quarantined
grant_access
restrict_grant
revoke_grant
reauthorize_grant
set_retention
place_hold
release_hold
global_restrict
restore_available
expire_access
mark_sensitive_discovery
redact_parts
purge
mark_corrupt
verify_recovery
restore_after_recovery
revalidate_metadata
resolve_quarantine_release
resolve_quarantine_rejection
issue_quarantine_review_authorization
issue_normal_access_authorization
issue_export_eligibility
issue_replication_eligibility

No unlisted operation is valid.

## MetadataProjectionSelector

metadata_projection_selector:
    source_identity_basic
    effective_speaker
    audience_scope_class
    audience_member_refs
    request_source_event_refs
    control_correlation_refs
    trusted_replay_identity
    active_lineage_refs
    full_authorized_audit

Rules:

- normal Shared Assessment does not receive control_correlation_refs,
  trusted_replay_identity, or full_authorized_audit;
- request_source_event_refs expose only currently authorized SourceEvent refs;
- rejected, ephemeral, quarantined, or control-only request refs are available
  only to exact authorized audit/recovery purposes;
- audience_member_refs requires explicit participant/audience authority;
- a payload-part grant does not implicitly grant all metadata.

## SubjectSelector

Tagged union:

1. none
2. producer
3. represented_speaker
4. explicit_principals
   - principal_refs: sorted unique non-empty
Rules:

- exactly one variant;
- unknown/conflicting principals cannot satisfy a normal grant;
- explicit principals belong to the same evidence space;

## AudienceUseConstraint

Tagged union:

1. exact_occurrence_audience
2. exact_private_subset
   - participant_refs: sorted unique non-empty
3. exact_room
   - room_ref
4. public_only
5. operator_review_scope
   - authority_scope_ref

Rules:

- exact_private_subset is a subset of effective occurrence audience;
- exact_room requires current room participation authority;
- public_only requires effective source audience public;
- operator review does not create downstream disclosure permission;
- assistant-response effective audience is the intersection of the Contract 1A
  configured occurrence audience and Contract 1E delivery cohort; either may
  narrow but neither may broaden the other.

## DestinationClassConstraint

destination_class:
    no_external_destination
    user_local_export
    encrypted_user_backup
    approved_device_replica
    approved_workspace_replica
    governed_migration_target

Rules:

- export grants use user_local_export or encrypted_user_backup;
- replication grants use approved_device_replica,
  approved_workspace_replica, or governed_migration_target;
- one grant does not authorize both export and replication unless it contains
  separate purpose-specific authorization records.

## AccessGrant v1

Schema:

    relaylm.evidence_access_grant.v1

Fields:

schema
grant_id
source_event_id
evidence_space_id
purpose
grantee
part_selector
metadata_projection_selectors
subject_selector
audience_use_constraint
locality_constraint
destination_class_constraint
grant_basis
issued_by_principal_ref
issued_by_authority_scope
issued_at
expires_at_or_null

purpose:
    relayctx_evidence_read
    relayref_observation_read
    shared_assessment_read
    authorized_evidence_review
    user_export_eligible
    replication_eligible
    recovery_read

grantee tagged union:

1. exact_principal
   - principal_ref
2. service_class
   - service_class:
       relayctx_service
       relayref_service
       shared_assessment_service
       evidence_review_service
       export_service
       replication_service
       recovery_service
3. authority_scope_match
   - authority_scope_ref

part_selector tagged union:

1. all_currently_available_parts
2. explicit_part_ids
   - part_ids: sorted unique non-empty

locality_constraint:
    device_local_only
    workspace_local_or_stricter
    replication_eligible_required
    any_policy_permitted

grant_basis fields:

policy_snapshot_ref
authorization_basis_ref
admission_decision_id
metadata_revision
governance_revision
validation_bundle_revision

Cross-field rules:

- grant source/evidence space MUST match;
- grant_basis governance_revision is the creating governance revision;
- metadata and validation bundle revisions MUST be current at issuance;
- selected explicit parts MUST be protected_available;
- all_currently_available_parts is evaluated only at issuance and authorization;
  it does not automatically include later-added successor content;
- user export uses exact principal unless an evidence operator acts under a
  separately audited management operation;
- replication names a replication service or migration authority;
- RelayCTX/RelayREF/Shared Assessment name their exact service class or configured
  principal;
- destination class is required for export/replication and
  no_external_destination for other purposes;
- expires_at, when present, is later than issued_at;
- metadata projection selectors are sorted unique, non-empty, and
  purpose-allowlisted;
- every normal content grant includes source_identity_basic;
- full_authorized_audit MUST be the only metadata projection selector in that
  grant and requires authorized_evidence_review or recovery_read;
- workspace administrator status creates no implicit grant.

Effective grant state is derived:

granted
restricted
revoked
expired
stale_metadata
stale_validation
stale_policy

A grant is active only when state is granted.

## EvidenceGovernanceState v1

Schema:

    relaylm.evidence_governance_state.v1

Fields:

schema
record_access_state
integrity_state
retention_state
part_access_states
active_holds
grant_records
sensitive_part_ids
purge_tombstone_id_or_null

record_access_state:
    available
    globally_restricted
    expired
    purged

integrity_state:
    verified
    unverified
    failed

part_access_state:
    protected_available
    protected_restricted
    quarantine_only
    redacted
    purged
    non_content

retention_state fields:

retention_class
access_until_or_null
purge_due_at_or_null
review_due_at_or_null
review_policy_ref_or_null
locality

retention_class:
    bounded
    review_bounded
    retained_until_revoked

locality:
    device_local
    workspace_local
    replication_eligible

GrantLifecycleRecord fields:

grant_id
access_grant
governance_lifecycle_state
lifecycle_governance_revision
lifecycle_reason_code_or_null

governance_lifecycle_state:
    granted
    restricted
    revoked

Rules:

- time-, metadata-, validation-, and policy-derived stale/expired states are not
  stored as mutable grant lifecycle;
- canonical governance digest includes immutable grant plus governance lifecycle
  state;
- resolver combines lifecycle with current time/metadata/validation/policy.

ActiveHold fields:

hold_id
hold_authority_ref
hold_reason_code
placed_at
review_due_at
placing_governance_revision

Rules:

- bounded requires finite access_until and purge_due_at;
- review_bounded requires finite access_until, purge_due_at, review_due_at, and
  review policy;
- when both deadlines exist, access_until is not later than purge_due_at;
- retained_until_revoked requires null access_until and purge_due_at, is
  exceptional, is forbidden for ordinary conversation raw content, and requires
  finite review_due_at plus an explicit revocation/purge path;
- after finite access_until, normal access fails even when a hold preserves
  bytes;
- after review_due_at without valid review, normal access fails closed;
- finite purge_due_at is a destruction deadline unless an active hold blocks
  purge;
- active holds never grant access;
- every retained content part has exactly one part access state;
- non-content parts contain no personal-evidence payload;
- purged is terminal;
- integrity failed blocks all normal access independently of record access;
- expired and purged cannot return to available;
- part redaction does not rewrite Contract 1A manifest.

EvidenceGovernanceState is the deterministic canonical state value derived
from a complete EvidenceGovernanceEvent chain. It is the input to
`resulting_governance_state_digest`; it is not an independent mutable authority
or a substitute for the event chain.

## EvidenceGovernanceEvent v1

Schema:

    relaylm.evidence_governance_event.v1

Fields:

schema
governance_event_id
source_event_id
evidence_space_id
governance_revision
expected_previous_governance_revision_or_null
expected_metadata_revision
expected_validation_bundle_revision
operation
operation_payload
operation_idempotency_key
authority_principal_ref
authority_scope
policy_snapshot_ref
recorded_at
effective_at
resulting_governance_state_digest
authority_change_set_ref

Rules:

- revision starts at 1 and is gap-free;
- effective_at is not later than recorded_at;
- future-dated activation is forbidden in v1;
- expected metadata/validation revisions MUST match at commit;
- operation payload is a closed union below;
- resulting digest is SHA-256 over canonical EvidenceGovernanceState;
- same idempotency key with different body is an integrity conflict;
- a natural-language request is causal provenance only, never operation authority;
- every effective event has a complete AuthorityChangeSetRef.

## Exact governance transition table

### initialize_admitted

Pre-state:
    no governance chain

Payload:
    integrity_state=verified
    retention_state
    initial_part_access_states
    initial_access_grants
    active_holds=[]

Post-state:

- record_access_state = available or globally_restricted;
- no quarantine_only part;
- omitted/reference parts = non_content;
- grants bind metadata revision 0 and current validation bundle;
- bounded retention deadlines valid.

### initialize_quarantined

Pre-state:
    no governance chain

Payload:
    integrity_state
    retention_state
    initial_part_access_states
    quarantine_review_due_at
    quarantine_dispose_due_at

Post-state:

- record_access_state = globally_restricted;
- integrity_state MAY be unverified or failed;
- retained content parts = quarantine_only or protected_restricted;
- no ordinary active grant;
- review_due_at = quarantine_review_due_at;
- purge_due_at is not later than quarantine_dispose_due_at;
- no active holds.

### grant_access

Pre-state:
    admitted; not purged; current metadata/validation

Payload:
    access_grant

Post-state:

- append immutable grant with governance lifecycle state granted;
- no other state changes.

### restrict_grant

Pre-state:
    named grant granted

Payload:
    grant_id
    reason_code

Post-state:

- named grant lifecycle state restricted;
- no automatic restoration.

### revoke_grant

Pre-state:
    named grant granted or restricted

Payload:
    grant_id
    revocation_basis_ref

Post-state:

- named grant lifecycle state revoked.

### reauthorize_grant

Pre-state:
    prior grant restricted, revoked, expired, or stale

Payload:
    prior_inactive_grant_id
    new_access_grant
    reauthorization_basis_ref

Post-state:

- prior grant unchanged;
- new grant appended as granted with a new grant ID.

### set_retention

Pre-state:
    not purged

Payload:
    new_retention_state
    change_basis_ref

Post-state:

- retention_state exactly replaced;
- access deadline MAY be shortened despite an active hold;
- purge deadline MUST NOT be shortened to an instant before hold release;
- active hold blocks physical/logical purge but never access restriction;
- access/purge/review deadline invariants validated;
- no record-access restoration occurs;
- an expired record remains expired even if a later purge deadline is extended;
- grants may become inactive by resolver.

### place_hold

Pre-state:
    not purged

Payload:
    active_hold

Post-state:

- append named hold;
- no access grant or access-state change.

### release_hold

Pre-state:
    named hold active

Payload:
    hold_id
    placing_governance_revision
    release_basis_ref

Post-state:

- remove exactly named hold;
- other holds unchanged;
- overdue purge remains due and must proceed under policy.

### global_restrict

Pre-state:
    not purged

Payload:
    reason_code
    required_followup
    affected_part_ids

required_followup:
    review
    redaction
    purge
    recovery
    policy_revalidation
    metadata_revalidation
    validation_revalidation

Post-state:

- record_access_state = globally_restricted unless already expired;
- all currently granted content grants become restricted;
- affected available parts become protected_restricted;
- follow-up obligation remains open until a referenced later governance event
  completes it.

### restore_available

Pre-state:
    admitted;
    globally_restricted;
    verified integrity;
    current metadata/validation;
    access/review deadlines current;
    not expired/purged

Payload:
    restoration_basis_ref
    completed_followup_governance_event_ids
    new_access_grants

Post-state:

- record_access_state = available;
- only explicitly restored parts become protected_available;
- prior restricted/revoked grants remain inactive;
- new grants use new IDs.

### expire_access

Pre-state:
    access_until reached;
    not purged

Payload:
    evaluated_at
    retention_basis_revision

Post-state:

- record_access_state = expired;
- all normal grants inactive;
- content remains until purge_due_at or hold release;
- cannot return to available.

### mark_sensitive_discovery

Pre-state:
    not purged

Payload:
    affected_part_ids
    finding_artifact_refs
    required_followup

Post-state:

- record_access_state = globally_restricted unless expired;
- affected parts = protected_restricted;
- all content grants = restricted;
- exact finding artifact refs recorded.

### redact_parts

Pre-state:
    not purged

Payload:
    affected_part_ids
    redaction_basis_ref
    sanitized_successor_source_event_id_or_null
    physical_redaction_obligation_ref

Post-state:

- affected parts = redacted;
- grants selecting affected parts become restricted;
- other available parts MAY remain available;
- if no protected_available part remains, record_access_state =
  globally_restricted;
- physical propagation is required but implemented by storage contract.

### purge

Pre-state:
    not purged;
    purge_due or explicit authorized purge;
    no active hold

Payload:
    purge_basis_ref
    affected_storage_classes
    purge_obligation_ref
    purge_tombstone

affected_storage_classes:
    primary_payload
    derived_payload
    search_index
    cache
    replica
    backup_key_material
    export_tracking

Post-state:

- record_access_state = purged;
- all formerly retained content part states = purged;
- omitted/reference-only parts remain non_content;
- all grants inactive;
- active holds empty;
- integrity state retained for audit only;
- purge_tombstone_id set;
- normal metadata/lineage/content unavailable;
- purge is terminal.

### mark_corrupt

Pre-state:
    not purged

Payload:
    affected_part_ids
    integrity_failure_refs

Post-state:

- integrity_state = failed;
- record_access_state becomes globally_restricted when previously available;
- an already expired record remains expired;
- every currently granted content grant lifecycle becomes restricted;
- already restricted/revoked grants remain unchanged;
- affected parts = protected_restricted.

### verify_recovery

Pre-state:
    integrity_state = failed;
    record_access_state is not purged

Payload:
    recovered_part_ids
    verification_artifact_refs
    verified_manifest_digest

Post-state:

- integrity_state becomes verified only when every retained content part needed
  for future access is covered by current verification artifacts;
- otherwise integrity_state remains unverified;
- record_access_state remains globally_restricted or expired;
- no grant restored.

### restore_after_recovery

Pre-state:
    record_access_state = globally_restricted;
    integrity verified;
    current metadata/validation;
    deadlines current;
    record has never become expired or purged

Payload:
    verified_recovery_governance_revision
    restoration_basis_ref
    restored_part_ids
    new_access_grants

Post-state:

- record_access_state = available or globally_restricted as payload declares;
- restored parts become protected_available only when available;
- prior grants remain inactive;
- new grants use new IDs.

### revalidate_metadata

Pre-state:
    not purged;
    current metadata revision greater than grant metadata revision

Payload:
    metadata_revision
    replacement_access_grants
    revalidation_basis_ref
    candidate_record_access_state

Post-state:

- older grants remain stale_metadata;
- replacement grants bind current metadata;
- record may become available only when all current eligibility gates pass.

### resolve_quarantine_release

Pre-state:
    initial quarantined;
    exact next revision;
    all Contract 1A review purposes accepted;
    current metadata/validation;
    integrity verified

Payload:
    review_decision_id
    resolved_part_access_states
    retention_state
    new_access_grants

Post-state:

- no quarantine_only part remains;
- record_access_state = available or globally_restricted;
- current retention valid;
- grants bind current metadata/validation;
- review and governance pair share AuthorityChangeSetRef.

### resolve_quarantine_rejection

Pre-state:
    initial quarantined;
    exact next revision;
    effective Contract 1A review decision rejected

Payload:
    review_decision_id
    disposal_action_ref
    tombstone_or_purge_plan_ref

Post-state:

- record_access_state = globally_restricted or purged;
- no active normal grant;
- all content restricted;
- disposal is complete or durably scheduled;
- event never becomes admitted.

## Current governance resolver

1. validate complete gap-free chain;
2. validate each transition's exact pre/post rule;
3. recompute canonical state digest;
4. evaluate time-derived expiry/review states;
5. evaluate metadata and validation staleness;
6. apply part-level redaction/restriction;
7. fail closed on conflict, gap, invalid transition, stale policy, or missing
   follow-up completion;
8. never use timestamps to repair revision conflict.

## PurgedEvidenceTombstone v1

Schema:

    relaylm.purged_evidence_tombstone.v1

Fields:

schema
purged_evidence_tombstone_id
source_event_id
evidence_space_id
replay_suppression_key
purged_at
tombstone_retain_until
purge_governance_revision
authority_change_set_ref

replay_suppression_key fields:

algorithm
key_id
input_schema_version
value

algorithm:
    hmac-sha256

Rules:

- HMAC input is the Contract 1A replay identity canonical representation plus
  manifest digest;
- HMAC key is a protected local security-domain secret;
- tombstone contains no source content, part digest, audience member list,
  display name, or raw replay identity;
- key rotation policy defines whether an old tombstone remains comparable;
- tombstone is private bounded control metadata;
- it cannot reactivate a SourceEvent or become Subjective MEM anti-reformation
  authority;
- replay after tombstone either remains suppressed or creates a policy-reviewed
  new occurrence; it never restores the old source ID.

## QuarantineReviewAuthorizationProjection v1

Schema:

    relaylm.quarantine_review_authorization_projection.v1

Fields:

schema
authorization_id
source_event_id
evidence_space_id
review_purpose
reviewer_principal_ref
reviewer_authority_scope_ref
selected_part_ids
metadata_projection_selectors
governance_revision
metadata_revision
validation_bundle_revision_or_null
policy_snapshot_ref
issued_at
not_after
access_log_reservation_ref
authorization_digest

Rules:

- purpose is one exact Contract 1A required quarantine review purpose;
- selected parts and metadata are minimum necessary;
- access log reservation exists before content materialization;
- not_after is short and bounded by review deadline and authority expiry;
- authorization grants no normal Shared Assessment, RelayCTX, export,
  replication, or MEM use;
- any newer governance/metadata/validation revision invalidates it;
- security, identity, audience, authorization, integrity, and source review have
  separate authority checks.

## EvidenceAccessAuthorizationProjection v1

Schema:

    relaylm.evidence_access_authorization_projection.v1

Fields:

schema
access_authorization_id
source_event_id
evidence_space_id
gate_kind
purpose
grantee
selected_part_ids
metadata_projection_selectors
matched_grant_ids
subject_selector_digest
audience_constraint_digest
destination_class_constraint
admission_decision_id
governance_revision
metadata_revision
validation_bundle_revision
policy_snapshot_ref
authority_snapshot_digest
change_partition_watermarks
emergency_authorization_ref_or_null
issued_at
not_after
authorization_digest

gate_kind:
    relayctx_evidence
    relayref_observation
    shared_assessment
    admitted_review
    recovery
    export_eligibility
    replication_eligibility

ChangePartitionWatermark fields:

change_partition_id
partition_epoch_id
highest_observed_partition_sequence

Rules:

- grantee uses the same exact union as AccessGrant;
- normal content gates require selected_part_ids sorted unique, non-empty, and
  protected_available;
- metadata-only emergency recovery MAY use an empty selected_part_ids list;
- matched grant IDs are non-empty except exact emergency recovery;
- validation bundle revision may be null only for a no-content recovery path
  explicitly authorized by emergency_authorization_ref;
- policy snapshot is current;
- subject/audience digests bind the exact selectors used;
- metadata projections are explicit;
- change_partition_watermarks is sorted unique by partition ID/epoch and
  includes every Contract 1D partition relevant to the server-side authority
  snapshot for this source/purpose;
- a consumer need not receive hidden control event details, but the authorizer
  MUST observe all relevant control/normal partition state before issuing;
- authority_snapshot_digest binds admission disposition, governance, metadata,
  validation bundle, lineage/artifact eligibility, policy, and the exact
  watermark list;
- not_after is the earliest of grant expiry, access/review deadline, policy
  expiry, and gate maximum lifetime;
- newer governance, metadata, validation, redaction, purge, or partition change
  invalidates it;
- it is content-free and not a durable grant.

## Normal access resolver

For a normal content gate:

1. Contract 1A current disposition is admitted;
2. current ValidationBundle is valid;
3. Contract 1C metadata/artifact state is complete;
4. governance state is available;
5. integrity is verified;
6. access/review deadlines are current;
7. selected parts are protected_available;
8. at least one active grant matches exact purpose, grantee, parts, metadata
   projections, subject, audience, locality, destination, policy, metadata, and
   validation revisions;
9. the server-side authorizer resolves every currently relevant Contract 1D
   partition from the SourceProjectionRegistry and observes its current
   contiguous committed watermark;
10. authorization projection binds the complete watermark list and authority
    snapshot digest;
11. all revisions, watermarks, and deadlines are rechecked immediately before
    materialization.

Any failure denies access.

## Purpose-specific rules

RelayCTX:
- exact relayctx_evidence_read grant;
- short interactive/session not_after;
- no broad injection of all pending evidence;
- no durable memory authority.

RelayREF:
- exact relayref_observation_read grant;
- assistant-response SourceEvent only;
- response-scoped;
- no first-token dependency;
- no output mutation or user-fact authority.

Shared Assessment:
- exact shared_assessment_read grant;
- character-independent service;
- no SOUL/STYLE meaning source;
- assistant origin remains attached.

Authorized admitted review:
- evidence operator scope;
- least-privilege content and metadata;
- workspace admin alone insufficient;
- access logged before release.

Recovery:
- integrity-failed or authoritative-incomplete source only;
- recovery/security authority;
- exact recovery_read grant or emergency authorization;
- no semantic consumer forwarding;
- verification does not restore normal access.

## Export eligibility

Requires:

- admitted, available, verified, current source;
- exact user_export_eligible grant;
- user_local_export or encrypted_user_backup destination class;
- exact principal or separately audited evidence operator;
- participant/audience/third-party disclosure constraints pass;
- selected metadata projection excludes unauthorized control refs;
- current authorization projection;
- no secret/security exclusion.

Contract 1B returns eligible/ineligible only.
File creation, encryption, format, and delivery are outside this contract.

## Replication eligibility

Requires:

- admitted, available, verified, current source;
- exact replication_eligible grant;
- approved destination class;
- replication service or migration authority;
- locality = replication_eligible;
- audience/subject/part/metadata constraints pass;
- current authorization projection;
- storage/migration contract approves destination and transport.

User export grant is neither required nor sufficient.

## Governance authority matrix

Own-source restriction:
    represented source principal within exact own-source scope; cannot override
    another participant's independent privacy.

Shared Assessment grant:
    deterministic policy authority or evidence operator with exact service,
    subject, audience, part, metadata, and validation scope.

RelayCTX/RelayREF grant:
    deterministic configured policy or evidence operator for exact service and
    bounded purpose.

Review grant:
    evidence operator with content-read authority; workspace admin insufficient.

Retention:
    retention service, source principal within policy, or evidence operator.

Hold:
    retention, recovery, security, or legal authority with exact review due date.

Redaction/purge:
    source principal within valid scope, retention deadline service, security
    operator, or evidence operator through explicit management route.
    Natural-language conversation alone is insufficient.

Recovery:
    recovery/security authority only; no semantic access implied.

Export:
    exact represented source principal or audited evidence operator.

Replication:
    evidence operator or migration authority with approved destination scope.

## Failure and recovery

Deadline passes before scheduler event:
    access resolver denies immediately using wall-clock evaluation.

Active hold after access expiry:
    no normal access; content preserved until hold release.

Purge due with active hold:
    purge blocked; overdue obligation remains visible to retention authority.

Metadata/validation revision changes:
    old grants/authorizations become stale; revalidation creates new grants.

Grant revoke races materialization:
    recheck before content read and before external commit; abort on change.

Physical purge incomplete:
    logical source remains purged and unavailable; storage obligation remains
    open and blocks completion claims.

## Acceptance gates

- Every operation has exact pre-state, changed dimensions, and post-state.
- Bounded retention has finite access and purge deadlines.
- Quarantine has review and disposal deadlines.
- Holds are independent and release by hold ID.
- AccessGrant subject/audience/metadata/destination fields are closed unions.
- Payload access does not imply all metadata access.
- Purge tombstone uses keyed HMAC and is listed as a formal record.
- Quarantine review has a separate authorization projection.
- Normal authorization binds consumer partition sequence.
- Export and replication are independent purposes.
- Conversational suppression, MEM Forget, and Evidence purge remain separate.
