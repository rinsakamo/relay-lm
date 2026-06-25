export type ConversationSourceMode = "real" | "preview";
export type ConversationRequestState =
  | "idle"
  | "submitting"
  | "streaming"
  | "completed"
  | "stopped"
  | "failed";
export type ConversationFailureReason =
  | "unavailable"
  | "ambiguous_route"
  | "invalid_request"
  | "http_failure"
  | "timeout"
  | "response_invalid"
  | "response_too_large"
  | "stream_invalid"
  | "stream_truncated"
  | "body_unavailable"
  | "aborted"
  | "network_failure";
export type ConversationMessageStatus =
  | "complete"
  | "pending"
  | "streaming"
  | "stopped"
  | "failed";

export interface ConversationMessage {
  messageId: string;
  role: "user" | "assistant";
  content: string;
  status: ConversationMessageStatus;
  occurredAtLabel: string;
  failureReason?: ConversationFailureReason;
}

export interface WireConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ConversationRequestSnapshot {
  requestId: string;
  characterId: string;
  routeModel: string;
  sessionId: string;
  generation: number;
  sourceMode: "real";
  stream: boolean;
  messages: WireConversationMessage[];
  assistantMessageId: string;
}

export interface ConversationSession {
  sessionId: string;
  generation: number;
  sourceMode: ConversationSourceMode;
  requestState: ConversationRequestState;
  messages: ConversationMessage[];
  draft: string;
  lastRequest: ConversationRequestSnapshot | null;
}

export interface ConversationTargetAvailable {
  status: "available";
  characterId: string;
  routeModel: string;
}

export interface ConversationTargetUnavailable {
  status: "unavailable" | "ambiguous_route";
  characterId: string;
}

export type ConversationTarget = ConversationTargetAvailable | ConversationTargetUnavailable;

export interface ConversationCompletion {
  text: string;
  finishReason: string | null;
}

export interface ConversationStreamCompletion {
  finishReason: string | null;
  eventCount: number;
}
