import type { ReactNode } from "react";
import type { CharacterSummary, Language } from "../../domain/lab";
import type {
  LabCharacterProjection,
  LabSettingsProjection,
} from "../settings/managementApi";
import "./characterWorkspace.css";

type WorkspaceSurface = "character" | "scenes" | "relationships" | "memory" | "runtime" | "advanced";
type StatusKind = "ready" | "pending" | "optional" | "advanced" | "blocked";

interface CharacterWorkspacePageProps {
  surface: WorkspaceSurface;
  language: Language;
  activeCharacter: CharacterSummary;
  characterProjection: LabCharacterProjection | null;
  settingsProjection: LabSettingsProjection | null;
}

interface WorkspaceCardProps {
  title: string;
  eyebrow: string;
  description: string;
  status?: StatusKind;
  children?: ReactNode;
}

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function WorkspaceHero({ language, title, eyebrow, description }: { language: Language; title: string; eyebrow: string; description: string }) {
  return (
    <section className="workspace-hero panel-grid-surface">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p className="hero-description">{description}</p>
      <p className="boundary-note">
        {text(
          language,
          "Browserはpresentation / interactionのみです。source自動更新、worker起動、runtime state更新は行いません。",
          "The browser is presentation / interaction only. It does not auto-write sources, start workers, or update runtime state.",
        )}
      </p>
    </section>
  );
}

function WorkspaceCard({ title, eyebrow, description, status = "ready", children }: WorkspaceCardProps) {
  return (
    <article className="surface-panel workspace-card">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <span className={`workspace-pill workspace-pill-${status}`}>{status}</span>
      </div>
      <p className="panel-description">{description}</p>
      {children}
    </article>
  );
}

function FactList({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="workspace-facts">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function VocabularyList({ items }: { items: string[] }) {
  return (
    <div className="workspace-vocabulary" aria-label="workspace vocabulary">
      {items.map((item) => <span key={item}>{item}</span>)}
    </div>
  );
}

function configuredLabel(language: Language, configured: boolean | null): string {
  if (configured === null) return text(language, "projection未接続", "projection unavailable");
  return configured ? text(language, "configured", "configured") : text(language, "missing / incomplete", "missing / incomplete");
}

function CharacterSurface(props: CharacterWorkspacePageProps) {
  const { language, characterProjection } = props;
  const sourceComplete = characterProjection?.source_complete ?? null;
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="CHARACTER SOURCES"
        title="Character"
        description={text(
          language,
          "SOUL / STYLE / EMOTION / BOUNDARY / optional LOREを、人間が読むCharacter Workspaceのsource面として表示します。編集はdraft / preview onlyで、明示save APIなしでは保存しません。",
          "Shows SOUL / STYLE / EMOTION / BOUNDARY / optional LORE as human-facing Character Workspace sources. Editing is draft / preview only unless an explicit save API exists.",
        )}
      />
      <section className="workspace-grid two-column-grid">
        <WorkspaceCard
          title="SOUL.md"
          eyebrow="IDENTITY SOURCE"
          description={text(language, "identity / values / relationship semanticsのsource。Relationship role assignmentとは分離します。", "Identity, values, and abstract relationship semantics source. Relationship role assignment stays separate.")}
          status="pending"
        >
          <FactList items={[["status", configuredLabel(language, characterProjection?.soul_configured ?? null)], ["source", "workspace-relative only"]]} />
        </WorkspaceCard>
        <WorkspaceCard
          title="STYLE.md"
          eyebrow="OUTPUT SURFACE"
          description={text(language, "口調、キャラ付け、formatting、presentation rulesを扱います。SOUL identityやmemory truthは所有しません。", "Owns voice, roleplay flavor, formatting, and presentation rules. It does not own SOUL identity or memory truth.")}
          status="pending"
        >
          <FactList items={[["status", configuredLabel(language, characterProjection?.output_policy_configured ?? null)], ["save", "preview only / not saved"]]} />
        </WorkspaceCard>
        <WorkspaceCard
          title="EMOTION.md"
          eyebrow="EMOTION MODULATION"
          description={text(language, "emotionごとの表現調整source。現在感情stateの保存やscene ownershipは行いません。", "Emotion-specific expression modulation source. It does not persist current emotion state or own scenes.")}
          status="pending"
        />
        <WorkspaceCard
          title="BOUNDARY.md"
          eyebrow="HIGH PRIORITY BOUNDARY"
          description={text(language, "Character Workspace内で見落としてはいけない境界sourceです。通常会話からの自動更新は禁止です。", "The boundary source must stay visible. Ordinary conversation must not auto-update it.")}
          status="blocked"
        >
          <FactList items={[["priority", "visible before optional LORE"], ["write", "proposal / explicit approval required"]]} />
        </WorkspaceCard>
        <WorkspaceCard
          title="LORE.md"
          eyebrow="OPTIONAL LORE"
          description={text(language, "任意sourceです。存在しない場合もCharacter Workspaceはfail-closed summaryを表示します。", "Optional source. Missing LORE keeps the workspace on a fail-closed summary.")}
          status="optional"
        >
          <FactList items={[["workspace", configuredLabel(language, sourceComplete)], ["content", "not shown in diagnostics"]]} />
        </WorkspaceCard>
      </section>
    </div>
  );
}

function ScenesSurface({ language }: CharacterWorkspacePageProps) {
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="SCENE WIKI"
        title="Scenes"
        description={text(language, "SCENE policy、active scenes、scene inboxを分けて表示します。scene classifierはstructured classifier pending / selection preview扱いです。", "Separates SCENE policy, active scenes, and scene inbox. The scene classifier remains structured classifier pending / selection preview.")}
      />
      <section className="workspace-grid three-column-grid">
        <WorkspaceCard title="SCENE.md" eyebrow="SCENE POLICY" description={text(language, "RelaySCNがscene policy ownerです。RelayEMOをscene ownerとして表示しません。", "RelaySCN remains the scene policy owner. RelayEMO is not presented as the scene owner.")} />
        <WorkspaceCard title="scenes/*.md" eyebrow="ACTIVE SCENES" description={text(language, "known scene pagesはcontent-free summaryのみ。active sceneのbrowser-owned決定をruntime authorityにしません。", "Known scene pages use content-free summaries only. Browser-owned active scene decisions are not runtime authority.")} />
        <WorkspaceCard title="scenes/_inbox/*.md" eyebrow="SCENE INBOX" description={text(language, "candidate / stagingです。直接prompt注入対象ではありません。auto-merge / auto-applyはCW-A4まで非対象です。", "Candidate / staging only. It is not direct prompt content. Auto-merge / auto-apply stays out of CW-A3.")} status="pending" />
      </section>
      <WorkspaceCard title="scene_units.jsonl / context_projection.json" eyebrow="CW-A2 BUILD SUMMARY" description={text(language, "利用できる場合はcounts / hashes / statusだけを表示します。raw scene page bodyやconfidenceの本文根拠は出しません。", "When available, only counts / hashes / status are displayed. Raw scene bodies and confidence evidence text are not shown.")} />
    </div>
  );
}

function RelationshipsSurface({ language }: CharacterWorkspacePageProps) {
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="RELATIONSHIP LAYER"
        title="Relationships"
        description={text(language, "RelayRELのrole vocabularyとtarget-specific relationshipsをSOUL identityから分離して見せます。重要parameterはproposal / explicit approval requiredです。", "Shows RelayREL role vocabulary and target-specific relationships separately from SOUL identity. Important parameters require proposal / explicit approval.")}
      />
      <section className="workspace-grid three-column-grid">
        <WorkspaceCard title="RELATIONSHIP.md" eyebrow="ROLE VOCABULARY" description={text(language, "role / parameter vocabularyのsource。relationship変更をSOULへ混入しません。", "Role / parameter vocabulary source. Relationship changes are not mixed into SOUL.")} />
        <WorkspaceCard title="relationships/user.md" eyebrow="SELECTED TARGET" description={text(language, "selected target contextをcontent-freeに表示します。target-specific sensitive detailsはgeneric traceへ出しません。", "Shows selected target context content-free. Target-specific sensitive details are not emitted to generic traces.")} />
        <WorkspaceCard title="relationships/_inbox/**" eyebrow="PENDING REL PROPOSALS" description={text(language, "pending proposal置き場です。browser-owned role assignmentやmost_important_person等の自動確定は行いません。", "Pending proposal area. Browser-owned role assignment and automatic critical relationship decisions are not applied.")} status="pending" />
      </section>
      <WorkspaceCard title="public / private scene disclosure" eyebrow="DISCLOSURE MODEL" description={text(language, "public/private sceneによりfamiliarityやmemory disclosureが変わることを説明します。実runtimeの決定権はRelayREL/RelaySCN側です。", "Explains that public/private scenes can change familiarity and memory disclosure. Runtime authority stays with RelayREL / RelaySCN.")} />
    </div>
  );
}

function MemorySurface({ language }: CharacterWorkspacePageProps) {
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="MEMORY WIKI"
        title="Memory Wiki"
        description={text(language, "MEMORY.md、memory pages、blocks、links、archive、forgotten itemsを人間向け語彙で整理します。one-file-per-memory前提には戻しません。", "Organizes MEMORY.md, memory pages, blocks, links, archive, and forgotten items with human-facing vocabulary. It does not revive a one-file-per-memory model.")}
      />
      <VocabularyList items={["important", "active", "archived", "forgotten", "held", "blocked", "proposal", "source"]} />
      <section className="workspace-grid three-column-grid">
        <WorkspaceCard title="MEMORY.md" eyebrow="MEMORY POLICY" description={text(language, "memory policy source。all memory pagesをprompt注入すると示唆しません。", "Memory policy source. The UI does not imply that all memory pages are injected into prompts.")} />
        <WorkspaceCard title="memory/**/*.md" eyebrow="PAGES / BLOCKS / CHUNKS" description={text(language, "memory page、memory block、retrieval chunkを別語彙で表示します。本文は対象画面だけで慎重に扱います。", "Separates memory page, memory block, and retrieval chunk vocabulary. Text bodies are handled only on intentional viewing surfaces.")} />
        <WorkspaceCard title="memory/inbox/**" eyebrow="CANDIDATE STAGING" description={text(language, "candidate / stagingであり、SLP auto-maintenanceやauto-mergeはCW-A4の非対象です。", "Candidate / staging only. SLP auto-maintenance and auto-merge are CW-A4 non-goals here.")} status="pending" />
        <WorkspaceCard title="memory/forgotten/**" eyebrow="FORGOTTEN ITEMS" description={text(language, "ordinary prompt対象外であることを明示します。historical auditやdiagnostic詳細はAdvancedへ分離します。", "Explicitly outside ordinary prompt candidates. Historical audit and diagnostic details move to Advanced.")} status="blocked" />
        <WorkspaceCard title="governance details" eyebrow="ADVANCED SEPARATION" description={text(language, "revision、pin state、apply token、queue / worker detailsはAdvancedに寄せます。", "Revision, pin state, apply token, and queue / worker details are kept in Advanced.")} status="advanced" />
        <WorkspaceCard title="used-memory evidence" eyebrow="RUNTIME LINK" description={text(language, "backend-bound contextに入ったかはRuntimeのused-memory evidenceをauthorityにし、visible response textから推測しません。", "Whether memory entered backend-bound context is based on Runtime used-memory evidence, not inferred from visible response text.")} />
      </section>
    </div>
  );
}

function RuntimeSurface({ language, characterProjection, settingsProjection }: CharacterWorkspacePageProps) {
  const componentCount = settingsProjection?.runtime_components.length ?? 0;
  const routeCount = characterProjection?.route_models.length ?? 0;
  const namespaceCount = characterProjection?.memory_namespaces.length ?? 0;
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="CONTENT-FREE RUNTIME"
        title="Runtime"
        description={text(language, "latest used scene / emotion / relationship / memory / context projectionをcontent-freeに表示します。backend prompt全文とraw traceは表示しません。", "Shows latest used scene / emotion / relationship / memory / context projection content-free. Full backend prompt and raw traces are not displayed.")}
      />
      <section className="workspace-grid three-column-grid">
        <WorkspaceCard title="latest used scene" eyebrow="RelaySCN" description={text(language, "scene selectionはruntime authorityであり、UI previewから本番適用しません。", "Scene selection is runtime authority and is not applied from UI preview.")} />
        <WorkspaceCard title="latest emotion" eyebrow="RelayEMO" description={text(language, "emotion hint summaryだけを扱い、scene ownerとして扱いません。", "Only emotion hint summaries are shown; RelayEMO is not treated as scene owner.")} />
        <WorkspaceCard title="latest relationship projection" eyebrow="RelayREL" description={text(language, "relationship projectionはSOUL identityとは別layerです。", "Relationship projection is a separate layer from SOUL identity.")} />
        <WorkspaceCard title="latest memory / used-memory evidence" eyebrow="RelayMEM" description={text(language, "backend-bound contextへの採用はused-memory evidenceがauthorityです。", "Used-memory evidence is the authority for backend-bound context inclusion.")} />
        <WorkspaceCard title="context_projection.json" eyebrow="CW-A2" description={text(language, "Tier 1 / Tier 2 / Tier 3をcounts / hash / statusで見える化します。source本文は表示しません。", "Tier 1 / Tier 2 / Tier 3 are visualized as counts / hash / status only. Source text is not shown.")}>
          <FactList items={[["route models", String(routeCount)], ["namespaces", String(namespaceCount)], ["runtime components", String(componentCount)]]} />
        </WorkspaceCard>
        <WorkspaceCard title="Recent Workspace Changes" eyebrow="HOME SUMMARY SOURCE" description={text(language, "Homeに表示する場合もcontent-free projectionまたは既存content-free observationだけを使います。", "When shown on Home, recent changes must come only from content-free projection or existing content-free observation.")} />
      </section>
    </div>
  );
}

function AdvancedSurface({ language, settingsProjection }: CharacterWorkspacePageProps) {
  return (
    <div className="workspace-surface">
      <WorkspaceHero
        language={language}
        eyebrow="DEVELOPER / GOVERNANCE"
        title="Advanced"
        description={text(language, "内部governance、diagnostics、existing loopback management controlsを集約します。Advancedへ移してもbrowser authorityは増えません。", "Collects internal governance, diagnostics, and existing loopback management controls. Moving them to Advanced does not increase browser authority.")}
      />
      <VocabularyList items={["memory_id", "revision", "pin_state", "lifecycle state", "apply token", "queue", "worker", "audit", "raw content-free projections"]} />
      <section className="workspace-grid two-column-grid">
        <WorkspaceCard title="memory governance" eyebrow="EXPLICIT LOOPBACK CONTRACTS" description={text(language, "Correct / Forget / Pin / Unpin / Held Governanceの詳細は既存token / revision / security gatingを維持します。", "Correct / Forget / Pin / Unpin / Held Governance details keep the existing token / revision / security gating.")} status="advanced" />
        <WorkspaceCard title="queue / worker / audit" eyebrow="DIAGNOSTICS ONLY" description={text(language, "queue recordsやworker状態は診断表示のみです。mutation、retry、worker startは提供しません。", "Queue records and worker state are diagnostic only. Mutation, retry, and worker start are not provided.")} status="advanced" />
        <WorkspaceCard title="settings / runtime boundary" eyebrow="READ-ONLY" description={text(language, "loopback / same-origin前提、navigation lock、stale fencingを維持します。", "Preserves loopback / same-origin assumptions, navigation lock, and stale fencing.")}>
          <FactList items={[["settings projection", settingsProjection ? "available" : "fail-closed"], ["raw prompt", "not displayed"]]} />
        </WorkspaceCard>
        <WorkspaceCard title="raw content-free projections" eyebrow="SAFE RAW VIEW" description={text(language, "content-bearing protected source、backend prompt、URL credential、API keyは表示しません。", "Content-bearing protected source, backend prompt, URL credential, and API keys are not displayed.")} status="advanced" />
      </section>
    </div>
  );
}

export function CharacterWorkspacePage(props: CharacterWorkspacePageProps) {
  switch (props.surface) {
    case "character":
      return <CharacterSurface {...props} />;
    case "scenes":
      return <ScenesSurface {...props} />;
    case "relationships":
      return <RelationshipsSurface {...props} />;
    case "memory":
      return <MemorySurface {...props} />;
    case "runtime":
      return <RuntimeSurface {...props} />;
    case "advanced":
      return <AdvancedSurface {...props} />;
  }
}
