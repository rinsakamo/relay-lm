# Exploratory Lab Session and Pre-Qualification Rehearsal

This document is the owner-local contract for RelayLM LAB3 exploratory execution.
It exists to keep execution-procedure discovery out of strict citable
Qualification without weakening any Qualification evidence rule.

> **Explore until the execution procedure is known. Then prove the known
> procedure once from fresh authority.**

## Boundary

LAB3 is explicitly **EXPLORATORY / NON-CITABLE**.

```text
verified Lab Environment
  -> existing owned runtime boundary
  -> ExploratoryLabSession
       |- trial A
       |- trial B with a changed mechanical condition
       `- successful rehearsal -> ExploratoryProcedureHint
  -> owned cleanup

later, separately
  -> fresh repository / owner authority
  -> fresh process / listener / GPU / admission / capacity authority
  -> EXECUTION_FROZEN
  -> Qualification evidence
```

An exploratory result may discover a procedure or hypothesis. It is never
retroactively promoted into Qualification evidence, even when its effective
condition happens to match a later Qualification condition.

LAB3 does not define a second launcher, process-ownership system, listener
contract, GPU-admission contract, freeze state, or evidence writer. When a warm
vLLM runtime is used, the caller obtains and owns it through the existing
`OwnedVLLMRuntime` boundary. `ExploratoryLabSession` only groups non-citable
trials around that already-owned runtime and delegates final cleanup back to
`OwnedVLLMRuntime.cleanup(...)`.

## Session identity

`ExploratoryLabSession` requires:

- one bounded `session_id`;
- one exact `LabEnvironmentManifest` fingerprint in `sha256:<hex>` form; and
- optionally one already-owned `OwnedVLLMRuntime`.

Its status is permanently marked:

```json
{
  "evidence_class": "EXPLORATORY_NON_CITABLE",
  "citable": false,
  "qualification_authority": false
}
```

There is deliberately no conversion API from an exploratory session, trial, or
procedure hint to `LiveLaunchAdmissionAttestation`, a frozen experiment
identity, a durable benchmark question run, a citable token-capacity reference,
or semantic Qualification evidence.

## Named exploratory trials

Every probe or rehearsal attempt is a separately identified trial. A trial
records only bounded, content-free procedure information:

- `trial_id`;
- Lab Environment fingerprint;
- `condition_id` describing the mechanical condition identity;
- declared `required_steps`;
- actually `completed_steps`;
- outcome: `PASS`, `FAIL`, or `INCONCLUSIVE`; and
- optional uppercase content-free detail codes.

The session permits multiple trials against the same owned warm runtime. A
researcher may change a mechanical condition between trials, such as a native
runtime root, environment composition, endpoint choice procedure, launch argv,
or other non-semantic execution detail. Such a change is represented by a new
trial and condition identity rather than hidden inside a retry.

LAB3 therefore permits the trial-and-error that Qualification intentionally
forbids.

It does not authorize benchmark-specific product changes, prompt tuning under a
citable identity, mutation of State/Continuity/MEMORY semantics, or sharing
mutable Cognitive Package state between experiments that are supposed to be
independent.

## Rehearsal completion

A rehearsal declares the mechanical steps that must succeed for its procedure
to be considered known. The exact step names are caller-owned content-free
codes. Typical actual-model rehearsal steps can include, when relevant:

```text
clean_checkout
runtime_paths
environment
endpoint
launch
readiness
profiler
final_launch
cleanup
```

`PASS` is valid only when every declared required step is complete. A partial
run must remain `FAIL` or `INCONCLUSIVE`.

A successful rehearsal may produce `ExploratoryProcedureHint`. The hint carries
only:

- session/trial identity;
- Lab Environment fingerprint;
- mechanical condition identity; and
- completed procedure-step codes.

It remains `EXPLORATORY_NON_CITABLE`, `citable=false`, and
`qualification_authority=false`. It says only **which procedure to attempt
freshly**, not that any current physical fact has been proved.

## What rehearsal is for

Use rehearsal when the execution procedure itself has material uncertainty that
could otherwise be discovered only by spending a strict physical transaction.
Examples include:

- whether controller/scratch placement preserves a required clean checkout;
- native-Linux temporary and IPC path composition;
- caller versus runtime-owned environment-variable composition;
- bounded endpoint selection and listener inspection mechanics;
- current runtime CLI/capability negotiation;
- startup/readiness wiring;
- profiler-to-final-launch procedure; and
- ownership-safe cleanup.

If current deterministic repository authority and prior stable procedure
already make those mechanics unambiguous, rehearsal is optional. LAB3 must not
become mandatory ceremony around a procedure that is already known.

## What rehearsal is not for

Rehearsal does not establish or persist as current authority:

- current repository HEAD or open writers;
- GPU free/total memory;
- utilization/admission decisions;
- KV/cache capacity observations;
- process PID/start-time/PGID/session identity;
- listener ownership or endpoint occupancy;
- runtime nonce or run id;
- `EXECUTION_FROZEN` state;
- semantic request count;
- benchmark answers/checkpoints;
- mutable Event/State/Continuity/MEMORY/Cognitive Package state; or
- any citable result.

Those facts are freshly established by the owner of a later Qualification
transaction when that contract requires them.

## Warm runtime reuse

A LAB3 session may keep one owned runtime alive across several named exploratory
trials when doing so is useful. The session does not claim that this warm
runtime is suitable for later Qualification.

When exploration ends, `stop()` delegates to the existing owned-runtime cleanup
primitive and accepts completion only from a complete `RuntimeCleanupReceipt`.
Cleanup therefore remains nonce/process/listener scoped to the current runtime
owner rather than introducing a LAB3-specific process-killing path.

Independent semantic experiment arms must not accidentally share mutable
RelayLM state merely because they share a physical Lab Environment or warm model
server.

## Historical notes

`save_notes(...)` may persist the session and its bounded trial records as
lightweight historical research notes. The saved mapping is explicitly
non-citable and contains procedure identities/codes only. It is not a current
authority database and has no promotion path into Qualification evidence.

Do not put secrets, prompts, request/response payloads, transient GPU values,
PIDs, listener snapshots, or semantic state into LAB3 trial identifiers or
notes.

## Qualification handoff

A successful rehearsal changes only the researcher's knowledge of the procedure.
It does not change the Qualification freshness model.

The later proof remains:

```text
successful non-citable rehearsal
  -> stop / clean exploratory runtime as applicable
  -> start a separate Qualification transaction
  -> reacquire current repository / Issue / open-writer authority
  -> restore/verify the stable Lab Environment if used
  -> freshly establish runtime ownership / listener state
  -> freshly establish GPU / admission / live capacity facts
  -> construct the owner-required live attestation
  -> EXECUTION_FROZEN
  -> one strict citable execution
```

If that fresh Qualification fails, its owner still follows the Qualification
stop/no-retry rules. If the failure reveals a previously unknown *mechanical
procedure* defect rather than a product/evidence result, converge that procedure
again through a later exploratory rehearsal before spending another fresh
citable successor.

## Relationship to current strict transactions

LAB3 does not rewrite or relax an already-open citable transaction. In
particular, adding LAB3 does not alter the frozen rules of a current physical
owner merely because rehearsal would have been useful before that owner was
created.

The boundary applies to future entry into proof: unknown mechanics are learned
outside the proof transaction, then the learned procedure is independently
reproduced once under fresh Qualification authority.

## Fixed principles

1. **Exploration discovers; Qualification proves.**
2. **A warm Lab Session is reusable execution convenience, not evidence.**
3. **Changed mechanical conditions are separate named exploratory trials.**
4. **A successful rehearsal produces only a non-citable procedure hint.**
5. **Exploratory artifacts have no promotion path into Qualification evidence.**
6. **Reuse existing runtime ownership and cleanup; do not create a second process authority.**
7. **When mechanics are already known from current deterministic authority, rehearsal is optional.**
8. **When mechanics are unknown, discover them before spending the one-shot proof.**
