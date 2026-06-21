# SOUL Lab UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity.

The current bounded UI implementation covers UI-A0 through UI-A6:

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
- mock Settings / Runtime Boundary route,
- read-only character registry projection,
- RelayLM, local model, TTS, and avatar endpoint / capability projections,
- browser-local external OpenAI-compatible peer configuration preview,
- explicit server-owned credential boundary,
- content-free diagnostics summary,
- hash-route enforcement while Communication, Pod, or Memory Inspector holds the navigation lock.

It intentionally does **not** connect to RelayLM runtime APIs, inspect source locations, read selected file contents, create character files, send peer network requests, mutate RelayRUN or RelaySLP, write SOUL or MEM, apply a SOUL candidate, execute rollback, execute a memory operation, read or store credentials, validate or write runtime configuration, probe endpoints, start processes, execute TTS, or control an avatar.

## Requirements

- Node.js 22.12 or newer
- npm

## Development

```bash
cd apps/soul-lab
npm install
npm run dev
```

Vite listens on `http://127.0.0.1:5173/lab/`.

Direct routes:

```text
http://127.0.0.1:5173/lab/#/home
http://127.0.0.1:5173/lab/#/adoption
http://127.0.0.1:5173/lab/#/observation
http://127.0.0.1:5173/lab/#/communication
http://127.0.0.1:5173/lab/#/pod
http://127.0.0.1:5173/lab/#/settings
```

## Validation

```bash
npm run typecheck
npm run build
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. A later RelayLM runtime slice will serve that bundle and provide dedicated `/lab/api/*` management endpoints.

## Authority boundary

The browser is presentation and interaction only. It must not become the authority for SOUL, MEM, RelayRUN, RelaySLP, peer transport, intervention apply, rollback, memory correction, forgetting, held-candidate discard, pinning, merging, runtime configuration, persistent character registry, authoritative connection state, process lifecycle, backend credentials, source inspection, or persistence decisions. Mock actions in these slices update browser-local React state only. Theme and the selected mock character may use existing non-secret display-preference storage; credentials and configuration drafts must not use `localStorage`.
