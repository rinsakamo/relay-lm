export type LifecycleAvailability = "available" | "empty" | "unavailable" | "not_connected";
export type LifecycleState = "active" | "hidden" | "prepared" | "recovery_required" | "corrupt" | "unknown";
export type DurableFinalizationStatus = "pending" | "complete" | "isolated" | "mixed" | "none" | "unknown" | "unavailable" | "not_connected";
export type QueueWorkerStatus = "queued" | "processing" | "formed" | "held" | "blocked" | "failed" | "mixed" | "none" | "unknown" | "unavailable" | "not_connected";

export interface LabLifecycleMemoryItem {
  memory_id: string;
  current_lifecycle_state: LifecycleState;
  current_revision: number | null;
  current_physical_status: "current" | "hidden" | "prepared" | "recovery_required" | "corrupt" | "unknown";
  retrieval_eligible: boolean | null;
  historical_used_memory_remains_unchanged: true;
  bounded_reason_ids: string[];
}

export interface LabDurableFinalizationVisibility {
  availability: LifecycleAvailability;
  status: DurableFinalizationStatus;
  pending_count: number;
  complete_count: number;
  isolated_count: number;
  content_free: true;
  locator_values_included: false;
  path_values_included: false;
  bounded_reason_ids: string[];
}

export interface LabQueueWorkerVisibility {
  availability: LifecycleAvailability;
  status: QueueWorkerStatus;
  queued_count: number;
  processing_count: number;
  formed_count: number;
  held_count: number;
  blocked_count: number;
  failed_count: number;
  content_free: true;
  queue_identifiers_included: false;
  claim_values_included: false;
  scheduler_controls_exposed: false;
  worker_controls_exposed: false;
  bounded_reason_ids: string[];
}

export interface LabFreshConversationVisibility {
  browser_local_session_reset_visible: true;
  durable_memory_store_reset: false;
  durable_memory_store_retained: true;
  active_current_memories_remain_retrieval_eligible: true;
  hidden_or_current_ineligible_memories_remain_excluded: true;
  home_transcript_is_durable_source: false;
  durable_transcript_persistence: false;
}

export interface LabLifecycleVisibilityProjection {
  schema: "relaylm.lab.lifecycle_visibility.v0";
  source: "relaylm_runtime";
  read_only: true;
  availability: LifecycleAvailability;
  capability: "read_only_lifecycle_and_operation_visibility";
  character_id: string;
  namespace: string;
  memory_items: LabLifecycleMemoryItem[];
  durable_finalization: LabDurableFinalizationVisibility;
  queue_worker: LabQueueWorkerVisibility;
  fresh_conversation: LabFreshConversationVisibility;
  mutation_controls_exposed: false;
  scheduler_controls_exposed: false;
  repair_controls_exposed: false;
  raw_content_included: false;
  raw_paths_included: false;
  raw_private_identifiers_included: false;
  bounded_reason_ids: string[];
}

export class LifecycleVisibilityError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "LifecycleVisibilityError";
  }
}

const projectionKeys = [
  "schema", "source", "read_only", "availability", "capability", "character_id", "namespace",
  "memory_items", "durable_finalization", "queue_worker", "fresh_conversation",
  "mutation_controls_exposed", "scheduler_controls_exposed", "repair_controls_exposed",
  "raw_content_included", "raw_paths_included", "raw_private_identifiers_included", "bounded_reason_ids",
] as const;
const memoryItemKeys = [
  "memory_id", "current_lifecycle_state", "current_revision", "current_physical_status",
  "retrieval_eligible", "historical_used_memory_remains_unchanged", "bounded_reason_ids",
] as const;
const durableKeys = [
  "availability", "status", "pending_count", "complete_count", "isolated_count", "content_free",
  "locator_values_included", "path_values_included", "bounded_reason_ids",
] as const;
const queueKeys = [
  "availability", "status", "queued_count", "processing_count", "formed_count", "held_count",
  "blocked_count", "failed_count", "content_free", "queue_identifiers_included", "claim_values_included",
  "scheduler_controls_exposed", "worker_controls_exposed", "bounded_reason_ids",
] as const;
const freshKeys = [
  "browser_local_session_reset_visible", "durable_memory_store_reset", "durable_memory_store_retained",
  "active_current_memories_remain_retrieval_eligible", "hidden_or_current_ineligible_memories_remain_excluded",
  "home_transcript_is_durable_source", "durable_transcript_persistence",
] as const;

export async function loadLifecycleVisibility(
  characterId: string,
  namespace: string,
  signal?: AbortSignal,
): Promise<LabLifecycleVisibilityProjection> {
  const character = encodeURIComponent(characterId);
  const query = `namespace=${encodeURIComponent(namespace)}`;
  const response = await fetch(`/lab/api/characters/${character}/lab/lifecycle-visibility?${query}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });
  if (!response.ok) {
    throw new LifecycleVisibilityError(
      response.status === 403 ? "lifecycle_visibility_access_refused" : `lifecycle_visibility_http_${response.status}`,
    );
  }
  const payload = await response.json() as unknown;
  const projection = parseLifecycleVisibility(payload, characterId, namespace);
  if (!projection) throw new LifecycleVisibilityError("invalid_lifecycle_visibility_schema");
  return projection;
}

export function parseLifecycleVisibility(
  value: unknown,
  characterId: string,
  namespace: string,
): LabLifecycleVisibilityProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, projectionKeys)) return null;
  if (
    value.schema !== "relaylm.lab.lifecycle_visibility.v0" ||
    value.source !== "relaylm_runtime" ||
    value.read_only !== true ||
    !isAvailability(value.availability) ||
    value.capability !== "read_only_lifecycle_and_operation_visibility" ||
    value.character_id !== characterId ||
    value.namespace !== namespace ||
    !Array.isArray(value.memory_items) ||
    value.memory_items.length > 20 ||
    !isRecord(value.durable_finalization) ||
    !isRecord(value.queue_worker) ||
    !isRecord(value.fresh_conversation) ||
    value.mutation_controls_exposed !== false ||
    value.scheduler_controls_exposed !== false ||
    value.repair_controls_exposed !== false ||
    value.raw_content_included !== false ||
    value.raw_paths_included !== false ||
    value.raw_private_identifiers_included !== false ||
    !isReasonIds(value.bounded_reason_ids)
  ) return null;
  const memoryItems = value.memory_items.map(parseMemoryItem);
  const durable = parseDurable(value.durable_finalization);
  const queue = parseQueue(value.queue_worker);
  const fresh = parseFresh(value.fresh_conversation);
  if (memoryItems.some((item) => item === null) || !durable || !queue || !fresh) return null;
  return {
    ...value,
    memory_items: memoryItems as LabLifecycleMemoryItem[],
    durable_finalization: durable,
    queue_worker: queue,
    fresh_conversation: fresh,
  } as LabLifecycleVisibilityProjection;
}

function parseMemoryItem(value: unknown): LabLifecycleMemoryItem | null {
  if (!isRecord(value) || !hasExactKeys(value, memoryItemKeys)) return null;
  if (
    !isOpaqueId(value.memory_id) ||
    !isLifecycleState(value.current_lifecycle_state) ||
    !(value.current_revision === null || isPositiveInteger(value.current_revision)) ||
    !["current", "hidden", "prepared", "recovery_required", "corrupt", "unknown"].includes(String(value.current_physical_status)) ||
    !(value.retrieval_eligible === null || typeof value.retrieval_eligible === "boolean") ||
    value.historical_used_memory_remains_unchanged !== true ||
    !isReasonIds(value.bounded_reason_ids)
  ) return null;
  return value as unknown as LabLifecycleMemoryItem;
}

function parseDurable(value: Record<string, unknown>): LabDurableFinalizationVisibility | null {
  if (!hasExactKeys(value, durableKeys)) return null;
  if (
    !isAvailability(value.availability) || !isDurableStatus(value.status) ||
    !isNonNegativeInteger(value.pending_count) || !isNonNegativeInteger(value.complete_count) ||
    !isNonNegativeInteger(value.isolated_count) || value.content_free !== true ||
    value.locator_values_included !== false || value.path_values_included !== false ||
    !isReasonIds(value.bounded_reason_ids)
  ) return null;
  return value as unknown as LabDurableFinalizationVisibility;
}

function parseQueue(value: Record<string, unknown>): LabQueueWorkerVisibility | null {
  if (!hasExactKeys(value, queueKeys)) return null;
  if (
    !isAvailability(value.availability) || !isQueueStatus(value.status) ||
    !isNonNegativeInteger(value.queued_count) || !isNonNegativeInteger(value.processing_count) ||
    !isNonNegativeInteger(value.formed_count) || !isNonNegativeInteger(value.held_count) ||
    !isNonNegativeInteger(value.blocked_count) || !isNonNegativeInteger(value.failed_count) ||
    value.content_free !== true || value.queue_identifiers_included !== false ||
    value.claim_values_included !== false || value.scheduler_controls_exposed !== false ||
    value.worker_controls_exposed !== false || !isReasonIds(value.bounded_reason_ids)
  ) return null;
  return value as unknown as LabQueueWorkerVisibility;
}

function parseFresh(value: Record<string, unknown>): LabFreshConversationVisibility | null {
  if (!hasExactKeys(value, freshKeys)) return null;
  if (
    value.browser_local_session_reset_visible !== true ||
    value.durable_memory_store_reset !== false ||
    value.durable_memory_store_retained !== true ||
    value.active_current_memories_remain_retrieval_eligible !== true ||
    value.hidden_or_current_ineligible_memories_remain_excluded !== true ||
    value.home_transcript_is_durable_source !== false ||
    value.durable_transcript_persistence !== false
  ) return null;
  return value as unknown as LabFreshConversationVisibility;
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => actual.includes(key));
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function isAvailability(value: unknown): value is LifecycleAvailability {
  return ["available", "empty", "unavailable", "not_connected"].includes(String(value));
}
function isLifecycleState(value: unknown): value is LifecycleState {
  return ["active", "hidden", "prepared", "recovery_required", "corrupt", "unknown"].includes(String(value));
}
function isDurableStatus(value: unknown): value is DurableFinalizationStatus {
  return ["pending", "complete", "isolated", "mixed", "none", "unknown", "unavailable", "not_connected"].includes(String(value));
}
function isQueueStatus(value: unknown): value is QueueWorkerStatus {
  return ["queued", "processing", "formed", "held", "blocked", "failed", "mixed", "none", "unknown", "unavailable", "not_connected"].includes(String(value));
}
function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 1;
}
function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}
function isOpaqueId(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}
function isReasonIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 32 && value.every(
    (item) => typeof item === "string" && /^[a-z0-9][a-z0-9_:-]{0,127}$/.test(item),
  );
}
