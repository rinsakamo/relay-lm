# RelayLM MVP Summaries

This directory is the index for RelayLM MVP milestone summaries and MVP-focused implementation notes.

The MVP files are being consolidated out of the top-level `docs/` directory. During the transition, entries point to legacy `../mvp*` files until they are physically moved in a follow-up docs-only cleanup.

## Current pipeline milestones

### RelayCTX short-term context

- [MVP-40: RelayCTX short-term extraction dry-run](../mvp40_summary.md)
- [MVP-41: RelayCTX short-term block assembly dry-run](../mvp41_summary.md)
- [MVP-42: RelayCTX short-term runtime injection preflight](../mvp42_summary.md)
- [MVP-43: RelayCTX short-term runtime injection apply gate](../mvp43_summary.md)

### RelayINT

- [MVP-45: RelayINT Fast Path dry-run](../mvp45_summary.md)
- [MVP-46: RelayINT quick clarification preflight](../mvp46_summary.md)
- [MVP-47: RelayINT quick clarification apply plan](../mvp47_summary.md)

## MVP-0 and MVP-1

- [MVP-0: pass-through proxy](../mvp0_pass_through_proxy.md)
- [MVP-1: config and routing smoke](../mvp1_config_routing_smoke.md)
- [MVP-1: runtime diagnostics smoke](../mvp1_runtime_diagnostics_smoke.md)
- [MVP-1: API diagnostics smoke](../mvp1_api_diagnostics_smoke.md)
- [MVP-1 summary](../mvp1_summary.md)

## MVP-2 focused notes

MVP-2 has several focused notes rather than only one summary file:

- [MVP-2: context compiler contract](../mvp2_context_compiler_contract.md)
- [MVP-2: profile file loading](../mvp2_profile_file_loading.md)
- [MVP-2: config profile resolution](../mvp2_config_profile_resolution.md)
- [MVP-2: compiled system message](../mvp2_compiled_system_message.md)
- [MVP-2: incoming system fallback](../mvp2_incoming_system_fallback.md)
- [MVP-2: profile compile dry-run](../mvp2_profile_compile_dry_run.md)
- [MVP-2: dry-run diagnostics headers](../mvp2_dry_run_diagnostics_headers.md)
- [MVP-2: gated compile decision](../mvp2_gated_compile_decision.md)
- [MVP-2: memory-light apply helper](../mvp2_memory_light_apply.md)
- [MVP-2: runtime memory-light apply](../mvp2_runtime_memory_light_apply.md)
- [MVP-2: memory-light API smoke](../mvp2_memory_light_api_smoke.md)
- [MVP-2 summary](../mvp2_summary.md)

## Earlier milestone summaries

These older summaries are kept indexed for discoverability while the documentation tree is being reorganized.

- [MVP-3 summary](../mvp3_summary.md)
- [MVP-4 summary](../mvp4_summary.md)
- [MVP-5 summary](../mvp5_summary.md)
- [MVP-6 summary](../mvp6_summary.md)
- [MVP-7 summary](../mvp7_summary.md)
- [MVP-8 summary](../mvp8_summary.md)
- [MVP-9 summary](../mvp9_summary.md)
- [MVP-10 summary](../mvp10_summary.md)
- [MVP-11 summary](../mvp11_summary.md)
- [MVP-12 summary](../mvp12_summary.md)
- [MVP-13 summary](../mvp13_summary.md)
- [MVP-14 summary](../mvp14_summary.md)
- [MVP-15 summary](../mvp15_summary.md)
- [MVP-16 summary](../mvp16_summary.md)
- [MVP-17 summary](../mvp17_summary.md)
- [MVP-18 summary](../mvp18_summary.md)
- [MVP-19 summary](../mvp19_summary.md)
- [MVP-20 summary](../mvp20_summary.md)
- [MVP-21 summary](../mvp21_summary.md)
- [MVP-22 summary](../mvp22_summary.md)
- [MVP-23 summary](../mvp23_summary.md)
- [MVP-24 summary](../mvp24_summary.md)
- [MVP-25 summary](../mvp25_summary.md)
- [MVP-26 summary](../mvp26_summary.md)
- [MVP-27 summary](../mvp27_summary.md)
- [MVP-28 summary](../mvp28_summary.md)
- [MVP-29 summary](../mvp29_summary.md)
- [MVP-30 summary](../mvp30_summary.md)
- [MVP-31 summary](../mvp31_summary.md)
- [MVP-32 summary](../mvp32_summary.md)
- [MVP-33 summary](../mvp33_summary.md)
- [MVP-37 summary](../mvp37_summary.md)

## Follow-up cleanup

A later docs-only PR should physically move the legacy files into this directory and update links, preferably in small batches:

1. Move current pipeline summaries first: MVP-40 through MVP-47.
2. Move earlier `mvp*_summary.md` files.
3. Move MVP-0, MVP-1, and MVP-2 focused notes if they still belong under the MVP index.
4. Remove legacy top-level `docs/mvp*` files after link checks pass.
