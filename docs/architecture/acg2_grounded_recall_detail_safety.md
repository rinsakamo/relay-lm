---
relaylm_doc_type: implementation_handoff
relaylm_authority: acg2_grounded_recall_detail_safety
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - Grounded Recall query-detail schema changes
  - unsupported-detail suppression changes
  - analyzer candidate governance changes
relaylm_not_authoritative_for:
  - current implemented runtime status
  - full RelayMEM retrieval policy
  - Character Workspace implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - analyzer_candidate_governance.md
  - acg1_analyzer_candidate_governance_contract.md
  - e1r4_retrieval_response_grounding.md
  - project_execution_plan.md
---
# ACG-2 Grounded Recall Detail Safety

Last reviewed: 2026-07-03 JST

## Purpose

ACG-2 moves request-side remembered-detail detection for Grounded Recall behind a governed Query Detail Analyzer artifact.

The goal is to keep multilingual free-text interpretation in one bounded analyzer producer and let Grounded Recall consume fixed English enum values rather than owning scattered keyword semantics.

## Implemented boundary

Implemented files:

```text
relaylm/query_detail_analyzer.py
relaylm/relaymem_grounded_recall_response.py
scripts/relaylm_acg2_query_detail_analyzer_smoke.py
scripts/relaylm_e1r4_grounded_recall_response_smoke.py
```

The Query Detail Analyzer emits a content-free artifact with fixed English detail values.

```text
schema_version
analyzer_kind = query_detail_candidate
source
source_language
requested_detail_types
unsupported_detail_risk
confidence
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
content_free
reason_ids
validation_errors
```

Supported detail enum values:

```text
date_or_time
person_or_name
quantity
relationship
cause_or_reason
preference
location
identity
unknown
```

## Governance behavior

Existing regex detection remains as a bounded `fallback_regex` candidate. It is non-authoritative, restrictive-only, and can only strengthen suppression. It cannot open permissive recall behavior.

Malformed analyzer candidates, unknown enum values, missing required detail output, or analyzer disagreement fail closed. When fallback detection and a structured candidate disagree, Grounded Recall uses the union of requested detail types when doing so increases suppression.

The ACG-1 governance helpers remain the authority gate. Even if an analyzer candidate claims high confidence or broader authority, Query Detail Analyzer normalization refuses to open runtime policy from non-permitted sources.

## Grounded Recall integration

Grounded Recall consumes `requested_detail_types` request-side while building the backend-bound grounded recall context. It does not perform post-hoc visible response rewriting.

Unsupported detail suppression now covers:

```text
dates / times
names / people
quantities
relationships
causes / reasons
preferences
locations
identities
unknown malformed detail requests
```

If retrieved evidence does not support a requested detail, the result remains `unsupported_detail_suppressed` under the suppress policy.

## Public diagnostics

Public diagnostics expose only content-free status and count fields, including analyzer source class, fixed enum values, unsupported-risk booleans, and validation reason IDs.

Public diagnostics must not include:

```text
raw user text
assistant text
memory text
protected source bodies
free-form rationale
regex match bodies
filesystem paths
queue payloads
```

Runtime-private backend context may still include eligible evidence for model grounding, but `to_log_dict()` and analyzer public projections remain content-free.

## Non-goals

ACG-2 does not implement:

```text
LLM classifier requirement
RelayMEM retrieval rewrite
post-hoc visible response rewriting
memory mutation authority
worker / scheduler behavior
SCN scene-wiki classifier
Character Workspace parser / compiler / UI
```

## Validation

Expected validation commands:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_analyzer_governance_smoke.py
PYTHONPATH=. python scripts/relaylm_acg2_query_detail_analyzer_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

The ACG-2 smoke covers English and Japanese detail queries, malformed/unknown analyzer output, fallback-regex authority limits, LLM-candidate authority limits, missing analyzer output preserving legacy suppression, content-free diagnostics, location/identity fail-closed regressions, and request-side Grounded Recall integration.
