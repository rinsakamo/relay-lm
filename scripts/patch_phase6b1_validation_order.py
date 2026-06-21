"""Apply the Phase 6-B1 validation-order fix, then remove this script."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "relaylm/relaymem_slp_dispatch_preflight.py"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    text = HELPER.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''    if runtime.get("candidate_kind") != "relayslp_deferred_job":
        return None, ("a2_candidate_kind_invalid",)
    if type(runtime.get("turn_index")) is not int or runtime.get("turn_index") < 0:
        return None, ("a2_candidate_runtime_turn_index_invalid",)
    if (
        type(runtime.get("source_count")) is not int
        or not 1 <= runtime.get("source_count") <= _MAX_SOURCES
    ):
        return None, ("a2_candidate_runtime_source_count_invalid",)
    if candidate.trigger_mode != "turn_end":
''',
        '''    if runtime.get("candidate_kind") != "relayslp_deferred_job":
        return None, ("a2_candidate_kind_invalid",)
    if candidate.trigger_mode != "turn_end":
''',
        label="remove early runtime counter validation",
    )

    text = replace_once(
        text,
        '''    if type(candidate.source_count) is not int or not 1 <= candidate.source_count <= _MAX_SOURCES:
        return None, ("a2_source_count_invalid",)
    if not _is_sha256(candidate.source_lineage_fingerprint):
''',
        '''    if type(candidate.source_count) is not int or not 1 <= candidate.source_count <= _MAX_SOURCES:
        return None, ("a2_source_count_invalid",)
    if type(runtime.get("turn_index")) is not int or runtime.get("turn_index") < 0:
        return None, ("a2_candidate_runtime_turn_index_invalid",)
    if (
        type(runtime.get("source_count")) is not int
        or not 1 <= runtime.get("source_count") <= _MAX_SOURCES
    ):
        return None, ("a2_candidate_runtime_source_count_invalid",)
    if not _is_sha256(candidate.source_lineage_fingerprint):
''',
        label="insert runtime counter validation after attributes",
    )

    text = replace_once(
        text,
        '''    if runtime.get("candidate_count") != 1 or runtime.get("candidate_created") is not True:
        return None, ("a2_runtime_candidate_cardinality_invalid",)
''',
        '''    if (
        type(runtime.get("candidate_count")) is not int
        or runtime.get("candidate_count") != 1
        or runtime.get("candidate_created") is not True
    ):
        return None, ("a2_runtime_candidate_cardinality_invalid",)
''',
        label="strict top-level candidate count",
    )

    HELPER.write_text(text, encoding="utf-8")
    print("Phase 6-B1 validation-order fix applied")


if __name__ == "__main__":
    main()
