# RelaySCN MVP Scene Policy

Date basis: JST 2026-05-31

## Purpose

RelaySCN is the RelayLM scene-state runtime/controller.

It estimates `scene_state` for the current turn and resolves it into `scene_policy` for downstream layers:

- RelayCTX
- RelayEMO
- RelayMEM
- RelaySOUL
- RelaySLP

RelaySCN is not an EMO submodule. It is a cross-cutting runtime controller that determines how the current conversational frame should constrain context packing, expression, retrieval, persistence, and recovery behavior.

## Canonical Runtime Order

```text
User input
↓
Input-side RelaySCN
↓
Input-side RelayEMO
↓
RelayCTX Repack
↓
Main LLM
↓
RelayCTX Unpack
↓
Return-side RelayEMO
↓
Output-side RelaySCN
↓
User output
```

### Input-side RelaySCN

Input-side RelaySCN controls the current turn.

It should:

- estimate `scene_state`
- resolve `scene_state` into `scene_policy`
- provide policy gates for RelayCTX / RelayEMO / RelayMEM / RelaySOUL / RelaySLP

### Output-side RelaySCN

Output-side RelaySCN observes scene transition candidates after:

1. RelayCTX Unpack
2. Return-side RelayEMO

Output-side RelaySCN is normally `next_turn` only.

It should not become a general output rewriter. Immediate transition is allowed only for:

- safety-sensitive scene escalation
- recovery/context-repair escalation
- high risk of wrong continuation

## RelaySCN MVP Definition

```text
RelaySCN = scene_state → scene_policy runtime controller
```

MVP priorities:

1. Define minimal `scene_state` schema.
2. Define `scene_state → scene_policy` conversion table.
3. Define `recovery` scene rules.
4. Define `persistence_block` rules.
5. Emit diagnostics/artifacts before any persistent mutation behavior.

---

## 1. Minimal scene_state Schema

```yaml
scene_state:
  schema_version: "relayscn.scene_state.v0"

  scene_type: design_talk
  confidence: 0.82
  stability: 0.74

  previous_scene_type: casual_chat
  transition_reason: user_started_architecture_discussion

  task_state: architecture_discussion
  safety_sensitivity: low
  formality: low

  memory_scope: project_context
  expression_allowance: light

  recovery_mode: false
  user_confirmation_required: false
```

### Required Fields

| Field | Purpose |
|---|---|
| `schema_version` | Schema identifier for diagnostics and compatibility |
| `scene_type` | Current scene estimate |
| `confidence` | Confidence of the current estimate |
| `stability` | Stability of the scene across turns |
| `previous_scene_type` | Previous turn scene |
| `transition_reason` | Reason for the latest transition or candidate transition |
| `task_state` | Task status inside the scene |
| `safety_sensitivity` | Safety / medical / legal / operational sensitivity |
| `formality` | Required level of formal style |
| `memory_scope` | Allowed retrieval scope |
| `expression_allowance` | Allowed RelayEMO expression strength |
| `recovery_mode` | Whether the runtime is in context repair |
| `user_confirmation_required` | Whether user confirmation is required before continuing |

---

## 2. MVP scene_type Candidates

```text
casual_chat
design_talk
implementation_work
review_work
formal_document
medical_or_safety
system_ops
vtuber_roleplay
recovery
```

| scene_type | Meaning |
|---|---|
| `casual_chat` | Casual conversation or light discussion |
| `design_talk` | Architecture, specification, or conceptual design |
| `implementation_work` | Implementation, Codex instructions, code changes |
| `review_work` | PR review, diff review, review response handling |
| `formal_document` | Formal writing, reports, public/professional documents |
| `medical_or_safety` | Medical, safety, legal, or other high-caution contexts |
| `system_ops` | Environment setup, GitHub operations, configuration, local ops |
| `vtuber_roleplay` | Character expression, TTS, Live2D, avatar-facing behavior |
| `recovery` | Context repair after confusion or unresolved SLP |

---

## 3. scene_policy Schema

Downstream layers should primarily consume `scene_policy`, not raw `scene_state`.

```yaml
scene_policy:
  schema_version: "relayscn.scene_policy.v0"

  relayctx_mode: design_compact

  relayemo_marker_policy: light
  relayemo_expression_policy: light

  relaymem_retrieval_scope: project_context
  relaymem_update_gate: allowed_dry_run

  relaysoul_update_gate: blocked

  slp_mode: optional
  persistence_block: false

  user_confirmation_required: false
  output_rewrite_allowed: false
  diagnostics_required: true
```

### Policy Fields

| Field | Purpose |
|---|---|
| `relayctx_mode` | How RelayCTX should repack/unpack context |
| `relayemo_marker_policy` | Text marker allowance |
| `relayemo_expression_policy` | TTS / Live2D / expressive output allowance |
| `relaymem_retrieval_scope` | Retrieval scope for RelayMEM |
| `relaymem_update_gate` | Whether MEM update candidates may be emitted |
| `relaysoul_update_gate` | Whether SOUL proposal/update is allowed |
| `slp_mode` | Whether SLP is optional, recommended, forced, or recently attempted |
| `persistence_block` | Hard block for persistent memory/persona mutation |
| `user_confirmation_required` | Whether the user must confirm before continuing |
| `output_rewrite_allowed` | Whether output-side rewriting is allowed |
| `diagnostics_required` | Whether diagnostics/artifact output is required |

---

## 4. scene_state → scene_policy Conversion Table

| scene_type | RelayCTX | RelayEMO | RelayMEM Retrieval | MEM update | SOUL update | SLP | Notes |
|---|---|---|---|---|---|---|---|
| `casual_chat` | `light_context` | `allowed` | `relationship_or_recent` | `dry_run_only` | `blocked` | `optional` | Casual conversation. Light retrieval is allowed. |
| `design_talk` | `design_compact` | `light` | `project_context` | `allowed_dry_run` | `proposal_only` | `optional` | Main design/specification scene. |
| `implementation_work` | `repo_task_compact` | `suppressed_or_light` | `project_context` | `allowed_dry_run` | `blocked` | `optional` | Codex/code-change-oriented work. |
| `review_work` | `review_strict` | `suppressed` | `current_project_only` | `allowed_dry_run` | `blocked` | `recommended` | PR review and validation-focused work. |
| `formal_document` | `formal_output` | `suppressed` | `evidence_only` | `blocked` | `blocked` | `optional` | Formal writing and public/professional documents. |
| `medical_or_safety` | `safety_cautious` | `suppressed` | `minimal_or_evidence_only` | `blocked` | `blocked` | `recommended` | Safety-first. Ask for clarification when ambiguous. |
| `system_ops` | `ops_precise` | `suppressed_or_light` | `project_or_ops_context` | `dry_run_only` | `blocked` | `optional` | Environment setup, GitHub, local ops. |
| `vtuber_roleplay` | `character_context` | `allowed` | `character_or_relationship` | `dry_run_only` | `proposal_only` | `optional` | Expression allowed, but safety scene overrides. |
| `recovery` | `context_repair` | `suppressed` | `current_context_only` | `blocked` | `blocked` | `forced_or_recently_attempted` | Confusion recovery. Confirmation required. |

---

## 5. Persistence Block Rules

MVP should treat persistence as any long-term or semi-long-term mutation path, including:

- RelayMEM update candidate
- RelayMEM compiled page update
- RelaySOUL proposal
- RelaySOUL approved mutation
- long-term relationship tint
- RelayEMO long-term policy feedback

### Core Principles

```text
Retrieval only reads.
SLP may produce candidates.
MEM update candidates must pass Scene gate.
SOUL update requires explicit approval.
Recovery / safety / formal scenes block persistence.
```

### Fail-Closed Block Reasons

If any of the following are true, MVP should set `persistence_block: true`.

```yaml
persistence_block_reasons:
  - scene_type_is_recovery
  - scene_type_is_medical_or_safety
  - scene_type_is_formal_document
  - user_confirmation_required
  - confidence_below_threshold
  - stability_below_threshold
  - slp_confusion_unresolved
  - contradiction_detected
  - unresolved_reference_detected
  - output_generated_from_recovery_context
```

### Thresholds

```yaml
persistence_thresholds:
  min_scene_confidence_for_mem_update: 0.70
  min_scene_stability_for_mem_update: 0.65
  min_scene_confidence_for_soul_proposal: 0.85
  min_scene_stability_for_soul_proposal: 0.80
```

MVP should not perform direct SOUL mutation. At most, it may emit explicit approval proposals.

---

## 6. Recovery Scene Rules

`recovery` is a context-repair scene, not a normal conversational mode.

### Recovery Triggers

```yaml
recovery_triggers:
  - slp_attempted_and_confusion_unresolved
  - unresolved_reference_detected
  - contradiction_detected
  - task_state_lost
  - previous_scene_unknown_or_unstable
  - user_correction_repeated
  - assistant_output_risk_of_wrong_continuation
  - safety_sensitive_ambiguity
```

Key rule:

```text
If SLP is attempted and confusion remains unresolved,
RelaySCN may switch to recovery/context_repair.
```

### Recovery scene_policy

```yaml
scene_policy:
  relayctx_mode: context_repair

  relayemo_marker_policy: suppress
  relayemo_expression_policy: suppress

  relaymem_retrieval_scope: current_context_only
  relaymem_update_gate: blocked

  relaysoul_update_gate: blocked

  slp_mode: forced_or_recently_attempted
  persistence_block: true

  user_confirmation_required: true
  output_rewrite_allowed: false
  diagnostics_required: true
```

### Recovery Response Rules

In `recovery`, RelayLM should not continue the task automatically.

It should:

1. Briefly state that context may be mixed.
2. Present the current understanding.
3. Narrow the unknown point to one question or choice.
4. Ask the user to confirm, choose, or re-enter.
5. Block MEM/SOUL updates.
6. Suppress RelayEMO expression.

Example:

```text
ここで前提が少し混ざっている可能性があります。
今の理解では、話題は RelaySCN のMVP設計で、特に recovery scene と persistence block の規則を整理しています。

次は「実装用のschema」に落としますか？
それとも「docs用の設計文書」としてまとめますか？
```

---

## 7. Output-side SCN Transition Rules

Output-side RelaySCN should observe the final user-facing candidate after:

- RelayCTX Unpack
- Return-side RelayEMO

It should emit a transition observation:

```yaml
output_scene_observation:
  scene_changed: false
  next_scene_candidate: implementation_work
  confidence: 0.58
  apply_timing: next_turn
  transition_reason: assistant_suggested_next_task
```

Default behavior:

```text
Output-side SCN is next_turn only.
```

Immediate transition is allowed only for:

```text
medical_or_safety
recovery
high wrong-continuation risk
```

Output-side SCN should not become a general output rewriter.

---

## 8. Artifact MVP

```yaml
relayscn_artifact:
  schema_version: "relayscn.artifact.v0"

  input_scene_state:
    scene_type: design_talk
    confidence: 0.82
    stability: 0.74
    previous_scene_type: casual_chat
    transition_reason: user_started_architecture_discussion
    task_state: architecture_discussion
    safety_sensitivity: low
    formality: low
    memory_scope: project_context
    expression_allowance: light
    recovery_mode: false
    user_confirmation_required: false

  scene_policy:
    relayctx_mode: design_compact
    relayemo_marker_policy: light
    relayemo_expression_policy: light
    relaymem_retrieval_scope: project_context
    relaymem_update_gate: allowed_dry_run
    relaysoul_update_gate: proposal_only
    slp_mode: optional
    persistence_block: false
    user_confirmation_required: false
    output_rewrite_allowed: false
    diagnostics_required: true

  output_scene_observation:
    scene_changed: false
    next_scene_candidate: implementation_work
    confidence: 0.58
    apply_timing: next_turn
    transition_reason: assistant_suggested_next_task

  persistence_decision:
    mem_update_allowed: true
    soul_update_allowed: false
    blocked_reasons: []
```

---

## 9. MVP Implementation Order

Suggested order:

```text
1. Add RelaySCN schema/policy docs.
2. Add scene classifier dry-run.
3. Add scene_policy resolver dry-run.
4. Wire scene_policy into RelayCTX Repack diagnostics.
5. Ensure RelayCTX Unpack is documented as mandatory after Main LLM.
6. Wire RelayEMO marker/expression gate to scene_policy.
7. Wire RelayMEM/SOUL persistence gate to scene_policy.
8. Add output-side transition observer.
9. Add recovery scene diagnostics.
```

---

## Summary

MVP fixed points:

```text
RelaySCN = scene_state → scene_policy runtime controller.
Recovery / medical_or_safety / formal_document trigger persistence_block.
If SLP cannot resolve confusion, switch to recovery/context_repair.
Output-side SCN is normally next_turn only.
RelayCTX Unpack is mandatory after Main LLM and before Return-side RelayEMO.
```
---

## 8. MVP Runtime Dry-run Artifact

RelayLM runtime diagnostics should emit a diagnostics-only RelaySCN artifact on every valid chat request. The artifact must not alter forwarded backend payloads and must not enforce policy at runtime until a later apply gate is introduced.

```yaml
relayscn_scene_policy_artifact:
  schema_version: relayscn.scene_policy_artifact.v0
  diagnostics_only: true
  scene_state_source: request_metadata | relayemo_artifact | heuristic
  scene_state:
    schema_version: relayscn.scene_state.v0
    scene_type: design_talk
    confidence: 0.74
    stability: 0.70
    signals:
      - keyword:design_talk
    is_estimate: true
  scene_policy:
    schema_version: relayscn.scene_policy.v0
    relayctx_mode: design_compact
    relayemo_marker_policy: light
    relayemo_expression_policy: light
    relaymem_retrieval_scope: project_context
    relaymem_update_gate: allowed_dry_run
    relaysoul_update_gate: proposal_only
    slp_mode: optional
    user_confirmation_required: false
    output_rewrite_allowed: false
    persistence_block: false
    persistence_block_reasons: []
    diagnostics_required: true
  persistence_block: false
  persistence_block_reasons: []
  diagnostics_required: true
```

MVP priority order is:

1. explicit request metadata (`metadata.scene_state` or `metadata.relayscn.scene_state`)
2. RelayEMO scene artifact, when enabled
3. lightweight input heuristic
4. fail-closed unknown scene

Unknown or missing scene metadata must remain safe: scene confidence/stability are low, diagnostics are required, and persistence is blocked or diagnostics-only. Recovery, formal document, medical/safety, user-confirmation, low confidence, and low stability cases must emit `persistence_block: true` with reasons.
