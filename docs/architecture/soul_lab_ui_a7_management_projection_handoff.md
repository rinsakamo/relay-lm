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
  -> server-owned content-free projection
  -> GET /lab/api/settings
  -> GET /lab/api/characters
  -> strict browser schema validation
  -> Settings server projection

request failure, non-loopback refusal, or invalid schema
  -> explicitly labeled UI-A6 mock fallback
```

## Bounded scope

UI-A7 implements only:

- loopback-only `GET /lab/api/settings`,
- loopback-only `GET /lab/api/characters`,
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

## Loopback access boundary

The management routes are available only when the configured RelayLM listen host is loopback.

Accepted loopback forms include:

- `localhost`,
- IPv4 loopback addresses such as `127.0.0.1` and `127.0.0.2`,
- IPv6 loopback `::1` and `[::1]`.

Non-loopback or wildcard listen hosts such as `0.0.0.0`, `::`, LAN addresses, and arbitrary hostnames cause both Lab management routes to return:

```json
{
  "detail": "lab_management_requires_loopback_listen"
}
```

with HTTP `403`.

This guard is derived from validated server configuration and is independent of request headers. It does not trust `Host`, `Origin`, or forwarded-address headers to prove locality. Existing Core routes remain available according to their existing runtime behavior when the Lab management routes are refused.

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
- configured route and model labels,
- TTS and avatar capability state,
- explicit credential-boundary metadata,
- content-free diagnostics counters.

The endpoint does not perform a network probe. `configured` means present in validated runtime configuration, not reachable or healthy.

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

`managementApi.ts` accepts a response only when the version, projection kind, source, read-only flags, loopback-only flag, credential flags, diagnostics flags, and item shapes match the UI-A7 contract.

```text
both responses valid
and settings.listen.loopback_only == true
  -> server projection

HTTP failure or 403 refusal
or JSON shape mismatch
or authority flag mismatch
or loopback-only mismatch
  -> discard response
  -> labeled mock fallback
```

The browser does not partially trust one response while silently mixing it with the other. The settings and character projections are loaded as one bundle.

## Settings presentation

`ConnectedSettingsPage` owns the read attempt and source-state display.

Server success displays:

- runtime component projections,
- runtime-config character projections,
- content-free diagnostics,
- the server-owned credential and authority boundary.

Failure displays the existing UI-A6 `SettingsPage` as an explicitly labeled browser-local mock fallback.

The two sources are not displayed simultaneously. This prevents mock labels from being mistaken for server state.

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

The development proxy is local-only and does not add permissive CORS behavior. RelayLM must also be configured with a loopback listen host for the management routes to return their projections.

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
6. `Cache-Control: no-store`,
7. mutation methods return `405`,
8. loopback host classification including IPv4 and IPv6 loopback,
9. non-loopback management requests return `403`,
10. core `/healthz` and `/v1/models` remain available in both loopback and non-loopback configurations.

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
