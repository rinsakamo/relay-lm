# OpenWebUI + RelayLM + LM Studio Manual Smoke Result (2026-05-26)

## Scope

- real manual smoke result record
- OpenWebUI -> RelayLM -> LM Studio path verification
- docs-only result record
- no runtime code change

## Environment

- date: 2026-05-26
- host/runtime: Windows host + WSL2
- RelayLM run mode: local venv
- LM Studio backend model: `qwen3.5-9b-ud-japanese-imatrix`
- OpenWebUI runtime: Docker container

## Network notes

- WSL could not initially reach Windows-side LM Studio via `127.0.0.1`.
- Windows Firewall / local network access adjustment was required before WSL -> Windows LM Studio access succeeded.
- LM Studio was reachable from WSL at `http://172.27.96.1:1234/v1` during this run.
- OpenWebUI container reached RelayLM through WSL IP `http://172.27.108.166:8090/v1` during this run.
- WSL IP values can change after restart; treat these addresses as run-specific observations.

## RelayLM checks

- RelayLM startup: Uvicorn running on `http://0.0.0.0:8090`.
- `/v1/models`: pass
  - returned:
    - `relaylm-code-reviewer`
    - `relaylm-companion`
    - `relaylm-work-assistant`
- non-stream (`POST /v1/chat/completions`, `relaylm-companion`): pass
  - backend model: `qwen3.5-9b-ud-japanese-imatrix`
  - response example: `Hello! It's nice to see you again. How has your day been going so far?`
- stream (`POST /v1/chat/completions`, `relaylm-companion`): pass
  - SSE `data:` chunks observed
  - final `data: [DONE]` observed

## OpenWebUI checks

- initial misconfiguration: RelayLM was configured under Tools / OpenAPI-style endpoint, which resulted in `/v1/openapi.json` 404.
- correction: configure RelayLM as an OpenAI-compatible connection.
- initial API mode/path issue: OpenWebUI attempted `/v1/responses`, which resulted in 404.
- correction: switch to Chat Completions / OpenAI-compatible chat completion path.
- final chat check: message to `relaylm-companion` succeeded.
- observed hello result: `Hello! It's nice to see you again. How is your day going so far?`

## Route differentiation result

Prompt used:

> I have too many tasks and limited time this week. Help me decide what to do first and what to defer.

Observed behavior by route:

- `relaylm-companion`
  - warm / supportive / continuity-oriented
  - acknowledges stress and asks for task list, non-negotiables, urgency/impact
- `relaylm-work-assistant`
  - conclusion-first
  - one-big-thing framing
  - assumptions / triage logic / execution path / recommended action plan
- `relaylm-code-reviewer`
  - risk-aware framework
  - impact vs effort
  - strict deferral criteria
  - validation command / blocker-oriented checks

Verdict: pass

## Failure / troubleshooting notes

Troubleshooting guide: [OpenWebUI + RelayLM + LM Studio troubleshooting](openwebui_lmstudio_troubleshooting.md).

- Windows Firewall can block WSL -> Windows LM Studio connectivity.
- `host.docker.internal` may not reach WSL RelayLM depending on environment; WSL IP may be required.
- Tools/OpenAPI endpoint configuration is incorrect for RelayLM chat usage.
- Responses API mode/path is not currently supported by RelayLM; use Chat Completions.

## Final verdict

- overall verdict: pass
- checks:
  - `/v1/models`: pass
  - non-stream via RelayLM: pass
  - stream via RelayLM: pass
  - OpenWebUI -> RelayLM -> LM Studio chat: pass
  - route-specific response differentiation: pass
- next follow-up:
  - MVP-23 summary
  - optional troubleshooting refinement docs
