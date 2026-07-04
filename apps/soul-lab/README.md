# Character Workspace UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity. As of CW-A3, the visible shell is organized as a file-first Character Workspace rather than an internal SOUL Lab administration surface.

The current bounded implementation covers UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0/UI-B1A, I-4E Forget UI, I-5B Pin / Unpin UI, I-7C Held Governance UI, and CW-A3:

- TypeScript + React + Vite foundation,
- Japanese-default message catalogs with English preview catalogs,
- light and dark themes,
- one shared shell owner for route, language, theme, active character, navigation lock, top bar, sidebar, footer, and route rendering,
- persistent active-character display preference,
- exact server-projected character records from `GET /lab/api/characters`,
- top-level Character Workspace routes: Home, Character, Scenes, Relationships, Memory Wiki, Runtime, and Advanced,
- real Home conversation through the existing RelayLM `/v1/chat/completions` path,
- server-owned single-route resolution with fail-closed unavailable/ambiguous states,
- bounded non-stream OpenAI-compatible response parsing,
- bounded UTF-8/SSE streaming parsing and one assistant entry per response,
- explicit `REAL RUNTIME` and `LOCAL PREVIEW` source modes,
- character × source-mode browser-local session separation,
- Stop with partial-text preservation,
- Retry from an exact request snapshot without duplicating the user message,
- New Conversation for only the current character/source session,
- character/session/generation/route stale-response fencing,
- no automatic mock fallback after real runtime failure,
- content-free runtime status projection,
- Phase I-2 latest-run, formed/held/blocked, and used-memory observation,
- Phase I-3 token-gated auditable Correct,
- formed / held / blocked Memory Inspector outcomes,
- existing Correct / Forget / Pin / Unpin / Held Governance details under Advanced,
- loopback-only read access to `GET /lab/api/settings`,
- strict browser-side management and observation schema validation,
- server-side endpoint redaction and credential exclusion,
- hash-route enforcement while Advanced-hosted governance surfaces hold a navigation lock.

CW-A3 does not create a new route, character, SOUL, memory, prompt, credential, backend, worker, source write, or runtime authority. The browser sends only the server-projected route model and standard user/assistant history to the same-origin RelayLM endpoint. Existing RelayLM character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and RelaySLP boundaries remain unchanged.

## Requirements

- Node.js 22.12 or newer
- npm
- RelayLM on loopback, normally `127.0.0.1:8090`
- LM Studio or another configured backend for real conversation, normally `127.0.0.1:1234`

## Development

Start the backend model server, then RelayLM:

```bash
cd ~/work/relay-lm
source .venv/bin/activate
relaylm --config config.yaml
```

Start Vite:

```bash
cd ~/work/relay-lm/apps/soul-lab
npm install --no-audit --no-fund
npm run dev
```

Open:

```text
http://127.0.0.1:5173/lab/
```

Vite proxies both `/lab/api/*` and `/v1/*` to `http://127.0.0.1:8090` with `changeOrigin: false`. The browser never connects directly to LM Studio and receives no backend credential.

Direct routes:

```text
http://127.0.0.1:5173/lab/#/home
http://127.0.0.1:5173/lab/#/character
http://127.0.0.1:5173/lab/#/scenes
http://127.0.0.1:5173/lab/#/relationships
http://127.0.0.1:5173/lab/#/memory
http://127.0.0.1:5173/lab/#/runtime
http://127.0.0.1:5173/lab/#/advanced
```

Legacy SOUL Lab hashes are absorbed instead of becoming new authority:

```text
#/observation   -> Runtime
#/communication -> Advanced
#/pod           -> Advanced
#/adoption      -> Advanced
#/settings      -> Advanced
```

## Character Workspace surfaces

- **Home** keeps the real conversation path and explicit Local Preview separation.
- **Character** shows SOUL.md, STYLE.md, EMOTION.md, BOUNDARY.md, and optional LORE.md as source-status / draft-preview surfaces.
- **Scenes** separates SCENE.md, active scene pages, and scene inbox candidates without ACG-6 runtime classifier execution or auto-merge.
- **Relationships** separates RELATIONSHIP.md vocabulary, target-specific relationship pages, and pending REL proposals without browser-owned role assignment.
- **Memory Wiki** shows memory policy, pages, blocks, retrieval chunks, inbox, archive, and forgotten items using user-friendly vocabulary.
- **Runtime** shows content-free latest used scene/emotion/relationship/memory/context and CW-A2 tier summaries.
- **Advanced** collects internal governance labels, queue/worker/audit diagnostics, and existing explicit loopback controls without increasing browser authority.

## Home conversation behavior

Real Runtime is selected by default. A real request is available only when the active exact server projection has one distinct non-empty `route_models` entry. Zero routes are unavailable; multiple routes are `ambiguous_route` until server-owned priority semantics exist.

The browser request contains only:

```json
{
  "model": "<server-projected route model>",
  "messages": [{ "role": "user", "content": "..." }],
  "stream": true
}
```

It does not send frontend-generated system/developer messages, raw SOUL, raw MEM, compiled context, namespace, backend ID, credentials, paths, or queue identities.

Local Preview is explicit and stores a separate browser-local session. Real runtime failures never switch to preview automatically.

## Validation

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run smoke:lifecycle-visibility
npm run smoke:forget-ui
npm run smoke:pin-unpin-ui
npm run smoke:held-governance-ui
npm run smoke:character-workspace
npm run build
```

Repository validation includes:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a1_file_first_workspace_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a2_workspace_compiler_smoke.py
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. Serving that bundle from RelayLM remains a separate bounded slice.

## Authority boundary

The browser is presentation and interaction only. It is not the authority for SOUL, MEM, RelayRUN, RelaySLP, worker execution, memory namespaces, backend selection, peer transport, intervention apply, rollback, memory governance, runtime configuration, persistent character registry, process lifecycle, backend credentials, source inspection, or persistence decisions.

Server projections and bounded observation responses exclude API keys, URL credentials, absolute source paths/content, raw traces, prompt text, compiled context, and protected source. Conversation transcripts remain browser-process-local and are not written to `localStorage`; CW-A3 does not persist raw source or memory bodies to browser storage.
