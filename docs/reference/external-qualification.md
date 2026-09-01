# Exact-RC external qualification harness

Status: preparation contract for #1981 under the bounded Core 1.0 release gate in #1449.

> **Prepare the ring before the contender is frozen; benchmark the exact contender only after it exists.**

This surface defines the repository-owned harness contract for external benchmark qualification. It is outside RelayLM Core semantic authority: benchmark adapters translate public benchmark cases into executions, but they do not change State, Continuity, MEMORY, Context, prompts, provider semantics, Cognitive Budget, or task routing.

## Ownership decision

Three existing authorities were evaluated before creating this owner.

1. `evaluation` (#1247) owns deterministic RelayLM-native evaluation and merge/report invariants. External public benchmark execution is not a deterministic product-semantic registry, so placing the harness there would broaden that owner incorrectly.
2. `actual_model_evaluation` (#1386) already proves exact model/runtime identity, stable run identity, immutable evidence, and separately reviewable execution evidence. Its current run manifests are intentionally Stage-R/Core-reference specific: they include RelayLM Character fixtures, cognition execution identity, pass requests, Cognitive Budget identity, and #1386 review semantics. Reusing those types as the common comparator manifest would make every external system pretend to be a RelayLM Stage R run.
3. `release_engineering` (#1447) owns the exact release manifest that binds version/tag/commit to wheel and sdist hashes. The external harness consumes that manifest directly for citable release qualification rather than inventing a second RC identity.

Therefore #1981 has one small external-qualification owner. It reuses the established identity/evidence primitives at their natural boundaries instead of creating a parallel release identity or pushing research comparison into Stage R.

## Reused primitives

The harness intentionally reuses existing repository behavior in two ways.

- `tools/release_identity.py manifest` remains the source of exact RC artifact identity. `validate_release_identity(...)` validates and embeds that REL2/REL3-shaped identity for the RelayLM slot.
- `actual_model_artifacts.write_actual_model_evidence(...)` already demonstrates the repository's run-id-addressed immutable-evidence pattern: a stable identity is hashed before execution results are persisted, identical rewrites are idempotent, and different evidence under the same run id fails closed. The external harness uses the same proven pattern with a separate schema because Stage R's evidence type is not architecture-neutral.

No new product qualification fingerprint input is added. The harness owner depends on release engineering, but Core semantic owners do not depend on this owner.

## Evidence purposes and RC gate

Every manifest declares one purpose:

```text
dry_run
  synthetic/deterministic adapter and serialization validation
  non-citable

prequalification_smoke
  moving-build harness debugging only
  non-citable

release_qualification
  bounded #1449 execution
  citable only when an exact #1447 RC/final release manifest is supplied
```

`release_qualification` fails closed without the exact release identity. A pre-RC purpose rejects a citable release identity instead of allowing a moving build to masquerade as the release contender.

This harness does not itself decide that Core 1.0 passes #1449. It records reproducible case evidence and the bounded classification that #1449 later consumes.

## Common case contract

The common benchmark-case mapping is benchmark-name agnostic. Each case records:

- stable case id;
- architecture-relevant axis;
- benchmark id and repository;
- exact benchmark revision;
- benchmark license observed for the execution;
- exact dataset revision and dataset license;
- adapter-local case reference.

The `axis` is an open string rather than a benchmark-specific enum. Preparation tests prove at least two materially distinct shapes: conflict/update/temporal validity and personalization/accurate retrieval. Execution-time benchmark names, versions, datasets, and licenses must be freshly verified upstream.

## Architecture slots

Every manifest represents the same canonical slots in order:

```text
A same_model_direct
B simple_baseline
C serious_comparator
D relaylm_exact_rc
```

System/product names are not part of the permanent slot contract.

- A is the same physical model/tokenizer/quantization as D under citable qualification. The harness rejects a citable manifest that violates that physical-model match.
- B may be explicitly omitted when a simple retrieval/full-history condition is not scientifically meaningful. Omission is an evidence fact and requires a reason; fake implementation identity is prohibited.
- C must be enabled for citable qualification and identifies the contemporary comparator implementation, source revision, version, deployment, license, model/runtime, hardware, retry policy, and unavoidable condition differences.
- D must be enabled for citable qualification. Its source revision and package version must match the exact #1447 release identity.

A, C, and D are mandatory in `release_qualification`; B is representable and may be omitted with justification.

## Execution identity

Each manifest first records the exact harness identity/revision and adapter identity/revision; both revisions are exact Git commits so a citable run cannot float with a moving adapter. Each enabled participant then records separately:

- implementation name;
- exact source revision;
- implementation/version identity;
- deployment identity;
- license;
- physical model artifact;
- tokenizer;
- quantization;
- provider/backend/runtime;
- context capacity;
- decoding controls;
- reasoning controls;
- GPU, CPU, and offload identity;
- failure/retry policy;
- matched-condition differences.

Judge identity and judge policy are manifest-level because the common case should use the same judge policy where the benchmark allows it. If a condition cannot be matched, the difference is recorded instead of hidden.

## Result evidence

Each participant result preserves four measurement groups rather than collapsing them into one aggregate:

```text
quality
  benchmark-native numeric metrics

tokens
  model-facing input tokens
  model output tokens
  model-call count

latency
  TTFT when available
  fair query latency when available
  end-to-end latency when available

resources
  peak GPU memory when available
  peak CPU memory when available
  persistent storage when available
  bounded notes
```

Unknown/unavailable observations remain `null`; they are not fabricated as zero.

Known limitations and an optional bounded failure detail are stored per participant. A failed execution may therefore preserve partial token/latency/resource observations instead of disappearing as an exception. Benchmark-native metrics remain benchmark-native keys rather than being projected into a RelayLM-only score.

## Classification

One case evidence record carries exactly one bounded classification for later #1449 reconciliation:

- `reproducible_competitive_result`;
- `specialist_deferred_capability_loss`;
- `generalizable_core_defect_candidate`;
- `benchmark_adapter_mismatch`;
- `non_reproducible_workload`;
- `resource_impracticality`;
- `comparison_condition_mismatch`.

Classification is evidence, not mutation authorization. A `generalizable_core_defect_candidate` still returns to the normal semantic/runtime owner before any product change. A benchmark-specific loss does not authorize test-set tuning or task detection.

## Runner boundary

`run_case(...)` executes one validated benchmark-case mapping through enabled A/B/C/D participant plans using caller-supplied executors. A benchmark adapter therefore owns only translation between the public benchmark and this common execution contract.

The runner does not import RelayLM cognition, State, Continuity, MEMORY, Context, provider routing, or Stage R execution types. A serious comparator adapter can be added or replaced without adding a comparator-specific subsystem to RelayLM.

## MemConflict RelayLM adapter boundary (#2047, #2068)

The shared MemConflict harness has two different provider operations: it ingests
the session dialogue, then recalls for each independent evaluation question. The
RelayLM adapter preserves that distinction at the external boundary.

For each benchmark session in the two-pass condition, the adapter:

1. validates the flattened supplied transcript as complete ordered `user` / `assistant` turn pairs and constructs the supplied messages as exact historical `message` Events, preserving role, content, timestamp, deterministic Event identity, and caller-provided provenance;
2. replays each completed turn through the public `replay_transcript_turn_two_pass(...)` product boundary from #2066, with zero Pass 1 calls and one ordinary governed Pass 2 attempt per imported turn, carrying the same execution and Continuity runtime sequentially so accepted State/Continuity from turn N is available to turn N+1;
3. records bounded content-free ingestion evidence for each Pass 2 attempt, including status, existing bounded diagnostics, completion usage when available, and elapsed time, without adding semantic retry or regenerating supplied assistant content;
4. leaves MEMORY unchanged unless existing explicit crystallization authority is separately invoked;
5. freezes the package immediately after that session's dialogue and before its questions; and
6. uses that frozen package as the sole question substrate. A later session gets a new snapshot after its own dialogue has been ingested.

Single-pass compatibility retains ordinary Event ingestion because no two-pass post-turn extraction exists in that declared condition. The governed two-pass adapter never implements a replay-specific State/Continuity parser, validator, lifecycle, or benchmark rule; it consumes the public Core boundary and existing authority.

Each evaluation question is executed exactly once by copying the frozen package
to a disposable per-question clone and calling the ordinary declared
`run_user_turn` or `run_user_turn_two_pass` path on that clone. The clone may
receive the normal question Event and normal answer-time State/Continuity
proposal processing required by that product path, but it is discarded after
the turn (including awaited Pass 2). The live package and the frozen snapshot
are never given the question or answer; the mechanics record that no question
or answer is ingested into either durable package. The adapter has no semantic retry,
fallback, question-specific prompt, retrieval rule, State rule, MEMORY rule,
Continuity rule, or benchmark answer/reference input.

`tools/memconflict_adapter.py` exposes the clone mechanics alongside each
`RelayLMQueryResult`. In two-pass mode the mechanics truthfully identify governed
transcript replay and include bounded ingestion Pass1/Pass2 counts and token totals.
The per-turn `dialogue_ingestion_evidence` surface retains the bounded ingestion
status/diagnostic/usage/latency observations without persisting transcript content a
second time. Its `AnswerTimeEvidence` is captured from the actual `CognitiveInput`
supplied to the answer provider: `context` remains the ordinary product context,
while the explicit `memory`, targeted `event`, and selected canonical `state` layers
remain separately identifiable. The optional `retrieved_memories_projection()`
contains only those three selected layers and labels each item with `source_role`
(`memory`, `event`, or `state`). It never projects package KNOWLEDGE as lived memory.
The projection is diagnostic evidence, not a replacement for the ordinary provider
input.

The adapter bridges the completed #1871 bounded failure contract at the same
external evidence boundary. It retains the failed provider-call class name and
retains message text only for the already-sanitized `ProviderProtocolError`
surface, bounded to 512 characters. An untrusted exception message is omitted.
Pass 2 still reports the ordinary bounded `pass2_failed` result; a Pass 1
failure is surfaced as `RelayLMReadOnlyQueryExecutionError` with the bounded
diagnostic available for external evidence. No raw response, request body,
traceback, API key, or semantic payload is added.

The adapter does not own long-run durability. A caller begins the corresponding
question in `DurableQuestionRun` before invoking the snapshot, appends the
adapter's model/request and failure evidence, and commits the result only after
the isolated turn is complete. `exact_infrastructure_resume` still requires
the complete frozen identity and question list; completed questions remain
skipped and semantic regeneration remains forbidden. A durable partial or
in-flight tail is retained exactly as required by #2045.

### Canonical typed query commit

The repository-owned external controller uses
`execute_relaylm_question(...)` from `tools.external_qualification` for each
question. Its success path is deliberately fixed to:

```text
RelayLMFrozenQuerySnapshot.query(question)
        -> RelayLMQueryResult
        -> RelayLMQueryResult.to_external_evidence()
        -> DurableQuestionRun.commit_question(...)
```

`commit_relaylm_query_result(...)` accepts only the public
`RelayLMQueryResult` type and persists the complete mapping returned by its
`to_external_evidence()` method. It does not inspect or reconstruct any
internal Pass 1/Pass 2 object. A `RelayLMReadOnlyQueryExecutionError` is routed
through `record_relaylm_query_failure(...)`: its existing bounded
`to_external_evidence()` mapping is appended as request evidence, the question
remains in flight, and no completion record is written. There is no semantic
retry or alternate result path.

### Live launch/admission identity

Before a run reaches `EXECUTION_FROZEN`, construct its
`FrozenExperimentIdentity` with `freeze_experiment_identity(...)` (or
`FrozenExperimentIdentity.from_live_attestation(...)`). The identity must
contain a `launch_admission` mapping with the final live backend, runtime,
model-runner identity, effective GPU reservation, admitted context, capacity
evidence, launch-evidence reference, and runtime-ownership-evidence
reference. The helper compares every one of those facts, plus the mirrored
backend/runtime/context/capacity fields, against the final
`LiveLaunchAdmissionAttestation` and fails closed on omission or mismatch.

Historical runtime literals cannot authorize a freeze. The live attestation is
transaction-scoped and must be freshly supplied by the launch/admission owner;
its evidence references are retained in the frozen identity for exact resume.
`DurableQuestionRun.start(...)` rejects an identity that was parsed directly
from a mapping without this live-attested construction step.

The deterministic acceptance for this boundary is in
`tests/unit/test_memconflict_adapter.py` and
`tests/unit/test_memconflict_transcript_replay_adapter.py`: a blank-package
synthetic two-pass transcript proves zero imported Pass1 calls, exactly one governed
Pass2 attempt per completed turn, transcript/provenance fidelity, Canonical State and
Continuity formation through existing validators, sequential accepted-authority
visibility, failure retention without retry, and MEMORY non-generation. The original
#2047 isolation test still proves that ingested dialogue remains available; Q2 after
Q1 has the same answer-time evidence as Q2 alone from the same frozen snapshot;
source-role projection excludes KNOWLEDGE; and bounded provider failures remain
exportable.

Stable run identity hashes the full manifest and case before observations. `replicate_id` is part of that manifest identity. Repeating a stochastic condition therefore requires a distinct replicate id; attempting to write different results under the same run id fails closed.

## Detached long-run durability

`DurableQuestionRun` provides the question-level persistence boundary for a long
external or actual-model run. It is a detached control plane and does not depend on
the lifetime of a Codex UI, terminal session, or model process. A fresh run creates
an immutable manifest containing the complete frozen experiment identity and ordered
question fingerprints, an atomic `checkpoint.json`, an atomic `run-state.json`, and
append-only `question-observations.jsonl` / `request-evidence.jsonl` files.

Each question is recorded as `in_flight` before model-facing work and as `completed`
only after its request evidence and result have been durably flushed. A process exit
therefore preserves the in-flight tail and any partial final JSONL record without
claiming semantic completion. Aggregates are rebuilt from completed question records,
not treated as the source of truth.

`exact_infrastructure_resume` is admitted only when the full frozen identity,
authority status, ordered question IDs, content fingerprints, and session IDs match
the manifest exactly. Completed questions are skipped and attempting to begin one is
rejected; semantic retry is not a supported mode. A fresh run uses a separate empty
artifact root, so an old shakedown cannot be silently continued or overwritten.

The 122-question MemConflict shakedown discussed in #2045 is historical evidence
only. This durability surface does not authorize rerunning or resuming that artifact.

## Preparation acceptance

The deterministic tests cover:

- two materially distinct benchmark axes;
- all A/B/C/D slots;
- justified B omission;
- exact RC blocking before a #1447 release identity exists;
- exact D release version/commit binding;
- A/D physical-model matching;
- non-citable pre-RC evidence;
- separate quality/token/call/latency/resource serialization;
- all seven result classifications;
- deterministic stable ids and immutable evidence collision behavior.

No public benchmark result or #1449 verdict is produced by this preparation transaction.
