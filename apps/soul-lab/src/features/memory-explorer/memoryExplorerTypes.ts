export type MemoryKind = "episodic" | "preference" | "relationship" | "procedural" | "boundary";
export type MemoryLifecycleStatus = "active" | "hidden";
export type ConfidenceBucket = "high" | "medium" | "low";
export type ProvenanceAvailability = "available" | "partial" | "unavailable";
export type SearchMode = "keyword" | "semantic" | "hybrid";
export type SortKey = "relevance" | "recentlyFormed" | "recentlyUsed";
export type SearchStatus = "idle" | "loading" | "ready" | "error";
export type TagEditState = "idle" | "editing" | "pending" | "applied" | "failed";
export type ForgetStage = "idle" | "confirming" | "pending" | "applied";

export interface MemoryUsageEvent {
  eventId: string;
  occurredAtLabel: string;
  occurredAtValue: string;
  detail: string;
}

export interface MemoryProvenanceStep {
  stepId: string;
  label: string;
  detail: string;
}

export interface MemoryExplorerRecord {
  memoryId: string;
  characterId: string;
  summary: string;
  content: string;
  kind: MemoryKind;
  userTags: string[];
  systemTags: string[];
  subject: string;
  formedAtLabel: string;
  formedAtValue: string;
  latestUseLabel: string | null;
  latestUseValue: string | null;
  confidence: ConfidenceBucket;
  provenanceAvailability: ProvenanceAvailability;
  status: MemoryLifecycleStatus;
  relatedMemoryIds: string[];
  provenance: MemoryProvenanceStep[];
  usageTimeline: MemoryUsageEvent[];
  pinned: boolean;
  tombstoned: boolean;
  tombstoneAtLabel: string | null;
}

export interface MemoryExplorerFilters {
  userTags: string[];
  systemTags: string[];
  kind: MemoryKind | "all";
  status: MemoryLifecycleStatus | "all";
  subject: string | "all";
  dateFrom: string;
  dateTo: string;
  recentlyFormed: boolean;
  recentlyUsed: boolean;
}

export interface MemoryExplorerSearchParams {
  query: string;
  mode: SearchMode;
  sort: SortKey;
  filters: MemoryExplorerFilters;
}

export type PlanStep =
  | { kind: "mode"; mode: SearchMode }
  | { kind: "queryTerms"; terms: string[] }
  | { kind: "userTags"; tags: string[] }
  | { kind: "systemTags"; tags: string[] }
  | { kind: "memoryKind"; value: MemoryKind }
  | { kind: "status"; value: MemoryLifecycleStatus }
  | { kind: "subject"; value: string }
  | { kind: "dateRange"; from: string; to: string }
  | { kind: "recentlyFormed" }
  | { kind: "recentlyUsed" }
  | { kind: "sort"; value: SortKey };

export function defaultFilters(): MemoryExplorerFilters {
  return {
    userTags: [],
    systemTags: [],
    kind: "all",
    status: "active",
    subject: "all",
    dateFrom: "",
    dateTo: "",
    recentlyFormed: false,
    recentlyUsed: false,
  };
}

export function defaultSearchParams(): MemoryExplorerSearchParams {
  return {
    query: "",
    mode: "hybrid",
    sort: "recentlyFormed",
    filters: defaultFilters(),
  };
}
