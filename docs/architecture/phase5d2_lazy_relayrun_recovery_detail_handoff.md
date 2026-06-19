# Phase 5-D2 Lazy RelayRUN Recovery Detail Handoff

## Status

Phase 5-D2 is split into two bounded implementation slices:

- **Phase 5-D2a** added the side-effect-free lazy RelayRUN recovery-detail helper and direct helper smoke coverage.
- **Phase 5-D2b** wires that helper into the request-runtime RelayRUN checkpoint builder used by `/v1/chat/completions`.

The existing full RelayRUN checkpoint/recovery helper remains available for direct callers and for paths where full detail is required.

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

## Implemented slices

### Phase 5-D2a helper

Implemented in `relaylm/relayrun_lazy_recovery.py`:

- `build_runtime_checkpoint_lazy_recovery_artifact(...)`,
- content-free `relayrun.recovery_detail.lazy.v0` summary,
- ordinary-path minimal runtime checkpoint artifact construction,
- full-detail fallback for blocked, failed, waiting-user, explicit checkpoint, and recovery diagnostics paths,
- explicit include/skip override for tests and narrowly bounded future callers,
- direct smoke coverage for ordinary, blocked, backend-failed, explicit override, and checkpoint/recovery flag paths.

### Phase 5-D2b runtime wiring

Implemented in `relaylm/app.py`:

- request-runtime RelayRUN checkpoint construction now calls `build_runtime_checkpoint_lazy_recovery_artifact(...)`,
- `backend_forward_status`, `relayrun_checkpoint_write_enabled`, and `relayrun_checkpoint_dry_run_only` are passed into the lazy helper,
- ordinary completed `/v1/chat/completions` paths can emit the lazy `recovery_detail.constructed=false` summary,
- failed/blocked/checkpoint/recovery diagnostics paths still fall back to full RelayRUN recovery detail,
- user-visible response behavior and backend payload forwarding are unchanged.

## Compatibility

The existing `build_runtime_checkpoint_dry_run_artifact(...)` helper is not changed. Existing direct callers can still opt into the full RelayRUN checkpoint/recovery detail contract by calling it directly.

The request-runtime path does not pass `include_recovery_details=False`. It relies on automatic status/gate detection so failed, blocked, checkpoint, and recovery diagnostics paths cannot be accidentally forced into the lazy ordinary path.

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

## Smoke

Direct helper smoke:

```bash
python scripts/relaylm_relayrun_lazy_recovery_detail_smoke.py
```

Request-runtime wiring smoke:

```bash
python scripts/relaylm_relayrun_lazy_recovery_runtime_wiring_smoke.py
```

Recommended focused regression set:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_relayrun_lazy_recovery_detail_smoke.py
python scripts/relaylm_relayrun_lazy_recovery_runtime_wiring_smoke.py
python scripts/relaylm_trace_content_free_contract_smoke.py
```

Broader RelayRUN regression candidates remain useful after follow-up changes touching full recovery details:

```bash
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
```
