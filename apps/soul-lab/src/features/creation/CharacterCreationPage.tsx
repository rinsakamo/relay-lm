import type { ReactNode } from "react";
import type { Language } from "../../domain/lab";

function text(language: Language, ja: string, en: string): string {
  return language === "ja" ? ja : en;
}

function CreationCard({ eyebrow, title, body, children }: { eyebrow: string; title: string; body: string; children?: ReactNode }) {
  return (
    <article className="surface-panel workspace-card">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <span className="workspace-pill workspace-pill-pending">approval</span>
      </div>
      <p className="panel-description">{body}</p>
      {children}
    </article>
  );
}

function PillList({ items }: { items: string[] }) {
  return <div className="workspace-vocabulary">{items.map((item) => <span key={item}>{item}</span>)}</div>;
}

export function CharacterCreationPage({ language, noCharacter = false }: { language: Language; noCharacter?: boolean }) {
  return (
    <div className="workspace-surface" data-testid="character-creation-page">
      <section className="workspace-hero panel-grid-surface">
        <p className="eyebrow">CW-A5 CHARACTER CREATION</p>
        <h1>{noCharacter ? text(language, "No character found.", "No character found.") : "Character Creation"}</h1>
        <p className="hero-description">
          {text(
            language,
            "有効なCharacter Workspaceがない場合は、自動default characterを作らず、Quick Create / Advanced Create / Showcase / Importから明示作成します。",
            "When no valid Character Workspace exists, RelayLM does not auto-create a default character. Use Quick Create, Advanced Create, Showcase, or Import with explicit approval.",
          )}
        </p>
        <p className="boundary-note">
          {text(
            language,
            "templateはsource候補です。workspace commitとactive character設定はユーザーの明示操作が必要です。",
            "Templates are source candidates. Workspace commit and active-character selection require explicit user action.",
          )}
        </p>
      </section>

      <section className="workspace-grid two-column-grid">
        <CreationCard
          eyebrow="QUICK CREATE"
          title={text(language, "Create quickly", "Create quickly")}
          body={text(language, "template / name / tone / intended use だけで完全なfile-first workspaceをstageします。", "Stage a complete file-first workspace from template / name / tone / intended use only.")}
        >
          <PillList items={["template", "name", "tone", "intended use", "explicit create"]} />
          <button className="primary-action" type="button">{text(language, "Create character（明示承認）", "Create character (explicit approval)")}</button>
        </CreationCard>

        <CreationCard
          eyebrow="ADVANCED CREATE"
          title={text(language, "Create in detail", "Create in detail")}
          body={text(language, "source modelを直接見ながら、validation / compiled preview / approval後にcommitします。", "Expose the source model directly, then commit only after validation, compiled preview, and approval.")}
        >
          <PillList items={["SOUL", "STYLE", "EMOTION", "RELATIONSHIP", "SCENE", "MEMORY", "BOUNDARY", "LORE", "Preview"]} />
        </CreationCard>

        <CreationCard
          eyebrow="SHOWCASE"
          title={text(language, "Try a showcase character", "Try a showcase character")}
          body={text(language, "grown-character体験をtemplate_exampleとして明示し、use as-is / use as starterを選べます。", "Showcase characters mark curated examples as template_example and support use as-is / use as starter.")}
        >
          <PillList items={["Showcase Friendly Companion", "Showcase VTuber", "Use as-is", "Use as starter"]} />
        </CreationCard>

        <CreationCard
          eyebrow="IMPORT"
          title={text(language, "Import", "Import")}
          body={text(language, "外部templateはscripts / symlinks / path traversal / .relaylm runtime artifactsをfail-closedで拒否します。", "External templates fail closed on scripts, symlinks, path traversal, and .relaylm runtime artifacts.")}
        >
          <PillList items={["This template was checked", "No scripts", "No runtime state", "No build import"]} />
        </CreationCard>
      </section>
    </div>
  );
}
