# SOUL Lab UI

`apps/soul-lab` is the browser-based local interface for RelayLM character continuity.

The current bounded implementation covers UI-A0 through UI-A7, Phase I-2, Phase I-3, and UI-B0:

- TypeScript + React + Vite foundation,
- Japanese-default message catalogs with English preview catalogs,
- light and dark themes,
- one shared shell owner for route, language, theme, active character, navigation lock, top bar, sidebar, footer, and route rendering,
- persistent active-character display preference,
- exact server-projected character records from `GET /lab/api/characters`,
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
- first-launch / No Active Character route,
- Lab Assistant guided entry,
- browser-local New Character draft,
- RelaySOUL persona source-set adoption draft,
- mock-driven Communication and Pod surfaces,
- formed / held / blocked Memory Inspector outcomes,
- shared Settings / Runtime Boundary route,
- loopback-only read access to `GET /lab/api/settings`,
- strict browser-side management and observation schema validation,
- server-side endpoint redaction and credential exclusion,
- hash-route enforcement while Communication, Pod, or Memory Inspector holds a navigation lock.

UI-B0 does not create a new route, character, SOUL, memory, prompt, credential, backend, or worker authority. The browser sends only the server-projected route model and standard user/assistant history to the same-origin RelayLM endpoint. Existing RelayLM character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and RelaySLP boundaries remain unchanged.

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
http://127.0.0.1:5173/lab/#/adoption
http://127.0.0.1:5173/lab/#/observation
http://127.0.0.1:5173/lab/#/communication
http://127.0.0.1:5173/lab/#/pod
http://127.0.0.1:5173/lab/#/settings
```

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
npm run build
```

Repository validation includes:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i2_lab_observation_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_config_smoke.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

The production bundle is written to `apps/soul-lab/dist/` with a `/lab/` asset base. Serving that bundle from RelayLM remains a separate bounded slice.

## Authority boundary

The browser is presentation and interaction only. It is not the authority for SOUL, MEM, RelayRUN, RelaySLP, worker execution, memory namespaces, backend selection, peer transport, intervention apply, rollback, memory governance, runtime configuration, persistent character registry, process lifecycle, backend credentials, source inspection, or persistence decisions.

Server projections and bounded observation responses exclude API keys, URL credentials, source paths/content, raw traces, prompt text, compiled context, and protected source. Conversation transcripts remain browser-process-local and are not written to `localStorage`.