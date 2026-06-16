# RelayMEM SLP Execution Design

## Purpose

RelaySLP is the target deferred memory and knowledge compiler. This document distinguishes existing dry-run/preflight foundations from the future write-capable execution path.

## Current implemented boundary

Current repository status provides partial candidate, diagnostics, approval, and persistence-preflight foundations. It does not provide:

- a complete asynchronous RelaySLP worker,
- scheduled/background SLP orchestration,
- complete page/index/log apply,
- a current `relaymem.slp_projection.v1` producer,
- durable memory writes from normal chat.

The current normal response path does not wait for RelaySLP and Retrieval remains read-only.

## Target inputs

RelaySLP may consume governed evidence such as:

- approved raw-event references,
- explicit user memory requests,
- validated detached RelayCTX update candidates,
- bounded INT/SCN/RUN/MEM summaries,
- existing approved memory pages/index/log,
- approved RelaySOUL constraints.

Generic content-free runtime trace alone is not sufficient source material for semantic memory compilation.

## Target outputs

- memory candidates,
- proposed page updates,
- held/rejected candidates,
- typed relation updates,
- lint findings,
- index/log plans,
- applied memory updates when future gates pass,
- RelaySOUL proposal candidates,
- typed content-free operation projections.

RelaySLP never directly emits the current answer, recovery wording, or resume text.

## Target execution flow

```text
governed source evidence
  -> candidate extraction
  -> memory-kind classification
  -> safety-scope classification
  -> existing-page lookup
  -> merge / update / hold / reject
  -> relation typing
  -> lint
  -> persistence preflight
  -> scene / approval / lineage / idempotency gates
  -> page/index/log apply or held plan
  -> optional RelaySOUL proposal
```

## Trigger modes

Target orchestration may support explicit/manual, turn-end deferred, scheduled/background, and rare forced reanchor-preparation modes. These are target modes unless an implementation document names a current producer and scheduler.

A single ambiguous reference, retrieval miss, or moderate token pressure is insufficient to trigger a forced path. Clarification belongs to RelayINT and recovery belongs to RelaySCN/RelayRUN.

## Persistence conditions

Target persistence is blocked when scene policy blocks it, confirmation is outstanding, confidence/lineage/scope is insufficient, contradiction remains unresolved, review or approval is required, idempotency checks fail, or a write would mutate RelaySOUL directly.

Threshold values belong in configuration/tests rather than architecture prose.

## Target projection

The following is a target example, not a current wire contract:

```yaml
relaymem_slp_projection:
  schema_version: relaymem.slp_projection.v1
  mode: deferred_dry_run
  source_count: 1
  candidate_count: 1
  update_count: 1
  hold_count: 0
  reject_count: 0
  persistence_attempted: false
  persistence_applied: false
  blocked_reason_ids:
    - dry_run_only
```

Default projections must not contain raw messages, candidate values, titles/summaries/snippets, page bodies/patches, filesystem paths, scene/intent semantic text, or visible response text.

## Target apply semantics

When future apply is enabled and all gates pass, it must preserve original evidence and lineage, use revision/idempotency checks, update page/index/log consistently, prevent duplicate writes after retry/resume, emit a content-free projection, and keep visible response delivery independent from persistence success.

## Required migration

Implement together:

1. governed source envelope and candidate schema,
2. deferred worker and RelayRUN scheduling,
3. memory page/index/log reader-writer interfaces,
4. safety, review, approval, scene, lineage, and idempotency gates,
5. RelaySOUL proposal adapter,
6. runtime-private SLP artifacts and typed projections,
7. failure/partial-write recovery,
8. SLP, persistence, retry, and trace smoke tests.
