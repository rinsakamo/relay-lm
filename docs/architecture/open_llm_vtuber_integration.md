# Open-LLM-VTuber Integration Design

## Purpose

Open-LLM-VTuber is an optional OpenAI-compatible frontend path:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

The primary local MVP path remains OpenWebUI -> RelayLM -> LM Studio.

RelayLM does not own Open-LLM-VTuber UI, display history, ASR, TTS execution, or avatar execution.

## Current implemented path

Current integration provides:

- `POST /v1/chat/completions`,
- `GET /v1/models`,
- backend model routing,
- non-stream and streaming forwarding,
- compatibility-preserving request handling,
- optional current RelayLM profile compilation.

Current streaming is primarily backend SSE forwarding. Stream Unpack, TTS-safe segmentation, RelayREF, and complete output-side RelaySCN are not implemented.

## Current managed history boundary

Current implementation includes a narrow default-off no-instruction history-exclusion slice:

```text
client_history_exclusion_apply.v0
```

It supports a managed compiled request only when client system/developer instruction messages are absent.

- disabled by default,
- dry-run by default,
- actual apply retains one RelayLM-owned compiled prefix and the validated current user message,
- explicit actual apply blocks backend forwarding when the required applied result is unavailable,
- explicit `pass_through` remains client-authority delegated.

This is not the complete instruction-bearing managed-route target.

## Target managed request path

```text
client request evidence
  -> validated current user turn
  -> bounded current instruction evidence
  -> active transaction preservation check
  -> prior client history exclusion
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

The original frontend message array is not target managed backend context.

## Persona prompt handling

An incoming frontend persona/system prompt is current request evidence, not approved RelaySOUL.

Target handling:

```text
incoming instruction evidence
  -> bounded low-trust scene role/context/constraint evidence
  -> current request behavior

optional explicit import
  -> RelaySOUL initialization/calibration candidate
  -> review and approval
  -> versioned durable persona source
```

Rules:

- do not copy raw frontend prompts into `SOUL.md`,
- do not treat them as stable persona authority,
- do not use them as managed fallback authority,
- approved RelaySOUL remains authoritative over conflicting client persona text.

The bounded instruction-bearing apply path is still required to complete this target behavior.

## History behavior

### Current

- normal proxy forwarding works,
- current no-instruction apply can remove prior client messages only when explicitly enabled,
- instruction-bearing managed requests are outside that apply slice.

### Target

Managed routes use:

- validated current user turn,
- RelayLM-owned selected recent context,
- approved RelayMEM evidence,
- approved RelaySOUL/output/relationship policy,
- normalized RelaySCN state,
- minimum compatible transaction state.

Frontend display history may remain in the frontend UI/storage without becoming backend authority.

## Minimal frontend configuration

Existing users should normally change only the OpenAI-compatible endpoint, API-key placeholder, and route model.

```yaml
llm_configs:
  openai_compatible_llm:
    base_url: http://localhost:8090/v1
    llm_api_key: relaylm
    model: relaylm-mili
```

Basic connection success does not mean target managed history handling or realtime output stages are enabled.

## Compatibility modes

### `pass_through`

Explicit delegated-authority connection/compatibility path. Messages remain client-owned apart from compatible model/header mapping.

### managed modes

RelayLM-owned context compilation. Current behavior is bounded by implemented schemas and feature flags; target behavior additionally requires complete instruction/history authority handling.

## Target realtime output path

```text
backend stream
  -> RelayCTX Stream Unpack
  -> safe output segmentation
  -> RelayREF
  -> Return-side RelayEMO hints
  -> Output-side RelaySCN
  -> approved visible segments
  -> external TTS / Avatar consumers
```

This is target architecture, not current runtime behavior.

Internal markers and malformed candidates must be blocked before external speech/avatar consumers receive them.

## Adapter boundary

RelayLM emits text segments and engine-neutral hints. External adapters map them to TTS and avatar runtimes.

RelayEMO does not call or control external engines directly.

## Required migration and validation

Complete together:

1. instruction-bearing managed history apply,
2. current-turn and active-transaction preservation,
3. Stream Unpack and marker buffering,
4. TTS-safe output segmentation,
5. RelayREF and output-side scene stages,
6. cancellation and duplicate-emission handling,
7. frontend -> RelayLM -> backend -> safe segment -> external adapter smoke.

## Non-goals

- no durable authority from arbitrary frontend prompts,
- no frontend history as canonical managed context,
- no ownership of ASR/TTS/avatar execution,
- no rewriting of tool/structured protocol as persona text,
- no heavy synchronous retrieval by default.
