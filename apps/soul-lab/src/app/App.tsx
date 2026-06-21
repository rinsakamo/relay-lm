import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type {
  CharacterSummary,
  ChatEntry,
  ConnectionState,
  LabRoute,
  Language,
} from "../domain/lab";
import { translate } from "../locales/messages";
import {
  initialChatEntriesByCharacter,
  mockEvents,
  mockRuntimeComponents,
} from "../mocks/lab";

const componentLabels = {
  relaylm: "RelayLM Core",
  backend: "Main LLM",
  tts: "TTS Adapter",
  avatar: "Avatar Adapter",
} as const;

interface AppProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onNavigate: (route: LabRoute) => void;
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

function connectionKey(state: ConnectionState) {
  if (state === "degraded") {
    return "status.degraded" as const;
  }
  return `status.${state}` as const;
}

function StatusBadge({ label, state }: { label: string; state: ConnectionState }) {
  return <span className={`status-badge status-${state}`}>{label}</span>;
}

export function App({ language, activeCharacter, onNavigate }: AppProps) {
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
  const [draftsByCharacter, setDraftsByCharacter] = useState<Record<string, string>>({});

  const chatEntries = chatEntriesByCharacter[activeCharacter.characterId] ?? [];
  const draft = draftsByCharacter[activeCharacter.characterId] ?? "";
  const runtimeConnectedCount = mockRuntimeComponents.filter(
    (component) => component.state === "connected",
  ).length;

  function updateDraft(event: ChangeEvent<HTMLInputElement>) {
    const value = event.target.value;
    setDraftsByCharacter((drafts) => ({
      ...drafts,
      [activeCharacter.characterId]: value,
    }));
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
    setDraftsByCharacter((drafts) => ({
      ...drafts,
      [activeCharacter.characterId]: "",
    }));
  }

  return (
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
              onClick={() => onNavigate("observation")}
            >
              {translate(language, "home.openObservation")}
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => onNavigate("communication")}
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
          <span className="session-state">MOCK SESSION</span>
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
            onChange={updateDraft}
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
  );
}
