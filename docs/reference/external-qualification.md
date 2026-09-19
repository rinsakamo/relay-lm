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

### Bounded physical campaign carriage (#2951)

The registered `v1:external-qualification-campaign` target is the repository-owned
carriage for a future #1449 run.  It is deliberately separate from the
admission-only `v1:external-qualification` target.  The campaign descriptor is
declarative and has no executable, shell fragment, or arbitrary child field.

`tools.v1_external_qualification_llama_cpp_campaign` exposes four typed
boundaries:

- `LiveLaunchSession` supplies one fresh llama.cpp runtime/GPU/context/capacity
  attestation and one owned cleanup receipt;
- `HindsightHealthProbe` supplies dependency-complete v0.10.0 health only, with
  retain/recall/reflect, answer-model, benchmark-question, and judge counts all
  zero before campaign work; its startup LLM connection verification is
  explicitly skipped under the zero-semantic policy;
- `CurrentAuthorityReader` rechecks the current repository authority immediately
  before each identity freeze;
- `ParticipantExecutors` binds the canonical A/B/C/D slots to
  `ParticipantExecutionContext` and `ParticipantExecutionResult`, never to an
  executable supplied by the plan.

The controller calls `freeze_experiment_identity(...)` only after the live
attestation, starts or exactly resumes one `DurableQuestionRun` per frozen axis,
and calls the owned session cleanup in a `finally` boundary.  Completed
questions are skipped on exact infrastructure resume; semantic retry and
fallback are not supported.  The command-line target performs only deterministic
zero-semantic descriptor validation, so it cannot spend a provider/model/GPU or
Hindsight semantic call on its own.  The campaign controller does not alter
RelayLM product semantics or the Core qualification fingerprint.

### Pre-spend execution closure (#2957)

The campaign descriptor now has one repository-owned production binding. It
accepts only typed, fixed inputs for the current authority, benchmark material,
the accepted RC1 wheel/configuration, the llama.cpp launch, and one exact
Hindsight lifecycle. It has no executable, import path, shell fragment,
`--command`, or arbitrary child-process escape. The public target remains the
only entry: `tools.relay_physical_run` owns the shared lease and invokes the
registered campaign module.

Production setup is ordered as follows:

```text
fresh exact authority
  -> owned Hindsight start + health/version identity
  -> one owned llama.cpp launch + /props/slots/GPU attestation
  -> exact RC1 wheel hash/install/import-origin proof
  -> benchmark material and prompt/fingerprint proof
  -> FrozenExperimentIdentity + durable question stores
  -> fsync pre-call barrier (SCIENTIFIC_SPEND=UNSPENT)
  -> optional zero-semantic rehearsal stop
     OR
  -> fsync UNSPENT -> CONSUMED immediately before the first A/B/C/D call
```

The zero-semantic rehearsal is a diagnostic option, not a mandatory gate.  A
fresh owner may proceed directly through the same registered `--execute` path
after deterministic and host preflight checks pass, because that path owns the
fsync-backed spend transition itself.  A pre-spend infrastructure failure with
zero participant/model/benchmark/Hindsight/judge work may be corrected without
inventing a new scientific result; all failed-attempt evidence remains
preserved.  Once the ledger is `CONSUMED`, the stricter no-fresh-retry and exact
infrastructure-resume rules remain unchanged.

The exact-RC boundary installs the accepted wheel bytes into a checkout-
external isolated runtime with `--no-deps --no-index`; it verifies the wheel
hash before and after installation, package version, and `relaylm` import
origin. The D participant is therefore never an import of qualification
checkout code and never a source rebuild. Qualification-only carriage changes
remain outside the accepted RC1 product identity under REL2.

The campaign-level `ScientificSpendLedger` is outside the per-axis question
stores. It is atomically replaced and file/directory-fsynced from `UNSPENT` to
`CONSUMED` immediately before the first A/B/C/D call. A process crash after
that transition rejects a fresh campaign under the same owner; only an exact
identity/authority resume may continue. Each participant result is appended
and fsynced in A/B/C/D order before the next slot. Resume verifies the
participant identity, counters, observation, and question aggregate, skips
completed slots/questions, and rejects duplicates, conflicts, or torn
non-final records.

The extended live attestation separates immutable runtime identity from
per-launch observations. The frozen identity binds upstream revision,
canonical `/props` build info, model alias/path, model and chat-template
hashes, context, slots, context-shift state, and stable GPU name/driver/total
memory. PID, launch evidence paths, timestamps, and current used memory remain
attempt evidence and do not change the exact-resume fingerprint. The llama.cpp
CLI parser structurally matches `build 10874, commit e2d2c0d6a` against
`b10874-e2d2c0d6a` from `/props`; stdout and stderr are both accepted.

Owned Hindsight is the same v0.10.0 deployment whose dependency-complete
health passed. Its source/tree, package hashes, embedding/reranking identity,
ONNX material, database profile, answer-model condition, start/health/semantic
endpoint, and cleanup are bound together. The owned health probe waits within
the fixed startup deadline for transient process readiness (without issuing a
semantic request), while deployment/version/identity drift fails closed.
The serious-comparator C boundary is retrieval-only Hindsight followed by the
shared/common answer model; Hindsight `reflect` is not an answer-generation
path. For the frozen MemConflict Arm-C condition, each ordered history session
is retained as stable-document `exchange_append` deltas. Every first-use
exchange carries the frozen harness metadata fields `retained_at`,
`message_count`, `turn_index`, and `session_date`; Hindsight v0.10.0 includes
that metadata in fact extraction, so it is semantic input rather than
provenance-only decoration. The exact materialized retain request is fsynced in
the repository-owned preload journal before the external sync retain. A
completed logical exchange is recognized before a later question materializes
another wall-clock `retained_at`; an unresolved started record remains an
exact-resume ambiguity barrier.

Consolidation visibility is scoped per newly retained history session: snapshot
the bank’s pre-existing consolidation work, retain that session’s exchanges,
wait for the new work to become terminal/visible, durably acknowledge those
exact requests, then advance to the next session. Recall is observation-only
with the frozen budget/max-token/preference/query-time condition before the
common answer-model call. The bounded LongMemEval knowledge-update axis uses
the same ordered timestamped append/retrieval boundary but does not inherit
MemConflict-specific retain metadata without a separate upstream contract.
Health-only evidence does not
authorize a different comparator process or a silent restart. Cleanup runs for
llama.cpp, Hindsight, the exact-RC runtime, and the shared lease on every
failure path; an active participant exception remains primary if cleanup also
fails.

Successful citable execution ends in the existing `run_case`/`stable_run_id`/
`write_citable_evidence` model and unchanged repository classification
vocabulary. It includes the frozen case/manifest, A/B/C/D results, benchmark
metrics, counters/calls/tokens, latency/resources, limitations, authority,
runtime observations, campaign identity, and frozen experiment fingerprint.
When a zero-semantic rehearsal is requested, it remains non-citable and must
report zero semantic, model, benchmark-question, answer-model, and judge calls
with `SCIENTIFIC_SPEND=UNSPENT`.  It is not required before direct registered
execution.

### Repeatable synthetic comparator diagnostic (#2986)

The registered `v1:hindsight-comparator-synthetic-smoke` target separates
engineering convergence from one-shot benchmark spend.  It runs only fixed
repository-owned synthetic dialogue and a synthetic question under a fresh
diagnostic Hindsight deployment/profile/bank and a fresh owned llama.cpp
process.  The diagnostic exercises the exact v0.10.0 retain endpoint,
consolidation visibility, recall response mapping, and local OpenAI-compatible
model transport repaired around #2985.

It never parses benchmark history or selected benchmark questions, never opens
a `ScientificSpendLedger`, never writes a scientific durable root, and emits
only `NON_CITABLE_DIAGNOSTIC_*` evidence.  It may therefore be repeated after
infrastructure-only fixes without spending or selecting against the citable
campaign.

```bash
python -m tools.relay_physical_run \
  --target v1:hindsight-comparator-synthetic-smoke -- \
  --source-descriptor /absolute/path/to/campaign-descriptor.json \
  --diagnostic-owner-id diag-2986-hindsight-001 \
  --repo-root /absolute/path/to/relay-lm-checkout \
  --artifact-root /absolute/path/to/fresh-diagnostic-root
```

The smoke is intentionally narrower than scientific acceptance.  In particular,
it does not prove that the exact-RC D participant receives the benchmark's
question-bounded history.  Citable execution must remain blocked until the
production D path is wired through the existing transcript replay/frozen-query
adapter (or an equivalent exact-RC history-preserving boundary) rather than
submitting only the isolated question prompt.

### Launch intent and observed execution authority

A fresh-owner campaign descriptor is a **launch intent**, not the final
scientific observation. Campaign axes are the canonical pre-execution input
representation. The duplicated `execution_freeze.release_cases` surface is
derived from those validated prepared axes; historical release-case copies are
not an independent authority that must match before a fresh launch can be
constructed.

Pre-execution fail-closed gates remain for facts that can change the
experiment: benchmark-material bytes and SHA-256, question content, accepted
RC bytes/configuration, owner-local Hindsight identity, registered physical
carriage, current repository authority, and no-retry/exact-resume policy.

After the registered campaign launches, the scientific evidence authority is
the observed execution bundle: terminal campaign receipt, fresh
`LiveLaunchAdmissionAttestation`, Hindsight runtime identity, durable
question/participant records, citable per-axis evidence, spend ledger, and
cleanup receipts. The terminal receipt exposes direct references and the live
attestation under `observed_execution`. Declared intent may be compared with
observed execution, but stale historical duplicate copies are not themselves a
reason to block a fresh canonical launch.

## MemConflict RelayLM adapter boundary (#2047, #2068, #2075)

The shared MemConflict harness has two different provider operations: it ingests
the session dialogue, then recalls for each independent evaluation question. The
RelayLM adapter preserves that distinction at the external boundary.

For each benchmark session in the two-pass condition, the adapter:

1. validates every supplied `user` / `assistant` message and constructs it exactly once as a historical `message` Event, preserving role, content, order, timestamp, deterministic Event identity, and caller-provided provenance;
2. scans the supplied role stream in order without searching ahead: only an adjacent `user` followed immediately by `assistant` is a completed historical turn, while every message not consumed by such a pair is a standalone historical Event;
3. replays each completed turn through the public `replay_transcript_turn_two_pass(...)` product boundary from #2066, with zero Pass 1 calls and one ordinary governed Pass 2 attempt per completed imported turn, carrying the same execution and Continuity runtime sequentially so accepted State/Continuity from turn N is available to the next replayed turn;
4. persists each standalone historical message through ordinary Event storage only, with zero generated counterpart, zero Pass 1 call, zero Pass 2 call, and no synthetic State/Continuity transition; a standalone message remains historical evidence that later ordinary Context/Event selection may use according to existing product rules;
5. records truthful mechanics for total supplied messages, completed replay turns, standalone user/assistant counts, and bounded content-free ingestion evidence for each actual Pass 2 attempt, including status, existing bounded diagnostics, completion usage when available, and elapsed time;
6. leaves MEMORY unchanged unless existing explicit crystallization authority is separately invoked;
7. freezes the package immediately after that session's dialogue and before its questions; and
8. uses that frozen package as the sole question substrate. A later session gets a new snapshot after its own dialogue has been ingested.

The segmentation rule never drops a supplied message, synthesizes a missing counterpart, reorders history, or pairs across an intervening message. In particular, a standalone assistant message has no originating user turn, so applying replay Pass 2 to it would fabricate cognition that did not occur. Single-pass compatibility retains ordinary Event ingestion because no two-pass post-turn extraction exists in that declared condition. The governed two-pass adapter never implements a replay-specific State/Continuity parser, validator, lifecycle, or benchmark rule; it consumes the public Core turn boundary and existing Event authority.

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
`RelayLMQueryResult`. In two-pass mode the mechanics truthfully identify role-aware governed transcript replay plus standalone Event persistence and include total message/completed-turn/standalone-role counts together with bounded ingestion Pass1/Pass2 counts and token totals. The per-turn `dialogue_ingestion_evidence` surface retains bounded observations only for actual completed-turn Pass 2 attempts; standalone messages have no fabricated provider-call evidence. Its `AnswerTimeEvidence` is captured from the actual `CognitiveInput` supplied to the answer provider: `context` remains the ordinary product context, while the explicit `memory`, targeted `event`, and selected canonical `state` layers remain separately identifiable. The optional `retrieved_memories_projection()` contains only those three selected layers and labels each item with `source_role` (`memory`, `event`, or `state`). It never projects package KNOWLEDGE as lived memory. The projection is diagnostic evidence, not a replacement for the ordinary provider input.

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
its evidence references and launch observation are retained as attempt evidence,
while immutable runtime/GPU facts are retained in the frozen identity for exact
resume. PID, launch directory, timestamp, and used-memory changes therefore do
not change the exact-resume identity.
`DurableQuestionRun.start(...)` rejects an identity that was parsed directly
from a mapping without this live-attested construction step.

The extended identity binds upstream revision, canonical `/props` build info,
model alias/path, model and chat-template SHA-256, context, slots,
context-shift state, and stable GPU name/driver/total memory. The llama.cpp CLI
probe parses build number and commit structurally from combined stdout/stderr
and compares them to the canonical `/props` value; it does not substring-match
formatted CLI output.

For citable campaign execution, `ScientificSpendLedger` transitions from
`UNSPENT` to `CONSUMED` with atomic file/directory fsync immediately before the
first participant call. Participant result records are fsynced in canonical
A/B/C/D order and exact infrastructure resume verifies identity, observation,
counter accounting, and the completed-question aggregate before skipping it.
The descriptor also binds exact benchmark material and prompt content
fingerprints, exact accepted RC1 wheel/configuration, and one owned/attested
Hindsight v0.10.0 deployment. An optional zero-semantic rehearsal reaches the
barrier without crossing spend and never invokes a participant; direct
`--execute` crosses the fsync-backed spend boundary immediately before its
first real participant call.

The deterministic acceptance for this boundary is in
`tests/unit/test_memconflict_adapter.py` and
`tests/unit/test_memconflict_transcript_replay_adapter.py`: a blank-package
synthetic two-pass transcript proves zero imported Pass1 calls, exactly one governed
Pass2 attempt per completed turn, transcript/provenance fidelity, Canonical State and
Continuity formation through existing validators, sequential accepted-authority
visibility, failure retention without retry, and MEMORY non-generation. Irregular
synthetic role streams additionally prove that standalone historical messages are
preserved exactly once without generated counterparts or provider calls, while later
completed turns continue to see prior Event history through ordinary cognitive input.
The original #2047 isolation test still proves that ingested dialogue remains
available; Q2 after Q1 has the same answer-time evidence as Q2 alone from the same
frozen snapshot; source-role projection excludes KNOWLEDGE; and bounded provider
failures remain exportable.

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
not treated as the sole source of truth: for the production campaign, the
fsynced participant records are checked against each completed question
aggregate before evidence is rebuilt.

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
