---
relaylm_doc_type: evidence
relaylm_authority: mvp2_incoming_system_fallback_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current RelaySCN semantic classification or scene-state apply
  - current RelaySOUL proposal generation or activation
  - the target client-instruction cache/identity and RelaySCN projection pipeline
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: ac963e98eb25b8d2f9402d7eb48b78d8c84f79a5
relaylm_source_origin_commit: accdeab36ab718feb7781c2bbd09b12cf6465544
relaylm_source_pr: 17
relaylm_recorded_on: 2026-05-21
relaylm_source_blob: 2662d59a3b6364610021a019c36ef3585ba2c684
relaylm_source_content_sha256: e2277a6b809b4a89ea139c7df2dd42f92b791e7ece8ea00605195e9dfb98f238
relaylm_pre_cutover_blob: f229f538222bd72e9b1fa4a0290d2320491c9ec0
relaylm_pre_cutover_content_sha256: efe00f859479bc17a09c220afb2cabcdeb42cda6fd41594ab19c90992414dde0
relaylm_exact_source_snapshot: mvp2_incoming_system_fallback-source.txt
---
# MVP-2 Incoming System Prompt Fallback Evidence

This frozen record preserves the incoming `system`/`developer` compatibility helper history as historical implementation evidence. Unlike its three sibling MVP-2 compile-chain records, this source was substantively rewritten once after introduction, and it mixes early helper history with later current-authority reinterpretation in the same body.

## Source versus pre-cutover provenance

The source commit and the pre-cutover blob are **different revisions and must not be paired as the same version**:

```text
old path: docs/mvp/mvp2_incoming_system_fallback.md
source PR: #17, merge accdeab36ab718feb7781c2bbd09b12cf6465544
source commit: ac963e98eb25b8d2f9402d7eb48b78d8c84f79a5 (2026-05-21, 50-line original)
source blob: 2662d59a3b6364610021a019c36ef3585ba2c684
source content SHA-256: e2277a6b809b4a89ea139c7df2dd42f92b791e7ece8ea00605195e9dfb98f238
pre-cutover commit: a7669fcb2906202fee8b89c601bf3dfbf28bfece (HEAD; content last changed by PR #246, 125-line revision)
pre-cutover blob: f229f538222bd72e9b1fa4a0290d2320491c9ec0
pre-cutover content SHA-256: efe00f859479bc17a09c220afb2cabcdeb42cda6fd41594ab19c90992414dde0
disposition: split (evidence_retained + absorbed)
```

The exact snapshot retained byte-for-byte as [mvp2_incoming_system_fallback-source.txt](mvp2_incoming_system_fallback-source.txt) is the **pre-cutover** (PR #246) revision, not the original PR #17 introduction, because the pre-cutover revision is what was live on `docs/mvp/` immediately before this cutover and is the version this record's absorption audit was performed against.

## Post-source modification

One content-modifying commit exists between introduction and the pre-cutover snapshot:

```text
commit: 3e502b710b794e83b45b0e66e6039c773e50c680
PR: #246 ("docs/runtime: define client canonicalization and SCN instruction cache")
date: 2026-06-12
change: expanded 50 -> 125 lines; added the "current authority meaning" reinterpretation
         block, developer-role support, extract_instruction_text() text-part
         normalization, the XML-escaping section and spoof-probe example, the
         RelaySOUL non-mutation paragraph, and expanded Out-of-scope list.
```

An earlier pure path-rename commit (`f84872eb4d671b7363575c996f8a38df6f369f89`) moved the file under `docs/mvp/` without changing content.

## Absorbed normative blocks

Three still-valid, currently-implemented rules had no current-authority owner anywhere in the documentation tree and were absorbed verbatim into [Context Compiler Contract](../../contracts/context_compiler_contract.md) (`### Current system/developer compatibility helper`) in this same PR:

```text
block: extract_instruction_text() text-part normalization, whitespace preservation, non-text-part handling
source digest (normalized SHA-256): 25ff74e11f1122d3a53b0d296d7c03a13627c7899aa23999d8b4bae058b69298
destination digest (normalized SHA-256): 25ff74e11f1122d3a53b0d296d7c03a13627c7899aa23999d8b4bae058b69298
match: exact

block: compiled render order (stable profile blocks -> incoming_system_prompt dynamic block -> recent non-instruction messages)
source digest (normalized SHA-256): 44de90416ffa1667c3d4d53634c72d071916c0e6477f30c4d2a2d76121e9b089
destination digest (normalized SHA-256): 44de90416ffa1667c3d4d53634c72d071916c0e6477f30c4d2a2d76121e9b089
match: exact

block: incoming_system_prompt XML-escaping mechanism and spoof-probe example
source digest (normalized SHA-256): 3ed46ebbf6367c302adb02e714704f1218ec07b43ee7c1d87aadde618db0d7db
destination digest (normalized SHA-256): 3ed46ebbf6367c302adb02e714704f1218ec07b43ee7c1d87aadde618db0d7db
match: exact
```

Digests are computed identically to `scripts/relaylm_docs_normative_digest.py`'s `digest()` function (SHA-256 over the block text after CRLF/CR normalization to LF). All three blocks moved into the destination with byte-identical wording; only the surrounding non-normative framing sentence around the compiled-order block changed tense (from "The historical compiled order is" to "The compiled order is"), which is outside the digested span.

Not absorbed (already covered, more rigorously, elsewhere): the raw-instruction non-authority rule and the RelaySOUL non-mutation paragraph are already stated in [Client Instruction Authority Contract](../../architecture/client_instruction_authority_contract.md); the RelaySCN scene-role interpretation is already stated there in more detail as explicit target architecture.

## Current authority

Current client system/developer instruction authority, RelaySCN semantic classification, and RelaySOUL non-mutation belong to [Client Instruction Authority Contract](../../architecture/client_instruction_authority_contract.md) and [Client History Authority Contract](../../architecture/client_history_authority_contract.md). Current compiled render order, text-part normalization, and evidence-escaping behavior belong to [Context Compiler Contract](../../contracts/context_compiler_contract.md) (see the newly absorbed section above). Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).
