# Release Candidate Mechanical Gate

Status: REL3 mechanical gate contract for RelayLM v1. Owning Issue: #1447.

REL3 proves the release-candidate mechanics against the **exact built wheel and sdist**, not merely against the source checkout. It does not choose cognitive defaults, decide RelayLM 1.0 readiness, create a git tag, or publish artifacts to a public distribution channel.

## Invocation boundary

The candidate workflow is `.github/workflows/v1-release-candidate.yml` and is manually dispatched with one explicit `candidate_commit`.

A candidate run fails closed unless:

- the requested SHA is a lowercase exact commit identity;
- the checked-out commit equals that SHA;
- a fresh fetch shows that SHA is the exact current remote `v1` HEAD;
- the working tree is clean before build;
- the package version is an REL2 `rc` or final version rather than a development version;
- a fresh tag fetch shows the REL2 expected `v<version>` tag is not already present.

Therefore the current `1.0.0.dev0` development line cannot accidentally pass as a release candidate. Promoting the package source to `1.0.0rc1` is a separate future release transaction and must not happen until the applicable #1388/#1446/#1449 upstream gates permit an actual RC.

## Exact artifact authority

The workflow builds one candidate wheel/sdist pair into `candidate/`. It also builds a second comparison pair into `rebuild/` and requires byte equality with the candidate pair. The comparison build is reproducibility evidence only; it never replaces the candidate pair.

From that point forward every installed-artifact check consumes the exact files in `candidate/`:

1. wheel/sdist metadata and required-file inspection;
2. REL2 manifest generation binding version, expected tag, exact commit, filenames, and SHA-256;
3. fresh non-editable wheel installation outside the repository checkout;
4. installed `relaylm --version`;
5. installed non-generative `relaylm doctor --json`;
6. installed `relaylm-eval` with `relaylm-native` status `pass`;
7. installed `relaylm serve` startup plus `/health` response from the wheel path;
8. a second fresh non-editable install from the exact sdist, with version/doctor/evaluation checks;
9. manifest/hash verification again after all execution, proving the tested bytes did not change.

`relaylm-eval` is the deterministic RelayLM-native artifact-level gate. Ordinary source CI remains a prerequisite for merging the candidate commit, but source pytest is not substituted for the installed candidate validation above.

The scratch Character and runtime configuration are generated in the runner temporary directory. They are not packaged data and do not become Character semantic authority.

## Candidate evidence bundle

A successful run preserves one GitHub Actions artifact named with exact package version and commit. The bundle contains:

- the exact candidate wheel;
- the exact candidate sdist;
- `release-identity.json` with SHA-256 artifact provenance;
- recorded build-environment versions;
- content-free installed `doctor` evidence;
- deterministic evaluation reports;
- wheel `serve` log and `/health` response.

The Actions artifact is CI evidence, not a public release channel. REL4 remains responsible for any later GitHub Release, PyPI, or other publication target and must publish only an approved exact candidate artifact.

## Relationship to runtime/default owners

REL3 consumes #1446 operator semantics and does not redefine them. RCFG6 already consumes REL1 installed-artifact evidence. Current #1446 still has RCFG5 blocked on #1388 canonical calibrated profile/default authority.

Accordingly, implementing this workflow does **not** authorize `1.0.0rc1` or declare REL3 acceptance complete. An actual candidate run must use the then-current #1446 path and applicable #1388 defaults/profile authority before #1449 can consume the evidence for final readiness.

## Tag and publication boundary

REL3 does not create tags. Immediately before an actual candidate run it refreshes tags and rejects a pre-existing expected identity. A successful mechanical run produces evidence that may later support an explicitly authorized immutable tag transaction; it does not itself mutate tag authority.

REL3 also does not upload to a public package registry or create a GitHub Release. The retained Actions artifact has bounded CI retention and preserves the exact tested bytes for review/hand-off only.

## Completion boundary

The REL3 **mechanics implementation** is complete when this workflow/tooling is green under normal v1 regression and its helper contract is tested. Full REL3 candidate acceptance remains pending until:

1. the source version is an authorized RC/final identity;
2. current upstream #1388/#1446 release dependencies are satisfied for that candidate;
3. the workflow passes on the exact current v1 commit;
4. the resulting candidate evidence bundle is the exact artifact later referenced by #1449/publication decisions.
