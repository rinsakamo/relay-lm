import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {
  applyMemoryCorrection,
  loadMemoryCorrectionHistory,
  MemoryCorrectionError,
  preflightMemoryCorrection,
} from "../.correction-smoke/correctionApi.js";

const characterId = "default";
const namespace = "phase-i3";
const memoryId = "a".repeat(64);
const correctionId = "b".repeat(64);
const preflightValue = {
  schema: "relaylm.lab.memory_correct_preflight.v0",
  status: "ready",
  read_only: true,
  memory_id: memoryId,
  current_revision: 1,
  candidate_revision: 2,
  diff: {
    title_changed: true,
    summary_changed: true,
    before: { title: "Tea", summary: "Tea is preferred." },
    after: { title: "Coffee", summary: "Coffee is preferred." },
  },
  apply_token: "opaque.token",
  expires_at: "2026-06-24T12:05:00Z",
};
const applyValue = {
  schema: "relaylm.lab.memory_correct_apply.v0",
  status: "applied",
  memory_id: memoryId,
  prior_revision: 1,
  result_revision: 2,
  correction_id: correctionId,
  reconciled: true,
  recovery_required: false,
  idempotent_replay: false,
  applied_at: "2026-06-24T12:01:00Z",
};
const historyValue = {
  schema: "relaylm.lab.memory_corrections.v0",
  source: "relaylm_runtime",
  read_only: true,
  memory_id: memoryId,
  current_revision: 2,
  correction_count: 1,
  last_corrected_at: "2026-06-24T12:01:00Z",
  last_correction_status: "reconciled",
  has_prior_revision: true,
  items: [{
    correction_id: correctionId,
    prior_revision: 1,
    result_revision: 2,
    reason: "explicit correction",
    status: "reconciled",
    applied_at: "2026-06-24T12:01:00Z",
    title_changed: true,
    summary_changed: true,
  }],
};

let responseValue = preflightValue;
let lastRequest = null;
globalThis.fetch = async (input, init = {}) => {
  lastRequest = { input: String(input), init };
  return new Response(JSON.stringify(responseValue), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
};

const preflight = await preflightMemoryCorrection(characterId, namespace, memoryId, {
  expectedRevision: 1,
  correctedTitle: "Coffee",
  correctedSummary: "Coffee is preferred.",
  reason: "explicit correction",
  operationId: "operation-1",
});
assert.equal(preflight.candidate_revision, 2);
assert.equal(lastRequest.init.method, "POST");
assert.equal(lastRequest.init.headers["Content-Type"], "application/json");
assert.equal(lastRequest.init.credentials, "same-origin");
assert.deepEqual(Object.keys(JSON.parse(lastRequest.init.body)).sort(), [
  "corrected_summary", "corrected_title", "expected_revision", "operation_id", "reason", "schema",
].sort());

responseValue = applyValue;
assert.equal((await applyMemoryCorrection(characterId, namespace, memoryId, {
  expectedRevision: 1,
  operationId: "operation-1",
  applyToken: "opaque.token",
})).result_revision, 2);
responseValue = historyValue;
assert.equal((await loadMemoryCorrectionHistory(characterId, namespace, memoryId)).correction_count, 1);

async function rejectSchema(value, call) {
  responseValue = value;
  await assert.rejects(call, (error) =>
    error instanceof MemoryCorrectionError && error.code === "schema_invalid");
}
const missing = structuredClone(preflightValue);
delete missing.status;
await rejectSchema(missing, () => preflightMemoryCorrection(characterId, namespace, memoryId, {
  expectedRevision: 1, correctedTitle: "x", correctedSummary: "y", reason: "z", operationId: "op",
}));
const unexpected = structuredClone(preflightValue);
unexpected.unexpected = true;
await rejectSchema(unexpected, () => preflightMemoryCorrection(characterId, namespace, memoryId, {
  expectedRevision: 1, correctedTitle: "x", correctedSummary: "y", reason: "z", operationId: "op",
}));
const wrongRevision = structuredClone(applyValue);
wrongRevision.result_revision = 3;
await rejectSchema(wrongRevision, () => applyMemoryCorrection(characterId, namespace, memoryId, {
  expectedRevision: 1, operationId: "op", applyToken: "token",
}));

globalThis.fetch = async () => new Response("{}", { status: 403 });
await assert.rejects(
  preflightMemoryCorrection(characterId, namespace, memoryId, {
    expectedRevision: 1, correctedTitle: "x", correctedSummary: "y", reason: "z", operationId: "op",
  }),
  (error) => error instanceof MemoryCorrectionError && error.code === "access_refused",
);

const connectedSource = await fs.readFile(
  new URL("../src/features/lab/ConnectedLabObservationPage.tsx", import.meta.url), "utf8");
const panelSource = await fs.readFile(
  new URL("../src/features/lab/PrimaryMemoryCorrectPanel.tsx", import.meta.url), "utf8");
assert.match(connectedSource, /if \(mockFallback\)/);
assert.match(connectedSource, /PrimaryMemoryCorrectPanel/);
assert.match(connectedSource, /generation\.current === requestGeneration/);
assert.match(panelSource, /generation\.current === currentGeneration/);
assert.match(panelSource, /state\.kind === "apply-loading"/);
assert.match(panelSource, /Confirm apply/);
assert.doesNotMatch(connectedSource + panelSource, /dangerouslySetInnerHTML|innerHTML/);

console.log("SOUL Lab correction browser schema smoke passed");
