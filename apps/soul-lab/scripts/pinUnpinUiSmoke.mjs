import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const labSourceRoot = new URL("../src/features/lab/", import.meta.url);
const temp = await mkdtemp(join(tmpdir(), "relaylm-pin-ui-"));
const memoryId = "b".repeat(64);

async function emit(name) {
  const source = await readFile(new URL(name, labSourceRoot), "utf8");
  const result = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022, jsx: ts.JsxEmit.ReactJSX, strict: true },
    fileName: name,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter((diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error);
  assert.equal(errors.length, 0, `transpile diagnostics in ${name}`);
  await writeFile(join(temp, name.replace(/\.tsx?$/, ".js")), result.outputText, "utf8");
}

try {
  await mkdir(temp, { recursive: true });
  await writeFile(join(temp, "package.json"), '{"type":"module"}\n', "utf8");
  await emit("pinApi.ts");
  const api = await import(pathToFileURL(join(temp, "pinApi.js")).href);
  const preflight = {
    schema: "relaylm.lab.memory_pin_preflight.v0",
    status: "ready",
    operation_kind: "pin",
    read_only: true,
    memory_id: memoryId,
    current_revision: 1,
    current_lifecycle_state: "active",
    current_mutation_state: "none",
    current_pin_state: "unpinned",
    target_pin_state: "pinned",
    pin_state_contract_only: false,
    effects: {
      audit_evidence_retained: true,
      future_priority_hint_contract: true,
      ordinary_retrieval_deleted: false,
      ordinary_retrieval_excluded: false,
      physical_deletion: false,
      semantic_content_changed: false,
    },
    apply_token: "token.safe-1",
    expires_at: "2026-06-27T00:05:00Z",
  };
  assert.deepEqual(api.parsePinPreflight(preflight, "pin", memoryId, 1), preflight);
  assert.equal(api.parsePinPreflight({ ...preflight, token_claims: { secret: true } }, "pin", memoryId, 1), null);
  assert.equal(api.parsePinPreflight({ ...preflight, effects: { ...preflight.effects, ordinary_retrieval_excluded: true } }, "pin", memoryId, 1), null);
  const receipt = {
    schema: "relaylm.lab.memory_pin_apply.v0",
    status: "applied",
    operation_kind: "pin",
    memory_id: memoryId,
    current_revision: 1,
    current_lifecycle_state: "active",
    current_mutation_state: "none",
    prior_pin_state: "unpinned",
    target_pin_state: "pinned",
    retrieval_eligible: true,
    ordinary_retrieval_excluded: false,
    priority_hint_enabled: true,
    semantic_content_changed: false,
    physical_deletion: false,
    audit_evidence_retained: true,
    idempotent_replay: false,
    effect_applied: true,
    receipt_id: "c".repeat(64),
    content_included: false,
    path_included: false,
    physical_id_included: false,
    reason_included: false,
    token_included: false,
  };
  assert.deepEqual(api.parsePinApply(receipt, "pin", memoryId, 1), receipt);
  assert.equal(api.parsePinApply({ ...receipt, physical_id: "secret" }, "pin", memoryId, 1), null);
  const captures = [];
  await api.preflightMemoryPin("char", "ns", memoryId, { expectedRevision: 1, reason: "runtime private audit reason", operationId: "op-1" }, new AbortController().signal, async (url, init) => {
    captures.push({ url, init });
    return new Response(JSON.stringify(preflight), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  assert.equal(captures.length, 1, "preflight does not apply");
  assert.equal(captures[0].url, `/lab/api/characters/char/memory/${memoryId}/pin/preflight?namespace=ns`);
  const body = JSON.parse(captures[0].init.body);
  for (const forbidden of ["store_root", "filesystem_path", "route_authority", "token_claims", "physical_id"]) assert.equal(forbidden in body, false, forbidden);
  await assert.rejects(api.applyMemoryPin("char", "ns", memoryId, { expectedRevision: 1, reason: "private reason should not render", operationId: "op-1", applyToken: "token.safe-1" }, new AbortController().signal, async () => new Response(JSON.stringify({ detail: "token_expired" }), { status: 409 })), (error) => error.name === "MemoryPinError" && error.code === "token_expired" && !String(error.message).includes("private reason"));
  const panelSource = await readFile(new URL("PrimaryMemoryPinPanel.tsx", labSourceRoot), "utf8");
  assert.match(panelSource, /onClick=\{\(\) => void confirmApply\(\)\}/);
  assert.match(panelSource, /明示的にPin \/ Unpinを適用/);
  assert.match(panelSource, /generation\.current === currentGeneration/);
  assert.match(panelSource, /AbortController/);
  assert.equal(panelSource.includes("dangerouslySetInnerHTML"), false);
  assert.equal(panelSource.includes("onMouseEnter"), false);
  assert.equal(panelSource.includes("token_claims"), false);
  const connectedSource = await readFile(new URL("ConnectedLabObservationPage.tsx", labSourceRoot), "utf8");
  assert.match(connectedSource, /PrimaryMemoryPinPanel/);
  assert.match(connectedSource, /kind: "pin"/);
  assert.match(connectedSource, /Pin \/ Unpin/);
  assert.match(connectedSource, /I-5B adds only the Pin \/ Unpin API\/UI/);
  assert.equal(connectedSource.includes("hidden retrieval"), true);
} finally {
  await rm(temp, { recursive: true, force: true });
}

console.log("Phase I-5B Pin/Unpin UI smoke passed");
