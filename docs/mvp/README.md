# RelayLM MVP Summaries

This directory is the index for RelayLM MVP milestone summaries.

The MVP summary files are being consolidated out of the top-level `docs/` directory. During the transition, some entries may still point to legacy `../mvp*_summary.md` files until they are physically moved in a follow-up docs-only cleanup.

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

## Earlier milestone summaries

These older summaries are kept indexed for discoverability while the documentation tree is being reorganized.

- [MVP-3](../mvp3_summary.md)
- [MVP-5](../mvp5_summary.md)
- [MVP-6](../mvp6_summary.md)
- [MVP-7](../mvp7_summary.md)
- [MVP-9](../mvp9_summary.md)
- [MVP-10](../mvp10_summary.md)
- [MVP-11](../mvp11_summary.md)
- [MVP-13](../mvp13_summary.md)
- [MVP-14](../mvp14_summary.md)
- [MVP-15](../mvp15_summary.md)
- [MVP-16](../mvp16_summary.md)
- [MVP-18](../mvp18_summary.md)
- [MVP-19](../mvp19_summary.md)
- [MVP-21](../mvp21_summary.md)
- [MVP-22](../mvp22_summary.md)
- [MVP-23](../mvp23_summary.md)
- [MVP-24](../mvp24_summary.md)
- [MVP-25](../mvp25_summary.md)
- [MVP-27](../mvp27_summary.md)
- [MVP-28](../mvp28_summary.md)
- [MVP-29](../mvp29_summary.md)
- [MVP-30](../mvp30_summary.md)
- [MVP-31](../mvp31_summary.md)
- [MVP-33](../mvp33_summary.md)

## MVP-2 split notes

MVP-2 has several focused notes rather than one summary file:

- [MVP-2: config profile resolution](../mvp2_config_profile_resolution.md)
- [MVP-2: memory_light apply](../mvp2_memory_light_apply.md)
- [MVP-2: profile file loading](../mvp2_profile_file_loading.md)
- [MVP-2: profile compile dry-run](../mvp2_profile_compile_dry_run.md)
- [MVP-2: incoming system fallback](../mvp2_incoming_system_fallback.md)

## Follow-up cleanup

A later docs-only PR should physically move the legacy files into this directory and update links, preferably in small batches:

1. Move current pipeline summaries first: MVP-40 through MVP-47.
2. Move earlier `mvp*_summary.md` files.
3. Move MVP-2 split notes if they still belong under the MVP index.
4. Remove legacy top-level `docs/mvp*` files after link checks pass.
