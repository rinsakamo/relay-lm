# Client Instruction Authority Contract

## Purpose

This document defines how RelayLM treats client-supplied `system` and `developer` messages when building persona-aware backend context.

It complements:

- `client_history_authority_contract.md`
- `pipeline_responsibility_design.md`
- `context_packing_design.md`
- `../contracts/context_compiler_contract.md`
- `../relaysoul/relaysoul_design.md`

The core rule is:

```text
An existing RelaySOUL persona source is authoritative.
A client system prompt may bootstrap a missing persona source,
but it must not silently override an existing one.
```

## Authority states

### Existing SOUL

When an approved `SOUL.md` or equivalent RelaySOUL revision exists:

- RelayLM uses it as the authoritative persona core.
- Client `system` and `developer` messages do not overwrite the stable prefix.
- They may be inspected only as explicitly allowed low-trust transient hints.
- Durable changes must go through RelaySOUL proposal, validation, revision, and rollback.

### Missing SOUL on the first managed request

When a RelayLM-managed persona route has no usable SOUL source, the first valid client system prompt may be used as a bootstrap seed.

```text
SOUL missing
  + first valid client system prompt
  + bootstrap policy enabled

  -> preserve as bootstrap evidence
  -> use a bounded temporary persona block for the first request
  -> create an initial RelaySOUL persona-source revision
  -> validate file boundaries and compile budget
  -> activate the generated revision
  -> use RelaySOUL on later turns
```

The bootstrap prompt is creation evidence, not durable authority by itself.

## First-turn behavior

The first request should not lose the frontend character merely because RelayLM has not created its own persona source yet.

RelayLM may therefore compile a bounded `incoming_system_prompt` block for the first request while bootstrap is pending.

Constraints:

- only the first eligible prompt for the route/persona scope is used,
- the block remains dynamic and outside the stable prefix hash,
- it is token-budgeted,
- diagnostics mark it as bootstrap evidence,
- it is not copied verbatim into persistent persona files,
- it is never accepted as a replacement when an approved SOUL already exists.

## Persona-source creation

RelaySOUL should classify the bootstrap prompt into the existing file boundaries:

```text
SOUL.md
  durable identity, values, worldview, invariants

OUTPUT_POLICY.md
  tone, verbosity, response shape, TTS-friendly expression

RELATIONSHIP_ANCHOR.md
  stable relationship expectations

SCENE_STATE.md
  temporary roleplay, setting, event, or situation
```

The prompt must not be dumped wholesale into `SOUL.md`.

The bootstrap process should always produce a bounded SOUL core and may create the other persona-source files when the source contains material that belongs there.

## Bootstrap activation authority

Bootstrap must be explicitly enabled by route or operator policy.

Recommended policy:

```text
client_instruction_policy = relay_soul_authoritative
soul_bootstrap_policy = from_first_client_system
```

This explicit configuration acts as operator authorization for initial persona creation.

A stricter deployment may use:

```text
soul_bootstrap_policy = proposal_only
```

In that mode the first prompt may shape the current request, but the generated persona revision remains a candidate until approved.

## Later client prompts

After RelaySOUL exists:

- repeated frontend persona prompts are not authoritative backend context,
- identical prompts may be ignored with diagnostics,
- materially different prompts may become transient evidence,
- an explicit character-change request may open RelaySOUL `character_creation` or `calibration`,
- no later prompt may directly mutate the active SOUL revision.

## Route behavior

### `pass_through`

```text
client owns instructions and history
RelayLM preserves client messages
```

### RelayLM-managed route with SOUL

```text
RelaySOUL owns persona authority
client instructions are non-authoritative
```

### RelayLM-managed route without SOUL

```text
first client system prompt may bootstrap persona creation
only when explicitly enabled
```

## Interaction with client history authority

Client history and client instruction authority are separate:

```text
Client History Authority:
  Which prior messages may reach the backend?

Client Instruction Authority:
  Which instruction source defines persona and policy?
```

The first bootstrap system prompt is a narrow exception to ordinary history exclusion. It is extracted specifically as bootstrap evidence before prior history is removed. The exception closes once a RelaySOUL revision exists.

## Diagnostics

Suggested diagnostics:

```json
{
  "client_instruction_policy": "relay_soul_authoritative",
  "soul_source_state": "missing",
  "client_system_prompt_present": true,
  "bootstrap_policy": "from_first_client_system",
  "bootstrap_eligible": true,
  "bootstrap_source_used_for_current_turn": true,
  "bootstrap_revision_created": false,
  "bootstrap_revision_activated": false,
  "client_instruction_overrode_existing_soul": false
}
```

Diagnostics should not copy the raw system prompt into content-free runtime artifacts.

## Failure behavior

### Existing SOUL conflicts with client prompt

```text
keep RelaySOUL
exclude the client prompt from persona authority
record conflict diagnostics
```

### Bootstrap generation or validation fails

```text
never activate a malformed candidate
never treat the raw prompt as durable SOUL
keep only the bounded temporary first-turn block when safe
route later turns to setup/recovery until a valid persona source exists
```

If both SOUL and a usable bootstrap prompt are missing, RelayLM must not invent a durable character identity from unrelated user history. It should enter explicit setup/recovery handling unless a route allows a minimal neutral bootstrap.

## Required smoke coverage

1. Existing SOUL wins over a conflicting client system prompt.
2. Missing SOUL plus a valid first prompt produces bootstrap diagnostics.
3. The first request retains temporary persona behavior while bootstrap is pending.
4. Bootstrap content is classified instead of copied wholesale into SOUL.
5. Later turns use the generated RelaySOUL revision.
6. Later client prompts do not silently mutate SOUL.
7. Missing SOUL and missing prompt fails closed or enters explicit setup.
8. Pass-through mode remains unchanged.
9. Bootstrap diagnostics remain content-free.
10. Failed candidates are never activated.

## Final boundary

```text
Use the SOUL when it exists.
When it does not exist, the first client system prompt may help create it.
After creation, RelaySOUL becomes the authority.
```
