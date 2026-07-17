import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const featureRoot = new URL("../src/features/memory-explorer/", import.meta.url);
const temp = await mkdtemp(join(tmpdir(), "relaylm-memory-explorer-"));

async function emit(name) {
  const source = await readFile(new URL(name, featureRoot), "utf8");
  const result = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ES2022,
      strict: true,
      moduleResolution: ts.ModuleResolutionKind.Bundler,
    },
    fileName: name,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter((diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error);
  assert.equal(errors.length, 0, `transpile diagnostics in ${name}: ${errors.map((error) => error.messageText).join("; ")}`);
  await writeFile(join(temp, name.replace(/\.ts$/, ".js")), result.outputText, "utf8");
}

try {
  await mkdir(temp, { recursive: true });
  await writeFile(join(temp, "package.json"), '{"type":"module"}\n', "utf8");
  await emit("memoryExplorerTypes.ts");
  await emit("memoryExplorerData.ts");
  await emit("memoryExplorerEngine.ts");

  const types = await import(pathToFileURL(join(temp, "memoryExplorerTypes.js")).href);
  const data = await import(pathToFileURL(join(temp, "memoryExplorerData.js")).href);
  const engine = await import(pathToFileURL(join(temp, "memoryExplorerEngine.js")).href);

  const rinaRecords = data.memoryExplorerRecordsByCharacter.rina;
  const micaRecords = data.memoryExplorerRecordsByCharacter.mica;
  assert.ok(rinaRecords.length >= 5, "rina mock data too small");
  assert.ok(micaRecords.length >= 5, "mica mock data too small");

  for (const [characterId, records] of Object.entries(data.memoryExplorerRecordsByCharacter)) {
    const ids = new Set(records.map((record) => record.memoryId));
    for (const record of records) {
      assert.equal(record.characterId, characterId, `record ${record.memoryId} escaped character ${characterId}`);
      for (const relatedId of record.relatedMemoryIds) {
        assert.ok(ids.has(relatedId), `related id ${relatedId} escaped character ${characterId}`);
      }
    }
  }
  const rinaIds = new Set(rinaRecords.map((record) => record.memoryId));
  assert.equal(micaRecords.some((record) => rinaIds.has(record.memoryId)), false, "memory IDs collide across characters");

  const runtimeRecords = data.createMemoryExplorerRecordsForCharacter("character_default", "Default Character");
  assert.ok(runtimeRecords.length >= 5, "arbitrary runtime character did not receive mock records");
  assert.ok(runtimeRecords.every((record) => record.characterId === "character_default"), "runtime records use a fixture-only character id");
  assert.ok(runtimeRecords.every((record) => record.memoryId.includes("character-default")), "runtime IDs are not character-scoped");

  const fixedNow = Date.parse("2032-01-20T12:00:00Z");
  const futureProofRecords = data.createMemoryExplorerRecordsForCharacter("future-character", "Future", fixedNow);
  const recentFormedParams = { ...types.defaultSearchParams(), filters: { ...types.defaultFilters(), recentlyFormed: true } };
  const recentUsedParams = { ...types.defaultSearchParams(), filters: { ...types.defaultFilters(), recentlyUsed: true } };
  assert.ok(engine.runMemoryExplorerSearch(futureProofRecords, recentFormedParams, fixedNow).length > 0, "relative recently formed fixture expired");
  assert.ok(engine.runMemoryExplorerSearch(futureProofRecords, recentUsedParams, fixedNow).length > 0, "relative recently used fixture expired");

  data.resetMemoryExplorerSessionRecords("session-character");
  const sessionRecords = data.getMemoryExplorerSessionRecords("session-character", "Session Character");
  sessionRecords[0] = { ...sessionRecords[0], userTags: [...sessionRecords[0].userTags, "persisted-tag"] };
  data.saveMemoryExplorerSessionRecords("session-character", sessionRecords);
  const restoredSession = data.getMemoryExplorerSessionRecords("session-character", "Session Character");
  assert.ok(restoredSession[0].userTags.includes("persisted-tag"), "browser-session edits did not survive remount");
  restoredSession[0].userTags.push("caller-only-mutation");
  const isolatedSession = data.getMemoryExplorerSessionRecords("session-character", "Session Character");
  assert.equal(isolatedSession[0].userTags.includes("caller-only-mutation"), false, "session cache leaked mutable references");

  const defaultParams = types.defaultSearchParams();
  assert.equal(defaultParams.filters.status, "active", "default lifecycle filter must be explicit");
  const defaultResults = engine.runMemoryExplorerSearch(rinaRecords, defaultParams);
  assert.equal(defaultResults.some((record) => record.status === "hidden"), false, "default active search must exclude hidden memory");
  assert.ok(rinaRecords.some((record) => record.status === "hidden"), "fixture must include hidden memory");
  const allStatusParams = { ...defaultParams, filters: { ...defaultParams.filters, status: "all" } };
  assert.ok(engine.runMemoryExplorerSearch(rinaRecords, allStatusParams).some((record) => record.status === "hidden"), "all status must include hidden memory");

  const hiddenParams = { ...defaultParams, filters: { ...defaultParams.filters, status: "hidden" } };
  const hiddenResults = engine.runMemoryExplorerSearch(rinaRecords, hiddenParams);
  assert.ok(hiddenResults.length >= 1 && hiddenResults.every((record) => record.status === "hidden"), "hidden filter is incorrect");

  const keywordParams = { ...defaultParams, query: "テーマ", mode: "keyword" };
  const keywordResults = engine.runMemoryExplorerSearch(rinaRecords, keywordParams);
  assert.ok(keywordResults.length >= 1 && keywordResults.length < rinaRecords.length, "keyword search did not narrow results");
  const semanticProbe = { ...defaultParams, query: "ありがとう" };
  assert.equal(engine.runMemoryExplorerSearch(rinaRecords, { ...semanticProbe, mode: "keyword" }).length, 0, "keyword mode unexpectedly used semantic aliases");
  assert.ok(engine.runMemoryExplorerSearch(rinaRecords, { ...semanticProbe, mode: "semantic" }).length > 0, "semantic mode did not expand the concept alias");
  assert.ok(engine.runMemoryExplorerSearch(rinaRecords, { ...semanticProbe, mode: "hybrid" }).length > 0, "hybrid mode did not combine semantic evidence");

  assert.equal(engine.isTagOperationBusy("pending"), true, "pending tag operation must lock the explorer");
  assert.equal(engine.isTagOperationBusy("applied"), true, "applied feedback window must remain locked");
  assert.equal(engine.isTagOperationBusy("failed"), false, "failed tag operation must release the explorer");

  const sourceRecord = rinaRecords[0];
  assert.equal(engine.addUserTag(sourceRecord, "新タグ").ok, true);
  assert.equal(engine.addUserTag(sourceRecord, sourceRecord.userTags[0]).error, "duplicate");
  assert.equal(engine.addUserTag(sourceRecord, sourceRecord.systemTags[0]).error, "collidesWithSystemTag");
  assert.equal(engine.renameUserTag(sourceRecord, sourceRecord.userTags[0], "改名タグ").ok, true);
  assert.equal(engine.removeUserTag(sourceRecord, sourceRecord.userTags[0]).tags.includes(sourceRecord.userTags[0]), false);

  const activeRecord = rinaRecords.find((record) => record.status === "active");
  const afterForget = engine.applyForgetToRecords(rinaRecords, activeRecord.memoryId, "mock-now");
  assert.equal(afterForget.find((record) => record.memoryId === activeRecord.memoryId).status, "hidden");
  assert.equal(engine.runMemoryExplorerSearch(afterForget, defaultParams).some((record) => record.memoryId === activeRecord.memoryId), false);
  const restored = engine.restoreFromHidden(afterForget, activeRecord.memoryId);
  assert.equal(restored.find((record) => record.memoryId === activeRecord.memoryId).status, "active");

  const pageSource = await readFile(new URL("MemoryExplorerPage.tsx", featureRoot), "utf8");
  assert.equal(pageSource.includes("dangerouslySetInnerHTML"), false, "dangerouslySetInnerHTML is forbidden");
  assert.equal(pageSource.includes("fetch("), false, "Memory Explorer mock must not call a backend API");
  assert.match(pageSource, /getMemoryExplorerSessionRecords/, "arbitrary character/session data loader missing");
  assert.match(pageSource, /saveMemoryExplorerSessionRecords/, "browser-session persistence missing");
  assert.match(pageSource, /rewriteUserTagFilter/, "tag filter reconciliation missing");
  assert.match(pageSource, /refreshWith\(nextRecords, nextExecuted/, "tag edits do not refresh executed search results");
  assert.match(pageSource, /explorer\.correction_applied/, "browser-local correction flow missing");
  assert.match(pageSource, /isTagOperationBusy\(tagOperation\?\.state\)/, "tag applied feedback is not part of the shared edit lock");
  assert.match(pageSource, /onExplorerLockChange\(isBusy\)/, "shared busy state is not synchronized to the navigation lock");
  assert.match(pageSource, /if \(!selectedRecord \|\| isBusy \|\| !correctionSummary\.trim\(\)/, "correction save does not guard the shared busy state");
  assert.match(pageSource, /aria-label=\{memoryExplorerMessage\(language, "searchLabel"\)\}/, "search input lacks an accessible label");
  assert.match(pageSource, /role="radiogroup"/, "search modes lack radiogroup semantics");
  assert.match(pageSource, /role="dialog"/, "forget confirmation lacks dialog semantics");
  assert.match(pageSource, /aria-pressed/, "toggle controls lack aria-pressed state");
  assert.match(pageSource, /\n\s+disabled\n/, "purge must render disabled");
  assert.match(pageSource, /purgeUnavailableNote/, "purge explanation missing");
  assert.match(pageSource, /forgetConfirmTitle/, "forget confirmation missing");
  assert.match(pageSource, /tombstoneNote/, "tombstone boundary copy missing");

  const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  assert.match(packageJson.scripts.build, /smoke:memory-explorer/, "Memory Explorer smoke is not wired into the frontend CI build");

  const localeSource = await readFile(new URL("../src/locales/memoryExplorer.ts", import.meta.url), "utf8");
  assert.match(localeSource, /tagEditApplied.*mock/i, "tag edit applied state must be labeled mock/browser-local");
  assert.match(localeSource, /承認する場所ではありません/, "hero copy must disclaim a per-memory approval queue");
  assert.match(localeSource, /承認なしに形成されています/, "autonomy copy must state memory forms without approval");
  assert.match(localeSource, /ものではありません/, "tombstone copy must avoid claiming server enforcement");

  console.log("Memory Explorer mock smoke passed");
} finally {
  await rm(temp, { recursive: true, force: true });
}
