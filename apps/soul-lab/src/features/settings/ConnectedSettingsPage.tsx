import { useEffect, useState } from "react";
import type { CharacterSummary, Language, Theme } from "../../domain/lab";
import { settingsMessage } from "../../locales/settings";
import { settingsA7Message } from "../../locales/settingsA7";
import { SettingsPage } from "./SettingsPage";
import {
  loadLabManagementProjections,
  type LabManagementProjectionBundle,
} from "./managementApi";
import "./managementProjection.css";

interface ConnectedSettingsPageProps {
  language: Language;
  theme: Theme;
  activeCharacterId: string;
  characters: CharacterSummary[];
}

type ProjectionLoadState = "loading" | "server" | "fallback";

export function ConnectedSettingsPage(props: ConnectedSettingsPageProps) {
  const { activeCharacterId, language } = props;
  const [projectionState, setProjectionState] = useState<ProjectionLoadState>("loading");
  const [projectionBundle, setProjectionBundle] =
    useState<LabManagementProjectionBundle | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setProjectionState("loading");
    loadLabManagementProjections(controller.signal)
      .then((bundle) => {
        if (controller.signal.aborted) {
          return;
        }
        setProjectionBundle(bundle);
        setProjectionState("server");
      })
      .catch(() => {
        if (controller.signal.aborted) {
          return;
        }
        setProjectionBundle(null);
        setProjectionState("fallback");
      });
    return () => controller.abort();
  }, [reloadToken]);

  const title = settingsA7Message(
    language,
    projectionState === "server"
      ? "sourceServer"
      : projectionState === "fallback"
        ? "sourceFallback"
        : "sourceLoading",
  );
  const description = settingsA7Message(
    language,
    projectionState === "server"
      ? "sourceServerDescription"
      : projectionState === "fallback"
        ? "sourceFallbackDescription"
        : "sourceLoadingDescription",
  );

  return (
    <div className="settings-page connected-settings-page">
      <section
        className={`management-projection-banner management-projection-${projectionState}`}
        aria-live="polite"
      >
        <div>
          <p className="eyebrow">{settingsA7Message(language, "sourceEyebrow")}</p>
          <strong>{title}</strong>
          <span>{description}</span>
          {projectionBundle ? (
            <span>
              {settingsA7Message(language, "schema")}: {projectionBundle.settings.schema_version}
            </span>
          ) : null}
        </div>
        <button
          className="button button-secondary"
          type="button"
          disabled={projectionState === "loading"}
          onClick={() => setReloadToken((value) => value + 1)}
        >
          {settingsA7Message(language, "retry")}
        </button>
      </section>

      {projectionState === "server" && projectionBundle ? (
        <>
          <section
            className="management-projection-grid"
            aria-label="SOUL Lab management projection"
          >
            <article className="surface-panel settings-panel">
              <p className="eyebrow">{settingsMessage(language, "runtimeEyebrow")}</p>
              <h2>{settingsMessage(language, "runtimeTitle")}</h2>
              <p className="panel-description">
                {settingsMessage(language, "runtimeDescription")}
              </p>
              <div className="settings-runtime-list">
                {projectionBundle.settings.runtime_components.map((component) => (
                  <article className="settings-runtime-card" key={component.component_id}>
                    <div className="settings-runtime-heading">
                      <strong>{component.label}</strong>
                      <span className={`settings-status settings-status-${component.state}`}>
                        {settingsMessage(language, component.state)}
                      </span>
                    </div>
                    <dl>
                      <div>
                        <dt>{settingsMessage(language, "endpoint")}</dt>
                        <dd>
                          <code>
                            {component.endpoint ??
                              settingsA7Message(language, "serverOwnedEndpoint")}
                          </code>
                        </dd>
                      </div>
                      <div>
                        <dt>{settingsMessage(language, "model")}</dt>
                        <dd>
                          {component.model_labels.join(" · ") ||
                            settingsA7Message(language, "notConfigured")}
                        </dd>
                      </div>
                      <div>
                        <dt>{settingsMessage(language, "capability")}</dt>
                        <dd>{component.capability}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </article>

            <article className="surface-panel settings-panel">
              <p className="eyebrow">{settingsMessage(language, "registryEyebrow")}</p>
              <h2>{settingsMessage(language, "registryTitle")}</h2>
              <p className="panel-description">
                {settingsMessage(language, "registryDescription")}
              </p>
              {projectionBundle.characters.characters.length === 0 ? (
                <p className="settings-empty-state">
                  {settingsA7Message(language, "registryEmpty")}
                </p>
              ) : (
                <div className="settings-character-grid">
                  {projectionBundle.characters.characters.map((character) => {
                    const active = character.character_id === activeCharacterId;
                    return (
                      <article
                        className={`settings-character-card ${active ? "settings-character-active" : ""}`}
                        key={character.character_id}
                      >
                        <div className="settings-character-avatar" aria-hidden="true">
                          {initialsFor(character.character_id)}
                        </div>
                        <div>
                          <strong>{character.character_id}</strong>
                          <code>{character.character_id}</code>
                        </div>
                        <span>{settingsMessage(language, active ? "active" : "inactive")}</span>
                        <small>
                          {settingsA7Message(
                            language,
                            character.source_complete ? "sourceComplete" : "sourceIncomplete",
                          )}
                          {" · "}
                          {settingsA7Message(language, "routeCount")}: {character.route_models.length}
                        </small>
                      </article>
                    );
                  })}
                </div>
              )}
            </article>

            <article className="surface-panel settings-panel management-projection-diagnostics">
              <p className="eyebrow">{settingsMessage(language, "diagnosticsEyebrow")}</p>
              <h2>{settingsMessage(language, "diagnosticsTitle")}</h2>
              <p className="panel-description">
                {settingsMessage(language, "diagnosticsDescription")}
              </p>
              <dl className="settings-fact-list">
                <div>
                  <dt>{settingsMessage(language, "diagnosticsMode")}</dt>
                  <dd>{projectionBundle.settings.diagnostics.mode}</dd>
                </div>
                <div>
                  <dt>{settingsA7Message(language, "contentFreeCount")}</dt>
                  <dd>{projectionBundle.settings.diagnostics.projected_event_count}</dd>
                </div>
                <div>
                  <dt>{settingsA7Message(language, "loadedCredentialCount")}</dt>
                  <dd>{projectionBundle.settings.diagnostics.credential_fields_loaded}</dd>
                </div>
              </dl>
            </article>
          </section>

          <section className="settings-authority-card" aria-labelledby="management-authority-title">
            <p className="eyebrow">{settingsMessage(language, "credentialsEyebrow")}</p>
            <h2 id="management-authority-title">
              {settingsMessage(language, "credentialsTitle")}
            </h2>
            <p>
              {settingsMessage(language, "credentialsDescription")} {" "}
              {settingsMessage(language, "boundaryDescription")}
            </p>
          </section>
        </>
      ) : null}

      {projectionState === "fallback" ? <SettingsPage {...props} /> : null}
    </div>
  );
}

function initialsFor(value: string): string {
  const parts = value.split(/[^A-Za-z0-9]+/).filter(Boolean);
  const initials = parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return initials || value.slice(0, 2).toUpperCase() || "?";
}
