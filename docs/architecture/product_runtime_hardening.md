# Archived: Product Runtime Hardening

The early cross-cutting product/runtime planning source has been retired from the live documentation tree after its durable responsibilities were absorbed into current architecture, memory, integration, and product authorities. Its exact historical text remains recoverable from Git history.

Use these current documents instead:

- [Pipeline implementation plan](pipeline_implementation_plan.md) for current implementation status and sequencing
- [RelayLM System Overview](system-overview.md), [Pipeline Responsibilities](pipeline-responsibilities.md), and [Request / Response Pipeline](runtime/request-response-pipeline.md) for runtime layers, component boundaries, and modes
- [Runtime reliability and compatibility](runtime/reliability-and-compatibility.md) for compatibility-safe degradation and cross-cutting acceptance posture
- [Runtime operational observability](runtime/operational-observability.md) for typed content-free diagnostics and operational evidence
- [Local-first runtime privacy](privacy/local-first-runtime.md) for storage destination, telemetry, and namespace-isolation posture
- [AI character product principles](ai_character_product_principles.md) for product value and experience priorities
- [Context packing design](context_packing_design.md) for authority order and prompt layout
- [RelayMEM retrieval execution design](relaymem_retrieval_execution_design.md) and [RelayMEM SLP execution design](relaymem_slp_execution_design.md) for memory read/write lifecycle boundaries
- [Open-LLM-VTuber integration design](open_llm_vtuber_integration.md) for frontend/API integration

The superseded MVP roadmap, broad mode fallback ladder, and early implementation examples are historical context only and no longer define current implementation status or canonical runtime requirements.
