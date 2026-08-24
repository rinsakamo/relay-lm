# Pass 2 Protocol Failure Diagnostic Boundary

Status: current #1533 contract for separating ordinary-turn failure semantics from #1386 diagnostic evidence.

## Runtime authority

Canonical two-pass runtime keeps the existing terminal failure contract:

```text
Pass 1 accepted
Pass 2 provider/parser exception
  -> TwoPassExtractionResult.status = failed
  -> failure_reason = pass2_failed
  -> no State/Continuity mutation from the failed Pass 2
```

The runtime result does not expose provider response bodies, parser exception chains, or other semantic payload merely to make a failed extraction diagnosable. A valid Pass 1 remains valid.

No diagnostic path may loosen RelayLM JSON/scaffold/candidate parsing, source checks, deterministic validation, stale guards, or commit semantics.

## Diagnostic evidence

#1386 may explicitly instrument an actual-model run and retain a separate non-authoritative protocol diagnostic sidecar containing facts observed for the failed Pass 2 attempt, including:

- successful upstream HTTP status and exact response text when available;
- provider message content, finish reason, and usage metadata when extractable from that response;
- the exact provider/parser exception type/message chain observed before runtime collapses it to `pass2_failed`.

This sidecar is evidence only. It is not `CognitionExtractionOutput`, accepted State, Continuity, source authority, or a new runtime failure taxonomy.

## Isolation

Protocol diagnostics must preserve the exact prompt, pass request, capacity/window, reasoning/decoding controls, provider/parser acceptance rules, source semantics, and scenario trajectory being diagnosed. They must not retry, repair malformed model output, add reasoning, or change the Stage R window.

A diagnostic for one failed attempt must not reuse an HTTP response or exception from an earlier successful or failed turn.

## Ownership

#1533 owns the stable two-pass provider/parser failure semantics above.

#1386 owns explicit actual-model observation, immutable diagnostic sidecars, and the decision about what further bounded experiment is justified by those observations.

> Diagnose a failed Pass 2 without turning diagnostic payload into product authority.
