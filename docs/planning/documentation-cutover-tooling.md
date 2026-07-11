---
relaylm_doc_type: planning
relaylm_authority: documentation_cutover_preparation_tooling_and_dry_run_contract
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - cutover inventory schema changes
  - normative digest extraction changes
  - path dependency scan changes
  - preparation workflow changes
relaylm_not_authoritative_for:
  - current documentation placement
  - exact runtime behavior
  - proof that documentation cutover has started or completed
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
relaylm_verified_by:
  - ../../.github/workflows/documentation-cutover-preparation.yml
---
# Documentation Cutover Preparation Tooling

This document defines the Preparation C tooling and dry-run boundary. The tools inspect the frozen baseline and emit planning artifacts; they do not move, rewrite, or delete documentation.

## Baseline

The Preparation C baseline is the Preparation B merge commit:

```text
22981c3b26b2ec0141093d1ec23592d304f1a053
```

The full SHA is stored in `documentation-cutover-rules.yaml` and repeated explicitly by the workflow. A baseline change requires a reviewed rules update and regenerated artifacts; silently using the PR head is forbidden.

## Commands

```bash
python scripts/relaylm_docs_cutover_prepare.py \
  --baseline 22981c3b26b2ec0141093d1ec23592d304f1a053 \
  --rules docs/planning/documentation-cutover-rules.yaml \
  --output-dir generated/documentation-cutover \
  --strict

python scripts/relaylm_docs_normative_digest.py \
  --baseline 22981c3b26b2ec0141093d1ec23592d304f1a053 \
  --rules docs/planning/documentation-cutover-rules.yaml \
  --inventory generated/documentation-cutover/inventory.json \
  --output-dir generated/documentation-cutover \
  --strict

python scripts/relaylm_docs_relative_link_inventory.py \
  --baseline 22981c3b26b2ec0141093d1ec23592d304f1a053 \
  --output-dir generated/documentation-cutover \
  --strict
```

The GitHub Actions workflow checks out full history because provenance extraction uses Git history and rename following.

## Inventory outputs

### `inventory.json`

One record is emitted for every Markdown blob under `docs/` at the frozen baseline.

Each record includes:

- old path and Git blob SHA;
- normalized content SHA-256;
- current front-matter type, status, and authority when present;
- target document type and target paths;
- disposition and matching classification rule;
- normative-signal and migration-decision markers;
- manual section-map requirement;
- first-introduction commit, date, and source PR when derivable;
- literal repository-root path-dependency count.

The source PR may be `null` when commit history does not identify one unambiguously. The tool never invents a PR number.

### `migration-receipt-preview.json`

This preview contains the old path, old blob SHA, disposition, planned new paths, source provenance, and `pending_cutover` verification state. It is not the final frozen migration receipt.

The final receipt is produced only after actual moves, section synthesis, contract verification, link updates, and deletion decisions have completed.

### `summary.md`

The summary reports:

- total records;
- missing front matter;
- disposition, current type, and status counts;
- normative-signal candidates;
- manual section-map count;
- strict errors and non-blocking warnings.

### `path-dependencies.json` and `path-dependencies.md`

The repository-root dependency scan uses the frozen Git tree and finds literal references such as `docs/...md` across the repository.

References are classified as:

- workflow;
- script;
- root router;
- documentation;
- other repository file.

### `relative-path-dependencies.json` and `relative-path-dependencies.md`

The relative-link companion scan reads every frozen Markdown blob and resolves:

- inline Markdown links;
- reference-definition links;
- Markdown autolinks; and
- HTML `href` / `src` attributes whose destination resolves to Markdown.

Relative destinations are normalized against the referrer's directory. Fragments and query strings are removed for target resolution. External schemes, protocol-relative URLs, and links escaping the `docs/` tree are ignored.

The scan distinguishes:

- links resolving to an existing baseline Markdown target; and
- links resolving within `docs/` to an absent target, which are reported separately.

The workflow contains an explicit regression assertion that the frozen `docs/mvp/README.md` link to `mvp10_summary.md` resolves to `docs/mvp/mvp10_summary.md`. This protects the dependency class that was missed during Cutover 1B.

A path move or deletion must review both dependency inventories and update every workflow, script, root-router, absolute documentation reference, and relative Markdown link in the same PR. Neither inventory authorizes redirect stubs or dual live paths.

## Classification model

`documentation-cutover-rules.yaml` is an executable planning model, not an exception list for retaining the old architecture.

Rule order is significant:

1. exact path decisions from Preparation B;
2. compatibility-stub deletion decisions;
3. target collection, evidence, operations, contract, and known source-family rules;
4. architecture keyword fallback into an approved graph node;
5. final generic docs placement.

The output records the matched rule for review.

The architecture fallback is intentionally conservative: it maps a source into an approved graph node and marks it for manual section mapping. It does not assert that the source can be copied intact.

## Strict failures

The inventory command fails in strict mode when:

- a baseline document is unclassified;
- a disposition is unknown;
- a non-deletion has no target;
- a deletion lacks a Git-history-only reason;
- multiple targets lack a split or synthesized disposition;
- a target architecture path is outside the approved graph;
- a known normative source lacks a migration decision;
- two exclusive retained/moved/rebuilt sources claim one target;
- a configured known normative source is absent from the baseline.

The relative-link command fails in strict mode when a configured dependency regression assertion is absent. It reports unresolved relative Markdown targets for review without treating all historical broken links as an automatic cutover blocker.

The commands emit warnings, but do not fail, for:

- sources requiring manual section mapping;
- sources with normative signals that need block review;
- moving sources referenced by workflows, scripts, or root routers;
- relative links resolving to absent baseline Markdown targets.

Warnings become cutover work items. They are not permission to ignore the source.

## Normative digest outputs

### `normative-digests.json`

The normative digest tool reads source blobs from the same baseline and selects candidate sections using:

- normative heading terms;
- must/must-not, required, forbidden, exact, and Japanese equivalent patterns;
- contract document type;
- the configured known normative source list.

For each candidate block it records:

- source path and blob SHA;
- exact source line range;
- heading;
- selection reasons;
- byte and line counts;
- SHA-256 after newline normalization only.

The extractor is deliberately over-inclusive. Preserving additional source text is safer than omitting a normative paragraph.

### `normative-digests.md`

The review summary lists source files, blob prefixes, block counts, and migration decisions.

## Cutover verification use

During contract reconstruction, each selected source block must be copied verbatim. The cutover receipt records:

```yaml
old_path: docs/architecture/example_contract.md
old_blob_sha: <sha>
source_block_id: docs/architecture/example_contract.md#L40-L72
normative_digest_before: <sha256>
new_path: docs/contracts/example.md
new_start_line: 30
new_end_line: 62
normative_digest_after: <sha256>
verification: exact_match
```

A digest mismatch blocks the cutover PR. A desired wording change is a separate contract-change PR and must not be disguised as documentation migration.

## Reproducibility

The workflow runs all three tools twice into separate directories and requires a recursive zero diff. The artifacts exclude wall-clock generation time and use only baseline commit data, sorted paths, sorted mappings, and deterministic JSON serialization.

## CI artifact

`.github/workflows/documentation-cutover-preparation.yml` uploads `documentation-cutover-preparation` for 14 days and publishes the classification, normative-digest, and relative-link summaries to the workflow job summary.

The artifact is the Preparation C dry-run result. It remains non-authoritative planning evidence until reviewed and merged.

## Security and privacy

The tools read repository documentation and Git metadata only. They do not read runtime stores, user/model content, protected source bodies, credentials, caches, or local private paths. Output includes hashes, repository paths, and link destinations, not runtime content.

## Known limits

- Semantic section assignment cannot be made fully reliable from filenames or keyword matches. Sources marked `requires_manual_section_map` need human or bounded AI review before deletion.
- Source PR extraction depends on commit messages and may be absent.
- Normative selection is candidate extraction, not a proof that every selected paragraph is independently normative.
- The relative-link scanner intentionally does not implement the complete CommonMark grammar; unusual dynamically constructed or extension-specific links still require review.
- Generated config/CLI/API reference and drift checking remain a post-cutover track.

## Completion boundary

Preparation C is complete when:

- strict classification, normative extraction, and relative-link regression assertions are green;
- two-run reproducibility is green;
- the workflow artifact contains all declared outputs;
- every known normative source has at least one digest block;
- no target architecture path falls outside the Preparation B graph;
- unresolved warnings are visible as cutover work rather than hidden exceptions.

Preparation C completion still does not authorize canonical path moves before the v0.1 frozen tag receipt.
