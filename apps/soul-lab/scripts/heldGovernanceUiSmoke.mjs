import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const labSourceRoot = new URL("../src/features/lab/", import.meta.url);
const temp = await mkdtemp(join(tmpdir(), "relaylm-held-governance-ui-"));
const candidateId = "held-candidate-ui";

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
  await emit("heldGovernanceApi.ts");
  const api = await import(pathToFileURL(join(temp, "heldGovernanceApi.js")).href);

  const preflight = {
    schema: "relaylm.lab.held_governance_preflight.v0",
    status: "ready",
    action: "apply",
    read_only: true,
    candidate_id_short: "held-candidate-ui",
    operation_id_short: "ui-op-1",
    reason_code: "ready",
    blocked_reason_ids: [],
    effects: {
      held_item_adopted_contract: true,
      held_item_discarded_contract: false,
      queue_state_mutated: false,
      primary_mem_mutated: false,
      worker_started: false,
      scheduler_started: false,
      automatic_retry_or_release: false,
      runtime_private_content_exposed: false,
    },
    already_applied: false,
    already_discarded: false,
    content_free: true,
    runtime_private_evidence_omitted: true,
    source_body_included: false,
    model_output_included: false,
    memory_content_included: false,
    queue_payload_included: false,
    primary_page_path_included: false,
    store_root_included: false,
    queue_root_included: false,
    claim_token_included: false,
    lease_owner_included: false,
    raw_exception_included: false,
    queue_state_mutated: false,
    primary_mem_mutated: false,
    worker_started: false,
    scheduler_started: false,
    automatic_retry_or_release: false,
    apply_token: "token.safe-1",
    expires_at: "2026-06-27T00:05:00Z",
  };
  assert.deepEqual(api.parseHeldGovernancePreflight(preflight, "apply"), preflight);
  assert.equal(api.parseHeldGovernancePreflight({ ...preflight, source_evidence_digest: "private" }, "apply"), null);
  assert.equal(api.parseHeldGovernancePreflight({ ...preflight, worker_started: true }, "apply"), null);

  const receipt = {
    ...preflight,
    schema: "relaylm.lab.held_governance_receipt.v0",
    status: "applied",
    read_only: false,
    idempotent_replay: false,
    candidate_generation_stable: true,
  };
  delete receipt.apply_token;
  delete receipt.expires_at;
  assert.deepEqual(api.parseHeldGovernanceReceipt(receipt, "apply"), receipt);
  assert.equal(api.parseHeldGovernanceReceipt({ ...receipt, queue_payload: "private" }, "apply"), null);

  const preflightCaptures = [];
  await api.preflightHeldGovernance("char", "ns", candidateId, "apply", {
    operationId: "ui-op-1",
    reason: "runtime private reason",
  }, new AbortController().signal, async (url, init) => {
    preflightCaptures.push({ url, init });
    return new Response(JSON.stringify(preflight), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  assert.equal(preflightCaptures.length, 1, "preflight does not apply");
  assert.equal(preflightCaptures[0].url, `/lab/api/characters/char/held/${candidateId}/apply/preflight?namespace=ns`);
  const preflightBody = JSON.parse(preflightCaptures[0].init.body);
  for (const forbidden of ["store_root", "queue_root", "source_path", "protected_source", "queue_payload", "claim_token", "lease_owner"]) {
    assert.equal(forbidden in preflightBody, false, forbidden);
  }

  const panelSource = await readFile(new URL("HeldGovernancePanel.tsx", labSourceRoot), "utf8");
  assert.match(panelSource, /onClick=\{\(\) => void confirmDecision\(\)\}/);
  assert.match(panelSource, /generation\.current === currentGeneration/);
  assert.match(panelSource, /AbortController/);
  assert.equal(panelSource.includes("dangerouslySetInnerHTML"), false);
  assert.equal(panelSource.includes("onMouseEnter"), false);
  assert.equal(panelSource.includes("store_root"), false);
  assert.equal(panelSource.includes("queue_payload"), false);

  const pageSource = await readFile(new URL("ConnectedLabObservationPage.tsx", labSourceRoot), "utf8");
  assert.match(pageSource, /HeldGovernancePanel/);
  assert.match(pageSource, /Apply \/ Discard/);
  const heldSection = pageSource.split("HELD / BLOCKED", 2)[1].split("{selectedOperation?.kind", 2)[0];
  assert.equal(heldSection.includes("item.title"), false);
  assert.equal(heldSection.includes("item.bounded_summary"), false);
  assert.equal(pageSource.includes("dangerouslySetInnerHTML"), false);
} finally {
  await rm(temp, { recursive: true, force: true });
}

console.log("Phase I-7C Held Governance UI smoke passed");
