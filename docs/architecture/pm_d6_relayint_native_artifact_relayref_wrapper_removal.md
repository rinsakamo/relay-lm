---
relaylm_doc_type: implementation_handoff
relaylm_authority: pm_d6_relayint_native_artifact_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relayint
relaylm_update_trigger:
  - RelayINT reference or intent artifact schema changes
  - RelayREF compatibility wrapper behavior changes
  - RelayMEM unresolved-reference blocking changes
relaylm_not_authoritative_for:
  - repository-wide current status
  - roadmap sequencing
  - output-side RelayREF runtime design
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - current_target_migration_guide.md
  - analyzer_candidate_governance.md
  - acg4_reference_intent_analyzer.md
---
# PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal

Date: 2026-07-04 JST

## Purpose

PM-D6 removes the input-side RelayINT dependency on the historical RelayREF-shaped compatibility helper. RelayINT now owns a request-local reference/intent artifact instead of importing `build_relayref_dry_run_artifact()` from `relaylm.relayref`.

## Legacy wrapper

Before PM-D6, `build_relayint_reference_repair_dry_run()` called RelayREF and returned a `relayref.dry_run_artifact.v0` payload annotated with `relayint_alias` and `source_compat_module: relayref`. That made the input-side reference/intent stage look like RelayREF even though it was used as RelayINT runtime diagnostics.

## Native RelayINT artifact

The native builder is `build_relayint_reference_intent_artifact()` in `relaylm/relayint.py`. It emits:

- runtime-private schema: `relayint.intent.v1`
- request-local diagnostics only
- `llm_called: false`
- `mem_lookup_executed: false`
- `backend_payload_mutation_allowed: false`
- `response_mutation_allowed: false`
- `mem_query_allowed: false`

The deprecated function name `build_relayint_reference_repair_dry_run()` is retained only as a RelayINT-native entrypoint. It no longer imports RelayREF and no longer emits `relayref.dry_run_artifact.v0`, `relayint_alias`, or `source_compat_module`.

## Public projection

The nested projection schema is `relayint.projection.v1`. It is content-free and limited to fixed booleans, enum-like decisions, confidence bands, counts, and reason IDs. It must not expose raw user text, resolved reference text, memory text, scene body, relationship body, file paths, queue payloads, runtime-private IDs, or backend prompts.

## Retrieval interaction

RelayMEM Retrieval continues to block ambiguous or unresolved references from authorizing silent long-term recall. PM-D6 preserves the top-level `unresolved_reference_detected` signal on the native RelayINT artifact so existing retrieval blocking remains intact while the input-side artifact schema is no longer RelayREF-shaped.

A later cleanup can rename remaining compatibility-shaped local variables and function parameters in wide runtime plumbing. This document must not be read as RelayREF module deletion: RelayREF remains available for a possible future output-side observation/reflection layer.

## Non-goals

PM-D6 does not implement an output-side RelayREF runtime, full RelayINT LLM classification, memory mutation, SOUL mutation, worker/scheduler authority, quick-clarification visible apply, or unbounded retrieval.

## Validation

Recommended validation:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_acg4_reference_intent_analyzer_smoke.py
PYTHONPATH=. python scripts/relaylm_relayint_fast_path_dry_run_smoke.py
PYTHONPATH=. python scripts/relaylm_pm_d6_relayint_native_artifact_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_selection_dry_run_smoke.py
PYTHONPATH=. python scripts/relaylm_p0_pipeline_ordering_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```
