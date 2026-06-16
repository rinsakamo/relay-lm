# RelayRUN Recovery Response Generator Contract

## Purpose

This contract separates the current diagnostics-only recovery-response artifact from the future generator that may create user-visible recovery wording.

## Current implemented artifact

Current runtime can build a diagnostics-only `recovery_response_generator` artifact.

Current fixed fields include:

```text
generator_allowed = false
generator_attempted = false
generated_text_present = false
output_pipeline_required = true
```

Current behavior:

- maps content-free source message kinds to content-free intent classes,
- records reason IDs and required output-pipeline stages,
- stores projected source metadata only,
- omits draft prompt text and nested content-bearing artifacts,
- does not invoke a text generator,
- does not produce visible recovery text,
- does not mutate backend payloads or response bodies.

Current downstream diagnostics-only artifacts may include `output_relayscn_recovery_gate`, `visible_recovery_apply_preflight`, and `user_action_contract`. They do not execute Output-side RelaySCN, apply visible output, parse user actions, resume, or retry.

## Stable ownership

RelayRUN may structure recovery intent, blocked/waiting-user state, transition metadata, and output-pipeline prerequisites. It does not finalize character-facing wording.

Any future visible recovery text must pass the normal output pipeline and output-side safety/scene gates.

## Recovery reanchor principle

Repaired or reconstructed context is not trusted merely because RelayLM produced it.

```text
recovery evidence
  -> bounded context/handoff candidate
  -> ask the user to confirm, correct, or restate
  -> confirmed scope may re-enter normal execution
```

While confirmation is outstanding:

- keep waiting-user state,
- do not auto-resume guessed work,
- do not persist guessed repair into MEM or SOUL,
- use open clarification when the candidate is weak.

## Current artifact inputs

Only content-free projected metadata from approved recovery-draft/preflight artifacts and route/scene classes may enter the current artifact.

It must not contain:

- raw user messages,
- backend payload/response text,
- prompt text,
- memory/snippet bodies,
- prior generated wording,
- full checkpoint bodies,
- nested source-artifact trees.

## Current intent mapping

Current content-free intent classes may represent:

- no recovery message,
- ask for clarification,
- ask for context repair/restate,
- explain a backend failure at a high level,
- ask the user to choose a recovery action.

The artifact describes intent only; it does not store final wording.

## Target generator

A future generator may run only after:

- explicit feature enablement,
- a non-dry-run execution posture,
- visible-response preflight,
- Output-side RelaySCN approval,
- applicable waiting-user confirmation,
- content-policy verification,
- normal output-pipeline availability.

Target visible output remains separate from RelayRUN's content-free runtime artifact.

## Required migration

Update together:

1. generator execution and feature flags,
2. output-pipeline integration,
3. Output-side RelaySCN gate execution,
4. waiting-user and user-action handling,
5. response adapters,
6. retry/resume state and idempotency,
7. content-free projections,
8. recovery and integration smoke tests.

## Safety constraints

Until that migration:

- no generator execution,
- no user-visible recovery output,
- no direct RelayRUN final text,
- no backend/request/response mutation,
- no actual resume, retry, or recovery-transition apply,
- no stream recovery.
