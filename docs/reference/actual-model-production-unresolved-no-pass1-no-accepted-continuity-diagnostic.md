# Production unresolved-only no-Pass1 without accepted Continuity context

This evaluation-only v1 diagnostic isolates factor B from #2616 after #2700.
It is not a production runtime mode and authorizes no model execution by itself.

## Scientific delta

The baseline is the merged #2700 retained-formation unresolved-only/no-Pass1
request. T1 still runs normally and its accepted Continuity is used by the
canonical T2 compiler, including active-State selection. Only after that
compilation does the treatment remove the projected accepted-Continuity
`ContextItem` prefix from the model-facing T2 `CognitiveInput.context`.

The treatment therefore keeps fixed:

- the exact already-selected T2 State and state classes;
- every non-context CognitiveInput field;
- ordinary user/assistant working context and its order/provenance;
- the #2700 no-Pass1 condition;
- unresolved-only projection semantics and response schema;
- retained #2529 formation overlay and run-local provenance rebound;
- decoding/reasoning controls and canonical parser/source validation.

## Canonical object boundary

Current canonical compilation emits:

```text
CognitiveInput.context
  = projected accepted Continuity ContextItems
  + ordinary working-context ContextItems
```

Projected accepted Continuity items have `actor=None`, canonical
`{"continuity": ...}` JSON semantic content and preserved sources. Ordinary
working-context items have `actor=user|assistant`.

The diagnostic works on this already-compiled typed tuple. It fails closed unless
the prefix is non-empty and canonical and the remaining suffix contains only
ordinary working-context actors. It then uses dataclass-level `context`
replacement. It never recompiles T2 with `continuity_context=None`, never deletes
serialized prompt substrings and never changes State selection.

## Factor evidence

The factor receipt preserves the #2700 baseline/treatment hashes and proves:

- both diagnostic Pass2 requests contain no Pass1 response component;
- selected State and every non-context CognitiveInput field are identical;
- the ordinary working-context suffix is identical;
- unresolved projection, retained overlay, response schema and non-projection
  request fields are identical;
- the exact removed ContextItems are retained;
- the only new removed model-facing responsibility is
  `accepted_continuity_context`.

Full serialized baseline and treatment CognitiveInput objects are retained by the
future physical host.

## Interpretation

A later mechanically valid exactly-once physical transaction is interpreted only
as:

- a valid unresolved set appears: supports model-facing accepted lifecycle
  context as a suppressive factor under the unresolved-only/no-Pass1 condition;
- valid `[]` or material misprojection remains: rejects factor B as sufficient
  and routes next to remaining full-CognitiveInput/instruction-volume burden;
- authority, provenance, protocol, reasoning or transport invalid: no causal
  inference.

A positive diagnostic result does not authorize permanent production removal of
Continuity context.

## Shared infrastructure boundary

Generic one-shot execution, persistent Python, queue/resource ownership, GPU and
process lifecycle, fresh-ref revalidation and target dispatch remain owned by
#2660 shared physical infrastructure.
