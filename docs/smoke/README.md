---
relaylm_doc_type: documentation_index
relaylm_authority: smoke_and_validation_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: validation
relaylm_update_trigger:
  - smoke runbooks are added or removed
  - consolidated workflow maintenance changes
  - validation placement rules change
relaylm_not_authoritative_for:
  - repository-wide current runtime behavior
  - MVP dependency sequencing
  - exact runtime contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Smoke and Validation Docs

This directory indexes manual smoke runbooks, recorded smoke results, troubleshooting guides, local behavior evaluation documents, and other retained smoke-related records not yet separately cut over. Cross-cutting consolidated CI maintenance procedures are canonical under `docs/operations/`, not `docs/smoke/`; this index carries a cross-collection link to that authority for discoverability only.

Implementation evidence remains under `docs/evidence/implementation/`. Executable smoke scripts remain under `scripts/`.

## Consolidated CI maintenance (cross-collection link)

- [Consolidated smoke workflow maintenance](../operations/consolidated-smoke-workflow-maintenance.md) — canonical under `docs/operations/`; current RelayMEM, Runtime, and UI workflow grouping, contract validation, and generated inventory procedure. Indexed here only as a cross-collection pointer, not owned content.
- [Scripts inventory summary](scripts_inventory.md) — latest audited summary and the authoritative generated-artifact regeneration path; a distinct, unmoved `docs/smoke/` authority with its own lifecycle.

## O1 manual one-round validation (cross-collection link)

- [O1 manual one-round operations runbook](../operations/o1-manual-one-round.md) — canonical under `docs/operations/`; lower-level compatibility/manual validation for one O1D1-style round; not O2/O3 service operation. Indexed here only as a cross-collection pointer, not owned content.

## OpenWebUI / LM Studio manual smoke

- [OpenWebUI + LM Studio manual smoke runbook](../operations/openwebui-lmstudio-manual-smoke.md)
- [Client history exclusion manual smoke](../operations/client-history-exclusion-manual-smoke.md)
- [RelayRUN recovery diagnostics manual smoke](../operations/relayrun-recovery-diagnostics-manual-smoke.md)
- [Manual smoke results template](../templates/evaluation/openwebui-lmstudio-manual-smoke-results.md)
- [Manual smoke result: 2026-05-26](../evidence/evaluations/openwebui-lmstudio-manual-smoke-2026-05-26.md)

## Setup checks and troubleshooting

- [OpenWebUI model preset/avatar checklist](../operations/openwebui-model-preset-checklist.md)
- [OpenWebUI route response differentiation checks](../operations/openwebui-response-differentiation-checks.md)
- [OpenWebUI + RelayLM + LM Studio troubleshooting](../operations/openwebui-lmstudio-troubleshooting.md)

## RelayMEM and local behavior evaluation

- [Value smoke runbook](../operations/value-smoke-runbook.md)
- [RelayMEM runtime payload diff evaluation](../operations/relaymem-runtime-payload-evaluation.md)
- [RelayMEM local LLM evaluation guide](../operations/relaymem-local-llm-evaluation.md)
- [RelayMEM local response comparison guide](../operations/relaymem-local-response-comparison.md)

## Placement rule

Create cross-cutting manual smoke, result, troubleshooting, and local evaluation docs directly under `docs/smoke/`. Keep implementation evidence under `docs/evidence/implementation/`, architecture docs under `docs/architecture/`, contract docs under `docs/contracts/`, evaluation templates or run records under `docs/evaluation/`, and operator runbooks or cross-cutting CI maintenance procedures under `docs/operations/`.
