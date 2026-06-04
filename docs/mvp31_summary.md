# MVP-31: RelayRUN Checkpoint Index and Waiting User Contract Summary

## Date basis

- JST date: 2026-06-04.
- Based on main after PR #219 and #220 merged.
- Scope: docs-only summary of the RelayRUN checkpoint index/listing diagnostics and waiting user contract chain.

## Completed scope

- `checkpoint_index` artifact:
  - RelayRUN emits a `relayrun_artifact.checkpoint_index` diagnostic object for checkpoint listing/index state.
- Checkpoint index/listing diagnostics:
  - RelayRUN can inspect checkpoint-root candidates and classify safe versus blocked checkpoint envelopes without selecting or resuming from them.
- Default-off index config:
  - Checkpoint index/listing diagnostics remain disabled by default and dry-run protected by configuration.
- Content-free checkpoint metadata summary:
  - Indexed checkpoint summaries keep only safe metadata such as path, run/turn identifiers, route/backend names, run status, node counts, blocked-reason counts, optional creation time, and `content_free=true`.
- `max_files` traversal cap:
  - Checkpoint scans are bounded so traversal and per-file processing stop at the configured cap and report truncation when applicable.
- Blocked unsafe roots/files:
  - Malformed JSON, wrong schema, non-content-free envelopes, forbidden raw-content keys, child symlinks, and paths outside the safe root are blocked rather than indexed.
- Absolute root / symlink root / symlink parent block:
  - Absolute checkpoint roots, symlinked checkpoint roots, and checkpoint roots with symlinked parent components are rejected before scanning.
- `waiting_user_contract` artifact:
  - RelayRUN emits a `relayrun_artifact.waiting_user_contract` diagnostic object that structures whether a run is waiting for user confirmation or clarification.
- Default-off waiting_user contract config:
  - Waiting-user contract diagnostics are explicitly configurable and remain default-off/dry-run-only.
- Recovery scene / unresolved reference / backend error waiting_user classification:
  - RelayRUN can classify recovery context repair, unresolved reference clarification, and backend-error recovery confirmation as structured diagnostics without changing user-visible behavior.

## Runtime safety

- Default disabled:
  - Checkpoint index/listing and waiting-user contract gates are default-off where applicable.
- Diagnostics-only:
  - MVP-31 reports indexing and waiting-user readiness; it does not apply resume, retry, recovery, or user-visible response behavior.
- No backend payload mutation:
  - RelayRUN checkpoint index and waiting-user artifacts are not forwarded to backend providers.
- No response body mutation:
  - Diagnostics do not change normal response payloads or error response behavior.
- No raw user/backend/response/snippet/page content in index summaries:
  - Index summaries exclude raw messages, user text, backend payloads, generated response text, prompts, snippet text, and page bodies.
- No resume selection yet:
  - Checkpoint listing does not choose a checkpoint or start a resume plan.
- No retry execution:
  - Waiting-user or blocked-state diagnostics do not retry failed work.
- No recovery transition apply:
  - Recovery transition artifacts remain unapplied.
- No user-visible waiting_user response:
  - The waiting-user contract does not produce direct user-facing text.
- Future visible response must pass through output pipeline:
  - Any future user-visible waiting/recovery response must pass through the full RelayLM output pipeline and may not bypass safety gates.

## Artifact chain

- `relayrun_artifact.checkpoint_index`:
  - Lists safe content-free checkpoint metadata and blocked file/root reasons as diagnostics.
- `relayrun_artifact.waiting_user_contract`:
  - Captures whether user confirmation or clarification is required, why it is required, and which actions are allowed.
- Relation to checkpoint writer / `resume_preflight` / `recovery_transition_artifact`:
  - The checkpoint writer can create content-free envelopes, `resume_preflight` can validate a specific envelope, `checkpoint_index` can list safe envelopes, `recovery_transition_artifact` can propose a recovery path, and `waiting_user_contract` can structure user-confirmation needs around those diagnostics.
- How `checkpoint_index` supports future resume selection:
  - It provides bounded, content-free checkpoint discovery that a later selection policy can use without reading raw prompt, response, or backend payload content.
- How `waiting_user_contract` supports future recovery/user confirmation:
  - It gives future recovery flows an internal contract for confirmation, clarification, and backend-error handling before any user-visible recovery output is allowed.

## Validation summary

- Checkpoint index smoke:
  - Validates default disabled behavior, enabled bounded scans, safe indexing, blocked malformed/unsafe files, absolute/symlink root blocks, symlink parent blocks, and backend payload immutability.
- Waiting-user contract smoke:
  - Validates normal, recovery-scene, unresolved-reference, and backend-error classifications while keeping `user_visible=false`, `apply_allowed=false`, and `applied=false`.
- Checkpoint writer smoke:
  - Revalidates default-off writer gates and safe content-free checkpoint envelope creation when explicitly enabled.
- Resume preflight smoke:
  - Revalidates checkpoint envelope readability and resume diagnostics without applying resume.
- Recovery transition dry-run smoke:
  - Revalidates recovery transition proposals without recovery apply or user-visible output.
- Runtime checkpoint dry-run smoke:
  - Revalidates RelayRUN runtime artifact and node-status diagnostics.
- Runtime diagnostics smoke:
  - Revalidates diagnostics/log payload structure and confirms RelayRUN artifacts remain metadata.
- Trace success smoke:
  - Revalidates trace metadata propagation for RelayRUN artifacts.
- RelaySCN / RelayREF / RelayMEM smokes:
  - Revalidates scene policy, reference diagnostics, and memory diagnostics alongside the new RelayRUN chain.
- Token budget truncation smokes:
  - Revalidates existing token-budget/truncation behavior and confirms RelayRUN diagnostics do not bypass truncation or payload safety ordering.

## Key design result

RelayRUN can now safely list existing content-free checkpoints and structure user-confirmation requirements without applying resume/retry/recovery or emitting user-visible recovery text.

## Remaining limitations

- No checkpoint index persistence/cache:
  - MVP-31 scans and reports diagnostics; it does not maintain a durable index cache.
- No checkpoint selection policy:
  - RelayRUN does not rank, choose, or recommend a checkpoint for resume.
- No actual resume:
  - Checkpoints can be listed and individually validated, but execution cannot resume from them.
- No retry execution:
  - Failed or blocked nodes are not retried.
- No user-visible waiting_user/recovery response:
  - Waiting-user and recovery diagnostics are not rendered as direct user-facing messages.
- No stream recovery:
  - Streaming recovery behavior is not implemented.
- No checkpoint pruning:
  - Checkpoint retention and cleanup remain future work.
- No multi-run UI/API:
  - RelayRUN does not expose a user-facing checkpoint browser, multi-run lookup API, or recovery UI.

## Next phase

- Recovery transition apply preflight:
  - Define the gates that must pass before any future recovery transition can be applied.
- Resume readiness policy:
  - Specify when a listed and validated checkpoint is eligible for resume planning.
- Checkpoint selection diagnostics:
  - Add diagnostics for candidate ranking, rejection, and selection without applying resume.
- Checkpoint pruning/index persistence:
  - Add safe retention and durable index maintenance policies.
- Eventual user-visible recovery through full output pipeline only:
  - If recovery output becomes visible, it must be generated through the normal output pipeline and must not bypass RelayLM safety or transformation stages.
