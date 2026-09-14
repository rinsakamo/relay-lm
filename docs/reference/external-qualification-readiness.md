# External qualification launch readiness

Status: zero-generation preparation contract for #2821 under the exact-RC gate in #1449.

> Prepare the execution plan before the contender exists; freeze exact external and physical identities before spending benchmark generations.

This surface extends the completed #1981 external-qualification harness. It does not redefine the A/B/C/D evidence contract, RelayLM cognition, benchmark scoring, or release identity.

## Boundary

The repository already owns the architecture-neutral evidence runner in `tools/external_qualification.py` and the MemConflict RelayLM adapter in `tools/memconflict_adapter.py`.

#2821 adds only the pre-execution layer needed to establish that a bounded two-axis release qualification can be launched without discovering missing identities after the exact RC is cut:

- `tools/external_qualification_readiness.py` validates a two-axis launch plan and an eventual exact execution freeze;
- `tools/longmemeval_adapter.py` maps the released LongMemEval `knowledge-update` shape into timestamp-preserving governed transcript ingestion without exposing gold labels to the model;
- `tools/v1_external_qualification_llama_cpp_gate.py` is the zero-generation shared-runner admission gate for a frozen exact-RC plan.

No provider, benchmark question, judge, server, GPU, Crystallization, or FastCal call belongs to this preparation surface.

## Readiness states

`pre_rc_readiness` is valid only without citable release cases. When the plan has at least two distinct axis families, a selected serious-comparator family, a declared physical carriage target, and the no-retry/exact-resume policies, validation returns:

```text
READY_EXCEPT_EXACT_RC
```

This status is explicitly non-citable. Exact comparator revisions, dataset revisions, licenses, and release artifacts remain execution-time facts.

`execution_freeze` is valid only after:

- the benchmark physical carriage is registered;
- every planned axis has one existing #1981 `release_qualification` case + manifest;
- every manifest is citable and binds the same exact #1447 RC;
- the existing A/C/D requirements remain satisfied;
- every case matches its planned benchmark and adapter;
- the serious comparator implementation/source revision/version/license matches the preselected comparator identity across the frozen cases;
- the complete serious-comparator participant identity is identical across axes;
- A and D bind the physical-carriage backend required by the plan.

Only then does validation return:

```text
EXECUTION_FROZEN
```

`assess_launch_readiness(...)` exposes a bounded `BLOCKED` record for invalid or unresolved plans. It never repairs a plan or launches anything.

## Preferred bounded Core 1.0 ring

The following is a preparation choice, not immutable execution authority. Fresh upstream verification is required again immediately before a citable run.

### Axis 1 — conflict / temporal validity

Use a bounded MemConflict-class slice through the already-owned RelayLM adapter. This axis targets stale/conflicting memory selection and temporal applicability.

### Axis 2 — update / belief revision

Use a bounded LongMemEval `knowledge-update` slice. The upstream released format supplies ordered timestamped sessions and distinguishes `knowledge-update` from its temporal-reasoning and other task types.

For Core 1.0 the adapter is deliberately limited to `knowledge-update`. It does not claim support for LongMemEval temporal-reasoning cases whose question-time semantics may require a separate benchmark-boundary decision. This keeps the second release axis materially distinct while avoiding a benchmark-specific mutation to the ordinary RelayLM turn API.

The adapter:

1. validates the released parallel `haystack_session_ids`, `haystack_dates`, and `haystack_sessions` structure;
2. preserves each supplied session timestamp on the model-facing historical messages;
3. preserves supplied user/assistant ordering;
4. strips `has_answer` and all unknown source fields rather than leaking benchmark labels;
5. retains gold answer, answer-session IDs, and question date only in evaluation-reference data;
6. ingests every supplied session exactly once through a caller-provided governed query adapter;
7. freezes the post-history package before the evaluation question.

The future execution controller remains responsible for running each question exactly once through the ordinary frozen-snapshot query path and for passing hypotheses to the exact benchmark-native scorer selected at execution freeze.

## Preferred serious comparator

Preparation-time reconnaissance selects Hindsight as the preferred C-slot family. This is not execution authority.

Do not encode a floating `main`, `latest` container, vendor headline score, or remembered release number as qualification authority. At execution freeze record the exact source revision, version, deployment, license observation, physical model, provider/runtime, decoding/reasoning controls, and unavoidable matched-condition differences in the existing #1981 participant identity.

If Hindsight is no longer reproducible or scientifically matchable before generation begins, #1449 may select a different current serious comparator. Once execution is frozen, comparator switching after observing RelayLM results is not allowed.

## External references to re-verify

Preparation-time references only:

- Hindsight: `https://github.com/vectorize-io/hindsight`
- LongMemEval: `https://github.com/xiaowu0162/LongMemEval`
- independent MemConflict comparison harness: `https://github.com/EngTurtle/hermes-memconflict`

Repository licenses and benchmark/dataset licensing remain execution-time identity fields. Preparation-time observations do not substitute for a fresh citable license/revision check.

## Registered physical admission path

The shared llama.cpp target registry exposes:

```text
target: v1:external-qualification
module: tools.v1_external_qualification_llama_cpp_gate
engine: llama.cpp
resource: llama-cpp:local-gpu
```

The operator-facing admission command is:

```bash
python -m tools.relay_physical_run \
  --target v1:external-qualification -- \
  --plan /absolute/path/to/execution-freeze.json
```

This target is intentionally an **admission gate, not a benchmark executor**. The common physical runner first proves the exact checkout, fresh protected-branch ancestry, persistent Python identity, module origin, and shared-resource queue ownership. The target then requires the plan to validate as `EXECUTION_FROZEN` and requires its physical carriage to be exactly:

```text
target       = v1:external-qualification
backend      = llama.cpp
resource_key = llama-cpp:local-gpu
registered   = true
```

A successful admission emits a bounded receipt containing the readiness fingerprint and exact RelayLM release identity while asserting zero semantic generations, zero benchmark questions, zero judge calls, and zero llama-server launches.

That receipt is not #1449 result evidence and authorizes no generation by itself. The future exact-RC scientific owner must consume fresh authority, the frozen plan, and its own bounded execution ceiling before invoking any A/C/D participant or judge. The gate deliberately does not accept an arbitrary executable or participant command.

The responsibility split remains:

```text
shared physical runner / queue = HOW / admission
benchmark adapters + launch plan = WHAT
future exact-RC benchmark owner = THIS RUN / generation spend
```

Scientific exactly-once ownership stays outside the common runner.

## Hard non-goals

This preparation does not:

- run a moving `v1` as release evidence;
- run any model or judge;
- launch llama-server merely to validate readiness;
- alter State, Continuity, MEMORY, Context, prompts, provider semantics, Cognitive Budget, or FastCal;
- tune product behavior to MemConflict or LongMemEval examples;
- freeze a comparator or benchmark version before execution-time verification;
- broaden the pre-1.0 benchmark into the full #1924 research matrix;
- provide an arbitrary-command escape hatch through the shared physical runner;
- touch `main`, `v2`, or the user's primary dirty checkout.

## Acceptance direction

Before the actual #1449 run starts, one plan must reach `EXECUTION_FROZEN` with two distinct axes, current exact benchmark/dataset/adapter identities, one preselected serious comparator, one exact #1447 RC, registered physical carriage, no-semantic-retry policy, and exact-infrastructure-resume policy.

That frozen plan must then pass `v1:external-qualification` admission under fresh shared-runner authority. Passing readiness or physical admission authorizes no generation by itself.
