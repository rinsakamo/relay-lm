import { useEffect, useRef, useState } from "react";
import type { Language } from "../../domain/lab";
import type { LabMemoryOutcomeItem } from "./observationApi";
import {
  applyHeldGovernance,
  HeldGovernanceError,
  loadHeldGovernanceHistory,
  preflightHeldGovernance,
  type HeldGovernanceAction,
  type HeldGovernanceHistory,
  type HeldGovernancePreflight,
  type HeldGovernanceReceipt,
} from "./heldGovernanceApi";

interface HeldGovernancePanelProps {
  language: Language;
  characterId: string;
  namespace: string;
  outcome: LabMemoryOutcomeItem;
  onApplied: () => void;
}

type OperationState =
  | { kind: "idle"; action: HeldGovernanceAction }
  | { kind: "preflight-loading"; action: HeldGovernanceAction }
  | { kind: "preflight-ready"; action: HeldGovernanceAction; value: HeldGovernancePreflight; operationId: string; reason: string }
  | { kind: "apply-loading"; action: HeldGovernanceAction; value: HeldGovernancePreflight; operationId: string; reason: string }
  | { kind: "applied"; receipt: HeldGovernanceReceipt }
  | { kind: "error"; action: HeldGovernanceAction; code: string };

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function codeFor(error: unknown): string {
  return error instanceof HeldGovernanceError ? error.code : "runtime_unavailable";
}

function shortId(value: string): string {
  return value.length <= 24 ? value : `${value.slice(0, 12)}...${value.slice(-6)}`;
}

function errorText(language: Language, code: string): string {
  const messages: Record<string, [string, string]> = {
    target_not_found: ["runtime-private candidate evidenceが見つかりません。", "Runtime-private candidate evidence was not found."],
    operation_conflict: ["別のgovernance decisionが先に収束しています。", "Another governance decision has already converged."],
    stale_candidate: ["candidate generationが古くなりました。一覧を更新してください。", "The candidate generation is stale. Refresh the list."],
    token_expired: ["確認tokenの期限が切れました。もう一度preflightしてください。", "The confirmation token expired. Run preflight again."],
    token_invalid: ["確認tokenが一致しません。最初からやり直してください。", "The confirmation token did not match. Start again."],
    source_corrupt: ["source evidenceがcorruptです。", "Source evidence is corrupt."],
    store_unavailable: ["memory storeを利用できません。", "The memory store is unavailable."],
  };
  const pair = messages[code] ?? ["Held governance操作を完了できませんでした。", "Held governance did not complete."];
  return language === "ja" ? pair[0] : pair[1];
}

export function HeldGovernancePanel({
  language,
  characterId,
  namespace,
  outcome,
  onApplied,
}: HeldGovernancePanelProps) {
  const [reason, setReason] = useState("");
  const [state, setState] = useState<OperationState>({ kind: "idle", action: "apply" });
  const [history, setHistory] = useState<HeldGovernanceHistory | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const currentGeneration = ++generation.current;
    const controller = new AbortController();
    setReason("");
    setState({ kind: "idle", action: "apply" });
    setHistory(null);
    void loadHeldGovernanceHistory(
      characterId,
      namespace,
      outcome.outcome_id,
      controller.signal,
    ).then((value) => {
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        setHistory(value);
      }
    }).catch(() => {
      // History is supporting evidence only; the explicit decision flow remains available.
    });
    return () => controller.abort();
  }, [characterId, namespace, outcome.outcome_id]);

  async function requestPreflight(action: HeldGovernanceAction) {
    if (state.kind === "preflight-loading" || state.kind === "apply-loading") return;
    const currentGeneration = generation.current;
    const operationId = crypto.randomUUID();
    const auditReason = reason;
    setState({ kind: "preflight-loading", action });
    try {
      const value = await preflightHeldGovernance(
        characterId,
        namespace,
        outcome.outcome_id,
        action,
        { operationId, reason: auditReason },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "preflight-ready", action, value, operationId, reason: auditReason });
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        setState({ kind: "error", action, code: codeFor(error) });
      }
    }
  }

  async function confirmDecision() {
    if (state.kind !== "preflight-ready") return;
    const currentGeneration = generation.current;
    const { action, value, operationId, reason: auditReason } = state;
    if (value.status !== "ready" || value.apply_token === null) return;
    setState({ kind: "apply-loading", action, value, operationId, reason: auditReason });
    try {
      const receipt = await applyHeldGovernance(
        characterId,
        namespace,
        outcome.outcome_id,
        action,
        { operationId, reason: auditReason, applyToken: value.apply_token },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "applied", receipt });
        onApplied();
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        setState({ kind: "error", action, code: codeFor(error) });
      }
    }
  }

  const loading = state.kind === "preflight-loading" || state.kind === "apply-loading";
  const ready = state.kind === "preflight-ready" || state.kind === "apply-loading" ? state.value : null;
  const activeAction: HeldGovernanceAction = state.kind === "applied" ? state.receipt.action : state.action;
  const canGovern = outcome.status === "held";

  return (
    <section className="surface-panel" aria-live="polite">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HELD GOVERNANCE</p>
          <h2>{text(language, "Held outcomeをApply / Discard", "Apply or discard held outcome")}</h2>
        </div>
        <span className="status-badge status-degraded">{outcome.status}</span>
      </div>
      <p>
        {text(
          language,
          "runtime-private evidenceを再読込し、明示確認されたgovernance decisionだけをdurable receiptへ収束させます。worker / scheduler / retry loopは開始しません。",
          "Reread runtime-private evidence and converge only an explicitly confirmed governance decision to a durable receipt. No worker, scheduler, or retry loop is started.",
        )}
      </p>
      <div className="memory-inspector-boundary-card">
        <strong>{text(language, "対象candidate", "Target candidate")}</strong>
        <p>candidate: {shortId(outcome.outcome_id)}</p>
        <p>{text(language, "本文・model output・queue payloadは表示しません。", "Body text, model output, and queue payload are not displayed.")}</p>
      </div>
      {!canGovern && <p role="alert">{text(language, "blocked outcomeはこの画面では変更できません。", "Blocked outcomes cannot be changed here.")}</p>}
      <label>
        {text(language, "監査理由", "Audit reason")}
        <textarea
          value={reason}
          maxLength={512}
          rows={3}
          disabled={!canGovern || loading || ready !== null || state.kind === "applied"}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>

      {ready && (
        <div className="memory-inspector-boundary-card">
          <strong>{text(language, "適用前の確認", "Review before decision")}</strong>
          <p>status: {ready.status} · reason: {ready.reason_code}</p>
          <ul>
            <li>{text(language, "public receiptはcontent-freeです。", "The public receipt is content-free.")}</li>
            <li>{text(language, "runtime-private evidenceはomittedです。", "Runtime-private evidence is omitted.")}</li>
            <li>{text(language, "queue / Primary MEMはこのUIから直接rewriteしません。", "The UI does not directly rewrite queue or Primary MEM files.")}</li>
            <li>{text(language, "自動実行・scheduler起動はありません。", "No automatic execution or scheduler start occurs.")}</li>
          </ul>
        </div>
      )}

      <div className="memory-inspector-actions">
        {!ready && state.kind !== "applied" && (
          <>
            <button className="button button-primary" type="button" disabled={!canGovern || loading || reason.length === 0} onClick={() => void requestPreflight("apply")}>
              {state.kind === "preflight-loading" && state.action === "apply"
                ? text(language, "確認中…", "Checking…")
                : text(language, "Apply影響を確認", "Preview Apply")}
            </button>
            <button className="button button-secondary" type="button" disabled={!canGovern || loading || reason.length === 0} onClick={() => void requestPreflight("discard")}>
              {state.kind === "preflight-loading" && state.action === "discard"
                ? text(language, "確認中…", "Checking…")
                : text(language, "Discard影響を確認", "Preview Discard")}
            </button>
          </>
        )}
        {ready && (
          <>
            <button className="button button-primary" type="button" disabled={loading || ready.status !== "ready" || ready.apply_token === null} onClick={() => void confirmDecision()}>
              {state.kind === "apply-loading"
                ? text(language, "収束中…", "Converging…")
                : text(language, `明示的に${activeAction}を確定`, `Explicitly confirm ${activeAction}`)}
            </button>
            <button className="button button-secondary" type="button" disabled={loading} onClick={() => setState({ kind: "idle", action: activeAction })}>
              {text(language, "理由入力へ戻る", "Back to reason")}
            </button>
          </>
        )}
      </div>

      {state.kind === "error" && <p role="alert">{errorText(language, state.code)} ({state.code})</p>}
      {state.kind === "applied" && (
        <div className="memory-inspector-boundary-card">
          <strong>{text(language, "Held governance receipt", "Held governance receipt")}</strong>
          <p>status: {state.receipt.status} · action: {state.receipt.action}</p>
          <p>idempotent replay: {String(state.receipt.idempotent_replay)}</p>
          <p>content-free · runtime-private evidence omitted</p>
        </div>
      )}

      {history && (
        <div>
          <h3>{text(language, "Governance履歴", "Governance history")}</h3>
          <p>{history.count} decision(s)</p>
        </div>
      )}
    </section>
  );
}
