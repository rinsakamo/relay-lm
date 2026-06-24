import type {
  ConversationCompletion,
  ConversationFailureReason,
  ConversationRequestSnapshot,
  ConversationStreamCompletion,
} from "./homeConversationTypes.js";
import { HOME_CONVERSATION_BOUNDS } from "./homeConversationState.js";

export class HomeConversationError extends Error {
  readonly reason: ConversationFailureReason;

  constructor(reason: ConversationFailureReason) {
    super(reason);
    this.name = "HomeConversationError";
    this.reason = reason;
  }
}

type FetchLike = typeof fetch;

export function buildChatCompletionsBody(snapshot: ConversationRequestSnapshot): {
  model: string;
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  stream: boolean;
} {
  if (
    snapshot.sourceMode !== "real" ||
    snapshot.routeModel.trim().length === 0 ||
    snapshot.messages.length === 0 ||
    snapshot.messages.length > HOME_CONVERSATION_BOUNDS.maxMessages
  ) {
    throw new HomeConversationError("invalid_request");
  }

  let transcriptChars = 0;
  const messages = snapshot.messages.map((message) => {
    if (
      (message.role !== "user" && message.role !== "assistant") ||
      typeof message.content !== "string" ||
      message.content.length === 0
    ) {
      throw new HomeConversationError("invalid_request");
    }
    const messageLimit =
      message.role === "user"
        ? HOME_CONVERSATION_BOUNDS.maxUserMessageChars
        : HOME_CONVERSATION_BOUNDS.maxResponseChars;
    if (message.content.length > messageLimit) {
      throw new HomeConversationError("invalid_request");
    }
    transcriptChars += message.content.length;
    if (transcriptChars > HOME_CONVERSATION_BOUNDS.maxTranscriptChars) {
      throw new HomeConversationError("invalid_request");
    }
    return { role: message.role, content: message.content };
  });

  const lastMessage = messages[messages.length - 1];
  if (!lastMessage || lastMessage.role !== "user" || lastMessage.content.trim().length === 0) {
    throw new HomeConversationError("invalid_request");
  }
  return { model: snapshot.routeModel, messages, stream: snapshot.stream };
}

export async function requestHomeConversation(
  snapshot: ConversationRequestSnapshot,
  signal: AbortSignal,
  fetchImpl: FetchLike = fetch,
): Promise<ConversationCompletion> {
  const response = await performRequest(snapshot, signal, fetchImpl, "application/json");
  const body = await readBoundedText(response, signal);
  let payload: unknown;
  try {
    payload = JSON.parse(body);
  } catch {
    throw new HomeConversationError("response_invalid");
  }
  return parseNonStreamCompletion(payload, responseCharacterLimit(snapshot));
}

export async function streamHomeConversation(
  snapshot: ConversationRequestSnapshot,
  signal: AbortSignal,
  onDelta: (delta: string) => void,
  fetchImpl: FetchLike = fetch,
): Promise<ConversationStreamCompletion> {
  const response = await performRequest(snapshot, signal, fetchImpl, "text/event-stream");
  if (!response.body) {
    throw new HomeConversationError("body_unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const visibleLimit = responseCharacterLimit(snapshot);
  let buffer = "";
  let byteCount = 0;
  let visibleCount = 0;
  let eventCount = 0;
  let doneSeen = false;
  let finishReason: string | null = null;
  let responseId: string | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (signal.aborted) throw new HomeConversationError("aborted");
      byteCount += value.byteLength;
      if (byteCount > HOME_CONVERSATION_BOUNDS.maxResponseBytes) {
        throw new HomeConversationError("response_too_large");
      }
      try {
        buffer += decoder.decode(value, { stream: true });
      } catch {
        throw new HomeConversationError("stream_invalid");
      }

      while (true) {
        const boundary = findEventBoundary(buffer);
        if (!boundary) break;
        const rawEvent = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary.length);
        if (rawEvent.trim().length === 0) continue;
        eventCount += 1;
        if (eventCount > HOME_CONVERSATION_BOUNDS.maxSseEvents) {
          throw new HomeConversationError("response_too_large");
        }
        const data = parseSseData(rawEvent);
        if (data === null) continue;
        if (data === "[DONE]") {
          doneSeen = true;
          continue;
        }
        if (doneSeen) throw new HomeConversationError("stream_invalid");

        let payload: unknown;
        try {
          payload = JSON.parse(data);
        } catch {
          throw new HomeConversationError("stream_invalid");
        }
        const parsed = parseStreamEvent(payload, responseId);
        responseId = parsed.responseId;
        if (parsed.finishReason !== null) finishReason = parsed.finishReason;
        if (parsed.delta.length > 0) {
          visibleCount += parsed.delta.length;
          if (visibleCount > visibleLimit) {
            throw new HomeConversationError("response_too_large");
          }
          onDelta(parsed.delta);
        }
      }
    }

    try {
      buffer += decoder.decode();
    } catch {
      throw new HomeConversationError("stream_invalid");
    }
    if (buffer.trim().length > 0) {
      throw new HomeConversationError("stream_truncated");
    }
    if (!doneSeen) {
      throw new HomeConversationError("stream_truncated");
    }
    return { finishReason, eventCount };
  } catch (error) {
    if (signal.aborted) throw new HomeConversationError("aborted");
    if (error instanceof HomeConversationError) throw error;
    throw new HomeConversationError("network_failure");
  } finally {
    reader.releaseLock();
  }
}

async function performRequest(
  snapshot: ConversationRequestSnapshot,
  signal: AbortSignal,
  fetchImpl: FetchLike,
  accept: string,
): Promise<Response> {
  let response: Response;
  try {
    response = await fetchImpl("/v1/chat/completions", {
      method: "POST",
      headers: {
        Accept: accept,
        "Content-Type": "application/json",
      },
      credentials: "same-origin",
      cache: "no-store",
      signal,
      body: JSON.stringify(buildChatCompletionsBody(snapshot)),
    });
  } catch (error) {
    if (error instanceof HomeConversationError) throw error;
    if (signal.aborted || (error instanceof DOMException && error.name === "AbortError")) {
      throw new HomeConversationError("aborted");
    }
    throw new HomeConversationError("network_failure");
  }
  if (!response.ok) {
    throw new HomeConversationError("http_failure");
  }
  return response;
}

async function readBoundedText(response: Response, signal: AbortSignal): Promise<string> {
  if (!response.body) throw new HomeConversationError("body_unavailable");
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let byteCount = 0;
  let result = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (signal.aborted) throw new HomeConversationError("aborted");
      byteCount += value.byteLength;
      if (byteCount > HOME_CONVERSATION_BOUNDS.maxResponseBytes) {
        throw new HomeConversationError("response_too_large");
      }
      try {
        result += decoder.decode(value, { stream: true });
      } catch {
        throw new HomeConversationError("response_invalid");
      }
    }
    try {
      result += decoder.decode();
    } catch {
      throw new HomeConversationError("response_invalid");
    }
  } catch (error) {
    if (signal.aborted) throw new HomeConversationError("aborted");
    if (error instanceof HomeConversationError) throw error;
    throw new HomeConversationError("network_failure");
  } finally {
    reader.releaseLock();
  }
  if (result.length > HOME_CONVERSATION_BOUNDS.maxResponseChars * 4) {
    throw new HomeConversationError("response_too_large");
  }
  return result;
}

function parseNonStreamCompletion(
  value: unknown,
  visibleLimit: number,
): ConversationCompletion {
  if (!isRecord(value) || !Array.isArray(value.choices) || value.choices.length === 0) {
    throw new HomeConversationError("response_invalid");
  }
  const choice = value.choices[0];
  if (!isRecord(choice) || !isRecord(choice.message) || typeof choice.message.content !== "string") {
    throw new HomeConversationError("response_invalid");
  }
  if (choice.message.content.length > visibleLimit) {
    throw new HomeConversationError("response_too_large");
  }
  const finishReason = choice.finish_reason;
  if (finishReason !== null && finishReason !== undefined && typeof finishReason !== "string") {
    throw new HomeConversationError("response_invalid");
  }
  return { text: choice.message.content, finishReason: finishReason ?? null };
}

function parseStreamEvent(
  value: unknown,
  expectedResponseId: string | null,
): { delta: string; finishReason: string | null; responseId: string | null } {
  if (!isRecord(value) || !Array.isArray(value.choices)) {
    throw new HomeConversationError("stream_invalid");
  }
  const responseId = value.id;
  if (responseId !== undefined && typeof responseId !== "string") {
    throw new HomeConversationError("stream_invalid");
  }
  if (expectedResponseId && responseId && responseId !== expectedResponseId) {
    throw new HomeConversationError("stream_invalid");
  }
  const resolvedResponseId =
    expectedResponseId ?? (typeof responseId === "string" ? responseId : null);
  if (value.choices.length === 0) {
    if (!isRecord(value.usage)) {
      throw new HomeConversationError("stream_invalid");
    }
    return { delta: "", finishReason: null, responseId: resolvedResponseId };
  }
  const choice = value.choices[0];
  if (!isRecord(choice) || !isRecord(choice.delta)) {
    throw new HomeConversationError("stream_invalid");
  }
  const role = choice.delta.role;
  if (role !== undefined && role !== "assistant") {
    throw new HomeConversationError("stream_invalid");
  }
  const content = choice.delta.content;
  if (content !== undefined && content !== null && typeof content !== "string") {
    throw new HomeConversationError("stream_invalid");
  }
  const finishReason = choice.finish_reason;
  if (finishReason !== null && finishReason !== undefined && typeof finishReason !== "string") {
    throw new HomeConversationError("stream_invalid");
  }
  return {
    delta: typeof content === "string" ? content : "",
    finishReason: finishReason ?? null,
    responseId: resolvedResponseId,
  };
}

function responseCharacterLimit(snapshot: ConversationRequestSnapshot): number {
  const requestCharacters = snapshot.messages.reduce(
    (total, message) => total + message.content.length,
    0,
  );
  return Math.min(
    HOME_CONVERSATION_BOUNDS.maxResponseChars,
    Math.max(0, HOME_CONVERSATION_BOUNDS.maxTranscriptChars - requestCharacters),
  );
}

function parseSseData(rawEvent: string): string | null {
  const dataLines: string[] = [];
  for (const line of rawEvent.split(/\r?\n/)) {
    if (line.startsWith(":")) continue;
    if (line === "data") {
      dataLines.push("");
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  return dataLines.length > 0 ? dataLines.join("\n") : null;
}

function findEventBoundary(value: string): { index: number; length: number } | null {
  const lf = value.indexOf("\n\n");
  const crlf = value.indexOf("\r\n\r\n");
  if (lf < 0 && crlf < 0) return null;
  if (lf < 0) return { index: crlf, length: 4 };
  if (crlf < 0) return { index: lf, length: 2 };
  return crlf < lf ? { index: crlf, length: 4 } : { index: lf, length: 2 };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
