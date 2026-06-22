export type ServerProjectionState = "configured" | "unconfigured";

export interface LabRuntimeComponentProjection {
  component_id: string;
  label: string;
  state: ServerProjectionState;
  endpoint: string | null;
  model_labels: string[];
  capability: string;
  network_probe_performed: boolean;
}

export interface LabSettingsProjection {
  schema_version: "relaylm.lab.settings.v0";
  projection_kind: "read_only";
  source: "runtime_config";
  content_free: true;
  settings_write_supported: false;
  network_probe_performed: false;
  listen: {
    host: string;
    port: number;
    loopback_only: boolean;
  };
  runtime_components: LabRuntimeComponentProjection[];
  credential_boundary: {
    owner: "relaylm_server";
    browser_loaded: false;
    credential_fields_included: false;
  };
  diagnostics: {
    mode: "content_free";
    projected_event_count: number;
    credential_fields_loaded: number;
    source_content_included: false;
    raw_trace_included: false;
  };
}

export interface LabCharacterProjection {
  character_id: string;
  route_models: string[];
  backend_ids: string[];
  memory_namespaces: string[];
  modes: string[];
  soul_configured: boolean;
  output_policy_configured: boolean;
  relationship_anchor_configured: boolean;
  memory_seed_configured: boolean;
  stable_memory_summary_configured: boolean;
  source_complete: boolean;
  source_content_included: false;
  source_paths_included: false;
}

export interface LabCharactersProjection {
  schema_version: "relaylm.lab.characters.v0";
  projection_kind: "read_only";
  source: "runtime_config";
  content_free: true;
  persistent_registry_mutation_supported: false;
  credential_fields_included: false;
  source_content_included: false;
  characters: LabCharacterProjection[];
}

export interface LabManagementProjectionBundle {
  settings: LabSettingsProjection;
  characters: LabCharactersProjection;
}

export async function loadLabManagementProjections(
  signal?: AbortSignal,
): Promise<LabManagementProjectionBundle> {
  const [settingsPayload, charactersPayload] = await Promise.all([
    fetchJson("/lab/api/settings", signal),
    fetchJson("/lab/api/characters", signal),
  ]);

  const settings = parseSettingsProjection(settingsPayload);
  const characters = parseCharactersProjection(charactersPayload);
  if (!settings || !characters) {
    throw new Error("invalid_lab_management_projection");
  }
  return { settings, characters };
}

async function fetchJson(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });
  if (!response.ok) {
    throw new Error(`lab_management_http_${response.status}`);
  }
  return response.json() as Promise<unknown>;
}

function parseSettingsProjection(value: unknown): LabSettingsProjection | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    value.schema_version !== "relaylm.lab.settings.v0" ||
    value.projection_kind !== "read_only" ||
    value.source !== "runtime_config" ||
    value.content_free !== true ||
    value.settings_write_supported !== false ||
    value.network_probe_performed !== false ||
    !isRecord(value.listen) ||
    typeof value.listen.host !== "string" ||
    typeof value.listen.port !== "number" ||
    typeof value.listen.loopback_only !== "boolean" ||
    !Array.isArray(value.runtime_components) ||
    !isRecord(value.credential_boundary) ||
    value.credential_boundary.owner !== "relaylm_server" ||
    value.credential_boundary.browser_loaded !== false ||
    value.credential_boundary.credential_fields_included !== false ||
    !isRecord(value.diagnostics) ||
    value.diagnostics.mode !== "content_free" ||
    typeof value.diagnostics.projected_event_count !== "number" ||
    typeof value.diagnostics.credential_fields_loaded !== "number" ||
    value.diagnostics.source_content_included !== false ||
    value.diagnostics.raw_trace_included !== false
  ) {
    return null;
  }

  const runtimeComponents = value.runtime_components.map(parseRuntimeComponent);
  if (runtimeComponents.some((component) => component === null)) {
    return null;
  }

  return {
    schema_version: "relaylm.lab.settings.v0",
    projection_kind: "read_only",
    source: "runtime_config",
    content_free: true,
    settings_write_supported: false,
    network_probe_performed: false,
    listen: {
      host: value.listen.host,
      port: value.listen.port,
      loopback_only: value.listen.loopback_only,
    },
    runtime_components: runtimeComponents as LabRuntimeComponentProjection[],
    credential_boundary: {
      owner: "relaylm_server",
      browser_loaded: false,
      credential_fields_included: false,
    },
    diagnostics: {
      mode: "content_free",
      projected_event_count: value.diagnostics.projected_event_count,
      credential_fields_loaded: value.diagnostics.credential_fields_loaded,
      source_content_included: false,
      raw_trace_included: false,
    },
  };
}

function parseRuntimeComponent(value: unknown): LabRuntimeComponentProjection | null {
  if (
    !isRecord(value) ||
    typeof value.component_id !== "string" ||
    typeof value.label !== "string" ||
    (value.state !== "configured" && value.state !== "unconfigured") ||
    (value.endpoint !== null && typeof value.endpoint !== "string") ||
    !isStringArray(value.model_labels) ||
    typeof value.capability !== "string" ||
    value.network_probe_performed !== false
  ) {
    return null;
  }
  return {
    component_id: value.component_id,
    label: value.label,
    state: value.state,
    endpoint: value.endpoint,
    model_labels: value.model_labels,
    capability: value.capability,
    network_probe_performed: false,
  };
}

function parseCharactersProjection(value: unknown): LabCharactersProjection | null {
  if (
    !isRecord(value) ||
    value.schema_version !== "relaylm.lab.characters.v0" ||
    value.projection_kind !== "read_only" ||
    value.source !== "runtime_config" ||
    value.content_free !== true ||
    value.persistent_registry_mutation_supported !== false ||
    value.credential_fields_included !== false ||
    value.source_content_included !== false ||
    !Array.isArray(value.characters)
  ) {
    return null;
  }

  const characters = value.characters.map(parseCharacterProjection);
  if (characters.some((character) => character === null)) {
    return null;
  }

  return {
    schema_version: "relaylm.lab.characters.v0",
    projection_kind: "read_only",
    source: "runtime_config",
    content_free: true,
    persistent_registry_mutation_supported: false,
    credential_fields_included: false,
    source_content_included: false,
    characters: characters as LabCharacterProjection[],
  };
}

function parseCharacterProjection(value: unknown): LabCharacterProjection | null {
  if (
    !isRecord(value) ||
    typeof value.character_id !== "string" ||
    !isStringArray(value.route_models) ||
    !isStringArray(value.backend_ids) ||
    !isStringArray(value.memory_namespaces) ||
    !isStringArray(value.modes) ||
    typeof value.soul_configured !== "boolean" ||
    typeof value.output_policy_configured !== "boolean" ||
    typeof value.relationship_anchor_configured !== "boolean" ||
    typeof value.memory_seed_configured !== "boolean" ||
    typeof value.stable_memory_summary_configured !== "boolean" ||
    typeof value.source_complete !== "boolean" ||
    value.source_content_included !== false ||
    value.source_paths_included !== false
  ) {
    return null;
  }
  return {
    character_id: value.character_id,
    route_models: value.route_models,
    backend_ids: value.backend_ids,
    memory_namespaces: value.memory_namespaces,
    modes: value.modes,
    soul_configured: value.soul_configured,
    output_policy_configured: value.output_policy_configured,
    relationship_anchor_configured: value.relationship_anchor_configured,
    memory_seed_configured: value.memory_seed_configured,
    stable_memory_summary_configured: value.stable_memory_summary_configured,
    source_complete: value.source_complete,
    source_content_included: false,
    source_paths_included: false,
  };
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
