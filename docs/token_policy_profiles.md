# Token Policy Shadow Profile Settings

RelayLM supports token policy in a diagnostics-first shadow mode.

## Global setting

Set the global default in `memory.token_policy_shadow_enabled`:

- `false`: default behavior (`policy_mode=disabled`)
- `true`: shadow behavior (`policy_mode=shadow`)

This controls diagnostics/trace outputs only. Runtime forwarding behavior is unchanged.

## Character override

Each character can override the global value with `characters.<id>.token_policy_shadow_enabled`:

- `true`: force shadow mode for that character
- `false`: force disabled mode for that character
- unset (`null`/omitted): fall back to global setting

## Effective source in diagnostics

`token_policy_decision.shadow_source` shows where the effective value came from:

- `character`: character override was applied
- `global`: global memory setting was applied

## Safety and scope

- token policy remains diagnostics/trace only
- forwarding payload/path is unchanged
- hard enforcement (`fallback`, `rejection`, `truncation`) is future work
- `enforcement_enabled` remains `false` in current MVP scope
