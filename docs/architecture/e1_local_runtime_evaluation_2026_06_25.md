---
relaylm_doc_type: evaluation_record
relaylm_authority: observed_local_runtime_evidence
relaylm_status: current
relaylm_volatility: low
relaylm_owner: evaluation
relaylm_update_trigger:
  - the documented local E1 path changes
  - a finding is fixed or invalidated
  - a later workstation evaluation supersedes this evidence
relaylm_not_authoritative_for:
  - production reliability claims
  - exact implementation contracts
  - future UI or memory-formation design
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - soul_lab_ui_b0_real_home_conversation.md
  - post_i3_evaluation_work_roadmap.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - o0_local_one_job_runner.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - i1g_pre_enqueue_durable_finalization_contract.md
---
# E1 Local Runtime Evaluation — 2026-06-25

## Purpose

This record captures the first hands-on local workstation evaluation that connected the real SOUL Lab Home conversation surface, RelayLM, LM Studio, durable RelaySLP publication, O0 one-job execution, Primary MEM formation, and later-turn recall.

It records observed evidence and discovered gaps. It does not upgrade any component contract or claim production readiness.

## Environment

Observed topology:

```text
SOUL Lab Vite on WSL2 :5173
  -> RelayLM on WSL2 :8090
  -> LM Studio on Windows :1234
```

Evaluated route and scope:

```text
route mode:       memory_light
character_id:     default
memory_namespace: character/default
```

The RelaySLP enqueue and O0 worker gates were explicitly changed from their safe defaults to apply mode for the evaluation. The configured queue, protected-source, and memory roots were absolute local paths.

## Result summary

The local experiment proved the following bounded path:

```text
real SOUL Lab text conversation
  -> existing RelayLM route and character resolution
  -> LM Studio response

explicit scene-qualified managed request
  -> finalized-turn source capture
  -> durable protected source publication
  -> durable B2 queue record
  -> relaylm-worker --once
  -> canonical reread and B3 claim
  -> restart rehydration through C1-5
  -> C1-2 / M3a-M3h execution
  -> Primary MEM page publication
  -> index/log convergence
  -> terminal_succeeded

later SOUL Lab Home question
  -> M2 selection
  -> bounded RelayCTX snippet injection
  -> answer using the formed Primary MEM
```

The final O0 projection contained:

```text
selected=true
eligible=true
canonical_reread_performed=true
character_scope_resolved=true
claim_performed=true
source_prepared=true
restart_rehydrated=true
worker_invoked=true
worker_status=terminal_succeeded
terminal=true
reason_ids=[]
```

A `relationship_moment` Primary MEM page was created under the opaque character partition, and both `memory/mem/index.md` and `memory/mem/log.md` converged.

A later Home question asking for the user's favorite season correctly recalled `秋`.

## Findings

### 1. UI-B0 Home does not currently produce persistence-eligible scene evidence

The Home request contains only the standard Chat Completions fields owned by UI-B0:

```json
{
  "model": "<projected route>",
  "messages": [],
  "stream": true
}
```

It does not send `metadata.scene_state`.

For an ordinary memory statement such as `覚えておいてください。私の好きな季節は秋です。`, RelaySCN fell back to heuristic `casual_chat` with confidence and stability below the persistence thresholds. The request remained valid for conversation and later retrieval, but finalized-turn persistence failed closed and produced no queue record.

The evaluation therefore used an explicit operator request with a bounded high-confidence `casual_chat` scene state to exercise the existing formation path.

Current boundary:

```text
Home conversation and recall: verified
Home-origin Primary MEM formation: not verified and currently blocked by scene admission
explicit scene-qualified request -> formation: verified
```

This must not be fixed by allowing the browser to self-assert arbitrary trusted policy. A follow-up slice must define whether trusted scene admission is server-owned, route-owned, or supplied through a bounded authenticated projection.

### 2. Character-scoped memory store requires explicit bootstrap

O0 correctly resolved the configured memory root to:

```text
<configured root>/characters/<opaque character digest>/
```

The first worker invocation reached claim and rehydration but returned:

```text
worker_status=pipeline_blocked
reason_ids=[memory_store_root_missing, m3e_m3g_results_required]
```

The root cause was the absence of the resolved character store structure. After creating the four Primary directories and the exact control-file headers, the next job completed successfully.

Required initial structure:

```text
memory/mem/primary/projects/
memory/mem/primary/relationships/
memory/mem/primary/sessions/
memory/mem/primary/scenes/
memory/mem/index.md    first line: # Index
memory/mem/log.md      first line: # Log
```

The current runtime intentionally does not auto-create this authority. Local evaluation and future packaged startup therefore need an explicit, idempotent bootstrap procedure or command.

A claimed job that returns `pipeline_blocked` before a queue outcome transition remains claimed and is not selected again by O0. The successful retry used a newly published job after store bootstrap; the prior record was not edited manually.

### 3. Assistant-authored text is admitted into trusted Primary MEM evidence

The formed page stored one summary containing both the user turn and the complete assistant response:

```text
User turn: 覚えておいてください。私の好きな季節は秋です。
Assistant response: ...涼しい風と紅葉のイメージ...
```

The user asserted only that the favorite season is autumn. The assistant supplied the decorative details. Because the combined summary was stored with `summary_origin: trusted_in_process_summary` and `content_role: evidence`, later retrieval could not distinguish user evidence from assistant-authored elaboration.

This is a provenance defect, not merely a response-style issue.

Target correction:

```text
user assertion evidence
  -> retained as factual memory candidate
assistant acknowledgement
  -> retained separately or excluded from factual evidence
assistant speculation / decoration
  -> never promoted as user fact
```

A future formation contract should preserve speaker-level provenance and should not label a simple concatenation of user and assistant text as one undifferentiated trusted summary.

### 4. Later response added details not present in the stored page

The recall answer correctly returned `秋`, but also added details such as a smell of fallen leaves, late-night work, and warm tea. Some autumn imagery was traceable to the assistant-authored content already stored; other details were absent from the page entirely.

Evaluation result:

```text
memory selection: successful
core user fact recall: successful
speaker provenance: insufficient
response grounding to retrieved evidence: insufficient
```

Retrieval-side instructions should require the backend to distinguish retrieved facts from inference and avoid presenting unsupported details as remembered history. This does not replace the formation-side provenance fix.

## Proof boundary

Verified manually:

- real SOUL Lab to RelayLM to LM Studio text conversation,
- explicit finalized-turn protected-source and queue publication through the existing background finalizer,
- O0 one-job discovery, canonical reread, claim, restart rehydration, and execution,
- M3a-M3h Primary MEM page/index/log convergence,
- terminal success and protected-source cleanup path,
- next-turn scoped Primary MEM retrieval and answer influence through Home.

Not verified by this experiment:

- direct Home-origin formation without separate scene admission,
- automatic queue polling, retry scheduling, or supervision,
- I1-GB pre-release durable-finalization publication under its later merged apply gates,
- I1-GC restart replay of sealed durable-finalization evidence and completion convergence,
- broad memory quality, contradiction handling, or long-running operation,
- provenance-safe formation,
- evidence-grounded response generation,
- production Forget, Pin, Merge, Held review, Secondary MEM, or RelaySOUL behavior.

## Required follow-up work

The evaluation produces four concrete follow-up items:

```text
E1-R1  trusted scene-admission path for ordinary Home conversations
E1-R2  explicit idempotent character-store bootstrap procedure or command
E1-R3  provenance-preserving Primary MEM formation summary
E1-R4  retrieval-response grounding and unsupported-detail suppression
```

These are independent from O1/O2/O3 operational automation. O1 would process more jobs but would not make a blocked Home request persistence-eligible, create a missing character store safely, or repair contaminated evidence.

## Evaluation verdict

The first local E1 infrastructure experiment is complete.

RelayLM can form a durable Primary MEM through the real production authorities and recall it in a later SOUL Lab Home conversation. The direct product loop is not yet seamless: Home-origin formation requires a trusted scene-admission fix, local store bootstrap is still operator-owned, and memory provenance/grounding quality requires correction before meaningful long-horizon evaluation.
