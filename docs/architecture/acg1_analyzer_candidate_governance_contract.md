---
relaylm_doc_type: architecture_contract
relaylm_authority: acg1_analyzer_candidate_governance_contract
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - analyzer candidate schema changes
  - analyzer source or authority enum changes
  - public diagnostic projection changes
  - content-free governance boundary changes
relaylm_not_authoritative_for:
  - full analyzer classifier implementation
  - SCN scene-wiki matching
  - RelayMEM retrieval rewrite
  - Grounded Recall detail migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - analyzer_candidate_governance.md
  - project_execution_plan.md
  - p0_relayrel_relayscn_relayemo_ordering_fix.md
---
# ACG-1 Analyzer Candidate Governance Contract

Last reviewed: 2026-07-03 JST

## Status

ACG-1 is current as the shared analyzer candidate governance contract/helper slice. The implementation lives in `relaylm/analyzer_governance.py`, with smoke coverage in `scripts/relaylm_analyzer_governance_smoke.py`.

This status does not imply that ACG-2 through ACG-6 are implemented. ACG-1 establishes the common schema, validation, authority, and content-free projection boundary that later analyzer producers must consume.

## Purpose

ACG-1 introduces the shared Analyzer Candidate Governance contract in `relaylm/analyzer_governance.py`.

The contract defines a minimal, English-only, schema-first artifact boundary for analyzer candidate outputs. It lets future Grounded Recall detail detection, retrieval query normalization, RelayREF / RelayINT reference intent detection, RelayEMO cleanup, and SCN scene-wiki classification share one candidate-vs-authority model.

## In scope

ACG-1 provides:

- fixed analyzer candidate schema keys;
- fixed English enum values and reason IDs;
- source-class normalization;
- fail-closed validation for malformed or unknown fields;
- helper functions for normalization, validation, authority checks, bounded runtime-open checks, and public projection;
- content-free public diagnostics;
- smoke coverage in `scripts/relaylm_analyzer_governance_smoke.py`.

The initial placeholder analyzer kinds are:

```text
query_detail_candidate
retrieval_query_candidate
reference_intent_candidate
affect_candidate
scene_policy_candidate
```

These are contract placeholders only. ACG-1 does not implement their full analyzers.

## Non-goals

ACG-1 does not implement:

- a large LLM classifier;
- SCN scene-wiki matching;
- Grounded Recall logic migration;
- RelayMEM retrieval rewrite;
- RelayEMO scene fallback restoration;
- request-path rewiring;
- broad runtime policy authority from heuristic or LLM candidate signals.

## Source authority model

The fixed source classes are:

```text
trusted_explicit
trusted_route
trusted_tool_signal
confirmed_user_action
heuristic
llm_candidate
locale_marker
fallback_regex
unknown
```

Trusted or confirmed sources may be represented as authoritative only when the caller explicitly sets `source_authoritative = true` and validation passes.

Heuristic, LLM candidate, locale marker, fallback regex, unknown, and malformed sources are non-authoritative. They may produce candidate labels and diagnostics, strengthen fail-closed safety restrictions, or remain restrictive-only. They must not open broad retrieval, memory update, SOUL mutation, output rewrite authority, scene-policy authority, or public diagnostics that contain raw user text.

## Public content-free projection

`content_free_projection(...)` emits only bounded fixed fields:

```text
schema_version
analyzer_kind
source_class
source_authoritative
policy_authority
restrictive_only
candidate_applied
confidence_bucket
stability_bucket
reason_ids
validation_error_ids
content_free
```

It does not expose raw user text, raw assistant text, free-form LLM rationale, unvalidated external signal bodies, filesystem paths, queue payload bodies, memory text, relationship markdown, scene markdown, or source markdown.

Unknown reason IDs and enum-like values are converted to fixed tokens such as `unknown_reason` or `unknown_enum_value` rather than being echoed.

## Validation behavior

Validation is fail-closed:

- unknown analyzer kind becomes `unknown` and disables authority;
- unknown source becomes `unknown`, disables authority, sets restrictive-only, and prevents candidate application;
- unknown policy authority becomes `none`;
- malformed confidence and stability become low bucket inputs;
- non-authoritative sources cannot open `bounded`, `broad`, `open`, `update`, `rewrite`, `mutation`, or `scene_policy` authority;
- public projection reports only validation error IDs, never free-form details.

## Validation commands

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_analyzer_governance_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

## Handoff

Future ACG slices should consume `relaylm.analyzer_governance` rather than minting separate natural-language heuristics as policy authorities. Candidate producers can add target-specific fields later, but public diagnostics must remain content-free and authority must stay with explicit gates or target contracts.
