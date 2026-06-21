import { useEffect, useMemo, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { podMessage, type PodMessageKey } from "../../locales/pod";
import "./pod.css";

type InterventionTarget = "response_style" | "initiative" | "recovery_tone";
type InterventionStage = "intent" | "candidate" | "compared" | "held" | "discarded";
type PreviewMode = "apply" | "rollback" | null;
type TimelineLevel = "info" | "warning";

interface TargetDefinition {
  target: InterventionTarget;
  titleKey: PodMessageKey;
  bodyKey: PodMessageKey;
  summaryKey: PodMessageKey;
  sectionKey: PodMessageKey;
  beforeKey: PodMessageKey;
  afterKey: PodMessageKey;
  reasonKey: PodMessageKey;
}

interface TimelineEvent {
  eventId: string;
  code:
    | "eventCandidate"
    | "eventProtected"
    | "eventCompared"
    | "eventApplyPreview"
    | "eventRollbackPreview"
    | "eventHeld"
    | "eventDiscarded";
  level: TimelineLevel;
  metadata: string;
  occurredAt: string;
}

interface PodPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onInterventionLockChange: (locked: boolean) => void;
}

const targetDefinitions: TargetDefinition[] = [
  {
    target: "response_style",
    titleKey: "targetResponseStyle",
    bodyKey: "targetResponseStyleBody",
    summaryKey: "candidateSummaryResponseStyle",
    sectionKey: "responseSection",
    beforeKey: "responseBefore",
    afterKey: "responseAfter",
    reasonKey: "responseReason",
  },
  {
    target: "initiative",
    titleKey: "targetInitiative",
    bodyKey: "targetInitiativeBody",
    summaryKey: "candidateSummaryInitiative",
    sectionKey: "initiativeSection",
    beforeKey: "initiativeBefore",
    afterKey: "initiativeAfter",
    reasonKey: "initiativeReason",
  },
  {
    target: "recovery_tone",
    titleKey: "targetRecoveryTone",
    bodyKey: "targetRecoveryToneBody",
    summaryKey: "candidateSummaryRecoveryTone",
    sectionKey: "recoverySection",
    beforeKey: "recoveryBefore",
    afterKey: "recoveryAfter",
    reasonKey: "recoveryReason",
  },
];

const protectedTraits: Array<{ titleKey: PodMessageKey; bodyKey: PodMessageKey }> = [
  { titleKey: "protectedIdentity", bodyKey: "protectedIdentityBody" },
  { titleKey: "protectedRelationship", bodyKey: "protectedRelationshipBody" },
  { titleKey: "protectedSafety", bodyKey: "protectedSafetyBody" },
  { titleKey: "protectedMemory", bodyKey: "protectedMemoryBody" },
];

function timeLabel(language: Language): string {
  return new Intl.DateTimeFormat(language === "ja" ? "ja-JP" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function previousSoulVersion(version: string): string {
  const match = /^v(\d+)$/.exec(version);
  if (!match) {
    return "previous approved checkpoint";
  }

  const value = Number(match[1]);
  return value > 1 ? `v${value - 1}` : "initial approved checkpoint";
}

function stageStatusKey(stage: InterventionStage): PodMessageKey {
  if (stage === "compared") return "candidateCompared";
  if (stage === "held") return "candidateHeld";
  if (stage === "discarded") return "candidateDiscarded";
  return "candidatePending";
}

export function PodPage({ language, activeCharacter, onInterventionLockChange }: PodPageProps) {
  const [target, setTarget] = useState<InterventionTarget>("response_style");
  const [intent, setIntent] = useState("");
  const [stage, setStage] = useState<InterventionStage>("intent");
  const [candidateId, setCandidateId] = useState("—");
  const [preview, setPreview] = useState<PreviewMode>(null);
  const [error, setError] = useState("");
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  const definition = useMemo(
    () => targetDefinitions.find((item) => item.target === target) ?? targetDefinitions[0]!,
    [target],
  );
  const candidateActive = stage === "candidate" || stage === "compared";
  const comparisonComplete = stage === "compared";

  useEffect(() => {
    return () => onInterventionLockChange(false);
  }, [onInterventionLockChange]);

  function appendEvent(
    code: TimelineEvent["code"],
    metadata: string,
    level: TimelineLevel = "info",
  ) {
    setTimeline((events) => [
      ...events,
      {
        eventId: `${code}-${crypto.randomUUID()}`,
        code,
        level,
        metadata,
        occurredAt: timeLabel(language),
      },
    ]);
  }

  function selectTarget(nextTarget: InterventionTarget) {
    if (candidateActive || nextTarget === target) {
      return;
    }

    setTarget(nextTarget);
    setError("");
  }

  function generateCandidate() {
    if (Array.from(intent.trim()).length < 12) {
      setError(podMessage(language, "validationIntent"));
      return;
    }

    const nextCandidateId = `soul-candidate-${crypto.randomUUID().slice(0, 8)}`;
    setCandidateId(nextCandidateId);
    setStage("candidate");
    setPreview(null);
    setError("");
    setTimeline([
      {
        eventId: `candidate-${crypto.randomUUID()}`,
        code: "eventCandidate",
        level: "info",
        metadata: `candidate_id=${nextCandidateId}; target=${target}; intent_content=omitted`,
        occurredAt: timeLabel(language),
      },
      {
        eventId: `protected-${crypto.randomUUID()}`,
        code: "eventProtected",
        level: "info",
        metadata: "protected_traits=4; mutation=false",
        occurredAt: timeLabel(language),
      },
    ]);
    onInterventionLockChange(true);
  }

  function compareCandidate() {
    if (stage !== "candidate") {
      return;
    }

    setStage("compared");
    appendEvent(
      "eventCompared",
      "backend_call=false; benchmark=false; protected_traits_changed=0",
    );
  }

  function openPreview(mode: Exclude<PreviewMode, null>) {
    if (!comparisonComplete) {
      return;
    }

    setPreview(mode);
    appendEvent(
      mode === "apply" ? "eventApplyPreview" : "eventRollbackPreview",
      mode === "apply"
        ? "executed=false; server_validation=pending"
        : `executed=false; rollback_point=${previousSoulVersion(activeCharacter.soulVersion)}`,
      "warning",
    );
  }

  function holdCandidate() {
    if (!comparisonComplete) {
      return;
    }

    setStage("held");
    setPreview(null);
    appendEvent("eventHeld", "persisted=false; browser_local=true", "warning");
    onInterventionLockChange(false);
  }

  function discardCandidate() {
    if (!comparisonComplete) {
      return;
    }

    setStage("discarded");
    setPreview(null);
    appendEvent("eventDiscarded", "soul_mutation=false; history_mutation=false", "warning");
    onInterventionLockChange(false);
  }

  function resetIntervention() {
    setTarget("response_style");
    setIntent("");
    setStage("intent");
    setCandidateId("—");
    setPreview(null);
    setError("");
    setTimeline([]);
    onInterventionLockChange(false);
  }

  if (stage === "held" || stage === "discarded") {
    return (
      <div className="pod-page pod-completion-page">
        <section className="pod-completion pod-chamber">
          <span className={`pod-decision-mark pod-decision-${stage}`} aria-hidden="true">
            {stage === "held" ? "Ⅱ" : "×"}
          </span>
          <p className="eyebrow">BROWSER-LOCAL DECISION</p>
          <h1>
            {podMessage(language, stage === "held" ? "heldTitle" : "discardedTitle")}
          </h1>
          <p>{podMessage(language, stage === "held" ? "heldBody" : "discardedBody")}</p>
          <dl className="pod-completion-facts">
            <div>
              <dt>{podMessage(language, "candidateId")}</dt>
              <dd>
                <code>{candidateId}</code>
              </dd>
            </div>
            <div>
              <dt>{podMessage(language, "candidateStatus")}</dt>
              <dd>{podMessage(language, stageStatusKey(stage))}</dd>
            </div>
            <div>
              <dt>{podMessage(language, "currentSoul")}</dt>
              <dd>SOUL {activeCharacter.soulVersion} · unchanged</dd>
            </div>
          </dl>
          <button className="button button-primary" type="button" onClick={resetIntervention}>
            {podMessage(language, "startOver")}
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="pod-page">
      <section className="pod-hero pod-chamber">
        <div>
          <p className="eyebrow">{podMessage(language, "eyebrow")}</p>
          <h1>{podMessage(language, "title")}</h1>
          <p>{podMessage(language, "description")}</p>
        </div>
        <div className="pod-boundary-card">
          <span className="pod-boundary-badge">{podMessage(language, "boundaryBadge")}</span>
          <p>{podMessage(language, "boundaryBody")}</p>
        </div>
        <dl className="pod-version-strip">
          <div>
            <dt>{podMessage(language, "currentSoul")}</dt>
            <dd>SOUL {activeCharacter.soulVersion}</dd>
          </div>
          <div>
            <dt>{podMessage(language, "rollbackPoint")}</dt>
            <dd>{previousSoulVersion(activeCharacter.soulVersion)}</dd>
          </div>
          <div>
            <dt>{podMessage(language, "stability")}</dt>
            <dd>{activeCharacter.stabilityLabel}</dd>
          </div>
        </dl>
      </section>

      <div className="pod-workspace-grid">
        <div className="pod-primary-column">
          <section className="pod-panel" aria-labelledby="pod-target-title">
            <div className="pod-section-heading">
              <div>
                <p className="eyebrow">BOUNDED TARGET</p>
                <h2 id="pod-target-title">{podMessage(language, "targetTitle")}</h2>
              </div>
            </div>
            <div className="pod-target-grid">
              {targetDefinitions.map((item) => (
                <button
                  className={`pod-target-card ${target === item.target ? "pod-target-selected" : ""}`}
                  type="button"
                  key={item.target}
                  disabled={candidateActive}
                  aria-pressed={target === item.target}
                  onClick={() => selectTarget(item.target)}
                >
                  <span className="pod-target-symbol" aria-hidden="true">
                    {item.target === "response_style" ? "↯" : item.target === "initiative" ? "→" : "↺"}
                  </span>
                  <strong>{podMessage(language, item.titleKey)}</strong>
                  <small>{podMessage(language, item.bodyKey)}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="pod-panel" aria-labelledby="pod-intent-title">
            <div className="pod-section-heading">
              <div>
                <p className="eyebrow">INTENT BEFORE DIFF</p>
                <h2 id="pod-intent-title">{podMessage(language, "intentTitle")}</h2>
              </div>
            </div>
            <textarea
              className="pod-intent-input"
              value={intent}
              disabled={candidateActive}
              rows={5}
              placeholder={podMessage(language, "intentPlaceholder")}
              onChange={(event) => {
                setIntent(event.target.value);
                setError("");
              }}
            />
            <p className="pod-boundary-note">{podMessage(language, "intentBoundary")}</p>
            {error && (
              <p className="pod-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button button-primary"
              type="button"
              disabled={candidateActive}
              onClick={generateCandidate}
            >
              {podMessage(language, "generate")}
            </button>
          </section>

          <section className="pod-panel" aria-labelledby="pod-protected-title">
            <div className="pod-section-heading">
              <div>
                <p className="eyebrow">LOCKED BOUNDARY</p>
                <h2 id="pod-protected-title">{podMessage(language, "protectedTitle")}</h2>
              </div>
            </div>
            <p className="pod-panel-description">{podMessage(language, "protectedDescription")}</p>
            <div className="pod-protected-grid">
              {protectedTraits.map((trait) => (
                <article key={trait.titleKey}>
                  <span aria-hidden="true">◆</span>
                  <div>
                    <strong>{podMessage(language, trait.titleKey)}</strong>
                    <p>{podMessage(language, trait.bodyKey)}</p>
                  </div>
                  <small>LOCKED</small>
                </article>
              ))}
            </div>
          </section>

          {candidateActive && (
            <section className="pod-panel pod-candidate-panel" aria-labelledby="pod-candidate-title">
              <div className="pod-section-heading">
                <div>
                  <p className="eyebrow">HUMAN-READABLE PROJECTION</p>
                  <h2 id="pod-candidate-title">{podMessage(language, "candidateTitle")}</h2>
                </div>
                <span className={`pod-stage-badge pod-stage-${stage}`}>
                  {podMessage(language, stageStatusKey(stage))}
                </span>
              </div>
              <dl className="pod-candidate-facts">
                <div>
                  <dt>{podMessage(language, "candidateId")}</dt>
                  <dd>
                    <code>{candidateId}</code>
                  </dd>
                </div>
                <div>
                  <dt>{podMessage(language, "candidateTarget")}</dt>
                  <dd>{podMessage(language, definition.titleKey)}</dd>
                </div>
                <div>
                  <dt>{podMessage(language, "candidateStatus")}</dt>
                  <dd>{podMessage(language, stageStatusKey(stage))}</dd>
                </div>
              </dl>
              <p className="pod-candidate-summary">{podMessage(language, definition.summaryKey)}</p>

              <div className="pod-diff-heading">
                <h3>{podMessage(language, "diffTitle")}</h3>
                <p>{podMessage(language, "diffDescription")}</p>
              </div>
              <div className="pod-diff-grid">
                <div>
                  <span>{podMessage(language, "diffSection")}</span>
                  <code>{podMessage(language, definition.sectionKey)}</code>
                </div>
                <div className="pod-diff-before">
                  <span>{podMessage(language, "diffBefore")}</span>
                  <p>{podMessage(language, definition.beforeKey)}</p>
                </div>
                <div className="pod-diff-after">
                  <span>{podMessage(language, "diffAfter")}</span>
                  <p>{podMessage(language, definition.afterKey)}</p>
                </div>
                <div className="pod-diff-reason">
                  <span>{podMessage(language, "diffReason")}</span>
                  <p>{podMessage(language, definition.reasonKey)}</p>
                </div>
              </div>
            </section>
          )}

          <section className="pod-panel" aria-labelledby="pod-comparison-title">
            <div className="pod-section-heading">
              <div>
                <p className="eyebrow">ONE BOUNDED COMPARISON</p>
                <h2 id="pod-comparison-title">{podMessage(language, "compareTitle")}</h2>
              </div>
              {candidateActive && (
                <span className="pod-comparison-state">
                  {podMessage(language, comparisonComplete ? "compareComplete" : "compareReady")}
                </span>
              )}
            </div>

            {!candidateActive ? (
              <p className="pod-empty-state">{podMessage(language, "compareIdle")}</p>
            ) : (
              <>
                <div className="pod-comparison-grid">
                  <article>
                    <h3>{podMessage(language, "baseline")}</h3>
                    <dl>
                      <div>
                        <dt>{podMessage(language, "continuity")}</dt>
                        <dd>{podMessage(language, "stable")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "directness")}</dt>
                        <dd>{podMessage(language, "moderate")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "boundedness")}</dt>
                        <dd>{podMessage(language, "high")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "relationshipTone")}</dt>
                        <dd>{podMessage(language, "stable")}</dd>
                      </div>
                    </dl>
                  </article>
                  <article className={comparisonComplete ? "pod-comparison-highlight" : ""}>
                    <h3>{podMessage(language, "candidate")}</h3>
                    <dl>
                      <div>
                        <dt>{podMessage(language, "continuity")}</dt>
                        <dd>{podMessage(language, "unchanged")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "directness")}</dt>
                        <dd>{podMessage(language, "improved")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "boundedness")}</dt>
                        <dd>{podMessage(language, "high")}</dd>
                      </div>
                      <div>
                        <dt>{podMessage(language, "relationshipTone")}</dt>
                        <dd>{podMessage(language, "unchanged")}</dd>
                      </div>
                    </dl>
                  </article>
                </div>
                <p className="pod-boundary-note">{podMessage(language, "compareBoundary")}</p>
                <button
                  className="button button-primary"
                  type="button"
                  disabled={stage !== "candidate"}
                  onClick={compareCandidate}
                >
                  {podMessage(language, "compare")}
                </button>
              </>
            )}
          </section>

          <section className="pod-panel" aria-labelledby="pod-decision-title">
            <div className="pod-section-heading">
              <div>
                <p className="eyebrow">EXPLICIT DECISION</p>
                <h2 id="pod-decision-title">{podMessage(language, "decisionTitle")}</h2>
              </div>
            </div>
            <p className="pod-panel-description">{podMessage(language, "decisionDescription")}</p>
            <div className="pod-decision-actions">
              <button
                className="button pod-preview-button"
                type="button"
                disabled={!comparisonComplete}
                onClick={() => openPreview("apply")}
              >
                {podMessage(language, "applyPreview")}
              </button>
              <button
                className="button pod-preview-button"
                type="button"
                disabled={!comparisonComplete}
                onClick={() => openPreview("rollback")}
              >
                {podMessage(language, "rollbackPreview")}
              </button>
              <button
                className="button button-secondary"
                type="button"
                disabled={!comparisonComplete}
                onClick={holdCandidate}
              >
                {podMessage(language, "hold")}
              </button>
              <button
                className="button pod-discard-button"
                type="button"
                disabled={!comparisonComplete}
                onClick={discardCandidate}
              >
                {podMessage(language, "discard")}
              </button>
            </div>

            {preview && (
              <div className="pod-preview-dialog" role="dialog" aria-modal="false">
                <span className="pod-boundary-badge">PREVIEW ONLY</span>
                <h3>
                  {podMessage(
                    language,
                    preview === "apply" ? "previewTitleApply" : "previewTitleRollback",
                  )}
                </h3>
                <p>
                  {podMessage(
                    language,
                    preview === "apply" ? "previewBodyApply" : "previewBodyRollback",
                  )}
                </p>
                <button className="button button-secondary" type="button" onClick={() => setPreview(null)}>
                  {podMessage(language, "closePreview")}
                </button>
              </div>
            )}
          </section>
        </div>

        <aside className="pod-side-column">
          <section className="pod-panel" aria-labelledby="pod-protocol-title">
            <div className="pod-section-heading compact-heading">
              <div>
                <p className="eyebrow">CURRENT REQUEST PROJECTION</p>
                <h2 id="pod-protocol-title">{podMessage(language, "ctxTitle")}</h2>
              </div>
            </div>
            <dl className="pod-protocol-list">
              <div>
                <dt>{podMessage(language, "ctxRepack")}</dt>
                <dd>{podMessage(language, "applied")}</dd>
              </div>
              <div>
                <dt>{podMessage(language, "ctxUnpack")}</dt>
                <dd>{podMessage(language, "applied")}</dd>
              </div>
              <div>
                <dt>{podMessage(language, "internalCandidate")}</dt>
                <dd>{candidateActive ? podMessage(language, "present") : "—"}</dd>
              </div>
              <div>
                <dt>{podMessage(language, "visibleFilter")}</dt>
                <dd>{podMessage(language, "noChange")}</dd>
              </div>
            </dl>
          </section>

          <section className="pod-panel" aria-labelledby="pod-timeline-title">
            <div className="pod-section-heading compact-heading">
              <div>
                <p className="eyebrow">CONTENT-FREE EVENTS</p>
                <h2 id="pod-timeline-title">{podMessage(language, "timelineTitle")}</h2>
              </div>
            </div>
            <p className="pod-panel-description">{podMessage(language, "timelineDescription")}</p>
            <div className="pod-timeline" aria-live="polite">
              {timeline.length === 0 && (
                <p className="pod-empty-state">{podMessage(language, "timelineEmpty")}</p>
              )}
              {timeline.map((event) => (
                <article className={`pod-event pod-event-${event.level}`} key={event.eventId}>
                  <span className="pod-event-dot" aria-hidden="true" />
                  <div>
                    <strong>{podMessage(language, event.code)}</strong>
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
