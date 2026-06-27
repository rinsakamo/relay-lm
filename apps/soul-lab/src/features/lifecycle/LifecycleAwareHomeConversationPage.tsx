import { useEffect, useMemo, useRef, useState } from "react";
import type { CharacterSummary, LabRoute, Language } from "../../domain/lab";
import type { LabCharacterProjection, LabSettingsProjection } from "../settings/managementApi";
import { HomeConversationPage } from "../home/HomeConversationPage";
import { LifecycleVisibilityPanel } from "./LifecycleVisibilityPanel";
import {
  LifecycleVisibilityError,
  loadLifecycleVisibility,
  type LabLifecycleVisibilityProjection,
} from "./lifecycleVisibilityApi";

interface LifecycleAwareHomeConversationPageProps {
  language: Language;
  activeCharacter: CharacterSummary;
  characterProjection: LabCharacterProjection | null;
  settingsProjection: LabSettingsProjection | null;
  onNavigate: (route: LabRoute) => void;
}

type LifecycleLoadState =
  | { kind: "loading"; namespace: string }
  | { kind: "real"; namespace: string; projection: LabLifecycleVisibilityProjection }
  | { kind: "error"; namespace: string | null; code: string };

export function LifecycleAwareHomeConversationPage(props: LifecycleAwareHomeConversationPageProps) {
  const { activeCharacter, characterProjection, language } = props;
  const [state, setState] = useState<LifecycleLoadState>({ kind: "error", namespace: null, code: "not_connected" });
  const generation = useRef(0);

  const namespace = useMemo(
    () => [...(characterProjection?.memory_namespaces ?? [])].sort()[0] ?? null,
    [characterProjection],
  );

  useEffect(() => {
    if (!namespace) {
      setState({ kind: "error", namespace: null, code: "namespace_unavailable" });
      return;
    }
    const controller = new AbortController();
    const requestGeneration = ++generation.current;
    setState({ kind: "loading", namespace });
    void loadLifecycleVisibility(activeCharacter.characterId, namespace, controller.signal)
      .then((projection) => {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        if (projection.character_id !== activeCharacter.characterId || projection.namespace !== namespace) return;
        setState({ kind: "real", namespace, projection });
      })
      .catch((error) => {
        if (controller.signal.aborted || generation.current !== requestGeneration) return;
        const code = error instanceof LifecycleVisibilityError ? error.code : "lifecycle_visibility_unavailable";
        setState({ kind: "error", namespace, code });
      });
    return () => controller.abort();
  }, [activeCharacter.characterId, namespace]);

  return (
    <>
      <HomeConversationPage {...props} />
      <LifecycleVisibilityPanel
        language={language}
        characterId={activeCharacter.characterId}
        namespace={state.namespace}
        projection={state.kind === "real" ? state.projection : null}
        loading={state.kind === "loading"}
        errorCode={state.kind === "error" ? state.code : null}
        surface="home"
      />
    </>
  );
}
