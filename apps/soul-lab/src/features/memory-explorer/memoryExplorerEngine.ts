import type {
  MemoryExplorerFilters,
  MemoryExplorerRecord,
  MemoryExplorerSearchParams,
  MemoryLifecycleStatus,
  PlanStep,
  TagEditState,
} from "./memoryExplorerTypes";

export const RECENTLY_FORMED_WINDOW_MS = 1000 * 60 * 60 * 24 * 3;
export const RECENTLY_USED_WINDOW_MS = 1000 * 60 * 60 * 24 * 3;
export const FORCE_ERROR_QUERY = "force-error";

export function isTagOperationBusy(state: TagEditState | undefined): boolean {
  return state === "pending" || state === "applied";
}

export function tokenize(query: string): string[] {
  return query
    .trim()
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

export function shouldSimulateError(query: string): boolean {
  return query.trim().toLowerCase() === FORCE_ERROR_QUERY;
}

const SEMANTIC_ALIASES: Record<string, string[]> = {
  "ありがとう": ["感謝"],
  "感謝": ["ありがとう"],
  "theme": ["テーマ", "ダーク", "ui テーマ"],
  "テーマ": ["theme", "ダーク", "ui テーマ"],
  "travel": ["旅行", "思い出"],
  "旅行": ["travel", "思い出"],
  "relationship": ["関係性", "relationship_continuity", "感謝"],
  "関係性": ["relationship", "relationship_continuity", "感謝"],
  "forget": ["hidden", "境界", "削除"],
  "削除": ["forget", "hidden", "境界"],
};

function keywordHaystackFor(record: MemoryExplorerRecord): string {
  return [record.summary, record.content, record.subject, ...record.userTags, ...record.systemTags]
    .join(" ")
    .toLowerCase();
}

function semanticHaystackFor(record: MemoryExplorerRecord): string {
  return [record.summary, record.subject, record.kind, ...record.userTags, ...record.systemTags]
    .join(" ")
    .toLowerCase();
}

function expandedSemanticTerms(tokens: string[]): string[] {
  return Array.from(
    new Set(
      tokens.flatMap((token) => {
        const normalized = token.toLowerCase();
        return [normalized, ...(SEMANTIC_ALIASES[normalized] ?? [])].map((term) => term.toLowerCase());
      }),
    ),
  );
}

function matchCount(haystack: string, terms: string[]): number {
  return terms.reduce((count, term) => count + (haystack.includes(term) ? 1 : 0), 0);
}

function relevanceScore(
  record: MemoryExplorerRecord,
  tokens: string[],
  mode: MemoryExplorerSearchParams["mode"],
): number {
  if (tokens.length === 0) return 0;
  const keywordTerms = tokens.map((token) => token.toLowerCase());
  const semanticTerms = expandedSemanticTerms(tokens);
  const keywordScore = matchCount(keywordHaystackFor(record), keywordTerms);
  const semanticScore = matchCount(semanticHaystackFor(record), semanticTerms);
  const subjectBonus = keywordTerms.includes(record.subject.toLowerCase()) ? 0.5 : 0;
  if (mode === "keyword") return keywordScore + subjectBonus;
  if (mode === "semantic") return semanticScore + subjectBonus;
  return keywordScore + semanticScore * 0.75 + subjectBonus;
}

function passesQuery(
  record: MemoryExplorerRecord,
  tokens: string[],
  mode: MemoryExplorerSearchParams["mode"],
): boolean {
  if (tokens.length === 0) return true;
  const keywordMatched = matchCount(keywordHaystackFor(record), tokens.map((token) => token.toLowerCase())) > 0;
  const semanticMatched = matchCount(semanticHaystackFor(record), expandedSemanticTerms(tokens)) > 0;
  if (mode === "keyword") return keywordMatched;
  if (mode === "semantic") return semanticMatched;
  return keywordMatched || semanticMatched;
}

function withinDateRange(record: MemoryExplorerRecord, filters: MemoryExplorerFilters): boolean {
  const formedDate = record.formedAtValue.slice(0, 10);
  if (filters.dateFrom && formedDate < filters.dateFrom) return false;
  if (filters.dateTo && formedDate > filters.dateTo) return false;
  return true;
}

export function isRecentlyFormed(record: MemoryExplorerRecord, now: number): boolean {
  return now - new Date(record.formedAtValue).getTime() <= RECENTLY_FORMED_WINDOW_MS;
}

export function isRecentlyUsed(record: MemoryExplorerRecord, now: number): boolean {
  if (!record.latestUseValue) return false;
  return now - new Date(record.latestUseValue).getTime() <= RECENTLY_USED_WINDOW_MS;
}

export function distinctSubjects(records: MemoryExplorerRecord[]): string[] {
  return Array.from(new Set(records.map((record) => record.subject))).sort();
}

export function distinctUserTags(records: MemoryExplorerRecord[]): string[] {
  return Array.from(new Set(records.flatMap((record) => record.userTags))).sort();
}

export function distinctSystemTags(records: MemoryExplorerRecord[]): string[] {
  return Array.from(new Set(records.flatMap((record) => record.systemTags))).sort();
}

export function runMemoryExplorerSearch(
  records: MemoryExplorerRecord[],
  params: MemoryExplorerSearchParams,
  now: number = Date.now(),
): MemoryExplorerRecord[] {
  const tokens = tokenize(params.query);
  const { filters } = params;

  const filtered = records.filter((record) => {
    if (filters.status !== "all" && record.status !== filters.status) return false;
    if (filters.kind !== "all" && record.kind !== filters.kind) return false;
    if (filters.subject !== "all" && record.subject !== filters.subject) return false;
    if (filters.userTags.length > 0 && !filters.userTags.every((tag) => record.userTags.includes(tag))) return false;
    if (filters.systemTags.length > 0 && !filters.systemTags.every((tag) => record.systemTags.includes(tag))) return false;
    if (!withinDateRange(record, filters)) return false;
    if (filters.recentlyFormed && !isRecentlyFormed(record, now)) return false;
    if (filters.recentlyUsed && !isRecentlyUsed(record, now)) return false;
    if (!passesQuery(record, tokens, params.mode)) return false;
    return true;
  });

  const sorted = [...filtered];
  if (params.sort === "relevance" && tokens.length > 0) {
    sorted.sort((a, b) => relevanceScore(b, tokens, params.mode) - relevanceScore(a, tokens, params.mode) || b.formedAtValue.localeCompare(a.formedAtValue));
  } else if (params.sort === "recentlyUsed") {
    sorted.sort((a, b) => (b.latestUseValue ?? "").localeCompare(a.latestUseValue ?? ""));
  } else {
    sorted.sort((a, b) => b.formedAtValue.localeCompare(a.formedAtValue));
  }
  return sorted;
}

export function buildSearchPlan(params: MemoryExplorerSearchParams): PlanStep[] {
  const steps: PlanStep[] = [{ kind: "mode", mode: params.mode }];
  const tokens = tokenize(params.query);
  if (tokens.length > 0) steps.push({ kind: "queryTerms", terms: tokens });
  if (params.filters.userTags.length > 0) steps.push({ kind: "userTags", tags: params.filters.userTags });
  if (params.filters.systemTags.length > 0) steps.push({ kind: "systemTags", tags: params.filters.systemTags });
  if (params.filters.kind !== "all") steps.push({ kind: "memoryKind", value: params.filters.kind });
  if (params.filters.status !== "all") steps.push({ kind: "status", value: params.filters.status });
  if (params.filters.subject !== "all") steps.push({ kind: "subject", value: params.filters.subject });
  if (params.filters.dateFrom || params.filters.dateTo) {
    steps.push({ kind: "dateRange", from: params.filters.dateFrom, to: params.filters.dateTo });
  }
  if (params.filters.recentlyFormed) steps.push({ kind: "recentlyFormed" });
  if (params.filters.recentlyUsed) steps.push({ kind: "recentlyUsed" });
  steps.push({ kind: "sort", value: params.sort });
  return steps;
}

export type TagValidationError = "empty" | "tooLong" | "duplicate" | "collidesWithSystemTag";

export function validateUserTagName(
  rawName: string,
  existingUserTags: string[],
  systemTags: string[],
  ignoreCurrentName?: string,
): TagValidationError | null {
  const trimmed = rawName.trim();
  if (trimmed.length === 0) return "empty";
  if (Array.from(trimmed).length > 32) return "tooLong";
  if (systemTags.some((tag) => tag.toLowerCase() === trimmed.toLowerCase())) return "collidesWithSystemTag";
  if (
    existingUserTags.some(
      (tag) => tag.toLowerCase() === trimmed.toLowerCase() && tag.toLowerCase() !== ignoreCurrentName?.toLowerCase(),
    )
  ) {
    return "duplicate";
  }
  return null;
}

export interface TagEditOutcome {
  ok: boolean;
  tags: string[];
  error: TagValidationError | null;
}

export function addUserTag(record: MemoryExplorerRecord, rawName: string): TagEditOutcome {
  const error = validateUserTagName(rawName, record.userTags, record.systemTags);
  if (error) return { ok: false, tags: record.userTags, error };
  return { ok: true, tags: [...record.userTags, rawName.trim()], error: null };
}

export function renameUserTag(record: MemoryExplorerRecord, oldName: string, rawNewName: string): TagEditOutcome {
  const error = validateUserTagName(rawNewName, record.userTags, record.systemTags, oldName);
  if (error) return { ok: false, tags: record.userTags, error };
  return {
    ok: true,
    tags: record.userTags.map((tag) => (tag === oldName ? rawNewName.trim() : tag)),
    error: null,
  };
}

export function removeUserTag(record: MemoryExplorerRecord, name: string): TagEditOutcome {
  return { ok: true, tags: record.userTags.filter((tag) => tag !== name), error: null };
}

export function applyForgetToRecords(
  records: MemoryExplorerRecord[],
  memoryId: string,
  tombstoneAtLabel: string,
): MemoryExplorerRecord[] {
  return records.map((record) =>
    record.memoryId === memoryId
      ? { ...record, status: "hidden" as MemoryLifecycleStatus, tombstoned: true, tombstoneAtLabel }
      : record,
  );
}

export function restoreFromHidden(records: MemoryExplorerRecord[], memoryId: string): MemoryExplorerRecord[] {
  return records.map((record) =>
    record.memoryId === memoryId
      ? { ...record, status: "active" as MemoryLifecycleStatus, tombstoned: false, tombstoneAtLabel: null }
      : record,
  );
}

export function relatedRecordsFor(
  records: MemoryExplorerRecord[],
  record: MemoryExplorerRecord,
): MemoryExplorerRecord[] {
  return record.relatedMemoryIds
    .map((memoryId) => records.find((candidate) => candidate.memoryId === memoryId))
    .filter((candidate): candidate is MemoryExplorerRecord => candidate !== undefined && candidate.status !== "hidden");
}

export function groupRelatedBySubject(
  related: MemoryExplorerRecord[],
): Array<{ subject: string; records: MemoryExplorerRecord[] }> {
  const groups = new Map<string, MemoryExplorerRecord[]>();
  for (const record of related) {
    const list = groups.get(record.subject) ?? [];
    list.push(record);
    groups.set(record.subject, list);
  }
  return Array.from(groups.entries()).map(([subject, groupRecords]) => ({ subject, records: groupRecords }));
}
