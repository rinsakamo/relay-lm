---
relaylm_doc_type: architecture_report
relaylm_authority: acg4_reference_intent_analyzer_contract
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - Reference/Intent Analyzer schema changes
  - RelayREF or RelayINT reference marker ownership changes
  - analyzer candidate governance authority changes
relaylm_not_authoritative_for:
  - ACG-2 Grounded Recall detail analyzer status
  - ACG-3 RelayMEM retrieval query normalization status
  - ACG-5 RelayEMO scene ownership cleanup
  - ACG-6 SCN scene-wiki classifier implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - analyzer_candidate_governance.md
  - project_execution_plan.md
  - relayint_mvp_design.md
  - relayref_relayslp_mvp_design.md
---
# ACG-4 Reference/Intent Analyzer Consolidation

Last reviewed: 2026-07-03 JST

## Purpose

ACG-4 consolidates unresolved-reference, continuation, prior-memory-request, and closely related intent marker detection behind a shared Reference/Intent Analyzer candidate artifact.

RelayREF and RelayINT no longer own independent free-text marker dictionaries for this boundary. They consume the shared analyzer output and keep their existing public diagnostics content-free.

## Implemented boundary

```text
user text / messages
  -> relaylm.reference_intent_analyzer.analyze_reference_intent()
  -> ACG-1 governed reference_intent_candidate
  -> RelayREF unresolved-reference mode selection
  -> RelayINT prior-memory / continuation / ambiguity classification
```

The analyzer emits fixed English schema values for:

```text
reference_kind:
  none
  unresolved_deictic
  prior_turn_reference
  prior_memory_reference
  ambiguous_choice
  context_repair_request
  unknown

intent_kinds:
  continuation
  clarification_request
  prior_memory_request
  correction_request
  review_request
  implementation_request
  unknown
```

Marker detection remains deterministic and fallback-only. Japanese and English marker coverage from the previous RelayREF and RelayINT paths is preserved at minimum, including unresolved references such as `それ`, `これ`, `あれ`, `さっき`, `どっち`, `どれ`, English references such as `which one`, `what was that`, `what were we`, prior-memory markers such as `前に話した`, `覚えてる`, `思い出して`, `前回`, `previous`, `remember`, and continuation markers such as `続き`, `その方向`, `それで`, `continue`.

## Governance and authority

The Reference/Intent Analyzer uses the ACG-1 analyzer governance helpers rather than reimplementing source authority locally.

Locale marker and fallback-regex sources are non-authoritative. They may recommend clarification, reflection, or restrictive handling, but they cannot open broad retrieval, memory update, mutation authority, output rewrite, or permissive runtime policy by themselves.

Expected marker-source authority:

```text
source_authoritative = false
restrictive_only = true
policy_authority = none | restrictive
runtime_policy_open_allowed = false
```

Unknown enum values, malformed analyzer artifacts, low confidence, and conflicting signals fail closed. The safe outcome is clarification or restrictive-only handling, never broad retrieval or memory mutation.

## Public diagnostics

Public projections stay content-free. They may expose fixed enum values, counts, boolean flags, confidence buckets, reason IDs, validation error IDs, and governance summaries. They must not expose raw user text, assistant text, matched marker bodies from private inputs, free-form rationale, memory text, protected source bodies, paths, queue payloads, or private context values.

## Non-goals

ACG-4 does not implement:

- a full LLM intent classifier;
- Grounded Recall detail migration from ACG-2 unless already merged and compatibility is required;
- RelayMEM retrieval query normalization from ACG-3 unless already merged and compatibility is required;
- RelayEMO scene cleanup;
- SCN scene-wiki behavior;
- broad retrieval or memory mutation authority from marker detection.
