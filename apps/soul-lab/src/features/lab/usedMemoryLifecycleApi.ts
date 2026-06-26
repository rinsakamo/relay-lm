export type CurrentMemoryLifecycle = "active" | "hidden" | "unknown";
export type LifecycleAvailability = "available" | "empty" | "unavailable";

export interface UsedMemoryLifecycleItem {
  memory_id: string;
  injected_summary: string;
  current_summary: string | null;
  current_lifecycle_state: CurrentMemoryLifecycle;
  representation_changed: boolean;
  lifecycle_changed: boolean;
  source_kind: string;
}

export interface UsedMemoryLifecycleProjection {
  schema: "relaylm.lab.memory_used_lifecycle.v1";
  source: "relaylm_runtime";
  read_only: true;
  availability: LifecycleAvailability;
  capability: "backend_bound_memory_evidence_with_current_lifecycle";
  character_id: string;
  namespace: string;
  run_id: string | null;
  retrieval_attempted: boolean;
  candidate_discovered: boolean;
  selected: boolean;
  relayctx_injection_performed: boolean;
  backend_bound_included: boolean;
  response_generation_completed: boolean;
  items: UsedMemoryLifecycleItem[];
  bounded_reason_ids: string[];
}

export class UsedMemoryLifecycleError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "UsedMemoryLifecycleError";
  }
}

const projectionKeys = [
  "schema", "source", "read_only", "availability", "capability",
  "character_id", "namespace", "run_id", "retrieval_attempted",
  "candidate_discovered", "selected", "relayctx_injection_performed",
  "backend_bound_included", "response_generation_completed", "items",
  "bounded_reason_ids",
] as const;
const itemKeys = [
  "memory_id", "injected_summary", "current_summary",
  "current_lifecycle_state", "representation_changed", "lifecycle_changed",
  "source_kind",
] as const;

export async function loadUsedMemoryLifecycle(
  characterId: string,
  namespace: string,
  signal?: AbortSignal,
): Promise<UsedMemoryLifecycleProjection> {
  const character = encodeURIComponent(characterId);
  const query = `namespace=${encodeURIComponent(namespace)}`;
  const response = await fetch(
    `/lab/api/characters/${character}/lab/last-run/memory/used-lifecycle?${query}`,
    { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", credentials: "same-origin", signal },
  );
  if (!response.ok) {
    throw new UsedMemoryLifecycleError(
      response.status === 403 ? "used_memory_lifecycle_access_refused" : `used_memory_lifecycle_http_${response.status}`,
    );
  }
  const parsed = parseUsedMemoryLifecycle(await response.json());
  if (parsed === null || parsed.character_id !== characterId || parsed.namespace !== namespace) {
    throw new UsedMemoryLifecycleError("invalid_used_memory_lifecycle_schema");
  }
  return parsed;
}

export function parseUsedMemoryLifecycle(value: unknown): UsedMemoryLifecycleProjection | null {
  if (!isRecord(value) || !hasExactKeys(value, projectionKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_used_lifecycle.v1" ||
    value.source !== "relaylm_runtime" || value.read_only !== true ||
    !["available", "empty", "unavailable"].includes(String(value.availability)) ||
    value.capability !== "backend_bound_memory_evidence_with_current_lifecycle" ||
    typeof value.character_id !== "string" || typeof value.namespace !== "string" ||
    !(value.run_id === null || typeof value.run_id === "string") ||
    typeof value.retrieval_attempted !== "boolean" || typeof value.candidate_discovered !== "boolean" ||
    typeof value.selected !== "boolean" || typeof value.relayctx_injection_performed !== "boolean" ||
    typeof value.backend_bound_included !== "boolean" || typeof value.response_generation_completed !== "boolean" ||
    !Array.isArray(value.items) || value.items.length > 16 || !isReasonIds(value.bounded_reason_ids)
  ) return null;
  const items = value.items.map(parseItem);
  if (items.some((item) => item === null)) return null;
  if (items.length > 0 && (!value.relayctx_injection_performed || !value.backend_bound_included)) return null;
  return { ...value, items: items as UsedMemoryLifecycleItem[] } as UsedMemoryLifecycleProjection;
}

function parseItem(value: unknown): UsedMemoryLifecycleItem | null {
  if (!isRecord(value) || !hasExactKeys(value, itemKeys)) return null;
  if (
    !isOpaqueId(value.memory_id) || !isSafeText(value.injected_summary, 512) ||
    !(value.current_summary === null || isSafeText(value.current_summary, 512)) ||
    !["active", "hidden", "unknown"].includes(String(value.current_lifecycle_state)) ||
    typeof value.representation_changed !== "boolean" || typeof value.lifecycle_changed !== "boolean" ||
    typeof value.source_kind !== "string"
  ) return null;
  if (value.current_lifecycle_state !== "active" && value.current_summary !== null) return null;
  if (value.current_lifecycle_state === "hidden" && value.lifecycle_changed !== true) return null;
  return value as unknown as UsedMemoryLifecycleItem;
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => actual.includes(key));
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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
  if (typeof value !== "string" || Array.from(value).length > maximum) return false;
  return Array.from(value).every((character) => {
    const code = character.codePointAt(0) ?? 0;
    return code >= 32 && code !== 127 && code !== 0x2028 && code !== 0x2029;
  });
}
