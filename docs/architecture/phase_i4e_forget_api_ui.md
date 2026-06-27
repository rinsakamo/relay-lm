---
relaylm_status: implemented_in_pr
relaylm_authority: phase_i4e_forget_api_ui_handoff
relaylm_phase: I-4E
---

# Phase I-4E Forget API and SOUL Lab UI

## Scope and status

Phase I-4E adds only the product surface for the already-completed Primary MEM Forget/Hide authorities. It connects SOUL Lab to a loopback-only API and UI flow for one real current active Primary MEM:

```text
SOUL Lab memory item
-> Forget preflight
-> bounded effect preview
-> explicit confirmation
-> exact apply token
-> existing I-4C1/I-4C2 apply/recovery authority
-> hidden / retrieval-ineligible convergence
-> bounded receipt
-> read-only history and lifecycle projection refresh
```

Status: implemented in this PR. This document is the slice-owned handoff. Repository-wide current-status/index reconciliation is intentionally left to Wave 4 integration audit unless a smoke requires a link.

## Route contract

All routes are loopback-only management routes and inherit the existing SOUL Lab management boundary:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight?namespace=...
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget?namespace=...
GET  /lab/api/characters/{character_id}/memory/{memory_id}/forget-history?namespace=...
```

Request schema anchors:

```text
relaylm.lab.memory_forget_preflight_request.v0
relaylm.lab.memory_forget_apply_request.v0
relaylm.lab.memory_forget_history.v0
```

Preflight accepts `expected_revision`, `expected_lifecycle_state=active`, runtime-private `reason`, and `operation_id`. Apply accepts the same exact operation binding plus `apply_token`. History is read-only and bounded.

The browser never supplies store root, filesystem path, physical ID, backend ID, route authority, recovery control, or namespace path authority. The server resolves the store root from the same SOUL Lab observation/correction scope resolver used by the existing Correct API.

## UI state machine

```text
idle
-> preflight-loading
-> preflight-ready
-> apply-loading
-> applied
```

Error states are terminal until the user refreshes or starts a new operation. The UI uses the existing character/source generation fencing pattern: stale responses are discarded when the active character, namespace, source mode, refresh key, or component generation changes.

The preview displays:

- shortened `memory_id`
- current revision
- target lifecycle `hidden`
- ordinary retrieval exclusion
- RelayCTX injection exclusion
- no physical deletion
- audit evidence retained
- historical used-memory evidence unchanged

Apply requires an explicit button click after preflight. Hover, row selection, initial page load, local preview mode, or history loading cannot call apply.

## API error mapping

The Lab API exposes only bounded reason codes and maps existing Forget authority errors as follows:

| authority code | HTTP | public detail |
| --- | ---: | --- |
| invalid_request | 422 | invalid_request |
| target_not_found | 404 | target_not_found |
| not_found_or_wrong_scope | 404 | not_found_or_wrong_scope |
| target_not_active | 409 | target_not_active |
| stale_revision | 409 | stale_revision |
| operation_conflict | 409 | operation_conflict |
| preflight_required | 409 | preflight_required |
| token_expired | 409 | token_expired |
| token_invalid | 403 | token_invalid |
| target_corrupt | 409 | target_corrupt |
| reconciliation_required | 503 | reconciliation_required |
| store_unavailable | 503 | store_unavailable |
| access_refused | 403 | access_refused |
| response_lost | 503 | response_lost |
| already_hidden | 409 | already_hidden |

Unknown internal exceptions are not surfaced. They collapse to bounded store/reconciliation failures.

## Security and leakage boundary

The API and UI do not expose:

- raw exception text or repr
- private filesystem path or store root
- token claims or token digests
- physical IDs
- raw tombstone content
- reason body or reason digest
- private memory content in error details
- browser-provided namespace/store/path authority

The preflight projection is intentionally smaller than the internal authority result. It includes only the current revision, target revision/lifecycle, bounded effects, token, and expiry. Apply returns only a bounded receipt proving hidden lifecycle, retrieval exclusion, RelayCTX exclusion, audit retention, convergence, and no physical deletion.

## Interaction with earlier I-4 authorities

- I-4B remains the authority for current-state resolution, shared mutation fence, read-only preflight, token creation/validation, and history boundary.
- I-4C1 remains the authority for hidden successor commit.
- I-4C2 remains the authority for prepared recovery, controls convergence, tombstone finalization, and public apply semantics.
- I-4D remains the authority for ordinary M2/RelayCTX lifecycle exclusion and historical lifecycle overlay.
- I-4E only passes already-validated path/query/body fields to those authorities through a loopback API and UI.

## Explicit non-goals

I-4E does not implement restore, purge, unhide, physical deletion, repair, automatic recovery controls, new retrieval filtering logic, M2 ranking, snippet construction, worker/queue/scheduler durability, or I-4F crash/race/security/fresh-conversation full validation.

## I-4F handoff items

I-4F should validate the completed surface under crash, race, stale browser generation, token expiry, token replay, response-lost, store-unavailable, fresh-conversation, and multi-character isolation conditions. It should also verify no lifecycle-hidden memory can be retrieved or injected after apply across full process restart and browser refresh paths.
