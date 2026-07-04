import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import type { CharacterSummary, LabRoute, Language, Theme } from "../domain/lab";
import { ConnectedLifecycleLabObservationPage } from "../features/lifecycle/ConnectedLifecycleLabObservationPage";
import {
  loadLabManagementProjections,
  type LabCharacterProjection,
  type LabSettingsProjection,
} from "../features/settings/managementApi";
import { CharacterWorkspacePage } from "../features/workspace/CharacterWorkspacePages";
import { translate, type MessageKey } from "../locales/messages";
import { mockCharacters } from "../mocks/lab";
import { App } from "./App";

const navigation: Array<{ route: LabRoute; label: MessageKey; marker: string }> = [
  { route: "home", label: "nav.home", marker: "⌂" },
  { route: "character", label: "nav.character", marker: "◆" },
  { route: "scenes", label: "nav.scenes", marker: "▦" },
  { route: "relationships", label: "nav.relationships", marker: "⇄" },
  { route: "memory", label: "nav.memory", marker: "◎" },
  { route: "runtime", label: "nav.runtime", marker: "◉" },
  { route: "advanced", label: "nav.advanced", marker: "⚙" },
];

const legacyRouteAliases: Record<string, LabRoute> = {
  observation: "runtime",
  communication: "advanced",
  pod: "advanced",
  adoption: "advanced",
  settings: "advanced",
};

const footerLabels: Record<LabRoute, string> = {
  home: "CW-A3 · Existing real Home conversation / explicit Local Preview",
  character: "CW-A3 · SOUL / STYLE / EMOTION / BOUNDARY / optional LORE",
  scenes: "CW-A3 · SCENE policy / active scenes / scene inbox",
  relationships: "CW-A3 · RELATIONSHIP vocabulary / target context / proposals",
  memory: "CW-A3 · Memory Wiki pages, blocks, links, archive, forgotten",
  runtime: "CW-A3 · content-free context projection and used-memory evidence",
  advanced: "CW-A3 · developer diagnostics / internal governance / existing loopback controls",
  observation: "CW-A3 · legacy route mapped to Runtime",
  communication: "CW-A3 · legacy route mapped to Advanced",
  pod: "CW-A3 · legacy route mapped to Advanced",
  adoption: "CW-A3 · legacy route mapped to Advanced",
  settings: "CW-A3 · legacy route mapped to Advanced",
};

function isLabRoute(value: string): value is LabRoute {
  return navigation.some((item) => item.route === value);
}

function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  if (isLabRoute(value)) return value;
  return legacyRouteAliases[value] ?? "home";
}

function runtimeCharacterSummary(character: LabCharacterProjection): CharacterSummary {
  const initials =
    Array.from(character.character_id)
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

export function RootApp() {
  const firstCharacter = mockCharacters[0];
  if (!firstCharacter) throw new Error("SOUL Lab mock data requires at least one character");

  const [route, setRoute] = useState<LabRoute>(hashRoute);
  const [theme, setTheme] = useState<Theme>(() => {
    const storedTheme = window.localStorage.getItem("soul-lab-theme");
    if (storedTheme === "light" || storedTheme === "dark") return storedTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [language, setLanguage] = useState<Language>("ja");
  const [activeCharacterId, setActiveCharacterId] = useState(() => {
    const storedCharacterId = window.localStorage.getItem("soul-lab-active-character");
    return mockCharacters.some((character) => character.characterId === storedCharacterId)
      ? (storedCharacterId as string)
      : firstCharacter.characterId;
  });
  const [navigationLock, setNavigationLock] = useState<LabRoute | null>(null);
  const [runtimeCharacters, setRuntimeCharacters] = useState<CharacterSummary[] | null>(null);
  const [characterProjections, setCharacterProjections] = useState<
    Record<string, LabCharacterProjection>
  >({});
  const [settingsProjection, setSettingsProjection] = useState<LabSettingsProjection | null>(null);

  const characters = useMemo(
    () => (runtimeCharacters && runtimeCharacters.length > 0 ? runtimeCharacters : mockCharacters),
    [runtimeCharacters],
  );
  const activeCharacter = useMemo(
    () =>
      characters.find((character) => character.characterId === activeCharacterId) ??
      characters[0] ??
      firstCharacter,
    [activeCharacterId, characters, firstCharacter],
  );
  const activeCharacterProjection = characterProjections[activeCharacter.characterId] ?? null;
  const interactionLocked = navigationLock !== null;

  useEffect(() => {
    const controller = new AbortController();
    void loadLabManagementProjections(controller.signal)
      .then((bundle) => {
        if (controller.signal.aborted) return;
        const ordered = [...bundle.characters.characters].sort((left, right) =>
          left.character_id.localeCompare(right.character_id),
        );
        setRuntimeCharacters(ordered.map(runtimeCharacterSummary));
        setCharacterProjections(
          Object.fromEntries(ordered.map((character) => [character.character_id, character])),
        );
        setSettingsProjection(bundle.settings);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setRuntimeCharacters(null);
        setCharacterProjections({});
        setSettingsProjection(null);
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
      const nextRoute = hashRoute();
      if (navigationLock && nextRoute !== navigationLock) {
        const lockedHash = `#/${navigationLock}`;
        if (window.location.hash !== lockedHash) window.history.replaceState(null, "", lockedHash);
        setRoute(navigationLock);
        return;
      }
      setRoute(nextRoute);
    };
    syncRoute();
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, [navigationLock]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("soul-lab-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    window.localStorage.setItem("soul-lab-active-character", activeCharacterId);
  }, [activeCharacterId]);

  const updateNavigationLock = useCallback((lockRoute: LabRoute, locked: boolean) => {
    setNavigationLock((current) => {
      if (locked) return lockRoute;
      return current === lockRoute ? null : current;
    });
  }, []);

  const handleAdvancedLockChange = useCallback(
    (locked: boolean) => updateNavigationLock("advanced", locked),
    [updateNavigationLock],
  );

  function navigate(nextRoute: LabRoute) {
    const canonicalRoute = legacyRouteAliases[nextRoute] ?? nextRoute;
    if (navigationLock && canonicalRoute !== navigationLock) return;
    const nextHash = `#/${canonicalRoute}`;
    if (window.location.hash === nextHash) setRoute(canonicalRoute);
    else window.location.hash = nextHash;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function selectCharacter(characterId: string) {
    if (!interactionLocked) setActiveCharacterId(characterId);
  }

  const workspacePageProps = {
    language,
    activeCharacter,
    characterProjection: activeCharacterProjection,
    settingsProjection,
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">CW</div>
          <div><strong>{translate(language, "app.name")}</strong><span>{translate(language, "app.subtitle")}</span></div>
        </div>
        <nav className="primary-navigation" aria-label="Character Workspace">
          {navigation.map((item) => (
            <button
              className={`nav-item ${item.route === route ? "nav-item-active" : ""}`}
              type="button"
              key={item.route}
              aria-current={item.route === route ? "page" : undefined}
              disabled={Boolean(navigationLock && item.route !== navigationLock)}
              onClick={() => navigate(item.route)}
            >
              <span className="nav-marker" aria-hidden="true">{item.marker}</span>
              <span>{translate(language, item.label)}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="mock-pill">
            {route === "home"
              ? "REAL / EXPLICIT PREVIEW"
              : runtimeCharacters
                ? "CONTENT-FREE PROJECTION"
                : translate(language, "app.mockBadge")}
          </span>
          <p>
            {navigationLock
              ? translate(language, "nav.locked")
              : route === "home"
                ? language === "ja"
                  ? "Homeは既存RelayLM /v1/chat/completions authority pathのままです。"
                  : "Home stays on the existing RelayLM /v1/chat/completions authority path."
                : translate(language, "nav.boundaryNote")}
          </p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <label className="character-selector">
            <span>{translate(language, "header.activeCharacter")}</span>
            <select value={activeCharacter.characterId} disabled={interactionLocked} onChange={(event: ChangeEvent<HTMLSelectElement>) => selectCharacter(event.target.value)}>
              {characters.map((character) => <option value={character.characterId} key={character.characterId}>{character.displayName}</option>)}
            </select>
          </label>
          <div className="topbar-status">
            <><span className={`status-badge status-${activeCharacter.status}`}>{translate(language, `status.${activeCharacter.status}`)}</span><span className="soul-version">SOUL {activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}</span></>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" aria-label={translate(language, "header.language")} title={translate(language, "header.language")} onClick={() => setLanguage((value) => (value === "ja" ? "en" : "ja"))}>{language === "ja" ? "EN" : "JA"}</button>
            <button className="icon-button" type="button" aria-label={translate(language, "header.theme")} title={translate(language, "header.theme")} onClick={() => setTheme((value) => (value === "light" ? "dark" : "light"))}>{theme === "light" ? "☾" : "☀"}</button>
          </div>
        </header>

        <main className="main-content">
          {route === "home" && (
            <App
              language={language}
              activeCharacter={activeCharacter}
              characterProjection={activeCharacterProjection}
              settingsProjection={settingsProjection}
              onNavigate={navigate}
            />
          )}
          {route === "character" && <CharacterWorkspacePage surface="character" {...workspacePageProps} />}
          {route === "scenes" && <CharacterWorkspacePage surface="scenes" {...workspacePageProps} />}
          {route === "relationships" && <CharacterWorkspacePage surface="relationships" {...workspacePageProps} />}
          {route === "memory" && <CharacterWorkspacePage surface="memory" {...workspacePageProps} />}
          {route === "runtime" && <CharacterWorkspacePage surface="runtime" {...workspacePageProps} />}
          {route === "advanced" && (
            <div className="advanced-stack">
              <CharacterWorkspacePage surface="advanced" {...workspacePageProps} />
              <ConnectedLifecycleLabObservationPage
                key={activeCharacter.characterId}
                language={language}
                activeCharacter={activeCharacter}
                onInspectorLockChange={handleAdvancedLockChange}
              />
            </div>
          )}
        </main>

        <footer className="footer-bar"><span>{translate(language, "footer.boundary")}</span><span>{footerLabels[route]}</span></footer>
      </div>
    </div>
  );
}
