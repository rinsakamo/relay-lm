from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing patch anchor in {path}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def patch_runtime_character_selector() -> None:
    path = "apps/soul-lab/src/app/RootApp.tsx"
    replace_once(
        path,
        'import type { LabRoute, Language, Theme } from "../domain/lab";\n',
        'import type { CharacterSummary, LabRoute, Language, Theme } from "../domain/lab";\n',
    )
    replace_once(
        path,
        'import { ConnectedSettingsPage } from "../features/settings/ConnectedSettingsPage";\n',
        'import { ConnectedSettingsPage } from "../features/settings/ConnectedSettingsPage";\n'
        'import {\n'
        '  loadLabManagementProjections,\n'
        '  type LabCharacterProjection,\n'
        '} from "../features/settings/managementApi";\n',
    )
    replace_once(
        path,
        '''function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\\/?/, "");
  return isLabRoute(value) ? value : "home";
}

''',
        '''function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\\/?/, "");
  return isLabRoute(value) ? value : "home";
}

function runtimeCharacterSummary(character: LabCharacterProjection): CharacterSummary {
  const initials = Array.from(character.character_id)
    .filter((value) => /[A-Za-z0-9]/.test(value))
    .slice(0, 2)
    .join("")
    .toUpperCase() || "RL";
  return {
    characterId: character.character_id,
    displayName: character.character_id,
    initials,
    status: character.source_complete ? "online" : "degraded",
    sceneName: character.modes[0] ?? "managed",
    soulVersion: character.soul_configured ? "configured" : "unconfigured",
    stabilityLabel: character.source_complete ? "Configured" : "Incomplete",
    interventionState: "inactive",
    lastActiveSeconds: 0,
  };
}

''',
    )
    replace_once(
        path,
        '''  const [navigationLock, setNavigationLock] = useState<LabRoute | null>(null);

  const activeCharacter = useMemo(
    () => mockCharacters.find((character) => character.characterId === activeCharacterId) ?? firstCharacter,
    [activeCharacterId, firstCharacter],
  );
''',
        '''  const [navigationLock, setNavigationLock] = useState<LabRoute | null>(null);
  const [runtimeCharacters, setRuntimeCharacters] = useState<CharacterSummary[] | null>(null);

  const characters = useMemo(
    () => runtimeCharacters && runtimeCharacters.length > 0 ? runtimeCharacters : mockCharacters,
    [runtimeCharacters],
  );
  const activeCharacter = useMemo(
    () => characters.find((character) => character.characterId === activeCharacterId) ?? characters[0] ?? firstCharacter,
    [activeCharacterId, characters, firstCharacter],
  );
''',
    )
    replace_once(
        path,
        '''  const interactionLocked = navigationLock !== null;
  const adoptionRoute = route === "adoption";

  useEffect(() => {
    const syncRoute = () => {
''',
        '''  const interactionLocked = navigationLock !== null;
  const adoptionRoute = route === "adoption";

  useEffect(() => {
    const controller = new AbortController();
    void loadLabManagementProjections(controller.signal)
      .then((bundle) => {
        if (controller.signal.aborted) return;
        const projected = [...bundle.characters.characters]
          .sort((left, right) => left.character_id.localeCompare(right.character_id))
          .map(runtimeCharacterSummary);
        if (projected.length > 0) setRuntimeCharacters(projected);
      })
      .catch(() => {
        if (!controller.signal.aborted) setRuntimeCharacters(null);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (characters.some((character) => character.characterId === activeCharacterId)) return;
    const nextCharacter = characters[0];
    if (nextCharacter) setActiveCharacterId(nextCharacter.characterId);
  }, [activeCharacterId, characters]);

  useEffect(() => {
    const syncRoute = () => {
''',
    )
    replace_once(
        path,
        '''            {route === "observation"
              ? "REAL / EXPLICIT PREVIEW"
              : translate(language, "app.mockBadge")}
''',
        '''            {route === "observation"
              ? "REAL / EXPLICIT PREVIEW"
              : runtimeCharacters
                ? "RUNTIME CHARACTERS"
                : translate(language, "app.mockBadge")}
''',
    )
    write(path, read(path).replace("{mockCharacters.map((character) => (", "{characters.map((character) => (")
    write(path, read(path).replace("characters={mockCharacters}", "characters={characters}"))

    smoke_path = "apps/soul-lab/scripts/observationApiSmoke.mjs"
    smoke = read(smoke_path)
    if "rootAppSource" not in smoke:
        marker = '''assert.doesNotMatch(componentSource, /dangerouslySetInnerHTML/);

console.log("SOUL Lab observation browser schema smoke passed");
'''
        addition = '''assert.doesNotMatch(componentSource, /dangerouslySetInnerHTML/);

const rootAppSource = await fs.readFile(
  new URL("../src/app/RootApp.tsx", import.meta.url),
  "utf8",
);
assert.match(rootAppSource, /loadLabManagementProjections/);
assert.match(rootAppSource, /runtimeCharacters/);
assert.match(rootAppSource, /characters\\.map/);

console.log("SOUL Lab observation browser schema smoke passed");
'''
        if marker not in smoke:
            raise RuntimeError("browser smoke insertion anchor missing")
        write(smoke_path, smoke.replace(marker, addition, 1))


def run_checked(command: tuple[str, ...], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        diagnostic = ROOT / "phase_i2_final_validation_temp.txt"
        diagnostic.write_text(
            "$ " + " ".join(command) + "\n\n" + completed.stdout,
            encoding="utf-8",
        )
        subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=False)
        subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=False)
        subprocess.run(("git", "add", str(diagnostic.relative_to(ROOT))), cwd=ROOT, check=False)
        subprocess.run(("git", "commit", "-m", "chore: capture final Phase I2 validation failure"), cwd=ROOT, check=False)
        subprocess.run(("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation"), cwd=ROOT, check=False)
        raise SystemExit(completed.returncode)
    print("PASS:", " ".join(command), flush=True)


def main() -> None:
    patch_runtime_character_selector()
    run_checked(("python", "-m", "pip", "install", "-e", "."))
    env = {"PYTHONPATH": ".:scripts"}
    run_checked(("python", "-m", "compileall", "-q", "relaylm", "scripts"))
    run_checked(("python", "scripts/relaylm_docs_link_check.py"), env={"PYTHONPATH": "."})
    run_checked(("python", "scripts/relaylm_documentation_current_boundary_smoke.py"), env={"PYTHONPATH": "."})
    run_checked(("python", "scripts/relaylm_phase_i2_documentation_boundary_smoke.py"), env={"PYTHONPATH": "."})
    for script in (
        "scripts/relaylm_phase_i2_lab_observation_ci_runner.py",
        "scripts/relaylm_phase6c1_primary_worker_ci_runner.py",
        "scripts/relaylm_phase6c1_worker_integration_ci_runner.py",
        "scripts/relaylm_phase6c1_durable_protected_source_smoke.py",
        "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py",
        "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py",
    ):
        run_checked(("python", script), env=env)

    frontend = ROOT / "apps" / "soul-lab"
    run_checked(("npm", "install", "--no-audit", "--no-fund"), cwd=frontend)
    run_checked(("npm", "run", "typecheck"), cwd=frontend)
    run_checked((
        "npx", "tsc", "src/features/lab/observationApi.ts",
        "--target", "ES2022", "--module", "ES2022",
        "--moduleResolution", "Bundler", "--outDir", ".observation-smoke",
        "--skipLibCheck",
    ), cwd=frontend)
    run_checked(("node", "scripts/observationApiSmoke.mjs"), cwd=frontend)
    run_checked(("npm", "run", "build"), cwd=frontend)

    for name in (
        "phase_i2_failure_temp.txt",
        "phase_i2_test_output_temp.txt",
        "phase_i2_final_validation_temp.txt",
    ):
        (ROOT / name).unlink(missing_ok=True)
    (frontend / ".observation-smoke").mkdir(exist_ok=True)
    for child in (frontend / ".observation-smoke").iterdir():
        child.unlink()
    (frontend / ".observation-smoke").rmdir()
    Path(__file__).unlink(missing_ok=True)

    subprocess.run(("git", "config", "user.name", "github-actions"), cwd=ROOT, check=True)
    subprocess.run(("git", "config", "user.email", "actions@github.com"), cwd=ROOT, check=True)
    subprocess.run(("git", "add", "-A"), cwd=ROOT, check=True)
    subprocess.run(("git", "commit", "-m", "fix: use runtime character scope in Phase I2 Lab"), cwd=ROOT, check=True)
    subprocess.run(
        ("git", "push", "origin", "HEAD:phase-i2-real-soul-lab-observation"),
        cwd=ROOT,
        check=True,
    )
    print("Phase I-2 final validation passed", flush=True)


if __name__ == "__main__":
    main()
