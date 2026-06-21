import { useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { Language } from "../../domain/lab";
import { adoptionMessage } from "../../locales/adoption";
import "./adoption.css";

type AdoptionMode = "choose" | "assistant" | "new" | "adopt" | "import" | "review" | "complete";
type AdoptionKind = "new" | "adopt" | "import";

type FileSlot = "soul" | "output" | "relationship";

interface AdoptionDraft {
  kind: AdoptionKind;
  displayName: string;
  characterId: string;
  sourceSummary: string[];
}

interface AdoptionPageProps {
  language: Language;
  onBackHome: () => void;
}

function slugify(value: string): string {
  const normalized = value
    .normalize("NFKD")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return normalized || "new-character";
}

function FilePicker({
  label,
  filename,
  onChange,
  language,
}: {
  label: string;
  filename: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  language: Language;
}) {
  return (
    <label className="adoption-file-picker">
      <span className="adoption-field-label">{label}</span>
      <span className="adoption-file-control">
        <span className="button button-secondary">{adoptionMessage(language, "chooseFile")}</span>
        <span className="adoption-file-name">
          {filename || adoptionMessage(language, "noFile")}
        </span>
      </span>
      <input type="file" accept=".md,text/markdown,text/plain" onChange={onChange} />
    </label>
  );
}

function ChoiceCard({
  marker,
  title,
  body,
  onClick,
}: {
  marker: string;
  title: string;
  body: string;
  onClick: () => void;
}) {
  return (
    <button className="adoption-choice-card" type="button" onClick={onClick}>
      <span className="adoption-choice-marker" aria-hidden="true">
        {marker}
      </span>
      <span>
        <strong>{title}</strong>
        <small>{body}</small>
      </span>
      <span className="adoption-choice-arrow" aria-hidden="true">
        →
      </span>
    </button>
  );
}

export function AdoptionPage({ language, onBackHome }: AdoptionPageProps) {
  const [mode, setMode] = useState<AdoptionMode>("choose");
  const [returnMode, setReturnMode] = useState<Exclude<AdoptionMode, "review" | "complete">>("choose");
  const [kind, setKind] = useState<AdoptionKind>("new");
  const [displayName, setDisplayName] = useState("");
  const [relationshipNote, setRelationshipNote] = useState("");
  const [sourceLocation, setSourceLocation] = useState("");
  const [sourceChecks, setSourceChecks] = useState({ soul: true, output: true, relationship: true });
  const [files, setFiles] = useState<Record<FileSlot, string>>({ soul: "", output: "", relationship: "" });
  const [initializeOutput, setInitializeOutput] = useState(true);
  const [initializeRelationship, setInitializeRelationship] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<AdoptionDraft | null>(null);

  const characterId = useMemo(() => slugify(displayName), [displayName]);

  function openMode(nextMode: Exclude<AdoptionMode, "review" | "complete">) {
    setError("");
    setMode(nextMode);
  }

  function reset() {
    setMode("choose");
    setReturnMode("choose");
    setKind("new");
    setDisplayName("");
    setRelationshipNote("");
    setSourceLocation("");
    setSourceChecks({ soul: true, output: true, relationship: true });
    setFiles({ soul: "", output: "", relationship: "" });
    setInitializeOutput(true);
    setInitializeRelationship(true);
    setError("");
    setDraft(null);
  }

  function setFile(slot: FileSlot, event: ChangeEvent<HTMLInputElement>) {
    const filename = event.target.files?.[0]?.name ?? "";
    setFiles((current) => ({ ...current, [slot]: filename }));
    setError("");
  }

  function validateAndReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (mode === "new") {
      if (!displayName.trim()) {
        setError(adoptionMessage(language, "validationName"));
        return;
      }

      setKind("new");
      setReturnMode("new");
      setDraft({
        kind: "new",
        displayName: displayName.trim(),
        characterId,
        sourceSummary: [
          "SOUL.md · safe default",
          "OUTPUT_POLICY.md · RelayLM recommended default",
          relationshipNote.trim()
            ? "RELATIONSHIP_ANCHOR.md · user-provided starting point"
            : "RELATIONSHIP_ANCHOR.md · safe default",
        ],
      });
      setMode("review");
      return;
    }

    if (mode === "adopt") {
      if (!sourceLocation.trim()) {
        setError(adoptionMessage(language, "validationLocation"));
        return;
      }
      if (!sourceChecks.soul || !sourceChecks.output || !sourceChecks.relationship) {
        setError(adoptionMessage(language, "validationSources"));
        return;
      }

      const inferredName = displayName.trim() || sourceLocation.trim().split(/[\\/]/).filter(Boolean).at(-1) || "Adopted character";
      setKind("adopt");
      setReturnMode("adopt");
      setDraft({
        kind: "adopt",
        displayName: inferredName,
        characterId: slugify(inferredName),
        sourceSummary: [
          `SOUL.md · ${sourceLocation.trim()}`,
          `OUTPUT_POLICY.md · ${sourceLocation.trim()}`,
          `RELATIONSHIP_ANCHOR.md · ${sourceLocation.trim()}`,
        ],
      });
      setMode("review");
      return;
    }

    if (mode === "import") {
      if (!files.soul) {
        setError(adoptionMessage(language, "validationSoul"));
        return;
      }
      if ((!files.output && !initializeOutput) || (!files.relationship && !initializeRelationship)) {
        setError(adoptionMessage(language, "validationCompanions"));
        return;
      }

      const inferredName = displayName.trim() || files.soul.replace(/\.md$/i, "") || "Imported character";
      setKind("import");
      setReturnMode("import");
      setDraft({
        kind: "import",
        displayName: inferredName,
        characterId: slugify(inferredName),
        sourceSummary: [
          `SOUL.md · ${files.soul}`,
          files.output
            ? `OUTPUT_POLICY.md · ${files.output}`
            : "OUTPUT_POLICY.md · safe default initialization",
          files.relationship
            ? `RELATIONSHIP_ANCHOR.md · ${files.relationship}`
            : "RELATIONSHIP_ANCHOR.md · safe default initialization",
        ],
      });
      setMode("review");
    }
  }

  function kindLabel(value: AdoptionKind): string {
    if (value === "new") return adoptionMessage(language, "kindNew");
    if (value === "adopt") return adoptionMessage(language, "kindAdopt");
    return adoptionMessage(language, "kindImport");
  }

  return (
    <div className="adoption-page">
      <section className="adoption-hero panel-grid-surface">
        <div>
          <p className="eyebrow">{adoptionMessage(language, "eyebrow")}</p>
          <h1>{adoptionMessage(language, "title")}</h1>
          <p>{adoptionMessage(language, "description")}</p>
        </div>
        <div className="adoption-no-character" role="status">
          <span className="adoption-empty-orbit" aria-hidden="true">
            ∅
          </span>
          <div>
            <strong>{adoptionMessage(language, "noCharacter")}</strong>
            <p>{adoptionMessage(language, "noCharacterDescription")}</p>
          </div>
        </div>
      </section>

      <section className="adoption-assistant surface-panel" aria-labelledby="assistant-name">
        <div className="adoption-assistant-avatar" aria-hidden="true">
          LA
        </div>
        <div>
          <p className="eyebrow">GUIDED ENTRY</p>
          <h2 id="assistant-name">{adoptionMessage(language, "assistantName")}</h2>
          <span>{adoptionMessage(language, "assistantRole")}</span>
          <p>{adoptionMessage(language, "assistantMessage")}</p>
        </div>
      </section>

      {mode === "choose" && (
        <section className="adoption-choice-section surface-panel" aria-labelledby="adoption-choice-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SAFE STARTING PATH</p>
              <h2 id="adoption-choice-title">{adoptionMessage(language, "chooseTitle")}</h2>
            </div>
          </div>
          <p className="panel-description">{adoptionMessage(language, "chooseDescription")}</p>
          <div className="adoption-choice-grid">
            <ChoiceCard
              marker="+"
              title={adoptionMessage(language, "newTitle")}
              body={adoptionMessage(language, "newBody")}
              onClick={() => openMode("new")}
            />
            <ChoiceCard
              marker="◇"
              title={adoptionMessage(language, "adoptTitle")}
              body={adoptionMessage(language, "adoptBody")}
              onClick={() => openMode("adopt")}
            />
            <ChoiceCard
              marker="⇩"
              title={adoptionMessage(language, "importTitle")}
              body={adoptionMessage(language, "importBody")}
              onClick={() => openMode("import")}
            />
            <ChoiceCard
              marker="?"
              title={adoptionMessage(language, "askTitle")}
              body={adoptionMessage(language, "askBody")}
              onClick={() => openMode("assistant")}
            />
          </div>
        </section>
      )}

      {mode === "assistant" && (
        <section className="adoption-form-panel surface-panel">
          <p className="eyebrow">{adoptionMessage(language, "assistantEyebrow")}</p>
          <h2>{adoptionMessage(language, "assistantHeading")}</h2>
          <div className="adoption-advice-list">
            <p>{adoptionMessage(language, "assistantNew")}</p>
            <p>{adoptionMessage(language, "assistantAdopt")}</p>
            <p>{adoptionMessage(language, "assistantImport")}</p>
          </div>
          <button className="button button-secondary" type="button" onClick={() => openMode("choose")}>
            {adoptionMessage(language, "back")}
          </button>
        </section>
      )}

      {mode === "new" && (
        <form className="adoption-form-panel surface-panel" onSubmit={validateAndReview}>
          <p className="eyebrow">{adoptionMessage(language, "newEyebrow")}</p>
          <h2>{adoptionMessage(language, "newHeading")}</h2>
          <div className="adoption-form-grid">
            <label>
              <span className="adoption-field-label">{adoptionMessage(language, "displayName")}</span>
              <input
                value={displayName}
                onChange={(event) => {
                  setDisplayName(event.target.value);
                  setError("");
                }}
                placeholder={adoptionMessage(language, "displayNamePlaceholder")}
                autoFocus
              />
            </label>
            <div className="adoption-id-preview">
              <span className="adoption-field-label">{adoptionMessage(language, "characterId")}</span>
              <code>{characterId}</code>
            </div>
            <label className="adoption-wide-field">
              <span className="adoption-field-label">{adoptionMessage(language, "relationshipNote")}</span>
              <textarea
                value={relationshipNote}
                onChange={(event) => setRelationshipNote(event.target.value)}
                placeholder={adoptionMessage(language, "relationshipPlaceholder")}
                rows={4}
              />
            </label>
          </div>
          <fieldset className="adoption-source-preview">
            <legend>{adoptionMessage(language, "safeDefaults")}</legend>
            <span>✓ {adoptionMessage(language, "soulDefault")}</span>
            <span>✓ {adoptionMessage(language, "outputDefault")}</span>
            <span>✓ {adoptionMessage(language, "relationshipDefault")}</span>
          </fieldset>
          {error && <p className="adoption-error">{error}</p>}
          <div className="adoption-form-actions">
            <button className="button button-secondary" type="button" onClick={() => openMode("choose")}>
              {adoptionMessage(language, "back")}
            </button>
            <button className="button button-primary" type="submit">
              {adoptionMessage(language, "continue")}
            </button>
          </div>
        </form>
      )}

      {mode === "adopt" && (
        <form className="adoption-form-panel surface-panel" onSubmit={validateAndReview}>
          <p className="eyebrow">{adoptionMessage(language, "adoptEyebrow")}</p>
          <h2>{adoptionMessage(language, "adoptHeading")}</h2>
          <div className="adoption-form-grid">
            <label>
              <span className="adoption-field-label">{adoptionMessage(language, "sourceLocation")}</span>
              <input
                value={sourceLocation}
                onChange={(event) => {
                  setSourceLocation(event.target.value);
                  setError("");
                }}
                placeholder={adoptionMessage(language, "sourceLocationPlaceholder")}
                autoFocus
              />
            </label>
            <label>
              <span className="adoption-field-label">{adoptionMessage(language, "displayName")}</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder={adoptionMessage(language, "displayNamePlaceholder")}
              />
            </label>
          </div>
          <fieldset className="adoption-checklist">
            <legend>{adoptionMessage(language, "sourceChecklist")}</legend>
            {([
              ["soul", "sourceSoul"],
              ["output", "sourceOutput"],
              ["relationship", "sourceRelationship"],
            ] as const).map(([key, label]) => (
              <label key={key}>
                <input
                  type="checkbox"
                  checked={sourceChecks[key]}
                  onChange={(event) => {
                    setSourceChecks((current) => ({ ...current, [key]: event.target.checked }));
                    setError("");
                  }}
                />
                <span>{adoptionMessage(language, label)}</span>
              </label>
            ))}
          </fieldset>
          <p className="boundary-note">{adoptionMessage(language, "sourceNote")}</p>
          {error && <p className="adoption-error">{error}</p>}
          <div className="adoption-form-actions">
            <button className="button button-secondary" type="button" onClick={() => openMode("choose")}>
              {adoptionMessage(language, "back")}
            </button>
            <button className="button button-primary" type="submit">
              {adoptionMessage(language, "continue")}
            </button>
          </div>
        </form>
      )}

      {mode === "import" && (
        <form className="adoption-form-panel surface-panel" onSubmit={validateAndReview}>
          <p className="eyebrow">{adoptionMessage(language, "importEyebrow")}</p>
          <h2>{adoptionMessage(language, "importHeading")}</h2>
          <label className="adoption-import-name">
            <span className="adoption-field-label">{adoptionMessage(language, "displayName")}</span>
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder={adoptionMessage(language, "displayNamePlaceholder")}
            />
          </label>
          <div className="adoption-file-grid">
            <FilePicker
              label={adoptionMessage(language, "soulFile")}
              filename={files.soul}
              language={language}
              onChange={(event) => setFile("soul", event)}
            />
            <FilePicker
              label={adoptionMessage(language, "outputFile")}
              filename={files.output}
              language={language}
              onChange={(event) => setFile("output", event)}
            />
            <FilePicker
              label={adoptionMessage(language, "relationshipFile")}
              filename={files.relationship}
              language={language}
              onChange={(event) => setFile("relationship", event)}
            />
          </div>
          <div className="adoption-default-options">
            <label>
              <input
                type="checkbox"
                checked={initializeOutput}
                disabled={Boolean(files.output)}
                onChange={(event) => {
                  setInitializeOutput(event.target.checked);
                  setError("");
                }}
              />
              <span>{adoptionMessage(language, "initializeOutput")}</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={initializeRelationship}
                disabled={Boolean(files.relationship)}
                onChange={(event) => {
                  setInitializeRelationship(event.target.checked);
                  setError("");
                }}
              />
              <span>{adoptionMessage(language, "initializeRelationship")}</span>
            </label>
          </div>
          <p className="boundary-note">{adoptionMessage(language, "importNote")}</p>
          {error && <p className="adoption-error">{error}</p>}
          <div className="adoption-form-actions">
            <button className="button button-secondary" type="button" onClick={() => openMode("choose")}>
              {adoptionMessage(language, "back")}
            </button>
            <button className="button button-primary" type="submit">
              {adoptionMessage(language, "continue")}
            </button>
          </div>
        </form>
      )}

      {mode === "review" && draft && (
        <section className="adoption-review surface-panel">
          <p className="eyebrow">{adoptionMessage(language, "reviewEyebrow")}</p>
          <h2>{adoptionMessage(language, "reviewHeading")}</h2>
          <dl className="adoption-review-grid">
            <div>
              <dt>{adoptionMessage(language, "reviewKind")}</dt>
              <dd>{kindLabel(kind)}</dd>
            </div>
            <div>
              <dt>{adoptionMessage(language, "reviewName")}</dt>
              <dd>{draft.displayName}</dd>
            </div>
            <div>
              <dt>{adoptionMessage(language, "reviewId")}</dt>
              <dd>
                <code>{draft.characterId}</code>
              </dd>
            </div>
            <div className="adoption-review-sources">
              <dt>{adoptionMessage(language, "reviewSources")}</dt>
              <dd>
                <ul>
                  {draft.sourceSummary.map((source) => (
                    <li key={source}>{source}</li>
                  ))}
                </ul>
              </dd>
            </div>
            <div className="adoption-review-boundary">
              <dt>{adoptionMessage(language, "reviewBoundary")}</dt>
              <dd>{adoptionMessage(language, "reviewBoundaryValue")}</dd>
            </div>
          </dl>
          <div className="adoption-form-actions">
            <button className="button button-secondary" type="button" onClick={() => setMode(returnMode)}>
              {adoptionMessage(language, "back")}
            </button>
            <button className="button button-primary" type="button" onClick={() => setMode("complete")}>
              {adoptionMessage(language, "finish")}
            </button>
          </div>
        </section>
      )}

      {mode === "complete" && draft && (
        <section className="adoption-complete panel-grid-surface">
          <span className="mock-pill">{adoptionMessage(language, "completeBadge")}</span>
          <p className="eyebrow">{adoptionMessage(language, "completeEyebrow")}</p>
          <h2>{adoptionMessage(language, "completeHeading")}</h2>
          <div className="adoption-complete-avatar" aria-hidden="true">
            {draft.displayName.slice(0, 2).toUpperCase()}
          </div>
          <strong>{draft.displayName}</strong>
          <code>{draft.characterId}</code>
          <p>{adoptionMessage(language, "completeBody")}</p>
          <div className="adoption-form-actions">
            <button className="button button-secondary" type="button" onClick={reset}>
              {adoptionMessage(language, "reset")}
            </button>
            <button className="button button-primary" type="button" onClick={onBackHome}>
              Home
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
