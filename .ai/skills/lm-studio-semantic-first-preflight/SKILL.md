---
schema_version: 1
id: lm-studio-semantic-first-preflight
responsibility: Apply the v2 host-owned physical-execution ownership boundary to RelayLM v1 LM Studio semantic-first qualification without adding provider HTTP preflight.
mode: execution_preflight
when_to_use:
  - Before RelayLM v1 LM Studio semantic-first actual-model qualification or a child diagnostic that depends on it.
  - When assembling declared stable model/runtime/context/reasoning facts for a repository-owned semantic-first host.
when_not_to_use:
  - To probe LM Studio with model-list, health, dummy completion, reasoning, or capability HTTP requests before semantic work.
  - To add a controller-side capability gate that duplicates the host/request boundary.
  - To retry or repair a bounded transaction after host entry.
required_authority:
  - .ai/README.md
  - .ai/agent-contract.yaml
  - docs/reference/development-workflow.md
  - docs/reference/actual-model-lm-studio-semantic-first.md
  - The selected actual-model owner and its current canonical surfaces.
authorization:
  repository_writes: prohibited_during_physical_transaction
  provider_calls: only_from_repository_host_after_host_entry
---

# LM Studio semantic-first preflight

This procedure ports the ownership invariant crystallized on RelayLM v2 physical execution:

> **Controller observes and assembles. Host validates and freezes.**

For the v1 LM Studio release-reference path, provider HTTP preflight remains zero. Stable non-secret binding facts are declared from current operator/local evidence; the repository-owned semantic-first host owns actual provider entry and actual runtime evidence.

## Controller setup

Before host invocation, the controller may:

- reconstruct fresh repository and Issue authority;
- select an isolated exact clean checkout;
- assemble current stable non-secret model, loaded-instance, artifact/tokenizer when available, quantization, context, and reasoning declarations from non-provider-HTTP local/operator evidence;
- create fresh empty workspace/artifact roots;
- validate deterministic argument shape and repository identity.

The controller must not:

- call `/api/v1/models`, `/v1/models`, health endpoints, dummy completions, dedicated reasoning probes, or capability probes;
- treat an absence-of-attestation descriptor as a negative live capability fact;
- call a generic provider capability descriptor to decide whether an explicit production request may be attempted;
- duplicate parsing, Validator, semantic acceptance, or runtime realization checks owned by the host/provider request path;
- restart, reload, swap, tune, or repair the serving treatment to obtain admission.

## Host boundary

Invoke the selected repository-owned semantic-first host at most once for the bounded transaction.

The host owns:

```text
exact repository / static argument validation
-> explicit production Pass request construction
-> first actual semantic provider request
-> provider response / native schema realization
-> passive completion evidence
-> production parser / source validation / Validator
-> execution and boundary evidence
```

An explicit `structured_output_mode=NATIVE` request is therefore tested by the real Pass 2 request. A generic descriptor that says `structured_output=false` because no independent attestation source exists is not an admission veto.

## Exactly-once behavior

Before host entry, deterministic controller-assembly defects may be corrected without spending the physical transaction, provided provider calls and semantic calls remain zero.

After host entry, do not retry, replay, reseed, rescue the schema, relax the parser/Validator, change reasoning, restart/reload/swap the provider, or invoke the same bounded host again.

## Runtime evidence

Declared facts are not completion evidence. Provider reachability, native request realization, finish reason, effective reasoning OFF, parser/source validity, and semantic results come from the actual semantic transaction.

When a real semantic request fails, preserve that failure under the selected owner contract. Do not move equivalent request work into controller setup on the next attempt.

## Child harness rule

Any evaluation/diagnostic harness that depends on `lm_studio_semantic_first_qualification` inherits this ownership boundary.

It may change only its owner-authorized diagnostic surface. It must not introduce a new controller-side or pre-provider capability/admission gate around the semantic-first host.

> **Do not implement a second host outside the host.**
