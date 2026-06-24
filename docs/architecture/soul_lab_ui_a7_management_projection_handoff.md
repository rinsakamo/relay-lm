---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - Lab management read schema changes
  - server projection redaction changes
  - Settings projection source behavior changes
  - Lab management mutation work begins
relaylm_not_authoritative_for:
  - runtime configuration persistence
  - credential storage or secret delivery
  - backend connectivity or health
  - persistent character registry mutation
  - SOUL, MEM, RelayRUN, or RelaySLP mutation
  - static UI bundle serving
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a6_shared_shell_settings_handoff.md
  - phase_i2_real_soul_lab_observation.md
  - soul_lab_runtime_mvp.md
---
# SOUL Lab UI-A7 Read-only Lab Management Projection

## Status

SOUL Lab UI-A7 remains complete and unchanged as the first server-owned Lab management boundary. It keeps the browser read-only and preserves UI-A6 as an explicit fallback.

```text
RelayLM loopback runtime config
and loopback transport peer
  -> server-owned content-free projection
  -> GET /lab/api/settings
  -> GET /lab/api/characters
  -> exact browser schema validation
  -> Settings server projection

request failure, access refusal, or invalid schema
  -> explicitly labeled UI-A6 mock fallback
```

Phase I-2 reuses the same ASGI and loopback access boundary for separate observation schemas. It does not widen the UI-A7 settings or characters responses and does not make them content-bearing.

## UI-A7 bounded scope

UI-A7 implements only:

- local-only `GET /lab/api/settings`,
- local-only `GET /lab/api/characters`,
- exact versioned projection schemas,
- server-side redaction and content exclusion,
- `Cache-Control: no-store`,
- a same-origin browser client,
- strict runtime validation before rendering,
- loading, server-owned, and fallback states,
- a Vite development proxy from `/lab/api/*` to RelayLM on port 8090.

It does not add settings writes, character mutation, connection tests, process actions, memory inspection, or adapter execution.

## ASGI ownership

`relaylm.soul_lab_app` wraps the existing `relaylm.app.create_app` factory and registers Lab read routes on the returned FastAPI application.

The canonical `relaylm` console command starts this wrapper. Existing `/healthz`, `/v1/models`, and `/v1/chat/completions` behavior continues to come from the core application. Direct use of `relaylm.app:create_app` remains a core-only application factory.

Phase I-2 preserves this ownership and adds observation middleware/read routes only to `relaylm.soul_lab_app`; it does not alter Core route ownership.

## Local access boundary

Both conditions are required for every Lab management or observation response:

1. validated RelayLM configuration uses a loopback listen host,
2. actual ASGI transport peer is loopback.

Accepted loopback forms include `localhost`, IPv4 loopback, and IPv6 loopback. Wildcard/non-loopback config, non-loopback transport, or unavailable peer causes:

```json
{
  "detail": "lab_management_requires_loopback_access"
}
```

with HTTP `403`.

Host, Origin, forwarded headers, browser declarations, and query parameters are not proof of locality. Existing Core routes retain their existing behavior when Lab access is refused.

## Settings projection

`GET /lab/api/settings` returns:

```text
relaylm.lab.settings.v0
```

The response contains only bounded configuration metadata:

- projection kind and source,
- content-free and read-only flags,
- listen host, port, and loopback classification,
- RelayLM endpoint metadata,
- redacted configured backend endpoint metadata,
- route/model labels inside bounded runtime components,
- TTS/avatar capability state,
- credential-boundary metadata,
- content-free diagnostics counters.

It does not perform network probes. `configured` does not mean reachable or healthy.

## Character projection

`GET /lab/api/characters` returns:

```text
relaylm.lab.characters.v0
```

Each item may contain:

- `character_id`,
- route/model labels,
- backend IDs,
- memory namespace labels,
- configured route modes,
- booleans for required persona-source presence,
- derived `source_complete`.

It contains no persona path/content, memory path/content, prompt, transcript, or credential. A route referencing an incomplete character is projected as incomplete rather than silently omitted.

Phase I-2 uses this projection only to discover the explicit server-owned character/namespace mapping for subsequent observation requests. It does not derive filesystem paths in the browser and does not treat browser-local mock characters as server authority.

## Redaction and exclusion

UI-A7 continues to exclude:

- backend API keys,
- URL usernames/passwords,
- URL query/fragment,
- persona paths/content,
- memory paths/content,
- trace paths/raw traces,
- prompt/conversation text,
- MEM or SOUL contents.

Backend URLs are reduced to scheme, host, optional port, and path. Invalid endpoint values degrade to a non-secret configured label.

Phase I-2 limited memory title/summary inspection is not added to these content-free schemas. It is exposed only through separate versioned observation schemas under the explicit Lab Observation route.

## Browser validation

`managementApi.ts` accepts the settings/characters bundle only when every object has the exact allowlisted key set and every value matches the UI-A7 contract.

```text
both responses valid
and settings.listen.loopback_only == true
and no object contains an unexpected key
  -> server projection

HTTP failure or refusal
or missing/unexpected field
or value/type mismatch
or loopback-only mismatch
  -> discard the bundle
  -> labeled mock fallback
```

The browser never partially trusts one response while mixing it with another. Reload clears stale server state before revalidation.

Phase I-2 applies the same exact-key principle in a separate `observationApi.ts`, plus explicit character, namespace, run, item-count, summary-length, and enum validation. Management and observation bundles remain separate contracts.

## Settings presentation

`ConnectedSettingsPage` owns the UI-A7 read attempt and source-state display.

Server success displays content-free runtime components, configured characters, diagnostics, and credential/authority boundaries. Failure displays the UI-A6 Settings page as an explicitly labeled browser-local mock fallback. The two sources are not simultaneous.

Phase I-2 uses a distinct `ConnectedLabObservationPage`. Settings fallback and Lab Observation fallback do not share trusted data bundles.

## Development topology

```text
browser
  http://127.0.0.1:5173/lab/

Vite proxy
  /lab/api/*
    -> http://127.0.0.1:8090/lab/api/*

RelayLM canonical CLI
  relaylm --config config.yaml
```

The proxy is local-only and does not add permissive CORS. Both RelayLM config and proxy-to-RelayLM peer must be loopback.

## Validation

UI-A7 server validation remains:

```bash
PYTHONPATH=. python scripts/relaylm_soul_lab_management_projection_smoke.py
```

It verifies exact schemas, secret/path/content exclusion, complete/incomplete character behavior, no-store, mutation `405`, loopback host/peer enforcement, spoof resistance, and unchanged Core health/model routes.

Frontend validation remains:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

Phase I-2 adds separate functional/security/restart/browser validation without replacing the UI-A7 smoke.

## Authority boundary

UI-A7 is read-only observation of bounded runtime configuration metadata. It does not authorize or implement:

- settings or character mutation,
- remote/LAN Lab access,
- backend connection testing,
- browser credential loading,
- persistent active-character changes,
- SOUL/MEM inspection or mutation,
- RelayRUN/RelaySLP mutation,
- process lifecycle,
- TTS/avatar execution,
- static UI serving.

Phase I-2 adds bounded explicit memory/run inspection only. Its receipts remain read-model evidence and cannot change UI-A7 authority or repair Core state.

## Downstream boundary

Phase I-2 real Lab observation is complete. The next bounded product slice is Phase I-3 auditable Correct, implemented as a separately reviewed mutation contract. It must not retrofit writes into UI-A7 settings/characters routes.
