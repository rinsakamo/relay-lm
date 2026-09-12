# Production-context unresolved-only no-Pass1 diagnostic

This evaluation-only v1 diagnostic isolates one remaining #2616 factor after #2689.
It is not a production runtime mode and does not authorize model execution by itself.

## Scientific delta

The baseline is the merged production-context unresolved-only retained-formation
request. The treatment keeps the same serialized T2 `CognitiveInput`, accepted T1
Continuity context, unresolved-only projection grammar, retained #2529 formed
observation, native response schema, decoding/reasoning controls and source
validation, while omitting only the canonical Pass 1 response component from T2
Pass 2.

The future physical transaction still generates T2 Pass 1 exactly once. Its text is
retained as evidence but is not supplied to the treatment Pass 2 request.

## Construction contract

The implementation must derive the baseline from
`build_unresolved_only_extraction_request_body(...)` and compose the treatment from
canonical exported extraction components. It must not subtract strings from a built
prompt, copy a production prompt, replace provider components at runtime, or teach a
fixture-specific answer.

The factor receipt proves:

- same system instruction;
- same serialized `CognitiveInput`, including accepted Continuity context;
- same unresolved-only projection component;
- same retained formation overlay and run-local provenance rebound;
- same response schema and non-projection request fields;
- baseline contains `extraction_response_component(...)`;
- treatment contains no `<PASS_1_RESPONSE_JSON>` block;
- the only removed model-facing responsibility is `pass1_response_component`.

Both baseline and treatment request-body hashes are retained.

## Interpretation

A later mechanically valid exactly-once physical transaction is interpreted only as:

- treatment emits a valid new `unresolved` set: Pass 1 response conditioning is
  supported as a suppressive factor under the held-fixed condition;
- treatment still emits `[]` or otherwise omits the valid unresolved transition:
  Pass 1 response conditioning is rejected as a sufficient cause and accepted
  lifecycle context is the next factor to isolate;
- authority, provenance, transport or protocol invalid: no causal inference.

No replay of #2689/#2685, formation regeneration, T3, retry, fallback, reasoning
escalation, FastCal, parser/oracle relaxation or production repair belongs to this
component.

## Shared physical infrastructure boundary

Generic one-shot execution, persistent Python environment, queue/resource ownership,
fresh-ref revalidation and target dispatch are owned by the shared physical execution
module introduced by #2660/#2690. Any future v1 physical specialization for this
diagnostic must consume that shared contract rather than duplicate it.
