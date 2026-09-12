---
schema_version: 2
id: physical-execution-queue
responsibility: Run RelayLM physical work through one llama.cpp-only one-shot controller and one shared local GPU lease.
mode: execution_control
when_to_use:
  - Before RelayLM v1 or v2 local llama.cpp/GPU physical execution.
  - When multiple LocalCodex tasks may contend for the same local inference resource.
  - When an independently started llama.cpp may already be running.
when_not_to_use:
  - To select LM Studio, vLLM, or another LLM engine.
  - To change experiment science, product semantics, prompts, schemas, seeds, budgets, or interpretation.
  - To retry an already-invoked target transaction.
  - To take over or kill an external llama.cpp process.
authorization:
  repository_writes: prohibited_during_physical_transaction
  provider_calls: target_owner_only
---

# One-shot llama.cpp physical execution

1. Read fresh protected-branch and target owner authority in an isolated checkout.
2. Complete all non-exclusive preparation first: environment, deterministic tests, fixtures/call plan, and treatment-safe hashes.
3. Use the repository target registry at `.ai/physical/llama_cpp_targets.json`.
4. Prefer the public entrypoint:
   `python -m tools.relay_physical_run --target <registered-target>`.
5. For infrastructure-only physical queue qualification, use the registered `infra:queue-smoke` target rather than borrowing a scientific target. Its child must perform zero provider/model/semantic calls.
6. Do not expose or hand-build `tools.physical_execution_queue -- <arbitrary child>` in normal operation.
7. The engine is fixed to llama.cpp and the current single-GPU resource key is fixed to `llama-cpp:local-gpu`.
8. While queued, another cooperative job causes `WAITING_RESOURCE`.
9. After lease acquisition, an external llama.cpp process/listener causes `WAITING_EXTERNAL_RUNTIME`. Never kill or reuse it.
10. The final gate rechecks the exact checkout, interpreter, target module, required distributions, protected branch remote head, and the pushed execution-branch head when present.
11. If authority drifted during the wait, stop before target invocation, release, reprepare, and requeue. The scientific owner remains unspent.
12. Once a scientific target wrapper is invoked, never retry/replay/reseed/fallback through this controller.
13. Preserve the target result unchanged. The queue receipt is infrastructure-only.

A short operator prompt naming the owner/experiment is sufficient; LocalCodex
must resolve the registered target and current target-owned procedure from fresh
repository authority rather than asking the operator to assemble runtime argv.
