# RelayCTX Short-Term Runtime Contract

## Purpose

RelayCTX's short-term runtime chain is a four-stage, default-off, content-free diagnostics-and-injection pipeline that runs on every managed chat completion request: extraction -> block assembly -> runtime injection preflight -> runtime injection apply. This document is the current-code-derived canonical authority for that chain's schemas, config owners, gate prerequisites, blocked-reason taxonomy, and stage ordering. It replaces four separate MVP milestone summaries (MVP-40 through MVP-43), which are retained only as frozen historical evidence under `docs/evidence/implementation/`.

This document separates **current implemented behavior** from **target RelayCTX working-state evolution**, which is target-only design direction tracked elsewhere and not implemented by this chain.

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md).

## Current runtime position and stage ordering

Each managed chat completion request builds all four artifacts in a fixed order inside `relaylm/managed_chat_runtime.py::handle_managed_chat_completion`:

```text
inbound OpenWebUI/OpenAI-compatible messages
  -> extraction dry-run       (build_relayctx_short_term_extraction_dry_run)
  -> block assembly dry-run   (build_relayctx_short_term_block_assembly_dry_run)
  -> injection preflight      (build_relayctx_short_term_runtime_injection_preflight)
  -> [ RelayMEM runtime CTX / snippet injection stage runs here ]
  -> injection apply gate     (run_relayctx_short_term_injection_stage / relaylm/relayctx_repack.py)
  -> token_budget_truncation
```

Each stage's builder consumes only the immediately preceding stage's artifact — extraction feeds assembly, assembly feeds preflight, preflight feeds apply — never raw messages a second time and never a stage two steps back.

The apply gate's position relative to RelayMEM injection and token-budget truncation is owned by [Pipeline Responsibility Design §9 RelayCTX Repack](../architecture/pipeline_responsibility_design.md#9-relayctx-repack), which states the current phase order (`relaymem runtime CTX/snippet injection -> RelayCTX short-term runtime injection -> token_budget_truncation`) and the rule that injection phases must not run after truncation. This contract does not restate that ordering rule as a second authority; it only confirms the apply gate (`relayctx_short_term_runtime_injection`) is the stage `run_relayctx_short_term_injection_stage` names in that ordering. [Project Status](../PROJECT_STATUS.md) records that this ordering was once implemented incorrectly (apply ran after truncation, in `relaylm/app.py`) and was fixed; `scripts/relaylm_ctx_repack_final_gate_smoke.py` is the regression test pinning the fix.

## Stage 1: Extraction dry-run

Producer: `build_relayctx_short_term_extraction_dry_run` in `relaylm/diagnostics.py`. Config owner: `relayctx_short_term_extraction_dry_run_enabled` (`relaylm/config.py`, default `False`). Consumer: `relaylm/managed_chat_runtime.py`, immediately followed by Stage 2.

- Schema version: `relayctx_short_term_extraction_dry_run.v0`.
- Source: `openwebui_messages` (inbound request messages only).
- Classification is deterministic heuristic-only: plain Python substring/marker matching against message text. No LLM or external classifier call is made anywhere in this stage or in Stages 2-4.
- Only `type: text` string parts of an OpenAI-compatible content array contribute to classification; non-text parts (e.g. `image_url`, Responses-API `input_text`) are silently excluded, never counted, never copied.
- The artifact reports aggregate counts only: message/user/assistant counts, latest-user-message character count, and five candidate-type counts (`temporary_fact_candidate_count`, `temporary_preference_candidate_count`, `instruction_candidate_count`, `override_candidate_count`, `contradiction_candidate_count`) plus their sum `short_term_candidate_count`.
- Content-free: no message text, image URL, or candidate body ever appears in the artifact.
- Five safety gates are hardcoded `False` regardless of input: `persistence_allowed`, `restore_allowed`, `injection_allowed`, `backend_payload_mutation_allowed`, `response_mutation_allowed`.

## Stage 2: Block assembly dry-run

Producer: `build_relayctx_short_term_block_assembly_dry_run` in `relaylm/diagnostics.py`. Config owner: `relayctx_short_term_block_assembly_dry_run_enabled` (default `False`). Consumes Stage 1's artifact directly (`extraction_artifact` parameter); its five candidate counts are copied 1:1 (renamed without the `_candidate` infix) with no re-aggregation.

- Schema version: `relayctx_short_term_block_assembly_dry_run.v0`.
- `blocked_reasons`: `extraction_missing` (extraction artifact absent or not a mapping) and/or `no_short_term_candidates` (`input_short_term_candidate_count <= 0`). `assembled_block_present` is true only when `blocked_reasons` is empty.
- When `assembled_block_present`, the artifact names an internal block concept `assembled_block_type = "relayctx_short_term"`, source `assembled_block_source = "openwebui_messages"`, priority `assembled_block_priority = "current_thread_over_memory_seed"`, and a token-budget hint `assembled_block_token_budget_hint`. **Current limitation:** this token-budget hint is a hardcoded `400`-token constant at this stage; it is not wired to any `RelayLMConfig` field (unlike the Stage 4 apply budget, which is a real config field — see Stage 4). All four `assembled_block_*` fields are `None` when `assembled_block_present` is false.
- Priority order (the only priority-ordering logic in the codebase; also read back unchanged by Stage 3):

```text
1. `current_user_instruction`
2. `openwebui_recent_messages`
3. `relayctx_short_term`
4. `memory_seed`
```

- Scope, verbatim from source PR #235 and still exactly current:

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

Producer: `build_relayctx_short_term_runtime_injection_preflight` in `relaylm/diagnostics.py`. Config owners: `relayctx_short_term_runtime_injection_preflight_enabled` (default `False`), `relayctx_short_term_runtime_injection_dry_run_only` (default `True`). Consumes Stage 2's artifact directly (`assembly_artifact` parameter).

- Schema version: `relayctx_short_term_runtime_injection_preflight.v0`.
- `injection_plan_present` is true only when the assembly artifact is present, `assembled_block_present` is true, and `input_short_term_candidate_count > 0`. Only then are `insertion_point = "before_latest_user"` and `inserted_message_role = "system"` populated (else both `None`).
- `blocked_reasons` (preflight tier): `dry_run_only` (if `dry_run_only`), `assembly_missing` (assembly artifact absent), `assembled_block_missing` (assembly present but its block was not assembled), `no_short_term_candidates`, and `payload_mutation_disabled` (appended unconditionally — the preflight builder never mutates by design, regardless of any other condition).
- Verbatim from source PR #236 and still exactly current, describing this stage's own artifact:

```text
The artifact records content-free metadata only: assembly input presence,
short-term candidate counts, whether a future injection plan is present, intended
insertion point (`before_latest_user`), intended message role (`system`), token
budget hints, priority order, and explicit safety gates showing payload mutation,
response mutation, persistence, and restore are not allowed.
```

- **Current limitation:** this stage's own artifact/behavior remains a pure, non-mutating plan generator exactly as originally documented, but the broader RelayCTX short-term feature area it feeds is no longer non-mutating as a whole — Stage 4 (below) can mutate the backend-bound payload when explicitly enabled. Any restatement of this stage's non-mutation claim must be scoped to the preflight artifact, not to the chain overall.
- The dedicated smoke script (`scripts/relaylm_relayctx_short_term_runtime_injection_preflight_smoke.py`) is not wired into any CI workflow group today; it is a manual-only regression check (see Current limitations below).

## Stage 4: Runtime injection apply gate

Producer/mutator: `_maybe_apply_relayctx_short_term_runtime_injection`, called via `apply_relayctx_short_term_runtime_injection_phase` / `run_relayctx_short_term_injection_stage` in `relaylm/relayctx_repack.py`. Apply-result builder: `build_relayctx_short_term_runtime_injection_apply_result` in `relaylm/diagnostics.py`. Consumes Stage 3's artifact directly (`preflight_artifact` parameter).

### Config owners

```yaml
relayctx_short_term_runtime_injection_apply_enabled: false   # relaylm/config.py
relayctx_short_term_runtime_injection_dry_run_only: true     # relaylm/config.py
relayctx_short_term_runtime_injection_token_budget: 400      # relaylm/config.py, gt=0
```

Token-budget arithmetic reuses `config.memory.chars_per_token` (`MemorySelectionConfig`, default `4`) — the injection stage has no chars-per-token field of its own; it borrows the memory stanza's.

If `relayctx_short_term_runtime_injection_apply_enabled` is `False`, the function short-circuits and returns the payload unchanged with **no apply-result artifact built at all** (not merely a present-but-inert one) — the smoke tests assert the key's absence, not a null/false value.

### Full blocked-reason taxonomy (code-derived; the retired MVP-43 doc named only 4 conditions in prose and is confirmed incomplete)

Apply-tier (evaluated only once `apply_enabled=True`):

```text
dry_run_only                        - dry_run_only is True
preflight_missing                   - preflight artifact absent or not a mapping
injection_plan_missing              - preflight.injection_plan_present is not True
assembled_block_missing             - preflight.input_assembled_block_present is not True (independent re-check)
no_short_term_candidates            - preflight.input_short_term_candidate_count <= 0
preflight_not_content_free          - preflight.content_free is not True
messages_not_list                   - payload["messages"] is not a list
latest_user_message_not_found       - no message with role == "user" found scanning from the end
inserted_content_empty              - the rendered content-free summary came out empty
token_budget_exceeded                - token_budget <= 0, or estimated tokens exceed it
payload_mutation_disabled           - appended whenever any of the above fired and dry_run_only or not apply_enabled
messages_contain_non_object_items   - late-stage-only: replaces the whole blocked_reasons list when filtering non-Mapping
                                       items would change original_message_count; applied=False
```

Preflight-tier (gates what `injection_plan_present`/`content_free` are for the apply tier to re-check; see Stage 3): `assembly_missing`, `dry_run_only`, `assembled_block_missing`, `no_short_term_candidates`, and an unconditional `payload_mutation_disabled`.

### Insertion mechanics

- Insertion point: immediately before the last message with `role == "user"`, found by scanning the messages list in reverse (`_relayctx_before_latest_user_index`) — "latest user" means latest by list position, not by any timestamp.
- Inserted message: exactly one `{"role": "system", "content": <content-free summary>}` message. The summary contains only fixed boilerplate plus the five non-negative candidate counts (`temporary_fact_count`, `temporary_preference_count`, `instruction_count`, `override_count`, `contradiction_count`) carried through from Stage 3; it never contains raw message text, snippet bodies, or image URLs.
- Payload copy discipline: the caller's original payload and message list are deep-copied before any mutation; the caller's original objects are never mutated in place.
- Applies identically regardless of route mode (`pass_through` or `memory_light`).

### Apply-result schema (`relayctx_short_term_runtime_injection_apply_result.v0`)

Fields include `enabled`, `dry_run_only`, `attempted`, `applied`, `source` (`"relayctx_short_term_runtime_injection_preflight"`), `preflight_present`, `injection_plan_present`, `insertion_point`, `inserted_message_role`, `inserted_chars`, `estimated_inserted_tokens`, `original_message_count`, `forwarded_message_count`, `apply_allowed`/`apply_attempted` (mirror `applied`/`attempted`), `backend_payload_mutation_allowed`/`backend_payload_mutation_applied` (mirror `applied`), and `blocked_reasons`. Four fields are hardcoded regardless of input and are the code-level proof of this stage's non-goals: `response_mutation_allowed: false`, `openwebui_message_mutation_allowed: false`, `persistence_allowed: false`, `restore_allowed: false`, `content_free: true`.

### Non-goals, verbatim from the retained pre-cutover source and still exactly current

```text
MVP-43 does not persist short-term CTX, restore cross-thread CTX, mutate
responses, alter OpenWebUI message history, or improve injection quality beyond
safe plumbing.
```

No code path in this stage touches the backend response, writes to any persistent store, or reads/writes cross-thread state; the entire function operates on the single request's payload and preflight artifact in scope.

## Current limitations

- Stage 2's token-budget hint is a fixed `400`-token constant, not config-driven, unlike Stage 4's real config-backed budget.
- The Stage 3 preflight smoke script (`scripts/relaylm_relayctx_short_term_runtime_injection_preflight_smoke.py`) is not wired into any CI workflow group; it must be run manually.
- The historical CTX-Repack ordering defect (apply once ran after truncation) predates the current fix and is recorded only as an operational caveat in [Project Status](../PROJECT_STATUS.md), not restated here as current behavior.

## Target RelayCTX working-state evolution (target only, not implemented by this chain)

[Context Packing Design](../architecture/context_packing_design.md) and [Context Compiler Contract](../contracts/context_compiler_contract.md#relayctx-working-state) describe a conceptual, not-yet-implemented "RelayCTX working state" and a "Target ContextBlock" shape (`block_id`, `block_type`, `stability_class`, `source_class`, `content`, `token_budget_hint`, `include_in_prefix_cache_target`). That target shape has not been reconciled with this chain's real, shipped field names (`assembled_block_type`, `assembled_block_source`, `assembled_block_priority`, `assembled_block_token_budget_hint`). Nothing in this contract implements or requires that target shape; the field names in this contract are the current, implemented ones and take precedence over the target sketch for any question about current behavior.

## Non-authority

This contract does not grant, and no stage in this chain implements, any of: short-term CTX persistence, cross-thread restore, response mutation, or OpenWebUI message deletion/compression/rewriting beyond the single Stage 4 system-message insertion. Repository-wide current implementation status remains owned by [Project Status](../PROJECT_STATUS.md).
