# Common physical generation certificate

RelayLM branches may carry the branch-neutral physical execution control plane at different qualified generations. The checked-in certificate at `.ai/physical/common_generation.json` makes that divergence explicit without synchronizing `v1` and `v2`.

## Authority

A generation certificate records:

- one stable `generation_id`;
- the exact branch-neutral surface paths and their generated Git blob OIDs;
- a deterministic aggregate identity over that ordered surface;
- the protected commit/tree from which the generation was promoted;
- promotion and predecessor provenance.

The Git blob OIDs are generated evidence, not a second handwritten specification. `tools/physical_common_generation.py generate` derives them from checkout bytes. Runtime verification does not need the historical origin object: it hashes the current checkout bytes using Git blob framing and compares those identities with the immutable certificate. This remains usable in shallow or partial checkouts where the origin commit object is unavailable.

The aggregate is SHA-256 over this byte stream:

```text
"relay-lm-common-physical-generation-v1\0"
+ for each surface entry in strict path order:
    UTF8(path) + "\0" + ASCII(git_blob_oid) + "\n"
```

The certificate itself and the verifier/generator are deliberately outside the aggregate so generation identity is non-recursive.

## Certified boundary

The generation includes only branch-neutral HOW: the physical Python policy, common environment/runner/queue/smoke-target implementations, their branch-neutral unit/integration contract tests, and the common queue skill/reference contract.

The following are intentionally outside generation identity:

- `.ai/physical/llama_cpp_targets.json` — branch-local target carriage;
- `.ai/authority/physical_execution_queue.yaml` — branch-local authority/carriage metadata;
- `tools/v1_*`, `tools/v2_*`, experiment/scientific target modules and their tests;
- THIS-RUN / exactly-once spend state and causal/scientific interpretation;
- `.ai/physical/common_generation.json` and `tools/physical_common_generation.py` themselves.

A change to a certified path therefore makes the existing generation fail verification. The change must either be promoted as a new common generation or explicitly classified outside common HOW.

## Verification

From repository root:

```bash
python3.12 -m tools.physical_common_generation verify
```

Success prints the generation id, aggregate identity, origin commit, and origin tree as JSON. Any malformed schema, path normalization problem, aggregate mismatch, missing/non-regular certified file, or current-byte blob drift fails closed with exit status 2.

Consumers may pin both identity coordinates:

```bash
python3.12 -m tools.physical_common_generation verify \
  --expect-generation-id relay-common-physical-g1 \
  --expect-aggregate-identity sha256:786b39f297b3330526e36115b0f8fa56d829d3adb4fc5913af3f385cd05eadc2
```

A generation id is not allowed to name two aggregate identities. `assert_generation_id_consistent()` enforces that invariant when declarations are compared or imported.

## Regeneration

Generation creation is an explicit promotion operation, never an import/test/help/preflight side effect. After qualifying a new branch-neutral common surface, invoke the generator with the fresh protected origin and predecessor provenance, review the resulting declaration, and assign a new generation id:

```bash
python3.12 -m tools.physical_common_generation generate \
  --generation-id <new-generation-id> \
  --origin-commit <fresh-protected-commit> \
  --origin-tree <fresh-protected-tree> \
  --promotion-owner <promotion-issue-number> \
  --predecessor-issue <predecessor-issue-number> \
  --predecessor-commit <qualified-predecessor> \
  --output .ai/physical/common_generation.json
```

`promotion_owner` and `predecessor_issue` are positive issue numbers carried as provenance; the common generator does not hard-code the bootstrap #2750/#2731 pair. Branches may carry different generation ids legitimately. Target registries and scientific campaigns do not affect common-generation identity.

## Bootstrap lineage

`relay-common-physical-g1` promotes the hardened common HOW merged by #2763 under #2760. Its origin is protected-v2 commit `10324f14bad1882d62544aa22272733f90f2f5b0`, tree `afdc87a13371f9bec0d9cd55f9fe1dfed3c16dff`. PR #2731 commit `a073362fbd7b455e8387021b9394b156b024e467` is recorded only as predecessor lineage; raw #2731 was deliberately not promoted after the #2750 review exposed defects subsequently repaired by #2760/#2763.

This authority performs no provider/model/GPU/llama.cpp execution and carries no scientific result.
