---
schema_version: 2
id: physical-execution-queue
responsibility: Run RelayLM physical work through one persistent-Python, llama.cpp-only one-shot controller and one shared local GPU lease.
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
2. Before taking the GPU lease, verify the persistent physical Python environment with `python3.12 -m tools.relay_physical_env --status`.
3. If it is absent, explicitly initialize it once with `python3.12 -m tools.relay_physical_env --prepare`. `--prepare` reuses a matching environment and never upgrades it.
4. If the environment exists but drifted, stop. Do not silently install/upgrade/repair. Only a deliberate non-transactional `--rebuild` may replace it.
5. The default shared local environment is `~/.local/share/relaylm/physical/venv`; v1 and v2 reuse it.
6. Use the repository target registry at `.ai/physical/llama_cpp_targets.json`.
7. Prefer the public entrypoint: `python -m tools.relay_physical_run --target <registered-target>`.
8. The runner automatically re-execs through the persistent physical Python and gives target children an exact checkout-only `PYTHONPATH` plus `PYTHONNOUSERSITE=1`.
9. For infrastructure-only qualification, use `infra:queue-smoke`; it performs zero provider/model/semantic calls.
10. Do not expose or hand-build `tools.physical_execution_queue -- <arbitrary child>` in normal operation.
11. The engine is fixed to llama.cpp and the shared resource key is `llama-cpp:local-gpu`.
12. While queued, another cooperative job causes `WAITING_RESOURCE`.
13. After lease acquisition, an external llama.cpp process/listener causes `WAITING_EXTERNAL_RUNTIME`. Never kill or reuse it.
14. The final gate rechecks checkout/ref authority and the persistent Python executable, policy digest, installed-distribution fingerprint, target module, and required distributions.
15. If any authority or environment identity drifted during the wait, stop before target invocation, release, reprepare, and requeue. The scientific owner remains unspent.
16. Once a scientific target wrapper is invoked, never retry/replay/reseed/fallback through this controller.
17. Preserve the target result unchanged. Queue receipts and Python-environment fingerprints are infrastructure-only.

A short operator prompt naming the owner/experiment is sufficient. LocalCodex
must resolve the target and current target-owned procedure from fresh authority;
the operator does not hand-build Python, httpx, server, model, port, HOME, lock,
or wrapper argv.
