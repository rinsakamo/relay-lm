import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { CharacterSummary, Language, Theme } from "../../domain/lab";
import { translate } from "../../locales/messages";
import {
  settingsMessage,
  type SettingsMessageKey,
} from "../../locales/settings";
import "./settings.css";

type ProjectionState = "configured" | "unconfigured" | "offline" | "degraded";
type DraftField = "label" | "endpoint" | "model" | "capability";

interface RuntimeProjection {
  componentId: "relaylm" | "local_model" | "tts" | "avatar";
  label: string;
  state: ProjectionState;
  endpoint: string;
  model: string;
  capabilityKey:
    | "capabilityRelaylm"
    | "capabilityModel"
    | "capabilityTts"
    | "capabilityAvatar";
}

interface PeerDraft {
  label: string;
  endpoint: string;
  model: string;
  capability: string;
}

interface SettingsPageProps {
  language: Language;
  theme: Theme;
  activeCharacterId: string;
  characters: CharacterSummary[];
}

const runtimeProjections: RuntimeProjection[] = [
  {
    componentId: "relaylm",
    label: "RelayLM Core",
    state: "configured",
    endpoint: "http://127.0.0.1:8090/v1",
    model: "relaylm-managed-route",
    capabilityKey: "capabilityRelaylm",
  },
  {
    componentId: "local_model",
    label: "Local Model",
    state: "degraded",
    endpoint: "http://127.0.0.1:1234/v1",
    model: "qwen3.5-9b · mock label",
    capabilityKey: "capabilityModel",
  },
  {
    componentId: "tts",
    label: "TTS Adapter",
    state: "unconfigured",
    endpoint: "server-owned adapter endpoint",
    model: "not loaded in browser",
    capabilityKey: "capabilityTts",
  },
  {
    componentId: "avatar",
    label: "Avatar Adapter",
    state: "offline",
    endpoint: "server-owned adapter endpoint",
    model: "not loaded in browser",
    capabilityKey: "capabilityAvatar",
  },
];

const initialPeerDraft: PeerDraft = {
  label: "External Studio",
  endpoint: "https://peer.example.invalid/v1",
  model: "not configured",
  capability: "chat.completions preview",
};

function stateKey(state: ProjectionState): SettingsMessageKey {
  return state;
}

export function SettingsPage({
  language,
  theme,
  activeCharacterId,
  characters,
}: SettingsPageProps) {
  const [peerDraft, setPeerDraft] = useState<PeerDraft>({ ...initialPeerDraft });
  const [preview, setPreview] = useState<PeerDraft | null>(null);

  function updateDraft(field: DraftField, event: ChangeEvent<HTMLInputElement>) {
    const value = event.target.value;
    setPeerDraft((current) => ({ ...current, [field]: value }));
    setPreview(null);
  }

  function previewDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPreview({ ...peerDraft });
  }

  function resetDraft() {
    setPeerDraft({ ...initialPeerDraft });
    setPreview(null);
  }

  return (
    <div className="settings-page">
      <section className="settings-hero panel-grid-surface">
        <div>
          <p className="eyebrow">{settingsMessage(language, "eyebrow")}</p>
          <h1>{settingsMessage(language, "title")}</h1>
          <p>{settingsMessage(language, "description")}</p>
        </div>
        <div className="settings-boundary-badges" aria-label={settingsMessage(language, "boundaryTitle")}>
          <span>{settingsMessage(language, "projectionOnly")}</span>
          <strong>{settingsMessage(language, "notPersisted")}</strong>
        </div>
      </section>

      <div className="settings-layout">
        <div className="settings-primary-column">
          <section className="surface-panel settings-panel" aria-labelledby="registry-title">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">{settingsMessage(language, "registryEyebrow")}</p>
                <h2 id="registry-title">{settingsMessage(language, "registryTitle")}</h2>
              </div>
            </div>
            <p className="panel-description">{settingsMessage(language, "registryDescription")}</p>
            <div className="settings-character-grid">
              {characters.map((character) => {
                const active = character.characterId === activeCharacterId;
                return (
                  <article
                    className={`settings-character-card ${active ? "settings-character-active" : ""}`}
                    key={character.characterId}
                  >
                    <div className="settings-character-avatar" aria-hidden="true">
                      {character.initials}
                    </div>
                    <div>
                      <strong>{character.displayName}</strong>
                      <code>{character.characterId}</code>
                    </div>
                    <span>{settingsMessage(language, active ? "active" : "inactive")}</span>
                    <small>
                      SOUL {character.soulVersion} · {translate(language, `status.${character.status}`)}
                    </small>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="surface-panel settings-panel" aria-labelledby="runtime-projection-title">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">{settingsMessage(language, "runtimeEyebrow")}</p>
                <h2 id="runtime-projection-title">{settingsMessage(language, "runtimeTitle")}</h2>
              </div>
            </div>
            <p className="panel-description">{settingsMessage(language, "runtimeDescription")}</p>
            <div className="settings-runtime-list">
              {runtimeProjections.map((component) => (
                <article className="settings-runtime-card" key={component.componentId}>
                  <div className="settings-runtime-heading">
                    <strong>{component.label}</strong>
                    <span className={`settings-status settings-status-${component.state}`}>
                      {settingsMessage(language, stateKey(component.state))}
                    </span>
                  </div>
                  <dl>
                    <div>
                      <dt>{settingsMessage(language, "endpoint")}</dt>
                      <dd>
                        <code>{component.endpoint}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>{settingsMessage(language, "model")}</dt>
                      <dd>{component.model}</dd>
                    </div>
                    <div>
                      <dt>{settingsMessage(language, "capability")}</dt>
                      <dd>{settingsMessage(language, component.capabilityKey)}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          <section className="surface-panel settings-panel" aria-labelledby="peer-preview-title">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">{settingsMessage(language, "peerEyebrow")}</p>
                <h2 id="peer-preview-title">{settingsMessage(language, "peerTitle")}</h2>
              </div>
              <span className="mock-pill">{settingsMessage(language, "notPersisted")}</span>
            </div>
            <p className="panel-description">{settingsMessage(language, "peerDescription")}</p>

            <form className="settings-peer-form" onSubmit={previewDraft} autoComplete="off">
              <label>
                <span>{settingsMessage(language, "peerLabel")}</span>
                <input
                  value={peerDraft.label}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => updateDraft("label", event)}
                />
              </label>
              <label>
                <span>{settingsMessage(language, "peerUrl")}</span>
                <input
                  type="url"
                  value={peerDraft.endpoint}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => updateDraft("endpoint", event)}
                />
              </label>
              <label>
                <span>{settingsMessage(language, "peerModel")}</span>
                <input
                  value={peerDraft.model}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => updateDraft("model", event)}
                />
              </label>
              <label>
                <span>{settingsMessage(language, "peerCapability")}</span>
                <input
                  value={peerDraft.capability}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => updateDraft("capability", event)}
                />
              </label>
              <div className="settings-peer-actions">
                <button className="button button-primary" type="submit">
                  {settingsMessage(language, "peerPreview")}
                </button>
                <button className="button button-secondary" type="button" onClick={resetDraft}>
                  {settingsMessage(language, "peerReset")}
                </button>
              </div>
            </form>

            <div className="settings-peer-preview" aria-live="polite">
              <h3>{settingsMessage(language, "peerPreviewTitle")}</h3>
              {!preview ? (
                <p>{settingsMessage(language, "peerPreviewEmpty")}</p>
              ) : (
                <>
                  <dl>
                    <div>
                      <dt>{settingsMessage(language, "peerLabel")}</dt>
                      <dd>{preview.label}</dd>
                    </div>
                    <div>
                      <dt>{settingsMessage(language, "peerUrl")}</dt>
                      <dd>
                        <code>{preview.endpoint}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>{settingsMessage(language, "peerModel")}</dt>
                      <dd>{preview.model}</dd>
                    </div>
                    <div>
                      <dt>{settingsMessage(language, "peerCapability")}</dt>
                      <dd>{preview.capability}</dd>
                    </div>
                  </dl>
                  <ul>
                    <li>{settingsMessage(language, "peerCredentialNote")}</li>
                    <li>{settingsMessage(language, "peerNetworkNote")}</li>
                    <li>{settingsMessage(language, "peerPersistenceNote")}</li>
                  </ul>
                </>
              )}
            </div>
          </section>
        </div>

        <aside className="settings-secondary-column">
          <section className="surface-panel settings-panel" aria-labelledby="credential-title">
            <p className="eyebrow">{settingsMessage(language, "credentialsEyebrow")}</p>
            <h2 id="credential-title">{settingsMessage(language, "credentialsTitle")}</h2>
            <p className="panel-description">{settingsMessage(language, "credentialsDescription")}</p>
            <dl className="settings-fact-list">
              <div>
                <dt>{settingsMessage(language, "credentialOwner")}</dt>
                <dd>{settingsMessage(language, "credentialOwnerValue")}</dd>
              </div>
              <div>
                <dt>{settingsMessage(language, "credentialBrowser")}</dt>
                <dd>{settingsMessage(language, "credentialBrowserValue")}</dd>
              </div>
              <div>
                <dt>{settingsMessage(language, "credentialStorage")}</dt>
                <dd>{settingsMessage(language, "credentialStorageValue")}</dd>
              </div>
            </dl>
          </section>

          <section className="surface-panel settings-panel" aria-labelledby="display-title">
            <p className="eyebrow">{settingsMessage(language, "displayEyebrow")}</p>
            <h2 id="display-title">{settingsMessage(language, "displayTitle")}</h2>
            <p className="panel-description">{settingsMessage(language, "displayDescription")}</p>
            <dl className="settings-fact-list">
              <div>
                <dt>{settingsMessage(language, "theme")}</dt>
                <dd>{settingsMessage(language, theme)}</dd>
              </div>
              <div>
                <dt>{settingsMessage(language, "language")}</dt>
                <dd>{settingsMessage(language, language === "ja" ? "japanese" : "english")}</dd>
              </div>
            </dl>
          </section>

          <section className="surface-panel settings-panel" aria-labelledby="capability-title">
            <p className="eyebrow">{settingsMessage(language, "capabilityEyebrow")}</p>
            <h2 id="capability-title">{settingsMessage(language, "capabilityTitle")}</h2>
            <p className="panel-description">{settingsMessage(language, "capabilityDescription")}</p>
            <ul className="settings-capability-list">
              {(
                [
                  "capabilityRelaylm",
                  "capabilityModel",
                  "capabilityTts",
                  "capabilityAvatar",
                ] as const
              ).map((key, index) => (
                <li key={key}>
                  <span>{settingsMessage(language, key)}</span>
                  <strong>
                    {settingsMessage(
                      language,
                      index < 2 ? "availableProjection" : "executionDisabled",
                    )}
                  </strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="surface-panel settings-panel" aria-labelledby="diagnostics-title">
            <p className="eyebrow">{settingsMessage(language, "diagnosticsEyebrow")}</p>
            <h2 id="diagnostics-title">{settingsMessage(language, "diagnosticsTitle")}</h2>
            <p className="panel-description">{settingsMessage(language, "diagnosticsDescription")}</p>
            <dl className="settings-fact-list">
              <div>
                <dt>{settingsMessage(language, "diagnosticsMode")}</dt>
                <dd>{settingsMessage(language, "diagnosticsModeValue")}</dd>
              </div>
              <div>
                <dt>{settingsMessage(language, "diagnosticsEvents")}</dt>
                <dd>{settingsMessage(language, "diagnosticsEventsValue")}</dd>
              </div>
              <div>
                <dt>{settingsMessage(language, "diagnosticsSecrets")}</dt>
                <dd>{settingsMessage(language, "diagnosticsSecretsValue")}</dd>
              </div>
            </dl>
          </section>

          <section className="settings-authority-card" aria-labelledby="settings-authority-title">
            <p className="eyebrow">{settingsMessage(language, "boundaryEyebrow")}</p>
            <h2 id="settings-authority-title">{settingsMessage(language, "boundaryTitle")}</h2>
            <p>{settingsMessage(language, "boundaryDescription")}</p>
          </section>
        </aside>
      </div>
    </div>
  );
}
