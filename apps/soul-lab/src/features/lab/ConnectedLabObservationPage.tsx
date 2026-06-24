import { useEffect, useRef, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { MemoryInspectorPage } from "../memory-inspector/MemoryInspectorPage";
import { loadLabManagementProjections } from "../settings/managementApi";
import { PrimaryMemoryCorrectPanel } from "./PrimaryMemoryCorrectPanel";
import {
  LabObservationError,
  loadLabObservation,
  type LabObservationBundle,
  type LabRecentMemoryItem,
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
  const [selectedMemory, setSelectedMemory] = useState<LabRecentMemoryItem | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const generation = useRef(0);

  useEffect(() => {
    setSelectedMemory(null);
  }, [activeCharacter.characterId]);

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
          setSelectedMemory((current) =>
            current === null
              ? null
              : bundle.recent.items.find(
                  (item) => item.memory_id === current.memory_id,
                ) ?? null,
          );
          setState({ kind: "real", namespace, bundle });
        }
      } catch (error) {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        const code =
          error instanceof LabObservationError
            ? error.code
            : "lab_observation_unavailable";
        setState({ kind: "error", code });
      }
    })();

    return () => controller.abort();
  }, [activeCharacter.characterId, onInspectorLockChange, refreshKey]);

  if (mockFallback) {
    return (
      <div>
        <section className="surface-panel">
          <p className="eyebrow">SOURCE</p>
          <h2>{text(language, "ローカルプレビューデータ", "Local preview data")}</h2>
          <p>
            {text(
              language,
              "サーバー実データとは混在していません。Correctを含む操作はpreview-onlyで永続化されません。",
              "This view is not mixed with server data. Correct and all other actions are preview-only and are not persisted.",
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
        <p>{text(language, "RelayLM runtimeのprojectionを確認しています。", "Reading the RelayLM runtime projection.")}</p>
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
          <p className="eyebrow">REAL LAB OBSERVATION + CORRECT</p>
          <h1>Lab Observation</h1>
          <p>{text(language, "実run、Primary MEM、RelayCTX注入証拠を観測し、formed Primary MEMだけを監査可能にCorrectします。", "Observe real runs, Primary MEM, and RelayCTX evidence, and audibly correct formed Primary MEM only.")}</p>
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
          <p>{text(language, "durable evidenceが形成されるまで推測せず空として表示します。", "The Lab remains empty until durable evidence exists; no result is inferred.")}</p>
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
                <span>
                  <strong>{item.title || item.memory_id}</strong>
                  <span className="memory-inspector-record-summary">{item.bounded_summary}</span>
                  <span className="memory-inspector-record-meta">{item.source_kind} · {item.scope_label} · revision {item.revision}</span>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setSelectedMemory(item)}
                  >
                    Correct
                  </button>
                </span>
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
          <p>{text(language, "held / blocked itemはこのPhaseでは変更できません。", "Held and blocked items are not mutable in this phase.")}</p>
        </section>
      </div>

      {selectedMemory && (
        <PrimaryMemoryCorrectPanel
          language={language}
          characterId={activeCharacter.characterId}
          namespace={state.namespace}
          memory={selectedMemory}
          onApplied={() => {
            setRefreshKey((value) => value + 1);
          }}
        />
      )}

      <section className="surface-panel">
        <div className="section-heading"><div><p className="eyebrow">USED IN LATEST RESPONSE</p><h2>{text(language, "backend-bound contextへ注入されたmemory", "Memories injected into backend-bound context")}</h2></div></div>
        <p>retrieval={String(used.retrieval_attempted)} · selected={String(used.selected)} · injection={String(used.relayctx_injection_performed)} · backend-bound={String(used.backend_bound_included)} · response-complete={String(used.response_generation_completed)}</p>
        {used.items.map((item) => (
          <article className="memory-inspector-record memory-record-formed" key={item.memory_id}>
            <span>
              <strong>{item.memory_id}</strong>
              <span className="memory-inspector-record-summary">{item.injected_summary}</span>
              {item.representation_changed && item.current_summary !== null && (
                <span className="memory-inspector-record-summary">{text(language, "現在の修正版", "Current corrected representation")}: {item.current_summary}</span>
              )}
              <span className="memory-inspector-record-meta">{item.representation_changed ? text(language, "この過去runは旧representationを使用", "This past run used the prior representation") : text(language, "現在表現と一致", "Matches current representation")}</span>
            </span>
          </article>
        ))}
        {used.items.length === 0 && <p>{text(language, "最新応答で使用されたmemory証拠はありません。", "No used-memory evidence for the latest response.")}</p>}
      </section>

      <section className="surface-panel">
        <h2>{text(language, "このPhaseの操作境界", "Operation boundary for this phase")}</h2>
        <div className="memory-inspector-actions">
          <button className="button button-secondary" type="button" disabled>forget</button>
          <button className="button button-secondary" type="button" disabled>pin / unpin</button>
          <button className="button button-secondary" type="button" disabled>merge</button>
          <button className="button button-secondary" type="button" disabled>apply / discard held</button>
        </div>
        <p>{text(language, "I-3はformed Primary MEMのCorrect一操作だけです。", "I-3 implements only Correct for formed Primary MEM.")}</p>
      </section>
    </div>
  );
}
