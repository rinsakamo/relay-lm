import type { LabCharacterProjection } from "../settings/managementApi.js";
import type {
  ConversationMessage,
  ConversationRequestSnapshot,
  ConversationSession,
  ConversationSourceMode,
  ConversationTarget,
  WireConversationMessage,
} from "./homeConversationTypes.js";

export const HOME_CONVERSATION_BOUNDS = Object.freeze({
  maxMessages: 40,
  maxUserMessageChars: 8_000,
  maxTranscriptChars: 64_000,
  maxResponseChars: 32_000,
  maxResponseBytes: 1_048_576,
  maxSseEvents: 2_048,
  requestTimeoutMs: 120_000,
});

export function conversationSessionKey(
  characterId: string,
  sourceMode: ConversationSourceMode,
): string {
  return `${characterId}\u0000${sourceMode}`;
}

export function createConversationSession(
  sourceMode: ConversationSourceMode,
  sessionId: string = crypto.randomUUID(),
): ConversationSession {
  return {
    sessionId,
    generation: 0,
    sourceMode,
    requestState: "idle",
    messages: [],
    draft: "",
    lastRequest: null,
  };
}

export function resetConversationSession(
  current: ConversationSession,
  sessionId: string = crypto.randomUUID(),
): ConversationSession {
  return {
    ...createConversationSession(current.sourceMode, sessionId),
    generation: current.generation + 1,
  };
}

export function resolveConversationTarget(
  projection: LabCharacterProjection | null,
  characterId: string,
): ConversationTarget {
  if (!projection || projection.character_id !== characterId) {
    return { status: "unavailable", characterId };
  }
  const routes = [...new Set(projection.route_models.filter((value) => value.trim().length > 0))];
  if (routes.length === 0) {
    return { status: "unavailable", characterId };
  }
  if (routes.length !== 1) {
    return { status: "ambiguous_route", characterId };
  }
  return { status: "available", characterId, routeModel: routes[0] as string };
}

export function toWireHistory(messages: readonly ConversationMessage[]): WireConversationMessage[] {
  return messages
    .filter((message) => message.status === "complete")
    .map((message) => ({ role: message.role, content: message.content }));
}

export function transcriptCharacterCount(messages: readonly ConversationMessage[]): number {
  return messages.reduce((total, message) => total + message.content.length, 0);
}

export function requestSnapshotMatches(
  snapshot: ConversationRequestSnapshot,
  current: {
    characterId: string;
    sessionId: string;
    generation: number;
    routeModel: string;
  },
): boolean {
  return (
    snapshot.characterId === current.characterId &&
    snapshot.sessionId === current.sessionId &&
    snapshot.generation === current.generation &&
    snapshot.routeModel === current.routeModel
  );
}

export function isRequestActive(state: ConversationSession["requestState"]): boolean {
  return state === "submitting" || state === "streaming";
}
