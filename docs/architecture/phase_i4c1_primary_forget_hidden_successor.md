# Phase I-4C1 Primary Forget Hidden-Successor Commit

Status: complete for the bounded I-4C1 commit boundary.

## Scope

I-4C1 consumes one exact I-4B Forget apply token for a real current active
Primary MEM and establishes durable lifecycle commit ownership:

```text
exact token + exact bounded reason
  -> shared Correct / Forget per-memory lock
  -> exact current physical identity and revision reread
  -> immutable relaylm.mem.forget_prepared.v0
  -> deterministic relaymem.primary_lifecycle_page.v0 candidate
  -> existing M3c page-candidate boundary
  -> existing M3d writer-handoff boundary
  -> existing M3e atomic Primary page I/O
  -> canonical page reread and prepared/page chain verification
  -> hidden / recovery_required / retrieval_eligible=false
```

This phase does not run M3f or M3g, does not publish a Forget tombstone or an
applied receipt, does not resume a prepared operation after restart, and does
not claim ordinary M2 or RelayCTX exclusion is already enforced.

## Shared mutation authority

Correct and Forget use
`relaymem_primary_mutation_coordinator.primary_memory_mutation_lock` at the
existing `memory/mem/corrections/v0/<logical-memory-id>/.lock` location.  The
coordinator recognizes:

- Correct `prepared` and `applied` artifacts;
- Forget `prepared` artifacts;
- same operation ID with a different kind or binding as a conflict;
- unknown, noncanonical, duplicate-key, unsafe, ambiguous, and impossible
  revision evidence as corruption.

The lock-internal sequence is token validation, exact operation inspection,
current-state reread, revision claim, prepared publication, and hidden page
publication.  No lock-acquisition-time read made outside the lock is commit
authority.

## Prepared artifact

Schema: `relaylm.mem.forget_prepared.v0`.

The exact field set is:

```text
schema_version
runtime_private
content_included
operation_kind
operation_id
operation_key
binding_digest
character_id
namespace
memory_id
prior_revision
result_revision
prior_lifecycle_state
result_lifecycle_state
prior_physical_id
successor_physical_id
successor_candidate_id
successor_relative_path
prior_canonical_digest
successor_expected_canonical_digest
source_event_kind
memory_kind
lineage_fingerprint
reason
reason_digest
token_digest
requested_at
prepared_at
status
recovery_required
```

The bounded reason is repeated at apply time and remains runtime-private.  The
I-4B reason digest binding is not weakened.  Publication uses canonical UTF-8
JSON, exact keys, duplicate-key rejection, create-if-absent no-clobber
semantics, file fsync, directory fsync, canonical reread, bounded size, and
symlink/hardlink/unsafe-file rejection.

## Hidden lifecycle page

Schema: `relaymem.primary_lifecycle_page.v0`.

Existing active `relaymem.primary_page.v0` pages remain compatible.  The hidden
schema is strict and adds canonical lifecycle metadata:

```text
lifecycle_state = hidden
memory_id = stable logical identity
revision = prior_revision + 1
prior_revision
prior_physical_id
operation_kind = forget
operation_key
binding_digest
```

It preserves character/namespace scope through the prepared binding and page
namespace, and preserves source event, memory kind, and lineage continuity.
Reason, token, and ordinary memory content are not copied into the hidden page.
The page body is a fixed lifecycle projection, not a hidden marker embedded in
free-form memory text.

## Determinism and M3e commit point

The candidate and physical identities bind the logical memory ID, prior
physical ID and revision, result revision, namespace, character, operation key,
binding digest, target hidden lifecycle, source event kind, memory kind, and
lineage fingerprint.  Time and randomness are not identity authority.

The I-4C1 commit point is reached only when all are true:

1. the exact Forget prepared artifact is durable;
2. the expected hidden successor was newly published by M3e or the exact same
   canonical page was already present;
3. the M3e receipt identity, path, and digest match the prepared artifact;
4. the page was canonically reread;
5. lifecycle, revision, prior-physical, operation, scope, and lineage linkage
   all match.

After that point the resolver returns:

```text
lifecycle_state = hidden
mutation_state = recovery_required
retrieval_eligible = false
```

Controls can still point to the prior active page because M3f/M3g are outside
this phase.  The resolver never falls back to that prior active page after an
exact hidden commit.

## Prepared-only state

When the prepared artifact exists and the hidden page does not, the resolver
returns:

```text
lifecycle_state = active
mutation_state = prepared
retrieval_eligible = false
```

This is durable continuation evidence for I-4C2.  I-4C1 intentionally does not
resume the operation.

## Content-free result

`PrimaryForgetCommitResult` exposes only bounded state and revision facts.  Its
`repr` and log projection exclude title, summary, reason, character, namespace,
logical and physical IDs, operation identifiers, tokens, digests, lineage,
store paths, nested prepared artifacts, nested M3e receipts, and raw exceptions.

## Fault seams

The production helper exposes deterministic test seams at:

```text
after_lock_before_revision_reread
after_revision_claim_before_prepared
after_prepared_publication
before_hidden_successor_publication
after_hidden_successor_publication_before_reread
after_hidden_successor_reread_before_return
```

A post-prepare fault leaves `active / prepared / false`.  A post-page fault
leaves `hidden / recovery_required / false`.  Neither state is rolled back.

## Still unimplemented

- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence,
  forward-only recovery, response-loss replay, and tombstone authority are complete;
- I-4D ordinary M2/RelayCTX hidden and prior-revision exclusion is unimplemented;
- I-4E loopback API and SOUL Lab UI;
- I-4F full crash/response-loss validation;
- restore/unhide, physical deletion, secure erase, Pin/Unpin,
  Merge/Supersession, Held Apply/Discard, Secondary consolidation, and
  RelaySOUL mutation.

I-4C1 therefore completes hidden-successor commit ownership. I-4C2 now completes
the bounded recovery/finalization continuation, but Phase I-4 as a whole and
product-complete Forget behavior remain incomplete until I-4D through I-4F.
