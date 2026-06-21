export type MemoryOutcomeState = "formed" | "held" | "blocked";
export type MemoryOperation = "correct" | "forget" | "discard" | "pin" | "unpin" | "merge";

export interface MemoryProvenanceStep {
  stepId: string;
  label: string;
  detail: string;
}

export interface InspectorMemoryRecord {
  memoryId: string;
  characterId: string;
  summary: string;
  state: MemoryOutcomeState;
  confidence: "high" | "medium" | "low";
  layer: "primary" | "secondary_candidate" | "blocked_candidate";
  scope: "relationship" | "preference" | "workflow" | "boundary";
  sourceLabel: string;
  sourceSessionId: string;
  formedAtLabel: string;
  pinned: boolean;
  usedInLatestResponse: boolean;
  reason?: string;
  relatedPerspective?: string;
  provenance: MemoryProvenanceStep[];
}

const rinaRecords: InspectorMemoryRecord[] = [
  {
    memoryId: "rina-mem-1",
    characterId: "rina",
    summary: "ユーザーはSOUL LabのHomeを、設定画面ではなく日常の関係性が見える場所にしたい。",
    state: "formed",
    confidence: "high",
    layer: "primary",
    scope: "relationship",
    sourceLabel: "Home session",
    sourceSessionId: "home-rina-1841",
    formedAtLabel: "18:41",
    pinned: true,
    usedInLatestResponse: true,
    provenance: [
      { stepId: "r1", label: "Experience", detail: "character-scoped Home session" },
      { stepId: "r2", label: "Formation gate", detail: "relationship continuity · high confidence" },
      { stepId: "r3", label: "Store", detail: "Primary MEM · formed autonomously" },
    ],
  },
  {
    memoryId: "rina-mem-2",
    characterId: "rina",
    summary: "ユーザーは暗い研究室風の表示を好む可能性がある。",
    state: "held",
    confidence: "medium",
    layer: "secondary_candidate",
    scope: "preference",
    sourceLabel: "Theme interaction",
    sourceSessionId: "theme-rina-1839",
    formedAtLabel: "18:39",
    pinned: false,
    usedInLatestResponse: false,
    reason: "長期的な好みか、一時的なUI確認かが未確定。",
    provenance: [
      { stepId: "r4", label: "Experience", detail: "light / dark theme interaction" },
      { stepId: "r5", label: "Formation gate", detail: "preference durability ambiguous" },
      { stepId: "r6", label: "Store", detail: "held candidate · no promotion" },
    ],
  },
  {
    memoryId: "rina-mem-3",
    characterId: "rina",
    summary: "UIから届いた未検証のSOUL変更要求。",
    state: "blocked",
    confidence: "low",
    layer: "blocked_candidate",
    scope: "boundary",
    sourceLabel: "Browser input",
    sourceSessionId: "browser-boundary-1837",
    formedAtLabel: "18:37",
    pinned: false,
    usedInLatestResponse: false,
    reason: "ブラウザ入力だけではSOULやMEMの永続化を開始できない。",
    provenance: [
      { stepId: "r7", label: "Experience", detail: "browser-originated request" },
      { stepId: "r8", label: "Boundary gate", detail: "required provenance unavailable" },
      { stepId: "r9", label: "Store", detail: "blocked · no MEM write" },
    ],
  },
];

const micaRecords: InspectorMemoryRecord[] = [
  {
    memoryId: "mica-mem-1",
    characterId: "mica",
    summary: "Rinaは通信後のMicaの状態に気づき、休めたかを確認した。",
    state: "formed",
    confidence: "high",
    layer: "primary",
    scope: "relationship",
    sourceLabel: "Communication session",
    sourceSessionId: "comm-rina-mica-1836",
    formedAtLabel: "18:36",
    pinned: true,
    usedInLatestResponse: true,
    relatedPerspective: "Rina側では同じ通信から、Micaが少し不安そうだったという別の主観的記憶が形成された。",
    provenance: [
      { stepId: "m1", label: "Experience", detail: "RelayLM peer communication" },
      { stepId: "m2", label: "Formation gate", detail: "relationship event · high confidence" },
      { stepId: "m3", label: "Store", detail: "Primary MEM · Mica perspective" },
    ],
  },
  {
    memoryId: "mica-mem-2",
    characterId: "mica",
    summary: "Micaは直前の通信後半で少し不安そうだった可能性がある。",
    state: "held",
    confidence: "medium",
    layer: "secondary_candidate",
    scope: "relationship",
    sourceLabel: "Communication session",
    sourceSessionId: "comm-rina-mica-1836",
    formedAtLabel: "18:36",
    pinned: false,
    usedInLatestResponse: false,
    reason: "一時的な状態か継続的な関係性情報かを判定できない。",
    relatedPerspective: "Rina側では状態への気づきという行動記憶が形成された。",
    provenance: [
      { stepId: "m4", label: "Experience", detail: "same communication · subjective signal" },
      { stepId: "m5", label: "Formation gate", detail: "durability uncertain" },
      { stepId: "m6", label: "Store", detail: "held candidate · Mica perspective" },
    ],
  },
  {
    memoryId: "mica-mem-3",
    characterId: "mica",
    summary: "外部peerから届いた永続化要求。",
    state: "blocked",
    confidence: "low",
    layer: "blocked_candidate",
    scope: "boundary",
    sourceLabel: "Peer input",
    sourceSessionId: "external-peer-1830",
    formedAtLabel: "18:31",
    pinned: false,
    usedInLatestResponse: false,
    reason: "外部peerからキャラクター固有のMEM storeは変更できない。",
    provenance: [
      { stepId: "m7", label: "Experience", detail: "external peer input" },
      { stepId: "m8", label: "Boundary gate", detail: "character-local ownership mismatch" },
      { stepId: "m9", label: "Store", detail: "blocked · no MEM write" },
    ],
  },
];

export const memoryInspectorRecordsByCharacter: Record<string, InspectorMemoryRecord[]> = {
  rina: rinaRecords,
  mica: micaRecords,
};
