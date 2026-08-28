# First-party Starter Cognitive Packages

Status: Core 1.0 onboarding product surface. Owning Issue: #1891.

RelayLM ships a deliberately small set of first-party Starter resources so an installed user can inspect, copy, and run concrete cognitive roles before authoring a package from scratch. The canonical assets live inside the installed `relaylm` Python package under `relaylm.starters`; repository examples and test fixtures are not Starter authority.

## Starter catalog

The Core 1.0 catalog contains exactly four roles:

```text
characters/
  blank/             minimal neutral starting point
  relm/              complete Character example

machines/
  fact-summarizer/   non-personal general summarization role
  medical-soap/      domain-specific SOAP documentation structurer
```

The `characters/` and `machines/` names organize the first-party catalog for humans. They are not a closed runtime type taxonomy.

All four roots validate through the production `CognitivePackageDirectory` boundary introduced by #1890. `blank` and `relm` also preserve the existing Character Package specialization. The two machine roots use `package.id` and do not fabricate `character.name`, relationship, emotion, or backstory fields merely to satisfy the runtime.

## Installed-artifact materialization

`relaylm.starters.materialize_starter_package(name, destination)` copies a bundled Starter into a newly created ordinary filesystem directory. It resolves its source through Python package resources rather than repository-relative paths, so the same operation works from a wheel, an sdist installation, and a source checkout.

Materialization fails rather than overwriting an existing destination. An unknown Starter name also fails closed. The resulting root is inspectable, editable, and portable user data; users never need to edit files inside the installed Python environment.

For example, after installing RelayLM:

```bash
python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("relm", "./relm")'
python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("fact-summarizer", "./fact-summarizer")'
```

The public catalog can be inspected programmatically with `relaylm.starters.list_starter_packages()`.

## Production loader, doctor, and startup path

Starter roots use the same production package loader and operator preflight as user-created Cognitive Packages. The current runtime configuration surface still names the selected root `character.directory`; #1889 owns the later Cognitive Profile routing schema and public OpenAI `model` meaning. Until #1889 merges, this document does not claim that `profiles[]` is executable current runtime configuration.

A materialized Starter can be checked with the current operator path without provider generation:

```bash
relaylm doctor \
  --character ./relm \
  --provider-base-url http://127.0.0.1:1234/v1 \
  --provider-model '<provider-model-id>'
```

The same root can then be supplied to `relaylm serve`. First-party acceptance covers all four roots through `doctor`, and covers both a Character-like root and a machine-like root through startup assembly.

## Portable authority boundary

Starter roots contain only portable semantic content. They do not contain:

- provider URLs or adapters;
- physical model IDs;
- API keys or secrets;
- server bind policy;
- host-specific filesystem paths;
- tokenizer, calibration, or other machine/runtime settings.

Those settings remain runtime configuration. Starter content demonstrates what the model is being used as, not which physical model or host executes it.

## Character and machine contrast

A Character is one specialization of Cognitive Package, not the runtime's only intended role. `relm` demonstrates a persistent character with explicit self, values, and interaction material. `fact-summarizer` demonstrates that a useful package can instead be deliberately non-personal and task-oriented without inventing relationships, emotion, or a backstory.

`blank` is intentionally sparse so a new user can fork it into their own Character. It should remain easy to read and edit rather than accumulating demonstration-only complexity.

## Medical SOAP boundary

`medical-soap` is a documentation-structuring example only. It organizes source-supported material into SOAP sections. It must not invent symptoms, findings, diagnoses, medications, measurements, tests, or plans, and it is not clinical decision authority or a substitute for diagnosis or treatment by a qualified clinician.

## Cognitive Profile binding dependency

Core 1.0's intended Profile shape remains owned by #1889:

```yaml
profiles:
  - name: relm
    root: ./characters/relm

  - name: fact-summarizer
    root: ./machines/fact-summarizer
```

This example documents how Starter roots are intended to bind once #1889 is current production authority. Starter distribution, package validation, doctor/startup acceptance, and installed-artifact usability do not depend on that unfinished routing work, and Starter names are not claimed to appear in `/v1/models` before #1889 ships.
