import { useEffect, useRef, useState } from "react";
import type { Language } from "../../domain/lab";
import type { LabRecentMemoryItem } from "./observationApi";
import {
  applyMemoryForget,
  loadMemoryForgetHistory,
  MemoryForgetError,
  preflightMemoryForget,
  type MemoryForgetApplyReceipt,
  type MemoryForgetHistory,
  type MemoryForgetPreflight,
} from "./forgetApi";

interface PrimaryMemoryForgetPanelProps {
  language: Language;
  characterId: string;
  namespace: string;
  memory: LabRecentMemoryItem;
  onApplied: () => void;
}

type OperationState =
  | { kind: "idle" }
  | { kind: "preflight-loading" }
  | { kind: "preflight-ready"; value: MemoryForgetPreflight; operationId: string; reason: string }
  | { kind: "apply-loading"; value: MemoryForgetPreflight; operationId: string; reason: string }
  | { kind: "applied"; receipt: MemoryForgetApplyReceipt }
  | { kind: "error"; code: string };

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function codeFor(error: unknown): string {
  return error instanceof MemoryForgetError ? error.code : "runtime_unavailable";
}

function shortMemoryId(memoryId: string): string {
  return `${memoryId.slice(0, 12)}…${memoryId.slice(-6)}`;
}

function requiresCurrentMemoryRefresh(code: string): boolean {
  return [
    "stale_revision",
    "operation_conflict",
    "target_not_active",
    "already_hidden",
    "target_corrupt",
    "reconciliation_required",
    "store_unavailable",
    "response_lost",
  ].includes(code);
}

function errorText(language: Language, code: string): string {
  const messages: Record<string, [string, string]> = {
    stale_revision: ["表示中のrevisionが古くなりました。memory一覧を更新してください。", "The displayed revision is stale. Refresh the memory list."],
    token_expired: ["確認tokenの期限が切れました。もう一度preflightしてください。", "The confirmation token expired. Run preflight again."],
    token_invalid: ["確認tokenが一致しません。最初からやり直してください。", "The confirmation token did not match. Start again."],
    operation_conflict: ["同じmemoryで別のmutationが進行中です。", "Another mutation is active for this memory."],
    target_not_active: ["対象memoryは現在activeではありません。", "The target memory is not currently active."],
    already_hidden: ["対象memoryはすでにhiddenです。", "The target memory is already hidden."],
    target_corrupt: ["対象memoryの状態確認が必要です。", "The target memory requires state review."],
    store_unavailable: ["memory storeを利用できません。", "The memory store is unavailable."],
  };
  const pair = messages[code] ?? ["Forget操作を完了できませんでした。", "Forget did not complete."];
  return language === "ja" ? pair[0] : pair[1];
}

export function PrimaryMemoryForgetPanel({
  language,
  characterId,
  namespace,
  memory,
  onApplied,
}: PrimaryMemoryForgetPanelProps) {
  const [reason, setReason] = useState("");
  const [state, setState] = useState<OperationState>({ kind: "idle" });
  const [history, setHistory] = useState<MemoryForgetHistory | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const currentGeneration = ++generation.current;
    const controller = new AbortController();
    setReason("");
    setState({ kind: "idle" });
    setHistory(null);
    void loadMemoryForgetHistory(
      characterId,
      namespace,
      memory.memory_id,
      controller.signal,
    ).then((value) => {
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        setHistory(value);
      }
    }).catch(() => {
      // History is read-only supporting evidence; the preflight flow remains usable.
    });
    return () => controller.abort();
  }, [characterId, namespace, memory.memory_id, memory.revision]);

  async function requestPreflight() {
    if (state.kind === "preflight-loading" || state.kind === "apply-loading") return;
    const currentGeneration = generation.current;
    const operationId = crypto.randomUUID();
    const auditReason = reason;
    setState({ kind: "preflight-loading" });
    try {
      const value = await preflightMemoryForget(
        characterId,
        namespace,
        memory.memory_id,
        {
          expectedRevision: memory.revision,
          expectedLifecycleState: "active",
          reason: auditReason,
          operationId,
        },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "preflight-ready", value, operationId, reason: auditReason });
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        const code = codeFor(error);
        setState({ kind: "error", code });
        if (requiresCurrentMemoryRefresh(code)) onApplied();
      }
    }
  }

  async function confirmApply() {
    if (state.kind !== "preflight-ready") return;
    const currentGeneration = generation.current;
    const { value, operationId, reason: auditReason } = state;
    setState({ kind: "apply-loading", value, operationId, reason: auditReason });
    try {
      const receipt = await applyMemoryForget(
        characterId,
        namespace,
        memory.memory_id,
        {
          expectedRevision: memory.revision,
          expectedLifecycleState: "active",
          reason: auditReason,
          operationId,
          applyToken: value.apply_token,
        },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "applied", receipt });
        onApplied();
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        const code = codeFor(error);
        setState({ kind: "error", code });
        if (requiresCurrentMemoryRefresh(code)) onApplied();
      }
    }
  }

  const loading = state.kind === "preflight-loading" || state.kind === "apply-loading";
  const ready =
    state.kind === "preflight-ready" || state.kind === "apply-loading"
      ? state.value
      : null;

  return (
    <section className="surface-panel" aria-live="polite">
      <div className="section-heading">
        <div>
          <p className="eyebrow">LOOPBACK FORGET</p>
          <h2>{text(language, "Primary MEMをForget", "Forget Primary MEM")}</h2>
        </div>
        <span className="status-badge status-degraded">revision {memory.revision}</span>
      </div>
      <p>
        {text(
          language,
          "既存のForget authorityを使い、activeなcurrent Primary MEMをhidden successorへ収束させます。物理削除・restore・purgeは行いません。",
          "Use the existing Forget authority to converge one active current Primary MEM to a hidden successor. No physical deletion, restore, or purge is performed.",
        )}
      </p>
      <div className="memory-inspector-boundary-card">
        <strong>{text(language, "対象", "Target")}</strong>
        <p>memory_id: {shortMemoryId(memory.memory_id)}</p>
        <p>current lifecycle: active · revision {memory.revision}</p>
      </div>
      <label>
        {text(language, "監査理由", "Audit reason")}
        <textarea
          value={reason}
          maxLength={512}
          rows={3}
          disabled={loading || ready !== null || state.kind === "applied"}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>

      {ready && (
        <div className="memory-inspector-boundary-card">
          <strong>{text(language, "適用前の確認", "Review before apply")}</strong>
          <p>{text(language, "対象memory", "Target memory")}: {shortMemoryId(ready.memory_id)}</p>
          <p>revision {ready.current_revision} → {ready.target_revision}</p>
          <ul>
            <li>{text(language, "target lifecycleはhiddenになります。", "Target lifecycle becomes hidden.")}</li>
            <li>{text(language, "ordinary retrievalから除外されます。", "It is excluded from ordinary retrieval.")}</li>
            <li>{text(language, "RelayCTX injectionから除外されます。", "It is excluded from RelayCTX injection.")}</li>
            <li>{text(language, "物理削除ではありません。", "This is not physical deletion.")}</li>
            <li>{text(language, "監査証跡は保持されます。", "Audit evidence is retained.")}</li>
            <li>{text(language, "過去のused-memory evidenceは改変しません。", "Historical used-memory evidence is not rewritten.")}</li>
          </ul>
        </div>
      )}

      <div className="memory-inspector-actions">
        {!ready && state.kind !== "applied" && (
          <button
            className="button button-primary"
            type="button"
            disabled={loading || reason.length === 0}
            onClick={() => void requestPreflight()}
          >
            {state.kind === "preflight-loading"
              ? text(language, "確認中…", "Checking…")
              : text(language, "Forget影響を確認", "Preview Forget effects")}
          </button>
        )}
        {ready && (
          <>
            <button
              className="button button-primary"
              type="button"
              disabled={loading}
              onClick={() => void confirmApply()}
            >
              {state.kind === "apply-loading"
                ? text(language, "適用中…", "Applying…")
                : text(language, "明示的にForgetを適用", "Explicitly apply Forget")}
            </button>
            <button
              className="button button-secondary"
              type="button"
              disabled={loading}
              onClick={() => setState({ kind: "idle" })}
            >
              {text(language, "理由入力へ戻る", "Back to reason")}
            </button>
          </>
        )}
      </div>

      {state.kind === "error" && (
        <p role="alert">
          {errorText(language, state.code)} ({state.code})
        </p>
      )}
      {state.kind === "applied" && (
        <div className="memory-inspector-boundary-card">
          <strong>{text(language, "Forget receipt", "Forget receipt")}</strong>
          <p>status: {state.receipt.status}</p>
          <p>revision {state.receipt.prior_revision} → {state.receipt.result_revision}</p>
          <p>hidden · retrieval excluded · audit retained</p>
          <p>{text(language, "過去のused-memory evidenceはそのままです。", "Historical used-memory evidence is unchanged.")}</p>
        </div>
      )}

      {history && (
        <div>
          <h3>{text(language, "Forget履歴", "Forget history")}</h3>
          <p>current lifecycle: {history.current_lifecycle_state} · revision {history.current_revision}</p>
          <p>{history.forget_count} forget operation(s)</p>
        </div>
      )}
    </section>
  );
}
