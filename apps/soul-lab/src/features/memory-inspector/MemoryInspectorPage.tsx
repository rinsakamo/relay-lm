import { useEffect, useMemo, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import {
  memoryInspectorMessage,
  type MemoryInspectorMessageKey,
} from "../../locales/memoryInspector";
import {
  memoryInspectorRecordsByCharacter,
  type InspectorMemoryRecord,
  type MemoryOperation,
  type MemoryOutcomeState,
} from "./memoryInspectorData";
import "./memoryInspector.css";

type MemoryFilter = "all" | MemoryOutcomeState;
type TimelineLevel = "info" | "warning";

interface TimelineEvent {
  eventId: string;
  code: "eventSelected" | "eventPreviewOpened" | "eventPreviewConfirmed" | "eventPreviewCancelled";
  metadata: string;
  occurredAt: string;
  level: TimelineLevel;
}

interface OperationResult {
  operation: MemoryOperation;
  memoryId: string;
}

interface MemoryInspectorPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onInspectorLockChange: (locked: boolean) => void;
}

const filters: MemoryFilter[] = ["all", "formed", "held", "blocked"];

function timeLabel(language: Language): string {
  return new Intl.DateTimeFormat(language === "ja" ? "ja-JP" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function stateLabel(language: Language, state: MemoryOutcomeState): string {
  return memoryInspectorMessage(language, state);
}

function layerKey(record: InspectorMemoryRecord): MemoryInspectorMessageKey {
  if (record.layer === "primary") return "formedLayer";
  if (record.layer === "secondary_candidate") return "candidateLayer";
  return "blockedLayer";
}

function operationKey(operation: MemoryOperation): MemoryInspectorMessageKey {
  return operation;
}

function effectKey(operation: MemoryOperation): MemoryInspectorMessageKey {
  if (operation === "correct") return "correctEffect";
  if (operation === "forget") return "forgetEffect";
  if (operation === "pin") return "pinEffect";
  if (operation === "unpin") return "unpinEffect";
  return "mergeEffect";
}

export function MemoryInspectorPage({
  language,
  activeCharacter,
  onInspectorLockChange,
}: MemoryInspectorPageProps) {
  const records = useMemo(
    () => memoryInspectorRecordsByCharacter[activeCharacter.characterId] ?? [],
    [activeCharacter.characterId],
  );
  const [filter, setFilter] = useState<MemoryFilter>("all");
  const [selectedMemoryId, setSelectedMemoryId] = useState(records[0]?.memoryId ?? "");
  const [activeOperation, setActiveOperation] = useState<MemoryOperation | null>(null);
  const [correctionDraft, setCorrectionDraft] = useState("");
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<OperationResult | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  const filteredRecords = useMemo(
    () => records.filter((record) => filter === "all" || record.state === filter),
    [filter, records],
  );
  const selectedMemory =
    records.find((record) => record.memoryId === selectedMemoryId) ?? records[0] ?? null;
  const mergeOptions = records.filter(
    (record) => record.memoryId !== selectedMemory?.memoryId && record.state !== "blocked",
  );
  const outcomeCounts = {
    formed: records.filter((record) => record.state === "formed").length,
    held: records.filter((record) => record.state === "held").length,
    blocked: records.filter((record) => record.state === "blocked").length,
  };

  useEffect(() => {
    return () => onInspectorLockChange(false);
  }, [onInspectorLockChange]);

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
        metadata,
        occurredAt: timeLabel(language),
        level,
      },
    ]);
  }

  function selectFilter(nextFilter: MemoryFilter) {
    if (activeOperation) return;
    setFilter(nextFilter);
    const nextRecord = records.find(
      (record) => nextFilter === "all" || record.state === nextFilter,
    );
    if (nextRecord) setSelectedMemoryId(nextRecord.memoryId);
    setResult(null);
  }

  function selectMemory(memoryId: string) {
    if (activeOperation || memoryId === selectedMemoryId) return;
    setSelectedMemoryId(memoryId);
    setResult(null);
    appendEvent("eventSelected", `memory_id=${memoryId}; summary_content=omitted`);
  }

  function openOperation(operation: MemoryOperation) {
    if (activeOperation || !selectedMemory || selectedMemory.state === "blocked") return;
    if ((operation === "pin" || operation === "unpin") && selectedMemory.state !== "formed") {
      return;
    }

    setActiveOperation(operation);
    setCorrectionDraft("");
    setMergeTargetId("");
    setError("");
    setResult(null);
    onInspectorLockChange(true);
    appendEvent(
      "eventPreviewOpened",
      `memory_id=${selectedMemory.memoryId}; operation=${operation}; mutation=false`,
      operation === "forget" ? "warning" : "info",
    );
  }

  function cancelOperation() {
    if (!activeOperation || !selectedMemory) return;
    appendEvent(
      "eventPreviewCancelled",
      `memory_id=${selectedMemory.memoryId}; operation=${activeOperation}`,
    );
    setActiveOperation(null);
    setCorrectionDraft("");
    setMergeTargetId("");
    setError("");
    onInspectorLockChange(false);
  }

  function confirmOperation() {
    if (!activeOperation || !selectedMemory) return;

    if (
      activeOperation === "correct" &&
      (Array.from(correctionDraft.trim()).length < 12 ||
        correctionDraft.trim() === selectedMemory.summary.trim())
    ) {
      setError(memoryInspectorMessage(language, "correctionValidation"));
      return;
    }

    if (activeOperation === "merge" && !mergeOptions.some((record) => record.memoryId === mergeTargetId)) {
      setError(memoryInspectorMessage(language, "mergeValidation"));
      return;
    }

    appendEvent(
      "eventPreviewConfirmed",
      [
        `memory_id=${selectedMemory.memoryId}`,
        `operation=${activeOperation}`,
        activeOperation === "merge" ? `merge_target=${mergeTargetId}` : null,
        activeOperation === "correct" ? "correction_content=omitted" : null,
        activeOperation === "forget" ? "destructive=true" : "destructive=false",
        "persisted=false",
      ]
        .filter(Boolean)
        .join("; "),
      activeOperation === "forget" ? "warning" : "info",
    );
    setResult({ operation: activeOperation, memoryId: selectedMemory.memoryId });
    setActiveOperation(null);
    setCorrectionDraft("");
    setMergeTargetId("");
    setError("");
    onInspectorLockChange(false);
  }

  function actionButtons(record: InspectorMemoryRecord) {
    if (record.state === "blocked") {
      return (
        <p className="memory-inspector-boundary-note">
          {memoryInspectorMessage(language, "blockedReadOnly")}
        </p>
      );
    }

    const operationOpen = Boolean(activeOperation);
    return (
      <>
        <div className="memory-inspector-actions">
          <button
            className="button button-secondary"
            type="button"
            disabled={operationOpen}
            onClick={() => openOperation("correct")}
          >
            {memoryInspectorMessage(language, "correct")}
          </button>
          <button
            className="button memory-inspector-danger-button"
            type="button"
            disabled={operationOpen}
            onClick={() => openOperation("forget")}
          >
            {memoryInspectorMessage(language, "forget")}
          </button>
          {record.state === "formed" && (
            <button
              className="button button-secondary"
              type="button"
              disabled={operationOpen}
              onClick={() => openOperation(record.pinned ? "unpin" : "pin")}
            >
              {memoryInspectorMessage(language, record.pinned ? "unpin" : "pin")}
            </button>
          )}
          <button
            className="button button-secondary"
            type="button"
            disabled={operationOpen}
            onClick={() => openOperation("merge")}
          >
            {memoryInspectorMessage(language, "merge")}
          </button>
        </div>
        {record.state === "held" && (
          <p className="memory-inspector-boundary-note">
            {memoryInspectorMessage(language, "heldPinUnavailable")}
          </p>
        )}
      </>
    );
  }

  return (
    <div className="memory-inspector-page">
      <section className="memory-inspector-hero panel-grid-surface">
        <div>
          <p className="eyebrow">{memoryInspectorMessage(language, "eyebrow")}</p>
          <h1>{memoryInspectorMessage(language, "title")}</h1>
          <p>{memoryInspectorMessage(language, "description")}</p>
        </div>
        <div className="memory-inspector-boundary-card">
          <span className="mock-pill">{memoryInspectorMessage(language, "boundaryBadge")}</span>
          <p>{memoryInspectorMessage(language, "boundaryBody")}</p>
        </div>
        <div className="memory-inspector-counts">
          {(["formed", "held", "blocked"] as const).map((state) => (
            <div key={state}>
              <span className={`memory-inspector-count-dot memory-dot-${state}`} aria-hidden="true" />
              <strong>{outcomeCounts[state]}</strong>
              <small>{stateLabel(language, state)}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="memory-inspector-autonomy surface-panel">
        <div>
          <p className="eyebrow">NO APPROVAL QUEUE</p>
          <h2>{memoryInspectorMessage(language, "autonomousTitle")}</h2>
        </div>
        <p>{memoryInspectorMessage(language, "autonomousBody")}</p>
      </section>

      <div className="memory-inspector-workspace">
        <section className="memory-inspector-list-panel surface-panel" aria-labelledby="memory-outcomes-title">
          <div className="section-heading compact-heading">
            <div>
              <p className="eyebrow">LATEST EXPERIENCE</p>
              <h2 id="memory-outcomes-title">{memoryInspectorMessage(language, "outcomes")}</h2>
            </div>
          </div>
          <div className="memory-inspector-filters" aria-label={memoryInspectorMessage(language, "outcomes")}>
            {filters.map((item) => (
              <button
                className={filter === item ? "memory-filter-active" : ""}
                type="button"
                key={item}
                disabled={Boolean(activeOperation)}
                onClick={() => selectFilter(item)}
              >
                {memoryInspectorMessage(language, item)}
              </button>
            ))}
          </div>
          <div className="memory-inspector-record-list">
            {filteredRecords.map((record) => (
              <button
                className={`memory-inspector-record memory-record-${record.state} ${selectedMemory?.memoryId === record.memoryId ? "memory-record-selected" : ""}`}
                type="button"
                key={record.memoryId}
                disabled={Boolean(activeOperation)}
                aria-pressed={selectedMemory?.memoryId === record.memoryId}
                onClick={() => selectMemory(record.memoryId)}
              >
                <span className={`memory-inspector-count-dot memory-dot-${record.state}`} aria-hidden="true" />
                <span>
                  <span className="memory-inspector-record-heading">
                    <strong>{stateLabel(language, record.state)}</strong>
                    <small>{record.memoryId}</small>
                  </span>
                  <span className="memory-inspector-record-summary">{record.summary}</span>
                  <span className="memory-inspector-record-meta">
                    {record.sourceLabel} · {record.confidence}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="memory-inspector-detail-panel surface-panel" aria-labelledby="selected-memory-title">
          {!selectedMemory ? (
            <p className="memory-inspector-empty">{memoryInspectorMessage(language, "selectPrompt")}</p>
          ) : (
            <>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{memoryInspectorMessage(language, "selectedMemory")}</p>
                  <h2 id="selected-memory-title">{stateLabel(language, selectedMemory.state)}</h2>
                </div>
                <span className={`memory-inspector-state memory-state-${selectedMemory.state}`}>
                  {selectedMemory.state}
                </span>
              </div>

              <p className="memory-inspector-summary">{selectedMemory.summary}</p>
              <dl className="memory-inspector-facts">
                <div><dt>{memoryInspectorMessage(language, "memoryId")}</dt><dd><code>{selectedMemory.memoryId}</code></dd></div>
                <div><dt>{memoryInspectorMessage(language, "layer")}</dt><dd>{memoryInspectorMessage(language, layerKey(selectedMemory))}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "scope")}</dt><dd>{memoryInspectorMessage(language, selectedMemory.scope)}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "source")}</dt><dd>{selectedMemory.sourceLabel}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "sourceSession")}</dt><dd><code>{selectedMemory.sourceSessionId}</code></dd></div>
                <div><dt>{memoryInspectorMessage(language, "confidence")}</dt><dd>{memoryInspectorMessage(language, selectedMemory.confidence)}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "formedAt")}</dt><dd>{selectedMemory.formedAtLabel}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "pinned")}</dt><dd>{memoryInspectorMessage(language, selectedMemory.pinned ? "yes" : "no")}</dd></div>
                <div><dt>{memoryInspectorMessage(language, "usedLatest")}</dt><dd>{memoryInspectorMessage(language, selectedMemory.usedInLatestResponse ? "yes" : "no")}</dd></div>
              </dl>

              {selectedMemory.reason && (
                <div className={`memory-inspector-reason memory-reason-${selectedMemory.state}`}>
                  <strong>{memoryInspectorMessage(language, "reason")}</strong>
                  <p>{selectedMemory.reason}</p>
                </div>
              )}
              {selectedMemory.relatedPerspective && (
                <div className="memory-inspector-perspective">
                  <strong>{memoryInspectorMessage(language, "relatedPerspective")}</strong>
                  <p>{selectedMemory.relatedPerspective}</p>
                </div>
              )}

              <div className="memory-inspector-provenance">
                <div>
                  <h3>{memoryInspectorMessage(language, "provenance")}</h3>
                  <p>{memoryInspectorMessage(language, "provenanceDescription")}</p>
                </div>
                <ol>
                  {selectedMemory.provenance.map((step) => (
                    <li key={step.stepId}>
                      <span aria-hidden="true" />
                      <div><strong>{step.label}</strong><small>{step.detail}</small></div>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="memory-inspector-operation-section">
                <h3>{memoryInspectorMessage(language, "operationTitle")}</h3>
                <p>{memoryInspectorMessage(language, "operationDescription")}</p>
                {actionButtons(selectedMemory)}
              </div>

              {activeOperation && (
                <div className={`memory-inspector-preview ${activeOperation === "forget" ? "memory-preview-destructive" : ""}`} role="dialog" aria-modal="false">
                  <div className="section-heading compact-heading">
                    <div>
                      <p className="eyebrow">CANDIDATE ONLY</p>
                      <h3>{memoryInspectorMessage(language, "previewTitle")}</h3>
                    </div>
                  </div>
                  {activeOperation === "correct" && (
                    <label>
                      <span>{memoryInspectorMessage(language, "correctionLabel")}</span>
                      <textarea
                        rows={4}
                        value={correctionDraft}
                        placeholder={memoryInspectorMessage(language, "correctionPlaceholder")}
                        onChange={(event) => { setCorrectionDraft(event.target.value); setError(""); }}
                      />
                    </label>
                  )}
                  {activeOperation === "merge" && (
                    <label>
                      <span>{memoryInspectorMessage(language, "mergeTarget")}</span>
                      <select value={mergeTargetId} onChange={(event) => { setMergeTargetId(event.target.value); setError(""); }}>
                        <option value="">{memoryInspectorMessage(language, "mergeSelect")}</option>
                        {mergeOptions.map((record) => (
                          <option value={record.memoryId} key={record.memoryId}>{record.memoryId} · {record.summary}</option>
                        ))}
                      </select>
                    </label>
                  )}
                  <dl className="memory-inspector-preview-facts">
                    <div><dt>{memoryInspectorMessage(language, "previewOperation")}</dt><dd>{memoryInspectorMessage(language, operationKey(activeOperation))}</dd></div>
                    <div><dt>{memoryInspectorMessage(language, "previewTarget")}</dt><dd><code>{selectedMemory.memoryId}</code></dd></div>
                    <div><dt>{memoryInspectorMessage(language, "previewEffect")}</dt><dd>{memoryInspectorMessage(language, effectKey(activeOperation))}</dd></div>
                    <div><dt>{memoryInspectorMessage(language, "previewBoundary")}</dt><dd>{memoryInspectorMessage(language, "noExecution")}</dd></div>
                  </dl>
                  {activeOperation === "forget" && <p className="memory-inspector-forget-warning">{memoryInspectorMessage(language, "forgetWarning")}</p>}
                  {error && <p className="memory-inspector-error" role="alert">{error}</p>}
                  <div className="memory-inspector-preview-actions">
                    <button className="button button-secondary" type="button" onClick={cancelOperation}>{memoryInspectorMessage(language, "cancelPreview")}</button>
                    <button className={`button ${activeOperation === "forget" ? "memory-inspector-danger-button" : "button-primary"}`} type="button" onClick={confirmOperation}>
                      {memoryInspectorMessage(language, activeOperation === "forget" ? "confirmForget" : "confirmPreview")}
                    </button>
                  </div>
                </div>
              )}

              {result && result.memoryId === selectedMemory.memoryId && (
                <div className="memory-inspector-result" role="status">
                  <span className="mock-pill">{memoryInspectorMessage(language, "resultBadge")}</span>
                  <div>
                    <strong>
                      {memoryInspectorMessage(language, "resultTitle")} · {memoryInspectorMessage(language, operationKey(result.operation))}
                    </strong>
                    <p>{memoryInspectorMessage(language, "resultBody")}</p>
                  </div>
                  <button className="button button-secondary" type="button" onClick={() => setResult(null)}>{memoryInspectorMessage(language, "clearResult")}</button>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      <div className="memory-inspector-lower-grid">
        <section className="surface-panel memory-inspector-protocol" aria-labelledby="memory-protocol-title">
          <div className="section-heading compact-heading"><div><p className="eyebrow">LATEST RUN SUMMARY</p><h2 id="memory-protocol-title">{memoryInspectorMessage(language, "protocolTitle")}</h2></div></div>
          <dl>
            <div><dt>{memoryInspectorMessage(language, "ctxRepack")}</dt><dd>{memoryInspectorMessage(language, "applied")}</dd></div>
            <div><dt>{memoryInspectorMessage(language, "ctxUnpack")}</dt><dd>{memoryInspectorMessage(language, "applied")}</dd></div>
            <div><dt>{memoryInspectorMessage(language, "slp")}</dt><dd>{memoryInspectorMessage(language, "observed")}</dd></div>
            <div><dt>{memoryInspectorMessage(language, "relayrun")}</dt><dd>{memoryInspectorMessage(language, "completed")}</dd></div>
          </dl>
        </section>

        <section className="surface-panel memory-inspector-timeline" aria-labelledby="memory-timeline-title">
          <div className="section-heading compact-heading"><div><p className="eyebrow">CONTENT-FREE EVENTS</p><h2 id="memory-timeline-title">{memoryInspectorMessage(language, "timelineTitle")}</h2></div></div>
          <p className="panel-description">{memoryInspectorMessage(language, "timelineDescription")}</p>
          <div className="memory-inspector-event-list" aria-live="polite">
            {timeline.length === 0 && <p className="memory-inspector-empty">{memoryInspectorMessage(language, "timelineEmpty")}</p>}
            {timeline.map((event) => (
              <article className={`memory-inspector-event memory-event-${event.level}`} key={event.eventId}>
                <span aria-hidden="true" />
                <div><strong>{memoryInspectorMessage(language, event.code)}</strong><code>{event.metadata}</code><time>{event.occurredAt}</time></div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
