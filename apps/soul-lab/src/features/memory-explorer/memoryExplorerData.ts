import type { MemoryExplorerRecord, MemoryKind } from "./memoryExplorerTypes";

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;
const sessionRecords = new Map<string, MemoryExplorerRecord[]>();

function stableHash(value: string): string {
  let hash = 2166136261;
  for (const character of value) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36);
}

function idPrefix(characterId: string): string {
  const readable = characterId
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 20) || "character";
  return `${readable}-${stableHash(characterId)}`;
}

function instant(now: number, ageMs: number): { label: string; value: string } {
  const value = new Date(now - ageMs).toISOString();
  return { value, label: value.slice(0, 16).replace("T", " ") };
}

function record(
  characterId: string,
  prefix: string,
  index: number,
  now: number,
  options: {
    summary: string;
    content: string;
    kind: MemoryKind;
    userTags?: string[];
    systemTags: string[];
    subject: string;
    formedAgeMs: number;
    usedAgeMs?: number;
    confidence: MemoryExplorerRecord["confidence"];
    provenanceAvailability: MemoryExplorerRecord["provenanceAvailability"];
    status?: MemoryExplorerRecord["status"];
    relatedIndexes?: number[];
    pinned?: boolean;
    tombstoned?: boolean;
  },
): MemoryExplorerRecord {
  const formed = instant(now, options.formedAgeMs);
  const used = options.usedAgeMs === undefined ? null : instant(now, options.usedAgeMs);
  const memoryId = `${prefix}-exp-${String(index).padStart(3, "0")}`;
  const status = options.status ?? "active";
  const tombstoned = options.tombstoned ?? status === "hidden";
  return {
    memoryId,
    characterId,
    summary: options.summary,
    content: options.content,
    kind: options.kind,
    userTags: options.userTags ?? [],
    systemTags: options.systemTags,
    subject: options.subject,
    formedAtLabel: formed.label,
    formedAtValue: formed.value,
    latestUseLabel: used?.label ?? null,
    latestUseValue: used?.value ?? null,
    confidence: options.confidence,
    provenanceAvailability: options.provenanceAvailability,
    status,
    relatedMemoryIds: (options.relatedIndexes ?? []).map(
      (relatedIndex) => `${prefix}-exp-${String(relatedIndex).padStart(3, "0")}`,
    ),
    provenance: [
      { stepId: `${memoryId}-source`, label: "Experience", detail: "character-scoped mock session" },
      { stepId: `${memoryId}-gate`, label: "Formation gate", detail: `${options.kind} signal · ${options.confidence} confidence` },
      { stepId: `${memoryId}-store`, label: "Store", detail: "Primary MEM · browser-local fixture" },
    ],
    usageTimeline: [
      ...(used
        ? [
            {
              eventId: `${memoryId}-used`,
              occurredAtLabel: used.label,
              occurredAtValue: used.value,
              detail: "used in a recent mock response",
            },
          ]
        : []),
      {
        eventId: `${memoryId}-formed`,
        occurredAtLabel: formed.label,
        occurredAtValue: formed.value,
        detail: "formed",
      },
    ],
    pinned: options.pinned ?? false,
    tombstoned,
    tombstoneAtLabel: tombstoned ? instant(now, Math.max(options.formedAgeMs - HOUR_MS, 0)).label : null,
  };
}

export function createMemoryExplorerRecordsForCharacter(
  characterId: string,
  displayName: string,
  now: number = Date.now(),
): MemoryExplorerRecord[] {
  const prefix = idPrefix(characterId);
  const name = displayName.trim() || characterId;
  return [
    record(characterId, prefix, 1, now, {
      summary: `ユーザーは${name}との日常的な関係性が自然に続くHomeを望んでいる。`,
      content: `ユーザーは、管理画面を眺めるよりも${name}と過ごす日常の延長としてHomeを感じたいと話した。形成済みmemoryの探索は関係性を壊さない補助機能として扱う。`,
      kind: "relationship",
      userTags: ["大切な話", "継続"],
      systemTags: ["relationship_continuity"],
      subject: name,
      formedAgeMs: 6 * HOUR_MS,
      usedAgeMs: 90 * 60 * 1000,
      confidence: "high",
      provenanceAvailability: "available",
      relatedIndexes: [2, 6],
      pinned: true,
    }),
    record(characterId, prefix, 2, now, {
      summary: "ユーザーは暗い表示を好む可能性がある。",
      content: "テーマ切り替え時の滞在時間から得たpreference候補。継続的な好みか一時的な確認かは断定されていない。",
      kind: "preference",
      userTags: ["ダーク推し"],
      systemTags: ["preference_signal"],
      subject: "UI テーマ",
      formedAgeMs: 30 * HOUR_MS,
      usedAgeMs: 10 * HOUR_MS,
      confidence: "medium",
      provenanceAvailability: "partial",
      relatedIndexes: [1, 3],
    }),
    record(characterId, prefix, 3, now, {
      summary: "Homeでの短い雑談セッションが記録された。",
      content: "特定の議題を持たない短い雑談。会話の流れ自体が日常の一部として形成された。",
      kind: "episodic",
      systemTags: ["session_event"],
      subject: "Home 会話",
      formedAgeMs: 52 * HOUR_MS,
      confidence: "medium",
      provenanceAvailability: "available",
      relatedIndexes: [2],
    }),
    record(characterId, prefix, 4, now, {
      summary: "検索の進め方についての手順メモ。",
      content: "まずキーワードで候補を確認し、その後にタグと日付で絞り込むという手順がprocedural memoryとして形成された。",
      kind: "procedural",
      userTags: ["手順メモ"],
      systemTags: ["workflow_note"],
      subject: "検索フロー",
      formedAgeMs: 8 * DAY_MS,
      usedAgeMs: 7 * DAY_MS,
      confidence: "low",
      provenanceAvailability: "unavailable",
    }),
    record(characterId, prefix, 5, now, {
      summary: "明示的なForget確認により通常検索から除外された境界ケース。",
      content: "境界確認用に形成された後、ユーザーが明示的にForgetを確認したためhidden状態になっている。",
      kind: "boundary",
      systemTags: ["boundary_case"],
      subject: "境界確認",
      formedAgeMs: 15 * DAY_MS,
      confidence: "low",
      provenanceAvailability: "unavailable",
      status: "hidden",
      tombstoned: true,
    }),
    record(characterId, prefix, 6, now, {
      summary: `ユーザーから${name}への感謝が関係性memoryとして形成された。`,
      content: `ユーザーが${name}に感謝を伝えた場面。関係性継続の観点で高信頼のmemoryとして形成された。`,
      kind: "relationship",
      userTags: ["感謝"],
      systemTags: ["relationship_continuity"],
      subject: name,
      formedAgeMs: 24 * DAY_MS,
      usedAgeMs: 23 * DAY_MS,
      confidence: "high",
      provenanceAvailability: "available",
      relatedIndexes: [1],
    }),
    record(characterId, prefix, 7, now, {
      summary: "以前の旅行について話した思い出のやり取り。",
      content: "ユーザーが以前の旅行について語った内容。継続的な利用実績はまだないが、思い出として形成された。",
      kind: "episodic",
      userTags: ["思い出"],
      systemTags: ["session_event"],
      subject: "旅行の話",
      formedAgeMs: 60 * DAY_MS,
      confidence: "medium",
      provenanceAvailability: "partial",
    }),
  ];
}

function clone(records: MemoryExplorerRecord[]): MemoryExplorerRecord[] {
  return structuredClone(records);
}

export function getMemoryExplorerSessionRecords(characterId: string, displayName: string): MemoryExplorerRecord[] {
  const existing = sessionRecords.get(characterId);
  if (existing) return clone(existing);
  const created = createMemoryExplorerRecordsForCharacter(characterId, displayName);
  sessionRecords.set(characterId, clone(created));
  return created;
}

export function saveMemoryExplorerSessionRecords(characterId: string, records: MemoryExplorerRecord[]): void {
  if (records.some((record) => record.characterId !== characterId)) {
    throw new Error(`Memory Explorer session data escaped character scope: ${characterId}`);
  }
  sessionRecords.set(characterId, clone(records));
}

export function resetMemoryExplorerSessionRecords(characterId?: string): void {
  if (characterId) sessionRecords.delete(characterId);
  else sessionRecords.clear();
}

export const memoryExplorerRecordsByCharacter: Record<string, MemoryExplorerRecord[]> = {
  rina: createMemoryExplorerRecordsForCharacter("rina", "Rina"),
  mica: createMemoryExplorerRecordsForCharacter("mica", "Mica"),
};

export const memoryKinds = ["episodic", "preference", "relationship", "procedural", "boundary"] as const;
