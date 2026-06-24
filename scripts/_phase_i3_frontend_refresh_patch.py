"""Temporary exact-source patch for Phase I-3 frontend refresh semantics."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one exact match, found {count}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


def replace_exact_count(path: str, old: str, new: str, expected: int) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    count = body.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} exact matches, found {count}")
    target.write_text(body.replace(old, new), encoding="utf-8")


replace_exact_count(
    "apps/soul-lab/src/features/lab/correctionApi.ts",
    '''  if (!response.ok) throw httpError(response.status);\n''',
    '''  if (!response.ok) throw await httpError(response);\n''',
    2,
)

replace_once(
    "apps/soul-lab/src/features/lab/correctionApi.ts",
    '''function httpError(status: number): MemoryCorrectionError {\n  const code = status === 403 ? "access_refused"\n    : status === 404 ? "not_found_or_wrong_scope"\n    : status === 409 ? "conflict"\n    : status === 415 || status === 422 ? "invalid_request"\n    : status === 503 ? "reconciliation_required"\n    : "runtime_unavailable";\n  return new MemoryCorrectionError(code);\n}\n''',
    '''const boundedServerErrorCodes = new Set([\n  "invalid_request",\n  "not_found_or_wrong_scope",\n  "stale_revision",\n  "operation_conflict",\n  "preflight_required",\n  "token_expired",\n  "token_invalid",\n  "target_corrupt",\n  "reconciliation_required",\n  "store_unavailable",\n  "access_refused",\n  "response_lost",\n]);\n\nasync function httpError(response: Response): Promise<MemoryCorrectionError> {\n  try {\n    const value: unknown = await response.json();\n    if (\n      isRecord(value) &&\n      hasExactKeys(value, ["detail"]) &&\n      typeof value.detail === "string" &&\n      boundedServerErrorCodes.has(value.detail)\n    ) {\n      return new MemoryCorrectionError(value.detail);\n    }\n  } catch {\n    // Fall back to the bounded status mapping below.\n  }\n  const status = response.status;\n  const code = status === 403 ? "access_refused"\n    : status === 404 ? "not_found_or_wrong_scope"\n    : status === 409 ? "conflict"\n    : status === 415 || status === 422 ? "invalid_request"\n    : status === 503 ? "reconciliation_required"\n    : "runtime_unavailable";\n  return new MemoryCorrectionError(code);\n}\n''',
)

replace_once(
    "apps/soul-lab/src/features/lab/PrimaryMemoryCorrectPanel.tsx",
    '''function codeFor(error: unknown): string {\n  return error instanceof MemoryCorrectionError ? error.code : "runtime_unavailable";\n}\n''',
    '''function codeFor(error: unknown): string {\n  return error instanceof MemoryCorrectionError ? error.code : "runtime_unavailable";\n}\n\nfunction requiresCurrentMemoryRefresh(code: string): boolean {\n  return code === "stale_revision" || code === "operation_conflict";\n}\n''',
)

replace_once(
    "apps/soul-lab/src/features/lab/PrimaryMemoryCorrectPanel.tsx",
    '''  }, [characterId, namespace, memory.memory_id, memory.title, memory.bounded_summary]);\n''',
    '''  }, [characterId, namespace, memory.memory_id, memory.revision, memory.title, memory.bounded_summary]);\n''',
)

replace_exact_count(
    "apps/soul-lab/src/features/lab/PrimaryMemoryCorrectPanel.tsx",
    '''      if (generation.current === currentGeneration) {\n        setState({ kind: "error", code: codeFor(error) });\n      }\n''',
    '''      if (generation.current === currentGeneration) {\n        const code = codeFor(error);\n        setState({ kind: "error", code });\n        if (requiresCurrentMemoryRefresh(code)) onApplied();\n      }\n''',
    2,
)

replace_once(
    "apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx",
    '''  const generation = useRef(0);\n\n  useEffect(() => {\n    onInspectorLockChange(false);\n    setMockFallback(false);\n    setSelectedMemory(null);\n''',
    '''  const generation = useRef(0);\n\n  useEffect(() => {\n    setSelectedMemory(null);\n  }, [activeCharacter.characterId]);\n\n  useEffect(() => {\n    onInspectorLockChange(false);\n    setMockFallback(false);\n''',
)

replace_once(
    "apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx",
    '''        if (!controller.signal.aborted && generation.current === requestGeneration) {\n          setState({ kind: "real", namespace, bundle });\n        }\n''',
    '''        if (!controller.signal.aborted && generation.current === requestGeneration) {\n          setSelectedMemory((current) =>\n            current === null\n              ? null\n              : bundle.recent.items.find(\n                  (item) => item.memory_id === current.memory_id,\n                ) ?? null,\n          );\n          setState({ kind: "real", namespace, bundle });\n        }\n''',
)

replace_once(
    "apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx",
    '''          onApplied={() => {\n            setSelectedMemory(null);\n            setRefreshKey((value) => value + 1);\n          }}\n''',
    '''          onApplied={() => {\n            setRefreshKey((value) => value + 1);\n          }}\n''',
)

replace_once(
    "apps/soul-lab/scripts/correctionApiSmoke.mjs",
    '''globalThis.fetch = async () => new Response("{}", { status: 403 });\n''',
    '''globalThis.fetch = async () => new Response(\n  JSON.stringify({ detail: "stale_revision" }),\n  { status: 409, headers: { "content-type": "application/json" } },\n);\nawait assert.rejects(\n  preflightMemoryCorrection(characterId, namespace, memoryId, {\n    expectedRevision: 1, correctedTitle: "x", correctedSummary: "y", reason: "z", operationId: "op",\n  }),\n  (error) => error instanceof MemoryCorrectionError && error.code === "stale_revision",\n);\n\nglobalThis.fetch = async () => new Response("{}", { status: 403 });\n''',
)

replace_once(
    "apps/soul-lab/scripts/correctionApiSmoke.mjs",
    '''assert.match(panelSource, /state\\.kind === "apply-loading"/);\nassert.match(panelSource, /Confirm apply/);\n''',
    '''assert.match(panelSource, /state\\.kind === "apply-loading"/);\nassert.match(panelSource, /requiresCurrentMemoryRefresh/);\nassert.match(panelSource, /code === "stale_revision"/);\nassert.match(panelSource, /code === "operation_conflict"/);\nassert.match(connectedSource, /setSelectedMemory\\(\\(current\\) =>/);\nassert.doesNotMatch(connectedSource, /onApplied=.*setSelectedMemory\\(null\\)/s);\nassert.match(panelSource, /Confirm apply/);\n''',
)

print("Phase I-3 frontend refresh semantics patch applied")
