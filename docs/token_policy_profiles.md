# Token Policy Shadow Profile Settings

RelayLM exposes token policy as diagnostics/trace artifacts in shadow mode.

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

## Decision fields in diagnostics/trace

`token_policy_decision` includes the operator-facing fields below:

- `status`: policy-readiness status (`ready_within_budget`, `would_exceed_budget`, `missing_signal`, `invalid_signal`)
- `action`: shadow-only action hint (`none`, `shadow_only`, `would_fallback`)
- `policy_mode`: effective mode (`disabled` or `shadow`)
- `shadow_enabled`: effective boolean gate
- `shadow_source`: where the gate came from (`global` or `character`)
- `enforcement_enabled`: always `false` in current MVP scope

## Status reading quick guide

- `ready_within_budget`: dry-run had usable budget data and was within budget.
- `would_exceed_budget`: dry-run had usable budget data and exceeded budget.
- `missing_signal`: dry-run/assembly signal was absent or incomplete.
- `invalid_signal`: signal payload shape was invalid.

Even for `would_exceed_budget`, RelayLM does not enforce hard actions yet.

## `shadow_source` interpretation

- `global`: no character override was applied (global fallback path)
- `character`: character-level override decided the effective value

This is useful for mixed-character workloads to confirm per-character isolation.

## JSON examples

Global fallback (global false, character unset):

```json
{
  "token_policy_decision": {
    "status": "ready_within_budget",
    "action": "none",
    "policy_mode": "disabled",
    "shadow_enabled": false,
    "shadow_source": "global",
    "enforcement_enabled": false
  }
}
```

Character override (character true over global false):

```json
{
  "token_policy_decision": {
    "status": "ready_within_budget",
    "action": "shadow_only",
    "policy_mode": "shadow",
    "shadow_enabled": true,
    "shadow_source": "character",
    "enforcement_enabled": false
  }
}
```

Budget exceeded in shadow mode (diagnostics only):

```json
{
  "token_policy_decision": {
    "status": "would_exceed_budget",
    "action": "would_fallback",
    "policy_mode": "shadow",
    "shadow_enabled": true,
    "shadow_source": "global",
    "enforcement_enabled": false
  }
}
```

## Safety and scope

- token policy remains diagnostics/trace only
- forwarding payload/path is unchanged
- hard enforcement (`fallback`, `rejection`, `truncation`) is future work
- `enforcement_enabled` remains `false` in current MVP scope
