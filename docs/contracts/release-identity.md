# Release Identity Contract

Status: REL2 exact release-identity contract for RelayLM v1. Owning Issue: #1447.

This contract freezes package version, git tag, source commit, artifact checksum, and reissue identity without choosing a publication registry/channel or declaring RelayLM 1.0 globally release-ready.

## Package version authority

`src/relaylm/_version.py` is the sole mutable source for the RelayLM Python package version. It contains one canonical version string in `__version__`.

`pyproject.toml` declares `version` as dynamic and instructs Hatchling to read that exact source. Runtime/version surfaces consume the same source:

- `relaylm.__version__` re-exports it;
- `relaylm --version` uses it;
- FastAPI application metadata uses it;
- wheel/sdist metadata is generated from it by Hatchling;
- REL1 package-smoke resolves it before build and requires built and installed metadata to match it.

The release workflow must not derive the package version from branch names, timestamps, dirty-tree state, registry responses, or ambient Git metadata. Source-distribution rebuilds therefore remain independent of a repository checkout.

## Canonical version forms

RelayLM 1.x release engineering accepts exactly these forms:

```text
X.Y.Z.devN   development source version; N >= 0
X.Y.ZrcN     release candidate; N >= 1
X.Y.Z        final release
```

Other PEP 440 forms are not RelayLM release identities for this product line. In particular, alpha/beta, post, local, epoch, hyphenated `-rc`, and non-canonical leading-zero spellings are rejected by the release-identity gate.

Development versions are not public release identities and receive no release tag. A candidate starts at `rc1` and advances monotonically by choosing a new source version (`rc2`, `rc3`, ...); an existing candidate identity is never rewritten.

Transitioning from the final accepted RC to `X.Y.Z` is a new source commit because the package metadata changes. The final artifact must therefore be rebuilt and pass its own exact-candidate gate rather than being a renamed RC artifact.

## Git tag mapping

Every releasable package version maps one-to-one to exactly one git tag:

```text
package 1.0.0rc1 -> tag v1.0.0rc1
package 1.0.0    -> tag v1.0.0
```

The tag spelling is exactly `v` plus the canonical package version. A development version must not be tagged as a release.

Release tags are immutable identity. Release tooling must:

1. refuse to create a tag when that exact tag already exists;
2. never force-update an existing release tag;
3. require the tag to resolve to the exact source commit recorded by the candidate evidence;
4. fail closed if a pre-existing RelayLM 1.x tag conflicts with the proposed package version or commit.

Historical tags outside the RelayLM 1.x release namespace are not rewritten by this policy. Their existence does not authorize alternate naming for new 1.x releases.

The repository workflow `.github/workflows/v1-release-identity.yml` validates version syntax on v1 transactions and validates tag spelling/new-tag/non-force semantics when a `v1.*` tag push is observed. This is an acceptance signal, not permission to mutate or recreate a tag.

## Exact commit and artifact provenance

An RC/final identity is not just a version string. Before acceptance, REL3 must bind at least:

```text
package name
package version
release kind: rc | final
expected git tag
exact 40-hex v1 commit
wheel filename + SHA-256
sdist filename + SHA-256
```

`tools/release_identity.py manifest` emits this bounded identity record for an exact wheel/sdist pair. The artifact checksums are part of the candidate identity: a rebuild that produces different bytes is a different candidate and cannot silently replace an already accepted manifest under the same version/tag.

The manifest itself does not make an artifact release-ready. REL3 owns the exact candidate-artifact mechanical gate and #1449 owns the final cross-work-package release decision.

## Same-version overwrite and reissue prohibition

One canonical package version identifies one immutable accepted release identity. Once a version/tag has been accepted or published:

- different artifact bytes must not be uploaded under the same version;
- a tag must not be moved to another commit;
- an artifact must not be renamed to impersonate another build;
- rebuilding alone does not authorize replacing accepted artifacts;
- a broken release is corrected by creating a new version, not by silent overwrite.

Before candidate tag creation, release tooling must fetch current tag refs and run the equivalent of:

```text
tools/release_identity.py assert-tag-absent <version>
```

That command is intentionally fail-closed for an already-present tag. REL3/REL4 must perform the remote/fetched-tag refresh immediately before relying on it; a stale local tag list is not release authority.

## Packaging-only emergency fixes

A packaging-only fix after a final release uses a new patch release line. For example, after `1.0.0`, a corrected distribution may use candidate `1.0.1rc1` and final `1.0.1`; it must never replace `1.0.0` artifacts or move `v1.0.0`.

The packaging-only nature of a fix does not waive REL3 artifact validation or #1449 readiness requirements that apply to the new release.

## Schema-version independence

Character Package `format_version`, runtime-config `format_version`, evaluation artifact schemas, and other domain/schema versions remain independent authorities. Advancing the RelayLM package version never mechanically advances them, and schema changes do not mechanically dictate a package version without their owning policy.

## Publication and signing boundary

REL2 chooses no publication registry/channel and no external signing/trust policy. REL4 remains blocked until the publication target and credentials/permissions boundary are explicitly selected.

Checksums, tag/commit provenance, and overwrite prohibition are required regardless of the later publication channel.

## REL2 completion boundary

REL2 is mechanically complete when the single version source, canonical dev/RC/final grammar, tag mapping, immutable tag/version rule, commit/checksum manifest shape, and packaging-only patch-fix rule are green on fresh v1 authority.

Creating an RC tag is not part of REL2 implementation. Tag creation occurs only after REL3 has validated the exact candidate artifact and the applicable upstream release gates permit an RC transaction.
