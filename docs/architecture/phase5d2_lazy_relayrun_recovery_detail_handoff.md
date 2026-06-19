# Phase 5-D2 Lazy RelayRUN Recovery Detail Handoff

## Status

This document describes the first bounded Phase 5-D2 implementation slice: a side-effect-free lazy RelayRUN recovery-detail helper and direct smoke coverage.

The helper is implemented as an opt-in runtime builder in `relaylm/relayrun_lazy_recovery.py`. Existing RelayRUN checkpoint and recovery helpers remain unchanged and continue to provide the full diagnostics chain when called directly.

## Goal

Phase 5-D2 reduces ordinary-path RelayRUN overhead before Stream Unpack by avoiding eager construction of recovery-chain detail when a request is already on the normal completed path.

The boundary is:

```text
ordinary completed path
  -> keep content-free checkpoint summary
  -> do not construct recovery transition / waiting-user / visible recovery detail

blocked / failed / checkpoint / recovery diagnostics path
  -> construct the existing full RelayRUN recovery detail chain
```

## Implemented bounded slice

Implemented in this slice:

- `build_runtime_checkpoint_lazy_recovery_artifact(...)`,
- content-free `relayrun.recovery_detail.lazy.v0` summary,
- ordinary-path minimal runtime checkpoint artifact construction,
- full-detail fallback for blocked, failed, waiting-user, explicit checkpoint, and recovery diagnostics paths,
- explicit include/skip override for tests and later app wiring,
- direct smoke coverage for ordinary, blocked, backend-failed, explicit override, and checkpoint/recovery flag paths,
- a dedicated GitHub Actions smoke workflow for this boundary.

## Compatibility

The existing `build_runtime_checkpoint_dry_run_artifact(...)` helper is not changed. Existing direct smoke tests and direct callers keep the full RelayRUN checkpoint/recovery detail contract by default.

The lazy helper is additive. It is intended for request-runtime callers that can determine whether the path is ordinary before choosing whether to build full detail.

## Content-free contract

The lazy summary exposes only:

- schema version,
- constructed/not-constructed boolean,
- reason IDs,
- required-reason IDs,
- diagnostics/content-free safety booleans.

It must not include conversation text, backend bodies, prompt text, snippet text, instruction bodies, hashes, cache bodies, or runtime-private payload candidates.

## Full-detail triggers

The helper constructs full recovery detail when any of the following content-free conditions apply:

- explicit `include_recovery_details=True`,
- backend forward status is `failed` or `blocked`,
- any node is `failed`, `blocked`, or `waiting_user`,
- top-level blocked reasons are present,
- checkpoint write diagnostics are explicitly requested, including dry-run write diagnostics,
- checkpoint index diagnostics are explicitly requested, including dry-run index diagnostics,
- resume, recovery transition, waiting-user, apply preflight, recovery response, visible recovery, output RelaySCN recovery gate, visible apply, or user-action diagnostics are explicitly enabled,
- recovery transition creation or runtime apply state is already present.

## Follow-up wiring

The next bounded follow-up should wire this helper into `app.py` / request runtime so ordinary completed requests call the lazy helper instead of the full checkpoint/recovery builder.

That follow-up must preserve:

- user-visible behavior,
- fail-closed blocked/error behavior,
- content-free trace/audit/public-error contracts,
- runtime checkpoint and node-result contracts,
- pass-through and managed-apply semantics,
- safe defaults.

## Smoke

Direct smoke:

```bash
python scripts/relaylm_relayrun_lazy_recovery_detail_smoke.py
```

Recommended regression set:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_relayrun_lazy_recovery_detail_smoke.py
python scripts/relaylm_relayrun_runtime_checkpoint_dry_run_smoke.py
python scripts/relaylm_relayrun_recovery_transition_dry_run_smoke.py
python scripts/relaylm_relayrun_waiting_user_contract_smoke.py
python scripts/relaylm_relayrun_recovery_apply_preflight_smoke.py
python scripts/relaylm_relayrun_recovery_response_draft_smoke.py
python scripts/relaylm_relayrun_visible_recovery_preflight_smoke.py
python scripts/relaylm_relayrun_recovery_response_generator_smoke.py
python scripts/relaylm_relayrun_output_relayscn_recovery_gate_smoke.py
python scripts/relaylm_relayrun_visible_recovery_apply_preflight_smoke.py
python scripts/relaylm_relayrun_user_action_contract_smoke.py
python scripts/relaylm_runtime_diagnostics_smoke.py
python scripts/relaylm_trace_content_free_contract_smoke.py
```
