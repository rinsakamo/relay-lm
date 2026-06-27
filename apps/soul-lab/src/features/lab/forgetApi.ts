export interface MemoryForgetEffects {
  audit_evidence_retained: boolean;
  historical_used_memory_unchanged: boolean;
  ordinary_retrieval_excluded: boolean;
  physical_deletion: boolean;
  relayctx_injection_excluded: boolean;
}

export interface MemoryForgetPreflight {
  schema: "relaylm.lab.memory_forget_preflight.v0";
  status: "ready";
  read_only: true;
  memory_id: string;
  current_revision: number;
  current_lifecycle_state: "active";
  target_revision: number;
  target_lifecycle_state: "hidden";
  effects: MemoryForgetEffects;
  apply_token: string;
  expires_at: string;
}

export interface MemoryForgetApplyReceipt {
  schema: "relaylm.lab.memory_forget_apply.v0";
  status: "applied" | "already_hidden";
  memory_id: string;
  prior_revision: number;
  result_revision: number;
  lifecycle_state: "hidden";
  mutation_state: "none";
  retrieval_eligible: false;
  ordinary_retrieval_excluded: true;
  relayctx_injection_excluded: true;
  physical_deletion: false;
  audit_evidence_retained: true;
  historical_used_memory_unchanged: true;
  page_converged: boolean;
  index_converged: boolean;
  log_converged: boolean;
  tombstone_present: boolean;
  tombstone_created: boolean;
  idempotent_replay: boolean;
  recovery_required: false;
  reason_ids: string[];
}

export interface MemoryForgetHistory {
  schema: "relaylm.lab.memory_forget_history.v0";
  source: "relaylm_runtime";
  read_only: true;
  memory_id: string;
  current_revision: number;
  current_lifecycle_state: "active" | "hidden" | "unknown";
  forget_count: number;
  items: Array<Record<string, unknown>>;
}

export class MemoryForgetError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "MemoryForgetError";
  }
}

const preflightKeys = [
  "schema", "status", "read_only", "memory_id", "current_revision",
  "current_lifecycle_state", "target_revision", "target_lifecycle_state",
  "effects", "apply_token", "expires_at",
] as const;
const effectKeys = [
  "audit_evidence_retained", "historical_used_memory_unchanged",
  "ordinary_retrieval_excluded", "physical_deletion", "relayctx_injection_excluded",
] as const;
const applyKeys = [
  "schema", "status", "memory_id", "prior_revision", "result_revision",
  "lifecycle_state", "mutation_state", "retrieval_eligible",
  "ordinary_retrieval_excluded", "relayctx_injection_excluded", "physical_deletion",
  "audit_evidence_retained", "historical_used_memory_unchanged", "page_converged",
  "index_converged", "log_converged", "tombstone_present", "tombstone_created",
  "idempotent_replay", "recovery_required", "reason_ids",
] as const;
const historyKeys = [
  "schema", "source", "read_only", "memory_id", "current_revision",
  "current_lifecycle_state", "forget_count", "items",
] as const;

export async function preflightMemoryForget(
  characterId: string,
  namespace: string,
  memoryId: string,
  input: {
    expectedRevision: number;
    expectedLifecycleState: "active";
    reason: string;
    operationId: string;
  },
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<MemoryForgetPreflight> {
  const value = await requestJson(
    pathFor(characterId, namespace, memoryId, "/forget/preflight"),
    {
      schema: "relaylm.lab.memory_forget_preflight_request.v0",
      expected_revision: input.expectedRevision,
      expected_lifecycle_state: input.expectedLifecycleState,
      reason: input.reason,
      operation_id: input.operationId,
    },
    signal,
    fetchImpl,
  );
  const parsed = parseForgetPreflight(value, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryForgetError("schema_invalid");
  return parsed;
}

export async function applyMemoryForget(
  characterId: string,
  namespace: string,
  memoryId: string,
  input: {
    expectedRevision: number;
    expectedLifecycleState: "active";
    reason: string;
    operationId: string;
    applyToken: string;
  },
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<MemoryForgetApplyReceipt> {
  const value = await requestJson(
    pathFor(characterId, namespace, memoryId, "/forget"),
    {
      schema: "relaylm.lab.memory_forget_apply_request.v0",
      expected_revision: input.expectedRevision,
      expected_lifecycle_state: input.expectedLifecycleState,
      reason: input.reason,
      operation_id: input.operationId,
      apply_token: input.applyToken,
    },
    signal,
    fetchImpl,
  );
  const parsed = parseForgetApply(value, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryForgetError("schema_invalid");
  return parsed;
}

export async function loadMemoryForgetHistory(
  characterId: string,
  namespace: string,
  memoryId: string,
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<MemoryForgetHistory> {
  const response = await fetchImpl(pathFor(characterId, namespace, memoryId, "/forget-history"), {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await httpError(response);
  const parsed = parseForgetHistory(await response.json(), memoryId);
  if (!parsed) throw new MemoryForgetError("schema_invalid");
  return parsed;
}

function pathFor(characterId: string, namespace: string, memoryId: string, suffix: string): string {
  return `/lab/api/characters/${encodeURIComponent(characterId)}/memory/${encodeURIComponent(memoryId)}${suffix}?namespace=${encodeURIComponent(namespace)}`;
}

async function requestJson(
  path: string,
  body: unknown,
  signal: AbortSignal | undefined,
  fetchImpl: typeof fetch,
): Promise<unknown> {
  const response = await fetchImpl(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw await httpError(response);
  return response.json() as Promise<unknown>;
}

const boundedServerErrorCodes = new Set([
  "invalid_request",
  "target_not_found",
  "not_found_or_wrong_scope",
  "target_not_active",
  "stale_revision",
  "operation_conflict",
  "preflight_required",
  "token_expired",
  "token_invalid",
  "target_corrupt",
  "reconciliation_required",
  "store_unavailable",
  "access_refused",
  "response_lost",
  "already_hidden",
]);

async function httpError(response: Response): Promise<MemoryForgetError> {
  try {
    const value: unknown = await response.json();
    if (
      isRecord(value) &&
      hasExactKeys(value, ["detail"]) &&
      typeof value.detail === "string" &&
      boundedServerErrorCodes.has(value.detail)
    ) {
      return new MemoryForgetError(value.detail);
    }
  } catch {
    // Fall back to the bounded status mapping below.
  }
  const status = response.status;
  const code = status === 403 ? "access_refused"
    : status === 404 ? "not_found_or_wrong_scope"
    : status === 409 ? "operation_conflict"
    : status === 415 || status === 422 ? "invalid_request"
    : status === 503 ? "reconciliation_required"
    : "runtime_unavailable";
  return new MemoryForgetError(code);
}

export function parseForgetPreflight(value: unknown, memoryId: string, revision: number): MemoryForgetPreflight | null {
  if (!isRecord(value) || !hasExactKeys(value, preflightKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_forget_preflight.v0" || value.status !== "ready" ||
    value.read_only !== true || value.memory_id !== memoryId || value.current_revision !== revision ||
    value.current_lifecycle_state !== "active" || value.target_revision !== revision + 1 ||
    value.target_lifecycle_state !== "hidden" || !parseEffects(value.effects) ||
    !isOpaqueToken(value.apply_token, 8192) || !isSafeText(value.expires_at, 128)
  ) return null;
  return value as unknown as MemoryForgetPreflight;
}

function parseEffects(value: unknown): boolean {
  if (!isRecord(value) || !hasExactKeys(value, effectKeys)) return false;
  return value.audit_evidence_retained === true &&
    value.historical_used_memory_unchanged === true &&
    value.ordinary_retrieval_excluded === true &&
    value.physical_deletion === false &&
    value.relayctx_injection_excluded === true;
}

export function parseForgetApply(value: unknown, memoryId: string, revision: number): MemoryForgetApplyReceipt | null {
  if (!isRecord(value) || !hasExactKeys(value, applyKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_forget_apply.v0" ||
    !["applied", "already_hidden"].includes(String(value.status)) ||
    value.memory_id !== memoryId || value.prior_revision !== revision ||
    !isPositiveInteger(value.result_revision) || Number(value.result_revision) < revision + 1 ||
    value.lifecycle_state !== "hidden" || value.mutation_state !== "none" ||
    value.retrieval_eligible !== false || value.ordinary_retrieval_excluded !== true ||
    value.relayctx_injection_excluded !== true || value.physical_deletion !== false ||
    value.audit_evidence_retained !== true || value.historical_used_memory_unchanged !== true ||
    typeof value.page_converged !== "boolean" || typeof value.index_converged !== "boolean" ||
    typeof value.log_converged !== "boolean" || typeof value.tombstone_present !== "boolean" ||
    typeof value.tombstone_created !== "boolean" || typeof value.idempotent_replay !== "boolean" ||
    value.recovery_required !== false || !isReasonIds(value.reason_ids)
  ) return null;
  return value as unknown as MemoryForgetApplyReceipt;
}

export function parseForgetHistory(value: unknown, memoryId: string): MemoryForgetHistory | null {
  if (!isRecord(value) || !hasExactKeys(value, historyKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_forget_history.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || value.memory_id !== memoryId || !isPositiveInteger(value.current_revision) ||
    !["active", "hidden", "unknown"].includes(String(value.current_lifecycle_state)) ||
    !isNonNegativeInteger(value.forget_count) || !Array.isArray(value.items) || value.items.length > 50 ||
    value.items.some((item) => !isBoundedHistoryItem(item))
  ) return null;
  return value as unknown as MemoryForgetHistory;
}

function isBoundedHistoryItem(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const forbidden = ["reason", "reason_digest", "token", "token_digest", "physical_id", "store_root", "path", "tombstone"];
  const serialized = JSON.stringify(value);
  return serialized.length <= 4096 && forbidden.every((key) => !serialized.includes(key));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 1;
}

function isNonNegativeInteger(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 0;
}

function isOpaqueToken(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && /^[A-Za-z0-9_.-]+$/.test(value);
}

function isReasonIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 32 && value.every(
    (item) => typeof item === "string" && /^[a-z0-9][a-z0-9_:-]{0,127}$/.test(item),
  );
}

function isSafeText(value: unknown, maximum: number): value is string {
  if (typeof value !== "string" || value.length > maximum || value.length === 0) return false;
  return ![...value].some((character) => {
    const code = character.codePointAt(0) ?? 0;
    return code < 32 || code === 0x2028 || code === 0x2029 || (code >= 0xd800 && code <= 0xdfff);
  });
}
