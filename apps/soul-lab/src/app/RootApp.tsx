import { useEffect, useMemo, useState } from "react";
import type { LabRoute, Language, Theme } from "../domain/lab";
import { AdoptionPage } from "../features/adoption/AdoptionPage";
import { CommunicationPage } from "../features/communication/CommunicationPage";
import { PodPage } from "../features/pod/PodPage";
import { translate, type MessageKey } from "../locales/messages";
import { mockCharacters } from "../mocks/lab";
import { App } from "./App";

const rootNavigation: Array<{ route: LabRoute; label: MessageKey; marker: string }> = [
  { route: "home", label: "nav.home", marker: "⌂" },
  { route: "observation", label: "nav.observation", marker: "◉" },
  { route: "communication", label: "nav.communication", marker: "⇄" },
  { route: "pod", label: "nav.pod", marker: "◇" },
  { route: "adoption", label: "nav.adoption", marker: "+" },
];

function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  return rootNavigation.some((item) => item.route === value) ? (value as LabRoute) : "home";
}

export function RootApp() {
  const firstCharacter = mockCharacters[0];
  if (!firstCharacter) {
    throw new Error("SOUL Lab mock data requires at least one character");
  }

  const [route, setRoute] = useState<LabRoute>(hashRoute);
  const [theme, setTheme] = useState<Theme>(() => {
    const storedTheme = window.localStorage.getItem("soul-lab-theme");
    if (storedTheme === "light" || storedTheme === "dark") {
      return storedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [language, setLanguage] = useState<Language>("ja");
  const [activeCharacterId, setActiveCharacterId] = useState(() => {
    const storedCharacterId = window.localStorage.getItem("soul-lab-active-character");
    return mockCharacters.some((character) => character.characterId === storedCharacterId)
      ? (storedCharacterId as string)
      : firstCharacter.characterId;
  });
  const [communicationLocked, setCommunicationLocked] = useState(false);
  const [interventionLocked, setInterventionLocked] = useState(false);

  const activeCharacter = useMemo(
    () => mockCharacters.find((character) => character.characterId === activeCharacterId) ?? firstCharacter,
    [activeCharacterId, firstCharacter],
  );
  const lockedRoute: LabRoute | null = communicationLocked
    ? "communication"
    : interventionLocked
      ? "pod"
      : null;
  const interactionLocked = lockedRoute !== null;

  useEffect(() => {
    const syncRoute = () => setRoute(hashRoute());
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

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

  function navigate(nextRoute: LabRoute) {
    if (lockedRoute && nextRoute !== lockedRoute) {
      return;
    }

    const nextHash = `#/${nextRoute}`;
    if (window.location.hash === nextHash) {
      setRoute(nextRoute);
      return;
    }
    window.location.hash = nextHash;
  }

  if (route !== "adoption" && route !== "communication" && route !== "pod") {
    return <App />;
  }

  const adoptionRoute = route === "adoption";
  const communicationRoute = route === "communication";
  const podRoute = route === "pod";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            S
          </div>
          <div>
            <strong>{translate(language, "app.name")}</strong>
            <span>{translate(language, "app.subtitle")}</span>
          </div>
        </div>

        <nav className="primary-navigation" aria-label="SOUL Lab">
          {rootNavigation.map((item) => (
            <button
              className={`nav-item ${item.route === route ? "nav-item-active" : ""}`}
              type="button"
              key={item.route}
              aria-current={item.route === route ? "page" : undefined}
              disabled={Boolean(lockedRoute && item.route !== lockedRoute)}
              onClick={() => navigate(item.route)}
            >
              <span className="nav-marker" aria-hidden="true">
                {item.marker}
              </span>
              <span>{translate(language, item.label)}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="mock-pill">{translate(language, "app.mockBadge")}</span>
          <p>{translate(language, "nav.settingsSoon")}</p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          {adoptionRoute ? (
            <div className="character-selector">
              <span>{translate(language, "header.activeCharacter")}</span>
              <strong>NO ACTIVE CHARACTER</strong>
            </div>
          ) : (
            <label className="character-selector">
              <span>{translate(language, "header.activeCharacter")}</span>
              <select
                value={activeCharacter.characterId}
                disabled={interactionLocked}
                onChange={(event) => setActiveCharacterId(event.target.value)}
              >
                {mockCharacters.map((character) => (
                  <option value={character.characterId} key={character.characterId}>
                    {character.displayName}
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="topbar-status">
            {adoptionRoute ? (
              <>
                <span className="status-badge status-unconfigured">First launch</span>
                <span className="soul-version">SOUL · not initialized</span>
              </>
            ) : (
              <>
                <span className={`status-badge status-${activeCharacter.status}`}>
                  {translate(language, `status.${activeCharacter.status}`)}
                </span>
                <span className="soul-version">
                  SOUL {activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}
                </span>
              </>
            )}
          </div>

          <div className="topbar-actions">
            <button
              className="icon-button"
              type="button"
              aria-label={translate(language, "header.language")}
              title={translate(language, "header.language")}
              onClick={() => setLanguage((value) => (value === "ja" ? "en" : "ja"))}
            >
              {language === "ja" ? "EN" : "JA"}
            </button>
            <button
              className="icon-button"
              type="button"
              aria-label={translate(language, "header.theme")}
              title={translate(language, "header.theme")}
              onClick={() => setTheme((value) => (value === "light" ? "dark" : "light"))}
            >
              {theme === "light" ? "☾" : "☀"}
            </button>
          </div>
        </header>

        <main className="main-content">
          {adoptionRoute && (
            <AdoptionPage language={language} onBackHome={() => navigate("home")} />
          )}
          {communicationRoute && (
            <CommunicationPage
              language={language}
              activeCharacter={activeCharacter}
              characters={mockCharacters}
              onSessionLockChange={setCommunicationLocked}
            />
          )}
          {podRoute && (
            <PodPage
              key={activeCharacter.characterId}
              language={language}
              activeCharacter={activeCharacter}
              onInterventionLockChange={setInterventionLocked}
            />
          )}
        </main>

        <footer className="footer-bar">
          <span>{translate(language, "footer.boundary")}</span>
          <span>
            {adoptionRoute
              ? "UI-A2 · Adoption / First Launch"
              : communicationRoute
                ? "UI-A3 · Character Communication"
                : "UI-A4 · Pod / SOUL Intervention"}
          </span>
        </footer>
      </div>
    </div>
  );
}
