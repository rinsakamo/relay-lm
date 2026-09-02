# Repository Practices

This document defines lightweight repository-use practices for the active RelayLM `v1` product line. Product semantics remain owned by architecture/contracts/reference docs and executable tests.

## Branch roles

- `v1` is the active product line and the only branch used for current RelayLM development.
- `main` is frozen RelayLM 0.x history/reference and is not modified by v1 transactions.
- Feature/work branches are short-lived transaction branches created from fresh current `v1` authority.

## Pull requests

One PR owns one bounded responsibility.

The repository PR template asks for:

- bounded responsibility;
- owning Issue;
- change classification;
- semantic meaning/examples when applicable;
- test/verification evidence;
- code/test/docs authority impact;
- non-goals/deferred work;
- canonical-convergence confirmation;
- fresh-head / exact-head completion checks.

The intended merge method for v1 is squash so one merged PR corresponds to one bounded transaction. Head branches should be deleted after merge.

Repository-host enforcement of squash-only merge and automatic head-branch deletion is a GitHub setting, not a source-controlled semantic contract. Current v1 operation expects those settings to remain active; if live GitHub no longer matches them, treat that as repository-administration drift rather than silently weakening the workflow.

## Issues

Use the smallest fitting Issue Form:

- Feature / semantic change — bounded behavior/contract work with Given / When / Then examples;
- Bug / regression — current-contract or previous-behavior failure;
- Design proposal — exploratory architecture that is explicitly not current authority until promoted.

Issue roles remain:

```text
Issue   intention + examples + remaining-work ledger
PR      bounded change transaction
Tests   executable contract / regression evidence
Code    implementation
Docs    current human-readable authority
History completed/superseded past work
```

An owning Issue discussion may carry the concise execution handoff required by `docs/reference/development-workflow.md` when a transaction performs material physical/external execution. The handoff comment is historical working evidence, not current authority, not a raw-log archive requirement, and not repository-mutation authorization. Keep the Issue body focused on intention and remaining work; stable reusable lessons are either converged by a transaction that already owns the relevant mutation or routed to the responsible owner/successor, while producer-owned immutable results remain evidence and volatile trial detail remains historical. When no owning Issue exists and a PR is the durable transaction surface, the same bounded handoff may live in the PR discussion.

Open Issues should represent real unresolved work. Successful transactions reconcile their owning Issues after merge.

## Architecture Decision Records

`docs/decisions/` is intentionally sparse. ADRs are for durable decisions that are costly to rediscover or reverse, not for ordinary implementation choices.

An ADR records why a durable constraint exists; canonical current behavior must still be described in normal architecture/contracts/reference docs.

## Repository authority declarations

`.ai/` is the repository-local authority root. Each semantic owner writes exactly one declaration at `.ai/authority/<id>.yaml` naming its canonical surfaces, supporting implementation/test surfaces, dependencies, produced/referenced evidence, and non-normative annotations.

There is no central registry to edit. A lane registers itself by writing its own declaration, so disjoint lanes do not contend on a shared navigation aggregate.

`tools/repository_authority.py` is the executable schema and is enforced by `tests/unit/test_repository_authority.py` under the required `v1 CI / pytest` check. It rejects duplicate canonical ownership, missing surfaces, unresolved dependencies or evidence references, dependency cycles, documents without an owner, and reintroduction of a hand-maintained authority aggregate.

```bash
python tools/repository_authority.py validate
```

Global authority, dependency, and navigation views are derived from these declarations rather than hand-maintained. Reverse dependencies are computed from consumers' `depends_on` and are never declared a second time.

## Evidence ownership

Evidence follows producer ownership.

```text
producer   declares the evidence record and owns its surfaces
consumer   declares evidence_refs and cites the id
```

Actual-model Evaluation owns the frozen scenario sets, target identities, and Character fixtures under `evaluation/actual_model/`. Calibration cites those evidence ids; it does not copy result tables, scenario counts, or target identity into its own authority. Validation rejects an evidence surface declared by any other owner, and rejects a producer restating its own evidence surface as implementation.

## Ephemeral projections

Global developer views — semantic-owner map, dependency graph, derived consumers, architecture overview, evidence map, repository status — are not committed. `.ai/projections/<id>.yaml` stores the recipe; the view is reconstructed when someone needs it.

```bash
python -m tools.repository_projection list
python -m tools.repository_projection render semantic-owner-map
```

A recipe declares its inputs, the freshness requirements of the facts it relies on, selection rules, prohibited inferences, and a preferred output shape. Rendering is deterministic and derives every fact from `.ai/authority/`; facts the recipe cannot derive from committed authority are printed as live inputs the agent must fetch. A rendered view is therefore never a second authority, and a stale rendered view cannot be mistaken for current state.

## Persistent human documentation

Root human-facing documentation is classified rather than assumed:

```text
README.md         canonical prose. Product description and operator entry point.
SECURITY.md       canonical prose.
ARCHITECTURE.md   generated projection. Never hand-edited.
```

`ARCHITECTURE.md` is materialized from owner-local authority and the release-owned package version at a version/release boundary. It carries machine-readable provenance in HTML comments naming the generator, projection schema version, frozen input commit, and package version, so a reader can tell which repository state it describes without that provenance appearing in the rendered page.

```bash
python -m tools.repository_docs --commit <frozen-input> write
python -m tools.repository_docs --commit <frozen-input> check
```

A normal semantic transaction does not regenerate it. Drift between release boundaries is expected and is made visible by the recorded input commit. The `v1 release candidate gate` workflow validates authority, validates projection recipes, and requires the committed projection to match generation from the exact frozen candidate commit, so the generated documentation is part of the release transaction rather than a commit added after the release.

```text
version/release transaction
  freeze input commit
  validate authority and recipes
  regenerate persistent projections
  verify deterministic output against the frozen input
  merge with the generated documentation included
  tag
```

## Bootstrap and freshness

`.ai/agent-contract.yaml` declares the ordered read path into repository authority and the freshness class of every fact a transaction relies on.

```text
live         repository HEAD, open PRs, CI/check state, Issue state and comments,
             branch protection, release tags
repository   semantic ownership, canonical surfaces, dependency graph,
             executable contracts, package version
evidence     merged evidence artifacts, referenced by evidence id
historical   handoff prompt state, projection output, merged PR bodies
```

A `live` fact is re-fetched at the start of a transaction and again immediately before merge. It is never stored as persistent authority: a 40-character commit id appearing anywhere in an owner declaration fails validation. A `historical` fact is never current authority, so the SHA, PR list, or status quoted in a handoff prompt is classified rather than argued about.

## Dependency maintenance

`.github/dependabot.yml` defines weekly version-update checks for GitHub Actions targeting `v1`.

Python requirements in `pyproject.toml` are lower-bound support declarations rather than lockfile pins. A routine Dependabot change such as `package>=old` to `package>=new` changes RelayLM's supported compatibility floor without selecting the installed version. Python dependency floors are therefore raised only by an explicit reviewed RelayLM transaction with a compatibility or security reason and relevant evidence; routine Dependabot `pip` version-update PRs are disabled.

`constraints/minimum.txt` is an executable CI projection of the direct lower bounds declared by `pyproject.toml`, not a lockfile and not a second dependency authority. The `v1 CI / minimum-supported` job installs those direct floor versions on Python 3.12, runs `pip check`, and runs the full v1 test suite. Any intentional lower-bound change must update the projection in the same transaction and remain green at the new floor.

Dependabot alerts and Dependabot security updates remain repository-host security controls. They are independent of routine version-update scheduling and may still produce a security update against the default branch, which is `v1`. A security advisory can justify a bounded dependency-floor change when the vulnerable range requires it.

GitHub Actions are executable CI supply-chain dependencies rather than Python support floors. Keep maintained Actions pinned to full commit SHAs, and use reviewed Dependabot GitHub Actions PRs to advance those pins after exact-head CI succeeds.

## Package integrity

Editable installs are development convenience, not proof that a distributable package works. The `v1 CI / package-smoke` job builds the RelayLM wheel from the exact transaction head, installs that wheel into a clean Python 3.12 virtual environment, runs `pip check`, imports the installed package, verifies the package version, and verifies the declared `relaylm` and `relaylm-eval` console entry points. Packaging metadata or build-system changes must keep this smoke green.

## Linting

Ruff is used as a lint-only mechanical error gate, not as an automatic formatter or broad style authority. `pyproject.toml` explicitly selects only `E4`, `E7`, `E9`, and `F` rules and targets Python 3.12 so Ruff release-default expansion cannot silently broaden RelayLM policy. The `v1 CI / lint` job uses an exact Ruff version and runs `ruff check .`. Expanding the rule set, enabling formatting, or advancing the pinned Ruff version is an explicit reviewed tooling transaction rather than an incidental source rewrite.

## Repository-host protections

The live GitHub-host configuration is intentionally small and should remain aligned with this contract.

### `v1`

- require pull request before branch updates/merge;
- require `v1 CI / pytest`;
- require `v1 CI / minimum-supported`;
- require `v1 CI / package-smoke`;
- require `v1 CI / lint`;
- do not require branches to be automatically updated/rebased onto the latest `v1` before merge;
- block force pushes;
- block branch deletion;
- require linear history where compatible with squash-only merge;
- allow no routine bypass that would make the checks advisory.

RelayLM reconstructs authority when `v1` moves and does not silently rebase a transaction.

### frozen `main`

- block routine updates;
- block force pushes;
- block deletion;
- retain only as 0.x historical/reference authority.

### repository merge/security settings

- allow squash merge only for active v1 work;
- automatically delete merged head branches;
- enable Dependabot alerts and Dependabot security updates;
- run routine Dependabot version updates for GitHub Actions only;
- enable secret scanning and repository push protection;
- require GitHub Actions workflow references to use full-length commit SHA pins;
- keep GitHub Actions on maintained versions and advance pinned SHAs through reviewed dependency transactions.

Ruleset details that are available through the GitHub API should be verified from live repository authority rather than inferred from this document. Repository settings that the linked automation cannot read must be explicitly confirmed in GitHub UI during an audit; documentation alone is not proof that a host-side setting is active.
