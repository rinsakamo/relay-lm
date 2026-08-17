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

Repository-host enforcement of squash-only merge and automatic head-branch deletion is a GitHub setting, not a source-controlled semantic contract. Until those settings are mechanically enabled, the development workflow still requires expected-head protected squash merges.

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

Open Issues should represent real unresolved work. Successful transactions reconcile their owning Issues after merge.

## Architecture Decision Records

`docs/decisions/` is intentionally sparse. ADRs are for durable decisions that are costly to rediscover or reverse, not for ordinary implementation choices.

An ADR records why a durable constraint exists; canonical current behavior must still be described in normal architecture/contracts/reference docs.

## Authority map

`docs/authority-map.yaml` is a lightweight navigation index connecting major runtime owners to representative tests and current-authority docs.

It is deliberately non-enforcing at first. Update it when a major ownership boundary or its representative contract/docs move. If repository scale later makes drift common, a mechanical existence/coverage check may be added without turning the map into a second semantic authority.

## Dependency maintenance

`.github/dependabot.yml` defines weekly version-update checks for Python dependencies and GitHub Actions, targeting `v1`.

GitHub reads Dependabot and community templates from the repository default branch. While frozen 0.x `main` remains the default branch, the v1 copies are staged repository configuration rather than active GitHub UI/Dependabot configuration. Activation therefore depends on a repository-host decision such as making `v1` the default branch at the appropriate product-line transition; `main` must not be modified merely to activate v1 tooling.

## Repository-host protections

The desired GitHub-host configuration is intentionally small:

### `v1`

- require pull request before branch updates/merge;
- require the current `v1 CI / pytest` status check;
- block force pushes;
- block branch deletion;
- require linear history where compatible with squash-only merge;
- allow no routine bypass that would make the checks advisory.

Do not require branches to be automatically updated/rebased onto the latest `v1`; RelayLM instead reconstructs authority when `v1` moves and does not silently rebase a transaction.

### frozen `main`

- block routine updates;
- block force pushes;
- block deletion;
- retain only as 0.x historical/reference authority.

### repository merge/security settings

- allow squash merge only for active v1 work;
- automatically delete merged head branches;
- enable Dependabot alerts/version updates when v1 configuration is active;
- enable secret scanning and repository push protection;
- keep GitHub Actions on maintained major versions.

These repository-host settings are not considered implemented merely because they are documented here. Any setting not observable as active in GitHub remains explicit administrative work.
