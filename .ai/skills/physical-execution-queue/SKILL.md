---
schema_version: 2
id: physical-execution-queue
responsibility: Run RelayLM physical work through one policy-addressed persistent-Python, llama.cpp-only one-shot controller and one shared local GPU lease.
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
2. Use CPython 3.12 as the host bootstrap. Before taking the GPU lease, verify the selected persistent physical Python environment with `python3.12 -m tools.relay_physical_env --status`.
3. If the current policy environment is absent, explicitly initialize it with `python3.12 -m tools.relay_physical_env --prepare`. `--prepare` reuses a matching selected instance and never upgrades it in place.
4. Persistent environments are addressed by the exact `.ai/physical/python_environment_policy.json` SHA-256 under `~/.local/share/relaylm/physical/environments/<policy-sha256>/`. Do not key them by branch name. v1/v2 carrying the same policy may reuse one instance; different policy generations coexist.
5. If the selected instance drifted, stop. Do not silently install/upgrade/repair. A deliberate non-transactional `--rebuild` creates a fresh immutable instance and atomically moves the policy's `current.json` pointer. It does not delete the previous instance underneath an active process.
6. Same-policy prepare/rebuild creation is serialized by a policy-specific local `flock`.
7. Use the branch-local repository target registry at `.ai/physical/llama_cpp_targets.json`. The common runner requires exact `schema_version=1`, `engine=llama.cpp`, and `resource_key=llama-cpp:local-gpu` before consuming it.
8. Prefer the public entrypoint: `python3.12 -m tools.relay_physical_run --target <registered-target>`. Do not assume a generic `python` alias exists.
9. The runner automatically re-execs through the selected persistent physical Python and gives target children an exact checkout-only `PYTHONPATH` plus `PYTHONNOUSERSITE=1`.
10. For infrastructure-only qualification, use `infra:queue-smoke`; it performs zero provider/model/semantic calls.
11. Do not expose or hand-build `tools.physical_execution_queue -- <arbitrary child>` in normal operation.
12. The engine is fixed to llama.cpp and the shared resource key is `llama-cpp:local-gpu`.
13. While queued, another cooperative job causes `WAITING_RESOURCE`.
14. After lease acquisition, an external llama.cpp process or a target listener address that is not presently bindable causes `WAITING_EXTERNAL_RUNTIME`. Never kill or reuse it. Bindability, not only successful TCP connection, is the controller-side listener criterion because the target must be able to acquire that exact address before its owned server launch.
15. Quiescence requires the configured consecutive idle confirmations before final preflight.
16. The final gate rechecks checkout/ref authority and the selected persistent Python executable, policy digest, installed-distribution fingerprint, target module, and required distributions.
17. After that potentially slow final gate, the controller checks external process/port availability again immediately at the invocation boundary. If busy state appeared during final preflight, do not invoke the child; return to `WAITING_EXTERNAL_RUNTIME`, regain stable quiescence, and rerun final preflight.
18. If any authority or selected environment identity drifted during the wait, stop before target invocation, release, reprepare, and requeue. The scientific owner remains unspent.
19. A policy-pointer switch after the final gate does not delete the frozen old interpreter because rebuild is non-destructive. The exact selected interpreter/fingerprint remains part of the run evidence.
20. The target retains its own fail-closed listener check as defense in depth. An arbitrary non-cooperating process can still race after the controller's last observation; the controller cannot make external TCP ownership atomic without changing the target lifecycle contract.
21. Once a scientific target wrapper is invoked, never retry/replay/reseed/fallback through this controller.
22. Preserve the target result unchanged. Queue receipts and Python-environment fingerprints are infrastructure-only.
23. Treat `.ai/physical/llama_cpp_targets.json` as branch-local carriage data, not as branch-neutral common-generation identity. Common HOW must not absorb `v1:*` / `v2:*` target science or THIS-RUN spend policy.

A short operator prompt naming the owner/experiment is sufficient. LocalCodex
must resolve the target and current target-owned procedure from fresh authority;
the operator does not hand-build Python, httpx, server, model, port, HOME, lock,
or wrapper argv.
