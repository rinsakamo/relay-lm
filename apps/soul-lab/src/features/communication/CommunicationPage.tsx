import { useEffect, useMemo, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { communicationMessage } from "../../locales/communication";
import "./communication.css";

type PeerKind = "relaylm" | "external" | "assistant";
type PeerState = "ready" | "degraded" | "offline" | "unconfigured";
type SessionPhase = "idle" | "active" | "closing" | "ended" | "emergency";
type TimelineLevel = "info" | "warning" | "error";

interface CommunicationPeer {
  peerId: string;
  kind: PeerKind;
  state: PeerState;
  displayName: string;
  initials: string;
  endpoint: string;
  model: string;
  hintKey: "relaylmHint" | "externalHint" | "assistantHint";
}

interface TimelineEvent {
  eventId: string;
  code:
    | "eventCandidate"
    | "eventBoundary"
    | "eventStarted"
    | "eventExchange"
    | "eventClosing"
    | "eventNoTopic"
    | "eventNaturalClose"
    | "eventSlp"
    | "eventLimit"
    | "eventEmergency"
    | "eventAborted";
  level: TimelineLevel;
  occurredAt: string;
  metadata: string;
}

interface CommunicationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  characters: CharacterSummary[];
  onSessionLockChange: (locked: boolean) => void;
}

function timeLabel(language: Language): string {
  return new Intl.DateTimeFormat(language === "ja" ? "ja-JP" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function peerKindLabel(language: Language, kind: PeerKind): string {
  if (kind === "relaylm") return communicationMessage(language, "peerRelaylm");
  if (kind === "external") return communicationMessage(language, "peerExternal");
  return communicationMessage(language, "peerAssistant");
}

function peerStateLabel(language: Language, state: PeerState): string {
  if (state === "ready") return communicationMessage(language, "ready");
  if (state === "degraded") return communicationMessage(language, "degraded");
  if (state === "offline") return communicationMessage(language, "offline");
  return communicationMessage(language, "unconfigured");
}

function phaseLabel(language: Language, phase: SessionPhase): string {
  if (phase === "active") return communicationMessage(language, "phaseActive");
  if (phase === "closing") return communicationMessage(language, "phaseClosing");
  if (phase === "ended") return communicationMessage(language, "phaseEnded");
  if (phase === "emergency") return communicationMessage(language, "phaseEmergency");
  return communicationMessage(language, "phaseIdle");
}

export function CommunicationPage({
  language,
  activeCharacter,
  characters,
  onSessionLockChange,
}: CommunicationPageProps) {
  const peers = useMemo<CommunicationPeer[]>(() => {
    const otherCharacter = characters.find(
      (character) => character.characterId !== activeCharacter.characterId,
    );

    const relayPeer: CommunicationPeer = otherCharacter
      ? {
          peerId: `relaylm:${otherCharacter.characterId}`,
          kind: "relaylm",
          state:
            otherCharacter.status === "offline"
              ? "offline"
              : otherCharacter.status === "degraded"
                ? "degraded"
                : "ready",
          displayName: otherCharacter.displayName,
          initials: otherCharacter.initials,
          endpoint: `relaylm://character/${otherCharacter.characterId}`,
          model: `SOUL ${otherCharacter.soulVersion} · managed route`,
          hintKey: "relaylmHint",
        }
      : {
          peerId: "relaylm:unavailable",
          kind: "relaylm",
          state: "unconfigured",
          displayName: "RelayLM peer",
          initials: "RL",
          endpoint: "not configured",
          model: "not configured",
          hintKey: "relaylmHint",
        };

    return [
      relayPeer,
      {
        peerId: "lab-assistant",
        kind: "assistant",
        state: "ready",
        displayName: "Lab Assistant",
        initials: "LA",
        endpoint: "relaylm://lab-assistant",
        model: "built-in local peer",
        hintKey: "assistantHint",
      },
      {
        peerId: "external-openai-compatible",
        kind: "external",
        state: "unconfigured",
        displayName: "External Studio",
        initials: "EX",
        endpoint: "https://peer.example.invalid/v1",
        model: "not configured",
        hintKey: "externalHint",
      },
    ];
  }, [activeCharacter.characterId, characters]);

  const defaultPeerId = peers[0]?.peerId ?? "";
  const [selectedPeerId, setSelectedPeerId] = useState(defaultPeerId);
  const [scene, setScene] = useState("quiet_room");
  const [maxTurns, setMaxTurns] = useState(6);
  const [phase, setPhase] = useState<SessionPhase>("idle");
  const [sessionId, setSessionId] = useState("—");
  const [turnCount, setTurnCount] = useState(0);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [emergencyConfirm, setEmergencyConfirm] = useState(false);

  const selectedPeer = peers.find((peer) => peer.peerId === selectedPeerId) ?? peers[0];
  const sessionLocked = phase === "active" || phase === "closing";
  const canStart =
    Boolean(selectedPeer) &&
    (selectedPeer?.state === "ready" || selectedPeer?.state === "degraded") &&
    !sessionLocked;

  useEffect(() => {
    setSelectedPeerId(defaultPeerId);
    setScene(activeCharacter.sceneName);
    setPhase("idle");
    setSessionId("—");
    setTurnCount(0);
    setTimeline([]);
    setEmergencyConfirm(false);
    onSessionLockChange(false);
  }, [activeCharacter.characterId, activeCharacter.sceneName, defaultPeerId, onSessionLockChange]);

  useEffect(() => {
    return () => onSessionLockChange(false);
  }, [onSessionLockChange]);

  useEffect(() => {
    if (phase !== "active" || turnCount >= maxTurns) {
      return;
    }

    const timer = window.setTimeout(() => {
      const nextTurn = turnCount + 1;
      const occurredAt = timeLabel(language);
      const exchangeEvent: TimelineEvent = {
        eventId: `exchange-${crypto.randomUUID()}`,
        code: "eventExchange",
        level: "info",
        occurredAt,
        metadata: `turn=${nextTurn}/${maxTurns}; message_content=omitted`,
      };

      setTimeline((events) => [...events, exchangeEvent]);
      setTurnCount(nextTurn);

      if (nextTurn >= maxTurns) {
        setTimeline((events) => [
          ...events,
          {
            eventId: `limit-${crypto.randomUUID()}`,
            code: "eventLimit",
            level: "warning",
            occurredAt,
            metadata: `max_turns=${maxTurns}; new_topic_allowed=false`,
          },
          {
            eventId: `slp-${crypto.randomUUID()}`,
            code: "eventSlp",
            level: "info",
            occurredAt,
            metadata: "dispatch=false; candidate_only=true",
          },
        ]);
        setPhase("ended");
        onSessionLockChange(false);
      }
    }, 900);

    return () => window.clearTimeout(timer);
  }, [language, maxTurns, onSessionLockChange, phase, turnCount]);

  useEffect(() => {
    if (phase !== "closing") {
      return;
    }

    const timer = window.setTimeout(() => {
      const occurredAt = timeLabel(language);
      setTimeline((events) => [
        ...events,
        {
          eventId: `no-topic-${crypto.randomUUID()}`,
          code: "eventNoTopic",
          level: "info",
          occurredAt,
          metadata: "new_topic_allowed=false",
        },
        {
          eventId: `natural-close-${crypto.randomUUID()}`,
          code: "eventNaturalClose",
          level: "info",
          occurredAt,
          metadata: "closing_mode=natural; message_content=omitted",
        },
        {
          eventId: `slp-${crypto.randomUUID()}`,
          code: "eventSlp",
          level: "info",
          occurredAt,
          metadata: "dispatch=false; candidate_only=true",
        },
      ]);
      setPhase("ended");
      onSessionLockChange(false);
    }, 1100);

    return () => window.clearTimeout(timer);
  }, [language, onSessionLockChange, phase]);

  function resetSessionProjection() {
    setPhase("idle");
    setSessionId("—");
    setTurnCount(0);
    setTimeline([]);
    setEmergencyConfirm(false);
  }

  function selectPeer(peerId: string) {
    if (sessionLocked || peerId === selectedPeerId) {
      return;
    }

    setSelectedPeerId(peerId);
    resetSessionProjection();
  }

  function selectScene(nextScene: string) {
    if (sessionLocked || nextScene === scene) {
      return;
    }

    setScene(nextScene);
    resetSessionProjection();
  }

  function selectMaxTurns(nextMaxTurns: number) {
    if (sessionLocked || nextMaxTurns === maxTurns) {
      return;
    }

    setMaxTurns(nextMaxTurns);
    resetSessionProjection();
  }

  function startSession() {
    if (!selectedPeer || !canStart) {
      return;
    }

    const occurredAt = timeLabel(language);
    const nextSessionId = `mock-${crypto.randomUUID().slice(0, 8)}`;
    setSessionId(nextSessionId);
    setTurnCount(0);
    setEmergencyConfirm(false);
    setTimeline([
      {
        eventId: `candidate-${crypto.randomUUID()}`,
        code: "eventCandidate",
        level: "info",
        occurredAt,
        metadata: `peer_kind=${selectedPeer.kind}; scene=${scene}`,
      },
      {
        eventId: `boundary-${crypto.randomUUID()}`,
        code: "eventBoundary",
        level: selectedPeer.state === "degraded" ? "warning" : "info",
        occurredAt,
        metadata: `network_call=false; runtime_mutation=false; peer_state=${selectedPeer.state}`,
      },
      {
        eventId: `start-${crypto.randomUUID()}`,
        code: "eventStarted",
        level: "info",
        occurredAt,
        metadata: `session_id=${nextSessionId}; max_turns=${maxTurns}`,
      },
    ]);
    setPhase("active");
    onSessionLockChange(true);
  }

  function requestSoftStop() {
    if (phase !== "active") {
      return;
    }

    setEmergencyConfirm(false);
    setTimeline((events) => [
      ...events,
      {
        eventId: `closing-${crypto.randomUUID()}`,
        code: "eventClosing",
        level: "warning",
        occurredAt: timeLabel(language),
        metadata: "stop_mode=soft; new_topic_allowed=false",
      },
    ]);
    setPhase("closing");
  }

  function confirmEmergencyStop() {
    if (phase !== "active" && phase !== "closing") {
      return;
    }

    const occurredAt = timeLabel(language);
    setTimeline((events) => [
      ...events,
      {
        eventId: `emergency-${crypto.randomUUID()}`,
        code: "eventEmergency",
        level: "error",
        occurredAt,
        metadata: "stop_mode=emergency; natural_close=false",
      },
      {
        eventId: `aborted-${crypto.randomUUID()}`,
        code: "eventAborted",
        level: "error",
        occurredAt,
        metadata: "network_call=false; runtime_mutation=false; manual_review=true",
      },
    ]);
    setEmergencyConfirm(false);
    setPhase("emergency");
    onSessionLockChange(false);
  }

  return (
    <div className="communication-page">
      <section className="communication-hero panel-grid-surface">
        <div>
          <p className="eyebrow">{communicationMessage(language, "eyebrow")}</p>
          <h1>{communicationMessage(language, "title")}</h1>
          <p>{communicationMessage(language, "description")}</p>
        </div>
        <div className="communication-boundary-card">
          <span className="mock-pill">MOCK / NO NETWORK</span>
          <p>{communicationMessage(language, "mockBoundary")}</p>
        </div>
      </section>

      <section className="communication-peer-panel surface-panel" aria-labelledby="peer-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PEER BOUNDARY</p>
            <h2 id="peer-title">{communicationMessage(language, "peerTitle")}</h2>
          </div>
        </div>
        <p className="panel-description">{communicationMessage(language, "peerDescription")}</p>
        <div className="communication-peer-grid">
          {peers.map((peer) => (
            <button
              className={`communication-peer-card ${selectedPeer?.peerId === peer.peerId ? "communication-peer-selected" : ""}`}
              type="button"
              key={peer.peerId}
              disabled={sessionLocked}
              onClick={() => selectPeer(peer.peerId)}
              aria-pressed={selectedPeer?.peerId === peer.peerId}
            >
              <span className="communication-peer-avatar" aria-hidden="true">
                {peer.initials}
              </span>
              <span className="communication-peer-copy">
                <span className="communication-peer-heading">
                  <strong>{peer.displayName}</strong>
                  <span
                    className={`communication-peer-state peer-state-${peer.state === "offline" ? "unconfigured" : peer.state}`}
                  >
                    {peerStateLabel(language, peer.state)}
                  </span>
                </span>
                <small>{peerKindLabel(language, peer.kind)}</small>
                <span>{communicationMessage(language, peer.hintKey)}</span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <div className="communication-main-grid">
        <section className="communication-session-panel surface-panel" aria-labelledby="session-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SESSION CONTROL</p>
              <h2 id="session-title">{communicationMessage(language, "activeTitle")}</h2>
            </div>
            <span className={`communication-phase phase-${phase}`}>{phaseLabel(language, phase)}</span>
          </div>

          <div className="communication-participants" aria-label={communicationMessage(language, "participantTitle")}>
            <article>
              <span className="communication-participant-avatar">{activeCharacter.initials}</span>
              <div>
                <small>{communicationMessage(language, "currentCharacter")}</small>
                <strong>{activeCharacter.displayName}</strong>
                <span>{activeCharacter.sceneName}</span>
              </div>
            </article>
            <span className="communication-link" aria-hidden="true">⇄</span>
            <article>
              <span className="communication-participant-avatar">{selectedPeer?.initials ?? "—"}</span>
              <div>
                <small>{selectedPeer ? peerKindLabel(language, selectedPeer.kind) : "Peer"}</small>
                <strong>{selectedPeer?.displayName ?? "—"}</strong>
                <span>{selectedPeer?.endpoint ?? "—"}</span>
              </div>
            </article>
          </div>

          <div className="communication-setup-grid">
            <label>
              <span>{communicationMessage(language, "scene")}</span>
              <select value={scene} disabled={sessionLocked} onChange={(event) => selectScene(event.target.value)}>
                <option value="quiet_room">{communicationMessage(language, "sceneQuiet")}</option>
                <option value="after_stream">{communicationMessage(language, "sceneAfterStream")}</option>
                <option value="first_meeting">{communicationMessage(language, "sceneFirstMeeting")}</option>
              </select>
            </label>
            <label>
              <span>{communicationMessage(language, "maxTurns")}</span>
              <select
                value={maxTurns}
                disabled={sessionLocked}
                onChange={(event) => selectMaxTurns(Number(event.target.value))}
              >
                <option value={4}>4</option>
                <option value={6}>6</option>
                <option value={8}>8</option>
              </select>
            </label>
          </div>

          {selectedPeer && (
            <dl className="communication-peer-details">
              <div>
                <dt>{communicationMessage(language, "peerEndpoint")}</dt>
                <dd>{selectedPeer.endpoint}</dd>
              </div>
              <div>
                <dt>{communicationMessage(language, "peerModel")}</dt>
                <dd>{selectedPeer.model}</dd>
              </div>
            </dl>
          )}

          <dl className="communication-session-facts">
            <div>
              <dt>{communicationMessage(language, "phase")}</dt>
              <dd>{phaseLabel(language, phase)}</dd>
            </div>
            <div>
              <dt>{communicationMessage(language, "sessionId")}</dt>
              <dd><code>{sessionId}</code></dd>
            </div>
            <div>
              <dt>{communicationMessage(language, "turns")}</dt>
              <dd>{turnCount} / {maxTurns}</dd>
            </div>
            <div>
              <dt>{communicationMessage(language, "transport")}</dt>
              <dd>{communicationMessage(language, "transportMock")}</dd>
            </div>
          </dl>

          <div className="communication-actions">
            <button className="button button-primary" type="button" disabled={!canStart} onClick={startSession}>
              {phase === "ended" || phase === "emergency"
                ? communicationMessage(language, "startNew")
                : communicationMessage(language, "start")}
            </button>
            <button
              className="button button-secondary"
              type="button"
              disabled={phase !== "active"}
              onClick={requestSoftStop}
            >
              {communicationMessage(language, "softStop")}
            </button>
            <button
              className="button communication-danger-button"
              type="button"
              disabled={phase !== "active" && phase !== "closing"}
              onClick={() => setEmergencyConfirm(true)}
            >
              {communicationMessage(language, "emergencyStop")}
            </button>
          </div>

          {selectedPeer && (selectedPeer.state === "unconfigured" || selectedPeer.state === "offline") && (
            <p className="communication-warning">{communicationMessage(language, "unavailable")}</p>
          )}

          <div className="communication-stop-notes">
            <article>
              <strong>{communicationMessage(language, "softStop")}</strong>
              <p>{communicationMessage(language, "softStopDescription")}</p>
            </article>
            <article>
              <strong>{communicationMessage(language, "emergencyStop")}</strong>
              <p>{communicationMessage(language, "emergencyDescription")}</p>
            </article>
          </div>

          {emergencyConfirm && (
            <div className="communication-emergency-confirm" role="alertdialog" aria-modal="false">
              <strong>{communicationMessage(language, "emergencyConfirmTitle")}</strong>
              <p>{communicationMessage(language, "emergencyConfirmBody")}</p>
              <div>
                <button className="button button-secondary" type="button" onClick={() => setEmergencyConfirm(false)}>
                  {communicationMessage(language, "cancel")}
                </button>
                <button className="button communication-danger-button" type="button" onClick={confirmEmergencyStop}>
                  {communicationMessage(language, "emergencyConfirm")}
                </button>
              </div>
            </div>
          )}
        </section>

        <aside className="communication-side-column">
          <section className="communication-autonomy surface-panel">
            <p className="eyebrow">NO PER-MESSAGE APPROVAL</p>
            <h2>{communicationMessage(language, "autonomousLoop")}</h2>
            <p>{communicationMessage(language, "autonomousDescription")}</p>
          </section>

          <section className="communication-timeline surface-panel" aria-labelledby="timeline-title">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">{communicationMessage(language, "noMessageContent")}</p>
                <h2 id="timeline-title">{communicationMessage(language, "timelineTitle")}</h2>
              </div>
            </div>
            <p className="panel-description">{communicationMessage(language, "timelineDescription")}</p>
            <div className="communication-event-list" aria-live="polite">
              {timeline.length === 0 && (
                <p className="communication-empty-event">{communicationMessage(language, "timelineEmpty")}</p>
              )}
              {timeline.map((event) => (
                <article className={`communication-event event-${event.level}`} key={event.eventId}>
                  <span className="communication-event-dot" aria-hidden="true" />
                  <div>
                    <strong>{communicationMessage(language, event.code)}</strong>
                    <code>{event.metadata}</code>
                    <time>{event.occurredAt}</time>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
