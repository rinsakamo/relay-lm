import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (relative) => readFileSync(join(root, relative), "utf8");

function require(condition, detail) {
  if (!condition) throw new Error(String(detail));
}

const api = read("src/features/lifecycle/lifecycleVisibilityApi.ts");
const panel = read("src/features/lifecycle/LifecycleVisibilityPanel.tsx");
const home = read("src/features/lifecycle/LifecycleAwareHomeConversationPage.tsx");
const observation = read("src/features/lifecycle/ConnectedLifecycleLabObservationPage.tsx");
const app = read("src/app/App.tsx");
const rootApp = read("src/app/RootApp.tsx");
const packageJson = read("package.json");

require(api.includes("relaylm.lab.lifecycle_visibility.v0"), "schema parser missing");
require(api.includes("/lab/api/characters/${character}/lab/lifecycle-visibility?${query}"), "route missing");
require(api.includes("cache: \"no-store\""), "no-store fetch missing");
require(api.includes("credentials: \"same-origin\""), "same-origin fetch missing");
require(api.includes("mutation_controls_exposed: false"), "mutation flag parser missing");
require(api.includes("scheduler_controls_exposed: false"), "scheduler flag parser missing");
require(api.includes("raw_private_identifiers_included: false"), "private identifier flag parser missing");

for (const state of ["active", "hidden", "prepared", "recovery_required", "corrupt", "unknown"]) {
  require(api.includes(state), `missing lifecycle vocabulary ${state}`);
  require(panel.includes(state), `missing UI lifecycle vocabulary ${state}`);
}
for (const status of ["pending", "complete", "isolated", "queued", "processing", "formed", "held", "blocked", "failed"]) {
  require(api.includes(status), `missing operation vocabulary ${status}`);
}

require(panel.includes("READ-ONLY LIFECYCLE VISIBILITY"), "panel boundary missing");
require(panel.includes("New Conversation"), "fresh conversation copy missing");
require(panel.includes("durable memory store"), "durable memory retention copy missing");
require(panel.includes("Home transcript is not a durable source") || panel.includes("Home transcriptはdurable sourceではありません"), "home transcript boundary missing");
require(!panel.includes("dangerouslySetInnerHTML"), "dangerouslySetInnerHTML is forbidden");
require(!panel.includes("<button"), "lifecycle panel must not expose controls");
require(!panel.includes("onClick"), "lifecycle panel must not expose command handlers");
require(!panel.includes("Run / Retry / Repair / Cleanup"), "control-like wording must not look like a command surface");

require(home.includes("generation.current"), "home stale-generation guard missing");
require(home.includes("projection.character_id !== activeCharacter.characterId"), "home stale character guard missing");
require(observation.includes("generation.current"), "observation stale-generation guard missing");
require(observation.includes("projection.character_id !== activeCharacter.characterId"), "observation stale character guard missing");
require(app.includes("LifecycleAwareHomeConversationPage"), "home wrapper not exported");
require(rootApp.includes("ConnectedLifecycleLabObservationPage"), "observation wrapper not wired");
require(packageJson.includes("smoke:lifecycle-visibility"), "npm smoke script missing");

for (const forbidden of [
  "scheduler run",
  "worker run",
  "replay run",
  "repair control",
  "cleanup button",
  "apply_token",
  "lease_token",
  "claim_owner",
  "dispatch_idempotency_key",
  "queue_root",
  "protected_source_root",
]) {
  require(!panel.includes(forbidden), `forbidden UI leakage/control text: ${forbidden}`);
}

console.log("SOUL Lab UI-B1A lifecycle visibility smoke passed");
