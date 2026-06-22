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
  - soul_lab_runtime_mvp.md
---
# SOUL Lab UI-A7 Read-only Lab Management Projection

## Status

SOUL Lab UI-A7 adds the first server-owned Lab management boundary while keeping the browser read-only and preserving UI-A6 as an explicit fallback.

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

## Bounded scope

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

It does not add a settings write endpoint, character mutation endpoint, connection test, process action, or adapter execution.

## ASGI ownership

`relaylm.soul_lab_app` wraps the existing `relaylm.app.create_app` factory and registers the two Lab read routes on the returned FastAPI application.

The canonical `relaylm` console command now starts this wrapper. Existing `/healthz`, `/v1/models`, and `/v1/chat/completions` behavior continues to come from the core application.

Direct use of `relaylm.app:create_app` remains a core-only application factory. The canonical CLI is the supported UI-A7 runtime entry point.

## Local access boundary

Both of the following conditions are required for a Lab management response:

1. the validated RelayLM configuration uses a loopback listen host,
2. the actual ASGI transport peer is loopback.

Accepted loopback forms include:

- `localhost`,
- IPv4 loopback addresses such as `127.0.0.1` and `127.0.0.2`,
- IPv6 loopback `::1` and `[::1]`.

A wildcard/non-loopback configured host, a non-loopback transport peer, or an unavailable peer address causes both Lab management routes to return:

```json
{
  "detail": "lab_management_requires_loopback_access"
}
```

with HTTP `403`.

The transport-peer check prevents a direct Uvicorn launch with a socket bind broader than `config.listen.host` from exposing the management routes to a remote client. The check does not use `Host` or `Origin` as proof of locality. Existing Core routes remain available according to their existing runtime behavior when the Lab management routes are refused.

The browser parser also requires `listen.loopback_only` to be exactly `true`. A response claiming a non-loopback projection is discarded even if it was delivered with HTTP `200`, and the UI uses the explicit mock fallback instead.

## Settings projection

`GET /lab/api/settings` returns schema:

```text
relaylm.lab.settings.v0
```

The response contains:

- projection kind and source,
- content-free and read-only flags,
- listen host, port, and loopback classification,
- RelayLM endpoint metadata,
- configured backend endpoint metadata,
- configured route and model labels inside runtime-component items,
- TTS and avatar capability state,
- explicit credential-boundary metadata,
- content-free diagnostics counters.

The endpoint does not perform a network probe. `configured` means present in validated runtime configuration, not reachable or healthy.

An earlier unused top-level `model_routes` projection was removed. Route-model labels needed by Settings remain inside the bounded runtime-component and character projections.

## Character projection

`GET /lab/api/characters` returns schema:

```text
relaylm.lab.characters.v0
```

Each character projection may contain:

- `character_id`,
- associated route-model labels,
- backend IDs,
- memory namespace labels,
- configured route modes,
- booleans for required persona-source presence,
- a derived `source_complete` boolean.

It does not contain persona source paths or file contents. A route that references a character without a matching character configuration is included as an incomplete registry projection rather than silently omitted.

## Redaction and exclusion

The server excludes:

- backend API keys,
- URL usernames and passwords,
- URL query strings and fragments,
- persona source paths,
- persona source contents,
- memory source paths,
- trace paths,
- raw traces,
- prompt text,
- conversation text,
- MEM or SOUL contents.

Backend URLs are reduced to scheme, host, optional port, and path. Invalid or unprojectable endpoint values degrade to a non-secret `configured` label.

## Browser validation

`managementApi.ts` accepts a response only when every object has the exact allowlisted key set and every value matches the UI-A7 contract.

Exact-key validation applies to:

- the settings projection,
- listen metadata,
- every runtime component,
- credential-boundary metadata,
- diagnostics metadata,
- the characters projection,
- every character item.

```text
both responses valid
and settings.listen.loopback_only == true
and no object contains an unexpected key
  -> server projection

HTTP failure or 403 refusal
or missing field
or unexpected field
or value/type mismatch
or loopback-only mismatch
  -> discard the bundle
  -> labeled mock fallback
```

The browser does not partially trust one response while silently mixing it with the other. The settings and character projections are loaded as one bundle. Unexpected fields are rejected rather than silently sanitized so a server regression cannot enter the trusted server-display state while carrying unreviewed metadata.

## Settings presentation

`ConnectedSettingsPage` owns the read attempt and source-state display.

Server success displays:

- runtime component projections,
- runtime-config character projections,
- content-free diagnostics,
- the server-owned credential and authority boundary.

Failure displays the existing UI-A6 `SettingsPage` as an explicitly labeled browser-local mock fallback.

The two sources are not displayed simultaneously. Reload clears the previous server bundle before entering the loading state, so stale server schema metadata is not shown during revalidation.

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

The development proxy is local-only and does not add permissive CORS behavior. RelayLM must use loopback configuration, and the proxy-to-RelayLM transport peer must also be loopback.

## Validation

Server validation runs:

```bash
python -m compileall -q \
  relaylm/soul_lab_management.py \
  relaylm/soul_lab_app.py \
  scripts/relaylm_soul_lab_management_projection_smoke.py
python scripts/relaylm_soul_lab_management_projection_smoke.py
```

The smoke verifies:

1. exact schema versions and read-only flags,
2. API key exclusion,
3. URL userinfo, query, and fragment removal,
4. source-path and trace-path exclusion,
5. complete and incomplete character projection behavior,
6. removal of the unused top-level `model_routes` field,
7. `Cache-Control: no-store`,
8. mutation methods return `405`,
9. loopback host classification including IPv4 and IPv6 loopback,
10. a non-loopback transport peer receives `403` even with loopback configuration,
11. loopback transport receives `403` with non-loopback configuration,
12. core `/healthz` and `/v1/models` remain available when management access is refused.

UI validation remains:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

## Authority boundary

UI-A7 is read-only observation of bounded runtime configuration metadata.

It does not authorize or implement:

- `PATCH /lab/api/settings/*`,
- `POST /lab/api/characters`,
- remote or LAN access to Lab management metadata,
- backend connection testing,
- credential loading into the browser,
- persistent active-character changes,
- SOUL or MEM inspection,
- SOUL or MEM mutation,
- RelayRUN or RelaySLP mutation,
- process start or stop,
- TTS or avatar execution,
- static UI bundle serving.

## Next bounded slice

A later slice may serve the built UI from RelayLM or add a narrowly scoped mutation preflight. Any mutation work must remain separate from UI-A7 and begin with an explicit server-side schema, validation, dry-run or preflight boundary, credential ownership model, and a separately reviewed access-control boundary.
