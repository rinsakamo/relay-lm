# CI Verification Contract

This document defines what RelayLM `v1` continuous-integration results mean.

It owns CI **guarantee semantics**. It does not own transaction sequencing, GitHub-host enforcement, product semantics, or empirical model-quality evaluation.

The core rule is:

> **CI verifies declared contracts. CI does not invent semantics.**

A workflow or job may implement a guarantee defined here. The existence of executable YAML does not by itself redefine what RelayLM promises.

## Relationship to existing workflow references

This document is the single semantic writer for what a green CI result proves and does not prove.

Other `development_workflow` surfaces may name CI jobs, commands, dependency floors, packaging steps, or required-check settings while describing transaction sequencing, repository mechanics, tooling policy, or host enforcement. Those descriptions are operational references to the executable workflow, not independent CI guarantee definitions.

In particular:

- `docs/reference/development-workflow.md` owns when exact-head CI is required and how merge sequencing consumes those results;
- `docs/reference/repository-practices.md` owns dependency, tooling, packaging, repository-use, and live host-enforcement practices;
- `.github/workflows/*.yml` execute the checks.

If an operational reference and this contract disagree about CI guarantee semantics, this contract is authoritative and the reference must be reconciled in the owning development-workflow transaction.

## Verification subject

Every CI result is scoped to the exact subject it tested.

For source verification, the subject is the exact checked-out commit SHA. For artifact verification, the subject is the exact built or supplied artifact identified by the workflow.

A result from another source head, another artifact, or another resolved environment is evidence about that other subject only.

> **Green is not transferable.**

The development workflow owns when an exact-head result is required before merge. This document owns what that green result proves.

## Current required merge guarantees

The source-controlled `v1` merge baseline consists of four jobs in `.github/workflows/v1-ci.yml`.

### `v1 CI / pytest`

Guarantee:

> The full RelayLM test suite passes on Python 3.12 in the job's current resolver-selected compatible dependency environment.

This includes repository structural and authority tests that are part of the normal pytest suite.

It does **not** prove:

- compatibility with every Python version allowed by package metadata;
- compatibility with every possible dependency resolution;
- minimum-version compatibility;
- package-installability from a built distribution artifact;
- model-quality behavior.

### `v1 CI / minimum-supported`

Guarantee:

> The full RelayLM test suite and dependency-consistency check pass on Python 3.12 when declared direct dependency floors are constrained by `constraints/minimum.txt` and compatible transitive dependencies are resolved for that run.

`constraints/minimum.txt` is the executable projection of direct lower bounds defined by package metadata. It is not a complete environment lockfile.

This job therefore proves the declared direct floors are viable under the resolver outcome tested. It does not prove that every historical or future transitive resolution will behave identically.

### `v1 CI / package-smoke`

Guarantee:

> The exact source head can produce the expected wheel and sdist, repeated builds are byte-identical within the workflow's resolved build environment, package contents and metadata satisfy the checked contract, and the produced distributions can be installed and exercised outside the source checkout on Python 3.12 as specified by the smoke fixture.

The repeated-build check is deliberately scoped to the environment resolved for that workflow run.

It does **not** claim cross-time or cross-platform reproducible builds unless a separately owned frozen build-environment contract is introduced and verified.

### `v1 CI / lint`

Guarantee:

> The repository passes the explicitly configured conservative Ruff rule set using the exact Ruff version installed by the workflow.

This is a mechanical error gate. It is not a general style, formatting, type-safety, complexity, or security-analysis guarantee.

## Additional exact-head workflows

A workflow may run on every pull request without being part of the four-job source-controlled merge baseline.

`v1 release identity` verifies the package version/tag identity policy implemented by `tools/release_identity.py` against the exact event head. It is a distinct guarantee from the general `v1 CI` baseline.

Whether GitHub currently requires any workflow or job as a host-side merge condition is a **live repository-host fact**. Source documentation does not prove that enforcement is active.

## Three distinct CI facts

Never collapse these into one statement:

```text
CI definition    the workflow/job exists and defines executable verification
CI result        a particular run completed with a particular result for a subject
CI enforcement   the live repository host currently requires that result before merge
```

A workflow can exist without running. A run can be green without being required. A required check can be misconfigured or detached from the intended exact head.

Repository-host enforcement is owned by repository practices and must be verified live when it matters.

## Environment classes

RelayLM does not treat every CI environment as equivalent.

Current merge CI uses these practical classes:

```text
current-resolved
  compatible versions are resolved at run time within declared package constraints
  example: v1 CI / pytest

floor-resolved
  declared direct floors are constrained while compatible transitives are resolved
  example: v1 CI / minimum-supported

artifact-smoke
  distributions are built and then installed/executed outside the checkout
  example: v1 CI / package-smoke

pinned-tool
  the verification tool itself is explicitly version-pinned
  example: Ruff in v1 CI / lint
```

A future frozen release environment may add a stronger reproducibility class. Until such a contract exists, CI documentation must not imply one.

## Deterministic CI and empirical evaluation

Required merge CI should verify properties that are deterministic enough to function as repository gates.

Actual-model quality, probabilistic behavior, calibration evidence, latency distributions, and other environment-sensitive model observations belong to their evidence owners rather than being silently promoted into ordinary deterministic merge CI.

> **CI proves deterministic repository contracts. Evaluation measures empirical model behavior.**

A model-backed check may become a merge gate only through an explicit authority transaction that defines its repeatability, failure semantics, environment ownership, and operational cost.

## Workflow implementation rules

A CI workflow implementing a guarantee should:

- bind verification to the intended exact source or artifact;
- fail closed when the verification subject cannot be established;
- use least-privilege repository permissions;
- pin executable third-party Actions to reviewed full commit SHAs;
- keep job responsibility narrow enough that a failure has an interpretable meaning;
- avoid hidden network or environment assumptions when a deterministic local check can provide the same guarantee;
- make timeouts and cancellation behavior explicit enough to avoid indefinite merge ambiguity.

The current workflows visibly implement exact-head binding, least-privilege `contents: read`, full-SHA Action pins, job timeouts, and cancellation behavior. Mechanical self-validation of workflow policy is a separate future enforcement transaction; this document does not claim such a validator already exists.

## One named gate, one named guarantee

A required job should have a stable, explainable responsibility.

Do not add a gate merely because another project uses it. A new required CI gate must answer:

1. What concrete failure class does it prevent?
2. What exact subject does its green result describe?
3. What environment class does it execute in?
4. Why is the property suitable for deterministic merge enforcement?
5. Which existing guarantee does it complement rather than duplicate?
6. What operational cost and false-positive surface does it add?
7. Which canonical owner maintains the rule it verifies?

If two jobs claim the same guarantee, consolidate or distinguish them rather than maintaining parallel semantic descriptions.

## CI is not a catch-all quality claim

A green merge baseline does not imply that RelayLM has been proven against properties no gate currently owns.

Unless separately introduced and verified, current merge CI does not claim exhaustive:

- static type correctness;
- complexity limits;
- source-code ownership coverage;
- semantic/import dependency alignment;
- vulnerability scanning;
- secret scanning;
- multi-version Python compatibility;
- multi-platform compatibility;
- cross-time reproducible builds;
- actual-model conversational quality.

Some of these may be enforced by GitHub-host services, evidence lanes, release workflows, or future repository checks. Their absence from this merge contract must not be hidden behind a generic statement that "CI is green."

## Change rule

Changing what a CI job proves is a contract change even when the workflow job name stays the same.

A transaction that materially changes a gate must converge:

```text
intended guarantee
  -> executable workflow/check
  -> relevant contract or regression tests where practical
  -> this CI verification contract
  -> repository-host requirement if the required-check set changes
```

Changing only a workflow command without reconciling the guarantee description is incomplete. Changing only this document without implementing the claimed check is also incomplete.

## Review rule

A CI change is converged only when a reviewer can answer all of these from current authority and the exact workflow:

1. What does green prove?
2. What does it explicitly not prove?
3. What exact source or artifact was tested?
4. What environment class produced the result?
5. Is the check source-defined, actually green for the relevant subject, and live-required when required?
6. Does the check duplicate another guarantee or introduce an unrelated quality policy?
7. Are empirical model observations kept in evidence rather than disguised as deterministic CI?

The objective is not more gates. The objective is a small set of exact, trustworthy guarantees whose meaning remains stable as RelayLM evolves.
