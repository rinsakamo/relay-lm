# OpenWebUI + RelayLM + LM Studio Troubleshooting

## Scope

Local setup troubleshooting for:

```text
OpenWebUI -> RelayLM -> LM Studio
```

See [manual smoke runbook](openwebui_lmstudio_manual_smoke.md).

## Connectivity

### WSL to Windows LM Studio

Try loopback first:

```bash
curl http://127.0.0.1:1234/v1/models
```

With default WSL NAT networking, use the Windows host address when loopback is unavailable:

```bash
WIN_HOST=$(ip route show default | awk '{print $3}')
curl http://${WIN_HOST}:1234/v1/models
```

Also verify LM Studio local-network serving and Windows Firewall TCP 1234 rules.

### OpenWebUI container to RelayLM

Test RelayLM locally:

```bash
curl http://127.0.0.1:8090/v1/models
```

From Docker, try `http://host.docker.internal:8090/v1`. If RelayLM runs in WSL, test the WSL address from the container. Binding RelayLM to `0.0.0.0` may be necessary, but it exposes the proxy beyond loopback and requires firewall controls.

SOUL Lab UI-A7 management reads are intentionally different: `/lab/api/settings` and `/lab/api/characters` require both a loopback configured listen host and a loopback transport peer. They return `403` for wildcard, LAN, remote, or unknown-peer access even when Core routes remain available.

## OpenWebUI configuration

Use **Admin Settings -> Connections -> OpenAI**. RelayLM is not a Tools/OpenAPI server.

RelayLM currently supports `/v1/models` and `/v1/chat/completions`. `/v1/responses` is not implemented, so select Standard/Compatible Chat Completions behavior.

## Route and profile checks

Verify that:

- the OpenWebUI model equals a RelayLM `model_routes` key,
- the selected backend exists,
- `backend_model` matches the LM Studio model ID,
- managed routes resolve a configured character,
- `soul`, `output_policy`, and common runtime policy files exist.

Client system prompts are not fallback SOUL sources.

## Unexpected prior history reaches backend

History-exclusion apply remains default-off and dry-run-only by default:

```yaml
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Therefore, default `memory_light` compatibility compilation may still preserve frontend history. This does not prove that current-turn-only reconstruction is active.

The implemented bounded contracts are:

- `client_history_exclusion_apply.v0`: supported no-instruction requests,
- `client_history_exclusion_apply.v1`: supported instruction-bearing requests with explicit provenance.

For v1, a frontend must identify the current instruction message indices through the reserved `relaylm.instruction_evidence` envelope using schema `client_instruction_source.v1`. Role, wording, and message position alone are not accepted as provenance.

Only explicitly selected `system` or `developer` candidates become bounded low-trust evidence. Unselected candidates, including frontend summaries and memory notes, are excluded. The reserved RelayLM control envelope is removed before managed backend forwarding.

A frontend that cannot emit explicit provenance should leave instruction-bearing actual apply disabled or dry-run-only.

## Backend forwarding is blocked

Expected fail-closed causes include:

- missing or invalid explicit instruction provenance,
- duplicate, unordered, out-of-range, post-user, or non-instruction indices,
- mismatch between provenance and request-local instruction identity,
- evidence exceeding the rendered-size bound,
- active tool transaction requiring preservation,
- preflight or compiler prerequisites not ready,
- no exact typed `applied` result,
- downstream mutation of the exact v1 payload candidate.

Do not restore raw prior history or treat every system/developer message as current instruction evidence. Return to dry-run settings and inspect bounded reason IDs.

Explicit `pass_through` routes remain client-owned and unchanged.

## Streaming

Test non-stream first, then test LM Studio direct streaming and proxy connectivity.

Current default streaming remains byte-compatible backend SSE forwarding. When explicitly enabled, Phase 5.5-B2 can wrap request-runtime SSE and suppress complete, split, or terminal-partial internal sentinels. Phase 5.5-C0 through C4 can then create content-free segmentation, TTS handoff, and transport-envelope metadata from B2 safe visible output.

These gates remain default-off and do not deliver adapter transport, execute TTS, generate audio, or control an avatar. A failure in the gated stream path should fail closed without replaying already emitted visible chunks.

## Historical local values

Addresses such as `172.x.x.x:1234` or `172.x.x.x:8090` in old smoke records are run-specific observations, not stable defaults.

## When code changes are appropriate

Consider runtime changes only when Chat Completions reaches RelayLM but RelayLM emits malformed output, a streaming mismatch is reproducible, or current behavior contradicts a typed authority contract. Ordinary firewall, address, connection-mode, and model-ID problems should be fixed in configuration or networking.
