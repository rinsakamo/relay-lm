import { useEffect, useRef, useState } from "react";
import type { Language } from "../../domain/lab";
import type { LabRecentMemoryItem } from "./observationApi";
import {
  applyMemoryCorrection,
  loadMemoryCorrectionHistory,
  MemoryCorrectionError,
  preflightMemoryCorrection,
  type MemoryCorrectionHistory,
  type MemoryCorrectionPreflight,
} from "./correctionApi";

interface PrimaryMemoryCorrectPanelProps {
  language: Language;
  characterId: string;
  namespace: string;
  memory: LabRecentMemoryItem;
  onApplied: () => void;
}

type OperationState =
  | { kind: "idle" }
  | { kind: "preflight-loading" }
  | { kind: "preflight-ready"; value: MemoryCorrectionPreflight; operationId: string }
  | { kind: "apply-loading"; value: MemoryCorrectionPreflight; operationId: string }
  | { kind: "applied"; revision: number }
  | { kind: "error"; code: string };

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function codeFor(error: unknown): string {
  return error instanceof MemoryCorrectionError ? error.code : "runtime_unavailable";
}

export function PrimaryMemoryCorrectPanel({
  language,
  characterId,
  namespace,
  memory,
  onApplied,
}: PrimaryMemoryCorrectPanelProps) {
  const [title, setTitle] = useState(memory.title);
  const [summary, setSummary] = useState(memory.bounded_summary);
  const [reason, setReason] = useState("");
  const [state, setState] = useState<OperationState>({ kind: "idle" });
  const [history, setHistory] = useState<MemoryCorrectionHistory | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const currentGeneration = ++generation.current;
    const controller = new AbortController();
    setTitle(memory.title);
    setSummary(memory.bounded_summary);
    setReason("");
    setState({ kind: "idle" });
    setHistory(null);
    void loadMemoryCorrectionHistory(
      characterId,
      namespace,
      memory.memory_id,
      controller.signal,
    ).then((value) => {
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        setHistory(value);
      }
    }).catch(() => {
      // The correction form remains usable; history is a separate bounded read.
    });
    return () => controller.abort();
  }, [characterId, namespace, memory.memory_id, memory.title, memory.bounded_summary]);

  async function requestPreflight() {
    if (state.kind === "preflight-loading" || state.kind === "apply-loading") return;
    const currentGeneration = generation.current;
    const operationId = crypto.randomUUID();
    setState({ kind: "preflight-loading" });
    try {
      const value = await preflightMemoryCorrection(
        characterId,
        namespace,
        memory.memory_id,
        {
          expectedRevision: memory.revision,
          correctedTitle: title,
          correctedSummary: summary,
          reason,
          operationId,
        },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "preflight-ready", value, operationId });
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        setState({ kind: "error", code: codeFor(error) });
      }
    }
  }

  async function confirmApply() {
    if (state.kind !== "preflight-ready") return;
    const currentGeneration = generation.current;
    const { value, operationId } = state;
    setState({ kind: "apply-loading", value, operationId });
    try {
      const result = await applyMemoryCorrection(
        characterId,
        namespace,
        memory.memory_id,
        {
          expectedRevision: memory.revision,
          operationId,
          applyToken: value.apply_token,
        },
      );
      if (generation.current === currentGeneration) {
        setState({ kind: "applied", revision: result.result_revision });
        onApplied();
      }
    } catch (error) {
      if (generation.current === currentGeneration) {
        setState({ kind: "error", code: codeFor(error) });
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
          <p className="eyebrow">AUDITABLE CORRECT</p>
          <h2>{text(language, "Primary MEMを修正", "Correct Primary MEM")}</h2>
        </div>
        <span className="status-badge status-online">revision {memory.revision}</span>
      </div>
      <p>
        {text(
          language,
          "identity・lineage・scopeは変更せず、titleとsummaryだけをsuccessor revisionとして保存します。",
          "Only title and summary are published as a successor revision; identity, lineage, and scope remain unchanged.",
        )}
      </p>
      <label>
        {text(language, "タイトル", "Title")}
        <input
          value={title}
          maxLength={160}
          disabled={loading || ready !== null}
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>
      <label>
        {text(language, "要約", "Summary")}
        <textarea
          value={summary}
          maxLength={2048}
          rows={6}
          disabled={loading || ready !== null}
          onChange={(event) => setSummary(event.target.value)}
        />
      </label>
      <label>
        {text(language, "修正理由", "Reason")}
        <textarea
          value={reason}
          maxLength={512}
          rows={3}
          disabled={loading || ready !== null}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>

      {ready && (
        <div className="memory-inspector-boundary-card">
          <strong>{text(language, "適用前の確認", "Review before apply")}</strong>
          <p>{text(language, "変更前", "Before")}: {ready.diff.before.title || "—"}</p>
          <p className="memory-inspector-record-summary">{ready.diff.before.summary}</p>
          <p>{text(language, "変更後", "After")}: {ready.diff.after.title || "—"}</p>
          <p className="memory-inspector-record-summary">{ready.diff.after.summary}</p>
          <p>revision {ready.current_revision} → {ready.candidate_revision}</p>
        </div>
      )}

      <div className="memory-inspector-actions">
        {!ready && (
          <button
            className="button button-primary"
            type="button"
            disabled={loading || reason.length === 0 || summary.length === 0}
            onClick={() => void requestPreflight()}
          >
            {state.kind === "preflight-loading"
              ? text(language, "確認中…", "Checking…")
              : text(language, "差分を確認", "Review diff")}
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
                : text(language, "明示的に適用", "Confirm apply")}
            </button>
            <button
              className="button button-secondary"
              type="button"
              disabled={loading}
              onClick={() => setState({ kind: "idle" })}
            >
              {text(language, "編集へ戻る", "Back to edit")}
            </button>
          </>
        )}
      </div>

      {state.kind === "error" && (
        <p role="alert">
          {text(language, "Correct操作を完了できませんでした", "Correction did not complete")}: {state.code}
        </p>
      )}
      {state.kind === "applied" && (
        <p>{text(language, "監査記録とともに適用しました", "Applied with an audit receipt")}: revision {state.revision}</p>
      )}

      {history && (
        <div>
          <h3>{text(language, "修正履歴", "Correction history")}</h3>
          <p>{history.correction_count} correction(s)</p>
          {history.items.map((item) => (
            <article className="memory-inspector-record" key={item.correction_id}>
              <span>
                <strong>revision {item.prior_revision} → {item.result_revision}</strong>
                <span className="memory-inspector-record-summary">{item.reason}</span>
                <span className="memory-inspector-record-meta">{item.status} · {item.applied_at}</span>
              </span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
