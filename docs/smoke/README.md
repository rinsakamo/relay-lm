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

This directory indexes manual smoke runbooks, recorded smoke results, troubleshooting guides, consolidated CI maintenance guidance, and local behavior evaluation documents.

Implementation evidence remains under `docs/evidence/implementation/`. Executable smoke scripts remain under `scripts/`.

## Consolidated CI maintenance

- [Consolidated smoke workflow maintenance](consolidated_workflow_maintenance.md) — current RelayMEM, Runtime, and UI workflow grouping, contract validation, and generated inventory procedure.
- [Scripts inventory summary](scripts_inventory.md) — latest audited summary and the authoritative generated-artifact regeneration path.

## OpenWebUI / LM Studio manual smoke

- [OpenWebUI + LM Studio manual smoke runbook](openwebui_lmstudio_manual_smoke.md)
- [Client history exclusion manual smoke](client_history_exclusion_manual_smoke.md)
- [RelayRUN recovery diagnostics manual smoke](relayrun_recovery_diagnostics_manual_smoke.md)
- [Manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md)
- [Manual smoke result: 2026-05-26](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)

## Setup checks and troubleshooting

- [OpenWebUI model preset/avatar checklist](openwebui_model_preset_checklist.md)
- [OpenWebUI route response differentiation checks](openwebui_response_differentiation_checks.md)
- [OpenWebUI + RelayLM + LM Studio troubleshooting](openwebui_lmstudio_troubleshooting.md)

## RelayMEM and local behavior evaluation

- [O1 manual one-round operations runbook](o1_manual_one_round_runbook.md) — lower-level compatibility/manual validation for one O1D1-style round; not O2/O3 service operation.
- [E2 value smoke runbook](e2_value_smoke_runbook.md)
- [RelayMEM runtime payload diff evaluation](relaymem_runtime_payload_eval.md)
- [RelayMEM local LLM evaluation guide](relaymem_local_llm_eval_guide.md)
- [RelayMEM local response comparison guide](relaymem_local_response_comparison.md)

## Placement rule

Create cross-cutting manual smoke, result, troubleshooting, consolidated CI maintenance, and local evaluation docs directly under `docs/smoke/`. Keep implementation evidence under `docs/evidence/implementation/`, architecture docs under `docs/architecture/`, contract docs under `docs/contracts/`, offline tooling docs under `docs/tools/`, and evaluation templates or run records under `docs/evaluation/`.
