import type { Language } from "../../domain/lab";
import type { LabLifecycleVisibilityProjection, LifecycleState } from "./lifecycleVisibilityApi";

interface LifecycleVisibilityPanelProps {
  language: Language;
  characterId: string;
  namespace: string | null;
  projection: LabLifecycleVisibilityProjection | null;
  loading?: boolean;
  errorCode?: string | null;
  surface: "home" | "observation";
}

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function lifecycleLabel(language: Language, state: LifecycleState): string {
  const ja: Record<LifecycleState, string> = {
    active: "active · 通常会話で使用可能",
    hidden: "hidden · 通常会話から除外",
    prepared: "prepared · 確定待ちで除外",
    recovery_required: "recovery_required · 回復確認が必要",
    corrupt: "corrupt · 安全のため除外",
    unknown: "unknown · 状態不明",
  };
  const en: Record<LifecycleState, string> = {
    active: "active · eligible for ordinary conversation",
    hidden: "hidden · excluded from ordinary conversation",
    prepared: "prepared · excluded until finalized",
    recovery_required: "recovery_required · needs recovery validation",
    corrupt: "corrupt · excluded fail-closed",
    unknown: "unknown · unresolved state",
  };
  return (language === "ja" ? ja : en)[state];
}

function statusClass(status: string): string {
  if (["active", "complete", "formed", "available", "none"].includes(status)) return "online";
  if (["hidden", "prepared", "recovery_required", "isolated", "processing", "queued", "mixed"].includes(status)) return "degraded";
  return "unconfigured";
}

export function LifecycleVisibilityPanel({
  language,
  characterId,
  namespace,
  projection,
  loading = false,
  errorCode = null,
  surface,
}: LifecycleVisibilityPanelProps) {
  const status = loading
    ? "loading"
    : projection?.availability ?? (errorCode ? "unavailable" : "not_connected");
  return (
    <section className="surface-panel lifecycle-visibility-panel" aria-labelledby={`${surface}-lifecycle-title`}>
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">UI-B1A · READ-ONLY LIFECYCLE VISIBILITY</p>
          <h2 id={`${surface}-lifecycle-title`}>Lifecycle Visibility</h2>
        </div>
        <span className={`status-badge status-${statusClass(status)}`}>{status}</span>
      </div>
      <p className="panel-description">
        {text(
          language,
          "server-owned projectionだけを表示します。queue、scheduler、repair、Forget/Pin/Held/SOUL apply の操作はありません。",
          "Only server-owned projections are shown. There are no queue, scheduler, repair, Forget, Pin, Held, or SOUL apply controls.",
        )}
      </p>
      <p className="memory-inspector-record-meta">
        character={characterId} · namespace={namespace ?? "—"} · {text(language, "raw path / locator / claim / exception は非表示", "raw paths, locators, claims, and exceptions are omitted")}
      </p>

      {loading && <p>{text(language, "lifecycle visibilityを読み込み中です。", "Loading lifecycle visibility.")}</p>}
      {!loading && !projection && (
        <p className="boundary-note">
          {text(language, "projectionを利用できません。", "Projection unavailable.")} {errorCode ?? "not_connected"}
        </p>
      )}

      {projection && (
        <>
          <div className="memory-inspector-counts">
            <div><strong>{projection.durable_finalization.status}</strong><small>durable-finalization</small></div>
            <div><strong>{projection.queue_worker.status}</strong><small>queue / worker</small></div>
            <div><strong>{projection.memory_items.length}</strong><small>Primary current items</small></div>
          </div>

          <div className="runtime-list">
            <div className="runtime-row">
              <div>
                <strong>{text(language, "durable-finalization", "durable-finalization")}</strong>
                <span>
                  pending {projection.durable_finalization.pending_count} · complete {projection.durable_finalization.complete_count} · isolated {projection.durable_finalization.isolated_count}
                </span>
              </div>
              <span className={`status-badge status-${statusClass(projection.durable_finalization.status)}`}>{projection.durable_finalization.status}</span>
            </div>
            {projection.durable_finalization.status === "isolated" || projection.durable_finalization.isolated_count > 0 ? (
              <p className="boundary-note">
                {text(language, "isolated recordは自動的にqueueへ流れず、operator validation対象として表示します。locatorやpathは表示しません。", "Isolated records are not automatically queued; they are shown only as operator-validation targets. Locators and paths are not displayed.")}
              </p>
            ) : null}
            <div className="runtime-row">
              <div>
                <strong>{text(language, "queue / worker", "queue / worker")}</strong>
                <span>
                  queued {projection.queue_worker.queued_count} · processing {projection.queue_worker.processing_count} · formed {projection.queue_worker.formed_count} · held {projection.queue_worker.held_count} · blocked {projection.queue_worker.blocked_count} · failed {projection.queue_worker.failed_count}
                </span>
              </div>
              <span className={`status-badge status-${statusClass(projection.queue_worker.status)}`}>{projection.queue_worker.status}</span>
            </div>
          </div>

          <div className="memory-inspector-record-list">
            {projection.memory_items.map((item) => (
              <article className={`memory-inspector-record memory-record-${item.retrieval_eligible ? "formed" : "blocked"}`} key={item.memory_id}>
                <span className={`memory-inspector-count-dot memory-dot-${item.retrieval_eligible ? "formed" : "blocked"}`} aria-hidden="true" />
                <span>
                  <strong>{lifecycleLabel(language, item.current_lifecycle_state)}</strong>
                  <span className="memory-inspector-record-meta">
                    revision {item.current_revision ?? "—"} · physical {item.current_physical_status} · retrieval {String(item.retrieval_eligible)}
                  </span>
                  <span className="memory-inspector-record-meta">
                    {text(language, "historical used-memory receiptは書き換えません。", "Historical used-memory receipts remain unchanged.")}
                  </span>
                </span>
              </article>
            ))}
            {projection.memory_items.length === 0 && (
              <p>{text(language, "表示できるPrimary MEM current-stateはありません。", "No Primary MEM current-state item is available.")}</p>
            )}
          </div>

          <section className="surface-panel" aria-label={text(language, "Fresh Conversation検証", "Fresh Conversation verification")}>
            <h3>{text(language, "Fresh Conversation の意味", "Fresh Conversation meaning")}</h3>
            <p>
              {text(
                language,
                "New Conversation はブラウザ内Home sessionのリセットです。durable memory storeはリセットされず、active current memoryは後続の通常検索に残り、hidden/current-ineligible memoryは除外されたままです。Home transcriptはdurable sourceではありません。",
                "New Conversation resets the browser-local Home session only. The durable memory store is retained; active current memories remain eligible for later ordinary retrieval, while hidden or current-ineligible memories remain excluded. The Home transcript is not a durable source.",
              )}
            </p>
          </section>
        </>
      )}
    </section>
  );
}
