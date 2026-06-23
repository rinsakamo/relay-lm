from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    source_path = Path("relaylm/relaymem_slp_finalized_turn_source.py")
    source = source_path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''    persistence_status = (
        "blocked" if scene.get("persistence_block") is True else "allowed"
    )
    source = RelayMEMSLPFinalizedTurnSource(
''',
        '''    if scene.get("persistence_block") is True:
        return _result(
            "blocked",
            enabled=True,
            response_finalized=True,
            blocked_reasons=("scene_persistence_blocked",),
        )
    source = RelayMEMSLPFinalizedTurnSource(
''',
        "scene persistence fail closed",
    )
    source = replace_once(
        source,
        "        persistence_policy_status=persistence_status,\n",
        "        persistence_policy_status=\"allowed\",\n",
        "allowed source policy",
    )
    source_path.write_text(source, encoding="utf-8")

    finalization_path = Path("relaylm/relaymem_slp_runtime_finalization.py")
    finalization = finalization_path.read_text(encoding="utf-8")
    marker = "def run_relaymem_slp_runtime_enqueue_after_response("
    prefix, separator, suffix = finalization.partition(marker)
    if not separator:
        raise SystemExit("background function marker missing")
    suffix = suffix.replace("except BaseException:", "except Exception:", 2)
    finalization_path.write_text(prefix + separator + suffix, encoding="utf-8")


if __name__ == "__main__":
    main()
