---
relaylm_doc_type: contract
relaylm_authority: source_capture_stream_sequence_terminal_coverage_and_privacy_partitioned_evidence_authority_change_feed
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evidence_operations
relaylm_update_trigger:
  - source-capture stream identity or reservation rules change
  - terminal coverage or gap semantics change
  - authority-change partitioning, projection, or coverage changes
  - multi-user evidence-feed privacy boundary changes
relaylm_not_authoritative_for:
  - SourceEvent admission or evidence governance semantics
  - metadata, lineage, or derived-artifact semantics
  - RelayCTX consumer cursors, catch-up budgets, CTX-OVL, or scene policy
  - RelaySLP job/episode coverage
  - physical queue, topic, database, transaction, or outbox implementation
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
  - assistant-response-evidence-binding.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1D v7: Evidence Streams, Coverage, and Authority-Change Feed

This document is authoritative for source-capture sequencing and coverage and the privacy-partitioned evidence authority-change feed.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This contract owns content-free operational ordering:

- source-capture stream descriptors and lifecycle;
- capture sequence reservation and terminalization;
- source-capture coverage;
- AuthorityChangeSet creation;
- privacy-partitioned authority-change projections;
- per-partition change coverage.

It does not own source content, admission meaning, governance semantics,
consumer acknowledgement, RelayCTX state, RelaySLP jobs, or physical queue/store
implementation.

## Contract 1D authority operations

capture_stream_create
capture_stream_seal
capture_stream_retire
capture_stream_rotate
capture_sequence_reserve
capture_sequence_terminalize_admission
capture_sequence_terminalize_no_source
capture_sequence_mark_aborted
capture_sequence_recover_aborted
capture_coverage_advance
change_set_plan
change_set_mark_complete
change_set_mark_corrupt
change_projection_emit
change_projection_abort
change_partition_create
change_partition_seal
change_partition_retire
source_projection_registry_initialize
source_projection_registry_add_partition
source_projection_registry_retire_visibility
change_coverage_advance

## SourceCaptureStreamDescriptor v1

Schema:

    relaylm.source_capture_stream_descriptor.v1

Fields:

schema
capture_stream_id
evidence_space_id
capture_stream_kind
stream_direction
stream_generation
capture_stream_epoch_id
start_sequence
stream_status
descriptor_revision
expected_previous_descriptor_revision_or_null
created_at
sealed_at_or_null
retired_at_or_null
issuer_principal_ref
issuer_authority_scope
policy_snapshot_ref

capture_stream_kind:
    managed_user_input
    managed_assistant_output
    tool_transaction
    sensor_input
    authorized_import
    governed_system_event
    pass_through_opt_in

stream_direction:
    inbound
    outbound
    internal
    import

stream_status:
    open
    sealed
    retired

Rules:

- descriptor revision starts at 1 and is gap-free;
- stream kind/direction/evidence space/epoch/start sequence are immutable;
- managed user and managed assistant output use distinct stream IDs;
- one assistant delivery cohort uses one sequence, never one sequence per chunk;
- sequence is never reused within an epoch;
- reset/reuse requires a new epoch ID;
- generation increases only on deliberate stream generation change;
- revision 1 starts open;
- allowed status transitions are open -> sealed -> retired;
- no reverse transition is allowed;
- seal forbids new sequence reservation;
- retirement is terminal;
- rotate creates a new descriptor/epoch and never reopens the old descriptor;
- stream authority gains no content access.

## CaptureSequenceEvent v1

Schema:

    relaylm.capture_sequence_event.v1

Fields:

schema
capture_sequence_event_id
capture_stream_id
capture_stream_epoch_id
capture_sequence
sequence_revision
expected_previous_sequence_revision_or_null
operation
operation_payload
operation_idempotency_key
recorded_at
issuer_principal_ref
issuer_authority_scope

operation:
    reserve
    terminalize_admission
    terminalize_no_source
    mark_aborted_recoverable
    recover_aborted

### reserve payload

capture_attempt_id
reservation_basis_ref
reserved_at

Rules:

- revision 1;
- stream open;
- sequence is next permitted sequence or within allowed bounded allocation window;
- one capture attempt only;
- no source content.

### terminalize_admission payload

capture_attempt_id
admission_decision_id
terminal_outcome

terminal_outcome:
    admitted
    quarantined
    ephemeral
    rejected
    duplicate_replay

Rules:

- Contract 1A outcome-specific completeness passes;
- same capture attempt as reservation.

### terminalize_no_source payload

capture_attempt_id
capture_attempt_terminal_event_id
terminal_reason

Rules:

- Contract 1A CaptureAttempt terminal_no_source;
- no AdmissionDecision/SourceEvent.

### mark_aborted_recoverable payload

capture_attempt_id
abort_reason
recovery_case_ref

Rules:

- sequence remains nonterminal for safe coverage;
- recovery is required.

### recover_aborted payload

recovery_case_ref
recovered_terminal_event_ref

Rules:

- exact aborted sequence only;
- recovered terminal reference is admission or no-source terminal;
- no sequence reuse.

### Sequence resolver

- reserve is required before terminalization;
- one terminal outcome only;
- conflicting terminal outcomes make stream epoch unverifiable;
- retry uses same idempotency key/body;
- sequence ordering is numerical; timestamps never establish sequence;
- a forward jump beyond policy bound blocks/quarantines the stream operation and
  does not allocate synthetic gap ranges.

## SourceCaptureCoverageCheckpoint v1

Schema:

    relaylm.source_capture_coverage_checkpoint.v1

Fields:

schema
coverage_checkpoint_id
capture_stream_id
capture_stream_epoch_id
coverage_revision
expected_previous_coverage_revision_or_null
start_sequence
highest_seen_sequence_or_null
highest_contiguous_terminal_sequence_or_null
missing_sequence_ranges
nonterminal_sequence_ranges
stream_status
derived_coverage_status
terminal_basis_digest_or_null
updated_at
issuer_principal_ref
issuer_authority_scope
operation_idempotency_key

derived_coverage_status:
    empty_open
    open_contiguous
    open_incomplete
    sealed_complete
    sealed_incomplete
    unverifiable

Rules:

- revision starts at 1 and is gap-free;
- empty stream uses highest seen/contiguous null and empty ranges;
- ranges are sorted, non-overlapping, inclusive, and bounded in count;
- missing ranges identify unreserved/unseen sequence numbers inside the observed
  window;
- nonterminal ranges identify reserved but not safely terminal sequences;
- highest contiguous terminal is the greatest sequence such that every sequence
  from start through it is terminal;
- terminal basis digest is SHA-256 over canonical sorted pairs
  `(sequence, terminal_record_id)` from start through highest contiguous;
- terminal basis is null when no contiguous terminal sequence exists;
- open_contiguous means no current gap through highest seen, not future complete;
- sealed_complete requires no missing/nonterminal range through highest seen;
- late terminalization closes the exact nonterminal range;
- RelayATN, RelayCTX, RelayREF, RelaySLP, Shared Assessment, and Subjective MEM
  cannot advance this checkpoint;
- later governance/redaction/purge does not retract historical capture
  terminality.

## Authority-change reference value objects

AuthoritativeMutationRef fields:

record_kind
record_id
record_revision_or_null

record_kind:
    evidence_space_descriptor
    source_event
    admission_decision
    admission_review_decision
    evidence_governance_event
    source_metadata_revision
    source_lineage_relation_event
    source_derived_artifact_event
    purge_tombstone

AuthorizedControlRefClass:
    governance_revision_ref
    metadata_revision_ref
    validation_bundle_ref
    lineage_relation_ref
    purge_tombstone_ref
    review_decision_ref
    evidence_space_descriptor_ref
    capture_control_ref

Rules:

- refs contain no content;
- projection plan allowlists classes per partition;
- source IDs/control refs are omitted when the partition may not know them.

## AuthorityChangeSetEvent v1

Schema:

    relaylm.evidence_authority_change_set_event.v1

Authority change-set lifecycle is append-only.

Common fields:

schema
change_set_event_id
change_set_id
change_set_revision
expected_previous_change_set_revision_or_null
evidence_space_id
operation
operation_payload
recorded_at
issuer_principal_ref
issuer_authority_scope
operation_idempotency_key

operation:
    plan
    mark_complete
    mark_corrupt

### plan payload

authoritative_mutation_refs
change_kind
projection_plan
projection_plan_digest

change_kind:
    source_admitted
    source_quarantined
    quarantine_released
    quarantine_rejected
    governance_changed
    source_metadata_changed
    source_lineage_changed
    authoritative_artifact_changed
    source_redacted
    source_purged
    evidence_space_retired

ProjectionPlanEntry fields:

change_partition_ref
projection_visibility
consumer_effect
authorized_source_event_refs
authorized_control_ref_classes

projection_visibility:
    normal_consumer
    quarantine_consumer
    security_consumer
    control_consumer

consumer_effect:
    candidate_available
    current_state_recheck
    metadata_recheck
    lineage_recheck
    validation_recheck
    content_invalidated
    source_remove
    quarantine_only
    evidence_space_retired

### mark_complete payload

planned_change_set_revision
completed_projection_event_ids
completed_projection_digest

Rules:

- every planned projection has exactly one terminal projection event;
- completed projection IDs are sorted unique;
- completed projection digest covers the plan entry and projection event pair;
- no unplanned partition projection may be counted.

### mark_corrupt payload

conflict_refs
corruption_reason

Rules:

- only change-feed recovery/security authority;
- terminal for downstream completeness claims;
- affected consumers fail closed.

### Change-set rules

- revision starts at 1 and is gap-free;
- plan is revision 1;
- projection plan is policy-derived before the mutation becomes
  downstream-visible;
- plan entries are sorted unique;
- each partition receives only source/control refs authorized for that partition;
- private source existence is not projected to an unauthorized partition;
- mark_complete is the only normal terminal state;
- `candidate_available` is not SLP enqueue, episode boundary, assessment request,
  or MEM write authorization;
- one mutation has one change set, but many partition projections;
- family mutation records reference change_set_id and revision-1 plan digest,
  not a global consumer sequence;
- gaps/conflicts make the change set incomplete or corrupt;
- timestamps never establish lifecycle order.

## ChangePartitionDescriptor v1

Schema:

    relaylm.evidence_change_partition_descriptor.v1

Fields:

schema
change_partition_id
evidence_space_id
partition_kind
participant_ref_or_null
relationship_ref_or_null
room_ref_or_null
shared_scene_ref_or_null
partition_reader_selector
partition_epoch_id
start_sequence
partition_status
descriptor_revision
expected_previous_descriptor_revision_or_null
policy_snapshot_ref
issuer_principal_ref
issuer_authority_scope

partition_kind:
    shared_scene
    participant
    relationship
    evidence_control
    quarantine_control
    security_control

partition_status:
    open
    sealed
    retired

PartitionReaderSelector tagged union:

1. exact_principals
   - principal_refs: sorted unique non-empty
2. exact_service_class
   - service_class
3. room_membership_policy
   - room_ref
   - membership_policy_ref
4. relationship_participants
   - relationship_ref
   - relationship_policy_ref
5. authority_scope_match
   - authority_scope_ref

Cross-field rules:

- participant requires participant_ref and null relationship/room/shared-scene
  refs;
- relationship requires relationship_ref and null participant/room/shared-scene
  refs;
- shared_scene requires exactly one of room_ref or shared_scene_ref and null
  participant/relationship refs;
- evidence/quarantine/security control require all participant/relationship/
  room/shared-scene refs null;
- evidence/quarantine/security control expose no normal consumer content
  authority and use service/authority reader selectors;
- reader selector MUST match partition kind and descriptor scope;
- membership/reader broadening requires a new partition epoch so new readers do
  not inherit prior private history automatically;
- reader narrowing seals/rotates the partition for future events;
- one partition has one privacy audience and independent sequence;
- partition epoch reset requires a new epoch ID;
- consumer cannot infer another partition's event count or gaps.

## SourceProjectionRegistryEvent v1

Schema:

    relaylm.source_projection_registry_event.v1

This append-only registry records which change partitions have previously been
authorized to know that a SourceEvent exists. It is control metadata, not a
content-access grant.

Fields:

schema
registry_event_id
source_event_id
evidence_space_id
registry_revision
expected_previous_registry_revision_or_null
operation
partition_entries
recorded_at
issuer_principal_ref
issuer_authority_scope
operation_idempotency_key

operation:
    initialize
    add_partition
    retire_partition_visibility

PartitionEntry fields:

change_partition_id
partition_epoch_id
visibility_class
first_projection_event_id
revocation_target_partition_ref
retired_at_or_null
retirement_basis_ref_or_null

visibility_class:
    normal_source_visibility
    quarantine_control_visibility
    security_control_visibility
    evidence_control_visibility

Rules:

- revision starts at 1 and is gap-free;
- initialize contains every partition receiving the first completed source
  authority-change projection;
- add_partition records a newly authorized partition before/with its first
  source-aware projection;
- revocation_target_partition_ref identifies the current internal control/feed
  partition that receives later restriction/redaction/purge propagation for
  caches or replicas associated with this visibility;
- retire_partition_visibility prevents future ordinary source projections to
  that reader epoch but preserves the historical need for revocation/purge
  handling through the revocation target;
- registry entries grant no source access;
- purge/redaction/restriction planning consults all current and retired entries
  that may hold a cache/replica/reference;
- unauthorized consumers cannot read the registry;
- conflicting registry chains block purge-completeness claims.

## EvidenceAuthorityChangeProjectionEvent v1

Schema:

    relaylm.evidence_authority_change_projection_event.v1

Fields:

schema
projection_event_id
change_set_id
change_partition_id
partition_epoch_id
partition_sequence
projection_event_kind
change_kind_or_null
authoritative_mutation_refs
authorized_source_event_refs
authorized_control_refs
consumer_effect_or_null
projection_visibility_or_null
recorded_at
operation_idempotency_key

projection_event_kind:
    authority_change
    change_projection_aborted

Rules:

- authority_change requires non-null change_kind matching a planned change-set
  entry;
- change_projection_aborted requires null change_kind;
- change_projection_aborted closes only an early allocated sequence, contains no
  source/mutation refs, and is never counted as the planned projection;
- after an abort, recovery emits the planned authority_change projection at a
  newly allocated sequence in the same partition/epoch;
- mark_complete references only the recovered planned projection, while coverage
  includes both the abort and recovered event;
- sequence allocated atomically with projection event commit;
- no sequence is pre-reserved and abandoned silently;
- when implementation must reserve early, it MUST emit a content-free
  change_projection_abort event in the same partition to close the sequence;
- event contains no source payload, digest, display name, hidden reasoning, or
  unauthorized audience list;
- source refs are included only when partition consumers may resolve them;
- authorized control refs use allowlisted classes and reveal no rejected/private
  content;
- duplicate delivery is harmless by projection_event_id;
- a projection event is actionable only after the referenced change set has a
  valid mark_complete revision; before that it is buffered/inert;
- consumers fetch current authoritative state; event itself grants no access;
- source_purged -> source_remove;
- redaction -> content_invalidated;
- metadata/lineage/validation changes -> exact recheck effect;
- one partition event never claims completeness in another partition.

## Change projection abort

change_kind:
    change_projection_aborted

Allowed only when:

- an implementation allocated partition sequence before durable projection;
- no authority mutation reference/content can be safely projected;
- abort event is content-free;
- it closes the sequence for coverage;
- repeated abort uses same ID/body.

Preferred implementation allocates sequence atomically with event and never needs
this case.

Evidence-space descriptor/control mutation:

- EvidenceSpaceDescriptor revision 1 is bootstrap state and may precede change
  partitions/change sets;
- later descriptor mutations use the evidence_control partition;
- normal source/content consumers receive only a separate authorized projection
  when the mutation affects their usable state.

## EvidenceChangeCoverageCheckpoint v1

Schema:

    relaylm.evidence_change_coverage_checkpoint.v1

Fields:

schema
change_coverage_checkpoint_id
change_partition_id
partition_epoch_id
coverage_revision
expected_previous_coverage_revision_or_null
start_sequence
highest_seen_sequence_or_null
highest_contiguous_committed_sequence_or_null
missing_sequence_ranges
nonterminal_sequence_ranges
partition_status
derived_coverage_status
change_basis_digest_or_null
updated_at
issuer_principal_ref
issuer_authority_scope
operation_idempotency_key

Rules:

- same empty/gap/range/revision principles as source-capture coverage;
- change basis digest covers `(partition_sequence, projection_event_id)` from
  start through highest contiguous committed;
- consumer observes only its authorized partition;
- no filtered global stream exists;
- missing a private event in another partition creates no local gap;
- RelayCTX may read its partition coverage but cannot advance it;
- consumer cursor/acknowledgement belongs to Contract 3;
- RelaySLP job coverage is separate;
- source-capture coverage cannot substitute for change coverage.

## Required partition planning examples

Participant-private source admission:

- participant partition for producer;
- participant partitions for authorized recipients if policy requires;
- no shared-scene projection unless occurrence audience permits;
- no quarantine/security projection unless needed.

Shared-scene source admission:

- shared_scene partition;
- participant projections only when participant-local current state differs.

Quarantined source:

- quarantine_control partition;
- security_control partition when security reason exists;
- no normal participant/shared-scene source ID projection before release.

Quarantine release:

- normal authorized partition projections receive candidate_available;
- quarantine partition receives terminal review effect.

Metadata correction affecting private audience:

- only partitions already authorized to know source existence receive
  metadata_recheck;
- no broad participant discovery.

Lineage between differently scoped endpoints:

- projection plan is intersection of consumers authorized to know both endpoints;
- otherwise emit separate endpoint-local control projections without revealing
  the other source ID;
- never emit a normal relation projection that leaks a quarantined/private
  endpoint.

Purge:

- every partition previously authorized to know source existence receives
  source_remove;
- unauthorized partitions receive nothing;
- quarantine/security control receives required audit effect.

## Logical atomicity and outbox boundary

A durable family mutation is downstream-complete only when:

1. authoritative mutation record commits;
2. AuthorityChangeSetEvent plan revision commits;
3. every required partition projection commits;
4. SourceProjectionRegistryEvent is updated for source-aware projections;
5. AuthorityChangeSetEvent mark_complete revision commits;
6. per-partition coverage may advance.

Physical transaction/outbox implementation belongs to storage contract.

Requirements:

- mutation and projection plan share one idempotency scope;
- an incomplete change set is recoverable by deterministic re-emission;
- a consumer cannot claim current state beyond an incomplete change set visible
  in its partition;
- underlying evidence remains protected and no duplicate mutation is created;
- recovery recreates same change set/projection IDs and sequences.

## Interruption and recovery

Capture stream crash after sequence reserve:
    sequence remains nonterminal; recover exact CaptureAttempt or terminalize
    aborted then recover.

Capture stream descriptor conflict:
    epoch unverifiable; block new reservation; recovery/migration authority
    creates new epoch only after reconciliation.

Change mutation committed, projection missing:
    change set remains planned; deterministic outbox recovery emits missing
    exact projection.

Partition sequence duplicate with different event:
    partition corrupt; consumers fail closed.

Consumer crash:
    resume using own partition cursor and coverage; replay projection events,
    then resolve current authoritative records.

Partition retired:
    no new event; successor partition uses new epoch/descriptor and explicit
    handoff under owning consumer contract.

## Acceptance gates

- Source capture stream has a formal descriptor/lifecycle.
- Empty and pending streams are representable.
- Missing and nonterminal ranges are distinct.
- No per-chunk assistant sequence exists.
- Sequence reservation abort cannot create silent permanent gap.
- Authority changes are privacy-partitioned, not globally filtered.
- Quarantined/private source existence cannot leak through sequence gaps.
- Relation projections do not expose unauthorized endpoints.
- SourceProjectionRegistry preserves prior visibility needed for revocation and
  purge propagation.
- Projection abort recovery cannot strand a planned change set.
- Every mutation has a complete projection plan.
- Consumer cursor and RelaySLP job coverage remain outside this contract.
