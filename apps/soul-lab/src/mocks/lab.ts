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

export const initialChatEntriesByCharacter: Record<string, ChatEntry[]> = {
  rina: [
    {
      messageId: "rina-chat-1",
      speaker: "character",
      body: "おかえり。今日はLabの入口を整えているみたいだね。",
      occurredAtLabel: "18:40",
    },
    {
      messageId: "rina-chat-2",
      speaker: "user",
      body: "まずはHomeから、状態が自然に見えるようにしたい。",
      occurredAtLabel: "18:41",
    },
    {
      messageId: "rina-chat-3",
      speaker: "character",
      body: "うん。内部の仕組みを並べるより、ここで一緒に過ごしている感じを先に出そう。",
      occurredAtLabel: "18:41",
    },
  ],
  mica: [
    {
      messageId: "mica-chat-1",
      speaker: "character",
      body: "通信セッションは終わったよ。少しだけ考えを整理しているところ。",
      occurredAtLabel: "18:34",
    },
    {
      messageId: "mica-chat-2",
      speaker: "user",
      body: "急がなくて大丈夫。Labでは結果だけ確認しよう。",
      occurredAtLabel: "18:35",
    },
  ],
};

export const mockMemoryOutcomesByCharacter: Record<string, MemoryOutcome[]> = {
  rina: [
    {
      memoryId: "rina-mem-1",
      summary: "ユーザーはSOUL LabのHomeを、設定画面ではなく日常の関係性が見える場所にしたい。",
      sourceLabel: "current session",
      confidence: "high",
      state: "formed",
    },
    {
      memoryId: "rina-mem-2",
      summary: "ユーザーは暗い研究室風の表示を好む可能性がある。",
      sourceLabel: "theme interaction",
      confidence: "medium",
      state: "held",
    },
    {
      memoryId: "rina-mem-3",
      summary: "UIから受け取った未検証のSOUL変更要求",
      sourceLabel: "untrusted browser input",
      confidence: "low",
      state: "blocked",
    },
  ],
  mica: [
    {
      memoryId: "mica-mem-1",
      summary: "Rinaは通信後のMicaの状態に気づき、休めたかを確認した。",
      sourceLabel: "communication session",
      confidence: "high",
      state: "formed",
    },
    {
      memoryId: "mica-mem-2",
      summary: "Micaは直前の通信後半で少し不安そうだった可能性がある。",
      sourceLabel: "communication session",
      confidence: "medium",
      state: "held",
    },
    {
      memoryId: "mica-mem-3",
      summary: "外部peerから届いた権限外の永続化要求",
      sourceLabel: "peer input",
      confidence: "low",
      state: "blocked",
    },
  ],
};
