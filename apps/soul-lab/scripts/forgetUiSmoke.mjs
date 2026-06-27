import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const labSourceRoot = new URL("../src/features/lab/", import.meta.url);
const temp = await mkdtemp(join(tmpdir(), "relaylm-forget-ui-"));
const memoryId = "a".repeat(64);

async function emit(name) {
  const source = await readFile(new URL(name, labSourceRoot), "utf8");
  const result = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022, strict: true },
    fileName: name,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter((diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error);
  assert.equal(errors.length, 0, `transpile diagnostics in ${name}`);
  await writeFile(join(temp, name.replace(/\.ts$/, ".js")), result.outputText, "utf8");
}

try {
  await mkdir(temp, { recursive: true });
  await writeFile(join(temp, "package.json"), '{"type":"module"}\n', "utf8");
  await emit("forgetApi.ts");
  const api = await import(pathToFileURL(join(temp, "forgetApi.js")).href);

  const preflight = {
    schema: "relaylm.lab.memory_forget_preflight.v0",
    status: "ready",
    read_only: true,
    memory_id: memoryId,
    current_revision: 3,
    current_lifecycle_state: "active",
    target_revision: 4,
    target_lifecycle_state: "hidden",
    effects: {
      audit_evidence_retained: true,
      historical_used_memory_unchanged: true,
      ordinary_retrieval_excluded: true,
      physical_deletion: false,
      relayctx_injection_excluded: true,
    },
    apply_token: "token.safe-1",
    expires_at: "2026-06-27T00:05:00Z",
  };
  assert.deepEqual(api.parseForgetPreflight(preflight, memoryId, 3), preflight);
  assert.equal(api.parseForgetPreflight({ ...preflight, token_claims: { secret: true } }, memoryId, 3), null);
  assert.equal(api.parseForgetPreflight({ ...preflight, effects: { ...preflight.effects, physical_deletion: true } }, memoryId, 3), null);

  const receipt = {
    schema: "relaylm.lab.memory_forget_apply.v0",
    status: "applied",
    memory_id: memoryId,
    prior_revision: 3,
    result_revision: 4,
    lifecycle_state: "hidden",
    mutation_state: "none",
    retrieval_eligible: false,
    ordinary_retrieval_excluded: true,
    relayctx_injection_excluded: true,
    physical_deletion: false,
    audit_evidence_retained: true,
    historical_used_memory_unchanged: true,
    page_converged: true,
    index_converged: true,
    log_converged: true,
    tombstone_present: true,
    tombstone_created: true,
    idempotent_replay: false,
    recovery_required: false,
    reason_ids: [],
  };
  assert.deepEqual(api.parseForgetApply(receipt, memoryId, 3), receipt);
  assert.equal(api.parseForgetApply({ ...receipt, physical_id: "secret" }, memoryId, 3), null);

  const history = {
    schema: "relaylm.lab.memory_forget_history.v0",
    source: "relaylm_runtime",
    read_only: true,
    memory_id: memoryId,
    current_revision: 4,
    current_lifecycle_state: "hidden",
    forget_count: 1,
    items: [{ status: "applied", prior_revision: 3, result_revision: 4 }],
  };
  assert.deepEqual(api.parseForgetHistory(history, memoryId), history);
  assert.equal(api.parseForgetHistory({ ...history, items: [{ reason: "leak" }] }, memoryId), null);

  const captures = [];
  const fetchImpl = async (url, init) => {
    captures.push({ url, init });
    return new Response(JSON.stringify(preflight), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  await api.preflightMemoryForget("char", "ns", memoryId, {
    expectedRevision: 3,
    expectedLifecycleState: "active",
    reason: "runtime private audit reason",
    operationId: "op-1",
  }, new AbortController().signal, fetchImpl);
  assert.equal(captures.length, 1, "preflight does not apply");
  assert.equal(captures[0].url, `/lab/api/characters/char/memory/${memoryId}/forget/preflight?namespace=ns`);
  assert.equal(captures[0].init.credentials, "same-origin");
  assert.equal(captures[0].init.cache, "no-store");
  assert.equal(captures[0].init.headers["Content-Type"], "application/json");
  const body = JSON.parse(captures[0].init.body);
  for (const forbidden of ["store_root", "filesystem_path", "route_authority", "token_claims", "physical_id"]) {
    assert.equal(forbidden in body, false, forbidden);
  }

  const applyCaptures = [];
  const applyFetch = async (url, init) => {
    applyCaptures.push({ url, init });
    return new Response(JSON.stringify(receipt), { status: 200 });
  };
  await api.applyMemoryForget("char", "ns", memoryId, {
    expectedRevision: 3,
    expectedLifecycleState: "active",
    reason: "runtime private audit reason",
    operationId: "op-1",
    applyToken: "token.safe-1",
  }, new AbortController().signal, applyFetch);
  assert.equal(applyCaptures[0].url, `/lab/api/characters/char/memory/${memoryId}/forget?namespace=ns`);

  await assert.rejects(
    api.applyMemoryForget("char", "ns", memoryId, {
      expectedRevision: 3,
      expectedLifecycleState: "active",
      reason: "private reason should not render",
      operationId: "op-1",
      applyToken: "token.safe-1",
    }, new AbortController().signal, async () => new Response(JSON.stringify({ detail: "token_expired" }), { status: 409 })),
    (error) => error.name === "MemoryForgetError" && error.code === "token_expired" && !String(error.message).includes("private reason"),
  );

  const panelSource = await readFile(new URL("PrimaryMemoryForgetPanel.tsx", labSourceRoot), "utf8");
  assert.match(panelSource, /onClick=\{\(\) => void confirmApply\(\)\}/);
  assert.match(panelSource, /明示的にForgetを適用/);
  assert.match(panelSource, /generation\.current === currentGeneration/);
  assert.match(panelSource, /AbortController/);
  assert.equal(panelSource.includes("dangerouslySetInnerHTML"), false);
  assert.equal(panelSource.includes("onMouseEnter"), false);
  assert.equal(panelSource.includes("token_claims"), false);

  const pageSource = await readFile(new URL("ConnectedLabObservationPage.tsx", labSourceRoot), "utf8");
  assert.match(pageSource, /loadUsedMemoryLifecycle/);
  assert.match(pageSource, /setMockFallback\(false\)/);
  assert.match(pageSource, /Correct \/ Forget/);
  assert.equal(pageSource.includes("dangerouslySetInnerHTML"), false);
} finally {
  await rm(temp, { recursive: true, force: true });
}

console.log("Phase I-4E Forget UI smoke passed");
