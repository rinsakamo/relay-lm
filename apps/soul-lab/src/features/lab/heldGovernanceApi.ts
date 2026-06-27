export type HeldGovernanceAction = "apply" | "discard";
export type HeldGovernanceStatus =
  | "ready"
  | "applied"
  | "discarded"
  | "already_applied"
  | "already_discarded"
  | "blocked"
  | "safe_failure"
  | "invalid_input"
  | "operation_conflict"
  | "stale_candidate";

export interface HeldGovernanceEffects {
  held_item_adopted_contract: boolean;
  held_item_discarded_contract: boolean;
  queue_state_mutated: boolean;
  primary_mem_mutated: boolean;
  worker_started: boolean;
  scheduler_started: boolean;
  automatic_retry_or_release: boolean;
  runtime_private_content_exposed: boolean;
}

export interface HeldGovernancePreflight {
  schema: "relaylm.lab.held_governance_preflight.v0";
  status: HeldGovernanceStatus;
  action: HeldGovernanceAction;
  read_only: true;
  candidate_id_short: string;
  operation_id_short: string;
  reason_code: string;
  blocked_reason_ids: string[];
  effects: HeldGovernanceEffects;
  already_applied: boolean;
  already_discarded: boolean;
  content_free: true;
  runtime_private_evidence_omitted: true;
  source_body_included: false;
  model_output_included: false;
  memory_content_included: false;
  queue_payload_included: false;
  primary_page_path_included: false;
  store_root_included: false;
  queue_root_included: false;
  claim_token_included: false;
  lease_owner_included: false;
  raw_exception_included: false;
  queue_state_mutated: false;
  primary_mem_mutated: false;
  worker_started: false;
  scheduler_started: false;
  automatic_retry_or_release: false;
  apply_token: string | null;
  expires_at: string | null;
}

export interface HeldGovernanceReceipt extends Omit<HeldGovernancePreflight, "schema" | "read_only" | "apply_token" | "expires_at"> {
  schema: "relaylm.lab.held_governance_receipt.v0";
  read_only: false;
  idempotent_replay: boolean;
  candidate_generation_stable: boolean;
}

export interface HeldGovernanceHistory {
  schema: "relaylm.lab.held_governance_history.v0";
  source: "relaylm_runtime";
  read_only: true;
  candidate_id_short: string;
  count: number;
  items: Array<{
    status: string;
    action: HeldGovernanceAction;
    operation_id_short: string;
    decided_at: string;
    reason_code: string;
    content_free: true;
    runtime_private_evidence_omitted: true;
  }>;
  content_free: true;
  runtime_private_evidence_omitted: true;
}

export class HeldGovernanceError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "HeldGovernanceError";
  }
}

const effectKeys = [
  "held_item_adopted_contract", "held_item_discarded_contract", "queue_state_mutated",
  "primary_mem_mutated", "worker_started", "scheduler_started", "automatic_retry_or_release",
  "runtime_private_content_exposed",
] as const;
const preflightKeys = [
  "schema", "status", "action", "read_only", "candidate_id_short", "operation_id_short",
  "reason_code", "blocked_reason_ids", "effects", "already_applied", "already_discarded",
  "content_free", "runtime_private_evidence_omitted", "source_body_included", "model_output_included",
  "memory_content_included", "queue_payload_included", "primary_page_path_included", "store_root_included",
  "queue_root_included", "claim_token_included", "lease_owner_included", "raw_exception_included",
  "queue_state_mutated", "primary_mem_mutated", "worker_started", "scheduler_started",
  "automatic_retry_or_release", "apply_token", "expires_at",
] as const;
const receiptKeys = [
  "schema", "status", "action", "read_only", "candidate_id_short", "operation_id_short",
  "reason_code", "blocked_reason_ids", "effects", "already_applied", "already_discarded",
  "content_free", "runtime_private_evidence_omitted", "source_body_included", "model_output_included",
  "memory_content_included", "queue_payload_included", "primary_page_path_included", "store_root_included",
  "queue_root_included", "claim_token_included", "lease_owner_included", "raw_exception_included",
  "queue_state_mutated", "primary_mem_mutated", "worker_started", "scheduler_started",
  "automatic_retry_or_release", "idempotent_replay", "candidate_generation_stable",
] as const;
const historyKeys = [
  "schema", "source", "read_only", "candidate_id_short", "count", "items",
  "content_free", "runtime_private_evidence_omitted",
] as const;

export async function preflightHeldGovernance(
  characterId: string,
  namespace: string,
  candidateId: string,
  action: HeldGovernanceAction,
  input: { operationId: string; reason: string },
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<HeldGovernancePreflight> {
  const value = await requestJson(pathFor(characterId, namespace, candidateId, `/${action}/preflight`), {
    schema: "relaylm.lab.held_governance_preflight_request.v0",
    operation_id: input.operationId,
    reason: input.reason,
  }, signal, fetchImpl);
  const parsed = parseHeldGovernancePreflight(value, action);
  if (!parsed) throw new HeldGovernanceError("schema_invalid");
  return parsed;
}

export async function applyHeldGovernance(
  characterId: string,
  namespace: string,
  candidateId: string,
  action: HeldGovernanceAction,
  input: { operationId: string; reason: string; applyToken: string },
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<HeldGovernanceReceipt> {
  const value = await requestJson(pathFor(characterId, namespace, candidateId, `/${action}`), {
    schema: "relaylm.lab.held_governance_decision_request.v0",
    operation_id: input.operationId,
    reason: input.reason,
    apply_token: input.applyToken,
  }, signal, fetchImpl);
  const parsed = parseHeldGovernanceReceipt(value, action);
  if (!parsed) throw new HeldGovernanceError("schema_invalid");
  return parsed;
}

export async function loadHeldGovernanceHistory(
  characterId: string,
  namespace: string,
  candidateId: string,
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<HeldGovernanceHistory> {
  const response = await fetchImpl(pathFor(characterId, namespace, candidateId, "/history"), {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await httpError(response);
  const parsed = parseHeldGovernanceHistory(await response.json());
  if (!parsed) throw new HeldGovernanceError("schema_invalid");
  return parsed;
}

function pathFor(characterId: string, namespace: string, candidateId: string, suffix: string): string {
  return `/lab/api/characters/${encodeURIComponent(characterId)}/held/${encodeURIComponent(candidateId)}${suffix}?namespace=${encodeURIComponent(namespace)}`;
}

async function requestJson(path: string, body: unknown, signal: AbortSignal | undefined, fetchImpl: typeof fetch): Promise<unknown> {
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
  "invalid_request", "target_not_found", "not_found_or_wrong_scope", "not_held", "not_governable",
  "operation_conflict", "stale_candidate", "preflight_required", "token_expired", "token_invalid",
  "source_missing", "source_corrupt", "source_ambiguous", "store_unavailable", "access_refused", "response_lost",
]);

async function httpError(response: Response): Promise<HeldGovernanceError> {
  try {
    const value: unknown = await response.json();
    if (isRecord(value) && hasExactKeys(value, ["detail"]) && typeof value.detail === "string" && boundedServerErrorCodes.has(value.detail)) {
      return new HeldGovernanceError(value.detail);
    }
  } catch {
    // bounded fallback below
  }
  const status = response.status;
  const code = status === 403 ? "access_refused"
    : status === 404 ? "target_not_found"
    : status === 409 ? "operation_conflict"
    : status === 415 || status === 422 ? "invalid_request"
    : status === 503 ? "store_unavailable"
    : "runtime_unavailable";
  return new HeldGovernanceError(code);
}

export function parseHeldGovernancePreflight(value: unknown, action: HeldGovernanceAction): HeldGovernancePreflight | null {
  if (!isRecord(value) || !hasExactKeys(value, preflightKeys)) return null;
  if (!parseCommon(value, "relaylm.lab.held_governance_preflight.v0", action, true)) return null;
  if (!(value.apply_token === null || isOpaqueToken(value.apply_token, 8192))) return null;
  if (!(value.expires_at === null || isSafeText(value.expires_at, 128))) return null;
  if (value.status === "ready" && (typeof value.apply_token !== "string" || typeof value.expires_at !== "string")) return null;
  return value as unknown as HeldGovernancePreflight;
}

export function parseHeldGovernanceReceipt(value: unknown, action: HeldGovernanceAction): HeldGovernanceReceipt | null {
  if (!isRecord(value) || !hasExactKeys(value, receiptKeys)) return null;
  if (!parseCommon(value, "relaylm.lab.held_governance_receipt.v0", action, false)) return null;
  if (typeof value.idempotent_replay !== "boolean" || typeof value.candidate_generation_stable !== "boolean") return null;
  return value as unknown as HeldGovernanceReceipt;
}

export function parseHeldGovernanceHistory(value: unknown): HeldGovernanceHistory | null {
  if (!isRecord(value) || !hasExactKeys(value, historyKeys)) return null;
  if (
    value.schema !== "relaylm.lab.held_governance_history.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || !isSafeText(value.candidate_id_short, 128) || !isNonNegativeInteger(value.count) ||
    !Array.isArray(value.items) || value.items.length > 50 || value.count !== value.items.length ||
    value.content_free !== true || value.runtime_private_evidence_omitted !== true ||
    value.items.some((item) => !isBoundedHistoryItem(item)) || hasForbiddenPrivateLeak(value)
  ) return null;
  return value as unknown as HeldGovernanceHistory;
}

function parseCommon(value: Record<string, unknown>, schema: string, action: HeldGovernanceAction, readOnly: boolean): boolean {
  return value.schema === schema && isHeldStatus(value.status) && value.action === action && value.read_only === readOnly &&
    isSafeText(value.candidate_id_short, 128) && isSafeText(value.operation_id_short, 128) && isReason(value.reason_code) &&
    isReasonIds(value.blocked_reason_ids) && parseEffects(value.effects, action) &&
    typeof value.already_applied === "boolean" && typeof value.already_discarded === "boolean" &&
    value.content_free === true && value.runtime_private_evidence_omitted === true &&
    value.source_body_included === false && value.model_output_included === false && value.memory_content_included === false &&
    value.queue_payload_included === false && value.primary_page_path_included === false && value.store_root_included === false &&
    value.queue_root_included === false && value.claim_token_included === false && value.lease_owner_included === false &&
    value.raw_exception_included === false && value.queue_state_mutated === false && value.primary_mem_mutated === false &&
    value.worker_started === false && value.scheduler_started === false && value.automatic_retry_or_release === false &&
    !hasForbiddenPrivateLeak(value);
}

function parseEffects(value: unknown, action: HeldGovernanceAction): value is HeldGovernanceEffects {
  if (!isRecord(value) || !hasExactKeys(value, effectKeys)) return false;
  return value.held_item_adopted_contract === (action === "apply") &&
    value.held_item_discarded_contract === (action === "discard") &&
    value.queue_state_mutated === false && value.primary_mem_mutated === false &&
    value.worker_started === false && value.scheduler_started === false &&
    value.automatic_retry_or_release === false && value.runtime_private_content_exposed === false;
}

function isBoundedHistoryItem(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const keys = ["status", "action", "operation_id_short", "decided_at", "reason_code", "content_free", "runtime_private_evidence_omitted"] as const;
  return hasExactKeys(value, keys) && typeof value.status === "string" && (value.action === "apply" || value.action === "discard") &&
    isSafeText(value.operation_id_short, 128) && isSafeText(value.decided_at, 128) && isReason(value.reason_code) &&
    value.content_free === true && value.runtime_private_evidence_omitted === true && !hasForbiddenPrivateLeak(value);
}

function hasForbiddenPrivateLeak(value: unknown): boolean {
  const serialized = JSON.stringify(value);
  return [
    "source_evidence_digest", "candidate_digest", "reason_digest", "token_digest",
    "source_path", "protected_source", "SECRET_",
  ].some((token) => serialized.includes(token));
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function isHeldStatus(value: unknown): value is HeldGovernanceStatus {
  return typeof value === "string" && [
    "ready", "applied", "discarded", "already_applied", "already_discarded", "blocked", "safe_failure",
    "invalid_input", "operation_conflict", "stale_candidate",
  ].includes(value);
}
function isNonNegativeInteger(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 0;
}
function isOpaqueToken(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && /^[A-Za-z0-9_.-]+$/.test(value);
}
function isReason(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9][a-z0-9_:-]{0,127}$/.test(value);
}
function isReasonIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 32 && value.every((item) => isReason(item));
}
function isSafeText(value: unknown, maximum: number): value is string {
  if (typeof value !== "string" || value.length > maximum || value.length === 0) return false;
  return ![...value].some((character) => {
    const code = character.codePointAt(0) ?? 0;
    return code < 32 || code === 0x2028 || code === 0x2029 || (code >= 0xd800 && code <= 0xdfff);
  });
}
