---
relaylm_doc_type: implementation_handoff
relaylm_authority: sm1_subjective_mem_create_runtime
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - SM-1 create input, decision, prepared result, or idempotency shape changes
  - ASM-1 formation-receipt or Evidence transaction behavior changes
  - ST-1 begins consuming or finalizing the prepared result
  - PM-D1 or PM-D9 changes the proposal-production authority boundary
relaylm_not_authoritative_for:
  - canonical Subjective MEM Markdown publication or final commit receipts
  - ordinary Subjective MEM Retrieval or projection authority
  - lifecycle, relation, merge, reinforcement, consolidation, or migration behavior
  - SOUL-conditioned proposal generation or multilingual Assessment policy
relaylm_related_authority:
  - project_execution_plan.md
  - asm1_shared_assessment_runtime_foundation.md
  - memory/formation.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0005-subjective-mem-storage-authority.md
---
# SM-1 Subjective MEM Create Runtime

Last reviewed: 2026-07-23 JST

## Purpose

SM-1 implements one bounded logical `create` path from an exact current-admitted ASM-1 Shared Assessment revision to one immutable decision and one revision-1 prepared Subjective MEM result.

The supported boundary is exactly:

```yaml
outcome: create
scope_kind: character_private
audience_class: private
participant_id_or_null: null
relationship_id_or_null: null
scene_id_or_null: null
identity_status: known
formation_stage: primary
memory_kind: episodic | semantic
candidate_memory_refs: []
similarity_granted_authority: false
mutation_state: prepared
retrieval_eligible: false
```

SM-1 is a library/runtime slice. It is not called by the ordinary response path, does not start a queue or worker, and does not publish canonical Subjective MEM.

## Producer and input boundary

`create_subjective_mem(...)` consumes explicit caller-owned inputs:

- one EV-1 Evidence space;
- one exact persisted `SharedAssessmentRevision` and its exact logical `SharedAssessmentCurrentState`;
- one configured character identity resolved by opaque character key through `resolve_subjective_mem_character_authority(...)`;
- an exact character-private scope;
- opaque SOUL, MEMORY policy, BOUNDARY, formation-schema, and proposal-model revision references;
- bounded caller-provided subjective meaning;
- explicit memory kind and multidimensional strength;
- one stable idempotency key;
- one exact decision time and a validation-time observation used to reject future decisions.

The character authority revision is derived only from the workspace reference, opaque character key, and versioned resolver schema. The resolver checks current registry membership but deliberately excludes SOUL/output-policy paths and all content-bearing character configuration from identity. `create_subjective_mem(...)` re-resolves that authority from the supplied current RelayLM configuration and requires it to equal the caller's exact authority object before any transaction work. Display names, titles, headings, prose, and filesystem paths do not create logical identity. The Evidence-space descriptor must name the same workspace and an active private-conversation boundary.

The proposal includes a fixed `SubjectiveMemProposalBoundary` attestation. It declares that the upstream producer preserved grounded content and uncertainty, did not invent participant identity, did not alter scope or temporal grounding, and excluded official product knowledge. SM-1 validates the exact attestation and the structural separation, but does not claim that this replaces semantic model evaluation or PM-D1/PM-D9 authority.

No LLM, translator, embedding model, classifier service, RelaySOUL call, or external provider is invoked by SM-1.

## Formation-time authority

Inside the same caller-owned `EvidenceRecordStore` transaction used for the SM-1 commit, the runtime:

1. verifies the exact active Evidence-space descriptor and workspace binding;
2. compares the caller's assessment revision and selector byte-semantically with the stored records;
3. calls ASM-1 `build_shared_assessment_formation_receipt(...)`;
4. therefore revalidates the singleton current selector, consecutive revision index, stored revision integrity, all referenced EV-1 authorization, and the supported-content digest;
5. binds the receipt to the exact deterministic `decision_id` and complete decision-input digest;
6. commits the receipt and decision together with the exact prepared result set.

A receipt returned during dry-run is non-persisted and has no independent authority. There is no API that commits a formation receipt by itself.

## Grounded and subjective separation

The revision is built deterministically so that:

```text
grounded_content
  == SharedAssessmentRevision.supported_content

grounded_content_digest
  == SharedAssessmentRevision.supported_content_digest

grounded_assessment_ref
  == exact assessment_id + revision + digest
```

Subjective meaning occupies a separate bounded field. It cannot replace the grounded field, Evidence references, assessment reference, scope, character, or authorization linkage. Grounded confidence is range-checked and capped conservatively by the Shared Assessment support state. Revision 1 always has no predecessor, no relation, no target memory, and reinforcement count zero.

## Atomic transaction and bidirectional linkage

One successful apply is one Evidence-space transaction containing:

```text
immutable SharedAssessment formation receipt
immutable SubjectiveMemDecision
immutable prepared SubjectiveMemRevision post-image
immutable content-free prepared manifest
immutable content-free operation/idempotency result
singleton prepared SubjectiveMemCurrentState replacement
```

The transaction journal is the crash-recovery boundary reused from EV-1/ASM-1. The operation record contains identifiers, revisions, digests, fixed states, and authority digests only. It does not contain grounded content, subjective meaning, prompts, or raw idempotency keys.

The runtime validates both directions:

```text
receipt.decision_id == decision.decision_id
decision.result_memory_ref == revision-1
revision.authorization_ref == decision.decision_id
current_state.current_revision == revision-1
prepared_manifest.revision_digest == digest(revision-1)
```

Character, scope, assessment references, supported-content digest, and all formation timestamps must also agree exactly. Under the Evidence-space lock, apply and retry use a bounded inventory to require exactly one logical current-state selector for the same character and memory even when a conflicting selector uses another state key. Corrupt, missing, duplicate, stale, or repointed records fail closed on retry.

## Identity and idempotency

The raw-key digest and exact Evidence-space plus character-authority namespace select a deterministic idempotency slot. The logical operation ID is derived from the same namespace and key digest. The slot binds that scoped operation to:

- the Evidence space;
- the exact character/workspace authority digest;
- the exact assessment revision and selector;
- the exact proposal, policy references, kind, strength, and boundary attestation;
- the exact decision time;
- the deterministic decision, memory, manifest, and current-state identities.

The raw key is never persisted or emitted publicly. Within one exact Evidence-space and character-authority namespace, the same key and equivalent immutable input returns the same decision, memory ID, revision, manifest, and current state, while changed immutable input is an integrity conflict. The same raw key may independently identify another operation in a different character/workspace namespace. A persisted operation that is repointed across namespaces or claims mismatched scope authority fails closed. Retry cannot create revision 2 or another selector.

`memory_id` is opaque and deterministic from the exact Evidence-space plus character-authority namespace and decision identity. It is not derived from a display name, title, path, heading, or subjective prose.

## Prepared result and ST-1 handoff

SM-1 intentionally stops before the storage contract's final publication pair.

The exact target-schema revision is stored as an immutable content-bearing **prepared post-image**, and a separate content-free manifest records its digest and immutable record reference. The current state is:

```yaml
current_revision: 1
lifecycle_state: active
mutation_state: prepared
retrieval_eligible: false
```

The revision itself also has `retrieval_visible: false`. The manifest states:

```yaml
publication_state: prepared_noncanonical
canonical_markdown_published: false
commit_receipt_present: false
st1_finalization_required: true
```

This prepared JSON post-image is not canonical Markdown and is not a second editable semantic authority. It is immutable transaction material that lets ST-1 consume the exact formation result without re-running an LLM or subjective formation.

ST-1 must:

1. verify the operation, receipt, decision, revision, manifest, and current-state crosslinks and digests;
2. render and durably install the supported canonical Markdown post-image under its accepted platform contract;
3. verify the installed canonical digest and lineage;
4. finalize the matching durable operations receipt and idempotency result;
5. replace or retire the SM-1 prepared linkage under an explicit atomic finalization/recovery protocol;
6. keep ordinary Retrieval fail closed until the canonical page and final receipt agree.

SM-1 creates no `.md` memory page, final commit receipt, projection row, normal Retrieval reader, or `mutation_state: none` record.

## Feature posture

Configuration is fully off by default:

```yaml
subjective_mem_create_enabled: false
subjective_mem_create_dry_run_only: true
subjective_mem_create_apply_enabled: false
```

A non-disabled posture requires ASM-1 and an absolute safe `evidence_data_root`. Apply requires ASM-1 apply and a usable non-symlinked store. Dry-run builds and validates the exact proposed receipt/decision/result bundle but writes no SM-1 records.

These flags do not authorize canonical publication, normal Retrieval, queueing, scheduling, or background execution.

## PM-D1 and PM-D9 boundaries

The formation snapshot requires an opaque `soul_revision`, but SM-1 does not call RelaySOUL and does not treat that reference as proof of production-authoritative SOUL-conditioned formation. The subjective proposal remains caller-provided. RelaySOUL intervention, veto, rollback, and production-authoritative SOUL conditioning remain PM-D1 work.

SM-1 does not generate Shared Assessments or proposals in any language. Model prompting, analyzer selection, multilingual schema policy, and production defaults remain PM-D9 work. Recording an opaque proposal-model revision does not close PM-D9.

## Public diagnostics and privacy

`SubjectiveMemCreateResult.to_log_dict()` contains only fixed status/reason IDs, opaque decision/memory/assessment IDs, revision number, scope kind, memory kind, and prepared/persisted booleans. It does not expose grounded content, subjective meaning, Evidence, Shared Assessment text, prompts, SOUL/REL/SCN bodies, filesystem paths, exception strings, or raw operation keys.

Unknown exceptions collapse to a fixed safe store-unavailable reason.

## Implementation files

```text
relaylm/subjective_mem.py
relaylm/subjective_mem_runtime.py
relaylm/shared_assessment_runtime.py
scripts/relaylm_sm1_subjective_mem_create_smoke.py
tests/test_subjective_mem_runtime.py
```

Configuration fields are in `relaylm/config.py` and `config.example.yaml`.

## Explicit non-goals

SM-1 does not implement:

- reinforce, refine, reinterpret, supersede, contradict, relate, hold, abstain, or leave-as-evidence apply;
- candidate discovery, lexical search, embeddings, merge, automatic reinforcement, or relation creation;
- participant, relationship, scene, unknown-identity, shared-scene, or multi-user durable scope;
- RelaySOUL intervention, RelaySLP scheduling, a worker, polling, or a response-path hook;
- canonical Markdown, a final operations receipt, storage cutover, projection, or ordinary Retrieval;
- lifecycle transition, Correct, Forget, Restore, Pin/Unpin, Consolidate, or Purge;
- current Primary MEM mutation, migration, replacement, or retirement.

ST-1 is the next consumer slice. LC-1 and RT-1 remain later dependent work.
