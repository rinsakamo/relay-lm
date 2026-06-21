import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type {
  CharacterStatus,
  ChatEntry,
  ConnectionState,
  LabRoute,
  Language,
  Theme,
} from "../domain/lab";
import { translate, type MessageKey } from "../locales/messages";
import {
  initialChatEntriesByCharacter,
  mockCharacters,
  mockEvents,
  mockMemoryOutcomesByCharacter,
  mockRuntimeComponents,
} from "../mocks/lab";

const navigation: Array<{ route: LabRoute; label: MessageKey; marker: string }> = [
  { route: "home", label: "nav.home", marker: "⌂" },
  { route: "observation", label: "nav.observation", marker: "◉" },
  { route: "communication", label: "nav.communication", marker: "⇄" },
  { route: "pod", label: "nav.pod", marker: "◇" },
  { route: "adoption", label: "nav.adoption", marker: "+" },
];

const componentLabels = {
  relaylm: "RelayLM Core",
  backend: "Main LLM",
  tts: "TTS Adapter",
  avatar: "Avatar Adapter",
} as const;

function isLabRoute(value: string): value is LabRoute {
  return navigation.some((item) => item.route === value);
}

function routeFromHash(): LabRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  return isLabRoute(value) ? value : "home";
}

function relativeTimeLabel(language: Language, seconds: number): string {
  if (seconds < 60) {
    return language === "ja" ? `${seconds}秒前` : `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return language === "ja" ? `${minutes}分前` : `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  return language === "ja" ? `${hours}時間前` : `${hours}h ago`;
}

function currentTimeLabel(language: Language): string {
  return new Intl.DateTimeFormat(language === "ja" ? "ja-JP" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function statusKey(status: CharacterStatus): MessageKey {
  return `status.${status}`;
}

function connectionKey(state: ConnectionState): MessageKey {
  if (state === "degraded") {
    return "status.degraded";
  }
  return `status.${state}`;
}

function StatusBadge({
  label,
  state,
}: {
  label: string;
  state: CharacterStatus | ConnectionState;
}) {
  return <span className={`status-badge status-${state}`}>{label}</span>;
}

function PlaceholderPage({
  route,
  language,
  onNavigate,
}: {
  route: Exclude<LabRoute, "home" | "observation">;
  language: Language;
  onNavigate: (route: LabRoute) => void;
}) {
  const bodyKey: Record<typeof route, MessageKey> = {
    communication: "route.communicationBody",
    pod: "route.podBody",
    adoption: "route.adoptionBody",
  };

  return (
    <section className="placeholder-page panel-grid-surface" aria-labelledby="placeholder-title">
      <div className="placeholder-orbit" aria-hidden="true">
        <span>{route === "communication" ? "⇄" : route === "pod" ? "◇" : "+"}</span>
      </div>
      <p className="eyebrow">BOUNDARY RESERVED</p>
      <h1 id="placeholder-title">{translate(language, "route.placeholderTitle")}</h1>
      <p>{translate(language, bodyKey[route])}</p>
      <button className="button button-primary" type="button" onClick={() => onNavigate("home")}>
        {translate(language, "route.backHome")}
      </button>
    </section>
  );
}

export function App() {
  const firstCharacter = mockCharacters[0];
  if (!firstCharacter) {
    throw new Error("SOUL Lab mock data requires at least one character");
  }

  const [route, setRoute] = useState<LabRoute>(routeFromHash);
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
  const [chatEntriesByCharacter, setChatEntriesByCharacter] = useState<
    Record<string, ChatEntry[]>
  >(() =>
    Object.fromEntries(
      Object.entries(initialChatEntriesByCharacter).map(([characterId, entries]) => [
        characterId,
        [...entries],
      ]),
    ),
  );
  const [draft, setDraft] = useState("");

  const activeCharacter = useMemo(
    () => mockCharacters.find((character) => character.characterId === activeCharacterId) ?? firstCharacter,
    [activeCharacterId, firstCharacter],
  );
  const chatEntries = chatEntriesByCharacter[activeCharacter.characterId] ?? [];
  const memoryOutcomes = mockMemoryOutcomesByCharacter[activeCharacter.characterId] ?? [];

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

  useEffect(() => {
    const syncRoute = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  function navigate(nextRoute: LabRoute) {
    setRoute(nextRoute);
    const nextHash = `#/${nextRoute}`;
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function selectCharacter(characterId: string) {
    setActiveCharacterId(characterId);
    setDraft("");
  }

  function submitMockMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = draft.trim();
    if (!body) {
      return;
    }

    const occurredAtLabel = currentTimeLabel(language);
    const userEntry: ChatEntry = {
      messageId: `user-${crypto.randomUUID()}`,
      speaker: "user",
      body,
      occurredAtLabel,
    };
    const characterEntry: ChatEntry = {
      messageId: `character-${crypto.randomUUID()}`,
      speaker: "character",
      body:
        language === "ja"
          ? "これはUIモックの応答です。Runtime APIが接続されるまでは、会話内容をCoreへ送りません。"
          : "This is a UI mock response. Conversation content is not sent to Core until the Runtime API is connected.",
      occurredAtLabel,
    };

    setChatEntriesByCharacter((sessions) => ({
      ...sessions,
      [activeCharacter.characterId]: [
        ...(sessions[activeCharacter.characterId] ?? []),
        userEntry,
        characterEntry,
      ],
    }));
    setDraft("");
  }

  const runtimeConnectedCount = mockRuntimeComponents.filter(
    (component) => component.state === "connected",
  ).length;

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
          {navigation.map((item) => (
            <button
              className={`nav-item ${route === item.route ? "nav-item-active" : ""}`}
              type="button"
              key={item.route}
              aria-current={route === item.route ? "page" : undefined}
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
          <label className="character-selector">
            <span>{translate(language, "header.activeCharacter")}</span>
            <select
              value={activeCharacter.characterId}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => selectCharacter(event.target.value)}
            >
              {mockCharacters.map((character) => (
                <option value={character.characterId} key={character.characterId}>
                  {character.displayName}
                </option>
              ))}
            </select>
          </label>

          <div className="topbar-status">
            <StatusBadge
              state={activeCharacter.status}
              label={translate(language, statusKey(activeCharacter.status))}
            />
            <span className="soul-version">
              SOUL {activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}
            </span>
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
          {route === "home" && (
            <div className="home-layout">
              <section className="hero-panel panel-grid-surface">
                <div className="hero-copy">
                  <p className="eyebrow">{translate(language, "home.eyebrow")}</p>
                  <h1>{translate(language, "home.title")}</h1>
                  <p className="hero-description">{translate(language, "home.description")}</p>
                  <div className="hero-actions">
                    <button
                      className="button button-primary"
                      type="button"
                      onClick={() => navigate("observation")}
                    >
                      {translate(language, "home.openObservation")}
                    </button>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => navigate("communication")}
                    >
                      {translate(language, "home.openCommunication")}
                    </button>
                  </div>
                </div>

                <div className="character-presence" aria-label={activeCharacter.displayName}>
                  <div className="presence-ring presence-ring-outer" aria-hidden="true" />
                  <div className="presence-ring presence-ring-inner" aria-hidden="true" />
                  <div className="avatar-placeholder">
                    <span>{activeCharacter.initials}</span>
                  </div>
                  <strong>{activeCharacter.displayName}</strong>
                  <span>{activeCharacter.sceneName}</span>
                </div>

                <dl className="character-facts">
                  <div>
                    <dt>{translate(language, "home.scene")}</dt>
                    <dd>{activeCharacter.sceneName}</dd>
                  </div>
                  <div>
                    <dt>{translate(language, "home.soul")}</dt>
                    <dd>
                      {activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}
                    </dd>
                  </div>
                  <div>
                    <dt>{translate(language, "home.lastActive")}</dt>
                    <dd>{relativeTimeLabel(language, activeCharacter.lastActiveSeconds)}</dd>
                  </div>
                </dl>
              </section>

              <section className="conversation-panel surface-panel" aria-labelledby="session-title">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">TEXT FIRST</p>
                    <h2 id="session-title">{translate(language, "home.session")}</h2>
                  </div>
                  <span className="session-state">Home</span>
                </div>

                <div className="chat-log" aria-live="polite">
                  {chatEntries.map((entry) => (
                    <article className={`chat-entry chat-${entry.speaker}`} key={entry.messageId}>
                      <div className="chat-meta">
                        <strong>
                          {entry.speaker === "character"
                            ? activeCharacter.displayName
                            : entry.speaker === "user"
                              ? "You"
                              : "System"}
                        </strong>
                        <time>{entry.occurredAtLabel}</time>
                      </div>
                      <p>{entry.body}</p>
                    </article>
                  ))}
                </div>

                <form className="composer" onSubmit={submitMockMessage}>
                  <input
                    value={draft}
                    onChange={(event: ChangeEvent<HTMLInputElement>) => setDraft(event.target.value)}
                    placeholder={translate(language, "home.composerPlaceholder")}
                    aria-label={translate(language, "home.composerPlaceholder")}
                  />
                  <button className="button button-primary" type="submit" disabled={!draft.trim()}>
                    {translate(language, "home.send")}
                  </button>
                </form>
                <p className="boundary-note">{translate(language, "home.mockNotice")}</p>
              </section>

              <aside className="right-rail">
                <section className="surface-panel runtime-panel" aria-labelledby="runtime-title">
                  <div className="section-heading compact-heading">
                    <div>
                      <p className="eyebrow">
                        {runtimeConnectedCount}/{mockRuntimeComponents.length} READY
                      </p>
                      <h2 id="runtime-title">{translate(language, "runtime.title")}</h2>
                    </div>
                  </div>
                  <p className="panel-description">{translate(language, "runtime.description")}</p>
                  <div className="runtime-list">
                    {mockRuntimeComponents.map((component) => (
                      <div className="runtime-row" key={component.componentId}>
                        <div>
                          <strong>{componentLabels[component.componentId]}</strong>
                          <span>{component.detail}</span>
                        </div>
                        <StatusBadge
                          state={component.state}
                          label={translate(language, connectionKey(component.state))}
                        />
                      </div>
                    ))}
                  </div>
                </section>

                <section className="surface-panel events-panel" aria-labelledby="events-title">
                  <div className="section-heading compact-heading">
                    <div>
                      <p className="eyebrow">CONTENT-FREE SUMMARY</p>
                      <h2 id="events-title">{translate(language, "events.title")}</h2>
                    </div>
                  </div>
                  <div className="event-list">
                    {mockEvents.length === 0 && <p>{translate(language, "events.empty")}</p>}
                    {mockEvents.map((event) => (
                      <article className="event-row" key={event.eventId}>
                        <span className={`event-dot severity-${event.severity}`} aria-hidden="true" />
                        <div>
                          <strong>{event.summary}</strong>
                          <span>
                            {event.category} · {event.occurredAtLabel}
                          </span>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              </aside>
            </div>
          )}

          {route === "observation" && (
            <div className="observation-layout">
              <section className="observation-intro panel-grid-surface">
                <p className="eyebrow">{translate(language, "observation.eyebrow")}</p>
                <h1>{translate(language, "observation.title")}</h1>
                <p>{translate(language, "observation.description")}</p>
              </section>

              <section className="surface-panel memory-panel" aria-labelledby="memory-title">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">LATEST EXPERIENCE</p>
                    <h2 id="memory-title">{translate(language, "observation.memoryFormation")}</h2>
                  </div>
                </div>
                <div className="memory-grid">
                  {memoryOutcomes.map((memory) => (
                    <article className={`memory-card memory-${memory.state}`} key={memory.memoryId}>
                      <div className="memory-card-header">
                        <span>{translate(language, `memory.${memory.state}`)}</span>
                        <small>{memory.memoryId}</small>
                      </div>
                      <p>{memory.summary}</p>
                      <dl>
                        <div>
                          <dt>{translate(language, "memory.source")}</dt>
                          <dd>{memory.sourceLabel}</dd>
                        </div>
                        <div>
                          <dt>{translate(language, "memory.confidence")}</dt>
                          <dd>{memory.confidence}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              </section>

              <section className="surface-panel protocol-panel" aria-labelledby="protocol-title">
                <div className="section-heading compact-heading">
                  <div>
                    <p className="eyebrow">{translate(language, "observation.runtimeSummary")}</p>
                    <h2 id="protocol-title">{translate(language, "observation.protocol")}</h2>
                  </div>
                </div>
                <ul className="protocol-list">
                  <li>{translate(language, "observation.repack")}</li>
                  <li>{translate(language, "observation.unpack")}</li>
                  <li>{translate(language, "observation.slp")}</li>
                </ul>
              </section>
            </div>
          )}

          {route === "communication" && (
            <PlaceholderPage route="communication" language={language} onNavigate={navigate} />
          )}
          {route === "pod" && <PlaceholderPage route="pod" language={language} onNavigate={navigate} />}
          {route === "adoption" && (
            <PlaceholderPage route="adoption" language={language} onNavigate={navigate} />
          )}
        </main>

        <footer className="footer-bar">
          <span>{translate(language, "footer.boundary")}</span>
          <span>UI-A0 / UI-A1</span>
        </footer>
      </div>
    </div>
  );
}
