---
relaylm_doc_type: documentation_index
relaylm_authority: implementation_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - an implementation evidence record is added, moved, or retired
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contracts
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
---
# Implementation Evidence

This collection preserves bounded implementation and smoke evidence after its active design or operational authority has moved elsewhere. Commands and expectations inside exact source snapshots describe their historical boundary and are not automatically current instructions.

## Early MVP smoke records

- [MVP-1 API diagnostics smoke](mvp1_api_diagnostics_smoke.md)
- [MVP-1 config and routing smoke](mvp1_config_routing_smoke.md)
- [MVP-2 memory-light API smoke](mvp2_memory_light_api_smoke.md)
- [MVP-2 profile compile dry-run](mvp2_profile_compile_dry_run.md)
