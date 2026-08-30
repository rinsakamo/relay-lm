# First-party Starter Cognitive Packages

Status: Core 1.0 onboarding product surface. Foundation: #1891. Current catalog/content convergence owner: #1996.

RelayLM ships a deliberately small set of first-party Starter resources so an installed user can inspect, copy, and run concrete cognitive roles before authoring a package from scratch. The canonical assets live inside the installed `relaylm` Python package under `relaylm.starters`; repository examples and test fixtures are not Starter authority.

## Current bundled catalog

The current bundled Core 1.0 catalog contains four roots:

```text
characters/
  blank/             neutral authoring vessel
  relm/              complete Character example

machines/
  fact-summarizer/   minimal non-personal summarization role
  relaylm-faq/       source-bounded RelayLM onboarding/reference role
```

The `characters/` and `machines/` names organize the first-party catalog for humans. They are not a closed runtime type taxonomy. Character is one specialization of Cognitive Package; a package may instead be deliberately machine-like.

`medical-soap` is not part of the bundled/public Core 1.0 Starter catalog. Core 1.0 does not require a regulated-domain example merely to prove machine-like cognition.

#1996 also owns the final public Character spectrum. ReLM/Rin authoring is frozen only when its explicit authoring/evidence boundary says so; this catalog document does not silently promote authoring drafts into shipped Character authority.

## Installed-artifact materialization

`relaylm.starters.materialize_starter_package(name, destination)` copies a bundled Starter into a newly created ordinary filesystem directory. It resolves its source through Python package resources rather than repository-relative paths, so the same operation works from a wheel, an sdist installation, and a source checkout.

Materialization fails rather than overwriting an existing destination. An unknown Starter name also fails closed. The resulting root is inspectable, editable, and portable user data; users never need to edit files inside the installed Python environment.

For example:

```bash
python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("relm", "./relm")'
python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("relaylm-faq", "./relaylm-faq")'
```

The catalog can be inspected programmatically with `relaylm.starters.list_starter_packages()`.

## Production loader, Profile binding, doctor, and startup path

Starter roots use the same production `CognitivePackageDirectory` loader and runtime operator path as user-created Cognitive Packages. Runtime configuration binds roots through Cognitive Profiles:

```yaml
format_version: 1
profiles:
  - name: relm
    root: ./relm

  - name: relaylm-faq
    root: ./relaylm-faq
provider:
  adapter: openai_compatible
  base_url: <operator-supplied endpoint>
  model: <physical provider model id>
server:
  host: 127.0.0.1
  port: 8090
```

The public OpenAI-compatible `model` field selects a configured Cognitive Profile; it does not directly override the physical inference model. Starter package data therefore remains separate from provider/model/host configuration.

A materialized Starter can be checked through the current operator configuration path with `relaylm doctor --config <runtime-config>`, and the same configured Profile can be supplied to `relaylm serve`. First-party acceptance covers every bundled Starter through production package validation and doctor, plus at least one Character-like and one machine-like Starter through startup assembly.

## Portable authority boundary

Starter roots contain only portable semantic content. They do not contain:

- provider URLs or adapters;
- physical model IDs;
- API keys or secrets;
- server bind policy;
- host-specific filesystem paths;
- tokenizer, calibration, or other machine/runtime settings.

Those settings remain runtime configuration. Starter content demonstrates what the model is being used as, not which physical model or host executes it.

## Blank, ReLM, and machine contrast

`blank` is intentionally a neutral authoring vessel rather than a person name. It should remain sparse, easy to inspect, and free of invented personality or relationship history.

`relm` demonstrates the Character specialization using the same package/runtime machinery. Its final authored Character content remains subject to #1996/#1823's explicit freeze boundary rather than being inferred by runtime code.

`fact-summarizer` demonstrates a minimal generic machine role without relationships, emotion, or backstory.

## RelayLM-FAQ

`relaylm-faq` is a non-personal onboarding/reference machine. Its `SOUL.md` constrains it to supplied RelayLM KNOWLEDGE and governed current context. Its bundled `knowledge/` assets are a deliberately bounded projection of shipped documentation, not a copy of the repository and not a second documentation authority.

The FAQ package follows the Core KNOWLEDGE boundary:

- KNOWLEDGE is package-authored read-only reference material;
- it is not lived `MEMORY`, Event evidence, Canonical State, or personal experience;
- document locations are not Event IDs or candidate provenance;
- ordinary turns and Crystallization do not rewrite it;
- unsupported RelayLM questions should be declined as unsupported by supplied package authority rather than answered from unrestricted model prior.

The installed wheel/sdist smoke verifies that the FAQ's knowledge assets are actually carried by distribution and load through the production Cognitive Package path. There is no FAQ-specific runtime injection path.

## Public teaching spectrum

The current machine/Character contrast can be introduced as:

```text
RelayLM-FAQ -> Blank -> ReLM
machine-like              character-like
```

`fact-summarizer` remains a secondary minimal machine example. #1996 may extend the Character end with a separately frozen Rin Starter once its authoring authority is ready; that future content does not change the rule that all Starters use the same Cognitive Package/runtime machinery.
