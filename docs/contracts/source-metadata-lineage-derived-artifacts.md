---
relaylm_doc_type: contract
relaylm_authority: effective_source_metadata_source_lineage_and_derived_artifact_lifecycle
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evidence_provenance
relaylm_update_trigger:
  - effective source metadata correction rules change
  - lineage relation or correction/retraction semantics change
  - RelayREF, accessibility, integrity, or security artifact lifecycle changes
  - validation bundle interface changes
relaylm_not_authoritative_for:
  - SourceEvent admission or replay identity
  - evidence retention, access grants, redaction, or purge
  - stream sequencing or consumer change-feed coverage
  - exact RelayREF model/prompt/output semantic schema
  - Shared Assessment, Subjective MEM, or physical derived-content storage
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_contracts:
  - governed-evidence-contract-family.md
  - governed-source-capture-admission.md
  - evidence-governance-access.md
  - evidence-streams-change-feed.md
  - assistant-response-evidence-binding.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1C v7: Source Metadata, Lineage, and Derived Artifacts

This document is authoritative for effective source metadata revisions, source lineage, and derived-artifact lifecycle and governance inheritance.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This contract owns:

- effective source metadata correction without SourceEvent rewrite;
- append-only source lineage;
- derived artifact creation, supersession, invalidation, and governance
  inheritance;
- exact RelayREF observation classification as an advisory artifact class;
- authoritative integrity/security artifact lifecycle consumed by Contract 1A
  validation bundles.

It does not own source admission, evidence access, stream ordering, RelayREF
model implementation, semantic truth, Shared Assessment, or memory formation.

## Contract 1C authority operations

metadata_correct
lineage_create
lineage_retract
lineage_supersede
artifact_create
artifact_supersede
artifact_invalidate
artifact_revalidate

## SourceMetadataRevision v1

Schema:

    relaylm.source_metadata_revision.v1

Fields:

schema
metadata_revision_id
source_event_id
evidence_space_id
metadata_revision
expected_previous_metadata_revision_or_null
expected_governance_revision
expected_validation_bundle_revision
corrected_fields
correction_basis
validation_artifact_refs
authority_principal_ref
authority_scope
policy_snapshot_ref
recorded_at
authority_change_set_ref

Allowed corrected fields:

represented_speaker_ref_or_null
speaker_identity_status
configured_occurrence_audience
source_occurrence_time.parsed_instant_or_null
source_occurrence_time.timezone_or_offset_or_null
source_occurrence_time.trust
provenance_snapshot.provenance_assurance
provenance_snapshot.independence_status
provenance_snapshot.independence_group_id_or_null
provenance_snapshot.independence_basis_or_null

Forbidden corrected fields:

source_event_id
evidence_space_id
capture_attempt_id
capture_stream_epoch_id
capture_sequence
route_capture_grant_snapshot_ref
capture_channel
source_role
origin_kind
producer_principal_ref
authenticated_account_ref
canonical_source_manifest
canonical_source_manifest_digest
protected_payload_binding_attestation_ids
source_replay_identity
assistant_response_binding_ref

Rules:

- revision starts at 1 and is gap-free;
- expected governance/validation revisions MUST be current at commit;
- natural-language model inference alone cannot correct metadata;
- trusted transport/runtime/import authority, exact source confirmation, or
  evidence operator authority is required;
- authenticated account or replay identity correction requires a new recovered
  SourceEvent and lineage, not metadata revision;
- for assistant-response SourceEvents, configured audience correction that would
  conflict with the immutable Contract 1E reservation/binding requires a
  recovered binding, new SourceEvent, and recovered_runtime_response_rebind_of
  lineage;
- every old metadata-bound grant becomes stale by resolver immediately;
- correction cannot broaden access until Contract 1B revalidate_metadata creates
  replacement grants;
- privacy/security conflict additionally requires Contract 1B global restriction;
- original metadata remains protected audit history;
- effective metadata is revision 0 SourceEvent metadata plus complete revisions.

## Source replay and metadata difference rule

When a trusted retry has:

- same replay identity;
- same canonical source manifest;
- different correctable metadata;

Contract 1A treats the source as duplicate and MAY create a metadata correction
candidate. It does not create payload integrity conflict.

When replay identity itself differs or is proven incorrect, create a new recovered
SourceEvent and lineage.

## SourceLineageRelationEvent v1

Schema:

    relaylm.source_lineage_relation_event.v1

Fields:

schema
lineage_event_id
relation_id
relation_revision
expected_previous_relation_revision_or_null
evidence_space_id
operation
operation_payload
authority_principal_ref
authority_scope
policy_snapshot_ref
recorded_at
operation_idempotency_key
authority_change_set_ref

operation:
    create
    retract
    supersede

### Operation payloads

create:
    relation_type
    predecessor_source_event_ids
    successor_source_event_ids
    relation_payload

retract:
    retracted_relation_revision
    retraction_basis_ref

supersede:
    superseded_relation_revision
    replacement_relation_id
    supersession_basis_ref

Rules:

- retract/supersede operate on the existing relation_id;
- retract/supersede do not repeat or mutate the original endpoints/type;
- replacement_relation_id identifies a separately created valid relation;
- same operation idempotency key with different payload is an integrity conflict.

relation_type:
    transport_revision_of
    source_declares_correction_of
    source_declares_retraction_of
    source_adds_context_to
    assistant_response_to
    governance_redaction_successor_of
    recovered_transport_rebind_of
    recovered_runtime_response_rebind_of

### Closed relation payloads

transport_revision_of:
    trusted_transport_identity_ref
    previous_upstream_revision
    new_upstream_revision

source_declares_correction_of:
    exact_source_reference_ref
    confirmation_basis_ref
    correction_scope:
        whole_event
        explicit_part_ids
    corrected_part_ids

source_declares_retraction_of:
    exact_source_reference_ref
    confirmation_basis_ref
    retraction_scope:
        whole_event
        explicit_part_ids
    retracted_part_ids

source_adds_context_to:
    exact_source_reference_ref
    confirmation_basis_ref
    context_scope:
        whole_event
        explicit_part_ids
    contextualized_part_ids

assistant_response_to:
    runtime_response_reference
    delivery_cohort_id
    request_source_event_ids

governance_redaction_successor_of:
    redaction_governance_event_id
    redacted_part_ids
    sanitized_successor_part_ids

recovered_transport_rebind_of:
    recovery_case_ref
    incorrect_replay_identity_ref
    recovered_replay_identity_ref

recovered_runtime_response_rebind_of:
    recovery_case_ref
    original_response_binding_ref
    recovered_response_binding_ref

Rules:

- relation revision starts at 1 and is gap-free;
- predecessor/successor IDs are sorted unique non-empty where relation type
  requires them;
- all endpoints belong to the same evidence space;
- relation graph is acyclic except no relation type permits cycles in v1;
- exact trusted reference or explicit confirmation is required;
- natural-language-only correction without resolved target creates no relation;
- assistant_response_to is provenance only, not support/confirmation;
- assistant-origin material cannot correct/retract participant evidence on the
  participant's behalf;
- retraction of a lineage relation does not purge SourceEvents;
- supersede names replacement_relation_id and makes the prior relation inactive;
- purged endpoint makes relation unavailable to normal consumers;
- relation never reconstructs purged content.

## Active lineage resolver

- create revision 1 -> active;
- retract -> inactive;
- supersede -> inactive and replacement relation becomes active separately;
- gap/conflict -> unusable;
- purged endpoint -> unavailable_due_to_purge;
- normal consumers receive only active relations with currently authorized
  endpoints and metadata projections;
- audit consumers require Contract 1B authorization.

## SourceDerivedArtifactEvent v1

Schema:

    relaylm.source_derived_artifact_event.v1

Fields:

schema
artifact_event_id
derived_artifact_id
artifact_revision
expected_previous_artifact_revision_or_null
evidence_space_id
subject
artifact_kind
artifact_authority_class
operation
operation_payload
mutation_principal_ref
mutation_authority_scope
policy_snapshot_ref
recorded_at
operation_idempotency_key
authority_change_set_ref_or_null

subject tagged union:

1. capture_attempt
   - capture_attempt_id
2. source_event
   - source_event_id
3. source_payload_part
   - source_event_id
   - part_id
4. assistant_response_binding
   - assistant_response_binding_id

artifact_kind:
    text_projection
    speech_transcription
    ocr_projection
    language_detection
    source_reference_candidate
    speech_act_hint
    modality_hint
    temporal_expression_hint
    relayref_response_observation
    malware_scan_result
    secret_scan_result
    integrity_validation_result
    canonicalization_validation_result
    assistant_finalization_validation_result

artifact_authority_class:
    accessibility_projection
    integrity_gate
    security_gate
    advisory_semantic

operation:
    create
    supersede
    invalidate
    revalidate

### create payload

producer_name
producer_version
input_schema
input_digest
output_binding_ref_or_null
output_digest_or_null
result_status
source_governance_inheritance_ref

result_status:
    pass
    fail
    unavailable
    advisory_only

### supersede payload

superseded_artifact_revision
replacement_derived_artifact_id
supersession_basis_ref
required_governance_event_ref_or_null

### invalidate payload

invalidated_artifact_revision
invalidation_basis_ref
required_governance_event_ref_or_null

### revalidate payload

prior_inactive_artifact_revision
revalidation_basis_ref
result_status
new_output_binding_ref_or_null
new_output_digest_or_null
required_governance_event_ref_or_null

Rules:

- revision starts at 1 and is gap-free;
- artifact authority class is separate from actor AuthorityScope;
- integrity/security gate create, supersede, invalidate, or revalidate requires
  a non-null AuthorityChangeSetRef;
- advisory/accessibility artifact lifecycle MAY keep AuthorityChangeSetRef null
  unless current consumer eligibility changes;
- create establishes active;
- supersede/invalidate makes prior revision inactive;
- revalidate is allowed only after invalidate, never after supersede;
- supersede permanently closes the old derived_artifact_id and activates the
  separately created replacement ID;
- revalidate creates a new active revision on the same derived_artifact_id after
  invalidation;
- artifact lifecycle is acyclic;
- output binding is governed at least as strictly as the source subject;
- content-bearing accessibility/advisory outputs cannot gain broader audience,
  retention, locality, export, or replication eligibility than the source;
- hidden reasoning is forbidden;
- advisory artifacts cannot admit evidence, create lineage, determine truth,
  define temporal validity, grant access, or form MEM;
- integrity/security artifacts gate only named requirement IDs;
- artifact invalidation requires a Contract 1A ValidationBundleRevision when the
  artifact is currently used;
- required governance event ref links the exact Contract 1B restriction/recovery
  operation when current eligibility changes;
- mutation actor and policy are required for every operation.

## RelayREF observation artifact

relayref_response_observation requires:

- subject = assistant_response_binding;
- valid Contract 1E response binding;
- when a SourceEvent exists, it references the same binding;
- artifact_authority_class = advisory_semantic;
- output contains only the registered bounded observation schema;
- no full prompt, SOUL, all MEM, hidden reasoning, or unrelated history;
- no response content replacement;
- no completion-status authority;
- no user-origin conversion;
- no authority_change_set_ref unless the artifact is used as an authoritative
  gate, which RelayREF observation is not;
- immediate response-complete observation may use the safe binding/output
  boundary directly;
- delayed/replayed SourceEvent content read uses Contract 1B RelayREF
  authorization;
- a pre-admission advisory artifact is operationally bounded and is retained
  beyond temporary TTL only when an admitted/quarantined SourceEvent binds the
  same response binding;
- failure/unavailable does not invalidate assistant-origin Evidence.

Registered conceptual observation classes:

speech_act
answer_completion_candidate
clarification_requested_candidate
repair_or_apology_candidate
user_claim_repeated_candidate
assistant_inference_present_candidate
unsupported_assertion_candidate
topic_or_task_boundary_candidate
unresolved_reference_presence
observed_transport_or_completion_class

Exact semantic fields remain a later RelayREF contract.

## Integrity/security artifact binding

An authoritative artifact is valid for Contract 1A only when:

- active current artifact revision;
- exact input digest matches;
- subject/evidence space matches;
- artifact kind and authority class satisfy one named GateRequirement;
- producer/version is policy-allowed;
- actor mutation authority is valid;
- required Contract 1B governance restriction/recovery obligations are complete;
- current policy snapshot permits the result.

Replacing or revalidating an artifact does not rewrite AdmissionDecision.
Contract 1A advances ValidationBundleRevision.

## Derived content governance inheritance

For text projection, OCR, transcription, or advisory output:

- output binding belongs to the same evidence space;
- output has no independent broad AccessGrant;
- source part grant and metadata projection requirements still apply;
- output retention ends no later than source purge deadline;
- source redaction/purge makes output unavailable;
- output export/replication requires source eligibility plus explicit derived
  format inclusion;
- derived output cannot be used to recreate a purged source;
- storage/index contract must propagate restriction and purge.

## Metadata and lineage access

Normal consumers see only:

- current effective metadata selectors authorized by Contract 1B;
- active lineage whose endpoints and relation metadata are authorized;
- no original/revised metadata audit values unless full_authorized_audit;
- no private audience member list without explicit selector;
- no control correlation or replay identity by default.

## Failure behavior

Metadata revision gap:
    current metadata unavailable; normal access fails closed.

Correction attempts forbidden field:
    reject metadata revision; SourceEvent unchanged.

Conflicting exact relation:
    relation unusable; SourceEvents remain separate.

Natural-language correction unresolved:
    no authoritative lineage; possible advisory candidate only.

Authoritative artifact invalidated:
    current validation bundle becomes invalid; Contract 1B access fails closed;
    later revalidation and ValidationBundleRevision may restore eligibility.

Derived output storage unavailable:
    source identity unaffected; projection unavailable.

Purged source endpoint:
    lineage/derived output unavailable to normal consumers.

## Acceptance gates

- Metadata correction cannot alter replay identity or canonical manifest.
- Retry metadata difference is not payload conflict.
- Lineage payload is a closed union per relation type.
- assistant_response_to is provenance-only.
- recovered runtime finalization has an explicit relation.
- Artifact actor authority is distinct from artifact authority class.
- Artifact revalidation can restore a validation bundle.
- Derived content inherits source governance and cannot broaden access.
- RelayREF remains advisory and independent from response Evidence validity.
- Metadata and lineage projection are AccessGrant-controlled.
