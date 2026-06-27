import { useEffect, useRef, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { MemoryInspectorPage } from "../memory-inspector/MemoryInspectorPage";
import { loadLabManagementProjections } from "../settings/managementApi";
import { HeldGovernancePanel } from "./HeldGovernancePanel";
import { PrimaryMemoryCorrectPanel } from "./PrimaryMemoryCorrectPanel";
import { PrimaryMemoryForgetPanel } from "./PrimaryMemoryForgetPanel";
import {
  LabObservationError,
  loadLabObservation,
  type LabMemoryOutcomeItem,
  type LabObservationBundle,
  type LabRecentMemoryItem,
} from "./observationApi";
import {
  loadUsedMemoryLifecycle,
  type UsedMemoryLifecycleProjection,
} from "./usedMemoryLifecycleApi";
import "../memory-inspector/memoryInspector.css";

interface ConnectedLabObservationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onInspectorLockChange: (locked: boolean) => void;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "real"; namespace: string; bundle: LabObservationBundle; usedLifecycle: UsedMemoryLifecycleProjection }
  | { kind: "error"; code: string };

type SelectedOperation =
  | { kind: "correct"; memory: LabRecentMemoryItem }
  | { kind: "forget"; memory: LabRecentMemoryItem }
  | { kind: "held"; outcome: LabMemoryOutcomeItem };

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function display(value: string | null): string {
  return value ?? "—";
}

function shortId(value: string): string {
  return value.length <= 24 ? value : `${value.slice(0, 12)}...${value.slice(-6)}`;
}

export function ConnectedLabObservationPage({
  language,
  activeCharacter,
  onInspectorLockChange,
}: ConnectedLabObservationPageProps) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [mockFallback, setMockFallback] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState<SelectedOperation | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const generation = useRef(0);

  useEffect(() => {
    setSelectedOperation(null);
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
        const [bundle, usedLifecycle] = await Promise.all([
          loadLabObservation(activeCharacter.characterId, namespace, controller.signal),
          loadUsedMemoryLifecycle(activeCharacter.characterId, namespace, controller.signal),
        ]);
        if (!controller.signal.aborted && generation.current === requestGeneration) {
          setSelectedOperation((current) => {
            if (current === null) return null;
            if (current.kind === "held") {
              const refreshed = bundle.held.items.find((item) => item.outcome_id === current.outcome.outcome_id);
              return refreshed ? { kind: "held", outcome: refreshed } : null;
            }
            const refreshed = bundle.recent.items.find((item) => item.memory_id === current.memory.memory_id);
            return refreshed ? { kind: current.kind, memory: refreshed } : null;
          });
          setState({ kind: "real", namespace, bundle, usedLifecycle });
        }
      } catch (error) {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        const code = error instanceof LabObservationError ? error.code : "lab_observation_unavailable";
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
          <p>{text(language, "サーバー実データとは混在していません。Correct / Forget / Held Governanceを含む操作はpreview-onlyで永続化されません。", "This view is not mixed with server data. Correct, Forget, Held Governance, and all other actions are preview-only and are not persisted.")}</p>
        </section>
        <MemoryInspectorPage language={language} activeCharacter={activeCharacter} onInspectorLockChange={onInspectorLockChange} />
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
  const { usedLifecycle } = state;
  const empty = latestRun.availability === "empty" && recent.items.length === 0 && held.items.length === 0 && used.items.length === 0;

  return (
    <div className="memory-inspector-page">
      <section className="memory-inspector-hero panel-grid-surface">
        <div>
          <p className="eyebrow">REAL LAB OBSERVATION + GOVERNANCE</p>
          <h1>Lab Observation</h1>
          <p>{text(language, "実run、Primary MEM、RelayCTX注入証拠を観測し、formed Primary MEMをCorrect / Forget、held outcomeをApply / Discardできます。", "Observe real runs, Primary MEM, and RelayCTX evidence; Correct / Forget formed Primary MEM and Apply / Discard held outcomes.")}</p>
        </div>
        <div className="memory-inspector-boundary-card"><span className="mock-pill">Source: RelayLM runtime</span><p>namespace: {state.namespace}</p></div>
        <div className="memory-inspector-counts">
          {([ ["formed", latestRun.formed_count], ["held", latestRun.held_count], ["blocked", latestRun.blocked_count] ] as const).map(([label, count]) => (
            <div key={label}><span className={`memory-inspector-count-dot memory-dot-${label}`} aria-hidden="true" /><strong>{count}</strong><small>{label}</small></div>
          ))}
        </div>
      </section>

      {empty && <section className="surface-panel"><h2>{text(language, "有効な観測結果はまだありません", "No valid observation yet")}</h2><p>{text(language, "durable evidenceが形成されるまで推測せず空として表示します。", "The Lab remains empty until durable evidence exists; no result is inferred.")}</p></section>}

      <section className="surface-panel">
        <div className="section-heading"><div><p className="eyebrow">LATEST MANAGED RUN</p><h2>{display(latestRun.run_id)}</h2></div><span className={`status-badge status-${latestRun.status === "completed" ? "online" : "degraded"}`}>{latestRun.status}</span></div>
        <div className="memory-inspector-counts"><div><strong>{latestRun.slp_status}</strong><small>RelaySLP</small></div><div><strong>{latestRun.relayrun_status}</strong><small>RelayRUN</small></div><div><strong>{latestRun.relayctx_repack_status}</strong><small>RelayCTX Repack</small></div><div><strong>{latestRun.relayctx_unpack_status}</strong><small>RelayCTX Unpack</small></div></div>
        <p>{text(language, "完了時刻", "Completed")}: {display(latestRun.completed_at)} · {latestRun.duration_ms ?? "—"} ms</p>
      </section>

      <div className="memory-inspector-workspace">
        <section className="memory-inspector-list-panel surface-panel">
          <div className="section-heading compact-heading"><div><p className="eyebrow">FORMED PRIMARY MEM</p><h2>{text(language, "最近形成されたmemory", "Recently formed memories")}</h2></div></div>
          <div className="memory-inspector-record-list">
            {recent.items.map((item) => (
              <article className="memory-inspector-record memory-record-formed" key={item.memory_id}>
                <span className="memory-inspector-count-dot memory-dot-formed" aria-hidden="true" />
                <span><strong>{item.title || item.memory_id}</strong><span className="memory-inspector-record-summary">{item.bounded_summary}</span><span className="memory-inspector-record-meta">{item.source_kind} · {item.scope_label} · revision {item.revision}</span><span className="memory-inspector-actions"><button className="button button-secondary" type="button" onClick={() => setSelectedOperation({ kind: "correct", memory: item })}>Correct</button><button className="button button-secondary" type="button" onClick={() => setSelectedOperation({ kind: "forget", memory: item })}>Forget</button></span></span>
              </article>
            ))}
            {recent.items.length === 0 && <p>{text(language, "active formed memoryはありません。", "No active formed memory.")}</p>}
          </div>
        </section>

        <section className="memory-inspector-detail-panel surface-panel">
          <div className="section-heading"><div><p className="eyebrow">HELD / BLOCKED</p><h2>{text(language, "不成立・保留outcome", "Held and blocked outcomes")}</h2></div></div>
          {held.items.map((item) => (
            <article key={item.outcome_id} className={`memory-inspector-record memory-record-${item.status}`}>
              <span className={`memory-inspector-count-dot memory-dot-${item.status}`} aria-hidden="true" />
              <span><strong>{item.status}: {shortId(item.outcome_id)}</strong><span className="memory-inspector-record-meta">{item.reason_ids.join(", ") || "no bounded reason"}</span>{item.status === "held" && <span className="memory-inspector-actions"><button className="button button-secondary" type="button" onClick={() => setSelectedOperation({ kind: "held", outcome: item })}>Apply / Discard</button></span>}</span>
            </article>
          ))}
          {held.items.length === 0 && <p>{text(language, "held / blocked outcomeはありません。", "No held or blocked outcome.")}</p>}
          <p>{text(language, "held candidate本文・model output・queue payloadは表示しません。", "Held candidate body, model output, and queue payload are not displayed.")}</p>
        </section>
      </div>

      {selectedOperation?.kind === "correct" && <PrimaryMemoryCorrectPanel language={language} characterId={activeCharacter.characterId} namespace={state.namespace} memory={selectedOperation.memory} onApplied={() => setRefreshKey((value) => value + 1)} />}
      {selectedOperation?.kind === "forget" && <PrimaryMemoryForgetPanel language={language} characterId={activeCharacter.characterId} namespace={state.namespace} memory={selectedOperation.memory} onApplied={() => setRefreshKey((value) => value + 1)} />}
      {selectedOperation?.kind === "held" && <HeldGovernancePanel language={language} characterId={activeCharacter.characterId} namespace={state.namespace} outcome={selectedOperation.outcome} onApplied={() => setRefreshKey((value) => value + 1)} />}

      <section className="surface-panel">
        <div className="section-heading"><div><p className="eyebrow">USED IN LATEST RESPONSE</p><h2>{text(language, "backend-bound contextへ注入されたmemory", "Memories injected into backend-bound context")}</h2></div></div>
        <p>retrieval={String(used.retrieval_attempted)} · selected={String(used.selected)} · injection={String(used.relayctx_injection_performed)} · backend-bound={String(used.backend_bound_included)} · response-complete={String(used.response_generation_completed)}</p>
        {used.items.map((item) => <article className="memory-inspector-record memory-record-formed" key={item.memory_id}><span><strong>{item.memory_id}</strong><span className="memory-inspector-record-summary">{item.injected_summary}</span>{item.representation_changed && item.current_summary !== null && <span className="memory-inspector-record-summary">{text(language, "現在の修正版", "Current corrected representation")}: {item.current_summary}</span>}<span className="memory-inspector-record-meta">{item.representation_changed ? text(language, "この過去runは旧representationを使用", "This past run used the prior representation") : text(language, "現在表現と一致", "Matches current representation")}</span></span></article>)}
        {used.items.length === 0 && <p>{text(language, "最新応答で使用されたmemory証拠はありません。", "No used-memory evidence for the latest response.")}</p>}
      </section>

      <section className="surface-panel">
        <div className="section-heading"><div><p className="eyebrow">USED MEMORY LIFECYCLE</p><h2>{text(language, "現在lifecycle overlay", "Current lifecycle overlay")}</h2></div></div>
        {usedLifecycle.items.map((item) => <article className={`memory-inspector-record memory-record-${item.current_lifecycle_state === "active" ? "formed" : "blocked"}`} key={item.memory_id}><span><strong>{item.memory_id}</strong><span className="memory-inspector-record-summary">{item.injected_summary}</span><span className="memory-inspector-record-meta">current={item.current_lifecycle_state} · lifecycle-changed={String(item.lifecycle_changed)} · representation-changed={String(item.representation_changed)}</span></span></article>)}
        {usedLifecycle.items.length === 0 && <p>{text(language, "最新応答で使用されたmemory lifecycle証拠はありません。", "No used-memory lifecycle evidence for the latest response.")}</p>}
      </section>

      <section className="surface-panel">
        <h2>{text(language, "このPhaseの操作境界", "Operation boundary for this phase")}</h2>
        <div className="memory-inspector-actions"><button className="button button-secondary" type="button" disabled>forget: active formed item row</button><button className="button button-secondary" type="button" disabled>pin / unpin</button><button className="button button-secondary" type="button" disabled>merge</button><button className="button button-secondary" type="button" disabled>held apply / discard: explicit confirm only</button></div>
        <p>{text(language, "I-7Cはheld outcomeの明示的なApply / Discard governance decisionだけを追加します。worker / scheduler / retry loop / daemonは起動しません。", "I-7C adds only explicit Apply / Discard governance decisions for held outcomes. It does not start workers, schedulers, retry loops, or daemons.")}</p>
      </section>
    </div>
  );
}
