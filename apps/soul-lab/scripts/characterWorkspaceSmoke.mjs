import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (relative) => readFileSync(join(root, relative), "utf8");

function require(condition, detail) {
  if (!condition) throw new Error(String(detail));
}

function section(source, start, end) {
  const startIndex = source.indexOf(start);
  require(startIndex >= 0, `missing section start: ${start}`);
  const endIndex = end ? source.indexOf(end, startIndex + start.length) : source.length;
  require(endIndex > startIndex, `missing section end: ${end}`);
  return source.slice(startIndex, endIndex);
}

const packageJson = read("package.json");
const domain = read("src/domain/lab.ts");
const messages = read("src/locales/messages.ts");
const rootApp = read("src/app/RootApp.tsx");
const workspace = read("src/features/workspace/CharacterWorkspacePages.tsx");
const workspaceCss = read("src/features/workspace/characterWorkspace.css");
const home = read("src/features/home/HomeConversationPage.tsx");

require(packageJson.includes('"smoke:character-workspace"'), "CW-A3 smoke script missing");
for (const route of ["home", "character", "scenes", "relationships", "memory", "runtime", "advanced"]) {
  require(domain.includes(`| "${route}"`) || domain.includes(`  | "${route}"`), `LabRoute missing ${route}`);
  require(rootApp.includes(`route: "${route}"`), `navigation missing ${route}`);
}
for (const label of ["Home", "Character", "Scenes", "Relationships", "Memory Wiki", "Runtime", "Advanced"]) {
  require(messages.includes(label), `navigation label missing ${label}`);
}
require(rootApp.includes("legacyRouteAliases"), "legacy route aliases missing");
require(rootApp.includes('observation: "runtime"'), "legacy observation route is not absorbed into Runtime");
require(rootApp.includes('communication: "advanced"'), "legacy communication route is not absorbed into Advanced");
require(rootApp.includes("navigationLock"), "navigation lock behavior missing");
require(rootApp.includes('updateNavigationLock("advanced", locked)'), "advanced lock route missing");
require(rootApp.includes("ConnectedLifecycleLabObservationPage"), "existing lifecycle/governance controls are not reachable from Advanced");

const character = section(workspace, "function CharacterSurface", "function ScenesSurface");
for (const source of ["SOUL.md", "STYLE.md", "EMOTION.md", "BOUNDARY.md", "LORE.md"]) {
  require(character.includes(source), `Character surface missing ${source}`);
}
require(character.includes("preview only / not saved"), "source editing draft boundary missing");
require(character.includes("proposal / explicit approval required"), "explicit approval boundary missing");
require(character.includes("BOUNDARY.md"), "BOUNDARY visibility missing");

const scenes = section(workspace, "function ScenesSurface", "function RelationshipsSurface");
for (const label of ["SCENE.md", "scenes/*.md", "scenes/_inbox/*.md", "SCENE POLICY", "ACTIVE SCENES", "SCENE INBOX"]) {
  require(scenes.includes(label), `Scenes surface missing ${label}`);
}
require(scenes.includes("structured classifier pending / selection preview"), "scene classifier pending boundary missing");
require(scenes.includes("RelaySCN"), "RelaySCN ownership copy missing");
require(!scenes.includes("RelayEMO is the scene owner"), "RelayEMO must not be presented as scene owner");

const relationships = section(workspace, "function RelationshipsSurface", "function MemorySurface");
for (const label of ["RELATIONSHIP.md", "relationships/user.md", "relationships/_inbox/**", "ROLE VOCABULARY", "SELECTED TARGET", "PENDING REL PROPOSALS"]) {
  require(relationships.includes(label), `Relationships surface missing ${label}`);
}
require(relationships.includes("RelayREL"), "RelayREL layer copy missing");
require(relationships.includes("SOUL identity"), "relationship/SOUL separation missing");
require(relationships.includes("public/private scene"), "public/private disclosure copy missing");
require(!relationships.includes("most_important_person等の自動確定は行います"), "relationship auto-apply wording must not be present");

const memory = section(workspace, "function MemorySurface", "function RuntimeSurface");
for (const label of ["MEMORY.md", "memory/**/*.md", "memory/inbox/**", "memory/forgotten/**", "important", "active", "archived", "forgotten", "held", "blocked", "proposal", "source"]) {
  require(memory.includes(label), `Memory Wiki surface missing ${label}`);
}
require(memory.includes("memory page") && memory.includes("memory block") && memory.includes("retrieval chunk"), "Memory Wiki vocabulary separation missing");
require(!memory.includes("memory_id"), "Memory Wiki default surface must not expose memory_id");
require(!memory.includes("one-file-per-memory前提には戻します"), "one-file-per-memory model revival wording must not exist");

const runtime = section(workspace, "function RuntimeSurface", "function AdvancedSurface");
for (const label of ["latest used scene", "latest emotion", "latest relationship projection", "latest memory / used-memory evidence", "context_projection.json", "Tier 1 / Tier 2 / Tier 3"]) {
  require(runtime.includes(label), `Runtime surface missing ${label}`);
}
require(runtime.includes("content-free"), "Runtime content-free boundary missing");
require(runtime.includes("backend prompt") && runtime.includes("not displayed"), "backend prompt hidden boundary missing");
require(runtime.includes("used-memory evidence"), "used-memory evidence authority missing");

const advanced = section(workspace, "function AdvancedSurface", "export function CharacterWorkspacePage");
for (const label of ["memory_id", "revision", "pin_state", "lifecycle state", "apply token", "queue", "worker", "audit", "raw content-free projections"]) {
  require(advanced.includes(label), `Advanced missing internal governance label ${label}`);
}
require(advanced.includes("Correct / Forget / Pin / Unpin / Held Governance"), "existing governance controls copy missing");
require(advanced.includes("does not increase browser authority") || advanced.includes("browser authorityは増えません"), "Advanced authority boundary missing");

const defaultSurfaces = [character, scenes, relationships, memory, runtime].join("\n");
for (const forbidden of ["/home/", "C:\\\\", "queue payload", "protected_source_root", "API key"]) {
  require(!defaultSurfaces.includes(forbidden), `default surface leaks forbidden text: ${forbidden}`);
}
require(!workspace.includes("dangerouslySetInnerHTML"), "dangerouslySetInnerHTML is forbidden");
require(!rootApp.includes("dangerouslySetInnerHTML"), "dangerouslySetInnerHTML is forbidden in shell");
require(home.includes("/v1/chat/completions"), "Home real runtime path missing");
require(home.includes("REAL RUNTIME") && home.includes("LOCAL PREVIEW"), "real runtime / local preview separation missing");
require(home.includes("server projection由来のrouteだけを使い"), "Home server-projected route boundary missing");
require(!rootApp.includes("setMockFallback(true)"), "automatic mock fallback must not be introduced");
require(workspaceCss.includes(".workspace-surface"), "Character Workspace CSS missing");
require(messages.includes("表示はcontent-free projection"), "Japanese default boundary label missing");
require(messages.includes("This surface is content-free projection"), "English preview catalog missing");

console.log("CW-A3 Character Workspace UI smoke passed");
