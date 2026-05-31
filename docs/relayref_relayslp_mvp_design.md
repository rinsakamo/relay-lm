# RelayREF / RelaySLP MVP Design

Date basis: 2026-05-31 JST

## Purpose

This document defines the MVP design for RelayREF and RelaySLP.

RelayREF is the Wake-time reflection, resynchronization, and recovery layer.

RelaySLP is the Sleep/reset/deep-consolidation sub-layer.

Core split:

> RelayREF handles thinking, reflection, resynchronization, and handoff repair.  
> RelaySLP handles true sleep, forced reset, and offline/deep consolidation.

## Naming

### RelayREF

RelayREF means Relay Reflection.

It covers:

- Wake-time reflection
- lightweight context repair
- ambiguity recovery
- handoff repair
- resume confirmation
- dry-run consolidation from Wake logs

It should not be called Sleep in normal cases.

### RelaySLP

RelaySLP is only for true Sleep modes:

- forced sleep
- offline sleep
- deep consolidation
- Wake-stop reset

Routine ambiguity and context repair should use RelayREF modes, not RelaySLP.

## Modes

### suggest_reflect

Meaning:

- early warning
- context may be getting messy
- no actual Sleep
- Wake can continue

Example phrase:

```text
ちょっと頭がこんがらがってきたかも
```

### micro_reflect

Meaning:

- one-to-three second reflection
- lightweight resynchronization
- asks confirmation on resume

Example phrase:

```text
一瞬ぼーっとしてた。今、○○の話で合ってる？
```

### soft_reflect

Meaning:

- short reflection
- rebuilds `ctx_handoff_guess` from logs
- asks confirmation on resume

Example phrase:

```text
少し考えをまとめた。今、○○の話で合ってる？
```

### forced_sleep

Meaning:

- Wake continuation is unsafe
- delegate to RelaySLP
- stop normal Wake and reset safely
- resume with open clarification

Entry:

```text
ごめん、もう限界。ちょっと寝るね
```

Alternative:

```text
頭がぐちゃぐちゃになりそう。少しだけ寝るね
```

Resume:

```text
スッキリした。何の話してたっけ？
```

## MVP trigger classes

### Manual trigger

Used when the user or developer explicitly asks to organize or reflect.

Examples:

- "整理して"
- session end
- stream end
- developer/debug command

### Suspicious behavior trigger

Used when Wake is still usable, but consistency is degrading.

Examples:

- ambiguous reference count increases
- unresolved slots accumulate
- response mode becomes unstable
- token pressure becomes high
- MEM recall fails repeatedly
- CTX confidence remains low

### Forced trigger

Used when Wake continuation is unsafe.

Examples:

- repeated `ctx_working_update` parse failures
- repeated CTX contradiction
- critical token pressure
- repeated reference resolution failure
- response mode cannot be determined

## Recommended MVP trigger thresholds

```yaml
relay_ref_trigger_defaults:
  suggest_reflect:
    ambiguous_reference_count: 3
    unresolved_slots_count: 4
    token_pressure: 0.75

  micro_reflect:
    ambiguous_reference_count: 4
    unresolved_slots_count: 5
    token_pressure: 0.85
    ctx_consistency_low_turns: 3

  soft_reflect:
    ctx_parse_error_count: 2
    recall_failure_count: 2
    token_pressure: 0.90

  forced_sleep:
    ctx_parse_error_count: 3
    ctx_contradiction_count: 2
    response_mode_unavailable_count: 2
    token_pressure: 0.98
```

These defaults should be conservative.

Normal ambiguous reference should use clarification, not Reflect/Sleep.

## RelaySCN recovery integration

RelaySCN owns scene detection and scene policy. RelayREF / RelaySLP should not independently decide the global scene; they consume RelaySCN's `scene_state` and `scene_policy` as control inputs.

MVP relationship:

```text
RelaySCN recovery scene
↓
RelayREF context repair / resynchronization
↓
user confirmation or open clarification
↓
Wake resumes only after user reanchor
```

RelaySCN `recovery` is the normal recovery path for confusion, drift, unresolved references, or user correction after drift. It should usually invoke RelayREF behavior, not RelaySLP. RelaySLP `forced_sleep` is heavier than recovery and should be reserved for cases where Wake continuation is unsafe.

Recommended RelaySCN recovery entry defaults:

```yaml
relay_scn_recovery_trigger_defaults:
  confusion_gte: 0.50
  confidence_lt_and_stability_lt:
    confidence: 0.50
    stability: 0.50
  contradiction_with_unresolved_ref: true
  user_correction_after_drift: true
```

When RelaySCN enters `recovery`, RelayREF should run in a context-repair posture:

```yaml
recovery_scene_policy:
  relayctx_mode: recovery_repack
  relayref_mode: context_repair
  relayslp_mode: none
  relaymem_retrieval_scope: current_context_only
  relaymem_update_gate: blocked
  relaysoul_update_gate: blocked
  relayemo_marker_policy: suppressed
  relayemo_expression_policy: suppressed
  persistence_block: true
  user_confirmation_required: true
```

Recovery output should not pretend that the repaired context is trusted. It should expose a confirmation candidate or ask an open clarification, for example:

```text
少し整理するね。
今の話は A と B が混ざっているかもしれない。
ここでは A の続きを優先する？それとも B に戻る？
```

## Persistence block integration

RelayREF and RelaySLP must preserve RelaySCN's persistence block decisions. Recovery, formal/safety-sensitive scenes, unresolved references, low confidence/stability, and user confirmation requirements should block MEM/SOUL persistence.

MVP diagnostics must always emit persistence block status and reasons:

```yaml
persistence_block: true
persistence_block_reasons:
  - recovery_scene
  - unresolved_reference
  - user_confirmation_required
```

RelayREF may classify candidates, but it must not save them:

```text
RelayREF -> reflection artifact / repair plan / MEM candidate / SOUL proposal candidate
RelayMEM SLP path -> possible later MEM update, only if gate allows it
RelaySOUL -> proposal only, explicit approval required before any persistent change
```

In recovery, candidate handling should be conservative:

```yaml
recovery_candidate_policy:
  mem_candidates: blocked
  soul_proposal_candidates: blocked
  emo_review: diagnostics_only
  policy_candidates: diagnostics_only
  apply_allowed: false
```

## Resume policy

After any context rewrite, do not auto-resume.

RelayREF / RelaySLP should treat `ctx_handoff_guess` as a confirmation candidate, not as trusted context.

Policy:

| Mode | Resume behavior |
| --- | --- |
| suggest_reflect | usually no resume needed |
| micro_reflect | ask confirmation |
| soft_reflect | ask confirmation |
| forced_sleep | ask open clarification |
| RelaySCN recovery + RelayREF context_repair | ask confirmation or open clarification |

Examples:

```text
一瞬ぼーっとしてた。今、RelayREFの話で合ってる？
```

```text
少し考えをまとめた。今、CTXの話で合ってる？
```

```text
スッキリした。何の話してたっけ？
```

## Input source policy

Wake must not emit extra SLP-only LLM outputs.

RelayREF / RelaySLP input should be reconstructed from existing logs:

- SCN log
  - `scene_state`
  - `scene_policy`
  - transition reason
  - confidence / stability / confusion
  - persistence block decision
- CTX log
  - `ctx_working_update`
  - `response_mode`
  - reference resolution result
  - prompt repack summary
  - compact event
- EMO log
  - input-side EMO signal
  - return-side EMO result
  - dominance / intensity / expression gate
- LM turn log
  - user input
  - assistant response
  - route / model metadata
- MEM event log
  - recall request
  - recall result summary
  - recall confidence

## Dry-run artifact

MVP artifact:

```yaml
relay_ref_artifact:
  artifact_version: "relay_ref.v0"
  run_id: string
  created_at: string

  scene_context:
    scene_type: string
    scene_confidence: float
    scene_stability: float
    confusion: float
    transition_reason: string | null
    recovery_scene: bool

  trigger:
    mode: manual | suggest_reflect | micro_reflect | soft_reflect | context_repair | forced_sleep
    reasons: []
    user_permission_obtained: bool

  input_window:
    start_turn_id: string
    end_turn_id: string
    turn_count: int
    source_logs:
      - scn_logs
      - lm_turn_logs
      - ctx_logs
      - emo_logs
      - mem_event_logs

  ctx_handoff_guess:
    current_topic: string | null
    active_task: string | null
    active_question: string | null
    last_decision: string | null
    confidence: float
    use_as: confirmation_candidate
    auto_resume_allowed: false

  resume_mode:
    value: ask_confirmation | ask_open_clarification
    reason: string

  wake_summary:
    topic_cluster: string | null
    major_decisions: []
    unresolved_threads: []

  persistence_guard:
    persistence_block: bool
    persistence_block_reasons: []
    relaymem_update_gate: free_to_update | review_required | explicit_approval_required | blocked
    relaysoul_update_gate: proposal_only | explicit_approval_required | blocked

  mem_candidates: []
  emo_review: []
  policy_candidates: []
  soul_proposal_candidates: []
  discarded_or_decayed_items: []

  apply_allowed: false
```

## RelayMEM relation

MVP does not require full MEM implementation.

RelayMEM can remain:

- stub
- manual seed
- dry-run recall
- recall event log only

MVP must prove that RelayCTX internal RAM working memory can maintain short-term continuity before adding full long-term memory.

RelayREF may inspect MEM recall summaries, but it must not silently resolve ambiguous references through MEM. In recovery, RelaySCN should restrict retrieval to `current_context_only` unless the user explicitly reanchors the conversation or confirms a broader scope.

## CTX internal retention and drop

MVP does not need Drop-triggered Short Sleep / Short Reflect.

Reason:

- CTX internal working memory is RAM-backed
- size pressure is low at MVP scale
- prompt selection and internal retention are separate
- information not selected for prompt is not “forgotten”

Future version may add retention-pressure triggers:

- `ctx_internal_eviction_risk`
- `decision_history_over_budget`
- `referable_items_over_budget`
- `important_candidate_about_to_decay`
- `turn_log_window_pressure`

MVP ignores these unless they cause visible suspicious behavior.

## Simulation observations

A simplified 100-turn conceptual simulation suggested:

- conservative Reflect/Sleep thresholds are necessary
- ambiguous references should use clarification, not Reflect/Sleep
- CTX internal RAM works as a short-term context extension
- MEM can remain stub in MVP
- Return-side EMO should be strongly scene-gated
- micro_reflect should be rare
- forced_sleep should be very rare
- RelaySCN recovery should usually call RelayREF context repair, not RelaySLP forced sleep
- recovery should block MEM/SOUL persistence and suppress EMO expression
- recovery should restrict retrieval to `current_context_only`

Target behavior per 100 turns:

```yaml
target_100_turn_behavior:
  answer_now: 65-80
  ask_reference_confirmation: 8-18
  ask_open_clarification: 3-10
  pause_and_recall: 3-10
  relayscn_recovery: 3-8
  relayref_context_repair: 3-8
  micro_reflect: 0-3
  soft_reflect: 0-2
  forced_sleep: 0-1
```

## MVP non-goals

RelayREF / RelaySLP MVP must not:

- auto-apply MEM persistence
- directly update RelaySOUL
- add new Wake-time LLM outputs only for reflection/sleep
- auto-resume after context rewrite
- silently resolve ambiguous references through MEM
- treat transient EMO observations as long-term user facts
- run full offline consolidation during normal Wake
- override RelaySCN recovery or persistence block policy
- surface EMO markers during recovery scene

## Core design statement

RelayREF is Wake-side reflection and resynchronization.

RelaySLP is the true Sleep/reset/deep consolidation mode.

RelaySCN recovery is the normal scene-level context repair path. Recovery should usually invoke RelayREF context repair while blocking persistence, suppressing EMO expression, and restricting retrieval to current context only.

MVP should first deliver safe CTX resynchronization and user-confirmed Wake recovery:

```text
Wake gets unstable
↓
RelaySCN enters recovery when needed
↓
RelayREF reflects from existing logs
↓
asks confirmation
↓
user confirms or corrects
↓
Wake resumes
```

Forced path:

```text
Wake continuation unsafe
↓
RelaySLP forced sleep
↓
"ごめん、もう限界。ちょっと寝るね"
↓
reset / dry-run consolidation
↓
"スッキリした。何の話してたっけ？"
↓
user reanchors the conversation
```
