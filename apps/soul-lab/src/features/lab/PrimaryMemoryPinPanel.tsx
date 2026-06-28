import { useEffect, useRef, useState } from "react";
import type { Language } from "../../domain/lab";
import type { LabRecentMemoryItem } from "./observationApi";
import { applyMemoryPin, applyMemoryUnpin, preflightMemoryPin, preflightMemoryUnpin, type MemoryPinApplyReceipt, type MemoryPinPreflight } from "./pinApi";

interface PrimaryMemoryPinPanelProps {
  language: Language;
  characterId: string;
  namespace: string;
  memory: LabRecentMemoryItem;
  onApplied: () => void;
}

type Operation = "pin" | "unpin";
type PanelState = { kind: "idle" } | { kind: "preflight"; operation: Operation; reason: string; operationId: string; value: MemoryPinPreflight } | { kind: "applied"; receipt: MemoryPinApplyReceipt } | { kind: "error"; code: string };

function text(language: Language, ja: string, en: string): string { return language === "ja" ? ja : en; }
function defaultReason(operation: Operation, memoryId: string): string { return `${operation} requested for ${memoryId.slice(0, 12)}`; }

export function PrimaryMemoryPinPanel({ language, characterId, namespace, memory, onApplied }: PrimaryMemoryPinPanelProps) {
  const [panelState, setPanelState] = useState<PanelState>({ kind: "idle" });
  const generation = useRef(0);

  useEffect(() => {
    setPanelState({ kind: "idle" });
    generation.current += 1;
  }, [characterId, namespace, memory.memory_id, memory.revision]);

  async function runPreflight(operation: Operation) {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const reason = defaultReason(operation, memory.memory_id);
    const operationId = `i5b-${operation}-${Date.now()}`;
    try {
      const value = operation === "pin"
        ? await preflightMemoryPin(characterId, namespace, memory.memory_id, { expectedRevision: memory.revision, reason, operationId }, controller.signal)
        : await preflightMemoryUnpin(characterId, namespace, memory.memory_id, { expectedRevision: memory.revision, reason, operationId }, controller.signal);
      if (!controller.signal.aborted && generation.current === currentGeneration) setPanelState({ kind: "preflight", operation, reason, operationId, value });
    } catch (error) {
      if (!controller.signal.aborted && generation.current === currentGeneration) setPanelState({ kind: "error", code: error instanceof Error ? error.message : "runtime_unavailable" });
    }
  }

  async function confirmApply() {
    if (panelState.kind !== "preflight" || panelState.value.status !== "ready" || panelState.value.apply_token === null) return;
    const controller = new AbortController();
    const currentGeneration = generation.current;
    try {
      const receipt = panelState.operation === "pin"
        ? await applyMemoryPin(characterId, namespace, memory.memory_id, { expectedRevision: memory.revision, reason: panelState.reason, operationId: panelState.operationId, applyToken: panelState.value.apply_token }, controller.signal)
        : await applyMemoryUnpin(characterId, namespace, memory.memory_id, { expectedRevision: memory.revision, reason: panelState.reason, operationId: panelState.operationId, applyToken: panelState.value.apply_token }, controller.signal);
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        setPanelState({ kind: "applied", receipt });
        onApplied();
      }
    } catch (error) {
      if (!controller.signal.aborted && generation.current === currentGeneration) setPanelState({ kind: "error", code: error instanceof Error ? error.message : "runtime_unavailable" });
    }
  }

  return (
    <section className="surface-panel" aria-live="polite">
      <div className="section-heading"><div><p className="eyebrow">PIN / UNPIN</p><h2>{text(language, "Primary MEMのPin / Unpin", "Pin / Unpin Primary MEM")}</h2></div></div>
      <p>{text(language, "明示的な確認時だけPin / Unpinを適用します。hover、選択、refreshでは適用しません。", "Pin / Unpin is applied only after explicit confirmation; hover, selection, and refresh never apply it.")}</p>
      <p className="memory-inspector-record-meta">memory={memory.memory_id} · revision {memory.revision}</p>
      <div className="memory-inspector-actions">
        <button className="button button-secondary" type="button" onClick={() => void runPreflight("pin")}>Pin preflight</button>
        <button className="button button-secondary" type="button" onClick={() => void runPreflight("unpin")}>Unpin preflight</button>
      </div>
      {panelState.kind === "preflight" && (
        <div className="memory-inspector-boundary-card">
          <p>{panelState.operation}: {panelState.value.current_pin_state} → {panelState.value.target_pin_state}</p>
          <button className="button button-primary" type="button" disabled={panelState.value.status !== "ready"} onClick={() => void confirmApply()}>{text(language, "明示的にPin / Unpinを適用", "Explicitly apply Pin / Unpin")}</button>
        </div>
      )}
      {panelState.kind === "applied" && <p>{panelState.receipt.status} · target={panelState.receipt.target_pin_state}</p>}
      {panelState.kind === "error" && <p>{panelState.code}</p>}
    </section>
  );
}
