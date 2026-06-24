import { useEffect, useRef, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { MemoryInspectorPage } from "../memory-inspector/MemoryInspectorPage";
import { loadLabManagementProjections } from "../settings/managementApi";
import {
  LabObservationError,
  loadLabObservation,
  type LabObservationBundle,
} from "./observationApi";
import "../memory-inspector/memoryInspector.css";

interface ConnectedLabObservationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onInspectorLockChange: (locked: boolean) => void;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "real"; namespace: string; bundle: LabObservationBundle }
  | { kind: "error"; code: string };

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function display(value: string | null): string {
  return value ?? "—";
}

export function ConnectedLabObservationPage({
  language,
  activeCharacter,
  onInspectorLockChange,
}: ConnectedLabObservationPageProps) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [mockFallback, setMockFallback] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    onInspectorLockChange(false);
    setMockFallback(false);
    setState({ kind: "loading" });
    const controller = new AbortController();
    const requestGeneration = ++generation.current;

    void (async () => {
      try {
        const management = await loadLabManagementProjections(controller.signal);
        const character = management.characters.characters.find(
          (item) => item.character_id === activeCharacter.characterId,
        );
        const namespace = [...(character?.memory_namespaces ?? [])].sort()[0];
        if (!namespace) {
          throw new LabObservationError("lab_observation_namespace_unavailable");
        }
        const bundle = await loadLabObservation(
          activeCharacter.characterId,
          namespace,
          controller.signal,
        );
        if (!controller.signal.aborted && generation.current === requestGeneration) {
          setState({ kind: "real", namespace, bundle });
        }
      } catch (error) {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        const code =
          error instanceof LabObservationError
            ? error.code
            : error instanceof Error
              ? error.message
              : "lab_observation_unavailable";
        setState({ kind: "error", code });
      }
    })();

    return () => controller.abort();
  }, [activeCharacter.characterId, onInspectorLockChange]);

  if (mockFallback) {
    return (
      <div>
        <section className="surface-panel">
          <p className="eyebrow">SOURCE</p>
          <h2>{text(language, "ローカルプレビューデータ", "Local preview data")}</h2>
          <p>
            {text(
              language,
              "サーバー実データとは混在していません。操作はpreview-onlyで永続化されません。",
              "This view is not mixed with server data. Actions are preview-only and are not persisted.",
            )}
          </p>
        </section>
        <MemoryInspectorPage
          language={language}
          activeCharacter={activeCharacter}
          onInspectorLockChange={onInspectorLockChange}
        />
      </div>
    );
  }

  if (state.kind === "loading") {
    return (
      <section className="surface-panel" aria-live="polite">
        <p className="eyebrow">LAB OBSERVATION</p>
        <h1>{text(language, "実行結果を読み込み中", "Loading runtime observation")}</h1>
        <p>{text(language, "RelayLM runtimeのread-only projectionを確認しています。", "Reading the RelayLM runtime projection.")}</p>
      </section>
    );
  }

  if (state.kind === "error") {
    const refused = state.code.includes("403") || state.code.includes("access_refused");
    const schema = state.code.includes("schema") || state.code.includes("mixed_lab");
    return (
      <section className="surface-panel" aria-live="polite">
        <p className="eyebrow">LAB OBSERVATION</p>
        <h1>
          {refused
            ? text(language, "アクセスが拒否されました", "Access refused")
            : schema
              ? text(language, "応答schemaが不正です", "Invalid response schema")
              : text(language, "runtime観測を利用できません", "Runtime observation unavailable")}
        </h1>
        <p>{state.code}</p>
        <button className="button button-secondary" type="button" onClick={() => setMockFallback(true)}>
          {text(language, "ローカルプレビューへ切替", "Use local preview data")}
        </button>
      </section>
    );
  }

  const { latestRun, recent, held, used } = state.bundle;
  const empty =
    latestRun.availability === "empty" &&
    recent.items.length === 0 &&
    held.items.length === 0 &&
    used.items.length === 0;

  return (
    <div className="memory-inspector-page">
      <section className="memory-inspector-hero panel-grid-surface">
        <div>
          <p className="eyebrow">REAL LAB OBSERVATION</p>
          <h1>Lab Observation</h1>
          <p>{text(language, "Phase I-1の実run・Primary MEM・RelayCTX注入証拠をread-onlyで表示します。", "Read-only evidence from real Phase I-1 runs, Primary MEM, and RelayCTX injection.")}</p>
        </div>
        <div className="memory-inspector-boundary-card">
          <span className="mock-pill">Source: RelayLM runtime</span>
          <p>namespace: {state.namespace}</p>
        </div>
        <div className="memory-inspector-counts">
          {([
            ["formed", latestRun.formed_count],
            ["held", latestRun.held_count],
            ["blocked", latestRun.blocked_count],
          ] as const).map(([label, count]) => (
            <div key={label}>
              <span className={`memory-inspector-count-dot memory-dot-${label}`} aria-hidden="true" />
              <strong>{count}</strong>
              <small>{label}</small>
            </div>
          ))}
        </div>
      </section>

      {empty && (
        <section className="surface-panel">
          <h2>{text(language, "有効な観測結果はまだありません", "No valid observation yet")}</h2>
          <p>{text(language, "データを推測せず、durable evidenceが形成されるまで空として表示します。", "The Lab remains empty until durable evidence exists; no result is inferred.")}</p>
        </section>
      )}

      <section className="surface-panel">
        <div className="section-heading">
          <div><p className="eyebrow">LATEST MANAGED RUN</p><h2>{display(latestRun.run_id)}</h2></div>
          <span className={`status-badge status-${latestRun.status === "completed" ? "online" : "degraded"}`}>{latestRun.status}</span>
        </div>
        <div className="memory-inspector-counts">
          <div><strong>{latestRun.slp_status}</strong><small>RelaySLP</small></div>
          <div><strong>{latestRun.relayrun_status}</strong><small>RelayRUN</small></div>
          <div><strong>{latestRun.relayctx_repack_status}</strong><small>RelayCTX Repack</small></div>
          <div><strong>{latestRun.relayctx_unpack_status}</strong><small>RelayCTX Unpack</small></div>
        </div>
        <p>{text(language, "完了時刻", "Completed")}: {display(latestRun.completed_at)} · {latestRun.duration_ms ?? "—"} ms</p>
      </section>

      <div className="memory-inspector-workspace">
        <section className="memory-inspector-list-panel surface-panel">
          <div className="section-heading compact-heading"><div><p className="eyebrow">FORMED PRIMARY MEM</p><h2>{text(language, "最近形成されたmemory", "Recently formed memories")}</h2></div></div>
          <div className="memory-inspector-record-list">
            {recent.items.map((item) => (
              <article className="memory-inspector-record memory-record-formed" key={item.memory_id}>
                <span className="memory-inspector-count-dot memory-dot-formed" aria-hidden="true" />
                <span><strong>{item.title || item.memory_id}</strong><span className="memory-inspector-record-summary">{item.bounded_summary}</span><span className="memory-inspector-record-meta">{item.source_kind} · {item.scope_label}</span></span>
              </article>
            ))}
            {recent.items.length === 0 && <p>{text(language, "formed memoryはありません。", "No formed memory.")}</p>}
          </div>
        </section>

        <section className="memory-inspector-detail-panel surface-panel">
          <div className="section-heading"><div><p className="eyebrow">HELD / BLOCKED</p><h2>{text(language, "不成立・保留outcome", "Held and blocked outcomes")}</h2></div></div>
          {held.items.map((item) => (
            <article key={item.outcome_id} className={`memory-inspector-record memory-record-${item.status}`}>
              <span className={`memory-inspector-count-dot memory-dot-${item.status}`} aria-hidden="true" />
              <span><strong>{item.status}: {item.title || item.outcome_id}</strong><span className="memory-inspector-record-summary">{item.bounded_summary}</span><span className="memory-inspector-record-meta">{item.reason_ids.join(", ") || "no bounded reason"}</span></span>
            </article>
          ))}
          {held.items.length === 0 && <p>{text(language, "held / blocked outcomeはありません。", "No held or blocked outcome.")}</p>}
        </section>
      </div>

      <section className="surface-panel">
        <div className="section-heading"><div><p className="eyebrow">USED IN LATEST RESPONSE</p><h2>{text(language, "backend-bound contextへ注入されたmemory", "Memories injected into backend-bound context")}</h2></div></div>
        <p>retrieval={String(used.retrieval_attempted)} · selected={String(used.selected)} · injection={String(used.relayctx_injection_performed)} · backend-bound={String(used.backend_bound_included)} · response-complete={String(used.response_generation_completed)}</p>
        {used.items.map((item) => (
          <article className="memory-inspector-record memory-record-formed" key={item.memory_id}>
            <span><strong>{item.memory_id}</strong><span className="memory-inspector-record-summary">{item.injected_summary}</span><span className="memory-inspector-record-meta">{item.representation_changed ? text(language, "現在表現との差分あり", "Current representation changed") : text(language, "現在表現と一致", "Matches current representation")}</span></span>
          </article>
        ))}
        {used.items.length === 0 && <p>{text(language, "最新応答で使用されたmemory証拠はありません。", "No used-memory evidence for the latest response.")}</p>}
      </section>

      <section className="surface-panel">
        <h2>Memory actions</h2>
        <div className="memory-inspector-actions">
          {["correct", "forget", "pin", "merge", "apply held", "discard held"].map((label) => (
            <button className="button button-secondary" type="button" disabled key={label}>{label}</button>
          ))}
        </div>
        <p>{text(language, "I-3で対応予定です。この画面はobserve onlyです。", "Planned for I-3. This surface is observe-only.")}</p>
      </section>
    </div>
  );
}
