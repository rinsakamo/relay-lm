from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import relaylm_i1gc_durable_finalization_replay_smoke as i1gc
from relaylm import _relaymem_slp_durable_finalization_replay_impl as replay_impl
from relaylm import relaymem_slp_durable_finalization_replay as replay_public
from relaylm.relaymem_durable_finalization_formation_replay_patch import (
    install_durable_finalization_formation_replay_patch,
)
from relaylm.relaymem_slp_durable_finalization_record import canonical_json_bytes


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _assert_compatibility_hook_syncs_public_replay() -> None:
    original = replay_impl._reconstruct_source

    def stale_reconstruct_source(evidence):
        del evidence
        return None, ("stale_replay_reconstruct_source",)

    try:
        replay_impl._reconstruct_source = stale_reconstruct_source
        require(replay_impl._reconstruct_source is not replay_public._reconstruct_source, "setup_failed")
        install_durable_finalization_formation_replay_patch()
        require(
            replay_impl._reconstruct_source is replay_public._reconstruct_source,
            "compatibility_hook_did_not_sync_public_replay",
        )
    finally:
        replay_impl._reconstruct_source = original
        replay_public._sync_dependency_seams()


def main() -> None:
    _assert_compatibility_hook_syncs_public_replay()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = i1gc._config(root)
        base, seal, source_result, _ = i1gc._publish_sealed(root)
        require(source_result.source is not None, source_result)
        source = source_result.source
        mapping = seal["finalized_turn_source"]
        require(type(mapping) is dict, mapping)
        require("formation_summary_artifact" in mapping, mapping)
        require(
            canonical_json_bytes(mapping["formation_summary_artifact"])
            == canonical_json_bytes(source.formation_summary_artifact),
            mapping,
        )
        result = i1gc._replay(config, str(base["locator_digest"]))
        require(result.status == "completed", result)
        require(result.finalized_turn_source_result is not None, result)
        require(result.finalized_turn_source_result.source is not None, result)
        replay_source = result.finalized_turn_source_result.source
        require(
            canonical_json_bytes(replay_source.formation_summary_artifact)
            == canonical_json_bytes(source.formation_summary_artifact),
            result,
        )
    print("relaylm_i1gc_canonical_formation_replay_smoke: ok")


if __name__ == "__main__":
    main()
