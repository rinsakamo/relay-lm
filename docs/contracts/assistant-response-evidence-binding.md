---
relaylm_doc_type: contract
relaylm_authority: managed_assistant_response_capture_reservation_emitted_range_delivery_cohort_finalization_replay_and_recovery_binding
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: runtime_evidence_boundary
relaylm_update_trigger:
  - managed assistant streaming or response-complete finalization changes
  - emitted-range, delivery observation, response replay, or recovery rules change
  - pass-through assistant capture opt-in changes
  - Contract 1A assistant SourceEvent interface changes
relaylm_not_authoritative_for:
  - response generation call count or semantic response content
  - chunk transport protocol, TTS, avatar, or client rendering implementation
  - SourceEvent admission, evidence governance, RelayREF observation schema, RelayCTX state, or RelaySLP formation
  - physical storage, queue, transaction, or transport acknowledgement mechanics
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_contracts:
  - governed-evidence-contract-family.md
  - governed-source-capture-admission.md
  - evidence-governance-access.md
  - source-metadata-lineage-derived-artifacts.md
  - evidence-streams-change-feed.md
relaylm_verified_by:
  - ../../scripts/relaylm_contract1_v7_validate.py
  - ../../scripts/relaylm_contract1_v7_equivalence.py
---
# Contract 1E v7: Assistant-Response Evidence Binding

This document is authoritative for the managed runtime-to-evidence handoff for assistant response reservation, canonical output binding, finalization, delivery observation, and recovery.

**Status:** Target contract. It is normative for the adopted target boundary, but it is not evidence that the runtime, storage, migration, or deployment behavior is implemented.

## Purpose

This contract owns the exact runtime/evidence handoff for managed assistant output:

- pre-emission response capture reservation;
- one capture sequence per delivery cohort;
- canonical output-boundary observation;
- emitted range;
- completion extent, termination cause, and delivery observation;
- frozen request correlation;
- assistant response replay identity;
- no-output terminalization;
- crash recovery and corrected runtime binding.

It does not own response generation semantics, SourceEvent admission, evidence
governance, RelayREF semantic output, RelayCTX state, or RelaySLP formation.

## Core invariants

R-1. The first visible token MUST NOT wait for RelayREF, Shared Assessment,
Subjective MEM, or completed evidence admission.

R-2. A content-free capture reservation MUST exist before or atomically with
acceptance of the first canonical assistant-output unit.

R-3. One response delivery cohort uses one Contract 1D capture sequence, never
one sequence per chunk.

R-4. Evidence represents only content accepted at the canonical output boundary.
Generated-but-discarded content, hidden reasoning, unsafe removed content, and
unemitted model tokens are excluded.

R-5. Human-visible delivery is not overclaimed. Contract 1E records observation
basis and certainty.

R-6. RelayREF observation is separate, advisory, and post-response.

R-7. Same response identity plus conflicting finalization is integrity failure.

R-8. Pass-through creates no response reservation by default.

## Runtime finalization authority operation enum

response_capture_reserve
response_emission_begin
response_output_observe
response_finalize
response_terminal_no_output
response_mark_abandoned
response_recover_finalization

## ResponseCaptureReservation v1

Schema:

    relaylm.assistant_response_capture_reservation.v1

Fields:

schema
response_capture_reservation_id
response_id
run_id
turn_id_or_null
evidence_space_id
route_capture_grant_snapshot_ref
capture_stream_id
capture_stream_epoch_id
capture_sequence
delivery_cohort_id
configured_occurrence_audience
delivery_cohort_audience
audience_policy_basis_ref
request_source_refs
reservation_state
reserved_at
reservation_idempotency_key
runtime_principal_ref
runtime_finalization_authority_scope
policy_snapshot_ref

reservation_state:
    reserved

Audience rules:

- configured_occurrence_audience and delivery_cohort_audience use Contract 1A
  OccurrenceAudienceSnapshot v1;
- configured audience is the route/runtime maximum audience;
- delivery cohort audience is the exact intended audience for this binding;
- delivery cohort audience is a non-empty subset of configured audience;
- audience_policy_basis_ref identifies the route/runtime policy snapshot used;
- participant/audience refs are protected metadata and do not grant access.

RequestSourceRef fields:

ref_kind
ref_id
request_role

ref_kind:
    source_event
    admission_decision
    capture_attempt

request_role:
    triggering_input
    additional_current_input
    tool_or_protocol_input

Rules:

- ref_id resolves the record kind selected by ref_kind;
- each tuple is unique;
- control refs expose no source content.

Rules:

- reservation is content-free;
- Contract 1D sequence is reserved before first canonical output acceptance;
- route snapshot profile is managed_assistant_response or explicit
  pass-through opt-in;
- request refs are ordered unique and frozen at reservation;
- admitted input SHOULD use SourceEvent ref;
- quarantined/ephemeral/rejected/still-processing input MAY use control ref for
  correlation only;
- control refs grant no request content access and create no lineage;
- normal solicited response has at least one triggering input ref;
- empty request refs are allowed only for explicitly governed unsolicited output;
- delivery cohort audience is a non-empty subset of configured audience;
- one delivery cohort is intended to receive identical canonical output;
- canonical content divergence requires a separate reservation/sequence/binding;
- late transport/client delivery-status divergence does not split SourceEvent and
  is represented by DeliveryObservationEvent.

## ResponseCaptureEvent v1

Schema:

    relaylm.assistant_response_capture_event.v1

Fields:

schema
response_capture_event_id
response_capture_reservation_id
response_revision
expected_previous_response_revision_or_null
operation
operation_payload
operation_idempotency_key
recorded_at
runtime_principal_ref
runtime_finalization_authority_scope

operation:
    emission_begin
    output_observed
    finalize
    terminal_no_output
    mark_abandoned
    recover_finalization

### emission_begin payload

first_output_unit_sequence
canonical_output_boundary_ref
first_output_accepted_at

Rules:

- revision 1;
- reservation exists;
- emitted payload bytes need not be durable yet, but protected recoverable
  buffering or equivalent write-ahead evidence basis MUST exist;
- this operation and first canonical output acceptance share one crash-recovery
  boundary;
- no user-facing delay for RelayREF/SLP.

### output_observed payload

output_unit_sequence
part_id
accepted_range
observation_basis
observed_at
protected_output_buffer_ref

observation_basis:
    accepted_by_canonical_output_boundary

AcceptedRange fields:

unit
start_inclusive
end_exclusive

unit:
    utf8_byte
    unicode_scalar
    media_frame
    opaque_part_unit

Rules:

- output unit sequence increases monotonically;
- ranges are inside canonical safe output part;
- repeated unit uses same body/idempotency key;
- canonical output observation is authoritative for evidence binding;
- transport/client status is recorded only by DeliveryObservationEvent;
- TTS audio/avatar/rendering are not additional response parts by default.

### finalize payload

assistant_response_binding

Rules:

- prior state has at least one output observation;
- binding validates below;
- exactly one terminal finalization;
- Contract 1A CaptureAttempt may finalize candidate afterward.

### terminal_no_output payload

no_output_reason
terminal_at

no_output_reason:
    blocked_before_output
    generation_failed_before_output
    cancelled_before_output
    route_cancelled_before_output
    safe_output_empty

Rules:

- no accepted output range;
- Contract 1A CaptureAttempt terminal_no_source;
- no AdmissionDecision/SourceEvent.

### mark_abandoned payload

abandon_reason
last_known_output_unit_sequence_or_null
recovery_case_ref

Rules:

- used only when process cannot prove terminal finalization;
- if accepted output may exist, sequence remains nonterminal;
- recovery required.

### recover_finalization payload

recovery_case_ref
recovered_assistant_response_binding
recovery_basis_ref

Rules:

- reconstruct only from trusted protected output buffer, canonical output
  boundary record, and content-free stream/run identities;
- never regenerate from prompt/model;
- never infer exact response from RelayREF;
- recovered binding receives new binding ID but same response/cohort identity;
- Contract 1C recovered_runtime_response_rebind_of relates a replacement
  SourceEvent if original SourceEvent binding was incorrect.

## Response capture resolver

- reservation exists before every ResponseCaptureEvent;
- terminal_no_output MAY be revision 1 when no emission began;
- emission_begin is revision 1 for emitted output;
- output_observed follows emission_begin and may repeat with increasing revision;
- finalize follows at least one output_observed and is terminal;
- mark_abandoned is nonterminal and requires recover_finalization or
  terminal_no_output when trusted recovery proves no output;
- recover_finalization is terminal when it contains a valid recovered binding;
- two different terminal bindings or terminal outcomes are integrity conflict;
- timestamps never substitute for revision ordering.

## AssistantResponseBinding v1

Schema:

    relaylm.assistant_response_binding.v1

Fields:

schema
assistant_response_binding_id
response_capture_reservation_id
response_id
run_id
turn_id_or_null
delivery_cohort_id
request_source_refs
canonical_output_parts
completion_extent
termination_cause
first_output_accepted_at
finalized_at
first_output_unit_sequence
last_output_unit_sequence
output_unit_count
finalization_idempotency_key
finalization_basis_ref
runtime_principal_ref
runtime_finalization_authority_scope
canonical_binding_digest

completion_extent:
    response_complete
    response_partial

termination_cause:
    normal
    model_limit
    safety_stop
    user_cancel
    runtime_cancel
    backend_error
    timeout
    transport_error
    unknown

CanonicalOutputPart fields:

part_id
media_type
content_representation
accepted_ranges

Canonical binding digest input contains exactly:

response_id
run_id
turn_id_or_null
delivery_cohort_id
request_source_refs
canonical_output_parts
completion_extent
termination_cause
first_output_unit_sequence
last_output_unit_sequence
output_unit_count
finalization_idempotency_key

It excludes timestamps, finalization_basis_ref, runtime principal/scope, physical
buffer/storage references, and its own digest.

ContentRepresentation tagged union:

1. content_digest
   - digest_algorithm = sha256
   - digest_value
2. omission_marker
   - omission_reason:
       secret
       security
       policy
   - opaque_incident_ref_or_null

Rules:

- no binding with zero accepted output; use terminal_no_output;
- output unit count positive and consistent with first/last sequence;
- accepted ranges are ordered, non-overlapping, and exactly cover Contract 1A
  governed representation;
- completion_extent describes whether the runtime reached its
  response-complete boundary, not human delivery;
- termination_cause normal requires response_complete;
- model_limit and safety_stop MAY be response_complete when the runtime
  deliberately finalized the bounded response, otherwise response_partial;
- user_cancel, runtime_cancel, backend_error, and timeout are normally
  response_partial unless a response-complete boundary was already durably
  recorded before the later control event;
- transport_error MAY pair with response_complete or response_partial depending
  on canonical boundary completion;
- unknown is used only when trusted recovery cannot resolve cause;
- completion extent and termination cause are immutable binding axes;
- transport/client delivery observation is a separate append-only event stream;
- binding describes canonical boundary acceptance, not guaranteed transport or
  human sight;
- request source refs exactly equal frozen reservation refs and are not upgraded
  later;
- canonical_binding_digest verifies the exact canonical input above;
- same response/cohort/finalization identity and same canonical digest ->
  duplicate;
- same identity and different canonical digest -> integrity conflict;
- finalizer scope matches response/route/resource;
- first output time is not later than finalized time;
- output contains no hidden reasoning or discarded candidate;
- unsafe secret/security content may be represented by Contract 1A omitted
  manifest part and opaque security incident ref; personal evidence need not
  retain leaked bytes.

## DeliveryObservationEvent v1

Schema:

    relaylm.assistant_delivery_observation_event.v1

This append-only event records transport/client delivery evidence that may
arrive after immutable response binding.

Fields:

schema
delivery_observation_event_id
delivery_observation_series_id
assistant_response_binding_id
delivery_cohort_id
observation_revision
expected_previous_observation_revision_or_null
recipient_selector
observation_class
observed_ranges
observation_basis_ref
observed_at
observer_principal_ref
observer_authority_scope
operation_idempotency_key

recipient_selector tagged union:

1. whole_delivery_cohort
2. exact_participants
   - participant_refs: sorted unique non-empty
3. exact_adapter_session
   - adapter_session_ref

observation_class:
    canonical_boundary_only
    transport_write_confirmed
    client_acknowledged
    delivery_failed
    mixed_or_unknown

Rules:

- delivery_observation_series_id is stable for one binding and canonical
  recipient selector;
- revision starts at 1 per series and is gap-free;
- events never mutate AssistantResponseBinding or SourceEvent identity;
- observed ranges are bounded by binding accepted ranges;
- later stronger observation may supersede certainty but cannot change content;
- contradictory observations remain explicit and make delivery status unknown;
- recipient-specific observations are protected metadata under Contract 1B;
- delivery_failed after response_complete does not rewrite completion extent;
- delivery observations are excluded from response replay identity and canonical
  binding digest;
- no delivery observation becomes user-origin fact or evidence-content authority.

## Delivery cohort rules

v1 scope:

- one assistant response SourceEvent represents one delivery cohort;
- every cohort member is intended to receive identical canonical output;
- configured audience, cohort audience, and observed delivery are separate;
- configured audience is the route/runtime maximum audience snapshot;
- cohort audience is the exact intended subset for this binding;
- if recipients receive different canonical content/ranges, create separate
  delivery_cohort_id, reservation, sequence, binding, and SourceEvent;
- if only transport/client status differs, keep one SourceEvent and append
  recipient/cohort DeliveryObservationEvents;
- no cohort may broaden configured occurrence audience;
- recipient-level acknowledgement is optional and not required for evidence
  identity;
- private recipient lists remain Contract 1B metadata-projection controlled.

## Contract 1A binding

For an assistant-response SourceEvent:

- origin_kind = assistant;
- capture stream kind = managed_assistant_output or pass_through_opt_in;
- direction = outbound;
- source replay identity = managed_response_identity;
- assistant_response_binding_ref required;
- canonical manifest parts match binding canonical output parts;
- manifest digest excludes storage bindings;
- producer/represented speaker identify assistant service/persona;
- configured occurrence audience matches configured reservation snapshot;
- delivery cohort audience is a non-empty subset and is used by Contract 1B to
  derive effective assistant-response audience;
- late delivery observations never broaden audience or rewrite SourceEvent;
- request_source_refs do not convert assistant output to user origin;
- assistant_response_to lineage is created only for source_event request refs.

## Pass-through

Default:

- no RouteCaptureGrantSnapshot for assistant capture;
- no response reservation;
- no SourceEvent;
- no RelayREF/SLP managed behavior implied.

Opt-in requires:

- external pass_through_explicit_opt_in route snapshot;
- exact evidence space;
- allowed outbound stream/origin/channel;
- independent retention and audience policy;
- no inherited managed-route AccessGrant;
- separate response reservation and finalization identical in rigor to managed
  route.

## RelayREF handoff

Immediate response-complete path MAY provide:

- safe finalized output or protected response reference;
- response/run/turn identity;
- binding ID;
- completion extent and cause;
- bounded latest delivery observation refs when available;
- bounded generation metadata.

Rules:

- RelayREF runs after output exists;
- first token never waits;
- delayed/replayed content access uses Contract 1B authorization;
- RelayREF cannot alter binding, completion, audience, or SourceEvent;
- missing/busy/failed RelayREF yields observation_unavailable, not Evidence
  invalidation.

## Crash and race behavior

Crash before reservation:
    no canonical output may be accepted; runtime recovery/fallback only.

Crash after reservation, before output:
    terminal_no_output or mark_abandoned then recover.

Crash between first output acceptance and event persistence:
    trusted protected write-ahead buffer/canonical output record reconstructs
    emission_begin and output observation; otherwise mark corrupt/incomplete and
    never fabricate output.

Crash after partial output:
    recover exact observed ranges; completion_extent partial; cause from trusted
    runtime evidence or unknown.

Backend complete, transport partial:
    canonical binding may be response_complete when accepted by the canonical
    boundary; append delivery observations for transport/client uncertainty.
    Split a binding only when canonical content differs, not merely delivery
    status.

Cancellation and transport failure:
    represented on separate axes; no enum overwrite.

Duplicate finalize retry:
    same idempotency/body returns same binding; different body is integrity
    conflict.

Incorrect finalization discovered after SourceEvent:
    Contract 1B restricts/corrupts original; recovered binding and new SourceEvent
    created; Contract 1C recovered_runtime_response_rebind_of links them.

RelayREF arrives before SourceEvent admission:
    Contract 1C artifact targets the stable assistant_response_binding.
    A later SourceEvent references the same binding; no artifact subject mutation
    or rebinding occurs.

New user turn arrives:
    interactive path proceeds; pending assistant evidence finalization/recovery
    remains operational and must not block unrelated response unless resource
    policy says otherwise.

## Privacy and security

- exact governed representation means exact safe canonical boundary observation,
  not necessarily raw leaked secret bytes;
- secret/security omitted part keeps no personal-evidence content digest;
- security forensic domain MAY retain opaque incident reference under separate
  authority;
- delivery audience is protected metadata;
- client acknowledgement data is not exposed to normal Shared Assessment unless
  explicitly authorized;
- response content retention does not prove truth, commitment fulfillment,
  tool execution, or canonical memory write;
- product-knowledge-derived response remains assistant-origin occurrence; product
  corpus is not copied as personal evidence authority.

## Acceptance gates

- Reservation exists before/with first canonical output acceptance.
- No per-chunk SourceEvent or sequence.
- No-output path has no AdmissionDecision.
- Completion extent, termination cause, and delivery observation are separate.
- Human visibility is not overclaimed.
- Request correlation is frozen and tagged.
- Canonical content divergence splits delivery cohorts; delivery-status
  divergence uses append-only DeliveryObservationEvents.
- Late acknowledgement cannot alter response replay identity.
- Same response identity conflict is fail-closed.
- Recovery never regenerates output from prompt/model/RelayREF.
- Secret leakage can be omitted from personal evidence while preserving incident
  control reference.
- RelayREF remains post-response and advisory.
- Pass-through remains default-no-capture.
