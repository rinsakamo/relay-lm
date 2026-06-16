# RelayRUN Recovery Response Generator Current / Target Boundary

## Purpose

This note resolves the difference between the implemented diagnostics-only recovery-response artifact and the future generator that may produce visible recovery wording.

## Current implemented artifact

The current runtime can build a diagnostics-only `recovery_response_generator` artifact.

Current fixed posture:

```text
generator_allowed = false
generator_attempted = false
generated_text_present = false
output_pipeline_required = true
```

The artifact:

- maps content-free recovery message kinds to content-free intent classes,
- records reason identifiers and output-pipeline prerequisites,
- stores projected source metadata only,
- omits draft prompt text and nested content-bearing artifacts,
- does not invoke a text generator,
- does not produce visible recovery output,
- does not change request or response payloads.

## Target generator

A future generator may transform approved recovery intent into candidate wording only after:

- the feature is explicitly enabled,
- dry-run-only posture is disabled in a later phase,
- visible-response preflight passes,
- output-side RelaySCN permits the response,
- waiting-user requirements are satisfied,
- the normal output pipeline is available.

RelayRUN remains responsible for runtime state and intent metadata. Character-facing wording must pass RelayCTX Unpack and the applicable output-side gates.

## Current downstream artifacts

The current chain may also build diagnostics-only projected artifacts for:

- `output_relayscn_recovery_gate`,
- `visible_recovery_apply_preflight`,
- `user_action_contract`.

These artifacts do not execute output-side RelaySCN, generate text, apply visible output, parse user actions, resume execution, or retry nodes.

## Content boundary

Current artifacts must not contain:

- raw request text,
- backend payload or response text,
- prompt text,
- memory/snippet bodies,
- final generated wording,
- full nested source artifacts.

## Required migration

A future visible-recovery implementation must update together:

1. generator execution and feature flags,
2. output-pipeline integration,
3. output-side RelaySCN gate execution,
4. waiting-user and user-action handling,
5. response adapters,
6. retry/resume state,
7. content-free projections,
8. recovery and integration smoke tests.

## References

- [RelayRUN Recovery Response Generator Contract](relayrun_recovery_response_generator_contract.md)
- [RelayRUN Runtime Checkpoint Design](../architecture/relayrun_runtime_checkpoint_design.md)
- [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md)
