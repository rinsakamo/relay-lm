import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const sourceRoot = new URL("../src/features/home/", import.meta.url);
const temp = await mkdtemp(join(tmpdir(), "relaylm-home-conversation-"));

async function emit(name) {
  const source = await readFile(new URL(name, sourceRoot), "utf8");
  const result = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ES2022,
      strict: true,
    },
    fileName: name,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter(
    (diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error,
  );
  assert.equal(errors.length, 0, `transpile diagnostics in ${name}`);
  await writeFile(join(temp, name.replace(/\.ts$/, ".js")), result.outputText, "utf8");
}

try {
  await mkdir(temp, { recursive: true });
  await writeFile(join(temp, "package.json"), '{"type":"module"}\n', "utf8");
  await emit("homeConversationTypes.ts");
  await emit("homeConversationState.ts");
  await emit("homeConversationApi.ts");

  const api = await import(pathToFileURL(join(temp, "homeConversationApi.js")).href);
  const state = await import(pathToFileURL(join(temp, "homeConversationState.js")).href);

  const baseSnapshot = {
    requestId: "request-1",
    characterId: "alice",
    routeModel: "alice-route",
    sessionId: "session-1",
    generation: 1,
    sourceMode: "real",
    stream: false,
    messages: [{ role: "user", content: "hello" }],
    assistantMessageId: "assistant-1",
  };

  const exactBody = api.buildChatCompletionsBody(baseSnapshot);
  assert.deepEqual(exactBody, {
    model: "alice-route",
    messages: [{ role: "user", content: "hello" }],
    stream: false,
  });
  assert.equal("characterId" in exactBody, false);
  assert.equal("memory_namespace" in exactBody, false);
  assert.equal("backend_id" in exactBody, false);
  assert.equal("system" in exactBody, false);

  async function expectReason(promise, reason) {
    await assert.rejects(promise, (error) => {
      assert.equal(error.name, "HomeConversationError");
      assert.equal(error.reason, reason);
      assert.equal(String(error.message).includes("secret backend body"), false);
      return true;
    });
  }

  for (const invalidSnapshot of [
    { ...baseSnapshot, sourceMode: "preview" },
    { ...baseSnapshot, messages: [{ role: "user", content: "   " }] },
    { ...baseSnapshot, messages: [{ role: "assistant", content: "not-final-user" }] },
    {
      ...baseSnapshot,
      messages: [
        {
          role: "user",
          content: "x".repeat(state.HOME_CONVERSATION_BOUNDS.maxUserMessageChars + 1),
        },
      ],
    },
    {
      ...baseSnapshot,
      messages: [
        {
          role: "assistant",
          content: "x".repeat(state.HOME_CONVERSATION_BOUNDS.maxResponseChars),
        },
        {
          role: "assistant",
          content: "y".repeat(state.HOME_CONVERSATION_BOUNDS.maxResponseChars),
        },
        { role: "user", content: "z" },
      ],
    },
  ]) {
    await expectReason(
      Promise.resolve().then(() => api.buildChatCompletionsBody(invalidSnapshot)),
      "invalid_request",
    );
  }

  const capture = {};
  const validFetch = async (url, init) => {
    capture.url = url;
    capture.init = init;
    return new Response(
      JSON.stringify({
        id: "chatcmpl-1",
        choices: [{ message: { role: "assistant", content: "world" }, finish_reason: "stop" }],
        usage: { total_tokens: 2 },
        relay_extension: { safe_optional: true },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };
  const completion = await api.requestHomeConversation(
    baseSnapshot,
    new AbortController().signal,
    validFetch,
  );
  assert.deepEqual(completion, { text: "world", finishReason: "stop" });
  assert.equal(capture.url, "/v1/chat/completions");
  assert.equal(capture.init.credentials, "same-origin");
  assert.equal(capture.init.cache, "no-store");
  assert.equal(capture.init.headers.Authorization, undefined);
  assert.equal(capture.init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(capture.init.body), exactBody);

  const jsonResponse = (payload, status = 200) =>
    async () => new Response(typeof payload === "string" ? payload : JSON.stringify(payload), { status });
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, jsonResponse({})),
    "response_invalid",
  );
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, jsonResponse({ choices: [null] })),
    "response_invalid",
  );
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, jsonResponse({ choices: [{ message: { content: 7 } }] })),
    "response_invalid",
  );
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, jsonResponse("secret backend body", 500)),
    "http_failure",
  );
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, jsonResponse("{malformed")),
    "response_invalid",
  );
  await expectReason(
    api.requestHomeConversation(baseSnapshot, new AbortController().signal, async () => new Response(null, { status: 200 })),
    "body_unavailable",
  );
  await expectReason(
    api.requestHomeConversation(
      baseSnapshot,
      new AbortController().signal,
      jsonResponse({ choices: [{ message: { content: "x".repeat(state.HOME_CONVERSATION_BOUNDS.maxResponseChars + 1) } }] }),
    ),
    "response_too_large",
  );
  const aborted = new AbortController();
  aborted.abort();
  await expectReason(
    api.requestHomeConversation(baseSnapshot, aborted.signal, async () => {
      throw new DOMException("secret backend body", "AbortError");
    }),
    "aborted",
  );

  function streamResponse(chunks, captureTarget = null) {
    return async (url, init) => {
      if (captureTarget) {
        captureTarget.url = url;
        captureTarget.init = init;
      }
      return new Response(
        new ReadableStream({
          start(controller) {
            for (const chunk of chunks) controller.enqueue(chunk);
            controller.close();
          },
        }),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    };
  }

  const encoder = new TextEncoder();
  const streamSnapshot = { ...baseSnapshot, stream: true };
  const eventText =
    'data: {"id":"r1","choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}\n\n' +
    'data: {"id":"r1","choices":[{"delta":{"content":""},"finish_reason":null}]}\n\n' +
    'data: {"id":"r1","choices":[{"delta":{"content":"こん"},"finish_reason":null}]}\n\n' +
    'data: {"id":"r1","choices":[{"delta":{"content":"にちは"},"finish_reason":"stop"}],"usage":{"total_tokens":3}}\n\n' +
    "data: [DONE]\n\n";
  const bytes = encoder.encode(eventText);
  const multibyteStart = bytes.findIndex((value) => value >= 0x80);
  assert.notEqual(multibyteStart, -1);
  const splitAfterFirstByte = multibyteStart + 1;
  const chunks = [
    bytes.slice(0, 7),
    bytes.slice(7, splitAfterFirstByte),
    bytes.slice(splitAfterFirstByte, splitAfterFirstByte + 1),
    bytes.slice(splitAfterFirstByte + 1),
  ];
  assert.equal(chunks.reduce((total, chunk) => total + chunk.byteLength, 0), bytes.byteLength);
  let streamed = "";
  const streamCapture = {};
  const streamResult = await api.streamHomeConversation(
    streamSnapshot,
    new AbortController().signal,
    (delta) => { streamed += delta; },
    streamResponse(chunks, streamCapture),
  );
  assert.equal(streamed, "こんにちは");
  assert.equal(streamResult.finishReason, "stop");
  assert.equal(streamResult.eventCount, 5);
  assert.equal(streamCapture.url, "/v1/chat/completions");
  assert.deepEqual(JSON.parse(streamCapture.init.body), {
    model: "alice-route",
    messages: [{ role: "user", content: "hello" }],
    stream: true,
  });
  assert.equal(streamCapture.init.credentials, "same-origin");
  assert.equal(streamCapture.init.headers.Authorization, undefined);

  await expectReason(
    api.streamHomeConversation(streamSnapshot, new AbortController().signal, () => {}, async () => new Response(null, { status: 200 })),
    "body_unavailable",
  );
  await expectReason(
    api.streamHomeConversation(streamSnapshot, new AbortController().signal, () => {}, streamResponse([encoder.encode("data: {bad}\n\ndata: [DONE]\n\n")])),
    "stream_invalid",
  );
  await expectReason(
    api.streamHomeConversation(streamSnapshot, new AbortController().signal, () => {}, streamResponse([encoder.encode('data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n')])),
    "stream_truncated",
  );
  await expectReason(
    api.streamHomeConversation(
      streamSnapshot,
      new AbortController().signal,
      () => {},
      streamResponse([
        encoder.encode(
          'data: {"id":"one","choices":[{"delta":{"content":"a"},"finish_reason":null}]}\n\n' +
          'data: {"id":"two","choices":[{"delta":{"content":"b"},"finish_reason":null}]}\n\n' +
          "data: [DONE]\n\n",
        ),
      ]),
    ),
    "stream_invalid",
  );
  await expectReason(
    api.streamHomeConversation(
      streamSnapshot,
      new AbortController().signal,
      () => {},
      streamResponse([encoder.encode(`data: ${JSON.stringify({ choices: [{ delta: { content: "x".repeat(state.HOME_CONVERSATION_BOUNDS.maxResponseChars + 1) }, finish_reason: null }] })}\n\ndata: [DONE]\n\n`)]),
    ),
    "response_too_large",
  );
  const tooManyEvents = `${": keepalive\n\n".repeat(state.HOME_CONVERSATION_BOUNDS.maxSseEvents + 1)}data: [DONE]\n\n`;
  await expectReason(
    api.streamHomeConversation(
      streamSnapshot,
      new AbortController().signal,
      () => {},
      streamResponse([encoder.encode(tooManyEvents)]),
    ),
    "response_too_large",
  );
  const streamAbort = new AbortController();
  const abortingFetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"choices":[{"delta":{"content":"a"},"finish_reason":null}]}\n\n'));
          streamAbort.abort();
          controller.close();
        },
      }),
      { status: 200 },
    );
  await expectReason(
    api.streamHomeConversation(streamSnapshot, streamAbort.signal, () => {}, abortingFetch),
    "aborted",
  );

  const target = state.resolveConversationTarget(
    { character_id: "alice", route_models: ["alice-route"] },
    "alice",
  );
  assert.deepEqual(target, { status: "available", characterId: "alice", routeModel: "alice-route" });
  assert.equal(state.resolveConversationTarget({ character_id: "alice", route_models: [] }, "alice").status, "unavailable");
  assert.equal(state.resolveConversationTarget({ character_id: "alice", route_models: ["one", "two"] }, "alice").status, "ambiguous_route");

  assert.notEqual(state.conversationSessionKey("alice", "real"), state.conversationSessionKey("alice", "preview"));
  assert.notEqual(state.conversationSessionKey("alice", "real"), state.conversationSessionKey("bob", "real"));
  const reset = state.resetConversationSession(
    { sessionId: "old", generation: 4, sourceMode: "real", requestState: "stopped", messages: [{ role: "user", content: "old", status: "complete", messageId: "m", occurredAtLabel: "now" }], draft: "draft", lastRequest: baseSnapshot },
    "new",
  );
  assert.equal(reset.sessionId, "new");
  assert.equal(reset.generation, 5);
  assert.deepEqual(reset.messages, []);
  assert.equal(reset.draft, "");

  assert.equal(state.requestSnapshotMatches(baseSnapshot, { characterId: "alice", sessionId: "session-1", generation: 1, routeModel: "alice-route" }), true);
  assert.equal(state.requestSnapshotMatches(baseSnapshot, { characterId: "bob", sessionId: "session-1", generation: 1, routeModel: "alice-route" }), false);
  assert.equal(state.requestSnapshotMatches(baseSnapshot, { characterId: "alice", sessionId: "session-1", generation: 2, routeModel: "alice-route" }), false);
  assert.equal(state.requestSnapshotMatches(baseSnapshot, { characterId: "alice", sessionId: "session-1", generation: 1, routeModel: "other-route" }), false);
  assert.equal(state.isRequestActive("submitting"), true);
  assert.equal(state.isRequestActive("streaming"), true);
  assert.equal(state.isRequestActive("failed"), false);

  const history = state.toWireHistory([
    { messageId: "u1", role: "user", content: "kept", status: "complete", occurredAtLabel: "now" },
    { messageId: "a1", role: "assistant", content: "partial", status: "stopped", occurredAtLabel: "now" },
    { messageId: "a2", role: "assistant", content: "failure", status: "failed", occurredAtLabel: "now" },
  ]);
  assert.deepEqual(history, [{ role: "user", content: "kept" }]);

  const componentSource = await readFile(new URL("../src/features/home/HomeConversationPage.tsx", import.meta.url), "utf8");
  assert.match(componentSource, /stoppedByUser/);
  assert.match(componentSource, /assistantMessageId/);
  assert.match(componentSource, /invalidateActiveRequest/);
  assert.match(componentSource, /requestSnapshotMatches/);
  assert.match(componentSource, /!session\.draft\.trim\(\)/);
  assert.match(componentSource, /isRequestActive\(current\.requestState\)/);
  assert.doesNotMatch(componentSource, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(componentSource, /localStorage.*session/i);

  console.log("SOUL Lab UI-B0 Home conversation smoke: PASS");
} finally {
  await rm(temp, { recursive: true, force: true });
}
