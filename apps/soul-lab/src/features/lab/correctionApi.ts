export interface MemoryCorrectionDiffValue {
  title: string;
  summary: string;
}

export interface MemoryCorrectionPreflight {
  schema: "relaylm.lab.memory_correct_preflight.v0";
  status: "ready";
  read_only: true;
  memory_id: string;
  current_revision: number;
  candidate_revision: number;
  diff: {
    title_changed: boolean;
    summary_changed: boolean;
    before: MemoryCorrectionDiffValue;
    after: MemoryCorrectionDiffValue;
  };
  apply_token: string;
  expires_at: string;
}

export interface MemoryCorrectionApplyResult {
  schema: "relaylm.lab.memory_correct_apply.v0";
  status: "applied";
  memory_id: string;
  prior_revision: number;
  result_revision: number;
  correction_id: string;
  reconciled: boolean;
  recovery_required: boolean;
  idempotent_replay: boolean;
  applied_at: string;
}

export interface MemoryCorrectionHistoryItem {
  correction_id: string;
  prior_revision: number;
  result_revision: number;
  reason: string;
  status: "reconciled";
  applied_at: string;
  title_changed: boolean;
  summary_changed: boolean;
}

export interface MemoryCorrectionHistory {
  schema: "relaylm.lab.memory_corrections.v0";
  source: "relaylm_runtime";
  read_only: true;
  memory_id: string;
  current_revision: number;
  correction_count: number;
  last_corrected_at: string | null;
  last_correction_status: "reconciled" | null;
  has_prior_revision: boolean;
  items: MemoryCorrectionHistoryItem[];
}

export class MemoryCorrectionError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "MemoryCorrectionError";
  }
}

const preflightKeys = [
  "schema", "status", "read_only", "memory_id", "current_revision",
  "candidate_revision", "diff", "apply_token", "expires_at",
] as const;
const diffKeys = ["title_changed", "summary_changed", "before", "after"] as const;
const diffValueKeys = ["title", "summary"] as const;
const applyKeys = [
  "schema", "status", "memory_id", "prior_revision", "result_revision",
  "correction_id", "reconciled", "recovery_required", "idempotent_replay", "applied_at",
] as const;
const historyKeys = [
  "schema", "source", "read_only", "memory_id", "current_revision", "correction_count",
  "last_corrected_at", "last_correction_status", "has_prior_revision", "items",
] as const;
const historyItemKeys = [
  "correction_id", "prior_revision", "result_revision", "reason", "status", "applied_at",
  "title_changed", "summary_changed",
] as const;

export async function preflightMemoryCorrection(
  characterId: string,
  namespace: string,
  memoryId: string,
  input: {
    expectedRevision: number;
    correctedTitle: string;
    correctedSummary: string;
    reason: string;
    operationId: string;
  },
  signal?: AbortSignal,
): Promise<MemoryCorrectionPreflight> {
  const value = await requestJson(
    pathFor(characterId, namespace, memoryId, "/correct/preflight"),
    {
      schema: "relaylm.lab.memory_correct_preflight_request.v0",
      expected_revision: input.expectedRevision,
      corrected_title: input.correctedTitle,
      corrected_summary: input.correctedSummary,
      reason: input.reason,
      operation_id: input.operationId,
    },
    signal,
  );
  const parsed = parsePreflight(value, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryCorrectionError("schema_invalid");
  return parsed;
}

export async function applyMemoryCorrection(
  characterId: string,
  namespace: string,
  memoryId: string,
  input: {
    expectedRevision: number;
    operationId: string;
    applyToken: string;
  },
  signal?: AbortSignal,
): Promise<MemoryCorrectionApplyResult> {
  const value = await requestJson(
    pathFor(characterId, namespace, memoryId, "/correct"),
    {
      schema: "relaylm.lab.memory_correct_apply_request.v0",
      operation_id: input.operationId,
      apply_token: input.applyToken,
      expected_revision: input.expectedRevision,
    },
    signal,
  );
  const parsed = parseApply(value, memoryId, input.expectedRevision);
  if (!parsed) throw new MemoryCorrectionError("schema_invalid");
  return parsed;
}

export async function loadMemoryCorrectionHistory(
  characterId: string,
  namespace: string,
  memoryId: string,
  signal?: AbortSignal,
): Promise<MemoryCorrectionHistory> {
  const response = await fetch(pathFor(characterId, namespace, memoryId, "/corrections"), {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await httpError(response);
  const parsed = parseHistory(await response.json(), memoryId);
  if (!parsed) throw new MemoryCorrectionError("schema_invalid");
  return parsed;
}

function pathFor(characterId: string, namespace: string, memoryId: string, suffix: string): string {
  return `/lab/api/characters/${encodeURIComponent(characterId)}/memory/${encodeURIComponent(memoryId)}${suffix}?namespace=${encodeURIComponent(namespace)}`;
}

async function requestJson(path: string, body: unknown, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(path, {
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
  "not_found_or_wrong_scope",
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
]);

async function httpError(response: Response): Promise<MemoryCorrectionError> {
  try {
    const value: unknown = await response.json();
    if (
      isRecord(value) &&
      hasExactKeys(value, ["detail"]) &&
      typeof value.detail === "string" &&
      boundedServerErrorCodes.has(value.detail)
    ) {
      return new MemoryCorrectionError(value.detail);
    }
  } catch {
    // Fall back to the bounded status mapping below.
  }
  const status = response.status;
  const code = status === 403 ? "access_refused"
    : status === 404 ? "not_found_or_wrong_scope"
    : status === 409 ? "conflict"
    : status === 415 || status === 422 ? "invalid_request"
    : status === 503 ? "reconciliation_required"
    : "runtime_unavailable";
  return new MemoryCorrectionError(code);
}

function parsePreflight(value: unknown, memoryId: string, revision: number): MemoryCorrectionPreflight | null {
  if (!isRecord(value) || !hasExactKeys(value, preflightKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_correct_preflight.v0" || value.status !== "ready" ||
    value.read_only !== true || value.memory_id !== memoryId || value.current_revision !== revision ||
    value.candidate_revision !== revision + 1 || !isOpaqueToken(value.apply_token, 8192) ||
    !isSafeText(value.expires_at, 128) || !parseDiff(value.diff)
  ) return null;
  return value as unknown as MemoryCorrectionPreflight;
}

function parseDiff(value: unknown): boolean {
  if (!isRecord(value) || !hasExactKeys(value, diffKeys)) return false;
  return typeof value.title_changed === "boolean" && typeof value.summary_changed === "boolean" &&
    parseDiffValue(value.before) && parseDiffValue(value.after) &&
    (value.title_changed || value.summary_changed);
}

function parseDiffValue(value: unknown): boolean {
  return isRecord(value) && hasExactKeys(value, diffValueKeys) &&
    isSafeText(value.title, 160, true) && isSafeText(value.summary, 2048);
}

function parseApply(value: unknown, memoryId: string, revision: number): MemoryCorrectionApplyResult | null {
  if (!isRecord(value) || !hasExactKeys(value, applyKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_correct_apply.v0" || value.status !== "applied" ||
    value.memory_id !== memoryId || value.prior_revision !== revision || value.result_revision !== revision + 1 ||
    !isOpaqueId(value.correction_id) || value.reconciled !== true || value.recovery_required !== false ||
    typeof value.idempotent_replay !== "boolean" || !isSafeText(value.applied_at, 128)
  ) return null;
  return value as unknown as MemoryCorrectionApplyResult;
}

function parseHistory(value: unknown, memoryId: string): MemoryCorrectionHistory | null {
  if (!isRecord(value) || !hasExactKeys(value, historyKeys)) return null;
  if (
    value.schema !== "relaylm.lab.memory_corrections.v0" || value.source !== "relaylm_runtime" ||
    value.read_only !== true || value.memory_id !== memoryId || !isPositiveInteger(value.current_revision) ||
    !isNonNegativeInteger(value.correction_count) || !isNullableSafeText(value.last_corrected_at, 128) ||
    !(value.last_correction_status === null || value.last_correction_status === "reconciled") ||
    typeof value.has_prior_revision !== "boolean" || !Array.isArray(value.items) || value.items.length > 50 ||
    value.items.length > value.correction_count
  ) return null;
  const items = value.items.map(parseHistoryItem);
  if (items.some((item) => item === null)) return null;
  return { ...value, items } as MemoryCorrectionHistory;
}

function parseHistoryItem(value: unknown): MemoryCorrectionHistoryItem | null {
  if (!isRecord(value) || !hasExactKeys(value, historyItemKeys)) return null;
  if (
    !isOpaqueId(value.correction_id) || !isPositiveInteger(value.prior_revision) ||
    value.result_revision !== value.prior_revision + 1 || !isSafeText(value.reason, 512) ||
    value.status !== "reconciled" || !isSafeText(value.applied_at, 128) ||
    typeof value.title_changed !== "boolean" || typeof value.summary_changed !== "boolean"
  ) return null;
  return value as unknown as MemoryCorrectionHistoryItem;
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

function isOpaqueId(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function isOpaqueToken(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && /^[A-Za-z0-9_.-]+$/.test(value);
}

function isNullableSafeText(value: unknown, maximum: number): value is string | null {
  return value === null || isSafeText(value, maximum);
}

function isSafeText(value: unknown, maximum: number, allowEmpty = false): value is string {
  if (typeof value !== "string" || value.length > maximum || (!allowEmpty && value.length === 0)) return false;
  return ![...value].some((character) => {
    const code = character.codePointAt(0) ?? 0;
    return code < 32 || code === 0x2028 || code === 0x2029 || (code >= 0xd800 && code <= 0xdfff);
  });
}
