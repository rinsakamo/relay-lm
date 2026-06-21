import type {
  CharacterSummary,
  ChatEntry,
  LabEvent,
  MemoryOutcome,
  RuntimeComponentStatus,
} from "../domain/lab";

export const mockCharacters: CharacterSummary[] = [
  {
    characterId: "rina",
    displayName: "Rina",
    initials: "RI",
    status: "online",
    sceneName: "quiet_room",
    soulVersion: "v3",
    stabilityLabel: "Stable",
    interventionState: "inactive",
    lastActiveSeconds: 12,
  },
  {
    characterId: "mica",
    displayName: "Mica",
    initials: "MI",
    status: "degraded",
    sceneName: "after_stream",
    soulVersion: "v2",
    stabilityLabel: "Observing",
    interventionState: "inactive",
    lastActiveSeconds: 480,
  },
];

export const mockRuntimeComponents: RuntimeComponentStatus[] = [
  {
    componentId: "relaylm",
    state: "connected",
    detail: "127.0.0.1:8090",
  },
  {
    componentId: "backend",
    state: "connected",
    detail: "LM Studio · qwen3.5-9b",
  },
  {
    componentId: "tts",
    state: "unconfigured",
    detail: "Runtime MVP adapter boundary",
  },
  {
    componentId: "avatar",
    state: "unconfigured",
    detail: "Runtime MVP adapter boundary",
  },
];

export const mockEvents: LabEvent[] = [
  {
    eventId: "event-1",
    category: "runtime",
    severity: "info",
    summary: "Managed route completed without recovery",
    occurredAtLabel: "18:42",
  },
  {
    eventId: "event-2",
    category: "memory",
    severity: "info",
    summary: "Primary MEM candidate formed",
    occurredAtLabel: "18:41",
  },
  {
    eventId: "event-3",
    category: "communication",
    severity: "warning",
    summary: "Peer session ended with Soft Stop",
    occurredAtLabel: "18:36",
  },
];

export const initialChatEntries: ChatEntry[] = [
  {
    messageId: "chat-1",
    speaker: "character",
    body: "おかえり。今日はLabの入口を整えているみたいだね。",
    occurredAtLabel: "18:40",
  },
  {
    messageId: "chat-2",
    speaker: "user",
    body: "まずはHomeから、状態が自然に見えるようにしたい。",
    occurredAtLabel: "18:41",
  },
  {
    messageId: "chat-3",
    speaker: "character",
    body: "うん。内部の仕組みを並べるより、ここで一緒に過ごしている感じを先に出そう。",
    occurredAtLabel: "18:41",
  },
];

export const mockMemoryOutcomes: MemoryOutcome[] = [
  {
    memoryId: "mem-1",
    summary: "ユーザーはSOUL LabのHomeを、設定画面ではなく日常の関係性が見える場所にしたい。",
    sourceLabel: "current session",
    confidence: "high",
    state: "formed",
  },
  {
    memoryId: "mem-2",
    summary: "Micaは直前の通信後半で少し不安そうだった可能性がある。",
    sourceLabel: "communication session",
    confidence: "medium",
    state: "held",
  },
  {
    memoryId: "mem-3",
    summary: "UIから受け取った未検証のSOUL変更要求",
    sourceLabel: "untrusted browser input",
    confidence: "low",
    state: "blocked",
  },
];
