---
relaylm_doc_type: implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: offline_tooling
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Twin Extraction Tooling Completion Report

## Scope

This report records the Twin Extraction offline material-extraction tooling slice: caller-invoked, bounded scripts that turn an X (Twitter) archive export and/or a ChatGPT export into batched material, run a fixed two-way extraction prompt (style vs. fact) against an OpenAI-compatible chat completions endpoint, and merge the batch results into a single review artifact for manual approval.

This is offline preprocessing tooling, not a RelayLM runtime slice. It does not import the `relaylm` package, does not add a daemon/poller/scheduler/worker pool, and does not write to MEM/SOUL or connect to the RelaySLP pipeline. The base branch is `main` at the time this slice started.

## Implemented production boundary

Implemented:

- `scripts/relaylm_twin_extraction_common.py`: stdlib-only shared helpers — a JSON top-level-array reader that transparently falls back from a single in-memory `json.loads` to bounded incremental parsing for files over a size threshold or on an in-memory parse failure (handles the JS variable-assignment prefix on X archive files without a dedicated stripping step, since it scans forward to the first `[`), plus JSONL read/write and batch-file writing.
- `scripts/relaylm_twin_extraction_preprocess.py`: `--source x` parses `tweets.js`, strips the JS prefix, excludes retweets, trims the trailing auto-appended quote-tweet link for quote posts, keeps `in_reply_to_status_id` as a thread hint, and supports `--since`/`--until` (`YYYY-MM`, inclusive) filtering. `--source chatgpt` parses `conversations.json`, orders each conversation's messages by `create_time`, keeps user messages as primary material and assistant messages as `role: context`, and skips conversations with no user message. Both sources write JSONL batch files (`batch_0001.jsonl`, ...; default 150 posts / 4 conversations per batch) and print a content-free counts-only summary (no post/utterance bodies, no absolute paths).
- `scripts/relaylm_twin_extraction_batch_runner.py`: discovers batch files, sends each with the fixed prompt file to `--base-url` (default `http://127.0.0.1:1234/v1`) via the standard library (`urllib.request`, no new dependency), bounded by `--max-batches`. `--dry-run` computes batch count and payload size with no network call. A batch whose response cannot be parsed as `{style_observations: [...], fact_candidates: [...]}` is retried up to `--retries` (default 1) and then recorded content-free under `--out-dir/failed/` (fail-closed; never partially applied). Successful batches are written under `--out-dir/results/`. Progress output is one JSON line per batch (batch id, record count, status, attempts, elapsed time) with no response bodies.
- `scripts/relaylm_twin_extraction_merge.py`: merges all `--results-dir/*.result.json` files into one `twin_extraction_review.json`. `style_observations` are never auto-merged (even identical descriptions from different batches stay separate); each observation's `strength` is recomputed from its own `evidence_ids` count. `fact_candidates` are merged only on an exact `(statement, type)` match — no fuzzy/similarity merging; merged `evidence_ids` are unioned, `provenance` becomes a sorted list, `time_context` values are collected into a sorted `time_contexts` list, and the merged candidate is `private_only` if any contributing candidate is `private_only` or omits `sensitivity` (fail-closed default). Writes MEM/SOUL is out of scope; this tool stops at the review artifact.
- `scripts/twin_extraction_prompts/x_extraction_prompt.txt` and `scripts/twin_extraction_prompts/chatgpt_extraction_prompt.txt`: the two extraction prompts copied verbatim from `docs/tools/twin_extraction_prompts.md` (schema unchanged).
- `docs/tools/twin_extraction_prompts.md`: the prompt specification document (front matter added; body content unchanged from the source specification).
- `docs/tools/twin_extraction_runbook.md`: the execution runbook (preprocess -> dry-run -> live run -> merge -> manual review), including the operational note that private_only-eligible batches must not be sent to a cloud endpoint before that determination has been reviewed.
- `.gitignore`: added `runtime/twin_extraction/` so archive input, batch files, and extraction results are never committed.

## Preserved authorities and non-goals

Preserved authorities:

- The RelayLM runtime (`relaylm/` package), RelayMEM mutation authority, RelaySLP, and SOUL Lab UI are untouched; none of these scripts import `relaylm`.
- O2/O3, CW-A4/CW-A5, and RelaySLP status are unchanged by this PR.

Non-goals:

- no MEM/SOUL bootstrap write path or ingestion;
- no automatic approval or automatic fuzzy merging of extracted candidates;
- no LLM-as-judge or automated extraction-quality scoring;
- no daemon, polling loop, scheduler, or worker pool (the batch runner is bounded by discovered batch count and `--max-batches`);
- no cloud-provider-specific client (OpenAI-compatible generic endpoint only);
- no OpenWebUI / SOUL Lab UI changes;
- no committed real archive data, extraction results, or batch files.

## Changed files

- `scripts/relaylm_twin_extraction_common.py`
- `scripts/relaylm_twin_extraction_preprocess.py`
- `scripts/relaylm_twin_extraction_batch_runner.py`
- `scripts/relaylm_twin_extraction_merge.py`
- `scripts/relaylm_twin_extraction_smoke.py`
- `scripts/relaylm_twin_extraction_security_smoke.py`
- `scripts/twin_extraction_prompts/x_extraction_prompt.txt`
- `scripts/twin_extraction_prompts/chatgpt_extraction_prompt.txt`
- `docs/tools/twin_extraction_prompts.md`
- `docs/tools/twin_extraction_runbook.md`
- `docs/mvp/wave8/twin_extraction_completion_report.md`
- `docs/README.md`
- `docs/PROJECT_STATUS.md`
- `.gitignore`

## Validation evidence

```bash
python -m compileall relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/twin_extraction_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_documentation_current_boundary_smoke.py
```

All of the above pass locally. `relaylm_twin_extraction_smoke.py` uses small, entirely fictional fixtures generated inline (fake `tweets.js`/`conversations.json` content) to cover JS-prefix stripping, retweet exclusion, quote-tweet trailing-link trimming, `--since`/`--until` date filtering, ChatGPT user/context separation, batch-count splitting, the batch runner's `--dry-run` path, fail-closed handling of a malformed extraction response (including through `main()`' `results/`/`failed/` output), and merge's exact-match union / private_only propagation / no-fuzzy-merge behavior, plus one end-to-end dry-run pass through preprocess -> batch runner (`--dry-run`) -> merge with zero LLM calls. `relaylm_twin_extraction_security_smoke.py` separately asserts that stdout/stderr/exception text from all three CLIs never contains post/utterance body canaries, a credential-like canary embedded in `--base-url`, or the fixture's absolute temp-directory path, including on fail-closed error paths (missing input, malformed input, missing prompt file, missing results directory). No LLM, network access, or real archive is required for either smoke.

## Known limitations

- ChatGPT message ordering is derived by sorting each conversation's messages by `create_time` rather than walking the `mapping` parent/child tree; this matches the common single-branch-conversation export shape but does not reconstruct edited/regenerated branch selection for multi-branch exports.
- The "明らかに使い捨ての操作指示だけの会話はスキップ可" (skip obviously disposable operational-instruction-only conversations) preprocessing option from the prompt specification is not automated; all conversations with at least one user message are kept, leaving that judgment to the manual review step.
- `fact_candidates` merge additionally keys on `type` (not statement text alone) so that an identical statement string filed under conflicting `type` values is kept separate rather than silently collapsed; this is a stricter behavior than the literal "統合" instruction, chosen to avoid masking a labeling disagreement.
- `time_context` values are merged into a `time_contexts` list rather than a single scalar field, since a merged candidate can carry more than one source time context; this is a superset of the single-batch schema, not a breaking change to it.
- The batch runner and merge CLIs operate purely on local files and a caller-specified endpoint; there is no queue, retry backoff beyond `--retries`, or resumable/partial-batch checkpointing across separate invocations.

## Shared documentation update inputs

- This PR does not change O2/O3, CW-A4/CW-A5, RelaySLP, or any RelayMEM/RelaySOUL runtime authority or status; `docs/PROJECT_STATUS.md` receives only a one-line addition noting the offline, runtime-non-contact tooling addition.
- No MEM bootstrap ingestion or SLP connection exists yet; any future slice that wires the reviewed `twin_extraction_review.json` output into MEM bootstrap or SOUL CW-A1 sources is separate follow-on work, not part of this PR.
- `docs/README.md` gains two new links (`docs/tools/twin_extraction_prompts.md`, `docs/tools/twin_extraction_runbook.md`) under a new "Offline tooling and runbooks" section; no existing anchors were removed or reworded.

## Source pull request

- PR: #503
- URL: https://github.com/rinsakamo/relay-lm/pull/503
