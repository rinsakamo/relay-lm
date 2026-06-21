# SOUL Lab UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity.

The current bounded UI implementation covers UI-A0 through UI-A3:

- TypeScript + React + Vite foundation,
- Japanese-default message catalogs with English preview catalogs,
- light and dark themes,
- persistent active-character selector,
- mock-driven Home conversation surface,
- character-scoped mock sessions and memory outcomes,
- content-free runtime status projection,
- recent event summary,
- read-only Lab Observation preview,
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
- reserved route for SOUL Intervention.

It intentionally does **not** connect to RelayLM runtime APIs, inspect source locations, read selected file contents, create character files, send peer network requests, mutate RelayRUN or RelaySLP, write SOUL or MEM, read credentials, execute TTS, or control an avatar.

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
http://127.0.0.1:5173/lab/#/adoption
http://127.0.0.1:5173/lab/#/communication
```

## Validation

```bash
npm run typecheck
npm run build
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. A later RelayLM runtime slice will serve that bundle and provide dedicated `/lab/api/*` management endpoints.

## Authority boundary

The browser is presentation and interaction only. It must not become the authority for SOUL, MEM, RelayRUN, RelaySLP, peer transport, backend credentials, source inspection, or persistence decisions. Mock actions in these slices update browser-local React state only.
