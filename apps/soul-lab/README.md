# SOUL Lab UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity.

This first bounded slice implements UI-A0 / UI-A1:

- TypeScript + React + Vite foundation,
- Japanese-default message catalog with an English preview catalog,
- light and dark themes,
- persistent active-character selector,
- mock-driven Home conversation surface,
- content-free runtime status projection,
- recent event summary,
- read-only Lab Observation preview,
- reserved routes for Communication, SOUL Intervention, and Adoption.

It intentionally does **not** connect to RelayLM runtime APIs, write SOUL or MEM, read credentials, execute TTS, or control an avatar.

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

## Validation

```bash
npm run typecheck
npm run build
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. A later RelayLM runtime slice will serve that bundle and provide dedicated `/lab/api/*` management endpoints.

## Authority boundary

The browser is presentation and interaction only. It must not become the authority for SOUL, MEM, RelayRUN, RelaySLP, backend credentials, or persistence decisions. Mock actions in this slice update browser-local React state only.
