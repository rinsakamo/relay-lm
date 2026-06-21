---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - shared shell ownership changes
  - Settings or Runtime Boundary projection changes
  - browser credential handling changes
  - SOUL Lab Runtime API integration begins
relaylm_not_authoritative_for:
  - runtime configuration schema or persistence
  - credential storage or secret delivery
  - process lifecycle management
  - authoritative endpoint health
  - persistent character registry semantics
  - SOUL, MEM, RelayRUN, or RelaySLP mutation
  - repository-wide implementation status
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - soul_lab_ui_a5_memory_inspector_handoff.md
---
# SOUL Lab UI-A6 Shared Shell / Settings

## Status

SOUL Lab UI-A6 is implemented under `apps/soul-lab/` as a shared application shell plus a mock `#/settings` Runtime Boundary surface.

```text
one browser application
  -> one shared shell owner
  -> route-specific bounded feature surface
  -> browser-local projection or draft only
  -> no Runtime API call or durable mutation
```

## Shared shell owner

`RootApp.tsx` is the single owner for:

- current hash route,
- display language,
- light / dark theme,
- active character,
- navigation lock,
- sidebar,
- top bar,
- footer,
- route rendering.

`App.tsx` is now the Home route surface. It no longer owns another route parser, language state, theme state, active-character selection, sidebar, top bar, footer, or route switch.

This removes the previous split where Home mounted a second shell and reset language to Japanese when the user returned from another route.

## Routes

The shared shell recognizes:

```text
#/home
#/observation
#/communication
#/pod
#/adoption
#/settings
```

An unknown hash resolves to `#/home` semantics.

All route surfaces receive language and character state from the shared shell rather than creating a second owner.

## Navigation lock

Communication, Pod, and Memory Inspector report their bounded operation lock to the shared shell.

```text
feature operation opens
  -> shared shell records locked route
  -> character selector is disabled
  -> other sidebar routes are disabled
  -> direct hash change to another route is rejected
  -> hash is restored to the locked route
  -> feature operation completes or cancels
  -> shared lock is released
```

The lock prevents a URL hash write from bypassing the visible navigation controls. Theme and language remain display-only controls and may still be changed while an operation preview is open.

The lock owner is a single route value rather than three independent shell booleans. Stable callbacks are passed to feature routes so feature effects are not reset by callback identity changes.

## Character scope

Home chat entries and composer drafts are keyed by `characterId`.

Communication, Pod, and Memory Inspector route components are keyed by the active character. When switching characters while no bounded operation is active, route-local candidate, timeline, preview, or session state is remounted instead of being relabeled as another character's state.

Character switching remains disabled while a Communication session, Pod candidate, or Memory Inspector operation preview holds the shared lock.

## Settings surface

`#/settings` provides a mock projection of:

- registered characters and the active selection,
- RelayLM endpoint label and state,
- local model endpoint and model label,
- TTS adapter state and capability,
- avatar adapter state and capability,
- current theme and language,
- runtime capability summary,
- content-free diagnostics status,
- external OpenAI-compatible peer configuration draft.

The runtime states demonstrate `configured`, `unconfigured`, `offline`, and `degraded` presentation. They are mock projections and are not treated as network probe results.

## External peer draft

The external peer form accepts only:

- endpoint label,
- endpoint URL,
- model label,
- adapter capability label.

Submitting the form creates a browser-local preview. Reset returns the local draft to mock defaults.

It does not:

- call `/lab/api/*`,
- contact the endpoint,
- validate the endpoint through a backend,
- write a configuration file,
- persist the draft,
- start a process,
- mutate RelayLM runtime state.

## Credential boundary

No API key or secret field exists in the UI-A6 browser state.

The Settings surface explicitly projects:

```text
credential owner = RelayLM server / adapter process
browser state = not loaded in browser
localStorage = never used for credentials
```

The browser does not receive, display, log, preview, or persist credential values. Endpoint labels and URLs are configuration metadata only; they do not grant authority or prove connectivity.

Existing theme and active-character display preferences may continue to use their pre-existing non-secret `localStorage` entries. The external peer draft and all credential-related state do not use `localStorage`.

## Content-free diagnostics

The diagnostics card contains only bounded mock metadata:

- diagnostics mode,
- projected event count,
- loaded credential-field count.

It does not contain:

- prompt text,
- conversation text,
- memory summaries,
- SOUL source content,
- raw traces,
- request or response bodies,
- credentials.

## Authority boundary

UI-A6 remains presentation and interaction only.

The browser is not authoritative for:

- SOUL,
- MEM,
- RelayRUN,
- RelaySLP,
- runtime configuration,
- credentials,
- process lifecycle,
- authoritative connection state,
- persistent character registry.

All Settings states are labeled as mock, projection, browser-local draft, or non-persistent preview.

## i18n and theme

Japanese remains the default display language. English remains a preview catalog.

Settings copy is separated into `src/locales/settings.ts`. The route supports both light and dark themes through shared design tokens and does not create a second theme owner.

## Validation

The SOUL Lab workflow runs:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run build
```

Manual review should verify:

1. language, theme, and active character remain unchanged across all routes,
2. Home does not mount a second shell,
3. direct hash changes cannot escape an active Communication, Pod, or Memory Inspector lock,
4. character switching does not relabel route-local candidate, session, timeline, or draft state,
5. Settings contains no secret input or credential value,
6. the external peer preview performs no network call and does not use `localStorage`,
7. endpoint and diagnostics projections contain no prompt, conversation, MEM, or SOUL content,
8. UI-A2 through UI-A5 routes remain available.

## Next bounded slice

Real Settings integration remains a separate server-owned slice.

A future contract should define dedicated `/lab/api/*` read projections and narrowly authorized mutation endpoints with:

- server-side credential ownership,
- explicit configuration schemas,
- validation before apply,
- dry-run-first changes,
- content-free diagnostics,
- process and network actions outside browser authority.

UI-A6 does not pre-implement those APIs or their persistence semantics.
