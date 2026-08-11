---
relaylm_doc_type: implementation_contract
relaylm_authority: relayint_quick_clarification_runtime_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: contracts
relaylm_update_trigger:
  - RelayINT fast-path, preflight, or apply-plan schema changes
  - quick-clarification gate or blocked-reason changes
  - actual user-visible apply is implemented
relaylm_not_authoritative_for:
  - repository-wide current RelayINT/RelayMEM component boundary and target v1 intent contract
  - the PM-D6 RelayINT-native-artifact / RelayREF supersession boundary
  - PipelineNodeResult shape or the full current pipeline node-name list
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayINT Quick-Clarification Runtime Contract

## Purpose

RelayINT's quick-clarification chain is a three-stage, default-off, content-free, plan-only diagnostics path: fast-path dry-run -> quick-clarification preflight -> quick-clarification apply plan. All three stages run as part of `relaylm/relayint.py`'s request-local processing. Each stage returns `None` while its own flag is disabled. Stage 2 additionally returns `None` when its upstream (Stage 1) artifact is missing. Stage 3 does **not** return `None` for a missing upstream (Stage 2) artifact — when Stage 3 is itself enabled, it always returns a plan artifact, one that always carries `apply_allowed: False` today regardless of any upstream state. See "Enablement and artifact presence" below for the exact per-stage distinction.

This document is the current-code-derived canonical authority for the chain's schemas, config owners, artifact dependency order, candidate-action/clarification-type/blocked-reason taxonomies, and content-free/no-side-effect boundaries. It replaces three separate MVP milestone summaries (MVP-45 through MVP-47), which are retained only as frozen historical evidence under `docs/evidence/implementation/`.

This document separates **current implemented plan-only behavior** from **target actual user-visible apply behavior** (Phase 6), which is target-only design direction tracked in [RelayINT MVP Design](../architecture/relayint_mvp_design.md) and not implemented by this chain.

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md).

## Not the same artifact as the PM-D6 native intent artifact

RelayINT owns **two independent artifacts** that must not be confused:

1. `relayint_intent_artifact` (schema `relayint.intent.v1`), the always-computed, PM-D6-native reference/intent artifact built by `build_relayint_reference_intent_artifact()`. It is not gated by a feature flag and is not part of this chain. Its current authority and its supersession of the historical RelayREF-shaped compatibility wrapper are owned by [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md).
2. The three default-off diagnostics artifacts this contract owns: `relayint_fast_path_dry_run.v0`, `relayint_quick_clarification_preflight.v0`, and `relayint_quick_clarification_apply_plan.v0`.

The two artifacts share the same underlying reference/continuation/prior-memory-request detection, both consumed from the ACG-4 shared analyzer (see Stage 1 below), but they are built by different functions, gated differently, and serve different consumers.

## Enablement and artifact presence

Stage 2 and Stage 3 have **different** missing-upstream-input behavior; do not describe them identically.

```text
Stage 1 disabled
  -> Stage 1 artifact is None

Stage 2 disabled, OR Stage 1 artifact missing/not a Mapping
  -> Stage 2 artifact is None (no missing-input blocked artifact is produced)

Stage 3 disabled
  -> Stage 3 artifact is None

Stage 3 enabled but Stage 2 artifact missing
  -> Stage 3 artifact IS produced, with "preflight_missing" in apply_block_reasons
     (apply_allowed is still False, but for the additional, unconditional
     "phase4_plan_only" reason as well as "preflight_missing")
```

Concretely:

- Stage 1 (`build_relayint_fast_path_dry_run()`) returns `None` unless `relayint_fast_path_dry_run_enabled` is `True`.
- Stage 2 (`build_relayint_quick_clarification_preflight()`) returns `None` immediately when `not enabled or not isinstance(relayint_fast_path_dry_run, Mapping)` — a single combined guard clause. A missing or malformed Stage 1 artifact never produces a Stage 2 artifact with a missing-input reason; it produces no artifact at all.
- Stage 3 (`build_relayint_quick_clarification_apply_plan()`) returns `None` only when `relayint_quick_clarification_apply_enabled` is `False`. When enabled, it always builds and returns an artifact object, even if the Stage 2 preflight artifact is absent — in that case `preflight_present` is `False` and `"preflight_missing"` is appended to `apply_block_reasons`. Its `apply_allowed` is unconditionally `False` today regardless of upstream input state (see Stage 3).

Enabling a later stage without its predecessor therefore never synthesizes a missing predecessor artifact; the two stages simply differ in whether "missing predecessor" means "no artifact" (Stage 2) or "an artifact recording a blocked reason" (Stage 3).

## Stage 1: Fast-path dry-run

Producer: `build_relayint_fast_path_dry_run()` in `relaylm/relayint.py`. Config owners: `relayint_fast_path_dry_run_enabled` (default `False`), `relayint_fast_path_high_confidence_threshold` (default `0.80`), `relayint_fast_path_low_confidence_threshold` (default `0.55`) — all in `relaylm/config.py`.

- Schema version: `relayint_fast_path_dry_run.v0`.
- Reference/continuation/prior-memory-request detection is delegated to the shared, ACG-4-consolidated `relaylm.reference_intent_analyzer.analyze_reference_intent()` (`docs/architecture/acg4_reference_intent_analyzer.md`, `relaylm_status: current`); this stage no longer owns an independent local marker dictionary. Detection remains fully heuristic (no LLM call).
- Exact candidate actions (`relaylm/relayint.py:18-23`, `_candidate_action()`):

```text
continue_without_clarification
ask_clarification
current_context_only
recall_then_answer_candidate
```

- Confidence bucket: `high` / `medium` / `low`, using the two threshold config fields.
- Content-free fields only: booleans, enums, counts, and character counts of the latest user message — never raw text, image URLs, or candidate bodies.
- Safety literals, hardcoded `True`/`False`: `content_free: true`, `llm_called: false`, `mem_lookup_executed: false`, `backend_payload_mutation_allowed: false`, `response_mutation_allowed: false`.
- Consumers: Stage 2 of this chain (its only current downstream diagnostics consumer); `relaylm/diagnostics_builder.py`, `relaylm/trace_runtime.py`, and `relaylm/audit_projection.py` project it into diagnostics/trace/audit output. It is not consumed by `relaylm/retrieval/runtime.py`, which instead consumes the separate PM-D6-native `relayint_intent_artifact` for unresolved-reference blocking. It does not feed `relaylm/pipeline_node_adapter.py`'s synthesized node results directly.

## Stage 2: Quick-clarification preflight

Producer: `build_relayint_quick_clarification_preflight()` in `relaylm/relayint.py`. Config owners: `relayint_quick_clarification_preflight_enabled` (default `False`), `relayint_quick_clarification_dry_run_only` (default `True`).

- Schema version: `relayint_quick_clarification_preflight.v0`.
- Sole input artifact: Stage 1's `relayint_fast_path_dry_run`. Optional secondary input: a RelaySCN scene-policy artifact, used only for the scene gate below.
- Returns `None` (not a blocked artifact) when disabled or when the Stage 1 artifact is missing/not a `Mapping` — see "Enablement and artifact presence" above.
- `preflight_applicable` is `True` only when Stage 1's `candidate_action == "ask_clarification"` and the scene gate (below) allows it.
- `clarification_type` enum (`_quick_clarification_type()`): `none`, `prior_memory_reentry`, `reference_confirmation`, `open_clarification`.
- `candidate_label_kinds` enum members (`_quick_clarification_candidate_label_kinds()`): subset of `topic_anchor`, `referable_item`, `prior_memory`, or `["unknown"]` when applicable but unclassified.
- Scene gate (`_quick_clarification_scene_gate()`) block reasons: `scene_type_is_recovery`, `recovery_mode_enabled`, `user_confirmation_required`. `quick_clarification_allowed` is `True` only when none apply.
- `suggested_response_mode`: `quick_clarification_candidate` or `no_quick_clarification`.
- Content-free and diagnostics-only: no LLM call, no MEM lookup, no backend payload mutation, no response mutation, no user-visible apply (`user_visible_apply_allowed: false` always).
- Consumers: Stage 3 of this chain; `relaylm/trace_runtime.py` and `relaylm/audit_projection.py` for tracing.

## Stage 3: Quick-clarification apply plan

Producer: `build_relayint_quick_clarification_apply_plan()` in `relaylm/relayint.py`. Config owners: `relayint_quick_clarification_apply_enabled` (default `False`), `relayint_quick_clarification_apply_dry_run_only` (default `True`), `relayint_quick_clarification_response_max_chars` (default `120`).

- Schema version: `relayint_quick_clarification_apply_plan.v0`.
- **Artifact dependency** (the one upstream artifact this stage consumes): Stage 2's `relayint_quick_clarification_preflight.v0`.
- **Runtime inputs** (broader than the artifact dependency): the Stage 2 preflight artifact; a request compatibility gate (`request_compatibility_gate`) derived from the current backend-bound request payload, not from any upstream artifact; the request's streaming flag (`stream_enabled`); `response_max_chars`; and the stage's own `enabled`/`dry_run_only` configuration. The request compatibility gate is normally produced by calling `build_relayint_request_compatibility_gate()` against the live payload at the call site; if the caller passes no gate, this stage builds one from an empty payload itself, which is never compatible-by-default in a way that changes today's outcome (`apply_allowed` is forced `False` regardless — see below).
- `apply_allowed` is computed from `apply_block_reasons` being empty, but **`apply_block_reasons` always includes `phase4_plan_only`**, appended unconditionally as the last step before returning — so `apply_allowed` is currently always `False`, for every request, regardless of every other gate's outcome. `response_short_circuit_allowed` and `short_circuit_applied` are hardcoded `False`.

### Complete apply-plan block-reason vocabulary (29 distinct names)

This is the full union of every reason string reachable through this stage, combining reasons this stage adds directly, reasons it copies in from the Stage-2-sourced scene gate, and reasons it copies in from the request compatibility gate. It is the complete reachable vocabulary, not the set that appears in any single call — most requests trigger only a handful of these at once.

Apply-plan-direct and scene-gate-expanded reasons (11):

```text
preflight_missing              - Stage 2 artifact absent (preflight_present is False)
preflight_not_applicable       - Stage 2 preflight_applicable is not True
scene_gate_blocked             - Stage 2 scene_gate.quick_clarification_allowed is not True
scene_type_is_recovery         - expanded from Stage 2's scene_gate.block_reasons
recovery_mode_enabled          - expanded from Stage 2's scene_gate.block_reasons
user_confirmation_required     - expanded from Stage 2's scene_gate.block_reasons
dry_run_only                   - apply_dry_run_only is True
streaming_not_supported        - stream_enabled is True
response_template_missing      - no template resolves for the clarification_type
response_max_chars_exceeded    - resolved candidate template exceeds response_max_chars
phase4_plan_only               - always appended unconditionally; forces apply_allowed = False
```

Request-compatibility-gate-expanded reasons (18, see below): `response_format_requested`, `tools_requested`, `tool_choice_requested`, `functions_requested`, `function_call_requested`, `multiple_choices_requested`, `unsupported_n_value`, `logprobs_requested`, `top_logprobs_requested`, `stop_sequence_requested`, `unsupported_token_limit`, `token_limit_requested`, `max_completion_tokens_too_small`, `max_tokens_too_small`, `unsupported_modalities_value`, `audio_modality_requested`, `non_text_modality_requested`, `audio_options_requested`.

11 + 18 = **29** distinct reachable reason names.

### Request compatibility gate: exact 18-name vocabulary

`build_relayint_request_compatibility_gate()` in `relaylm/relayint.py` evaluates the raw backend-bound payload. Its full reachable `block_reasons` vocabulary is exactly these 18 distinct names — each is a separate reason string; none of the pairs below collapse into one name in code:

```text
response_format_requested          - "response_format" key present and not None
tools_requested                    - "tools" is a non-empty list
tool_choice_requested               - "tool_choice" present and not "none"
functions_requested                - "functions" is a non-empty list
function_call_requested            - "function_call" present and not "none"
multiple_choices_requested         - "n" is numeric and > 1
unsupported_n_value                - "n" is a bool, or numeric and <= 0, or a non-numeric type
logprobs_requested                 - "logprobs" is True
top_logprobs_requested             - "top_logprobs" key present and not None
stop_sequence_requested            - "stop" key present and not None
unsupported_token_limit            - "max_completion_tokens" or "max_tokens" present but is a
                                      bool, non-numeric, or <= 0
token_limit_requested              - "max_completion_tokens" or "max_tokens" present and a
                                      valid positive number (always added alongside the
                                      too-small reason below when both apply)
max_completion_tokens_too_small    - "max_completion_tokens" is valid but below the response
                                      token floor
max_tokens_too_small               - "max_tokens" is valid but below the response token floor
unsupported_modalities_value       - "modalities" present but not a non-empty list of strings
audio_modality_requested           - "modalities" contains "audio"
non_text_modality_requested        - "modalities" contains a non-"text", non-"audio" entry
audio_options_requested            - "audio" key present and not None
```

`token_limit_requested` is easy to miss: it is added whenever `max_completion_tokens` or `max_tokens` is present and numerically valid, independent of whether it is also too small — a valid-but-not-too-small token limit still adds `token_limit_requested` alone (which alone makes `compatible: False`), while a too-small one adds both `token_limit_requested` and the corresponding `*_too_small` reason.

- Response template metadata is computed in two distinct places and must not be conflated:
  - **Candidate metadata**, computed before any block-reason evaluation, purely from `clarification_type`: `generated_response_kind` (`generic_prior_memory_reentry`, `generic_reference_clarification`, `generic_open_clarification`, or `none`), `response_template_id` (`{kind}.ja.v0` or `none`), `response_chars` (a fixed count per template — 25 for the prior-memory-reentry template, 19 for the other two, never computed from live text). These candidate values are used only internally, to decide `response_template_missing`/`response_max_chars_exceeded`, and are never exposed directly.
  - **Final artifact values**, exposed in the returned dict, are gated by `apply_allowed`: `"generated_response_kind": generated_response_kind if apply_allowed else "none"`, `"response_template_id": response_template_id if apply_allowed else "none"`, `"response_chars": response_chars if apply_allowed else 0`. Because `apply_allowed` is always `False` today (see above), **the artifact's actual returned values are always `"none"`, `"none"`, and `0`** — never the 25/19-character candidate counts — regardless of what `clarification_type` the preflight reported. Do not describe the returned artifact as containing the candidate template metadata; it does not, today.
- Backend forwarding, payload, and response ownership are unaffected: `relaylm/managed_chat_runtime.py` forwards the payload to the backend unconditionally; nothing reads this artifact to skip or alter that call. `backend_payload_mutation_allowed`, `backend_payload_mutation_applied`, `response_mutation_allowed`, and `user_visible_apply_allowed` are hardcoded `False`.
- No LLM call, no MEM lookup, no persistence: `llm_called: false`, `mem_lookup_executed: false` are hardcoded.

## Actual user-visible apply (target only, not implemented by this chain)

As of this cutover, no phase beyond MVP-47 has shipped actual user-visible quick-clarification apply. `apply_block_reasons` always includes `phase4_plan_only`; no runtime code path reads `apply_allowed` to change request handling. [RelayINT MVP Design](../architecture/relayint_mvp_design.md) records this as a target "Phase 6" route requiring compatibility/active-transaction gates, RelaySCN scene/formality/recovery gates, RelayRUN short-circuit/checkpoint routing, and the normal output safety boundary — none of which this chain implements. Treat any future claim that actual apply exists as requiring independent code verification, not this contract or the retired MVP-47 text.

## Superseded RelayREF history

MVP-45 through MVP-47 predate PM-D6. None of the three stages in this chain ever depended on the historical RelayREF-shaped compatibility wrapper (`relayref_artifact`, `build_relayref_dry_run_artifact()`); that wrapper is unrelated to this chain and its supersession is owned entirely by [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md). This contract does not restate or duplicate PM-D6's boundary.

## Non-authority

This contract does not grant, and no stage in this chain implements, actual user-visible clarification text generation, backend-forward short-circuiting, response mutation, MEM lookup execution, LLM calls, or short-term CTX/RelayINT state persistence. It is not authoritative for the PM-D6-native `relayint_intent_artifact` / `relayint.intent.v1` boundary, for `PipelineNodeResult` shape or the current pipeline node-name list (see [PipelineNodeResult Contract](pipeline_node_result_contract.md)), or for the repository-wide RelayINT target component boundary (see [RelayINT MVP Design](../architecture/relayint_mvp_design.md)). Repository-wide current implementation status remains owned by [Project Status](../PROJECT_STATUS.md).
