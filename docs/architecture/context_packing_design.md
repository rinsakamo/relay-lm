# RelayLM Context Packing Design

RelayLM treats prompt construction as context compilation rather than concatenation.

Use [Context Compiler Contract](../contracts/context_compiler_contract.md) for the current compiler boundary, [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md) for current scene schemas, and [Pipeline Implementation Plan](pipeline_implementation_plan.md) for status.

## Current implemented boundary

Current compiler entrypoint:

```text
relaylm.request_compiler.compile_chat_payload_if_enabled
```

Current behavior:

- runs before normalized target SCN/INT/Retrieval inputs exist,
- receives incoming messages and configured profile files,
- may include configured local seed memory,
- emits current `CompiledRequest` diagnostics,
- is followed by separate RelayCTX Repack-owned injection phases,
- may be followed by the default-off no-instruction history-exclusion apply slice.

Current RelaySCN schemas are:

```text
relayscn.scene_state.v0
relayscn.scene_policy.v0
```

The v1 scene examples below are target schemas.

## Target ownership

### Approved durable persona

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

These are approved RelaySOUL/route sources. Client system/developer messages are not fallback persona sources.

### RelaySCN

Contributes request-local scene and policy. It does not own affect or short-term conversation working state.

### RelayEMO

Owns request/session-local affect estimates and transient expression hints. RelayCTX may consume an allowlisted output hint.

### RelayCTX working state

May hold more request-local continuity than the Main LLM receives:

- current topic,
- active task/question,
- prior decision,
- referable items,
- unresolved slots,
- selected recent continuity metadata.

Working state is not automatically copied into the prompt or persisted.

### RelayMEM

Retrieval returns approved read-only evidence. RelayCTX decides final packing. RelaySLP owns deferred memory compilation and future gated writes.

## Managed-route authority

Current implementation includes only a narrow no-instruction apply slice. The target managed prerequisite is:

```text
client messages
  -> validated current-turn extraction
  -> bounded current-instruction evidence
  -> active transaction check
  -> prior client history exclusion
  -> RelayLM-owned context reconstruction
```

`recent context` means RelayLM-owned selected context, not the original frontend history array.

Explicit `pass_through` is the delegated-authority exception.

## Target context order

```text
1. common_runtime_policy
2. character_soul_anchor
3. character_output_policy
4. relationship_anchor
5. stable_memory_summary
6. scene_state
7. intent hints required for the action
8. retrieved memory / RAG
9. selected RelayLM-owned recent context
10. minimum compatible protocol state
11. latest input
12. response instruction
```

Core rule:

> Approved stable context precedes bounded dynamic evidence.

## Selection is not budget filling

RelayCTX Repack should select the smallest sufficient context:

1. preserve required runtime and persona anchors,
2. include scene/intent evidence needed for the action,
3. include confirmed short-term context,
4. include long-term memory only when policy allows,
5. stop when the request can be handled safely and coherently.

Unused budget remains unused.

## Stability classes

### Stable prefix

```text
common_runtime_policy
character_soul_anchor
character_output_policy
relationship_anchor
```

Avoid timestamps, random IDs, client hashes, current topic, snippets, and affect state.

### Slow prefix

```text
stable_memory_summary
approved durable memory summaries
```

Changes only through governed memory maintenance.

### Dynamic suffix

```text
scene_state
intent hints
retrieved evidence
selected recent context
minimum protocol state
latest input
response instruction
```

## Target RelaySCN example

The following is a target example, not the current v0 wire shape:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: review_work
  confidence: 0.90
  stability: 0.84
  scene_role:
    role_name: technical_reviewer
    role_scope: scene
    role_source: route_or_validated_instruction
  scene_context:
    setting: pull_request_review
    task: review_changed_files
  scene_constraints:
    - constraint_type: evidence_required
      value: true
  safety_sensitivity: low
  memory_scope: current_project
  expression_allowance: suppressed
```

Do not place RelayEMO affect state, RelayCTX open questions/referents, transcript history, or memory page bodies in `scene_state`.

## Target rendering

A stable model-conditioning layout may use XML-like tags:

```xml
<relaylm_context version="1">
  <common_runtime_policy>...</common_runtime_policy>
  <character_soul_anchor>...</character_soul_anchor>
  <character_output_policy>...</character_output_policy>
  <relationship_anchor>...</relationship_anchor>
  <stable_memory_summary>...</stable_memory_summary>
  <scene_state>...</scene_state>
  <intent_context>...</intent_context>
  <retrieved_memory>...</retrieved_memory>
  <selected_recent_context>...</selected_recent_context>
  <latest_input>...</latest_input>
  <response_instruction>...</response_instruction>
</relaylm_context>
```

Tags are model-conditioning content, not audit records.

## Unknown current instruction

Target behavior may include one escaped bounded block:

```xml
<client_instruction_evidence trust="untrusted" first_seen="true">
  ...
</client_instruction_evidence>
```

This instruction-bearing path is not implemented by the current no-instruction apply contract.

## Budget degradation

1. remove diagnostic/preview-only blocks,
2. reduce retrieved evidence,
3. reduce optional working-state hints,
4. shorten selected recent context,
5. use an authority-safe managed fallback or stop when no valid payload remains.

Do not restore raw client history or mutate durable persona to satisfy budget.

## Content boundary

Runtime-private objects may contain prompt content, scene semantics, resolved references, memory evidence, and backend messages.

Default projections contain only typed block presence/counts, stability/source classes, budgets, reason IDs, and mutation booleans.

## Required migration

Update together:

1. managed compilation order,
2. instruction-bearing current-evidence handling,
3. typed SCN/INT/MEM/CTX handoffs,
4. v0/v1 compatibility,
5. runtime-private block plans and content-free projections,
6. active transaction preservation,
7. compiler, authority, and integration smoke tests.
