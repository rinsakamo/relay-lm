import { useEffect, useState } from "react";
import type { LabRoute, Language, Theme } from "../domain/lab";
import { AdoptionPage } from "../features/adoption/AdoptionPage";
import { translate, type MessageKey } from "../locales/messages";
import { App } from "./App";

const adoptionNavigation: Array<{ route: LabRoute; label: MessageKey; marker: string }> = [
  { route: "home", label: "nav.home", marker: "⌂" },
  { route: "observation", label: "nav.observation", marker: "◉" },
  { route: "communication", label: "nav.communication", marker: "⇄" },
  { route: "pod", label: "nav.pod", marker: "◇" },
  { route: "adoption", label: "nav.adoption", marker: "+" },
];

function hashRoute(): LabRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  return adoptionNavigation.some((item) => item.route === value) ? (value as LabRoute) : "home";
}

export function RootApp() {
  const [route, setRoute] = useState<LabRoute>(hashRoute);
  const [theme, setTheme] = useState<Theme>(() => {
    const storedTheme = window.localStorage.getItem("soul-lab-theme");
    if (storedTheme === "light" || storedTheme === "dark") {
      return storedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [language, setLanguage] = useState<Language>("ja");

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

  function navigate(nextRoute: LabRoute) {
    const nextHash = `#/${nextRoute}`;
    if (window.location.hash === nextHash) {
      setRoute(nextRoute);
      return;
    }
    window.location.hash = nextHash;
  }

  if (route !== "adoption") {
    return <App />;
  }

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
          {adoptionNavigation.map((item) => (
            <button
              className={`nav-item ${item.route === "adoption" ? "nav-item-active" : ""}`}
              type="button"
              key={item.route}
              aria-current={item.route === "adoption" ? "page" : undefined}
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
          <div className="character-selector">
            <span>{translate(language, "header.activeCharacter")}</span>
            <strong>NO ACTIVE CHARACTER</strong>
          </div>
          <div className="topbar-status">
            <span className="status-badge status-unconfigured">First launch</span>
            <span className="soul-version">SOUL · not initialized</span>
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
          <AdoptionPage language={language} onBackHome={() => navigate("home")} />
        </main>

        <footer className="footer-bar">
          <span>{translate(language, "footer.boundary")}</span>
          <span>UI-A2 · Adoption / First Launch</span>
        </footer>
      </div>
    </div>
  );
}
