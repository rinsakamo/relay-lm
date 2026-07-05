"""Regression smoke for the Pydantic `schema` field to `schema_`/alias migration.

Proves, without touching any real memory store, that:
- affected SOUL Lab projection/request models no longer emit the BaseModel
  shadow warning on import or construction,
- projections still serialize the public `schema` key (not `schema_`) when
  dumped with `by_alias=True`, and
- request models still accept `{"schema": ...}` and reject the previous
  invalid/missing shapes.
"""
from __future__ import annotations

import warnings

from pydantic import ValidationError

from relaylm.soul_lab_held_governance import LabHeldGovernancePreflightRequest
from relaylm.soul_lab_lifecycle_visibility_projection import (
    LabDurableFinalizationVisibility,
    LabLifecycleVisibilityProjection,
    LabQueueWorkerVisibility,
)
from relaylm.soul_lab_memory_correction import LabMemoryCorrectPreflightRequest
from relaylm.soul_lab_memory_forget import LabMemoryForgetPreflightRequest
from relaylm.soul_lab_memory_pin import LabMemoryPinPreflightRequest
from relaylm.soul_lab_observation_projection import LabLastRunProjection
from relaylm.soul_lab_used_memory_lifecycle_projection import LabMemoryUsedLifecycleProjection

_PROJECTION_SCHEMA_FIELD_NAMES = (
    LabLastRunProjection,
    LabLifecycleVisibilityProjection,
    LabMemoryUsedLifecycleProjection,
)
_REQUEST_MODELS = (
    (LabMemoryForgetPreflightRequest, "relaylm.lab.memory_forget_preflight_request.v0"),
    (LabMemoryCorrectPreflightRequest, "relaylm.lab.memory_correct_preflight_request.v0"),
    (LabMemoryPinPreflightRequest, "relaylm.lab.memory_pin_preflight_request.v0"),
    (LabHeldGovernancePreflightRequest, "relaylm.lab.held_governance_preflight_request.v0"),
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def check_no_shadow_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for model in _PROJECTION_SCHEMA_FIELD_NAMES:
            require(
                "schema_" in model.model_fields,
                (model, "expected internal attribute name schema_"),
            )
            require(
                model.model_fields["schema_"].alias == "schema",
                (model, "expected public alias schema"),
            )
        for model, _ in _REQUEST_MODELS:
            require(
                "schema_" in model.model_fields,
                (model, "expected internal attribute name schema_"),
            )
            require(
                model.model_fields["schema_"].alias == "schema",
                (model, "expected public alias schema"),
            )
        shadow_warnings = [
            item for item in caught if "shadows an attribute" in str(item.message)
        ]
        require(not shadow_warnings, [str(item.message) for item in shadow_warnings])


def check_projection_alias_serialization() -> None:
    last_run = LabLastRunProjection(
        availability="empty",
        character_id="smoke-character",
        namespace="smoke-namespace",
        run_id=None,
        status="empty",
        started_at=None,
        completed_at=None,
        duration_ms=None,
        response_mode="unknown",
        slp_status="unavailable",
        memory_outcome_status="none",
        relayrun_status="unavailable",
        relayctx_repack_status="unavailable",
        relayctx_unpack_status="unavailable",
        formed_count=0,
        held_count=0,
        blocked_count=0,
        used_memory_count=0,
        recovery_required=False,
        bounded_reason_ids=[],
    )
    aliased = last_run.model_dump(mode="json", by_alias=True)
    require(aliased.get("schema") == "relaylm.lab.last_run.v0", aliased)
    require("schema_" not in aliased, aliased)

    lifecycle = LabLifecycleVisibilityProjection(
        availability="empty",
        character_id="smoke-character",
        namespace="smoke-namespace",
        memory_items=[],
        durable_finalization=LabDurableFinalizationVisibility(
            availability="not_connected",
            status="not_connected",
            pending_count=0,
            complete_count=0,
            isolated_count=0,
            bounded_reason_ids=[],
        ),
        queue_worker=LabQueueWorkerVisibility(
            availability="not_connected",
            status="not_connected",
            queued_count=0,
            processing_count=0,
            formed_count=0,
            held_count=0,
            blocked_count=0,
            failed_count=0,
            bounded_reason_ids=[],
        ),
        bounded_reason_ids=[],
    )
    aliased = lifecycle.model_dump(mode="json", by_alias=True)
    require(aliased.get("schema") == "relaylm.lab.lifecycle_visibility.v0", aliased)
    require("schema_" not in aliased, aliased)


def check_request_models_accept_alias_and_reject_as_before() -> None:
    for model, schema_value in _REQUEST_MODELS:
        payload = _minimal_payload(model, schema_value)
        parsed = model.model_validate(payload)
        require(parsed.schema_ == schema_value, (model, parsed))
        require(parsed.model_dump(by_alias=True) == payload, (model, parsed.model_dump(by_alias=True)))

        missing = dict(payload)
        del missing["schema"]
        try:
            model.model_validate(missing)
            raise AssertionError((model, "missing schema unexpectedly accepted"))
        except ValidationError:
            pass

        wrong_literal = dict(payload)
        wrong_literal["schema"] = "relaylm.lab.wrong_schema.v0"
        try:
            model.model_validate(wrong_literal)
            raise AssertionError((model, "invalid schema literal unexpectedly accepted"))
        except ValidationError:
            pass

        broadened = dict(payload)
        broadened["schema_"] = broadened.pop("schema")
        try:
            model.model_validate(broadened)
            raise AssertionError((model, "schema_ key unexpectedly accepted, contract broadened"))
        except ValidationError:
            pass

        extra = dict(payload)
        extra["unexpected_extra_field"] = "x"
        try:
            model.model_validate(extra)
            raise AssertionError((model, "extra field unexpectedly accepted"))
        except ValidationError:
            pass


def _minimal_payload(model: type, schema_value: str) -> dict[str, object]:
    payload: dict[str, object] = {"schema": schema_value}
    if "expected_revision" in model.model_fields:
        payload["expected_revision"] = 1
    if "reason" in model.model_fields:
        payload["reason"] = "operator-requested"
    if "operation_id" in model.model_fields:
        payload["operation_id"] = "op-1"
    if "expected_lifecycle_state" in model.model_fields:
        payload["expected_lifecycle_state"] = "active"
    if "corrected_title" in model.model_fields:
        payload["corrected_title"] = "Corrected title"
    if "corrected_summary" in model.model_fields:
        payload["corrected_summary"] = "Corrected summary"
    return payload


def main() -> int:
    check_no_shadow_warning()
    check_projection_alias_serialization()
    check_request_models_accept_alias_and_reject_as_before()
    print("Pydantic schema alias migration smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
