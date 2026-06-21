"""Apply the bounded Phase 6-B1 review fixes, then remove this script."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "relaylm/relaymem_slp_dispatch_preflight.py"
SECURITY_SMOKE = ROOT / "scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_helper() -> None:
    text = HELPER.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''}
_A2_CANDIDATE_FIELDS = {''',
        '''}
_A2_SOURCE_PROJECTION_FIELDS = {
    "trigger_mode",
    "processing_stage",
    "source_event_kind",
    "source_count",
    "correlation",
}
_A2_SOURCE_CORRELATION_FIELDS = {
    "run_id_present",
    "turn_index_present",
    "session_id_present",
    "namespace_present",
}
_A2_CANDIDATE_FIELDS = {''',
        label="projection allowlist constants",
    )

    text = replace_once(
        text,
        '''    if runtime.get("schema_version") != _SOURCE_RESULT_SCHEMA:
        return None, ("a2_handoff_schema_mismatch",)
    for field in ("helper_only", "diagnostics_only", "read_only"):
''',
        '''    if runtime.get("schema_version") != _SOURCE_RESULT_SCHEMA:
        return None, ("a2_handoff_schema_mismatch",)
    projection_errors = _validate_source_projection_runtime(
        source.source_projection,
        source_projection,
    )
    if projection_errors:
        return None, projection_errors
    for field in ("helper_only", "diagnostics_only", "read_only"):
''',
        label="serialized projection validation call",
    )

    text = replace_once(
        text,
        '''
def _validate_source_candidate_consistency(
''',
        '''
def _validate_source_projection_runtime(
    projection: RelayMEMSLPSourceProjection,
    runtime: object,
) -> tuple[str, ...]:
    if not isinstance(runtime, Mapping):
        return ("a2_source_projection_shape_invalid",)
    if (
        len(runtime) != len(_A2_SOURCE_PROJECTION_FIELDS)
        or set(runtime) != _A2_SOURCE_PROJECTION_FIELDS
    ):
        return ("a2_source_projection_shape_mismatch",)

    correlation = runtime.get("correlation")
    if not isinstance(correlation, Mapping):
        return ("a2_source_projection_correlation_invalid",)
    if (
        len(correlation) != len(_A2_SOURCE_CORRELATION_FIELDS)
        or set(correlation) != _A2_SOURCE_CORRELATION_FIELDS
    ):
        return ("a2_source_projection_correlation_shape_mismatch",)

    for field in ("trigger_mode", "processing_stage", "source_event_kind"):
        attribute = getattr(projection, field)
        runtime_value = runtime.get(field)
        if type(attribute) is not str or type(runtime_value) is not str:
            return ("a2_source_projection_enum_invalid",)
        if runtime_value != attribute:
            return (f"a2_source_projection_{field}_mismatch",)

    if (
        type(projection.source_count) is not int
        or not 1 <= projection.source_count <= _MAX_SOURCES
        or type(runtime.get("source_count")) is not int
        or runtime.get("source_count") != projection.source_count
    ):
        return ("a2_source_projection_source_count_invalid",)

    for field in _A2_SOURCE_CORRELATION_FIELDS:
        attribute = getattr(projection, field)
        runtime_value = correlation.get(field)
        if type(attribute) is not bool or type(runtime_value) is not bool:
            return ("a2_source_projection_presence_invalid",)
        if runtime_value is not attribute:
            return (f"a2_source_projection_{field}_mismatch",)
    return ()


def _validate_source_candidate_consistency(
''',
        label="serialized projection validator",
    )

    text = replace_once(
        text,
        '''    if runtime.get("candidate_kind") != "relayslp_deferred_job":
        return None, ("a2_candidate_kind_invalid",)
    if candidate.trigger_mode != "turn_end":
''',
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
        label="candidate runtime counter validation",
    )

    text = replace_once(
        text,
        '''        if runtime.get(field) != getattr(candidate, field):
            return None, (f"a2_candidate_{field}_mismatch",)
''',
        '''        runtime_value = runtime.get(field)
        attribute = getattr(candidate, field)
        if type(runtime_value) is not type(attribute) or runtime_value != attribute:
            return None, (f"a2_candidate_{field}_mismatch",)
''',
        label="candidate runtime strict equality",
    )

    HELPER.write_text(text, encoding="utf-8")


def patch_security_smoke() -> None:
    text = SECURITY_SMOKE.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPEnqueueCandidate,
    build_relaymem_slp_response_finalization_handoff,
)
''',
        '''from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPEnqueueCandidate,
    RelayMEMSLPSourceProjection,
    build_relaymem_slp_response_finalization_handoff,
)
''',
        label="source projection smoke import",
    )

    text = replace_once(
        text,
        '''    assert handoff.source_projection is not None
    _assert_consistency_rejected(
''',
        '''    assert handoff.source_projection is not None
    projection_original = RelayMEMSLPSourceProjection.to_log_dict

    def projection_extra_field(
        self: RelayMEMSLPSourceProjection,
    ) -> dict[str, object]:
        value = projection_original(self)
        value["private_value"] = "must-not-pass"
        return value

    RelayMEMSLPSourceProjection.to_log_dict = projection_extra_field  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_source_projection_shape_mismatch")
    finally:
        RelayMEMSLPSourceProjection.to_log_dict = projection_original  # type: ignore[method-assign]

    def projection_non_mapping(self: RelayMEMSLPSourceProjection) -> object:
        return ["invalid"]

    RelayMEMSLPSourceProjection.to_log_dict = projection_non_mapping  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_source_projection_shape_invalid")
    finally:
        RelayMEMSLPSourceProjection.to_log_dict = projection_original  # type: ignore[method-assign]

    _assert_consistency_rejected(
''',
        label="serialized projection smoke cases",
    )

    text = replace_once(
        text,
        '''    original = RelayMEMSLPEnqueueCandidate.to_runtime_dict

    def extra_field(self: RelayMEMSLPEnqueueCandidate) -> dict[str, object]:
''',
        '''    original = RelayMEMSLPEnqueueCandidate.to_runtime_dict

    def bool_runtime_turn_index(
        self: RelayMEMSLPEnqueueCandidate,
    ) -> dict[str, object]:
        value = original(self)
        value["turn_index"] = True
        return value

    RelayMEMSLPEnqueueCandidate.to_runtime_dict = bool_runtime_turn_index  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_candidate_runtime_turn_index_invalid")
    finally:
        RelayMEMSLPEnqueueCandidate.to_runtime_dict = original  # type: ignore[method-assign]

    def bool_runtime_source_count(
        self: RelayMEMSLPEnqueueCandidate,
    ) -> dict[str, object]:
        value = original(self)
        value["source_count"] = True
        return value

    RelayMEMSLPEnqueueCandidate.to_runtime_dict = bool_runtime_source_count  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_candidate_runtime_source_count_invalid")
    finally:
        RelayMEMSLPEnqueueCandidate.to_runtime_dict = original  # type: ignore[method-assign]

    def extra_field(self: RelayMEMSLPEnqueueCandidate) -> dict[str, object]:
''',
        label="candidate runtime counter smoke cases",
    )

    SECURITY_SMOKE.write_text(text, encoding="utf-8")


def main() -> None:
    patch_helper()
    patch_security_smoke()
    print("Phase 6-B1 review fixes applied")


if __name__ == "__main__":
    main()
