---
relaylm_doc_type: contract
relaylm_authority: governed_source_capture_canonical_sourceevent_admission_quarantine_replay_and_validation_binding
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evidence_admission
relaylm_update_trigger:
  - SourceEvent, source payload, capture attempt, admission, quarantine, replay, or validation-bundle rules change
  - route capture snapshot interface changes
  - Contract 1E response binding changes
relaylm_not_authoritative_for:
  - route lifecycle or route selection
  - evidence retention, grants, redaction, or purge
  - metadata correction, lineage, or derived-artifact lifecycle
  - source-capture stream implementation or authority-change delivery
  - exact assistant streaming/finalization details owned by Contract 1E
  - RelayATN turn admission, RelayCTX state, RelayREF semantics, RelaySLP jobs, or memory formation
  - physical payload storage or migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - ../adr/relayatn_pre_request_authority_separation.md
relaylm_related_contracts:
  - governed-evidence-contract-family.md
  - evidence-governance-access.md
  - source-metadata-lineage-derived-artifacts.md
  - evidence-streams-change-feed.md
  - assistant-response-evidence-binding.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1A v7: Governed Source Capture and Admission

This document is authoritative for governed source capture, immutable SourceEvent creation, admission, quarantine review, replay resolution, and validation-bundle binding.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This contract owns:

- acceptance of an external route capture grant snapshot;
- capture-attempt lifecycle after a source-capture sequence is reserved;
- canonical source manifest identity;
- immutable SourceEvent creation;
- admission outcome and authoritative completeness;
- quarantine disposition and terminal review pairing;
- exact replay/revision handling;
- current validation-bundle binding.

It does not own route configuration lifecycle, stream sequencing, governance,
metadata correction, lineage, RelayREF semantics, or physical payload storage.

## Contract 1A authority operations

AuthorityScope.allowed_operations uses only:

capture_attempt_reserve
capture_attempt_begin_content
capture_attempt_finalize_candidate
capture_attempt_bind_admission
capture_attempt_terminal_no_source
capture_attempt_mark_abandoned
capture_attempt_recover
admission_decide
admission_review_decide
validation_bundle_create
validation_bundle_revise

No unlisted operation is valid.

## External RouteCaptureGrantSnapshot interface

Schema:

    relaylm.route_capture_grant_snapshot.v1

This is an immutable snapshot issued by an external route contract.

Fields:

schema
route_binding_id
route_contract_ref
route_contract_revision
route_contract_snapshot_digest
evidence_space_id
route_mode
capture_profile
allowed_origin_kinds
allowed_capture_stream_kinds
allowed_stream_directions
effective_from
expires_at_or_null
revocation_revision_observed
validated_at
validator_principal_ref
validator_authority_scope

route_mode:
    managed_conversation
    explicit_pass_through
    tool_transaction
    authorized_import
    governed_system

capture_profile:
    managed_user_input
    managed_assistant_response
    pass_through_explicit_opt_in
    tool_transaction_evidence
    authorized_import_evidence
    governed_system_evidence

Rules:

- Contract 1A does not issue, supersede, revoke, or select this snapshot;
- snapshot evidence space MUST match the current EvidenceSpaceDescriptor;
- managed_conversation permits only managed_user_input and
  managed_assistant_response;
- explicit_pass_through permits capture only with
  pass_through_explicit_opt_in;
- tool_transaction_evidence requires a separate tool transaction contract;
- validated_at MUST be inside effective/expiry bounds;
- revocation_revision_observed MUST be current at validated_at;
- missing, expired, revoked, conflicting, or cross-space snapshot creates no
  Contract 1 CaptureAttempt;
- capture denial is a content-free route diagnostic outside Contract 1;
- later route expiry blocks new attempts but does not erase an already reserved
  in-flight attempt;
- an external security cancellation MAY force an in-flight attempt to terminate
  without SourceEvent, but cannot erase already emitted assistant output.

## Capture channel

capture_channel:
    managed_text
    managed_voice_input
    managed_assistant_text
    tool_result
    sensor
    authorized_import
    governed_system
    pass_through_opt_in

Closed cross-field matrix:

- managed_user_input:
  stream kind managed_user_input;
  direction inbound;
  source role user_input;
  channel managed_text or managed_voice_input.

- managed_assistant_response:
  stream kind managed_assistant_output;
  direction outbound;
  source role assistant_response;
  channel managed_assistant_text;
  requires Contract 1E binding.

- pass_through_explicit_opt_in:
  stream kind pass_through_opt_in;
  direction explicitly permitted by snapshot;
  source role/channel explicitly permitted by snapshot.

- tool_transaction_evidence:
  stream kind tool_transaction;
  direction inbound, outbound, or internal as the tool contract permits;
  source role tool_result or tool_action.

- authorized_import_evidence:
  stream kind authorized_import;
  direction import;
  source role imported_source.

- governed_system_evidence:
  stream kind governed_system_event;
  direction internal;
  source role system_source.

No unlisted combination is valid.

## CaptureAttemptEvent v1

Schema:

    relaylm.capture_attempt_event.v1

Capture attempt lifecycle is append-only.

Common fields:

schema
capture_attempt_event_id
capture_attempt_id
attempt_revision
expected_previous_attempt_revision_or_null
evidence_space_id
capture_stream_epoch_id
capture_sequence
route_capture_grant_snapshot_ref
capture_channel
source_role
operation
operation_payload
recorded_at
operation_idempotency_key
authority_principal_ref
authority_scope

operation:
    reserve
    begin_content
    finalize_candidate
    bind_admission
    terminal_no_source
    mark_abandoned_recoverable
    recover_abandoned

source_role:
    user_input
    assistant_response
    tool_result
    tool_action
    sensor_result
    imported_source
    system_source

### reserve payload

capture_stream_kind
stream_direction
temporary_control_ref
response_capture_reservation_ref_or_null

Rules:

- revision 1 only;
- sequence MUST already be reserved by Contract 1D;
- assistant_response requires Contract 1E response reservation;
- no source payload is required at reserve time.

### begin_content payload

temporary_payload_handle
first_content_observed_at
content_observation_basis

Rules:

- prior state reserved;
- content handle is temporary and not source identity;
- assistant response uses Contract 1E canonical output-boundary observation.

### finalize_candidate payload

preallocated_source_event_id_or_null
canonical_source_manifest
canonical_source_manifest_digest
temporary_payload_part_handles
validation_bundle_id
validation_bundle_revision
finalization_basis_ref

Rules:

- prior state reserved or collecting;
- canonical manifest digest MUST verify;
- every content-bearing part has one temporary payload handle at candidate
  finalization;
- preallocated_source_event_id is required only when the admission path is
  preparing admitted/quarantined authoritative bundle creation;
- ProtectedPayloadBindingAttestation records are created only for admitted/quarantined
  SourceEvents, never for ephemeral/rejected/duplicate outcomes;
- assistant response finalization basis is Contract 1E;
- hidden reasoning and generated-but-not-emitted assistant content are forbidden.

### bind_admission payload

admission_decision_id

Rules:

- prior state finalizing;
- referenced AdmissionDecision is complete and terminal;
- retry with a different decision ID is an integrity conflict.

### terminal_no_source payload

terminal_reason
terminal_at

terminal_reason:
    no_canonical_content_observed
    assistant_output_not_emitted
    external_security_cancel_before_source
    route_cancel_before_source

Rules:

- no SourceEvent and no AdmissionDecision exist;
- temporary content is absent or disposed;
- this terminal state closes the reserved capture sequence.

### mark_abandoned_recoverable payload

abandon_reason
abandoned_at
recovery_case_ref
last_verified_attempt_state

last_verified_attempt_state:
    reserved
    collecting
    finalizing

Rules:

- only recovery/capture-stream authority may use it;
- it contains no source content;
- it is not terminal and Contract 1D keeps the sequence nonterminal;
- a later recover_abandoned event is required.

### recover_abandoned payload

recovery_case_ref
recovered_attempt_state
recovery_basis_ref

recovered_attempt_state:
    reserved
    collecting
    finalizing

Rules:

- exact prior mark_abandoned_recoverable event required;
- recovered state cannot advance beyond trusted recovery evidence;
- recovery never fabricates source content or admission;
- normal attempt processing resumes from recovered state.

### Capture attempt resolver

- revisions start at 1 and are gap-free;
- reserve -> begin_content? -> finalize_candidate -> bind_admission is the normal
  source path;
- reserve -> terminal_no_source is a valid no-source path;
- any nonterminal state -> mark_abandoned_recoverable -> recover_abandoned is a
  valid recovery detour;
- terminal states are bind_admission and terminal_no_source only and are
  immutable;
- two conflicting events at the same revision make the attempt corrupt;
- timestamps never replace revision ordering;
- attempt ID and sequence are never reused.

## CanonicalSourceManifest v1

Schema:

    relaylm.canonical_source_manifest.v1

Canonical encoding:

- JSON Canonicalization Scheme compatible with RFC 8785;
- UTF-8 without BOM;
- duplicate object keys forbidden;
- arrays preserve declared order;
- sets are sorted unique arrays;
- non-finite numbers forbidden;
- schema version is included in the object.

Text content digest:

- digest input is UTF-8 without BOM of the exact Unicode scalar sequence after
  trusted transport decoding;
- no Unicode normalization is performed;
- invalid Unicode scalar input is rejected or represented as binary media.

Fields:

schema
occurrence_kind
parts
manifest_extensions

occurrence_kind:
    message
    assistant_response
    action
    tool_result
    sensor_result
    setting_change
    lifecycle_request
    import_record
    system_event

manifest_extensions:
    empty object in v1

### SourceReference v1

Fields:

reference_kind
reference_id
reference_scope

reference_kind:
    source_event
    external_resource
    import_manifest
    governed_system_resource

reference_scope:
    whole_resource
    bounded_fragment

Rules:

- reference ID is opaque and content-free;
- cross-space SourceEvent reference is forbidden;
- external resources do not become trusted source authority merely by reference.

### SourcePartManifest

Fields:

part_id
part_kind
media_type
byte_length_or_null
content_digest_or_null
initial_disposition
part_origin
part_derivation_class
represented_source_ref_or_null
reference_basis_or_null
omission_reason_code_or_null

part_kind:
    text
    audio
    image
    video
    structured
    binary
    reference

initial_disposition:
    protected
    quarantine_only
    reference_only
    omitted_secret
    omitted_security
    omitted_policy

part_origin:
    participant_authored
    assistant_authored
    tool_produced
    sensor_produced
    system_produced
    quoted_external
    forwarded_external
    imported_external
    unknown_external

part_derivation_class:
    direct_occurrence
    model_generated
    product_knowledge_derived
    tool_derived
    transformed_external
    unknown

reference_basis:
    trusted_transport_reference
    trusted_runtime_response_reference
    verified_import_manifest
    explicit_source_confirmation

Cross-field rules:

- parts is ordered, non-empty, and has unique part IDs;
- byte_length is a non-negative integer;
- protected/quarantine_only require byte_length and content_digest;
- reference_only requires null byte_length/content_digest and a valid
  SourceReference in represented_source_ref_or_null;
- omitted dispositions require null byte_length/content_digest and an omission
  reason;
- non-omitted parts require null omission reason;
- secret/security omitted parts retain no raw digest in personal evidence;
- unknown_external cannot be admitted for participant-authored use;
- participant_authored normally uses direct_occurrence;
- assistant_authored uses model_generated, product_knowledge_derived,
  tool_derived, or transformed_external;
- product_knowledge_derived preserves assistant origin and never becomes
  participant fact or product-corpus authority;
- an initially admitted SourceEvent has no initial quarantine_only part;
- omitted bytes are intentionally outside replay equality.

## ProtectedPayloadBindingAttestation v1

Schema:

    relaylm.protected_payload_binding_attestation.v1

Fields:

schema
payload_binding_attestation_id
source_event_id
part_id
content_digest
storage_binding_ref
storage_binding_schema
storage_authority_ref
attested_at
attester_principal_ref
attester_authority_scope

Rules:

- SourceEvent ID is preallocated for an admitted/quarantined candidate before
  attestation creation;
- temporary pre-admission payload uses CaptureAttempt temporary handles and is
  never a ProtectedPayloadBindingAttestation;
- this attestation states only that the storage authority accepted one logical
  source part with the exact content digest;
- storage_binding_ref is opaque and is not a locator;
- physical locator, encryption, key, replica, revision, migration, and erasure
  lifecycle belong exclusively to Contract 5/storage authority;
- SourceEvent references the immutable attestation ID;
- content_digest MUST equal the manifest part digest;
- attester authority MUST identify the external storage authority interface;
- attestation and storage refs are excluded from canonical source identity and
  replay equality;
- a later physical binding revision does not change this attestation or
  SourceEvent;
- lost/invalid storage binding makes content inaccessible under Contract 1B but
  does not change source identity.

## SourceReplayIdentity v1

Tagged union:

1. trusted_connector_identity
   - connector_instance_ref
   - upstream_event_id
   - upstream_revision_id_or_null
   - idempotency_key_or_null

2. managed_response_identity
   - response_id
   - delivery_cohort_id
   - response_finalization_idempotency_key
   - canonical_response_binding_digest

3. verified_import_identity
   - import_manifest_id
   - import_row_id
   - import_revision_id_or_null

4. deterministic_system_identity
   - system_event_namespace
   - system_event_id
   - system_revision_id_or_null

5. none
   - permitted only when policy requires content-digest-based distinct admission;
   - retries cannot claim duplicate without another trusted identity.

Rules:

- correctable speaker, audience, occurrence time, or provenance metadata are not
  part of replay identity;
- raw transport digest is not replay identity;
- managed assistant response identity is owned by Contract 1E;
- same trusted identity and same canonical manifest -> duplicate;
- same trusted identity and different canonical manifest -> integrity conflict,
  except a trusted upstream revision creates a new SourceEvent;
- same text at a different occurrence is not duplicate.

## Source occurrence metadata value objects

### SourceOccurrenceTime v1

Fields:

raw_value_or_null
parsed_instant_or_null
timezone_or_offset_or_null
trust

trust:
    trusted_source
    trusted_transport
    asserted
    inferred
    unknown

Rules:

- parsed instant is RFC 3339 UTC when present;
- timezone/offset is retained when supplied;
- inferred time is metadata only and never semantic valid-from/valid-until;
- absence is explicit null, not current time.

### OccurrenceAudienceSnapshot v1

Fields:

audience_class
participant_refs
room_ref_or_null
shared_scene_ref_or_null
trust

audience_class:
    private_direct
    private_group
    shared_scene
    public
    system_internal
    unknown

trust:
    trusted_transport
    trusted_route
    asserted
    unresolved

Cross-field rules:

- private_direct requires participant refs and null room/shared-scene;
- private_group requires participant refs and MAY include room;
- shared_scene requires exactly one room/shared-scene ref;
- public requires no private participant refs;
- system_internal uses service/system principals only;
- unknown cannot authorize normal participant, export, or replication access;
- participant refs are protected metadata.

### ProvenanceSnapshot v1

Fields:

capture_method
provenance_assurance
independence_status
independence_group_id_or_null
independence_basis_or_null
source_material_classes

capture_method:
    trusted_connector
    managed_runtime
    verified_import
    trusted_tool
    trusted_sensor
    governed_system
    untrusted_external

provenance_assurance:
    verified
    asserted
    unresolved
    conflicting

independence_status:
    independent
    same_origin_group
    unknown

source_material_class:
    personal_source
    assistant_generation
    product_knowledge_derived
    tool_derived
    external_reference
    system_policy
    unknown

Rules:

- source material classes are sorted unique;
- product_knowledge_derived marks assistant output provenance only and does not
  copy product corpus into personal evidence authority;
- conflicting provenance blocks normal access/admission as policy requires;
- independence metadata is candidate evidence only, never truth authority.

## SourceEvent v1

Schema:

    relaylm.source_event.v1

Fields:

schema
source_event_id
evidence_space_id
evidence_space_descriptor_revision
capture_attempt_id
capture_stream_epoch_id
capture_sequence
route_capture_grant_snapshot_ref
received_at
observed_at
capture_channel
source_role
origin_kind
producer_principal_ref
authenticated_account_ref_or_null
represented_speaker_ref_or_null
speaker_identity_status
source_occurrence_time
configured_occurrence_audience
scene_occurrence_ref_or_null
conversation_ref_or_null
canonical_source_manifest
canonical_source_manifest_digest
protected_payload_binding_attestation_ids
source_replay_identity
assistant_response_binding_ref_or_null
provenance_snapshot
authority_change_set_ref

origin_kind:
    participant
    assistant
    tool
    sensor
    system
    import
    external

speaker_identity_status:
    verified
    asserted
    unresolved
    conflicting
    not_applicable

Rules:

- immutable after creation;
- no extension_data in v1;
- manifest digest verifies canonical manifest;
- payload binding attestation IDs are sorted unique and excluded from manifest digest and
  replay identity;
- every protected/quarantine_only content part has exactly one payload binding attestation;
- reference/omitted parts have no payload binding attestation;
- assistant_response requires origin assistant and Contract 1E binding;
- every other occurrence requires null assistant response binding;
- source_occurrence_time uses SourceOccurrenceTime v1;
- configured audience uses OccurrenceAudienceSnapshot v1 and is source
  occurrence metadata, not future read permission;
- provenance uses ProvenanceSnapshot v1;
- source event does not contain semantic truth, Subjective MEM, RelayREF output,
  current CTX, or mutable governance;
- corrections never rewrite this record;
- purge destroys/restricts payload through Contract 1B and may leave only a
  tombstone/control reference.

## ValidationBundleRevision v1

Schema:

    relaylm.admission_validation_bundle_revision.v1

Fields:

schema
validation_bundle_revision_id
validation_bundle_id
capture_attempt_id
source_event_id_or_null
bundle_revision
expected_previous_bundle_revision_or_null
bundle_state
gate_requirements
active_artifact_refs
policy_snapshot_ref
authority_principal_ref
authority_scope
recorded_at
authority_change_set_ref_or_null

bundle_state:
    valid
    invalidated
    held

GateRequirement fields:

requirement_id
gate_kind
required_result

gate_kind:
    canonicalization
    integrity
    malware
    secret
    route_authority
    assistant_finalization
    import_authority

Rules:

- revision starts at 1 and is gap-free;
- capture_attempt_id is immutable across revisions;
- source_event_id is null for non-SourceEvent outcomes and otherwise fixed from
  revision 1 using a preallocated SourceEvent ID;
- active artifact refs point to Contract 1C artifacts;
- each requirement has exactly one current satisfying artifact when bundle_state
  is valid;
- artifact replacement creates a new bundle revision;
- invalidating an old artifact does not permanently strand evidence when a later
  valid bundle revision exists;
- current eligibility uses the latest complete bundle revision, not only the
  immutable AdmissionDecision's original artifact IDs;
- gaps/conflicts make the bundle invalidated;
- a new valid revision for an existing SourceEvent emits an authority change
  set; pre-SourceEvent or non-SourceEvent validation may keep the ref null;
- the initial admitted/quarantined SourceEvent, AdmissionDecision, validation
  revision, and Contract 1B governance revision 1 reserve the same
  AuthorityChangeSetRef.

## ReplayResolution v1

Tagged union:

1. new_source
   - source_event_id

2. existing_source
   - existing_source_event_id
   - checked_governance_revision

3. purged_tombstone
   - purged_evidence_tombstone_id
   - checked_purge_governance_revision

4. none

Rules:

- admitted/quarantined use new_source and the ID equals
  source_event_id_or_null;
- duplicate_replay uses existing_source and creates no new SourceEvent;
- rejected_purged_exact_replay uses purged_tombstone;
- ordinary ephemeral/rejected outcomes use none;
- checked revision is part of replay/purge race validation;
- replay resolution grants no content access and never reactivates purged
  evidence.

## AdmissionDecision v1

Schema:

    relaylm.evidence_admission_decision.v1

Fields:

schema
admission_decision_id
capture_attempt_id
evidence_space_id
operation_idempotency_key
outcome
primary_reason_code
reason_codes
decided_at
decider_principal_ref
decider_authority_scope
policy_snapshot_ref
route_capture_grant_snapshot_ref
replay_resolution
canonical_source_manifest_digest_or_null
validation_bundle_id_or_null
validation_bundle_revision_or_null
source_event_id_or_null
initial_governance_event_id_or_null
authority_change_set_ref_or_null

outcome:
    admitted
    quarantined
    ephemeral
    rejected
    duplicate_replay

Reachable reason codes:

admitted_policy_valid
admitted_managed_assistant_response
quarantined_identity
quarantined_audience
quarantined_authorization
quarantined_security
quarantined_integrity
quarantined_source
ephemeral_policy_only
rejected_content_policy
rejected_security_policy
rejected_authorization
rejected_schema_invalid
rejected_integrity_conflict
rejected_purged_exact_replay
duplicate_exact_replay

Rules:

- reason codes are sorted unique and include primary reason;
- route-capture denial and no-output terminalization are not AdmissionDecision
  outcomes because no source candidate exists;
- admitted/quarantined require replay_resolution=new_source, non-null
  source_event_id, initial_governance_event_id, validation bundle,
  canonical manifest digest, and AuthorityChangeSetRef;
- ephemeral and ordinary rejected outcomes require replay_resolution=none,
  null source/governance IDs, and null AuthorityChangeSetRef;
- rejected_purged_exact_replay requires replay_resolution=purged_tombstone;
- duplicate_replay requires replay_resolution=existing_source, null new
  source/governance IDs, and null AuthorityChangeSetRef;
- ephemeral/rejected/duplicate create no new SourceEvent or
  ProtectedPayloadBinding;
- RelayREF availability is never an admission prerequisite;
- evidence outcome does not decide RelayATN turn admission or guarantee turn
  continuation;
- same idempotency key with different canonical body is an integrity conflict.

## Outcome-specific authoritative completeness

Admitted:

- complete CaptureAttempt chain through finalize_candidate;
- SourceEvent;
- AdmissionDecision admitted;
- ValidationBundle latest revision valid;
- Contract 1B initialize_admitted governance revision 1;
- SourceEvent, AdmissionDecision, current ValidationBundle revision, and
  Contract 1B governance revision 1 share one complete AuthorityChangeSet.

Quarantined:

- complete CaptureAttempt chain;
- SourceEvent;
- AdmissionDecision quarantined;
- ValidationBundle sufficient for safe quarantine retention;
- Contract 1B initialize_quarantined revision 1 with review/disposal deadlines;
- SourceEvent, AdmissionDecision, current ValidationBundle revision, and
  Contract 1B governance revision 1 share one complete AuthorityChangeSet.

Ephemeral:

- complete CaptureAttempt chain;
- AdmissionDecision ephemeral;
- temporary content disposal deadline durably registered;
- no SourceEvent.

Rejected:

- complete CaptureAttempt chain;
- AdmissionDecision rejected;
- temporary content disposed or disposal durably registered;
- no SourceEvent.

Duplicate replay:

- complete CaptureAttempt chain;
- AdmissionDecision duplicate_replay;
- existing non-purged SourceEvent identity and current governance revision
  verified under Contract 1B;
- no new SourceEvent.

Purged exact replay suppressed:

- complete CaptureAttempt chain;
- AdmissionDecision rejected with rejected_purged_exact_replay;
- matching Contract 1B keyed tombstone verified;
- no old SourceEvent content or identity is reactivated;
- no new SourceEvent.

Purged exact replay admitted as a new occurrence:

- policy explicitly permits a new occurrence;
- new SourceEvent ID and current retention/governance are created;
- no lineage to reconstruct the purged source content;
- the old source ID remains terminally purged.

No-source:

- CaptureAttempt terminal_no_source;
- no AdmissionDecision;
- no SourceEvent.

AdmissionReceipt is irrelevant to all predicates.

## Quarantine reason-to-purpose map

quarantined_identity:
    quarantine_identity_review

quarantined_audience:
    quarantine_audience_review

quarantined_authorization:
    quarantine_authorization_review

quarantined_security:
    quarantine_security_review

quarantined_integrity:
    quarantine_integrity_review

quarantined_source:
    quarantine_source_review

Rules:

- required review purposes are the all-of mapping of every quarantine reason;
- one reviewer need not own every purpose;
- Contract 1B issues one purpose-specific quarantine authorization per reviewer;
- release requires every required purpose to have an accepted review result;
- review purpose not derived from a reason is forbidden.

## AdmissionReviewDecision v1

Schema:

    relaylm.admission_review_decision.v1

Fields:

schema
review_decision_id
source_event_id
evidence_space_id
reviewed_governance_revision
reviewed_metadata_revision
reviewed_validation_bundle_revision
required_review_purposes
accepted_review_result_refs
outcome
primary_reason_code
reason_codes
reviewer_principal_refs
reviewer_authority_scope_refs
policy_snapshot_ref
paired_governance_event_id
authority_change_set_ref
operation_idempotency_key
decided_at

outcome:
    released_as_admitted
    rejected_from_evidence

Effectiveness rules:

- the decision record is effective only if Contract 1B commits the exact paired
  next governance revision with matching CAS preconditions;
- an unpaired or failed-CAS review record is inert audit evidence;
- at most one effective terminal pair exists because the governance revision is
  gap-free and compare-and-set;
- conflicting inert proposals do not block a later valid pair;
- two effective pairs imply storage split-brain and mark the source corrupt;
- release requires current valid validation bundle and all required review
  purposes;
- rejection requires disposal/purge registration under Contract 1B;
- review and governance share one AuthorityChangeSetRef.

## Admission disposition resolver

- initial admitted -> admitted;
- initial quarantined with no effective terminal pair -> quarantined;
- initial quarantined plus effective release pair -> admitted;
- initial quarantined plus effective rejection pair -> rejected_from_evidence;
- ephemeral/rejected/duplicate/no-source never become SourceEvent admission;
- stale metadata, governance, validation bundle, or review precondition blocks
  the new transition but does not rewrite historical initial outcome.

## Replay and correction rules

- replay matching uses SourceReplayIdentity and canonical manifest only;
- metadata-correctable differences do not create payload conflict;
- trusted later upstream revision creates a new SourceEvent and Contract 1C
  transport_revision_of lineage;
- incorrect trusted replay identity requires a recovered new SourceEvent and
  Contract 1C recovered_transport_rebind_of or
  recovered_runtime_response_rebind_of;
- natural-language correction without exact confirmed target creates no
  authoritative lineage;
- purge does not reactivate the prior SourceEvent;
- duplicate_replay applies only to a non-purged existing source;
- a keyed tombstone match resolves to rejected_purged_exact_replay or a
  policy-authorized new occurrence;
- duplicate/tombstone decisions bind the checked governance/tombstone revision
  and re-evaluate on concurrent purge.

## Managed request/response timing boundary

Managed user input:

- route snapshot and sequence reservation occur before the ordinary request path;
- evidence admission and turn admission remain independent;
- later response failure does not roll back admitted input evidence;
- live current-request transport is not a stored-evidence read.

Managed assistant output:

- Contract 1E reserves response capture before first canonical output emission;
- first token does not wait for evidence finalization, RelayREF, or RelaySLP;
- exactly one delivery-cohort SourceEvent may result per response binding;
- no per-chunk SourceEvent exists;
- partial output is bound only to content observed at the canonical output
  boundary;
- no-output terminalizes the capture attempt without AdmissionDecision.

## Failure behavior

Missing/invalid route snapshot:
    no Contract 1 capture; external content-free route diagnostic only.

Capture reservation exists, no content:
    terminal_no_source.

Canonicalization fails:
    rejected_schema_invalid if source candidate exists; otherwise terminal_no_source.

Same replay identity, conflicting manifest:
    rejected_integrity_conflict and integrity/security handling.

Validation artifact invalidated:
    latest ValidationBundle becomes invalid; current use fails closed; later
    valid ValidationBundleRevision may restore eligibility.

Quarantine review conflict:
    failed-CAS proposals remain inert; only paired next governance revision is
    effective.

Storage binding unavailable:
    SourceEvent identity remains; content access fails closed under Contract 1B.

## Acceptance gates

- RouteCaptureGrantSnapshot is validated but not lifecycle-owned here.
- No unreachable admission reason exists.
- CaptureAttempt no-source and source paths are both terminal.
- Canonical manifest excludes storage locator and optional forensic digest.
- SourceEvent contains no v1 extension escape hatch.
- Replay identity is a tagged union.
- Correctable metadata is outside replay equality.
- Validation artifact replacement can create a later valid bundle revision.
- Quarantine reason-purpose mapping is exact and all-of.
- Review effectiveness is paired-governance CAS, not timestamp precedence.
- Evidence outcome does not force turn continuation.
- Assistant output relies on Contract 1E pre-emission reservation.
