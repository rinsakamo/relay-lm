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
from relaylm.relaymem_slp_durable_finalization_record import canonical_json_bytes


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
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
    print("relaylm_i1gc_durable_finalization_formation_replay_smoke: ok")


if __name__ == "__main__":
    main()
