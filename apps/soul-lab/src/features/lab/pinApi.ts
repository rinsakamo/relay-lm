export interface MemoryPinEffects {
  audit_evidence_retained: boolean;
  future_priority_hint_contract?: boolean;
  future_priority_hint_removed_contract?: boolean;
  ordinary_retrieval_deleted: boolean;
  ordinary_retrieval_excluded: boolean;
  physical_deletion: boolean;
  semantic_content_changed: boolean;
}

export interface MemoryPinPreflight {
  schema: "relaylm.lab.memory_pin_preflight.v0" | "relaylm.lab.memory_unpin_preflight.v0";
  status: "ready" | "already_pinned" | "already_unpinned";
  operation_kind: "pin" | "unpin";
  read_only: true;
  memory_id: string;
  current_revision: number;
  current_lifecycle_state: "active";
  current_mutation_state: "none";
  current_pin_state: "pinned" | "unpinned";
  target_pin_state: "pinned" | "unpinned";
  pin_state_contract_only: false;
  effects: MemoryPinEffects;
  apply_token: string | null;
  expires_at: string | null;
}

export interface MemoryPinApplyReceipt {
  schema: "relaylm.lab.memory_pin_apply.v0" | "relaylm.lab.memory_unpin_apply.v0";
  status: "applied" | "already_pinned" | "already_unpinned";
  operation_kind: "pin" | "unpin";
  memory_id: string;
  current_revision: number;
  current_lifecycle_state: "active";
  current_mutation_state: "none";
  prior_pin_state: "pinned" | "unpinned";
  target_pin_state: "pinned" | "unpinned";
  retrieval_eligible: true;
  ordinary_retrieval_excluded: false;
  priority_hint_enabled: boolean;
  semantic_content_changed: false;
  physical_deletion: false;
  audit_evidence_retained: true;
  idempotent_replay: boolean;
  effect_applied: boolean;
  receipt_id: string;
  content_included: false;
  path_included: false;
  physical_id_included: false;
  reason_included: false;
  token_included: false;
}

export class MemoryPinError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "MemoryPinError";
  }
}

export async function preflightMemoryPin(characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string }, signal?: AbortSignal, fetchImpl: typeof fetch = fetch): Promise<MemoryPinPreflight> {
  return requestPreflight("pin", characterId, namespace, memoryId, input, signal, fetchImpl);
}

export async function preflightMemoryUnpin(characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string }, signal?: AbortSignal, fetchImpl: typeof fetch = fetch): Promise<MemoryPinPreflight> {
  return requestPreflight("unpin", characterId, namespace, memoryId, input, signal, fetchImpl);
}

export async function applyMemoryPin(characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string; applyToken: string }, signal?: AbortSignal, fetchImpl: typeof fetch = fetch): Promise<MemoryPinApplyReceipt> {
  return requestApply("pin", characterId, namespace, memoryId, input, signal, fetchImpl);
}

export async function applyMemoryUnpin(characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string; applyToken: string }, signal?: AbortSignal, fetchImpl: typeof fetch = fetch): Promise<MemoryPinApplyReceipt> {
  return requestApply("unpin", characterId, namespace, memoryId, input, signal, fetchImpl);
}

async function requestPreflight(kind: "pin" | "unpin", characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string }, signal: AbortSignal | undefined, fetchImpl: typeof fetch): Promise<MemoryPinPreflight> {
  const value = await requestJson(pathFor(characterId, namespace, memoryId, `/${kind}/preflight`), {
    schema: `relaylm.lab.memory_${kind}_preflight_request.v0`,
    expected_revision: input.expectedRevision,
    reason: input.reason,
    operation_id: input.operationId,
  }, signal, fetchImpl);
  const parsed = parsePinPreflight(value, kind, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryPinError("schema_invalid");
  return parsed;
}

async function requestApply(kind: "pin" | "unpin", characterId: string, namespace: string, memoryId: string, input: { expectedRevision: number; reason: string; operationId: string; applyToken: string }, signal: AbortSignal | undefined, fetchImpl: typeof fetch): Promise<MemoryPinApplyReceipt> {
  const value = await requestJson(pathFor(characterId, namespace, memoryId, `/${kind}`), {
    schema: `relaylm.lab.memory_${kind}_apply_request.v0`,
    expected_revision: input.expectedRevision,
    reason: input.reason,
    operation_id: input.operationId,
    apply_token: input.applyToken,
  }, signal, fetchImpl);
  const parsed = parsePinApply(value, kind, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryPinError("schema_invalid");
  return parsed;
}

function pathFor(characterId: string, namespace: string, memoryId: string, suffix: string): string {
  return `/lab/api/characters/${encodeURIComponent(characterId)}/memory/${encodeURIComponent(memoryId)}${suffix}?namespace=${encodeURIComponent(namespace)}`;
}

async function requestJson(path: string, body: unknown, signal: AbortSignal | undefined, fetchImpl: typeof fetch): Promise<unknown> {
  const response = await fetchImpl(path, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, credentials: "same-origin", cache: "no-store", body: JSON.stringify(body), signal });
  if (!response.ok) throw await httpError(response);
  return response.json() as Promise<unknown>;
}

const boundedServerErrorCodes = new Set(["invalid_request", "target_not_found", "not_found_or_wrong_scope", "target_not_active", "stale_revision", "operation_conflict", "preflight_required", "token_expired", "token_invalid", "target_corrupt", "recovery_required", "store_unavailable", "access_refused", "response_lost", "already_pinned", "already_unpinned"]);

async function httpError(response: Response): Promise<MemoryPinError> {
  try {
    const value: unknown = await response.json();
    if (isRecord(value) && hasExactKeys(value, ["detail"]) && typeof value.detail === "string" && boundedServerErrorCodes.has(value.detail)) return new MemoryPinError(value.detail);
  } catch {}
  const code = response.status === 403 ? "access_refused" : response.status === 404 ? "not_found_or_wrong_scope" : response.status === 409 ? "operation_conflict" : response.status === 415 || response.status === 422 ? "invalid_request" : response.status === 503 ? "store_unavailable" : "runtime_unavailable";
  return new MemoryPinError(code);
}

export function parsePinPreflight(value: unknown, kind: "pin" | "unpin", memoryId: string, revision: number): MemoryPinPreflight | null {
  if (!isRecord(value)) return null;
  const keys = ["schema", "status", "operation_kind", "read_only", "memory_id", "current_revision", "current_lifecycle_state", "current_mutation_state", "current_pin_state", "target_pin_state", "pin_state_contract_only", "effects", "apply_token", "expires_at"];
  const target = kind === "pin" ? "pinned" : "unpinned";
  const alreadyStatus = kind === "pin" ? "already_pinned" : "already_unpinned";
  if (!hasExactKeys(value, keys) || value.schema !== `relaylm.lab.memory_${kind}_preflight.v0` || value.operation_kind !== kind || !["ready", alreadyStatus].includes(String(value.status)) || value.read_only !== true || value.memory_id !== memoryId || value.current_revision !== revision || value.current_lifecycle_state !== "active" || value.current_mutation_state !== "none" || !isPinState(value.current_pin_state) || value.target_pin_state !== target || value.pin_state_contract_only !== false || !parseEffects(value.effects, kind)) return null;
  if (value.status === "ready") return value.current_pin_state !== target && isOpaqueToken(value.apply_token, 8192) && isSafeText(value.expires_at, 128) ? value as unknown as MemoryPinPreflight : null;
  return value.current_pin_state === target && value.apply_token === null && value.expires_at === null ? value as unknown as MemoryPinPreflight : null;
}

function parseEffects(value: unknown, kind: "pin" | "unpin"): boolean {
  if (!isRecord(value)) return false;
  const hint = kind === "pin" ? "future_priority_hint_contract" : "future_priority_hint_removed_contract";
  return hasExactKeys(value, ["audit_evidence_retained", "ordinary_retrieval_deleted", "ordinary_retrieval_excluded", "physical_deletion", "semantic_content_changed", hint]) && value.audit_evidence_retained === true && value.ordinary_retrieval_deleted === false && value.ordinary_retrieval_excluded === false && value.physical_deletion === false && value.semantic_content_changed === false && value[hint] === true;
}

export function parsePinApply(value: unknown, kind: "pin" | "unpin", memoryId: string, revision: number): MemoryPinApplyReceipt | null {
  if (!isRecord(value)) return null;
  const keys = ["schema", "status", "operation_kind", "memory_id", "current_revision", "current_lifecycle_state", "current_mutation_state", "prior_pin_state", "target_pin_state", "retrieval_eligible", "ordinary_retrieval_excluded", "priority_hint_enabled", "semantic_content_changed", "physical_deletion", "audit_evidence_retained", "idempotent_replay", "effect_applied", "receipt_id", "content_included", "path_included", "physical_id_included", "reason_included", "token_included"];
  const target = kind === "pin" ? "pinned" : "unpinned";
  const alreadyStatus = kind === "pin" ? "already_pinned" : "already_unpinned";
  if (!hasExactKeys(value, keys) || value.schema !== `relaylm.lab.memory_${kind}_apply.v0` || value.operation_kind !== kind || !["applied", alreadyStatus].includes(String(value.status)) || value.memory_id !== memoryId || value.current_revision !== revision || value.current_lifecycle_state !== "active" || value.current_mutation_state !== "none" || !isPinState(value.prior_pin_state) || value.target_pin_state !== target || value.retrieval_eligible !== true || value.ordinary_retrieval_excluded !== false || value.priority_hint_enabled !== (target === "pinned") || value.semantic_content_changed !== false || value.physical_deletion !== false || value.audit_evidence_retained !== true || typeof value.idempotent_replay !== "boolean" || typeof value.effect_applied !== "boolean" || (value.status === "applied") !== value.effect_applied || !isSafeId(value.receipt_id) || value.content_included !== false || value.path_included !== false || value.physical_id_included !== false || value.reason_included !== false || value.token_included !== false) return null;
  return value as unknown as MemoryPinApplyReceipt;
}

function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean { const actual = Object.keys(value).sort(); const expected = [...keys].sort(); return actual.length === expected.length && actual.every((key, index) => key === expected[index]); }
function isOpaqueToken(value: unknown, maximum: number): value is string { return typeof value === "string" && value.length > 0 && value.length <= maximum && /^[A-Za-z0-9_.-]+$/.test(value); }
function isPinState(value: unknown): value is "pinned" | "unpinned" { return value === "pinned" || value === "unpinned"; }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{64}$/.test(value); }
function isSafeText(value: unknown, maximum: number): value is string { if (typeof value !== "string" || value.length > maximum || value.length === 0) return false; return ![...value].some((character) => { const code = character.codePointAt(0) ?? 0; return code < 32 || code === 0x2028 || code === 0x2029 || (code >= 0xd800 && code <= 0xdfff); }); }
