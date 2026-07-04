import { readFileSync } from "node:fs";

const rootApp = readFileSync(new URL("../src/app/RootApp.tsx", import.meta.url), "utf8");
const creationPage = readFileSync(new URL("../src/features/creation/CharacterCreationPage.tsx", import.meta.url), "utf8");
const domain = readFileSync(new URL("../src/domain/lab.ts", import.meta.url), "utf8");
const packageJson = readFileSync(new URL("../package.json", import.meta.url), "utf8");

function assertIncludes(source, needle, label) {
  if (!source.includes(needle)) {
    throw new Error(`missing ${label}: ${needle}`);
  }
}

assertIncludes(domain, '| "create"', "create route type");
assertIncludes(rootApp, 'label: "nav.create"', "create navigation label");
assertIncludes(rootApp, 'runtimeCharacters !== null && runtimeCharacters.length === 0', "zero-character state");
assertIncludes(rootApp, 'No default character was auto-created', "no default auto-create copy");
assertIncludes(rootApp, '<CharacterCreationPage language={language} noCharacter />', "zero-character creation route");
assertIncludes(creationPage, "Create quickly", "quick create card");
assertIncludes(creationPage, "Create in detail", "advanced create card");
assertIncludes(creationPage, "Try a showcase character", "showcase card");
assertIncludes(creationPage, "Import", "import card");
assertIncludes(creationPage, "template", "quick create template input label");
assertIncludes(creationPage, "name", "quick create name input label");
assertIncludes(creationPage, "tone", "quick create tone input label");
assertIncludes(creationPage, "intended use", "quick create use input label");
assertIncludes(creationPage, "SOUL", "advanced SOUL section");
assertIncludes(creationPage, "STYLE", "advanced STYLE section");
assertIncludes(creationPage, "EMOTION", "advanced EMOTION section");
assertIncludes(creationPage, "RELATIONSHIP", "advanced RELATIONSHIP section");
assertIncludes(creationPage, "SCENE", "advanced SCENE section");
assertIncludes(creationPage, "MEMORY", "advanced MEMORY section");
assertIncludes(creationPage, "BOUNDARY", "advanced BOUNDARY section");
assertIncludes(creationPage, "LORE", "advanced LORE section");
assertIncludes(creationPage, "Preview", "advanced Preview section");
assertIncludes(creationPage, "Use as-is", "showcase use as-is option");
assertIncludes(creationPage, "Use as starter", "showcase use as starter option");
assertIncludes(creationPage, "This template was checked", "import validation summary");
assertIncludes(packageJson, "smoke:character-creation", "package smoke script");

const forbidden = ["api_key", "secret", "C:\\\\", "/home/", "queue_id", "runtime state path"];
for (const needle of forbidden) {
  if (creationPage.includes(needle)) {
    throw new Error(`creation UI rendered forbidden internal detail: ${needle}`);
  }
}

console.log("Character creation UI smoke passed");
