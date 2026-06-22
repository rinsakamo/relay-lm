import type { Language } from "../domain/lab";

const ja = {
  sourceEyebrow: "READ-ONLY LAB API",
  sourceLoading: "server projectionを読み込んでいます",
  sourceServer: "server-owned projectionを表示中",
  sourceFallback: "mock fallbackを表示中",
  sourceLoadingDescription: "GET /lab/api/settings と GET /lab/api/characters を待機しています。",
  sourceServerDescription: "secret、source content、raw traceを含まないruntime config projectionです。",
  sourceFallbackDescription: "Lab APIへ到達できないため、既存のbrowser-local mock projectionを表示しています。",
  retry: "再読込",
  schema: "Schema",
  registryEmpty: "runtime configに登録済みcharacterはありません。",
  sourceComplete: "persona source set: complete",
  sourceIncomplete: "persona source set: incomplete",
  routeCount: "route count",
  notConfigured: "not configured",
  serverOwnedEndpoint: "server-owned endpoint",
  contentFreeCount: "content-free event count",
  loadedCredentialCount: "loaded credential fields",
} as const;

type SettingsA7MessageKey = keyof typeof ja;

const en: Record<SettingsA7MessageKey, string> = {
  sourceEyebrow: "READ-ONLY LAB API",
  sourceLoading: "Loading the server projection",
  sourceServer: "Showing the server-owned projection",
  sourceFallback: "Showing the mock fallback",
  sourceLoadingDescription: "Waiting for GET /lab/api/settings and GET /lab/api/characters.",
  sourceServerDescription:
    "This runtime-config projection contains no secrets, source content, or raw traces.",
  sourceFallbackDescription:
    "The Lab API is unavailable, so the existing browser-local mock projection is shown.",
  retry: "Reload",
  schema: "Schema",
  registryEmpty: "No characters are registered in the runtime config.",
  sourceComplete: "persona source set: complete",
  sourceIncomplete: "persona source set: incomplete",
  routeCount: "route count",
  notConfigured: "not configured",
  serverOwnedEndpoint: "server-owned endpoint",
  contentFreeCount: "content-free event count",
  loadedCredentialCount: "loaded credential fields",
};

const catalogs: Record<Language, Record<SettingsA7MessageKey, string>> = { ja, en };

export function settingsA7Message(language: Language, key: SettingsA7MessageKey): string {
  return catalogs[language][key];
}

export type { SettingsA7MessageKey };
