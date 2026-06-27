import { useEffect, useRef, useState } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import { ConnectedLabObservationPage } from "../lab/ConnectedLabObservationPage";
import { loadLabManagementProjections } from "../settings/managementApi";
import { LifecycleVisibilityPanel } from "./LifecycleVisibilityPanel";
import {
  LifecycleVisibilityError,
  loadLifecycleVisibility,
  type LabLifecycleVisibilityProjection,
} from "./lifecycleVisibilityApi";

interface ConnectedLifecycleLabObservationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  onInspectorLockChange: (locked: boolean) => void;
}

type LifecycleLoadState =
  | { kind: "loading"; namespace: string | null }
  | { kind: "real"; namespace: string; projection: LabLifecycleVisibilityProjection }
  | { kind: "error"; namespace: string | null; code: string };

export function ConnectedLifecycleLabObservationPage({
  language,
  activeCharacter,
  onInspectorLockChange,
}: ConnectedLifecycleLabObservationPageProps) {
  const [state, setState] = useState<LifecycleLoadState>({ kind: "loading", namespace: null });
  const generation = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const requestGeneration = ++generation.current;
    let namespaceForError: string | null = null;
    setState({ kind: "loading", namespace: null });
    void (async () => {
      try {
        const management = await loadLabManagementProjections(controller.signal);
        const character = management.characters.characters.find(
          (item) => item.character_id === activeCharacter.characterId,
        );
        const namespace = [...(character?.memory_namespaces ?? [])].sort()[0];
        if (!namespace) throw new LifecycleVisibilityError("namespace_unavailable");
        namespaceForError = namespace;
        setState({ kind: "loading", namespace });
        const projection = await loadLifecycleVisibility(activeCharacter.characterId, namespace, controller.signal);
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        if (projection.character_id !== activeCharacter.characterId || projection.namespace !== namespace) return;
        setState({ kind: "real", namespace, projection });
      } catch (error) {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        const code = error instanceof LifecycleVisibilityError ? error.code : "lifecycle_visibility_unavailable";
        setState({ kind: "error", namespace: namespaceForError, code });
      }
    })();
    return () => controller.abort();
  }, [activeCharacter.characterId]);

  return (
    <>
      <ConnectedLabObservationPage
        language={language}
        activeCharacter={activeCharacter}
        onInspectorLockChange={onInspectorLockChange}
      />
      <LifecycleVisibilityPanel
        language={language}
        characterId={activeCharacter.characterId}
        namespace={state.namespace}
        projection={state.kind === "real" ? state.projection : null}
        loading={state.kind === "loading"}
        errorCode={state.kind === "error" ? state.code : null}
        surface="observation"
      />
    </>
  );
}
