import assert from "node:assert/strict";
import {
  loadUsedMemoryLifecycle,
  parseUsedMemoryLifecycle,
  UsedMemoryLifecycleError,
} from "../.used-memory-lifecycle-smoke/usedMemoryLifecycleApi.js";

const characterId = "default";
const namespace = "phase-i4d";
const memoryId = "a".repeat(64);

function fixture() {
  return {
    schema: "relaylm.lab.memory_used_lifecycle.v1",
    source: "relaylm_runtime",
    read_only: true,
    availability: "available",
    capability: "backend_bound_memory_evidence_with_current_lifecycle",
    character_id: characterId,
    namespace,
    run_id: "run-i4d",
    retrieval_attempted: true,
    candidate_discovered: true,
    selected: true,
    relayctx_injection_performed: true,
    backend_bound_included: true,
    response_generation_completed: true,
    items: [{
      memory_id: memoryId,
      injected_summary: "The user prefers tea.",
      current_summary: null,
      current_lifecycle_state: "hidden",
      representation_changed: false,
      lifecycle_changed: true,
      source_kind: "preference",
    }],
    bounded_reason_ids: [],
  };
}

function clone(value) {
  return structuredClone(value);
}

let current = fixture();
globalThis.fetch = async () => new Response(JSON.stringify(current), {
  status: 200,
  headers: { "content-type": "application/json" },
});
const accepted = await loadUsedMemoryLifecycle(characterId, namespace);
assert.equal(accepted.items[0].current_lifecycle_state, "hidden");
assert.equal(accepted.items[0].injected_summary, "The user prefers tea.");
assert.equal(accepted.items[0].current_summary, null);

for (const mutate of [
  (value) => { delete value.items[0].lifecycle_changed; },
  (value) => { value.items[0].current_lifecycle_state = "deleted"; },
  (value) => { value.items[0].current_summary = "must be null while hidden"; },
  (value) => { value.items[0].injected_summary = "x".repeat(513); },
  (value) => { value.unexpected = true; },
  (value) => { value.schema = "relaylm.lab.memory_used_lifecycle.v2"; },
]) {
  const invalid = clone(fixture());
  mutate(invalid);
  assert.equal(parseUsedMemoryLifecycle(invalid), null);
}

current = fixture();
current.character_id = "other";
await assert.rejects(
  loadUsedMemoryLifecycle(characterId, namespace),
  (error) => error instanceof UsedMemoryLifecycleError &&
    error.code === "invalid_used_memory_lifecycle_schema",
);

globalThis.fetch = async () => new Response("{}", { status: 403 });
await assert.rejects(
  loadUsedMemoryLifecycle(characterId, namespace),
  (error) => error instanceof UsedMemoryLifecycleError &&
    error.code === "used_memory_lifecycle_access_refused",
);

globalThis.fetch = async () => new Response("{}", { status: 500 });
await assert.rejects(
  loadUsedMemoryLifecycle(characterId, namespace),
  (error) => error instanceof UsedMemoryLifecycleError &&
    error.code === "used_memory_lifecycle_http_500",
);

console.log("SOUL Lab used-memory lifecycle browser schema smoke passed");
