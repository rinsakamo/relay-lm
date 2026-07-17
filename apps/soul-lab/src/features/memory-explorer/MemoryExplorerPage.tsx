import { useEffect, useMemo, useRef, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { memoryExplorerMessage } from "../../locales/memoryExplorer";
import {
  getMemoryExplorerSessionRecords,
  saveMemoryExplorerSessionRecords,
} from "./memoryExplorerData";
import {
  addUserTag,
  applyForgetToRecords,
  buildSearchPlan,
  distinctSubjects,
  distinctSystemTags,
  distinctUserTags,
  groupRelatedBySubject,
  isTagOperationBusy,
  relatedRecordsFor,
  removeUserTag,
  renameUserTag,
  restoreFromHidden,
  runMemoryExplorerSearch,
  shouldSimulateError,
  tokenize,
  type TagValidationError,
} from "./memoryExplorerEngine";
import {
  defaultFilters,
  defaultSearchParams,
  type ForgetStage,
  type MemoryExplorerRecord,
  type MemoryExplorerSearchParams,
  type MemoryKind,
  type MemoryLifecycleStatus,
  type PlanStep,
  type SearchMode,
  type SearchStatus,
  type SortKey,
  type TagEditState,
} from "./memoryExplorerTypes";
import "./memoryExplorer.css";

interface MemoryExplorerPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onExplorerLockChange: (locked: boolean) => void;
}

interface TagOperation {
  kind: "add" | "rename" | "remove";
  state: TagEditState;
  error: TagValidationError | null;
}

interface ExplorerEvent {
  eventId: string;
  label: string;
  metadata: string;
  occurredAtLabel: string;
  level: "info" | "warning";
}

const memoryKinds: MemoryKind[] = ["episodic", "preference", "relationship", "procedural", "boundary"];
const searchModes: SearchMode[] = ["keyword", "semantic", "hybrid"];
const sortKeys: SortKey[] = ["relevance", "recentlyFormed", "recentlyUsed"];
const statuses: MemoryLifecycleStatus[] = ["active", "hidden"];

function copy(language: Language, japanese: string, english: string): string {
  return language === "ja" ? japanese : english;
}

function timeLabel(language: Language): string {
  return new Intl.DateTimeFormat(language === "ja" ? "ja-JP" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function kindLabel(language: Language, kind: MemoryKind): string {
  const keys = {
    episodic: "kindEpisodic",
    preference: "kindPreference",
    relationship: "kindRelationship",
    procedural: "kindProcedural",
    boundary: "kindBoundary",
  } as const;
  return memoryExplorerMessage(language, keys[kind]);
}

function statusLabel(language: Language, status: MemoryLifecycleStatus): string {
  return memoryExplorerMessage(language, status === "active" ? "statusActive" : "statusHidden");
}

function modeLabel(language: Language, mode: SearchMode): string {
  const keys = { keyword: "modeKeyword", semantic: "modeSemantic", hybrid: "modeHybrid" } as const;
  return memoryExplorerMessage(language, keys[mode]);
}

function sortLabel(language: Language, sort: SortKey): string {
  const keys = {
    relevance: "sortRelevance",
    recentlyFormed: "sortRecentlyFormed",
    recentlyUsed: "sortRecentlyUsed",
  } as const;
  return memoryExplorerMessage(language, keys[sort]);
}

function confidenceLabel(language: Language, value: MemoryExplorerRecord["confidence"]): string {
  const keys = { high: "confidenceHigh", medium: "confidenceMedium", low: "confidenceLow" } as const;
  return memoryExplorerMessage(language, keys[value]);
}

function provenanceLabel(language: Language, value: MemoryExplorerRecord["provenanceAvailability"]): string {
  const keys = {
    available: "provenanceAvailable",
    partial: "provenancePartial",
    unavailable: "provenanceUnavailable",
  } as const;
  return memoryExplorerMessage(language, keys[value]);
}

function tagErrorLabel(language: Language, error: TagValidationError): string {
  const keys = {
    empty: "tagErrorEmpty",
    tooLong: "tagErrorTooLong",
    duplicate: "tagErrorDuplicate",
    collidesWithSystemTag: "tagErrorCollidesWithSystemTag",
  } as const;
  return memoryExplorerMessage(language, keys[error]);
}

function formatPlanStep(language: Language, step: PlanStep): string {
  switch (step.kind) {
    case "mode":
      return modeLabel(language, step.mode);
    case "queryTerms":
      return `${memoryExplorerMessage(language, "planQueryTerms")} ${step.terms.join(language === "ja" ? "、" : ", ")}`;
    case "userTags":
      return `${memoryExplorerMessage(language, "planUserTags")} ${step.tags.join(language === "ja" ? "、" : ", ")}`;
    case "systemTags":
      return `${memoryExplorerMessage(language, "planSystemTags")} ${step.tags.join(language === "ja" ? "、" : ", ")}`;
    case "memoryKind":
      return `${memoryExplorerMessage(language, "planKind")} ${kindLabel(language, step.value)}`;
    case "status":
      return memoryExplorerMessage(language, step.value === "active" ? "planStatusActive" : "planStatusHidden");
    case "subject":
      return `${memoryExplorerMessage(language, "planSubject")} ${step.value}`;
    case "dateRange":
      return `${memoryExplorerMessage(language, "planDateRange")} ${step.from || "…"} – ${step.to || "…"}`;
    case "recentlyFormed":
      return memoryExplorerMessage(language, "planRecentlyFormed");
    case "recentlyUsed":
      return memoryExplorerMessage(language, "planRecentlyUsed");
    case "sort":
      return sortLabel(language, step.value);
  }
}

function rewriteUserTagFilter(
  params: MemoryExplorerSearchParams,
  operation: "rename" | "remove",
  oldName: string,
  newName?: string,
): MemoryExplorerSearchParams {
  const userTags = params.filters.userTags
    .map((tag) => (operation === "rename" && tag === oldName ? (newName ?? tag) : tag))
    .filter((tag) => operation !== "remove" || tag !== oldName);
  return { ...params, filters: { ...params.filters, userTags: Array.from(new Set(userTags)) } };
}

export function MemoryExplorerPage({ language, activeCharacter, onExplorerLockChange }: MemoryExplorerPageProps) {
  const initialRecords = useMemo(
    () => getMemoryExplorerSessionRecords(activeCharacter.characterId, activeCharacter.displayName),
    [activeCharacter.characterId, activeCharacter.displayName],
  );
  const [records, setRecords] = useState<MemoryExplorerRecord[]>(initialRecords);
  const [draftParams, setDraftParams] = useState<MemoryExplorerSearchParams>(defaultSearchParams);
  const [executedParams, setExecutedParams] = useState<MemoryExplorerSearchParams>(defaultSearchParams);
  const [results, setResults] = useState(() => runMemoryExplorerSearch(initialRecords, defaultSearchParams()));
  const [selectedMemoryId, setSelectedMemoryId] = useState(() => results[0]?.memoryId ?? "");
  const [searchStatus, setSearchStatus] = useState<SearchStatus>("ready");
  const [tagOperation, setTagOperation] = useState<TagOperation | null>(null);
  const [newTagDraft, setNewTagDraft] = useState("");
  const [renamingTag, setRenamingTag] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [correctionOpen, setCorrectionOpen] = useState(false);
  const [correctionSummary, setCorrectionSummary] = useState("");
  const [correctionContent, setCorrectionContent] = useState("");
  const [forgetStage, setForgetStage] = useState<ForgetStage>("idle");
  const [events, setEvents] = useState<ExplorerEvent[]>([]);
  const timers = useRef<number[]>([]);

  const selectedRecord = records.find((record) => record.memoryId === selectedMemoryId) ?? null;
  const isBusy = searchStatus === "loading" || isTagOperationBusy(tagOperation?.state) || forgetStage === "confirming" || forgetStage === "pending";
  const isStale = searchStatus !== "loading" && JSON.stringify(draftParams) !== JSON.stringify(executedParams);
  const userTags = useMemo(() => distinctUserTags(records), [records]);
  const systemTags = useMemo(() => distinctSystemTags(records), [records]);
  const subjects = useMemo(() => distinctSubjects(records), [records]);
  const plan = useMemo(() => buildSearchPlan(draftParams), [draftParams]);
  const relatedGroups = useMemo(
    () => (selectedRecord ? groupRelatedBySubject(relatedRecordsFor(records, selectedRecord)) : []),
    [records, selectedRecord],
  );

  useEffect(() => {
    onExplorerLockChange(isBusy);
  }, [isBusy, onExplorerLockChange]);

  useEffect(() => {
    return () => {
      for (const timer of timers.current) window.clearTimeout(timer);
      onExplorerLockChange(false);
    };
  }, [onExplorerLockChange]);

  function schedule(callback: () => void, delay: number) {
    const timer = window.setTimeout(() => {
      timers.current = timers.current.filter((candidate) => candidate !== timer);
      callback();
    }, delay);
    timers.current.push(timer);
  }

  function appendEvent(label: string, metadata: string, level: ExplorerEvent["level"] = "info") {
    setEvents((current) => [
      ...current,
      {
        eventId: crypto.randomUUID(),
        label,
        metadata,
        occurredAtLabel: timeLabel(language),
        level,
      },
    ]);
  }

  function refreshWith(
    nextRecords: MemoryExplorerRecord[],
    nextExecuted: MemoryExplorerSearchParams = executedParams,
    preferredSelection: string = selectedMemoryId,
  ) {
    saveMemoryExplorerSessionRecords(activeCharacter.characterId, nextRecords);
    setRecords(nextRecords);
    const nextResults = runMemoryExplorerSearch(nextRecords, nextExecuted);
    setResults(nextResults);
    setSelectedMemoryId(
      nextResults.some((record) => record.memoryId === preferredSelection)
        ? preferredSelection
        : (nextResults[0]?.memoryId ?? ""),
    );
  }

  function updateDraft(mutate: (current: MemoryExplorerSearchParams) => MemoryExplorerSearchParams) {
    if (!isBusy) setDraftParams(mutate);
  }

  function executeSearch() {
    if (isBusy) return;
    const params = structuredClone(draftParams);
    setSearchStatus("loading");
    schedule(() => {
      if (shouldSimulateError(params.query)) {
        setSearchStatus("error");
        appendEvent("explorer.search_executed", `mode=${params.mode}; result=error`, "warning");
        return;
      }
      const nextResults = runMemoryExplorerSearch(records, params);
      setExecutedParams(params);
      setResults(nextResults);
      setSelectedMemoryId((current) =>
        nextResults.some((record) => record.memoryId === current) ? current : (nextResults[0]?.memoryId ?? ""),
      );
      setSearchStatus("ready");
      appendEvent(
        "explorer.search_executed",
        `mode=${params.mode}; token_count=${tokenize(params.query).length}; result_count=${nextResults.length}`,
      );
    }, 350);
  }

  function selectMemory(memoryId: string) {
    if (isBusy) return;
    setSelectedMemoryId(memoryId);
    setCorrectionOpen(false);
    setRenamingTag(null);
    setTagOperation(null);
    setForgetStage("idle");
    appendEvent("explorer.memory_selected", `memory_id=${memoryId}`);
  }

  function applyTagOperation(
    kind: TagOperation["kind"],
    perform: (record: MemoryExplorerRecord) => { ok: boolean; tags: string[]; error: TagValidationError | null },
    oldName?: string,
  ) {
    if (!selectedRecord || isBusy) return;
    const captured = selectedRecord;
    setTagOperation({ kind, state: "pending", error: null });
    onExplorerLockChange(true);
    schedule(() => {
      const outcome = perform(captured);
      if (!outcome.ok) {
        setTagOperation({ kind, state: "failed", error: outcome.error });
        appendEvent("explorer.tag_edit_failed", `memory_id=${captured.memoryId}; action=${kind}; error=${outcome.error}`, "warning");
        onExplorerLockChange(false);
        return;
      }

      let nextDraft = draftParams;
      let nextExecuted = executedParams;
      if (kind === "rename" && oldName) {
        const newName = outcome.tags.find((tag) => !captured.userTags.includes(tag)) ?? renameDraft.trim();
        nextDraft = rewriteUserTagFilter(draftParams, "rename", oldName, newName);
        nextExecuted = rewriteUserTagFilter(executedParams, "rename", oldName, newName);
      } else if (kind === "remove" && oldName) {
        nextDraft = rewriteUserTagFilter(draftParams, "remove", oldName);
        nextExecuted = rewriteUserTagFilter(executedParams, "remove", oldName);
      }

      const nextRecords = records.map((record) =>
        record.memoryId === captured.memoryId ? { ...record, userTags: outcome.tags } : record,
      );
      setDraftParams(nextDraft);
      setExecutedParams(nextExecuted);
      refreshWith(nextRecords, nextExecuted, captured.memoryId);
      setTagOperation({ kind, state: "applied", error: null });
      setNewTagDraft("");
      setRenamingTag(null);
      appendEvent("explorer.tag_edit_applied", `memory_id=${captured.memoryId}; action=${kind}_user_tag`);
      schedule(() => setTagOperation(null), 1400);
    }, 300);
  }

  function openCorrection() {
    if (!selectedRecord || isBusy) return;
    setCorrectionSummary(selectedRecord.summary);
    setCorrectionContent(selectedRecord.content);
    setCorrectionOpen(true);
  }

  function saveCorrection() {
    if (!selectedRecord || isBusy || !correctionSummary.trim() || !correctionContent.trim()) return;
    const nextRecords = records.map((record) =>
      record.memoryId === selectedRecord.memoryId
        ? { ...record, summary: correctionSummary.trim(), content: correctionContent.trim() }
        : record,
    );
    refreshWith(nextRecords, executedParams, selectedRecord.memoryId);
    appendEvent("explorer.correction_applied", `memory_id=${selectedRecord.memoryId}; fields=summary,content`);
    setCorrectionOpen(false);
  }

  function confirmForget() {
    if (!selectedRecord || isBusy && forgetStage !== "confirming") return;
    const memoryId = selectedRecord.memoryId;
    setForgetStage("pending");
    schedule(() => {
      const nextRecords = applyForgetToRecords(records, memoryId, timeLabel(language));
      refreshWith(nextRecords, executedParams, memoryId);
      setForgetStage("applied");
      appendEvent("explorer.forget_confirmed", `memory_id=${memoryId}`, "warning");
      onExplorerLockChange(false);
      schedule(() => setForgetStage("idle"), 1800);
    }, 350);
  }

  function restoreSelected() {
    if (!selectedRecord || selectedRecord.status !== "hidden" || isBusy) return;
    const nextRecords = restoreFromHidden(records, selectedRecord.memoryId);
    refreshWith(nextRecords, executedParams, selectedRecord.memoryId);
    appendEvent("explorer.restore_applied", `memory_id=${selectedRecord.memoryId}`);
  }

  function toggleTagFilter(key: "userTags" | "systemTags", value: string) {
    updateDraft((current) => ({
      ...current,
      filters: {
        ...current.filters,
        [key]: current.filters[key].includes(value)
          ? current.filters[key].filter((tag) => tag !== value)
          : [...current.filters[key], value],
      },
    }));
  }

  return (
    <div className="memory-explorer-page">
      <section className="memory-explorer-hero panel-grid-surface">
        <div>
          <p className="eyebrow">MEMORY EXPLORER</p>
          <h1>{memoryExplorerMessage(language, "title")}</h1>
          <p>{memoryExplorerMessage(language, "description")}</p>
        </div>
        <div className="memory-explorer-boundary-card">
          <span className="mock-pill">{memoryExplorerMessage(language, "boundaryBadge")}</span>
          <p>{memoryExplorerMessage(language, "boundaryBody")}</p>
        </div>
      </section>

      <section className="memory-explorer-autonomy surface-panel">
        <div>
          <p className="eyebrow">NO APPROVAL QUEUE</p>
          <h2>{memoryExplorerMessage(language, "autonomyTitle")}</h2>
        </div>
        <p>{memoryExplorerMessage(language, "autonomyBody")}</p>
      </section>

      <section className="surface-panel memory-explorer-search" aria-labelledby="explorer-search-title">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">NATURAL LANGUAGE SEARCH</p>
            <h2 id="explorer-search-title">{memoryExplorerMessage(language, "searchLabel")}</h2>
          </div>
        </div>
        <form
          className="memory-explorer-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            executeSearch();
          }}
        >
          <input
            type="text"
            aria-label={memoryExplorerMessage(language, "searchLabel")}
            placeholder={memoryExplorerMessage(language, "searchPlaceholder")}
            value={draftParams.query}
            disabled={isBusy}
            onChange={(event) => updateDraft((current) => ({ ...current, query: event.target.value }))}
          />
          <div className="memory-explorer-mode-group" role="radiogroup" aria-label={memoryExplorerMessage(language, "modeGroupLabel")}>
            {searchModes.map((mode) => (
              <button
                type="button"
                role="radio"
                aria-checked={draftParams.mode === mode}
                className={draftParams.mode === mode ? "memory-explorer-mode-active" : ""}
                disabled={isBusy}
                key={mode}
                onClick={() => updateDraft((current) => ({ ...current, mode }))}
              >
                {modeLabel(language, mode)}
              </button>
            ))}
          </div>
          <button className="button button-primary" type="submit" disabled={isBusy}>
            {memoryExplorerMessage(language, "searchButton")}
          </button>
        </form>

        <div className="memory-explorer-plan">
          <h3>{memoryExplorerMessage(language, "planTitle")}</h3>
          <p className="panel-description">{memoryExplorerMessage(language, "planDescription")}</p>
          <ul className="memory-explorer-plan-list">
            {plan.map((step, index) => <li key={`${step.kind}-${index}`}>{formatPlanStep(language, step)}</li>)}
          </ul>
        </div>
        {isStale && searchStatus !== "error" && <p className="memory-explorer-stale" role="status">{memoryExplorerMessage(language, "staleNotice")}</p>}
        {searchStatus === "loading" && <p className="memory-explorer-loading" role="status">{memoryExplorerMessage(language, "loadingLabel")}</p>}
        {searchStatus === "error" && (
          <div className="memory-explorer-error" role="alert">
            <strong>{memoryExplorerMessage(language, "errorTitle")}</strong>
            <p>{memoryExplorerMessage(language, "errorBody")}</p>
            <button className="button button-secondary" type="button" onClick={executeSearch}>{memoryExplorerMessage(language, "retryButton")}</button>
          </div>
        )}
      </section>

      <section className="surface-panel memory-explorer-filters" aria-labelledby="explorer-filters-title">
        <div className="section-heading compact-heading">
          <div><p className="eyebrow">FILTERS AND SORTING</p><h2 id="explorer-filters-title">{memoryExplorerMessage(language, "filtersTitle")}</h2></div>
          <button className="button button-secondary" type="button" disabled={isBusy} onClick={() => updateDraft((current) => ({ ...current, filters: defaultFilters() }))}>
            {memoryExplorerMessage(language, "clearFilters")}
          </button>
        </div>
        <div className="memory-explorer-filter-grid">
          <label><span>{memoryExplorerMessage(language, "filterKind")}</span><select value={draftParams.filters.kind} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, filters: { ...current.filters, kind: event.target.value as MemoryKind | "all" } }))}><option value="all">{memoryExplorerMessage(language, "allOption")}</option>{memoryKinds.map((kind) => <option key={kind} value={kind}>{kindLabel(language, kind)}</option>)}</select></label>
          <label><span>{memoryExplorerMessage(language, "filterStatus")}</span><select value={draftParams.filters.status} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, filters: { ...current.filters, status: event.target.value as MemoryLifecycleStatus | "all" } }))}><option value="all">{memoryExplorerMessage(language, "allOption")}</option>{statuses.map((status) => <option key={status} value={status}>{statusLabel(language, status)}</option>)}</select></label>
          <label><span>{memoryExplorerMessage(language, "filterSubject")}</span><select value={draftParams.filters.subject} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, filters: { ...current.filters, subject: event.target.value } }))}><option value="all">{memoryExplorerMessage(language, "allOption")}</option>{subjects.map((subject) => <option key={subject} value={subject}>{subject}</option>)}</select></label>
          <label><span>{memoryExplorerMessage(language, "sortLabel")}</span><select value={draftParams.sort} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, sort: event.target.value as SortKey }))}>{sortKeys.map((sort) => <option key={sort} value={sort}>{sortLabel(language, sort)}</option>)}</select></label>
          <label><span>{memoryExplorerMessage(language, "filterDateFrom")}</span><input type="date" value={draftParams.filters.dateFrom} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, filters: { ...current.filters, dateFrom: event.target.value } }))} /></label>
          <label><span>{memoryExplorerMessage(language, "filterDateTo")}</span><input type="date" value={draftParams.filters.dateTo} disabled={isBusy} onChange={(event) => updateDraft((current) => ({ ...current, filters: { ...current.filters, dateTo: event.target.value } }))} /></label>
        </div>
        <div className="memory-explorer-quick-filters">
          <button type="button" aria-pressed={draftParams.filters.recentlyFormed} className={draftParams.filters.recentlyFormed ? "memory-explorer-chip-active" : ""} disabled={isBusy} onClick={() => updateDraft((current) => ({ ...current, filters: { ...current.filters, recentlyFormed: !current.filters.recentlyFormed } }))}>{memoryExplorerMessage(language, "filterRecentlyFormed")}</button>
          <button type="button" aria-pressed={draftParams.filters.recentlyUsed} className={draftParams.filters.recentlyUsed ? "memory-explorer-chip-active" : ""} disabled={isBusy} onClick={() => updateDraft((current) => ({ ...current, filters: { ...current.filters, recentlyUsed: !current.filters.recentlyUsed } }))}>{memoryExplorerMessage(language, "filterRecentlyUsed")}</button>
        </div>
        <div className="memory-explorer-tag-filters">
          <div><span className="memory-explorer-filter-label">{memoryExplorerMessage(language, "filterUserTags")}</span><div className="memory-explorer-chip-row">{userTags.map((tag) => <button type="button" key={tag} aria-pressed={draftParams.filters.userTags.includes(tag)} className={draftParams.filters.userTags.includes(tag) ? "memory-explorer-chip-active" : ""} disabled={isBusy} onClick={() => toggleTagFilter("userTags", tag)}>{tag}</button>)}</div></div>
          <div><span className="memory-explorer-filter-label">{memoryExplorerMessage(language, "filterSystemTags")}</span><div className="memory-explorer-chip-row">{systemTags.map((tag) => <button type="button" key={tag} aria-pressed={draftParams.filters.systemTags.includes(tag)} className={draftParams.filters.systemTags.includes(tag) ? "memory-explorer-chip-active" : ""} disabled={isBusy} onClick={() => toggleTagFilter("systemTags", tag)}>{tag}</button>)}</div></div>
        </div>
      </section>

      {forgetStage === "applied" && <div className="memory-explorer-result" role="status"><span className="mock-pill">{memoryExplorerMessage(language, "forgetAppliedBadge")}</span><p>{memoryExplorerMessage(language, "forgetAppliedBody")}</p></div>}

      <div className="memory-explorer-workspace">
        <section className="memory-explorer-results surface-panel" aria-labelledby="explorer-results-title">
          <div className="section-heading compact-heading"><div><p className="eyebrow">RESULTS</p><h2 id="explorer-results-title">{memoryExplorerMessage(language, "resultsTitle")} · {results.length} {memoryExplorerMessage(language, "resultsCount")}</h2></div></div>
          {searchStatus === "ready" && results.length === 0 && <p className="memory-explorer-empty"><strong>{memoryExplorerMessage(language, "emptyTitle")}</strong><br />{memoryExplorerMessage(language, "emptyBody")}</p>}
          <div className="memory-explorer-record-list">
            {results.map((record) => (
              <button type="button" key={record.memoryId} className={`memory-explorer-record ${selectedMemoryId === record.memoryId ? "memory-explorer-record-selected" : ""}`} aria-pressed={selectedMemoryId === record.memoryId} disabled={isBusy} onClick={() => selectMemory(record.memoryId)}>
                <div className="memory-explorer-record-heading"><strong>{kindLabel(language, record.kind)}</strong><span className={`memory-explorer-status-pill memory-explorer-status-${record.status}`}>{statusLabel(language, record.status)}</span></div>
                <p className="memory-explorer-record-summary">{record.summary}</p>
                <div className="memory-explorer-record-tags">{record.userTags.map((tag) => <span className="memory-explorer-tag-chip memory-explorer-tag-user" key={tag}>{tag}</span>)}{record.systemTags.map((tag) => <span className="memory-explorer-tag-chip memory-explorer-tag-system" key={tag}>{tag}</span>)}</div>
                <div className="memory-explorer-record-meta"><span>{memoryExplorerMessage(language, "formed")}: {record.formedAtLabel}</span><span>{memoryExplorerMessage(language, "latestUse")}: {record.latestUseLabel ?? memoryExplorerMessage(language, "neverUsed")}</span><span>{memoryExplorerMessage(language, "confidence")}: {confidenceLabel(language, record.confidence)}</span><span>{memoryExplorerMessage(language, "provenance")}: {provenanceLabel(language, record.provenanceAvailability)}</span></div>
              </button>
            ))}
          </div>
        </section>

        <section className="memory-explorer-detail surface-panel" aria-labelledby="explorer-detail-title">
          {!selectedRecord ? <p className="memory-explorer-empty">{memoryExplorerMessage(language, "selectPrompt")}</p> : (
            <>
              <div className="section-heading"><div><p className="eyebrow">SELECTED MEMORY</p><h2 id="explorer-detail-title">{kindLabel(language, selectedRecord.kind)}</h2></div><span className={`memory-explorer-status-pill memory-explorer-status-${selectedRecord.status}`}>{statusLabel(language, selectedRecord.status)}</span></div>
              <p className="memory-explorer-content">{selectedRecord.content}</p>
              <dl className="memory-explorer-facts">
                <div><dt>{memoryExplorerMessage(language, "detailId")} <span className="memory-explorer-origin-pill">{memoryExplorerMessage(language, "systemDerived")}</span></dt><dd><code>{selectedRecord.memoryId}</code></dd></div>
                <div><dt>{memoryExplorerMessage(language, "detailSubject")}</dt><dd>{selectedRecord.subject}</dd></div>
                <div><dt>{memoryExplorerMessage(language, "detailFormed")}</dt><dd>{selectedRecord.formedAtLabel}</dd></div>
                <div><dt>{memoryExplorerMessage(language, "detailLatestUse")}</dt><dd>{selectedRecord.latestUseLabel ?? memoryExplorerMessage(language, "neverUsed")}</dd></div>
                <div><dt>{memoryExplorerMessage(language, "detailConfidence")}</dt><dd>{confidenceLabel(language, selectedRecord.confidence)}</dd></div>
                <div><dt>{memoryExplorerMessage(language, "detailProvenanceAvailability")}</dt><dd>{provenanceLabel(language, selectedRecord.provenanceAvailability)}</dd></div>
              </dl>

              <div className="memory-explorer-tags-section">
                <div className="section-heading compact-heading"><div><h3>{copy(language, "記憶の訂正", "Correct memory")}</h3><p className="panel-description">{copy(language, "summaryと本文をブラウザ内だけで訂正します。", "Correct the summary and content in browser-local state only.")}</p></div>{!correctionOpen && <button className="button button-secondary" type="button" disabled={isBusy} onClick={openCorrection}>{copy(language, "訂正する", "Correct")}</button>}</div>
                {correctionOpen && <div className="memory-explorer-tag-group"><label><span>{copy(language, "要約", "Summary")}</span><input type="text" value={correctionSummary} disabled={isBusy} onChange={(event) => setCorrectionSummary(event.target.value)} /></label><label><span>{copy(language, "本文", "Content")}</span><textarea value={correctionContent} disabled={isBusy} onChange={(event) => setCorrectionContent(event.target.value)} /></label><div className="memory-explorer-preview-actions"><button className="button button-secondary" type="button" disabled={isBusy} onClick={() => setCorrectionOpen(false)}>{memoryExplorerMessage(language, "cancelTagButton")}</button><button className="button button-primary" type="button" disabled={isBusy || !correctionSummary.trim() || !correctionContent.trim()} onClick={saveCorrection}>{memoryExplorerMessage(language, "saveTagButton")}</button></div></div>}
              </div>

              <div className="memory-explorer-tags-section">
                <h3>{memoryExplorerMessage(language, "tagsTitle")}</h3>
                <div className="memory-explorer-tag-group">
                  <span className="memory-explorer-filter-label">{memoryExplorerMessage(language, "userTagsLabel")} <span className="memory-explorer-origin-pill">{memoryExplorerMessage(language, "userManaged")}</span></span>
                  <div className="memory-explorer-chip-row">
                    {selectedRecord.userTags.map((tag) => renamingTag === tag ? <span className="memory-explorer-tag-edit-row" key={tag}><input type="text" value={renameDraft} disabled={isBusy} onChange={(event) => setRenameDraft(event.target.value)} /><button className="button button-secondary" type="button" disabled={isBusy} onClick={() => applyTagOperation("rename", (record) => renameUserTag(record, tag, renameDraft), tag)}>{memoryExplorerMessage(language, "saveTagButton")}</button><button className="button button-secondary" type="button" disabled={isBusy} onClick={() => setRenamingTag(null)}>{memoryExplorerMessage(language, "cancelTagButton")}</button></span> : <span className="memory-explorer-tag-chip memory-explorer-tag-user memory-explorer-tag-editable" key={tag}>{tag}<button type="button" aria-label={memoryExplorerMessage(language, "renameTagButton")} disabled={isBusy} onClick={() => { setRenamingTag(tag); setRenameDraft(tag); }}>✎</button><button type="button" aria-label={memoryExplorerMessage(language, "removeTagButton")} disabled={isBusy} onClick={() => applyTagOperation("remove", (record) => removeUserTag(record, tag), tag)}>×</button></span>)}
                  </div>
                  <div className="memory-explorer-add-tag-row"><input type="text" value={newTagDraft} placeholder={memoryExplorerMessage(language, "addTagPlaceholder")} disabled={isBusy} onChange={(event) => setNewTagDraft(event.target.value)} /><button className="button button-secondary" type="button" disabled={isBusy || !newTagDraft.trim()} onClick={() => applyTagOperation("add", (record) => addUserTag(record, newTagDraft))}>{memoryExplorerMessage(language, "addTagButton")}</button></div>
                  {tagOperation?.state === "pending" && <p className="memory-explorer-tag-status">{memoryExplorerMessage(language, "tagEditPending")}</p>}
                  {tagOperation?.state === "applied" && <p className="memory-explorer-tag-status memory-explorer-tag-applied" role="status"><span className="mock-pill">{memoryExplorerMessage(language, "tagEditApplied")}</span></p>}
                  {tagOperation?.state === "failed" && tagOperation.error && <p className="memory-explorer-tag-status memory-explorer-tag-failed" role="alert">{memoryExplorerMessage(language, "tagEditFailed")}: {tagErrorLabel(language, tagOperation.error)}</p>}
                </div>
                <div className="memory-explorer-tag-group"><span className="memory-explorer-filter-label">{memoryExplorerMessage(language, "systemTagsLabel")} <span className="memory-explorer-origin-pill">{memoryExplorerMessage(language, "systemDerived")}</span></span><div className="memory-explorer-chip-row">{selectedRecord.systemTags.map((tag) => <span className="memory-explorer-tag-chip memory-explorer-tag-system" key={tag}>{tag}</span>)}</div></div>
              </div>

              <div className="memory-explorer-provenance"><h3>{memoryExplorerMessage(language, "provenanceTitle")}</h3><p>{memoryExplorerMessage(language, "provenanceDescription")}</p><ol>{selectedRecord.provenance.map((step) => <li key={step.stepId}><span aria-hidden="true" /><div><strong>{step.label}</strong><small>{step.detail}</small></div></li>)}</ol></div>
              <div className="memory-explorer-related"><h3>{memoryExplorerMessage(language, "relatedTitle")}</h3><p>{memoryExplorerMessage(language, "relatedDescription")}</p>{relatedGroups.length === 0 ? <p className="memory-explorer-empty">{memoryExplorerMessage(language, "relatedEmpty")}</p> : relatedGroups.map((group) => <div className="memory-explorer-related-group" key={group.subject}><p className="memory-explorer-related-heading">{memoryExplorerMessage(language, "relatedGroupBySubject")} {group.subject}</p><ul className="memory-explorer-related-list">{group.records.map((record) => <li key={record.memoryId}><button type="button" disabled={isBusy} onClick={() => selectMemory(record.memoryId)}><strong>{kindLabel(language, record.kind)}</strong><span>{record.summary}</span></button></li>)}</ul></div>)}</div>
              <div className="memory-explorer-usage-timeline"><h3>{memoryExplorerMessage(language, "usageTimelineTitle")}</h3><p>{memoryExplorerMessage(language, "usageTimelineDescription")}</p><ul className="memory-explorer-usage-list">{selectedRecord.usageTimeline.map((event) => <li key={event.eventId}><time>{event.occurredAtLabel}</time><span>{event.detail}</span></li>)}</ul></div>

              <div className="memory-explorer-lifecycle">
                <h3>{memoryExplorerMessage(language, "lifecycleTitle")}</h3>
                <p>{memoryExplorerMessage(language, selectedRecord.status === "active" ? "lifecycleActiveNote" : "lifecycleHiddenNote")}</p>
                {selectedRecord.tombstoned && <p className="memory-explorer-tombstone-note">{memoryExplorerMessage(language, "tombstoneNote")}</p>}
                <div className="memory-explorer-lifecycle-actions">
                  {selectedRecord.status === "active" && forgetStage === "idle" && <button className="button memory-explorer-danger-button" type="button" disabled={isBusy} onClick={() => { setForgetStage("confirming"); onExplorerLockChange(true); }}>{memoryExplorerMessage(language, "forgetButton")}</button>}
                  {selectedRecord.status === "hidden" && <button className="button button-secondary" type="button" disabled={isBusy} onClick={restoreSelected}>{memoryExplorerMessage(language, "restoreButton")}</button>}
                  <button
                    className="button button-secondary"
                    type="button"
                    disabled
                    title={memoryExplorerMessage(language, "purgeUnavailableNote")}
                    aria-disabled="true"
                  >
                    {memoryExplorerMessage(language, "purgeButton")}
                  </button>
                </div>
                <p className="memory-explorer-boundary-note">{memoryExplorerMessage(language, "purgeUnavailableNote")}</p>
                {(forgetStage === "confirming" || forgetStage === "pending") && <div className="memory-explorer-forget-confirm" role="dialog" aria-modal="false"><p className="eyebrow">DESTRUCTIVE CONFIRMATION</p><h4>{memoryExplorerMessage(language, "forgetConfirmTitle")}</h4><p>{memoryExplorerMessage(language, "forgetConfirmBody")}</p><p className="memory-explorer-forget-warning">{memoryExplorerMessage(language, "forgetConfirmWarning")}</p><div className="memory-explorer-preview-actions"><button className="button button-secondary" type="button" disabled={forgetStage === "pending"} onClick={() => { setForgetStage("idle"); onExplorerLockChange(false); }}>{memoryExplorerMessage(language, "forgetCancelButton")}</button><button className="button memory-explorer-danger-button" type="button" disabled={forgetStage === "pending"} onClick={confirmForget}>{memoryExplorerMessage(language, "forgetConfirmButton")}</button></div></div>}
              </div>
            </>
          )}
        </section>
      </div>

      <section className="surface-panel memory-explorer-timeline" aria-labelledby="explorer-events-title">
        <div className="section-heading compact-heading"><div><p className="eyebrow">CONTENT-FREE EVENTS</p><h2 id="explorer-events-title">{memoryExplorerMessage(language, "eventsTitle")}</h2></div></div>
        <p className="panel-description">{memoryExplorerMessage(language, "eventsDescription")}</p>
        <div className="memory-explorer-event-list" aria-live="polite">{events.length === 0 && <p className="memory-explorer-empty">{memoryExplorerMessage(language, "eventsEmpty")}</p>}{events.map((event) => <article className={`memory-explorer-event memory-explorer-event-${event.level}`} key={event.eventId}><span aria-hidden="true" /><div><strong>{event.label}</strong><code>{event.metadata}</code><time>{event.occurredAtLabel}</time></div></article>)}</div>
      </section>
    </div>
  );
}
