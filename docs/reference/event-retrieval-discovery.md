# Targeted Event discovery

This document is the current authority for retrieval-scaled lexical discovery over persisted Event evidence.

## Authority boundary

`memory/events.jsonl` remains the only occurrence/provenance authority. The process-local `EventDiscoveryIndex` is derived acceleration over an already validated `CharacterDirectory` Event snapshot. It is not persisted, cannot establish that an Event occurred, and is always disposable/rebuildable from the Journal.

The persistence boundary owns index lifetime:

- first access in a `CharacterDirectory` validates the authoritative Event Journal before building discovery;
- an unchanged Journal reuses the validated snapshot and its derived discovery index;
- a RelayLM-owned append extends both the validated snapshot and the derived index after the JSONL append succeeds;
- reopening a Character Package starts with no derived index and rebuilds from the authoritative Journal;
- an external file signature change invalidates the derived index together with the validated snapshot and forces authoritative JSONL revalidation before a replacement index can be used;
- malformed externally changed Journal data raises `CharacterDataError`; previously cached discovery is not allowed to hide it.

The existing Journal signature boundary remains `(device, inode, size, mtime_ns)`. The discovery index has no independent persistence or validity claim.

## Discovery and selection

The derived index records lexical-feature postings only for eligible non-blank `message` Events plus aggregate eligibility metadata needed by the existing content-free diagnostics. Query-time discovery visits postings for the normalized positive query features instead of iterating every Event in the validated snapshot.

The shared retrieval feature rule is defined in `docs/reference/retrieval-lexical-relevance.md`: existing normalized whole tokens are preserved, while contiguous CJK runs additionally contribute bounded 2- and 3-character n-grams. Latin/ASCII tokens do not gain substring features.

After discovery, `select_event_evidence(...)` retains the existing selector contract:

- only positive shared lexical-feature matches are candidates;
- explicit Event IDs, including the Current Event ID, are excluded before ranking/admission;
- higher lexical overlap ranks first;
- equal scores prefer the newer Journal occurrence;
- whole Events are admitted under the explicit Event and character budgets; content is never truncated;
- selected Events are returned in Journal chronology;
- diagnostics remain content-free and preserve their existing aggregate meanings.

The generic iterable selector path remains valid for callers that do not have a `CharacterDirectory` discovery source. It uses the same shared lexical features and necessarily inspects its supplied iterable. Ordinary-turn targeted Event retrieval uses `CharacterDirectory.event_retrieval_source()` so it receives the indexed path without changing runtime budget defaults.

## Scaling boundary

For a validated, unchanged process-local Journal snapshot, targeted lexical discovery no longer performs unconditional O(N) Event inspection. It reads postings for the query features and materializes only positive candidates; work therefore scales with matching postings/candidates rather than the full Event count. A feature that legitimately occurs in most Events can still produce O(N) matching work.

The following operations intentionally remain full-authority work and are not hidden by the index:

- initial Journal validation in a fresh `CharacterDirectory`;
- Journal revalidation after reopen or external mutation;
- rebuilding the derived index after such invalidation.

This change does not introduce semantic/vector retrieval, alter MEMORY/State authority, or add another cognitive LLM generation.

## Deferred

Persistent or segmented indexes, semantic/vector retrieval, broader semantic ranking, total token-aware runtime budgeting, and cross-layer redundancy policy remain outside this boundary. Any future persistent acceleration must remain derived from and invalidatable against the Event Journal rather than becoming a second occurrence/provenance authority.
