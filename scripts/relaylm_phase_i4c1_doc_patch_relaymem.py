"""Apply deterministic I-4C1 RelayMEM current/target documentation updates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def swap(path: str, old: str, new: str) -> None:
    target = ROOT / path
    body = target.read_text(encoding="utf-8")
    if old not in body:
        if new in body:
            return
        raise RuntimeError(f"missing documentation anchor in {path}: {old[:72]!r}")
    if body.count(old) != 1:
        raise RuntimeError(f"ambiguous documentation anchor in {path}: {old[:72]!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


def mvp() -> None:
    path = "docs/architecture/relaymem_mvp_implementation_plan.md"
    swaps = (
        (
            "  - phase_i4b_primary_current_state_shared_fence.md\n",
            "  - phase_i4b_primary_current_state_shared_fence.md\n"
            "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "M3a-M3h, worker execution, protected-source restart recovery, C2 one-job execution, O0 explicit local operation, Phase I-1 recall, Phase I-2 observation, Phase I-3 Correct, and the I-4B read-only resolver/shared-fence boundary are complete. Phase I-4A defines the target Forget / Hide contract. The next RelayMEM governance implementation slice is I-4C1, not product-level Forget completion.",
            "M3a-M3h, worker execution, protected-source restart recovery, C2 one-job execution, O0 explicit local operation, Phase I-1 recall, Phase I-2 observation, Phase I-3 Correct, the I-4B read-only resolver/shared-fence boundary, and I-4C1 hidden-successor commit are complete. Phase I-4A defines the target Forget / Hide contract. The next RelayMEM governance implementation slice is I-4C2, not product-level Forget completion.",
        ),
        (
            "  -> I-4C token-gated hidden-successor apply/recovery\n  -> I-4D index/log and M2/RelayCTX exclusion convergence",
            "  -> I-4C1 token-gated prepared evidence and hidden-successor M3e commit\n  -> I-4C2 resume/replay/recovery/tombstone\n  -> I-4D index/log and M2/RelayCTX exclusion convergence",
        ),
        (
            "  M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B",
            "  M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B\n"
            "  M3i-g hidden-successor commit ownership: complete as Phase I-4C1",
        ),
        (
            "  Forget hidden apply/M2/UI/smoke: unimplemented as I-4C through I-4F",
            "  Forget hidden-successor commit: complete as I-4C1\n"
            "  Forget resume/replay/tombstone/M2/UI/full validation: unimplemented as I-4C2 through I-4F",
        ),
        (
            "The completed I-4B read-only boundary does not implement:\n\n- a hidden successor or prepared Forget artifact;\n- a Forget tombstone or recovery replay;",
            "The completed I-4C1 commit boundary does not implement:\n\n- prepared-operation resume, exact applied-result replay, or response-loss convergence;\n- a Forget tombstone or forward recovery beyond the M3e commit;",
        ),
        (
            "Phase I-2 observation receipts, correction artifacts, current-state operation evidence, and future Forget prepared/tombstone artifacts remain runtime-private non-candidates.",
            "Phase I-2 observation receipts, correction artifacts, current-state operation evidence, and the current Forget prepared artifact remain runtime-private non-candidates; the future Forget tombstone remains runtime-private as well.",
        ),
        (
            "Phase I-4B adds the canonical read-only Primary current-state resolver while preserving current active-state M2 behavior and Phase I-3 Correct compatibility. I-4D must consume lifecycle eligibility",
            "Phase I-4B adds the canonical read-only Primary current-state resolver and I-4C1 adds committed hidden lifecycle evidence while preserving current M2 behavior and Phase I-3 Correct compatibility. I-4D must consume lifecycle eligibility",
        ),
        (
            "No production hidden-state filtering exists yet because hidden apply and I-4D integration are not implemented.",
            "No production hidden-state filtering exists yet because I-4D integration is not implemented, even though I-4C1 can now durably commit the hidden lifecycle page.",
        ),
        (
            "## MEM-M3i: Runtime integration — complete through I-4B read-only lifecycle resolution",
            "## MEM-M3i: Runtime integration — complete through I-4C1 hidden lifecycle commit",
        ),
        (
            "- canonical read-only current-state resolution and shared Correct/Forget fence.",
            "- canonical read-only current-state resolution and shared Correct/Forget fence;\n"
            "- exact Forget prepared artifact and deterministic hidden-successor M3e commit.",
        ),
        (
            "It performs no Forget lifecycle write and changes no ordinary M2, RelayCTX, or browser behavior.\n\n### Remaining I-4 slices",
            "It performs no Forget lifecycle write and changes no ordinary M2, RelayCTX, or browser behavior.\n\n### I-4C1 hidden-successor commit — complete\n\nI-4C1 revalidates the exact token and bounded reason under the shared lock, claims one revision, publishes immutable `relaylm.mem.forget_prepared.v0`, constructs deterministic `relaymem.primary_lifecycle_page.v0`, passes through M3c/M3d/M3e, canonically rereads the page, and resolves `hidden / recovery_required / false`. It does not run M3f/M3g, finalize a tombstone, resume a prepared operation, or change M2.\n\n### Remaining I-4 slices",
        ),
        (
            "I-4C1  token/fence/revision ownership, prepared artifact,\n       hidden successor and M3e publication",
            "I-4C1  token/fence/revision ownership, prepared artifact,\n       hidden successor and M3e publication — complete",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def current_target() -> None:
    path = "docs/architecture/relaymem_slp_current_target.md"
    swaps = (
        (
            "  - phase_i4b_primary_current_state_shared_fence.md\n",
            "  - phase_i4b_primary_current_state_shared_fence.md\n"
            "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, and canonical read-only Primary current-state resolution.",
            "RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, and I-4C1 hidden-successor lifecycle commit ownership.",
        ),
        (
            "- Phase I-4B canonical read-only current-state resolver and shared Correct/Forget mutation fence.",
            "- Phase I-4B canonical read-only current-state resolver and shared Correct/Forget mutation fence;\n"
            "- Phase I-4C1 immutable Forget prepare and deterministic hidden-successor M3e commit.",
        ),
        (
            "Phase I-4B completes the canonical read-only Primary current-state resolver while preserving current active-state M2 and RelayCTX behavior.",
            "Phase I-4B completes the canonical read-only Primary current-state resolver. Phase I-4C1 consumes it to publish exact prepared evidence and a hidden successor while preserving current M2 and RelayCTX behavior until I-4D.",
        ),
        (
            "I-4B performs no hidden successor write, prepared Forget artifact, tombstone, index/log mutation, loopback route, or browser behavior change. Ordinary M2 and RelayCTX behavior remains unchanged until I-4D.\n\n## Defined target: Phase I-4A Forget / Hide",
            "I-4B itself performs no hidden successor write, prepared Forget artifact, tombstone, index/log mutation, loopback route, or browser behavior change. Ordinary M2 and RelayCTX behavior remains unchanged until I-4D.\n\n### Phase I-4C1 hidden-successor commit — complete\n\nI-4C1 revalidates the exact token/reason under the shared lock, publishes immutable `relaylm.mem.forget_prepared.v0`, deterministically constructs `relaymem.primary_lifecycle_page.v0`, delegates publication to existing M3c/M3d/M3e authority, canonically rereads the page, and returns `hidden / recovery_required / false`. It stops before M3f/M3g, tombstone, exact replay, and M2 exclusion.\n\n## Defined target: Phase I-4A Forget / Hide",
        ),
        (
            "- I-4C hidden-successor apply, prepared artifact, exact replay/recovery, and Forget tombstone finalization;",
            "- I-4C2 prepared resume, exact replay/response-loss convergence, forward recovery, and Forget tombstone finalization;",
        ),
        (
            "  -> canonical read-only lifecycle resolution        complete as I-4B",
            "  -> canonical read-only lifecycle resolution        complete as I-4B\n"
            "  -> hidden-successor lifecycle commit                complete as I-4C1",
        ),
        (
            "Phase I-4B adds no implemented hidden-lifecycle step to the ordinary retrieval path.",
            "Phase I-4C1 adds a durable hidden-lifecycle commit, but no implemented M2/RelayCTX exclusion step yet exists in the ordinary retrieval path.",
        ),
        (
            "I-4C1 shared revision claim, prepared artifact, hidden successor         unimplemented",
            "I-4C1 shared revision claim, prepared artifact, hidden successor         complete",
        ),
        (
            "I-4B completed the narrow resolver/fence refactor while preserving M2 relevance ownership and avoiding a broad generic mutation framework. I-4C and I-4D consume this boundary without absorbing queue or worker semantics.",
            "I-4B completed the narrow resolver/fence refactor and I-4C1 consumed it for the hidden lifecycle commit while preserving M2 relevance ownership and avoiding a broad generic mutation framework. I-4C2 and I-4D continue from this boundary without absorbing queue or worker semantics.",
        ),
        (
            "M3a-M3h, C1-0 through C1-5, C2, O0, I-1 recall, I-2 observation, I-3 Correct, and I-4B read-only current-state/fence/preflight-token-history are implemented. I-4A is the target contract. Forget is not product-complete until I-4C through I-4F provide hidden apply/recovery, retrieval exclusion, API/UI, and production validation.",
            "M3a-M3h, C1-0 through C1-5, C2, O0, I-1 recall, I-2 observation, I-3 Correct, I-4B read-only current-state/fence/preflight-token-history, and I-4C1 hidden-successor commit are implemented. I-4A is the target contract. Forget is not product-complete until I-4C2 through I-4F provide recovery/tombstone, retrieval exclusion, API/UI, and production validation.",
        ),
        (
            "UI-B0 and O0 are complete; O1/O2/O3 and I-4C through I-4F remain separate work.",
            "UI-B0 and O0 are complete; O1/O2/O3 and I-4C2 through I-4F remain separate work.",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def main() -> None:
    mvp()
    current_target()
    print("I-4C1 RelayMEM documentation updated")


if __name__ == "__main__":
    main()
