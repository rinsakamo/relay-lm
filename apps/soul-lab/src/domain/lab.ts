export type CharacterStatus = "online" | "offline" | "degraded";
export type ConnectionState = "connected" | "disconnected" | "degraded" | "unconfigured";
export type InterventionState = "inactive" | "active" | "ending";
export type Severity = "info" | "warning" | "error";
export type Theme = "light" | "dark";
export type Language = "ja" | "en";
export type LabRoute =
  | "home"
  | "observation"
  | "communication"
  | "pod"
  | "adoption";

export interface CharacterSummary {
  characterId: string;
  displayName: string;
  initials: string;
  status: CharacterStatus;
  sceneName: string;
  soulVersion: string;
  stabilityLabel: string;
  interventionState: InterventionState;
  lastActiveLabel: string;
}

export interface RuntimeComponentStatus {
  componentId: "relaylm" | "backend" | "tts" | "avatar";
  state: ConnectionState;
  detail: string;
}

export interface LabEvent {
  eventId: string;
  category: "runtime" | "memory" | "communication" | "intervention";
  severity: Severity;
  summary: string;
  occurredAtLabel: string;
}

export interface ChatEntry {
  messageId: string;
  speaker: "character" | "user" | "system";
  body: string;
  occurredAtLabel: string;
}

export interface MemoryOutcome {
  memoryId: string;
  summary: string;
  sourceLabel: string;
  confidence: "high" | "medium" | "low";
  state: "formed" | "held" | "blocked";
}
