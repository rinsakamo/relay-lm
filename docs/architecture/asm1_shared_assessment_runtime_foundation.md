---
relaylm_doc_type: implementation_handoff
relaylm_authority: asm1_shared_assessment_runtime_foundation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Shared Assessment runtime record shape or validation changes
  - EV-1 shared-assessment access authorization changes
  - Assessment Pass boundary or formation-time receipt changes
  - ASM-1 feature posture or local persistence boundary changes
relaylm_not_authoritative_for:
  - Subjective MEM decision, revision, relation, lifecycle, or retrieval authority
  - permanent Shared Assessment physical storage authority
  - RelaySLP queue, worker, scheduler, or model-selection policy
  - SOUL-conditioned Subjective Formation
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - project_execution_plan.md
  - memory/formation.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/governed-evidence-contract-family.md
  - ../contracts/evidence-governance-access.md
---
# ASM-1 Shared Assessment Runtime Foundation

Last reviewed: 2026-07-22 JST

## Purpose

ASM-1 implements the first bounded runtime path from EV-1 governed Evidence to character-independent Shared Assessment. It provides:

- exact EV-1 `shared_assessment_read` authorization resolution;
- a transient, content-bearing split Assessment Pass input bundle;
- immutable consecutive `SharedAssessmentRevision` records;
- one logical `SharedAssessmentCurrentState` selector;
- a decision-bound formation authorization receipt builder for the exact current admitted revision;
- explicit default-off / dry-run / apply configuration gates.

ASM-1 ends before Subjective MEM. It does not create a `SubjectiveMemDecision`, `SubjectiveMemRevision`, `SubjectiveMemCurrentState`, `SubjectiveMemRelation`, or `SubjectiveMemLifecycleTransition`.

## Runtime boundary

```text
EV-1 admitted SourceEvents
  -> exact current shared_assessment_read authorization
  -> protected text integrity and provenance validation
  -> transient character-independent Assessment Pass bundle
  -> external / later Assessment Pass generation
  -> deterministic proposal validation
  -> immutable SharedAssessmentRevision
  + one logical current-state selector
  -> decision-transaction-bound exact formation authorization receipt builder

STOP: no SOUL conditioning and no Subjective MEM write
```

The ordinary response route does not invoke this path. The functions are explicit deferred-worker/library entry points and do not start a queue, worker, polling loop, scheduler, or background service.

## Split Assessment Pass

`prepare_shared_assessment_pass(...)` consumes one to 64 exact SourceEvent IDs from one EV-1 evidence space. For each source it verifies:

- the canonical SourceEvent and manifest digest;
- an admitted `AdmissionDecision` bound through the capture-attempt log;
- the exact valid validation-bundle revision;
- the initial governance event and resulting governance-state digest;
- the current least-privilege `shared_assessment_read` grant;
- retention deadline, record availability, integrity, selected part availability, locality, audience, and destination constraints through the EV-1 access resolver;
- payload-binding attestation, protected payload digest, and text media type;
- source provenance and the product-knowledge exclusion boundary.

The resulting `SharedAssessmentPassBundle` contains exact evidence references, authorized protected text parts, and stable authority-snapshot digests. It contains no character, SOUL, REL, SCN, EMO, STYLE, or subjective-meaning fields. The bundle is transient and is not persisted by ASM-1.

Official RelayLM product knowledge marked `product_knowledge_derived` fails closed and cannot enter personal Shared Assessment formation.

## Revision and current-state publication

`commit_shared_assessment_revision(...)` re-resolves EV-1 authorization under the evidence-space lock immediately before publication. A stale or altered pass bundle fails closed.

Publication is one EV-1 store transaction containing:

- one immutable target-schema `relaylm.shared_assessment_revision.v1` record;
- one immutable operation-idempotency record;
- replacement of the singleton `relaylm.shared_assessment_current_state.v1` selector;
- append of a bounded consecutive revision index used to prove that the selector names the latest persisted revision.

The caller derives `assessment_id` with `derive_shared_assessment_id(evidence_space_id, logical_key)`, preventing the same logical ID from being independently current in another session Evidence space. The caller supplies `expected_current_revision_or_null`. Revision 1 requires `null`; every successor requires the exact current revision. Stale model output therefore cannot silently become a later revision. Successors increment exactly once and name the immediate predecessor.

Operation retries use a stable semantic input digest rather than the transient pass ID or short-lived authorization-projection ID. Re-preparing the same exact authorized evidence and retrying the same operation is duplicate-safe. Reusing an operation key with different evidence or proposal content is an integrity conflict.

## Formation-time authorization receipt

`build_shared_assessment_formation_receipt(...)` builds a self-authenticating receipt only inside a caller-owned Evidence transaction when:

- the requested revision is the one logical current revision;
- lifecycle is `active`;
- authorization is `current_admitted`;
- the revision and revision index are internally consistent;
- every referenced SourceEvent still resolves current EV-1 Shared Assessment read authority;
- the stored supported-content digest matches the exact UTF-8 content.

The receipt preserves the contract fields:

```json
{
  "current_revision_at_decision": 1,
  "lifecycle_state_at_decision": "active",
  "authorization_state_at_decision": "current_admitted"
}
```

It also records content-free Evidence authority snapshot digests and the supported-content digest. It does not duplicate protected source text or supported content. ASM-1 does not persist this receipt independently. SM-1 must bind it to an exact `decision_id` and decision-input digest, then commit the receipt and `SubjectiveMemDecision` in the same transaction. A prepared-but-uncommitted receipt has no authority.

## Feature posture

Configuration remains fully off by default:

```yaml
shared_assessment_enabled: false
shared_assessment_dry_run_only: true
shared_assessment_apply_enabled: false
```

When enabled, ASM-1 requires an absolute `evidence_data_root` and reuses the EV-1 device-local evidence store. This is a bounded implementation choice for ASM-1, not a permanent Shared Assessment physical-storage authority decision.

Dry-run validates and returns the proposed revision/current selector without writing Shared Assessment files. Apply must be explicitly enabled. No configuration posture enables Subjective MEM.

## Fail-closed boundaries

ASM-1 rejects or blocks:

- missing, cross-space, rejected, expired, restricted, or integrity-invalid Evidence;
- invalid or missing grants, validation bundles, governance state, payload binding, or protected payload;
- unsupported origin or product-knowledge-derived source material;
- duplicate Evidence references or more than 64 SourceEvents;
- invalid support, temporal, uncertainty, content, or governance fields;
- stale expected-current revisions;
- duplicate, corrupt, dangling, or nonconsecutive current-state/revision indexes;
- idempotency-key reuse with different semantic input;
- formation receipts for a prior, missing, restricted, or non-current revision.

False merge and subjective relation decisions remain outside ASM-1 rather than being approximated here.

## Implementation files

```text
relaylm/shared_assessment.py
relaylm/shared_assessment_evidence.py
relaylm/shared_assessment_runtime.py
scripts/relaylm_asm1_shared_assessment_smoke.py
tests/test_shared_assessment_runtime.py
```

Configuration fields are in `relaylm/config.py` and `config.example.yaml`.

## Validation

Focused validation:

```bash
PYTHONPATH=tests:. pytest -q tests/test_shared_assessment_runtime.py
python scripts/relaylm_asm1_shared_assessment_smoke.py
```

The tests cover target JSON Schema validation, user and assistant Evidence, character/SOUL contamination absence, current authorization and expiry, exact first/successor revisions, stale-output fencing, singleton current-state authority, revision-index integrity, dry-run no-write behavior, operation retry equivalence, conflict detection, exact formation-time receipts, prior-revision rejection, product-knowledge exclusion, default-off configuration, and the explicit absence of Subjective MEM records.

## Explicit non-goals

ASM-1 does not implement:

- Shared Assessment model prompts, multilingual generation policy, or model selection;
- RelaySLP job admission, queueing, worker execution, scheduling, or resource policy;
- Subjective MEM create/reinforce/refine/reinterpret/supersede/contradict/relate decisions;
- SOUL-, REL-, SCN-, or EMO-conditioned meaning;
- Markdown canonical memory publication or SQLite projection;
- Subjective MEM lifecycle, Retrieval projection, migration, or hard cutover;
- multi-user/shared-scene Evidence authority, export, replication, or purge;
- default-on deployment.

Those remain owned by SM-1, ST-1, LC-1, RT-1, later Evidence/OVL slices, or separate accepted decision gates.
