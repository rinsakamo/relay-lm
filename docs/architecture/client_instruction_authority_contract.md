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

### 1. Configured SOUL exists

When an approved `SOUL.md` or equivalent RelaySOUL persona revision exists:

- RelayLM uses that persona source as the authoritative character core.
- Client `system` and `developer` messages are not promoted into RelaySOUL.
- They do not overwrite or replace the stable persona prefix.
- A route may inspect an explicitly allowed client instruction as a low-trust transient hint.
- Any durable persona change must go through RelaySOUL proposal, validation, approval, revision, and rollback rules.

```text
approved RelaySOUL exists
  -> use RelaySOUL
  -> client system prompt is non-authoritative
  -> no silent persona mutation
```

### 2. SOUL is missing on the first managed request

When a RelayLM-managed persona route has no usable SOUL source, RelayLM may use the first valid client system prompt as a bootstrap persona seed.

This is the onboarding and compatibility path for frontends that already carry a character persona prompt.

```text
SOUL missing
  + first valid client system prompt present
  + bootstrap policy enabled

  -> preserve the prompt as bootstrap evidence
  -> use a bounded temporary persona block for the first request
  -> create an initial RelaySOUL persona-source revision
  -> validate file boundaries and compile budget
  -> activate the generated persona source
  -> use the generated RelaySOUL revision on later turns
```

The bootstrap prompt is a source for creation, not permanent authority by itself.

## First-turn behavior

The first request must not lose the frontend character merely because RelayLM has not created its own SOUL file yet.

Therefore, while bootstrap is in progress, RelayLM may compile a bounded `incoming_system_prompt` block as temporary persona evidence for that request.

Required constraints:

- only the first valid bootstrap source for the route/persona scope is eligible,
- the block is dynamic and not part of the stable prefix hash,
- it is token-budgeted,
- it is marked as bootstrap evidence in diagnostics,
- it must not be copied verbatim into persistent persona files without classification,
- it must not be accepted when an approved SOUL already exists.

This preserves URL-swap onboarding while keeping the stable persona boundary explicit.

## Persona-source creation

RelaySOUL should classify the bootstrap prompt into the existing persona file boundaries.

```text
SOUL.md
  durable identity, values, worldview, invariants

OUTPUT_POLICY.md
  tone, verbosity, response shape, TTS-friendly expression

RELATIONSHIP_ANCHOR.md
  stable relationship expectations

SCENE_STATE.md
  temporary roleplay, current setting, current event, transient situation
```

The client prompt must not be dumped wholesale into `SOUL.md`.

At minimum, the bootstrap process should always produce a bounded `SOUL.md` core. Other persona-source files may be created when the source prompt contains material that belongs outside the persona core.

## Bootstrap activation authority

Bootstrap activation must be explicit at the route or operator-policy level.

Recommended policy:

```text
client_instruction_policy = relay_soul_authoritative
soul_bootstrap_policy = from_first_client_system
```

The explicit bootstrap configuration acts as operator authorization to create the initial persona revision from the first client system prompt.

After the initial revision exists, normal RelaySOUL mutation rules apply. Later client prompts cannot silently replace it.

A stricter deployment may use:

```text
soul_bootstrap_policy = proposal_only
```

In that mode, the first prompt may be used temporarily for the current request, but the generated persona revision remains a candidate until approved.

## Missing bootstrap source

If SOUL is missing and there is no usable client system prompt:

- do not reuse old client history as a substitute,
- do not invent a durable character identity from unrelated user messages,
- create a minimal neutral bootstrap candidate only when an explicit route policy allows it,
- otherwise enter setup/recovery handling rather than pretending that a configured persona exists.

## Later client system prompts

After RelaySOUL has been created:

- repeated frontend persona prompts are excluded from authoritative backend context,
- identical or near-identical prompts may be ignored with diagnostics,
- materially different prompts may become low-trust transient evidence,
- a clear user request to change the character may open RelaySOUL `character_creation` or `calibration`,
- no later prompt may directly rewrite the active SOUL revision.

## Route behavior

### `pass_through`

```text
client owns instructions and history
RelayLM preserves client messages
no RelaySOUL authority is asserted
```

### RelayLM-managed route with existing SOUL

```text
RelaySOUL owns persona authority
client system/developer messages are non-authoritative
```

### RelayLM-managed route without SOUL

```text
first client system prompt may bootstrap persona creation
only when bootstrap policy explicitly allows it
```

## Interaction with client history authority

Client history and client instruction authority are separate decisions.

```text
Client History Authority:
  Which prior messages may reach the backend?

Client Instruction Authority:
  Which instruction source defines persona and policy?
```

The first bootstrap system prompt is a narrow exception to normal history exclusion. It is extracted specifically as bootstrap evidence before prior client history is removed.

Once a RelaySOUL revision exists, this exception closes.

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

After activation:

```json
{
  "soul_source_state": "approved_revision_present",
  "bootstrap_eligible": false,
  "bootstrap_source_used_for_current_turn": false,
  "client_instruction_overrode_existing_soul": false
}
```

Diagnostics should not copy the raw client system prompt into content-free runtime artifacts.

## Failure behavior

### SOUL exists but client prompt conflicts

```text
keep existing RelaySOUL
exclude conflicting client instruction from persona authority
record conflict diagnostics
continue or clarify according to route policy
```

### Bootstrap generation fails

```text
keep the bounded temporary first-turn persona block when safe
record bootstrap failure
never persist a malformed persona source
route later turns to setup/recovery until a valid source exists
```

### Bootstrap validation fails

```text
do not activate the candidate
preserve the previous persona state, which is still "missing"
do not treat the raw client prompt as a durable SOUL revision
```

## Required validation

Before activation, the initial persona-source revision should pass:

- persona file-boundary classification,
- source-size and token-budget checks,
- stable-prefix compile dry-run,
- forbidden content/key checks,
- revision metadata creation,
- rollback availability,
- route/persona scope isolation.

## Required smoke coverage

1. Existing SOUL wins over a conflicting client system prompt.
2. Missing SOUL plus a valid first system prompt produces bootstrap diagnostics.
3. The first request retains temporary persona behavior while bootstrap is pending.
4. Bootstrap source is classified instead of copied wholesale into `SOUL.md`.
5. After activation, later requests use the generated RelaySOUL source.
6. Later conflicting client prompts do not silently mutate SOUL.
7. Missing SOUL and missing client system prompt fails closed or enters explicit setup policy.
8. Pass-through mode remains unchanged.
9. Bootstrap diagnostics remain content-free.
10. A failed bootstrap candidate is never activated.

## Final boundary

```text
Use the SOUL when it exists.
When it does not exist, the first client system prompt may help create it.
After creation, RelaySOUL becomes the authority.
```
