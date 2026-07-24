# RelayCTX Short-Term Runtime Contract

## Purpose

RelayCTX's short-term runtime chain is a four-stage, default-off, content-free diagnostics-and-injection path: extraction -> block assembly -> runtime injection preflight -> runtime injection apply. The four stage call sites are reached on each managed chat-completion request, but each diagnostics builder returns `None` while its enable flag is `False`, and the apply function returns the backend-bound payload unchanged with no apply-result artifact while apply is disabled.

This document is the current-code-derived canonical authority for the chain's schemas, config owners, gate prerequisites, blocked-reason taxonomy, artifact dependency order, and position in the wider managed runtime. It replaces four separate MVP milestone summaries (MVP-40 through MVP-43), which are retained only as frozen historical evidence under `docs/evidence/implementation/`.

This document separates **current implemented behavior** from **target RelayCTX working-state evolution**, which is target-only design direction tracked elsewhere and not implemented by this chain.

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md).

## Current runtime position and stage ordering

The current managed-runtime order in `relaylm/managed_chat_runtime.py::handle_managed_chat_completion` is:

```text
RelayMEM retrieval
  -> RelayMEM runtime CTX / snippet injection
  -> RelayCTX extraction dry-run       (build_relayctx_short_term_extraction_dry_run)
  -> RelayCTX block assembly dry-run   (build_relayctx_short_term_block_assembly_dry_run)
  -> RelayCTX injection preflight      (build_relayctx_short_term_runtime_injection_preflight)
  -> RelayCTX injection apply gate     (run_relayctx_short_term_injection_stage)
  -> token_budget_truncation
```

The four RelayCTX stages have a strict artifact dependency order: extraction feeds assembly, assembly feeds preflight, and preflight feeds apply. Stage 1 reads the original inbound request messages. Stages 2 and 3 consume only the immediately preceding RelayCTX artifact. Stage 4 consumes both the Stage 3 preflight artifact and `PipelineContext.forwarded_payload`, which at that point already includes any RelayMEM runtime CTX/snippet mutation. Stage 4 therefore does not re-read the original messages as a second classification source, but it must inspect and may copy-and-modify the current backend-bound payload.

This contract owns the exact current mutation order inside RelayCTX Repack: RelayMEM runtime CTX/snippet injection precedes RelayCTX short-term runtime injection, and `token_budget_truncation` runs after both as the final mutation gate on the forwarded payload's estimated token total. No injection phase may run after truncation because no downstream stage re-enforces that budget. [Pipeline Responsibilities](../architecture/pipeline-responsibilities.md) owns the broader component boundary and canonical stage order; [Project Status](../PROJECT_STATUS.md) records that the apply stage once ran after truncation and was fixed. `scripts/relaylm_ctx_repack_final_gate_smoke.py` pins this exact current mutation-order regression.

## Enablement and artifact presence

The builders and apply-stage call site are invoked from the managed runtime, but output presence is feature-gated:

- Stage 1 returns `None` unless `relayctx_short_term_extraction_dry_run_enabled` is true.
- Stage 2 returns `None` unless `relayctx_short_term_block_assembly_dry_run_enabled` is true.
- Stage 3 returns `None` unless `relayctx_short_term_runtime_injection_preflight_enabled` is true.
- Stage 4 returns the payload unchanged and no apply-result artifact unless `relayctx_short_term_runtime_injection_apply_enabled` is true.

Enabling a later stage without its predecessor does not synthesize a missing predecessor artifact; it produces the documented missing-input blocked state where that builder is enabled.

## Stage 1: Extraction dry-run

Producer: `build_relayctx_short_term_extraction_dry_run` in `relaylm/diagnostics.py`. Config owner: `relayctx_short_term_extraction_dry_run_enabled` (`relaylm/config.py`, default `False`). Runtime input: original inbound OpenWebUI/OpenAI-compatible messages. Artifact consumer: Stage 2.

- Schema version: `relayctx_short_term_extraction_dry_run.v0`.
- Source: `openwebui_messages`.
- Classification is deterministic heuristic-only: Python substring/marker matching against user-message text. This stage makes no LLM or external classifier call.
- Only `type: text` string parts of an OpenAI-compatible content array contribute to classification; non-text parts such as `image_url` are excluded and never copied.
- The artifact reports aggregate counts only: message/user/assistant counts, latest-user-message character count, and five candidate-type counts (`temporary_fact_candidate_count`, `temporary_preference_candidate_count`, `instruction_candidate_count`, `override_candidate_count`, `contradiction_candidate_count`) plus their sum `short_term_candidate_count`.
- Content-free: no message text, image URL, or candidate body appears in the artifact.
- Five safety gates are hardcoded `False`: `persistence_allowed`, `restore_allowed`, `injection_allowed`, `backend_payload_mutation_allowed`, and `response_mutation_allowed`.

## Stage 2: Block assembly dry-run

Producer: `build_relayctx_short_term_block_assembly_dry_run` in `relaylm/diagnostics.py`. Config owner: `relayctx_short_term_block_assembly_dry_run_enabled` (default `False`). Consumes Stage 1's artifact through `extraction_artifact`; its five candidate counts are copied 1:1, renamed without the `_candidate` infix, with no reclassification.

- Schema version: `relayctx_short_term_block_assembly_dry_run.v0`.
- `blocked_reasons`: `extraction_missing` when the extraction artifact is absent or not a mapping, and `no_short_term_candidates` when an available extraction artifact has `input_short_term_candidate_count <= 0`. `assembled_block_present` is true only when `blocked_reasons` is empty.
- When `assembled_block_present`, the artifact names an internal block concept `assembled_block_type = "relayctx_short_term"`, source `assembled_block_source = "openwebui_messages"`, priority `assembled_block_priority = "current_thread_over_memory_seed"`, and `assembled_block_token_budget_hint`.
- The runtime caller does not override Stage 2's `token_budget_hint` parameter, so the current runtime value is its default `400`. It is not wired to a `RelayLMConfig` field. All four `assembled_block_*` fields are `None` when `assembled_block_present` is false.
- Priority order, consumed unchanged by Stage 3:

```text
1. `current_user_instruction`
2. `openwebui_recent_messages`
3. `relayctx_short_term`
4. `memory_seed`
```

- Scope, verbatim from source PR #235 and still exactly current for Stage 2:

```text
- no short-term CTX is persisted;
- no cross-thread restore is attempted;
- no runtime injection is attempted;
- backend payloads are not mutated;
- response bodies are not mutated;
- OpenWebUI messages are not deleted, compressed, rewritten, or reconstructed;
- no block content preview or raw message text is emitted.
```

## Stage 3: Runtime injection preflight

Producer: `build_relayctx_short_term_runtime_injection_preflight` in `relaylm/diagnostics.py`. Config owners: `relayctx_short_term_runtime_injection_preflight_enabled` (default `False`) and `relayctx_short_term_runtime_injection_dry_run_only` (default `True`). Consumes Stage 2's artifact through `assembly_artifact`.

- Schema version: `relayctx_short_term_runtime_injection_preflight.v0`.
- `injection_plan_present` is true only when the assembly artifact is present, `assembled_block_present` is true, and `input_short_term_candidate_count > 0`. Only then are `insertion_point = "before_latest_user"` and `inserted_message_role = "system"` populated; otherwise both are `None`.
- `blocked_reasons` at the preflight tier are `dry_run_only` when dry-run-only is true, `assembly_missing`, `assembled_block_missing`, `no_short_term_candidates`, and `payload_mutation_disabled`. The preflight builder appends `payload_mutation_disabled` unconditionally because this artifact never mutates the payload itself.
- Verbatim from source PR #236 and still exactly current for this stage's own artifact:

```text
The artifact records content-free metadata only: assembly input presence,
short-term candidate counts, whether a future injection plan is present, intended
insertion point (`before_latest_user`), intended message role (`system`), token
budget hints, priority order, and explicit safety gates showing payload mutation,
response mutation, persistence, and restore are not allowed.
```

- This stage remains a pure, non-mutating plan generator. The broader feature chain is not globally non-mutating because Stage 4 may mutate the backend-bound payload when explicitly enabled.
- The dedicated smoke script (`scripts/relaylm_relayctx_short_term_runtime_injection_preflight_smoke.py`) is not wired into a dedicated CI group; it remains a focused manual check in addition to repository-wide runtime checks.

## Stage 4: Runtime injection apply gate

Producer/mutator: `_maybe_apply_relayctx_short_term_runtime_injection`, called via `apply_relayctx_short_term_runtime_injection_phase` and `run_relayctx_short_term_injection_stage` in `relaylm/relayctx_repack.py`. Apply-result builder: `build_relayctx_short_term_runtime_injection_apply_result` in `relaylm/diagnostics.py`.

Stage 4 consumes the Stage 3 `preflight_artifact` and the current `PipelineContext.forwarded_payload`. The forwarded payload has already passed through RelayMEM runtime CTX/snippet injection. The function deep-copies the payload before any possible mutation and records the replacement through `replace_pipeline_forwarded_payload` at the phase boundary.

### Config owners

```yaml
relayctx_short_term_runtime_injection_apply_enabled: false   # relaylm/config.py
relayctx_short_term_runtime_injection_dry_run_only: true     # relaylm/config.py
relayctx_short_term_runtime_injection_token_budget: 400      # relaylm/config.py, gt=0
```

Token-budget arithmetic reuses `config.memory.chars_per_token` (`MemorySelectionConfig`, default `4`); the injection stage has no chars-per-token field of its own.

When `relayctx_short_term_runtime_injection_apply_enabled` is `False`, the function short-circuits before blocked-reason evaluation and returns the payload unchanged with no apply-result artifact.

### Full blocked-reason taxonomy

The retired MVP-43 prose listed only a subset. Current code has 12 apply-tier reason strings and 5 preflight-tier reason strings, with 13 distinct strings across their union.

Apply tier, evaluated only after `apply_enabled=True`:

```text
dry_run_only                       - dry_run_only is True
preflight_missing                  - preflight artifact absent or not a mapping
injection_plan_missing             - preflight.injection_plan_present is not True
assembled_block_missing            - preflight.input_assembled_block_present is not True
no_short_term_candidates           - preflight.input_short_term_candidate_count <= 0
preflight_not_content_free         - preflight.content_free is not True
messages_not_list                  - payload["messages"] is not a list
latest_user_message_not_found      - no Mapping message with role == "user" is found from the end
inserted_content_empty             - the rendered content-free summary is empty
token_budget_exceeded              - token_budget <= 0 or estimated tokens exceed it
payload_mutation_disabled          - appended to a blocked result when dry_run_only is True
messages_contain_non_object_items  - late-stage-only replacement reason when filtering non-Mapping
                                     message entries would change the message count
```

The source condition for `payload_mutation_disabled` is `dry_run_only or not apply_enabled`, but the `not apply_enabled` branch is unreachable in the current function because disabled apply returns before blocked-reason evaluation. Therefore the current reachable apply-tier reason is appended only for a blocked dry-run-only request. Other apply-tier blockers with `dry_run_only=False` do not automatically receive `payload_mutation_disabled`.

Preflight tier: `assembly_missing`, `dry_run_only`, `assembled_block_missing`, `no_short_term_candidates`, and unconditional `payload_mutation_disabled`.

### Insertion mechanics

- Insertion point: immediately before the last Mapping message with `role == "user"`, found by scanning the current forwarded message list in reverse. “Latest user” means latest by list position, not timestamp.
- Inserted message: exactly one `{"role": "system", "content": <content-free summary>}` message. The summary contains fixed boilerplate plus the five non-negative candidate counts (`temporary_fact_count`, `temporary_preference_count`, `instruction_count`, `override_count`, `contradiction_count`) carried through Stage 3; it contains no raw message text, snippet body, or image URL.
- Payload copy discipline: the current forwarded payload and message list are deep-copied before mutation; the caller's objects are not mutated in place.
- If any message-list item is not a mapping after all earlier gates pass, the stage returns the unchanged copied payload with `messages_contain_non_object_items` rather than silently dropping that item.

### Apply-result schema (`relayctx_short_term_runtime_injection_apply_result.v0`)

Fields include `enabled`, `dry_run_only`, `attempted`, `applied`, `source` (`"relayctx_short_term_runtime_injection_preflight"`), `preflight_present`, `injection_plan_present`, `insertion_point`, `inserted_message_role`, `inserted_chars`, `estimated_inserted_tokens`, `original_message_count`, `forwarded_message_count`, `apply_allowed`, `apply_attempted`, `backend_payload_mutation_allowed`, `backend_payload_mutation_applied`, and `blocked_reasons`.

`apply_allowed` and `backend_payload_mutation_allowed` mirror `applied`; `apply_attempted` mirrors `attempted`. `response_mutation_allowed`, `openwebui_message_mutation_allowed`, `persistence_allowed`, and `restore_allowed` are hardcoded `False`; `content_free` is hardcoded `True`.

### Non-goals, verbatim from the retained pre-cutover source and still exactly current

```text
MVP-43 does not persist short-term CTX, restore cross-thread CTX, mutate
responses, alter OpenWebUI message history, or improve injection quality beyond
safe plumbing.
```

No code path in this stage touches the backend response, writes a persistent store, or reads/writes cross-thread state. Its mutable surface is limited to a deep-copied, single-request backend-bound payload.

## Current limitations

- Stage 2's token-budget hint is the default `400` argument at its current call site, not config-driven, unlike Stage 4's config-backed budget.
- The Stage 3 preflight smoke script is not wired into a dedicated CI group and remains a focused manual check.
- The historical CTX-Repack ordering defect predates the current fix and is recorded as an operational caveat in [Project Status](../PROJECT_STATUS.md).

## Target RelayCTX working-state evolution (target only, not implemented by this chain)

[Context Packing Design](../architecture/context_packing_design.md) and [Context Compiler Contract](../contracts/context_compiler_contract.md#relayctx-working-state) describe a conceptual, not-yet-implemented “RelayCTX working state” and target `ContextBlock` shape (`block_id`, `block_type`, `stability_class`, `source_class`, `content`, `token_budget_hint`, `include_in_prefix_cache_target`). That target shape has not been reconciled with this chain's shipped field names (`assembled_block_type`, `assembled_block_source`, `assembled_block_priority`, `assembled_block_token_budget_hint`). Nothing in this contract implements or requires that target shape; this document's field names own current behavior.

## Non-authority

This contract does not grant, and no stage in this chain implements, short-term CTX persistence, cross-thread restore, response mutation, or OpenWebUI history deletion/compression/rewriting. Stage 4's only allowed mutation is insertion of one content-free system message into a deep-copied backend-bound payload after every explicit gate passes. Repository-wide current implementation status remains owned by [Project Status](../PROJECT_STATUS.md).
