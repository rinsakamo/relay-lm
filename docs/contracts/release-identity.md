# Release Identity Contract

Status: REL2 package-version authority slice for RelayLM v1. Owning Issue: #1447.

This slice freezes one source of package-version truth without yet choosing the public tag/pre-release/reissue policy that completes REL2.

## Package version authority

`src/relaylm/_version.py` is the sole mutable source for the RelayLM Python package version. It contains one PEP 440 version string in `__version__`.

`pyproject.toml` declares `version` as dynamic and instructs Hatchling to read that exact source. Therefore a source commit cannot intentionally assign one version to runtime code and a different version to wheel/sdist metadata without failing the release tests/gates.

Runtime/version surfaces consume the same source:

- `relaylm.__version__` re-exports it;
- `relaylm --version` uses it;
- FastAPI application metadata uses it;
- wheel/sdist metadata is generated from it by Hatchling;
- REL1 package-smoke resolves it before build and requires built and installed metadata to match it.

The release workflow must not derive the package version implicitly from branch names, timestamps, dirty-tree state, a registry response, or ambient Git metadata. This keeps source-distribution rebuilds independent of a repository checkout.

## Artifact filename identity

Wheel and sdist filenames are build-backend projections of package name `relaylm` plus the authoritative normalized package version and artifact compatibility/format suffixes. A filename is not independent version authority; it must agree with artifact metadata and the source authority.

## Version changes

Changing the package version is an explicit source change to `src/relaylm/_version.py`. Any release transaction that changes it must rebuild and revalidate wheel and sdist rather than renaming an existing artifact.

Character Package `format_version`, runtime-config `format_version`, evaluation artifact schemas, and other domain/schema versions remain independent authorities. Package tooling must not mechanically advance them when the Python package version changes.

## Still unresolved in REL2

This slice intentionally does not choose among materially different release-policy alternatives. REL2 still must freeze, against fresh tag/release history and explicit release policy:

- git tag naming and tag-to-package-version mapping;
- development and release-candidate naming/numbering beyond the current valid PEP 440 source value;
- final-release transition policy;
- exact commit/tag provenance record;
- same-version overwrite rejection across accepted artifacts;
- rebuild identity/checksum expectations across release environments;
- packaging-only emergency-fix versioning.

Until those are frozen, the package-version source is authoritative but no source version alone constitutes an immutable public release identity.
