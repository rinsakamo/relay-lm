import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import type { CharacterSummary, LabRoute, Language, Theme } from "../domain/lab";
import { AdoptionPage } from "../features/adoption/AdoptionPage";
import { CommunicationPage } from "../features/communication/CommunicationPage";
import { ConnectedLifecycleLabObservationPage } from "../features/lifecycle/ConnectedLifecycleLabObservationPage";
import { PodPage } from "../features/pod/PodPage";
import { ConnectedSettingsPage } from "../features/settings/ConnectedSettingsPage";
import {
  loadLabManagementProjections,
  type LabCharacterProjection,
  type LabSettingsProjection,
} from "../features/settings/managementApi";
import { translate, type MessageKey } from "../locales/messages";
import { mockCharacters } from "../mocks/lab";
import { App } from "./App";

const navigation: Array<{ route: LabRoute; label: MessageKey; marker: string }> = [
  { route: "home", label: "nav.home", marker: "⌂" },
  { route: "observation", label: "nav.observation", marker: "◉" },
  { route: "communication", label: "nav.communication", marker: "⇄" },
  { route: "pod", label: "nav.pod", marker: "◇" },
  { route: "adoption", label: "nav.adoption", marker: "+" },
  { route: "settings", label: "nav.settings", marker: "⚙" },
];

const footerLabels: Record<LabRoute, string> = {
  home: "UI-B0 / UI-B1A · Real Home Conversation / Lifecycle Visibility",
  adoption: "UI-A2 · Adoption / First Launch",
  communication: "UI-A3 · Character Communication",
  pod: "UI-A4 · Pod / SOUL Intervention",
  observation: "Phase I-2 / I-3 / UI-B1A · Observation / Correct / Lifecycle Visibility",
  settings: "UI-A6 / UI-A7 · Shared Shell / Management Projection",
};

function isLabRoute(value: string): value is LabRoute {
  return navigation.some((item) => item.route === value);
}

function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  return isLabRoute(value) ? value : "home";
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
  const adoptionRoute = route === "adoption";

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

  const handleCommunicationLockChange = useCallback(
    (locked: boolean) => updateNavigationLock("communication", locked),
    [updateNavigationLock],
  );
  const handleInterventionLockChange = useCallback(
    (locked: boolean) => updateNavigationLock("pod", locked),
    [updateNavigationLock],
  );
  const handleInspectorLockChange = useCallback(
    (locked: boolean) => updateNavigationLock("observation", locked),
    [updateNavigationLock],
  );

  function navigate(nextRoute: LabRoute) {
    if (navigationLock && nextRoute !== navigationLock) return;
    const nextHash = `#/${nextRoute}`;
    if (window.location.hash === nextHash) setRoute(nextRoute);
    else window.location.hash = nextHash;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function selectCharacter(characterId: string) {
    if (!interactionLocked) setActiveCharacterId(characterId);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">S</div>
          <div><strong>{translate(language, "app.name")}</strong><span>{translate(language, "app.subtitle")}</span></div>
        </div>
        <nav className="primary-navigation" aria-label="SOUL Lab">
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
            {route === "home" || route === "observation"
              ? "REAL / EXPLICIT PREVIEW"
              : runtimeCharacters
                ? "RUNTIME CHARACTERS"
                : translate(language, "app.mockBadge")}
          </span>
          <p>
            {navigationLock
              ? translate(language, "nav.locked")
              : route === "home" || route === "observation"
                ? language === "ja"
                  ? "実runtimeを優先し、ローカルプレビューは明示的に切り替えます。"
                  : "Real runtime is primary; local preview requires an explicit switch."
                : translate(language, "nav.boundaryNote")}
          </p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          {adoptionRoute ? (
            <div className="character-selector"><span>{translate(language, "header.activeCharacter")}</span><strong>NO ACTIVE CHARACTER</strong></div>
          ) : (
            <label className="character-selector">
              <span>{translate(language, "header.activeCharacter")}</span>
              <select value={activeCharacter.characterId} disabled={interactionLocked} onChange={(event: ChangeEvent<HTMLSelectElement>) => selectCharacter(event.target.value)}>
                {characters.map((character) => <option value={character.characterId} key={character.characterId}>{character.displayName}</option>)}
              </select>
            </label>
          )}
          <div className="topbar-status">
            {adoptionRoute ? (
              <><span className="status-badge status-unconfigured">First launch</span><span className="soul-version">SOUL · not initialized</span></>
            ) : (
              <><span className={`status-badge status-${activeCharacter.status}`}>{translate(language, `status.${activeCharacter.status}`)}</span><span className="soul-version">SOUL {activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}</span></>
            )}
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
          {route === "adoption" && <AdoptionPage language={language} onBackHome={() => navigate("home")} />}
          {route === "observation" && <ConnectedLifecycleLabObservationPage key={activeCharacter.characterId} language={language} activeCharacter={activeCharacter} onInspectorLockChange={handleInspectorLockChange} />}
          {route === "communication" && <CommunicationPage key={activeCharacter.characterId} language={language} activeCharacter={activeCharacter} characters={characters} onSessionLockChange={handleCommunicationLockChange} />}
          {route === "pod" && <PodPage key={activeCharacter.characterId} language={language} activeCharacter={activeCharacter} onInterventionLockChange={handleInterventionLockChange} />}
          {route === "settings" && <ConnectedSettingsPage language={language} theme={theme} activeCharacterId={activeCharacter.characterId} characters={characters} />}
        </main>

        <footer className="footer-bar"><span>{translate(language, "footer.boundary")}</span><span>{footerLabels[route]}</span></footer>
      </div>
    </div>
  );
}
