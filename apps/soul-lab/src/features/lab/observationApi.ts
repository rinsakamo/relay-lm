export type ObservationAvailability = "available" | "empty" | "unavailable";

export interface LabLastRunProjection {
  schema: "relaylm.lab.last_run.v0";
  source: "relaylm_runtime";
  read_only: true;
  availability: ObservationAvailability;
  capability: "latest_completed_managed_run";
  character_id: string;
  namespace: string;
  run_id: string | null;
  status: "completed" | "failed" | "empty" | "unavailable";
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  response_mode: "stream" | "non_stream" | "unknown";
  slp_status: string;
  memory_outcome_status: "formed" | "held" | "blocked" | "mixed" | "none" | "unavailable";
  relayrun_status: string;
  relayctx_repack_status: string;
  relayctx_unpack_status: string;
  formed_count: number;
  held_count: number;
  blocked_count: number;
  used_memory_count: number;
  recovery_required: boolean;
  bounded_reason_ids: string[];
}

export interface LabRecentMemoryItem {
  memory_id: string;
  layer: "primary";
  status: "formed";
  title: string;
  bounded_summary: string;
  confidence_label: "not_recorded";
  scope_label: "character_namespace";
  formed_at: string | null;
  pinned: boolean;
  source_kind: string;
}

export interface LabRecentMemoryProjection {
  schema: "relaylm.lab.memory_recent.v0";
  source: "relaylm_runtime";
  read_only: true;
  availability: ObservationAvailability;
  capability: "validated_primary_memory_read";
  character_id: string;
  namespace: string;
  limit: number;
  next_cursor: string | null;
  items: LabRecentMemoryItem[];
  bounded_reason_ids: string[];
}

export interface LabMemoryOutcomeItem {
  outcome_id: string;
  run_id: string;
  status: "held" | "blocked";
  title: string;
  bounded_summary: string;
  observed_at: string;
  reason_ids: string[];
}

export interface LabMemoryHeldProjection {
  schema: "relaylm.lab.memory_held.v0";
  source: "relaylm_runtime";
  read_only: true;
  availability: ObservationAvailability;
  capability: "durable_memory_outcome_read";
  character_id: string;
  namespace: string;
  limit: number;
  next_cursor: string | null;
  items: LabMemoryOutcomeItem[];
  bounded_reason_ids: string[];
}

export interface LabUsedMemoryItem {
  memory_id: string;
  injected_summary: string;
  current_summary: string | null;
  representation_changed: boolean;
  source_kind: string;
}

export interface LabMemoryUsedProjection {
  schema: "relaylm.lab.memory_used.v0";
  source: "relaylm_runtime";
  read_only: true;
  availability: ObservationAvailability;
  capability: "backend_bound_memory_evidence_read";
  character_id: string;
  namespace: string;
  run_id: string | null;
  retrieval_attempted: boolean;
  candidate_discovered: boolean;
  selected: boolean;
  relayctx_injection_performed: boolean;
  backend_bound_included: boolean;
  response_generation_completed: boolean;
  items: LabUsedMemoryItem[];
  bounded_reason_ids: string[];
}

export interface LabObservationBundle {
  latestRun: LabLastRunProjection;
  recent: LabRecentMemoryProjection;
  held: LabMemoryHeldProjection;
  used: LabMemoryUsedProjection;
}

export class LabObservationError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "LabObservationError";
  }
}

const availabilityValues = ["available", "empty", "unavailable"] as const;
const lastRunKeys = [
  "schema", "source", "read_only", "availability", "capability", "character_id",
  "namespace", "run_id", "status", "started_at", "completed_at", "duration_ms",
  "response_mode", "slp_status", "memory_outcome_status", "relayrun_status",
  "relayctx_repack_status", "relayctx_unpack_status", "formed_count", "held_count",
  "blocked_count", "used_memory_count", "recovery_required", "bounded_reason_ids",
] as const;
const recentKeys = [
  "schema", "source", "read_only", "availability", "capability", "character_id",
  "namespace", "limit", "next_cursor", "items", "bounded_reason_ids",
] as const;
const recentItemKeys = [
  "memory_id", "layer", "status", "title", "bounded_summary", "confidence_label",
  "scope_label", "formed_at", "pinned", "source_kind",
] as const;
const heldKeys = recentKeys;
const heldItemKeys = [
  "outcome_id", "run_id", "status", "title", "bounded_summary", "observed_at", "reason_ids",
] as const;
const usedKeys = [
  "schema", "source", "read_only", "availability", "capability", "character_id",
  "namespace", "run_id", "retrieval_attempted", "candidate_discovered", "selected",
  "relayctx_injection_performed", "backend_bound_included", "response_generation_completed",
  "items", "bounded_reason_ids",
] as const;
const usedItemKeys = [
  "memory_id", "injected_summary", "current_summary", "representation_changed", "source_kind",
] as const;

export async function loadLabObservation(
  characterId: string,
  namespace: string,
  signal?: AbortSignal,
): Promise<LabObservationBundle> {
  const character = encodeURIComponent(characterId);
  const query = `namespace=${encodeURIComponent(namespace)}`;
  const [lastRunValue, recentValue, heldValue, usedValue] = await Promise.all([
    fetchJson(`/lab/api/characters/${character}/lab/last-run?${query}`, signal),
    fetchJson(`/lab/api/characters/${character}/memory/recent?${query}&limit=20`, signal),
    fetchJson(`/lab/api/characters/${character}/memory/held?${query}&limit=20`, signal),
    fetchJson(`/lab/api/characters/${character}/lab/last-run/memory/used?${query}`, signal),
  ]);
  const latestRun = parseLastRun(lastRunValue, characterId, namespace);
  const recent = parseRecent(recentValue, characterId, namespace);
  const held = parseHeld(heldValue, characterId, namespace);
  const used = parseUsed(usedValue, characterId, namespace);
  if (!latestRun || !recent || !held || !used) {
    throw new LabObservationError("invalid_lab_observation_schema");
  }
  if (used.run_id !== null && latestRun.run_id !== null && used.run_id !== latestRun.run_id) {
    throw new LabObservationError("mixed_lab_observation_run");
  }
  return { latestRun, recent, held, used };
}

async function fetchJson(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });
  if (!response.ok) {
    throw new LabObservationError(
      response.status === 403 ? "lab_observation_access_refused" : `lab_observation_http_${response.status}`,
    );
  }
  return response.json() as Promise<unknown>;
}

function parseLastRun(value: unknown, characterId: string, namespace: string): LabLastRunProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, lastRunKeys)) return null;
  if (
    value.schema !== "relaylm.lab.last_run.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || !isAvailability(value.availability) ||
    value.capability !== "latest_completed_managed_run" || value.character_id !== characterId ||
    value.namespace !== namespace || !isNullableString(value.run_id) ||
    !["completed", "failed", "empty", "unavailable"].includes(String(value.status)) ||
    !isNullableString(value.started_at) || !isNullableString(value.completed_at) ||
    !(value.duration_ms === null || isNonNegativeInteger(value.duration_ms)) ||
    !["stream", "non_stream", "unknown"].includes(String(value.response_mode)) ||
    typeof value.slp_status !== "string" ||
    !["formed", "held", "blocked", "mixed", "none", "unavailable"].includes(String(value.memory_outcome_status)) ||
    typeof value.relayrun_status !== "string" || typeof value.relayctx_repack_status !== "string" ||
    typeof value.relayctx_unpack_status !== "string" || !isNonNegativeInteger(value.formed_count) ||
    !isNonNegativeInteger(value.held_count) || !isNonNegativeInteger(value.blocked_count) ||
    !isNonNegativeInteger(value.used_memory_count) || typeof value.recovery_required !== "boolean" ||
    !isReasonIds(value.bounded_reason_ids)
  ) return null;
  return value as unknown as LabLastRunProjection;
}

function parseRecent(value: unknown, characterId: string, namespace: string): LabRecentMemoryProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, recentKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_recent.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || !isAvailability(value.availability) ||
    value.capability !== "validated_primary_memory_read" || value.character_id !== characterId ||
    value.namespace !== namespace || !isBoundedLimit(value.limit) || value.next_cursor !== null ||
    !Array.isArray(value.items) || value.items.length > value.limit || !isReasonIds(value.bounded_reason_ids)
  ) return null;
  const items = value.items.map(parseRecentItem);
  if (items.some((item) => item === null)) return null;
  return { ...value, items: items as LabRecentMemoryItem[] } as LabRecentMemoryProjection;
}

function parseRecentItem(value: unknown): LabRecentMemoryItem | null {
  if (!isRecord(value) || !hasExactKeys(value, recentItemKeys)) return null;
  if (
    !isOpaqueId(value.memory_id) || value.layer !== "primary" || value.status !== "formed" ||
    !isSafeText(value.title, 160) || !isSafeText(value.bounded_summary, 512) ||
    value.confidence_label !== "not_recorded" || value.scope_label !== "character_namespace" ||
    !isNullableString(value.formed_at) || typeof value.pinned !== "boolean" ||
    typeof value.source_kind !== "string"
  ) return null;
  return value as unknown as LabRecentMemoryItem;
}

function parseHeld(value: unknown, characterId: string, namespace: string): LabMemoryHeldProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, heldKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_held.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || !isAvailability(value.availability) ||
    value.capability !== "durable_memory_outcome_read" || value.character_id !== characterId ||
    value.namespace !== namespace || !isBoundedLimit(value.limit) || value.next_cursor !== null ||
    !Array.isArray(value.items) || value.items.length > value.limit || !isReasonIds(value.bounded_reason_ids)
  ) return null;
  const items = value.items.map(parseHeldItem);
  if (items.some((item) => item === null)) return null;
  return { ...value, items: items as LabMemoryOutcomeItem[] } as LabMemoryHeldProjection;
}

function parseHeldItem(value: unknown): LabMemoryOutcomeItem | null {
  if (!isRecord(value) || !hasExactKeys(value, heldItemKeys)) return null;
  if (
    !isOpaqueId(value.outcome_id) || typeof value.run_id !== "string" ||
    (value.status !== "held" && value.status !== "blocked") || !isSafeText(value.title, 160) ||
    !isSafeText(value.bounded_summary, 512) || typeof value.observed_at !== "string" ||
    !isReasonIds(value.reason_ids)
  ) return null;
  return value as unknown as LabMemoryOutcomeItem;
}

function parseUsed(value: unknown, characterId: string, namespace: string): LabMemoryUsedProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, usedKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_used.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || !isAvailability(value.availability) ||
    value.capability !== "backend_bound_memory_evidence_read" || value.character_id !== characterId ||
    value.namespace !== namespace || !isNullableString(value.run_id) ||
    typeof value.retrieval_attempted !== "boolean" || typeof value.candidate_discovered !== "boolean" ||
    typeof value.selected !== "boolean" || typeof value.relayctx_injection_performed !== "boolean" ||
    typeof value.backend_bound_included !== "boolean" || typeof value.response_generation_completed !== "boolean" ||
    !Array.isArray(value.items) || value.items.length > 16 || !isReasonIds(value.bounded_reason_ids)
  ) return null;
  const items = value.items.map(parseUsedItem);
  if (items.some((item) => item === null)) return null;
  if (items.length > 0 && (!value.backend_bound_included || !value.relayctx_injection_performed)) return null;
  return { ...value, items: items as LabUsedMemoryItem[] } as LabMemoryUsedProjection;
}

function parseUsedItem(value: unknown): LabUsedMemoryItem | null {
  if (!isRecord(value) || !hasExactKeys(value, usedItemKeys)) return null;
  if (
    !isOpaqueId(value.memory_id) || !isSafeText(value.injected_summary, 512) ||
    !(value.current_summary === null || isSafeText(value.current_summary, 512)) ||
    typeof value.representation_changed !== "boolean" || typeof value.source_kind !== "string"
  ) return null;
  return value as unknown as LabUsedMemoryItem;
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => actual.includes(key));
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function isAvailability(value: unknown): value is ObservationAvailability {
  return availabilityValues.includes(value as ObservationAvailability);
}
function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}
function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}
function isBoundedLimit(value: unknown): value is number {
  return isNonNegativeInteger(value) && value >= 1 && value <= 50;
}
function isOpaqueId(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}
function isReasonIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 32 && value.every(
    (item) => typeof item === "string" && /^[a-z0-9][a-z0-9_:-]{0,127}$/.test(item),
  );
}
function isSafeText(value: unknown, maximum: number): value is string {
  return typeof value === "string" && Array.from(value).length <= maximum &&
    !/[\u0000-\u001f\u007f\u2028\u2029]/u.test(value);
}
