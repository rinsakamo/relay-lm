import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { loadLabObservation, LabObservationError } from "../.observation-smoke/observationApi.js";

const characterId = "default";
const namespace = "phase-i2";
const memoryId = "a".repeat(64);

function fixtures() {
  return {
    latest: {
      schema: "relaylm.lab.last_run.v0",
      source: "relaylm_runtime",
      read_only: true,
      availability: "available",
      capability: "latest_completed_managed_run",
      character_id: characterId,
      namespace,
      run_id: "run-1",
      status: "completed",
      started_at: "2026-06-24T08:00:00+00:00",
      completed_at: "2026-06-24T08:00:01+00:00",
      duration_ms: 1000,
      response_mode: "non_stream",
      slp_status: "disabled",
      memory_outcome_status: "formed",
      relayrun_status: "completed",
      relayctx_repack_status: "applied",
      relayctx_unpack_status: "not_observed",
      formed_count: 1,
      held_count: 0,
      blocked_count: 0,
      used_memory_count: 1,
      recovery_required: false,
      bounded_reason_ids: [],
    },
    recent: {
      schema: "relaylm.lab.memory_recent.v0",
      source: "relaylm_runtime",
      read_only: true,
      availability: "available",
      capability: "validated_primary_memory_read",
      character_id: characterId,
      namespace,
      limit: 20,
      next_cursor: null,
      items: [
        {
          memory_id: memoryId,
          layer: "primary",
          status: "formed",
          title: "Tea preference",
          bounded_summary: "The user prefers tea.",
          confidence_label: "not_recorded",
          scope_label: "character_namespace",
          formed_at: null,
          pinned: false,
          source_kind: "preference",
        },
      ],
      bounded_reason_ids: [],
    },
    held: {
      schema: "relaylm.lab.memory_held.v0",
      source: "relaylm_runtime",
      read_only: true,
      availability: "empty",
      capability: "durable_memory_outcome_read",
      character_id: characterId,
      namespace,
      limit: 20,
      next_cursor: null,
      items: [],
      bounded_reason_ids: [],
    },
    used: {
      schema: "relaylm.lab.memory_used.v0",
      source: "relaylm_runtime",
      read_only: true,
      availability: "available",
      capability: "backend_bound_memory_evidence_read",
      character_id: characterId,
      namespace,
      run_id: "run-1",
      retrieval_attempted: true,
      candidate_discovered: true,
      selected: true,
      relayctx_injection_performed: true,
      backend_bound_included: true,
      response_generation_completed: true,
      items: [
        {
          memory_id: memoryId,
          injected_summary: "The user prefers tea.",
          current_summary: "The user prefers tea.",
          representation_changed: false,
          source_kind: "preference",
        },
      ],
      bounded_reason_ids: [],
    },
  };
}

function clone(value) {
  return structuredClone(value);
}

function installFetch(values, failureStatus = null) {
  globalThis.fetch = async (input) => {
    const url = String(input);
    if (failureStatus !== null) {
      return new Response(JSON.stringify({ detail: "bounded_failure" }), {
        status: failureStatus,
        headers: { "content-type": "application/json" },
      });
    }
    let value;
    if (url.includes("/memory/recent")) value = values.recent;
    else if (url.includes("/memory/held")) value = values.held;
    else if (url.includes("/memory/used")) value = values.used;
    else value = values.latest;
    return new Response(JSON.stringify(value), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
}

async function expectRejected(mutator, expectedCode = "invalid_lab_observation_schema") {
  const values = fixtures();
  mutator(values);
  installFetch(values);
  await assert.rejects(
    loadLabObservation(characterId, namespace),
    (error) => error instanceof LabObservationError && error.code === expectedCode,
  );
}

installFetch(fixtures());
const accepted = await loadLabObservation(characterId, namespace);
assert.equal(accepted.latestRun.run_id, "run-1");
assert.equal(accepted.recent.items.length, 1);
assert.equal(accepted.used.items.length, 1);

await expectRejected((value) => delete value.latest.status);
await expectRejected((value) => { value.recent.unexpected = true; });
await expectRejected((value) => { value.held.schema = "relaylm.lab.memory_held.v999"; });
await expectRejected((value) => { value.used.selected = "yes"; });
await expectRejected((value) => { value.recent.items[0].bounded_summary = "x".repeat(513); });
await expectRejected((value) => { value.latest.status = "running"; });
await expectRejected((value) => { value.recent.character_id = "other"; });
await expectRejected(
  (value) => { value.used.run_id = "run-other"; },
  "mixed_lab_observation_run",
);
await expectRejected((value) => { value.used.items[0].injected_summary = "unsafe\u2028text"; });

installFetch(fixtures(), 403);
await assert.rejects(
  loadLabObservation(characterId, namespace),
  (error) => error instanceof LabObservationError && error.code === "lab_observation_access_refused",
);

installFetch(fixtures(), 500);
await assert.rejects(
  loadLabObservation(characterId, namespace),
  (error) => error instanceof LabObservationError && error.code === "lab_observation_http_500",
);

const componentSource = await fs.readFile(
  new URL("../src/features/lab/ConnectedLabObservationPage.tsx", import.meta.url),
  "utf8",
);
assert.match(componentSource, /new AbortController\(\)/);
assert.match(componentSource, /generation\.current === requestGeneration/);
assert.match(componentSource, /controller\.abort\(\)/);
assert.match(componentSource, /Source: RelayLM runtime/);
assert.match(componentSource, /Local preview data/);
assert.doesNotMatch(componentSource, /dangerouslySetInnerHTML/);

console.log("SOUL Lab observation browser schema smoke passed");
