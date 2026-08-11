---
relaylm_doc_type: operations
relaylm_authority: p0_mobile_dogfood_entry_target_boundary
relaylm_status: target
relaylm_volatility: high
relaylm_owner: operations
relaylm_update_trigger:
  - a dedicated chat-only origin is implemented
  - external path allowlist or reverse-proxy behavior changes
  - production Character Workspace bundle serving changes
  - Cloudflare exposure procedure is validated end to end
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - Cloudflare product documentation
  - production multi-user access control
  - RelayLM runtime behavior
  - MEM/SOUL mutation authority
  - public deployment security guarantee
---
# P0 Mobile Dogfood Entry

## Current readiness

```text
single-owner mobile dogfood target: defined
safe dedicated chat-only public origin: not implemented or identified in this repository
current Vite Character Workspace development server: local development only
RelayLM static Character Workspace bundle serving: not implemented
Cloudflare Tunnel publication from this runbook: blocked until the acceptance gates below pass
```

Do not expose the Vite development server, the full Character Workspace / SOUL Lab surface, RelayLM `/v1`, LM Studio, or any management/debug endpoint through Cloudflare Tunnel based on this document. The earlier wording "chat-only UI" did not identify a concrete process, port, or path boundary and therefore was not an executable safe runbook.

## Purpose

This document defines the target boundary for a future single-owner mobile dogfood entry that lets the operator converse with ReLM from a smartphone while keeping RelayLM management, memory governance, backend, and debug surfaces private.

Actual Cloudflare secrets, real domains, email addresses, tunnel IDs, credentials, and credential paths must never be committed.

## Single-owner boundary

The target operation is for the primary operator only. It does not include:

- family testers;
- multiple actors or actor identification;
- family namespaces;
- per-actor memory modes;
- public SaaS operation;
- shared account administration.

Multi-user use requires a separate identity, authorization, namespace, and memory-isolation design.

## Required dedicated public origin

Before this runbook may become `current`, the repository or deployment must provide one concrete public origin that satisfies all of the following:

1. It serves conversation UI only.
2. Its exact start command or supervised service is documented.
3. Its exact loopback host and port are documented.
4. Its allowed URL paths are enumerated.
5. `/v1`, `/lab/api`, Advanced/management routes, Memory Inspector, admin/debug routes, raw artifacts, and filesystem access are unreachable through that origin.
6. It does not depend on exposing the Vite development server.
7. It does not expose LM Studio or backend credentials to the browser.
8. An end-to-end external negative test proves every forbidden path is blocked.

A generic placeholder such as `<chat-ui-port>` is not sufficient to satisfy this boundary.

## Current local UI facts

The current browser Character Workspace development flow is:

```text
relaylm --config config.yaml                 # loopback RelayLM + management API
cd apps/soul-lab && npm run dev              # Vite development server
http://127.0.0.1:5173/lab/                   # full local Character Workspace
```

This is a local development arrangement. The full surface includes Create, Character, Scenes, Relationships, Memory Wiki, Runtime, and Advanced. It is not the dedicated chat-only public origin required above. The production bundle under `apps/soul-lab/dist/` is not currently served by RelayLM.

## Target topology

Only after a dedicated origin exists:

```text
smartphone browser
  -> Cloudflare Access
  -> Cloudflare Tunnel
  -> dedicated chat-only origin on loopback
  -> RelayLM conversation endpoint through an internal hop
  -> local backend / LM Studio
```

The home router and firewall should not require inbound port forwarding. The tunnel connects outward from the local environment.

## Public and forbidden surfaces

### May be public after acceptance

- the dedicated chat-only origin only;
- only its explicitly documented conversation paths.

### Must remain unreachable externally

- RelayLM `/v1` OpenAI-compatible API;
- RelayLM `/lab/api` management and observation APIs;
- full Character Workspace / SOUL Lab routes other than the approved chat-only origin;
- Memory Inspector and Advanced governance controls;
- LM Studio, including port `1234` or any backend API;
- admin/debug endpoints;
- local file browsing;
- raw runtime, queue, trace, audit, MEM, SOUL, REL, or SCENE artifacts;
- Vite development tooling and development websocket endpoints.

## Cloudflare Access policy target

When the dedicated origin exists:

- allow exactly the primary operator identity;
- require Access authentication before the tunnel route is considered usable;
- validate the Access token at the protected origin or through a verified equivalent boundary;
- leave no public hostname active when Access protection is disabled;
- stop both the tunnel route and the protected origin when suspending external access.

Cloudflare product configuration details remain governed by current Cloudflare documentation, not this repository.

## Placeholder tunnel shape

The following remains a non-executable example until `<dedicated-chat-origin-port>` is replaced by the documented accepted origin:

```yaml
# cloudflared config.yml -- placeholders only
# Do not commit real values.
tunnel: <tunnel-id-placeholder>
credentials-file: /path/to/placeholder-credentials.json

ingress:
  - hostname: chat.example.com
    service: http://127.0.0.1:<dedicated-chat-origin-port>
  - service: http_status:404
```

Do not point this service at RelayLM `:8090`, LM Studio `:1234`, or Vite `:5173`.

## Acceptance tests required before external use

Record the exact command, expected status, and result for each test:

```text
[ ] unauthenticated request to public hostname is rejected
[ ] non-owner identity is rejected
[ ] approved owner reaches the chat-only page
[ ] direct /v1 request is rejected
[ ] /lab/api request is rejected
[ ] Advanced / management / Memory Inspector route is rejected
[ ] LM Studio is unreachable externally
[ ] Vite development endpoints are unreachable externally
[ ] browser receives no backend credential
[ ] tunnel shutdown removes external reachability
[ ] no real secret, domain, email, tunnel ID, or credential path is committed
```

The document may be changed from `target` to `current` only after these tests have concrete evidence for the chosen deployment.

## Stop procedure target

Once a dedicated origin is in use, stop external reachability in this order:

1. stop the dedicated chat-only origin;
2. stop the local `cloudflared` process/service;
3. disable or remove the tunnel public-hostname route;
4. disable the Access application;
5. remove or disable the associated DNS/public-hostname record;
6. verify the hostname and every forbidden path are unreachable externally.

Do not leave the tunnel active without Access protection or Access configured for an origin that is no longer controlled.

## Dogfood observation scope

After safe access exists, observe:

- conversation quality in short daily interactions;
- natural or inappropriate memory recall;
- memory under-recall and over-recall;
- perceived response latency;
- robustness to short and rough smartphone input.

Use the [Mobile Dogfood Observation Method](../operations/mobile-dogfood-observation.md) for local-only daily and weekly records. Content-bearing transcripts remain outside the repository.

## Non-goals

- implementing the dedicated chat-only origin in this document;
- user management or family tester support;
- Cloudflare API automation;
- public SaaS deployment;
- changing RelayLM runtime or MEM/SOUL behavior;
- designing secret storage;
- TTS, avatar, or ASR support.

## Related authority

RelayLM runtime status remains in [Project Status](../PROJECT_STATUS.md). Local Character Workspace development steps remain in [`apps/soul-lab/README.md`](../../apps/soul-lab/README.md). This target runbook does not authorize public exposure until its dedicated-origin and acceptance-test requirements are satisfied.
