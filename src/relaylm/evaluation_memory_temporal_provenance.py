from __future__ import annotations

from collections.abc import Callable

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
)


def _raises(error: type[Exception], action: Callable[[], object]) -> bool:
    try:
        action()
    except error:
        return True
    except Exception:
        return False
    return False


async def evaluate_memory_temporal_provenance() -> EvaluationScenarioResult:
    event_source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.EVENT,
        reference_id="event-123",
    )
    state_source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.STATE,
        reference_id="state-456",
    )
    provenance = MemoryProvenance(
        memory_id="memory-preferred-beverage",
        derivation_id="crystallization-2026-08-18-a",
        sources=(event_source, state_source),
    )

    unknown_without_provenance = MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.UNKNOWN,
    )
    current = MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.CURRENT,
        provenance=provenance,
    )
    historical = MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.HISTORICAL,
        provenance=provenance,
    )
    unknown_with_provenance = MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.UNKNOWN,
        provenance=provenance,
    )

    invalid_rejections = (
        _raises(ValueError, lambda: MemoryTemporalScope("formerly")),
        _raises(ValueError, lambda: MemoryProvenanceSourceKind("markdown")),
        _raises(
            TypeError,
            lambda: MemoryProvenanceSource(
                kind="event",  # type: ignore[arg-type]
                reference_id="event-123",
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryProvenanceSource(
                kind=MemoryProvenanceSourceKind.EVENT,
                reference_id=" ",
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryProvenance(
                memory_id=" ",
                derivation_id="derivation-1",
                sources=(event_source,),
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryProvenance(
                memory_id="memory-1",
                derivation_id=" ",
                sources=(event_source,),
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryProvenance(
                memory_id="memory-1",
                derivation_id="derivation-1",
                sources=(),
            ),
        ),
        _raises(
            TypeError,
            lambda: MemoryProvenance(
                memory_id="memory-1",
                derivation_id="derivation-1",
                sources=("event-123",),  # type: ignore[arg-type]
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryTemporalAuthority(
                temporal_scope=MemoryTemporalScope.CURRENT,
            ),
        ),
        _raises(
            ValueError,
            lambda: MemoryTemporalAuthority(
                temporal_scope=MemoryTemporalScope.HISTORICAL,
            ),
        ),
    )

    checks = (
        EvaluationCheck(
            check_id="temporal_scope_is_closed_and_unknown_is_first_class",
            boundary="memory_provenance",
            passed=(
                tuple(scope.value for scope in MemoryTemporalScope)
                == ("current", "historical", "unknown")
                and unknown_without_provenance.temporal_scope
                is MemoryTemporalScope.UNKNOWN
                and unknown_without_provenance.provenance is None
            ),
            expected="current,historical,unknown",
            observed=",".join(scope.value for scope in MemoryTemporalScope),
        ),
        EvaluationCheck(
            check_id="provenance_sources_are_typed_event_or_state_only",
            boundary="memory_provenance",
            passed=(
                tuple(kind.value for kind in MemoryProvenanceSourceKind)
                == ("event", "state")
                and event_source.kind is MemoryProvenanceSourceKind.EVENT
                and state_source.kind is MemoryProvenanceSourceKind.STATE
                and event_source.reference_id == "event-123"
                and state_source.reference_id == "state-456"
            ),
            expected="event,state",
            observed=",".join(kind.value for kind in MemoryProvenanceSourceKind),
        ),
        EvaluationCheck(
            check_id="classified_authority_requires_typed_provenance",
            boundary="memory_provenance",
            passed=(
                current.provenance is provenance
                and historical.provenance is provenance
                and invalid_rejections[8]
                and invalid_rejections[9]
            ),
            expected=2,
            observed=sum((invalid_rejections[8], invalid_rejections[9])),
        ),
        EvaluationCheck(
            check_id="provenance_requires_stable_memory_and_derivation_identity",
            boundary="memory_provenance",
            passed=(
                provenance.memory_id == "memory-preferred-beverage"
                and provenance.derivation_id == "crystallization-2026-08-18-a"
                and provenance.sources == (event_source, state_source)
                and all(invalid_rejections[index] for index in (4, 5, 6, 7))
            ),
            expected=True,
            observed=(
                provenance.memory_id == "memory-preferred-beverage"
                and provenance.derivation_id == "crystallization-2026-08-18-a"
            ),
        ),
        EvaluationCheck(
            check_id="unknown_scope_may_preserve_provenance_without_promotion",
            boundary="memory_provenance",
            passed=(
                unknown_with_provenance.temporal_scope is MemoryTemporalScope.UNKNOWN
                and unknown_with_provenance.provenance is provenance
            ),
            expected="unknown",
            observed=unknown_with_provenance.temporal_scope.value,
        ),
        EvaluationCheck(
            check_id="invalid_and_untyped_provenance_inputs_are_rejected",
            boundary="memory_provenance",
            passed=all(invalid_rejections),
            expected=10,
            observed=sum(invalid_rejections),
        ),
    )
    classified = (current, historical)
    valid_sources = (event_source, state_source)
    return EvaluationScenarioResult(
        scenario_id="memory_temporal_provenance",
        checks=checks,
        metrics={
            "temporal_scope_count": len(MemoryTemporalScope),
            "provenance_source_kind_count": len(MemoryProvenanceSourceKind),
            "classified_scope_count": len(classified),
            "valid_source_count": len(valid_sources),
            "invalid_input_rejection_count": sum(invalid_rejections),
        },
    )
