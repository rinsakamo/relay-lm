import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { CharacterSummary, ConnectionState, LabRoute, Language } from "../../domain/lab";
import { translate } from "../../locales/messages";
import { mockEvents, mockRuntimeComponents } from "../../mocks/lab";
import type {
  LabCharacterProjection,
  LabSettingsProjection,
} from "../settings/managementApi";
import {
  HomeConversationError,
  requestHomeConversation,
  streamHomeConversation,
} from "./homeConversationApi";
import {
  HOME_CONVERSATION_BOUNDS,
  conversationSessionKey,
  createConversationSession,
  isRequestActive,
  requestSnapshotMatches,
  resetConversationSession,
  resolveConversationTarget,
  toWireHistory,
  transcriptCharacterCount,
} from "./homeConversationState";
import type {
  ConversationFailureReason,
  ConversationMessage,
  ConversationRequestSnapshot,
  ConversationSession,
  ConversationSourceMode,
} from "./homeConversationTypes";
import "./homeConversation.css";

interface HomeConversationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  characterProjection: LabCharacterProjection | null;
  settingsProjection: LabSettingsProjection | null;
  onNavigate: (route: LabRoute) => void;
}

interface ActiveRequest {
  snapshot: ConversationRequestSnapshot;
  controller: AbortController;
  stoppedByUser: boolean;
  timedOut: boolean;
  timeoutId: number;
}

function relativeTimeLabel(language: Language, seconds: number): string {
  if (seconds < 60) return language === "ja" ? `${seconds}秒前` : `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return language === "ja" ? `${minutes}分前` : `${minutes}m ago`;
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
  if (state === "degraded") return "status.degraded" as const;
  return `status.${state}` as const;
}

function StatusBadge({ label, state }: { label: string; state: ConnectionState }) {
  return <span className={`status-badge status-${state}`}>{label}</span>;
}

function failureLabel(language: Language, reason: ConversationFailureReason): string {
  const ja: Record<ConversationFailureReason, string> = {
    unavailable: "会話routeを利用できません。",
    ambiguous_route: "会話routeを一意に決定できません。",
    invalid_request: "送信内容が会話上限または契約に適合しません。",
    http_failure: "RelayLMが会話要求を受理できませんでした。",
    timeout: "会話要求がタイムアウトしました。",
    response_invalid: "応答形式を安全に検証できませんでした。",
    response_too_large: "応答がブラウザ防御上限を超えました。",
    stream_invalid: "ストリーム形式を安全に検証できませんでした。",
    stream_truncated: "ストリームが完了前に終了しました。",
    body_unavailable: "応答本文を読み取れませんでした。",
    aborted: "会話要求を停止しました。",
    network_failure: "RelayLMへ接続できませんでした。",
  };
  const en: Record<ConversationFailureReason, string> = {
    unavailable: "No conversation route is available.",
    ambiguous_route: "The conversation route is ambiguous.",
    invalid_request: "The request does not satisfy the bounded conversation contract.",
    http_failure: "RelayLM did not accept the conversation request.",
    timeout: "The conversation request timed out.",
    response_invalid: "The response could not be validated safely.",
    response_too_large: "The response exceeded the browser safety bound.",
    stream_invalid: "The stream could not be validated safely.",
    stream_truncated: "The stream ended before completion.",
    body_unavailable: "The response body was unavailable.",
    aborted: "The conversation request was stopped.",
    network_failure: "RelayLM could not be reached.",
  };
  return (language === "ja" ? ja : en)[reason];
}

function sourceStateLabel(
  mode: ConversationSourceMode,
  session: ConversationSession,
  targetStatus: "available" | "unavailable" | "ambiguous_route",
): string {
  if (mode === "preview") return `LOCAL PREVIEW · ${session.requestState.toUpperCase()}`;
  if (targetStatus !== "available") return `REAL RUNTIME · ${targetStatus.toUpperCase()}`;
  const state = session.requestState === "idle" ? "ready" : session.requestState;
  return `REAL RUNTIME · ${state.toUpperCase()}`;
}

function updateAssistant(
  session: ConversationSession,
  messageId: string,
  updater: (message: ConversationMessage) => ConversationMessage,
): ConversationSession {
  return {
    ...session,
    messages: session.messages.map((message) =>
      message.messageId === messageId ? updater(message) : message,
    ),
  };
}

export function HomeConversationPage({
  language,
  activeCharacter,
  characterProjection,
  settingsProjection,
  onNavigate,
}: HomeConversationPageProps) {
  const [sourceModes, setSourceModes] = useState<Record<string, ConversationSourceMode>>({});
  const [streamModes, setStreamModes] = useState<Record<string, boolean>>({});
  const [sessions, setSessions] = useState<Record<string, ConversationSession>>({});
  const sessionsRef = useRef(sessions);
  const activeCharacterIdRef = useRef(activeCharacter.characterId);
  const activeRequestRef = useRef<ActiveRequest | null>(null);
  const previousCharacterIdRef = useRef(activeCharacter.characterId);

  activeCharacterIdRef.current = activeCharacter.characterId;
  sessionsRef.current = sessions;

  const sourceMode = sourceModes[activeCharacter.characterId] ?? "real";
  const stream = streamModes[activeCharacter.characterId] ?? true;
  const sessionKey = conversationSessionKey(activeCharacter.characterId, sourceMode);
  const session =
    sessions[sessionKey] ?? createConversationSession(sourceMode, `${activeCharacter.characterId}-${sourceMode}`);
  const target = useMemo(
    () => resolveConversationTarget(characterProjection, activeCharacter.characterId),
    [activeCharacter.characterId, characterProjection],
  );

  function commitSessions(
    updater: (current: Record<string, ConversationSession>) => Record<string, ConversationSession>,
  ) {
    setSessions((current) => {
      const next = updater(current);
      sessionsRef.current = next;
      return next;
    });
  }

  function currentSession(characterId: string, mode: ConversationSourceMode): ConversationSession {
    const key = conversationSessionKey(characterId, mode);
    return sessionsRef.current[key] ?? createConversationSession(mode, `${characterId}-${mode}`);
  }

  function replaceSession(characterId: string, next: ConversationSession) {
    const key = conversationSessionKey(characterId, next.sourceMode);
    commitSessions((current) => ({ ...current, [key]: next }));
  }

  function invalidateActiveRequest(markStopped: boolean) {
    const active = activeRequestRef.current;
    if (!active) return;
    active.controller.abort();
    window.clearTimeout(active.timeoutId);
    activeRequestRef.current = null;
    const key = conversationSessionKey(active.snapshot.characterId, "real");
    commitSessions((current) => {
      const existing = current[key];
      if (!existing || existing.sessionId !== active.snapshot.sessionId) return current;
      let next: ConversationSession = {
        ...existing,
        generation: existing.generation + 1,
        requestState: markStopped ? "stopped" : existing.requestState,
      };
      if (markStopped) {
        next = updateAssistant(next, active.snapshot.assistantMessageId, (message) => ({
          ...message,
          status: "stopped",
        }));
      }
      return { ...current, [key]: next };
    });
  }

  useEffect(() => {
    const previous = previousCharacterIdRef.current;
    if (previous !== activeCharacter.characterId) {
      invalidateActiveRequest(true);
      previousCharacterIdRef.current = activeCharacter.characterId;
    }
  }, [activeCharacter.characterId]);

  useEffect(() => () => invalidateActiveRequest(false), []);

  function isCurrent(snapshot: ConversationRequestSnapshot): boolean {
    if (activeCharacterIdRef.current !== snapshot.characterId) return false;
    const current = sessionsRef.current[conversationSessionKey(snapshot.characterId, "real")];
    if (!current) return false;
    return requestSnapshotMatches(snapshot, {
      characterId: activeCharacterIdRef.current,
      sessionId: current.sessionId,
      generation: current.generation,
      routeModel: snapshot.routeModel,
    });
  }

  function mutateCurrentSnapshot(
    snapshot: ConversationRequestSnapshot,
    updater: (current: ConversationSession) => ConversationSession,
  ) {
    if (!isCurrent(snapshot)) return;
    const key = conversationSessionKey(snapshot.characterId, "real");
    commitSessions((current) => {
      const existing = current[key];
      if (!existing || !isCurrent(snapshot)) return current;
      return { ...current, [key]: updater(existing) };
    });
  }

  async function executeSnapshot(snapshot: ConversationRequestSnapshot) {
    const controller = new AbortController();
    const active: ActiveRequest = {
      snapshot,
      controller,
      stoppedByUser: false,
      timedOut: false,
      timeoutId: window.setTimeout(() => {
        active.timedOut = true;
        controller.abort();
      }, HOME_CONVERSATION_BOUNDS.requestTimeoutMs),
    };
    activeRequestRef.current = active;
    mutateCurrentSnapshot(snapshot, (current) => ({
      ...current,
      requestState: snapshot.stream ? "streaming" : "submitting",
    }));

    try {
      if (snapshot.stream) {
        await streamHomeConversation(snapshot, controller.signal, (delta) => {
          if (!isCurrent(snapshot)) return;
          mutateCurrentSnapshot(snapshot, (current) =>
            updateAssistant(current, snapshot.assistantMessageId, (message) => ({
              ...message,
              content: message.content + delta,
              status: "streaming",
            })),
          );
        });
        mutateCurrentSnapshot(snapshot, (current) =>
          updateAssistant(
            { ...current, requestState: "completed" },
            snapshot.assistantMessageId,
            (message) => ({ ...message, status: "complete" }),
          ),
        );
      } else {
        const completion = await requestHomeConversation(snapshot, controller.signal);
        mutateCurrentSnapshot(snapshot, (current) =>
          updateAssistant(
            { ...current, requestState: "completed" },
            snapshot.assistantMessageId,
            (message) => ({ ...message, content: completion.text, status: "complete" }),
          ),
        );
      }
    } catch (error) {
      if (!isCurrent(snapshot)) return;
      const reason: ConversationFailureReason = active.timedOut
        ? "timeout"
        : active.stoppedByUser
          ? "aborted"
          : error instanceof HomeConversationError
            ? error.reason
            : "network_failure";
      const stopped = active.stoppedByUser;
      mutateCurrentSnapshot(snapshot, (current) =>
        updateAssistant(
          { ...current, requestState: stopped ? "stopped" : "failed" },
          snapshot.assistantMessageId,
          (message) => ({
            ...message,
            status: stopped ? "stopped" : "failed",
            failureReason: reason,
          }),
        ),
      );
    } finally {
      window.clearTimeout(active.timeoutId);
      if (activeRequestRef.current?.snapshot.requestId === snapshot.requestId) {
        activeRequestRef.current = null;
      }
    }
  }

  function updateDraft(event: ChangeEvent<HTMLTextAreaElement>) {
    const value = event.target.value;
    const current = currentSession(activeCharacter.characterId, sourceMode);
    replaceSession(activeCharacter.characterId, { ...current, draft: value });
  }

  function submitPreview(body: string) {
    const current = currentSession(activeCharacter.characterId, "preview");
    const occurredAtLabel = currentTimeLabel(language);
    const reply =
      language === "ja"
        ? "これは明示的なローカルプレビュー応答です。会話内容はRelayLMへ送信されていません。"
        : "This is an explicit local preview response. The conversation was not sent to RelayLM.";
    replaceSession(activeCharacter.characterId, {
      ...current,
      generation: current.generation + 1,
      requestState: "completed",
      draft: "",
      messages: [
        ...current.messages,
        {
          messageId: `preview-user-${crypto.randomUUID()}`,
          role: "user",
          content: body,
          status: "complete",
          occurredAtLabel,
        },
        {
          messageId: `preview-assistant-${crypto.randomUUID()}`,
          role: "assistant",
          content: reply,
          status: "complete",
          occurredAtLabel,
        },
      ],
    });
  }

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const current = currentSession(activeCharacter.characterId, sourceMode);
    const body = current.draft.trim();
    if (!body || isRequestActive(current.requestState)) return;
    if (body.length > HOME_CONVERSATION_BOUNDS.maxUserMessageChars) return;
    if (current.messages.length + 2 > HOME_CONVERSATION_BOUNDS.maxMessages) return;
    if (
      transcriptCharacterCount(current.messages) + body.length >
      HOME_CONVERSATION_BOUNDS.maxTranscriptChars
    ) return;
    if (sourceMode === "preview") {
      submitPreview(body);
      return;
    }
    if (target.status !== "available") return;

    const generation = current.generation + 1;
    const occurredAtLabel = currentTimeLabel(language);
    const userMessage: ConversationMessage = {
      messageId: `user-${crypto.randomUUID()}`,
      role: "user",
      content: body,
      status: "complete",
      occurredAtLabel,
    };
    const assistantMessage: ConversationMessage = {
      messageId: `assistant-${crypto.randomUUID()}`,
      role: "assistant",
      content: "",
      status: "pending",
      occurredAtLabel,
    };
    const snapshot: ConversationRequestSnapshot = {
      requestId: crypto.randomUUID(),
      characterId: activeCharacter.characterId,
      routeModel: target.routeModel,
      sessionId: current.sessionId,
      generation,
      sourceMode: "real",
      stream,
      messages: [...toWireHistory(current.messages), { role: "user", content: body }],
      assistantMessageId: assistantMessage.messageId,
    };
    replaceSession(activeCharacter.characterId, {
      ...current,
      generation,
      requestState: "submitting",
      draft: "",
      messages: [...current.messages, userMessage, assistantMessage],
      lastRequest: snapshot,
    });
    void executeSnapshot(snapshot);
  }

  function stopRequest() {
    const active = activeRequestRef.current;
    if (!active || active.snapshot.characterId !== activeCharacter.characterId) return;
    active.stoppedByUser = true;
    active.controller.abort();
  }

  function retryRequest() {
    const current = currentSession(activeCharacter.characterId, "real");
    const previous = current.lastRequest;
    if (!previous || isRequestActive(current.requestState) || target.status !== "available") return;
    if (target.routeModel !== previous.routeModel || previous.sessionId !== current.sessionId) return;
    const generation = current.generation + 1;
    const snapshot: ConversationRequestSnapshot = {
      ...previous,
      requestId: crypto.randomUUID(),
      generation,
    };
    const next = updateAssistant(
      { ...current, generation, requestState: "submitting", lastRequest: snapshot },
      snapshot.assistantMessageId,
      (message) => ({
        ...message,
        content: "",
        status: "pending",
        failureReason: undefined,
        occurredAtLabel: currentTimeLabel(language),
      }),
    );
    replaceSession(activeCharacter.characterId, next);
    void executeSnapshot(snapshot);
  }

  function startNewConversation() {
    invalidateActiveRequest(false);
    const current = currentSession(activeCharacter.characterId, sourceMode);
    replaceSession(activeCharacter.characterId, resetConversationSession(current));
  }

  function changeSourceMode(nextMode: ConversationSourceMode) {
    if (nextMode === sourceMode) return;
    invalidateActiveRequest(true);
    setSourceModes((current) => ({ ...current, [activeCharacter.characterId]: nextMode }));
  }

  const routeFailure = target.status === "available" ? null : target.status;
  const active = isRequestActive(session.requestState);
  const canRetry =
    sourceMode === "real" &&
    (session.requestState === "failed" || session.requestState === "stopped") &&
    session.lastRequest !== null &&
    target.status === "available" &&
    session.lastRequest.routeModel === target.routeModel;
  const draftRejected = session.draft.length > HOME_CONVERSATION_BOUNDS.maxUserMessageChars;
  const runtimeRows =
    sourceMode === "preview"
      ? mockRuntimeComponents.map((component) => ({
          id: component.componentId,
          label:
            component.componentId === "relaylm"
              ? "RelayLM Core"
              : component.componentId === "backend"
                ? "Main LLM"
                : component.componentId === "tts"
                  ? "TTS Adapter"
                  : "Avatar Adapter",
          detail: component.detail,
          state: component.state,
        }))
      : (settingsProjection?.runtime_components ?? []).map((component) => ({
          id: component.component_id,
          label: component.label,
          detail: component.capability,
          state: component.state === "configured" ? ("connected" as const) : ("unconfigured" as const),
        }));
  const readyCount = runtimeRows.filter((component) => component.state === "connected").length;

  return (
    <div className="home-layout">
      <section className="hero-panel panel-grid-surface">
        <div className="hero-copy">
          <p className="eyebrow">{translate(language, "home.eyebrow")}</p>
          <h1>{translate(language, "home.title")}</h1>
          <p className="hero-description">{translate(language, "home.description")}</p>
          <div className="hero-actions">
            <button className="button button-primary" type="button" onClick={() => onNavigate("observation")}>
              {translate(language, "home.openObservation")}
            </button>
            <button className="button button-secondary" type="button" onClick={() => onNavigate("memory")}>
              {translate(language, "home.openCommunication")}
            </button>
          </div>
        </div>
        <div className="character-presence" aria-label={activeCharacter.displayName}>
          <div className="presence-ring presence-ring-outer" aria-hidden="true" />
          <div className="presence-ring presence-ring-inner" aria-hidden="true" />
          <div className="avatar-placeholder"><span>{activeCharacter.initials}</span></div>
          <strong>{activeCharacter.displayName}</strong>
          <span>{activeCharacter.sceneName}</span>
        </div>
        <dl className="character-facts">
          <div><dt>{translate(language, "home.scene")}</dt><dd>{activeCharacter.sceneName}</dd></div>
          <div><dt>{translate(language, "home.soul")}</dt><dd>{activeCharacter.soulVersion} · {activeCharacter.stabilityLabel}</dd></div>
          <div><dt>{translate(language, "home.lastActive")}</dt><dd>{relativeTimeLabel(language, activeCharacter.lastActiveSeconds)}</dd></div>
        </dl>
      </section>

      <section className="conversation-panel surface-panel" aria-labelledby="session-title">
        <div className="section-heading conversation-heading">
          <div><p className="eyebrow">TEXT FIRST</p><h2 id="session-title">{translate(language, "home.session")}</h2></div>
          <span className="session-state">{sourceStateLabel(sourceMode, session, target.status)}</span>
        </div>
        <div className="source-toggle" role="group" aria-label="conversation source mode">
          <button
            className={sourceMode === "real" ? "toggle-active" : ""}
            type="button"
            onClick={() => changeSourceMode("real")}
          >
            REAL RUNTIME
          </button>
          <button
            className={sourceMode === "preview" ? "toggle-active" : ""}
            type="button"
            onClick={() => changeSourceMode("preview")}
          >
            LOCAL PREVIEW
          </button>
        </div>
        {sourceMode === "real" && routeFailure ? (
          <div className="conversation-warning" role="status">
            {failureLabel(language, routeFailure)}
          </div>
        ) : null}
        <div className="chat-log" aria-live="polite">
          {session.messages.length === 0 ? (
            <div className="empty-chat">
              <p>{translate(language, "home.mockNotice")}</p>
              <small>{language === "ja" ? "REAL RUNTIMEはserver projection由来のrouteだけを使います。" : "REAL RUNTIME uses only server-projected routes."}</small>
            </div>
          ) : session.messages.map((message) => (
            <article className={`chat-entry ${message.role === "user" ? "chat-user" : "chat-assistant"}`} key={message.messageId}>
              <div className="chat-meta"><strong>{message.role === "user" ? "You" : activeCharacter.displayName}</strong><span>{message.occurredAtLabel}</span></div>
              <p>{message.content || (message.status === "pending" ? "…" : "")}</p>
              {message.failureReason ? <small className="message-error">{failureLabel(language, message.failureReason)}</small> : null}
            </article>
          ))}
        </div>
        <form className="composer" onSubmit={submitMessage}>
          <textarea
            aria-label={translate(language, "home.composerPlaceholder")}
            disabled={active}
            maxLength={HOME_CONVERSATION_BOUNDS.maxUserMessageChars + 1}
            onChange={updateDraft}
            placeholder={translate(language, "home.composerPlaceholder")}
            rows={3}
            value={session.draft}
          />
          <button className="button button-primary" disabled={active || draftRejected || !session.draft.trim()} type="submit">{translate(language, "home.send")}</button>
        </form>
        <div className="conversation-controls">
          <label className="stream-toggle">
            <input
              checked={stream}
              disabled={active || sourceMode === "preview"}
              onChange={(event) => setStreamModes((current) => ({ ...current, [activeCharacter.characterId]: event.currentTarget.checked }))}
              type="checkbox"
            />
            <span>stream</span>
          </label>
          <button className="button button-secondary" disabled={!active} onClick={stopRequest} type="button">Stop</button>
          <button className="button button-secondary" disabled={!canRetry} onClick={retryRequest} type="button">Retry</button>
          <button className="button button-secondary" disabled={active} onClick={startNewConversation} type="button">New Conversation</button>
        </div>
      </section>

      <aside className="right-rail">
        <section className="runtime-panel surface-panel">
          <div className="section-heading compact-heading"><div><p className="eyebrow">RUNTIME</p><h2>{translate(language, "runtime.title")}</h2></div><StatusBadge label={`${readyCount}/${runtimeRows.length}`} state={readyCount === runtimeRows.length && runtimeRows.length > 0 ? "online" : "degraded"} /></div>
          <p className="panel-description">{translate(language, "runtime.description")}</p>
          <div className="runtime-list">
            {runtimeRows.map((component) => (
              <div className="runtime-row" key={component.id}>
                <div><strong>{component.label}</strong><span>{component.detail}</span></div>
                <StatusBadge label={translate(language, connectionKey(component.state))} state={component.state} />
              </div>
            ))}
          </div>
        </section>

        <section className="events-panel surface-panel">
          <div className="section-heading compact-heading"><div><p className="eyebrow">WORKSPACE</p><h2>{translate(language, "events.title")}</h2></div></div>
          <div className="event-list">
            {mockEvents.length === 0 ? <p>{translate(language, "events.empty")}</p> : mockEvents.map((event) => (
              <div className="event-row" key={event.eventId}>
                <span className={`event-dot severity-${event.severity}`} aria-hidden="true" />
                <div><strong>{event.title}</strong><span>{event.description}</span></div>
              </div>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}
