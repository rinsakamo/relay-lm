# External qualification launch readiness

Status: zero-generation preparation contract for #2821 under the exact-RC gate in #1449.

> Prepare the execution plan before the contender exists; freeze exact external and physical identities before spending benchmark generations.

This surface extends the completed #1981 external-qualification harness. It does not redefine the A/B/C/D evidence contract, RelayLM cognition, benchmark scoring, or release identity.

## Boundary

The repository already owns the architecture-neutral evidence runner in `tools/external_qualification.py` and the proven MemConflict RelayLM adapter in `tools/memconflict_adapter.py`.

#2821 adds only the pre-execution layer needed to establish that a bounded two-axis release qualification can be launched without discovering missing identities after the exact RC is cut:

- `tools/external_qualification_readiness.py` validates a two-axis launch plan and an eventual exact execution freeze;
- `tools/longmemeval_adapter.py` maps the released LongMemEval `knowledge-update` shape into timestamp-preserving governed transcript ingestion without exposing gold labels to the model;
- physical-target registration is deliberately sequenced after #2811 because #2811 currently owns a write to the shared llama.cpp target registry.

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
- the serious comparator implementation/source revision/version/license matches the preselected comparator identity across the frozen cases.

Only then does validation return:

```text
EXECUTION_FROZEN
```

`assess_launch_readiness(...)` exposes a bounded `BLOCKED` record for invalid or unresolved plans. It never repairs a plan or launches anything.

## Preferred bounded Core 1.0 ring

The following is a current preparation choice, not immutable execution authority. Fresh upstream verification is required again immediately before a citable run.

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

Current reconnaissance selects Hindsight as the preferred C-slot family because, as of #2821 creation, its public project is self-hostable, actively maintained, permissively licensed, supports local/OpenAI-compatible inference, and publishes reproducible long-term-memory benchmark work including LongMemEval.

Do not encode a floating `main`, `latest` container, vendor headline score, or remembered release number as qualification authority. At execution freeze record the exact source revision, version, deployment, license observation, physical model, provider/runtime, decoding/reasoning controls, and unavoidable matched-condition differences in the existing #1981 participant identity.

If Hindsight is no longer reproducible or scientifically matchable before generation begins, #1449 may select a different current serious comparator. Once execution is frozen, comparator switching after observing RelayLM results is not allowed.

## External references to re-verify

Preparation-time references only:

- Hindsight: `https://github.com/vectorize-io/hindsight`
- LongMemEval: `https://github.com/xiaowu0162/LongMemEval`
- independent MemConflict comparison harness: `https://github.com/EngTurtle/hermes-memconflict`

Repository licenses and benchmark/dataset licensing remain execution-time identity fields. Preparation-time observations do not substitute for a fresh citable license/revision check.

## Physical sequencing

The local release reference currently uses the shared llama.cpp queue/resource boundary. #2811 is simultaneously preparing off-turn Crystallization carriage and is expected to mutate `.ai/physical/llama_cpp_targets.json`.

Therefore #2821 must not create a parallel edit to that registry while #2811 is an active writer. The benchmark physical target is registered only after fresh authority shows that the shared boundary is free. Until then, a pre-RC plan may name the intended target and resource while `registered=false`; execution freeze rejects that state.

The responsibility split remains:

```text
shared physical runner / queue = HOW
benchmark adapters + launch plan = WHAT
future exact-RC benchmark owner = THIS RUN
```

The future exact-RC owner, not this readiness surface, owns bounded execution count, exact physical attestation, and the first immutable result.

## Hard non-goals

This preparation does not:

- run a moving `v1` as release evidence;
- run any model or judge;
- alter State, Continuity, MEMORY, Context, prompts, provider semantics, Cognitive Budget, or FastCal;
- tune product behavior to MemConflict or LongMemEval examples;
- freeze a comparator or benchmark version before execution-time verification;
- broaden the pre-1.0 benchmark into the full #1924 research matrix;
- touch `main`, `v2`, or the user's primary dirty checkout.

## Acceptance direction

Before the actual #1449 run starts, one plan must reach `EXECUTION_FROZEN` with two distinct axes, current exact benchmark/dataset/adapter identities, one preselected serious comparator, one exact #1447 RC, registered physical carriage, no-semantic-retry policy, and exact-infrastructure-resume policy.

The readiness validator is a gate, not an executor. Passing it authorizes no generation by itself.
