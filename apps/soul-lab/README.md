# SOUL Lab UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity.

The current bounded UI implementation covers UI-A0 through UI-A7:

- TypeScript + React + Vite foundation,
- Japanese-default message catalogs with English preview catalogs,
- light and dark themes,
- one shared shell owner for route, language, theme, active character, navigation lock, top bar, sidebar, footer, and route rendering,
- persistent active-character selector,
- mock-driven Home conversation surface,
- character-scoped mock sessions and memory outcomes,
- content-free runtime status projection,
- recent event summary,
- first-launch / No Active Character route,
- Lab Assistant guided entry,
- browser-local New Character draft,
- RelaySOUL persona source-set adoption draft,
- `SOUL.md` import composition with explicit `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md` handling,
- mock-driven Communication with explicit RelayLM, external OpenAI-compatible, and Lab Assistant peer types,
- autonomous mock exchange loop without per-message user approval,
- Soft Stop as the normal communication close boundary,
- two-step emergency stop as an explicit exception,
- content-free communication timeline,
- mock-driven Pod / SOUL Intervention workflow,
- bounded intervention targets and locked protected traits,
- human-readable candidate summary and SOUL diff projection,
- one browser-local comparison,
- Hold and Discard decisions,
- non-executing Apply and Rollback previews,
- content-free intervention timeline,
- formed / held / blocked Memory Inspector outcomes,
- bounded source, gate, store, and subjective-perspective projections,
- browser-local Correct and Merge previews for formed or held outcomes,
- browser-local Forget, Pin, and Unpin previews for formed memory,
- browser-local Discard preview for an unpromoted held candidate,
- explicit destructive-preview confirmation for formed-memory Forget,
- content-free memory-inspection timeline,
- shared Settings / Runtime Boundary route,
- read-only `GET /lab/api/settings` runtime-config projection,
- read-only `GET /lab/api/characters` character-registry projection,
- strict browser-side schema validation before server data is displayed,
- explicit loading, server-owned, and mock-fallback source states,
- server-side endpoint redaction and credential exclusion,
- RelayLM, backend, TTS, and avatar endpoint / capability projections,
- content-free diagnostics summary,
- browser-local external OpenAI-compatible peer configuration preview only in mock fallback,
- hash-route enforcement while Communication, Pod, or Memory Inspector holds the navigation lock.

UI-A7 connects only to the two read-only Lab management endpoints. It intentionally does **not** inspect source locations, read source contents, create character files, write settings, test backend connectivity, send peer communication requests, mutate RelayRUN or RelaySLP, write SOUL or MEM, apply a SOUL candidate, execute rollback, execute a memory operation, read or store credentials, probe endpoints, start processes, execute TTS, or control an avatar.

## Requirements

- Node.js 22.12 or newer
- npm
- RelayLM running on `127.0.0.1:8090` for the connected UI-A7 projection

## Development

Start RelayLM from the repository root with a valid config:

```bash
source .venv/bin/activate
relaylm --config config.yaml
```

Then start Vite:

```bash
cd apps/soul-lab
npm install
npm run dev
```

Vite listens on `http://127.0.0.1:5173/lab/` and proxies `/lab/api/*` reads to `http://127.0.0.1:8090`.

Direct routes:

```text
http://127.0.0.1:5173/lab/#/home
http://127.0.0.1:5173/lab/#/adoption
http://127.0.0.1:5173/lab/#/observation
http://127.0.0.1:5173/lab/#/communication
http://127.0.0.1:5173/lab/#/pod
http://127.0.0.1:5173/lab/#/settings
```

When both Lab API responses pass exact schema validation, Settings shows the server-owned projection. If either request fails or returns an invalid schema, Settings explicitly labels and displays the UI-A6 browser-local mock fallback.

## Validation

```bash
npm run typecheck
npm run build
```

The server projection smoke is run from the repository root:

```bash
python scripts/relaylm_soul_lab_management_projection_smoke.py
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. Serving that bundle from RelayLM remains a later bounded slice; UI-A7 adds the read-only management APIs and development proxy only.

## Authority boundary

The browser is presentation and interaction only. It must not become the authority for SOUL, MEM, RelayRUN, RelaySLP, peer transport, intervention apply, rollback, memory correction, forgetting, held-candidate discard, pinning, merging, runtime configuration, persistent character registry, authoritative connection state, process lifecycle, backend credentials, source inspection, or persistence decisions.

The server projections contain configuration metadata and booleans only. They exclude API keys, URL credentials, URL query/fragment data, persona source paths, persona source contents, memory source paths, trace paths, raw traces, prompt text, and conversation text. Theme and the selected mock character may use existing non-secret display-preference storage; credentials and configuration drafts must not use `localStorage`.
