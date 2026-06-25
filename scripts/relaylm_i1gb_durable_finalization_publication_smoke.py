"""I1-GB production record/store contract, security, and leakage smoke."""
from __future__ import annotations

import json
import os
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from relaylm.config import BackendConfig, RelayLMConfig
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_durable_finalization_record import (
    RECORD_SCHEMA,
    ZERO_DIGEST,
    base_filename,
    build_base_record,
    build_seal_record,
    build_segment_record,
    canonical_json_bytes,
    derive_locator_digest,
    seal_filename,
    segment_filename,
    validate_seal_record,
    validate_segment_record,
)
from relaylm.relaymem_slp_durable_finalization_store import (
    RelayMEMSLPDurableFinalizationStore,
)
import relaylm.relaymem_slp_durable_finalization_store as store_module
from relaylm.relaymem_slp_finalized_turn_source import (
    build_relaymem_slp_finalized_turn_source,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    prepare_relaymem_slp_runtime_enqueue,
)
from relaylm.routing import ResolvedRoute

USER_CANARY = "CANARY_I1GB_STORE_USER_DO_NOT_LEAK"
ASSISTANT_CANARY = "CANARY_I1GB_STORE_ASSISTANT_DO_NOT_LEAK"
NAMESPACE_CANARY = "CANARY_I1GB_STORE_NAMESPACE_DO_NOT_LEAK"
RUN_ID = "run-i1gb-store"
CHARACTER_ID = "character-i1gb"
SESSION_ID = "session-i1gb"
REQUEST_ID = "request-i1gb"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _route() -> ResolvedRoute:
    return ResolvedRoute(
        route_model="relay-i1gb",
        backend_name="local",
        backend=BackendConfig(base_url="http://127.0.0.1:1234/v1"),
        backend_model="backend",
        character_id=CHARACTER_ID,
        mode_requested="memory_light",
        mode_applied="memory_light",
        cache_namespace="cache-i1gb",
        memory_namespace=NAMESPACE_CANARY,
        session_id=SESSION_ID,
        client_history_exclusion_preflight_enabled=True,
    )


def _context(*, request_id: str = REQUEST_ID) -> PipelineContext:
    payload = {
        "model": "relay-i1gb",
        "messages": [{"role": "user", "content": USER_CANARY}],
    }
    return PipelineContext(
        request_id=request_id,
        run_id=RUN_ID,
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=_route(),
        stream_enabled=False,
    )


def _scene() -> dict[str, object]:
    return {
        "scene_state": {
            "scene_type": "implementation_work",
            "confidence": 0.99,
            "stability": 0.99,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _emo() -> dict[str, object]:
    return {
        "assistant_emotion_state": {"intensity": 0.2},
        "user_affect_estimate": {"confidence": 0.8, "mode": "engaged"},
    }


def _records(
    *, contents: tuple[str, ...] = (), request_id: str = REQUEST_ID
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    base = build_base_record(
        run_id=RUN_ID,
        turn_index=0,
        character_id=CHARACTER_ID,
        request_correlation=request_id,
        stream_mode=bool(contents),
        static_finalized_turn_inputs={
            "status_code": 200,
            "resolved_session_id": SESSION_ID,
            "namespace": NAMESPACE_CANARY,
            "current_user_message": {"role": "user", "content": USER_CANARY},
            "relayscn_scene_policy_artifact": _scene(),
            "relayemo_artifact": _emo(),
        },
    )
    segments: list[dict[str, object]] = []
    previous = ZERO_DIGEST
    for sequence, content in enumerate(contents):
        segment = build_segment_record(
            base=base,
            sequence=sequence,
            previous_segment_digest=previous,
            content=content.encode("utf-8"),
        )
        segments.append(segment)
        previous = str(segment["segment_digest"])
    visible = "".join(contents) if contents else ASSISTANT_CANARY
    source = build_relaymem_slp_finalized_turn_source(
        _context(request_id=request_id),
        assistant_visible_text=visible,
        status_code=200,
        resolved_session_id=SESSION_ID,
        relayscn_scene_policy_artifact=_scene(),
        relayemo_artifact=_emo(),
        response_finalized=True,
        enabled=True,
    )
    require(source.status == "ready", source.to_log_dict())
    prepared = prepare_relaymem_slp_runtime_enqueue(source)
    require(prepared.status == "dry_run_ready", prepared.to_log_dict())
    seal = build_seal_record(
        base=base,
        segments=segments,
        visible_content=visible.encode("utf-8"),
        finalized_turn_source_result=source,
        prepared_runtime_enqueue=prepared,
    )
    return base, segments, seal


def _store(root: Path, **overrides: int) -> RelayMEMSLPDurableFinalizationStore:
    values = {
        "max_record_bytes": 512 * 1024,
        "max_segment_bytes": 64 * 1024,
        "max_segment_count": 256,
        "max_record_count": 1024,
        "operation_timeout_ms": 5000,
    }
    values.update(overrides)
    return RelayMEMSLPDurableFinalizationStore(str(root.resolve()), **values)


def _publish(
    store: RelayMEMSLPDurableFinalizationStore,
    base: dict[str, object],
    segments: list[dict[str, object]],
    seal: dict[str, object],
) -> None:
    require(store.publish_base(base).status == "published_new", base)
    for segment in segments:
        require(store.publish_segment(segment).status == "published_new", segment)
    sealed = store.publish_seal(seal)
    require(sealed.status == "published_new", sealed)
    require(sealed.sealed and sealed.replayable, sealed)


def _write_invalid(root: Path, base: dict[str, object], data: bytes) -> None:
    (root / base_filename(str(base["locator_digest"]))).write_bytes(data)


def _assert_content_free(value: object) -> None:
    text = repr(value)
    for canary in (
        USER_CANARY,
        ASSISTANT_CANARY,
        NAMESPACE_CANARY,
        RUN_ID,
        SESSION_ID,
        REQUEST_ID,
        "slp-job-v0:",
        "slp-dispatch-v0:",
    ):
        require(canary not in text, (canary, text))


def test_valid_and_duplicate() -> None:
    # 1. valid non-stream base + seal; 3. exact equivalent convergence.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = _store(root)
        base, segments, seal = _records()
        _publish(store, base, segments, seal)
        duplicate_base = store.publish_base(base)
        duplicate_seal = store.publish_seal(seal)
        require(duplicate_base.status == "duplicate_existing", duplicate_base)
        require(duplicate_seal.status == "duplicate_existing", duplicate_seal)
        loaded = store.read_evidence(str(base["locator_digest"]))
        require(loaded.status == "loaded", loaded)
        require(loaded.sealed and loaded.replayable, loaded)
        _assert_content_free(loaded)

    # 2. valid ordered stream segments + seal.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = _store(root)
        base, segments, seal = _records(contents=("hello ", "world"))
        _publish(store, base, segments, seal)
        loaded = store.read_evidence(str(base["locator_digest"]))
        require(loaded.bounded_segment_count == 2, loaded)
        require(loaded.evidence is not None and loaded.evidence.replayable, loaded)


def test_collision_chain_and_schema_validation() -> None:
    # 4. same locator / different protected content collision.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = _store(root)
        base, _, _ = _records()
        require(store.publish_base(base).status == "published_new", base)
        other, _, _ = _records(request_id="request-i1gb-other")
        collision = store.publish_base(other)
        require(collision.status == "collision", collision)

    base, segments, seal = _records(contents=("a", "b"))
    # 5. order mismatch.
    wrong_order = dict(segments[1])
    _, reasons = validate_segment_record(
        wrong_order,
        expected_base=base,
        expected_sequence=0,
        expected_previous_digest=ZERO_DIGEST,
    )
    require("durable_finalization_segment_order_mismatch" in reasons, reasons)
    # 6. chain mismatch.
    wrong_chain = dict(segments[1])
    wrong_chain["previous_segment_digest"] = ZERO_DIGEST
    _, reasons = validate_segment_record(
        wrong_chain,
        expected_base=base,
        expected_sequence=1,
        expected_previous_digest=str(segments[0]["segment_digest"]),
    )
    require("durable_finalization_segment_chain_mismatch" in reasons, reasons)
    # 7. seal digest mismatch.
    bad_seal = dict(seal)
    bad_seal["seal_digest"] = ZERO_DIGEST
    _, reasons = validate_seal_record(
        bad_seal, expected_base=base, expected_segments=segments
    )
    require("durable_finalization_seal_digest_mismatch" in reasons, reasons)

    malformed_cases: list[tuple[str, bytes]] = []
    # 8. unknown field.
    unknown = dict(base)
    unknown["unknown"] = True
    malformed_cases.append(("unknown", canonical_json_bytes(unknown)))
    # 9. duplicate JSON key.
    valid_text = canonical_json_bytes(base).decode("utf-8")
    duplicate = valid_text[:-1] + ',"schema_version":"' + RECORD_SCHEMA + '"}'
    malformed_cases.append(("duplicate", duplicate.encode("utf-8")))
    # 10. malformed UTF-8.
    malformed_cases.append(("utf8", b"\xff\xfe"))
    # 11. malformed JSON.
    malformed_cases.append(("json", b'{"schema_version":'))
    # 12. noncanonical bytes.
    malformed_cases.append(
        ("noncanonical", json.dumps(base, ensure_ascii=False, indent=2).encode("utf-8"))
    )
    # 13. unsupported schema.
    unsupported = dict(base)
    unsupported["schema_version"] = "relaymem.slp_durable_finalization.v999"
    malformed_cases.append(("schema", canonical_json_bytes(unsupported)))
    # 14. revision mismatch.
    revision = dict(base)
    revision["record_revision"] = 1
    malformed_cases.append(("revision", canonical_json_bytes(revision)))

    for label, data in malformed_cases:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_invalid(root, base, data)
            result = _store(root).read_evidence(str(base["locator_digest"]))
            require(result.status == "corrupt", (label, result))

    # Impossible marker combination: a segment or seal without its base is corrupt,
    # and base publication must not silently repair it.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        orphan_name = segment_filename(str(base["locator_digest"]), 0)
        (root / orphan_name).write_bytes(canonical_json_bytes(segments[0]))
        store = _store(root)
        result = store.read_evidence(str(base["locator_digest"]))
        require(result.status == "corrupt", result)
        require(store.publish_base(base).status == "corrupt", result)


def test_bounds_and_capacity() -> None:
    base, segments, seal = _records(contents=("x" * 200,))
    # 15. oversized base.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        result = _store(
            root, max_record_bytes=128, max_segment_bytes=64
        ).publish_base(base)
        require(result.status == "capacity_exceeded", result)
    # 16. oversized segment.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = _store(root, max_segment_bytes=128)
        require(store.publish_base(base).status == "published_new", base)
        result = store.publish_segment(segments[0])
        require(result.status == "capacity_exceeded", result)
    # 17. segment count overflow.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        base2, segments2, _ = _records(contents=("a", "b"))
        store = _store(root, max_segment_count=1)
        require(store.publish_base(base2).status == "published_new", base2)
        require(store.publish_segment(segments2[0]).status == "published_new", segments2)
        result = store.publish_segment(segments2[1])
        require(result.status == "capacity_exceeded", result)
    # 18. total record capacity overflow.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        base3, segments3, _ = _records(contents=("z" * 100,))
        base_size = len(canonical_json_bytes(base3))
        segment_size = len(canonical_json_bytes(segments3[0]))
        maximum = base_size + segment_size - 1
        store = _store(
            root,
            max_record_bytes=maximum,
            max_segment_bytes=min(maximum, segment_size + 8),
        )
        require(store.publish_base(base3).status == "published_new", base3)
        result = store.publish_segment(segments3[0])
        require(result.status == "capacity_exceeded", result)
    # Extra bounded logical-record count admission.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        first, _, _ = _records()
        second = build_base_record(
            run_id="run-i1gb-second",
            turn_index=0,
            character_id=CHARACTER_ID,
            request_correlation="request-i1gb-second",
            stream_mode=False,
            static_finalized_turn_inputs={"value": "second"},
        )
        store = _store(root, max_record_count=1)
        require(store.publish_base(first).status == "published_new", first)
        require(store.publish_base(second).status == "capacity_exceeded", second)


def test_root_path_and_file_security() -> None:
    base, _, _ = _records()
    # 19. relative root rejection.
    relative = RelayMEMSLPDurableFinalizationStore("relative-root")
    require(relative.publish_base(base).status == "blocked", relative)
    # 20. missing root rejection.
    with TemporaryDirectory() as directory:
        missing = Path(directory) / "missing"
        require(_store(missing).publish_base(base).status == "blocked", missing)
    # 21. symlink root.
    with TemporaryDirectory() as directory:
        parent = Path(directory)
        real = parent / "real"
        real.mkdir()
        link = parent / "link"
        link.symlink_to(real, target_is_directory=True)
        result = RelayMEMSLPDurableFinalizationStore(str(link.resolve(strict=False)))
        # Path.resolve follows the link, so use literal absolute symlink path.
        result = RelayMEMSLPDurableFinalizationStore(str(link.absolute())).publish_base(base)
        require(result.status == "blocked", result)
    # 22. symlink record component.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "target"
        target.write_text("{}", encoding="utf-8")
        (root / base_filename(str(base["locator_digest"]))).symlink_to(target)
        result = _store(root).publish_base(base)
        require(result.status == "corrupt", result)
    # 23. path escape.
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        escaped = str(root / "child" / "..")
        result = RelayMEMSLPDurableFinalizationStore(escaped).publish_base(base)
        require(result.status == "blocked", result)
    # 24. unsafe file type.
    if hasattr(os, "mkfifo"):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            os.mkfifo(root / base_filename(str(base["locator_digest"])))
            result = _store(root).publish_base(base)
            require(result.status == "corrupt", result)


def test_publication_faults_and_reread() -> None:
    base, _, _ = _records()
    # 25. temp write failure.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(
            store_module,
            "_write_all",
            side_effect=OSError("write failed"),
        ):
            result = _store(root).publish_base(base)
        require(result.status == "failed", result)
    # 26. atomic publication ambiguity.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(store_module, "_rename_noreplace", return_value="failed"):
            result = _store(root).publish_base(base)
        require(result.status == "ambiguous", result)
    # 27. file fsync failure.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(store_module, "_fsync", side_effect=OSError("fsync")):
            result = _store(root).publish_base(base)
        require(result.status == "failed", result)
    # 28. directory fsync failure must remain ambiguous, never inferred success.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls = 0

        def fail_second(fd: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("dir fsync")
            os.fsync(fd)

        with patch.object(store_module, "_fsync", side_effect=fail_second):
            result = _store(root).publish_base(base)
        require(result.status == "ambiguous", result)
        require(result.record_present, result)
    # 29. canonical reread is required after publication.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = _store(root)
        original = store._read_named  # noqa: SLF001 - intentional fault seam
        calls = 0

        def fail_publication_reread(
            self: RelayMEMSLPDurableFinalizationStore,
            root_fd: int,
            filename: str,
            *,
            kind: str,
        ) -> tuple[dict[str, object] | None, str, tuple[str, ...]]:
            nonlocal calls
            calls += 1
            if calls == 2:
                return None, "failed", ("injected_canonical_reread_failure",)
            return original(root_fd, filename, kind=kind)

        store._read_named = types.MethodType(  # type: ignore[method-assign]  # noqa: SLF001
            fail_publication_reread, store
        )
        result = store.publish_base(base)
        require(result.status == "failed", result)


def test_leakage_and_locator() -> None:
    # Deterministic locator contains no raw protected identity.
    locator = derive_locator_digest(
        run_id=RUN_ID, turn_index=0, character_id=CHARACTER_ID
    )
    require(len(locator) == 64, locator)
    filename = base_filename(locator)
    for protected in (RUN_ID, CHARACTER_ID, USER_CANARY, NAMESPACE_CANARY):
        require(protected not in filename, filename)
    # 30. protected content leakage canary.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        base, segments, seal = _records(contents=(ASSISTANT_CANARY,))
        store = _store(root)
        _publish(store, base, segments, seal)
        result = store.read_evidence(str(base["locator_digest"]))
        _assert_content_free(result)
        _assert_content_free(result.evidence)
        require(RECORD_SCHEMA in canonical_json_bytes(base).decode("utf-8"), base)



def test_config_validation() -> None:
    common = {
        "backends": {"local": BackendConfig(base_url="http://127.0.0.1:1234/v1")},
        "model_routes": {},
    }
    config = RelayLMConfig(**common)
    require(config.relaymem_slp_durable_finalization_enabled is False, config)
    require(config.relaymem_slp_durable_finalization_dry_run_only is True, config)
    require(config.relaymem_slp_durable_finalization_apply_enabled is False, config)
    for field, value in (
        ("relaymem_slp_durable_finalization_enabled", 1),
        ("relaymem_slp_durable_finalization_dry_run_only", 0),
        ("relaymem_slp_durable_finalization_apply_enabled", 1),
        ("relaymem_slp_durable_finalization_max_record_bytes", True),
        ("relaymem_slp_durable_finalization_max_segment_bytes", False),
        ("relaymem_slp_durable_finalization_max_segment_count", True),
        ("relaymem_slp_durable_finalization_max_record_count", False),
        ("relaymem_slp_durable_finalization_publication_timeout_ms", True),
    ):
        try:
            RelayLMConfig(**common, **{field: value})
        except ValidationError:
            continue
        raise AssertionError(("strict config unexpectedly accepted", field, value))


def main() -> None:
    test_valid_and_duplicate()
    test_collision_chain_and_schema_validation()
    test_bounds_and_capacity()
    test_root_path_and_file_security()
    test_publication_faults_and_reread()
    test_leakage_and_locator()
    test_config_validation()
    print("I1-GB durable-finalization publication smoke: OK")


if __name__ == "__main__":
    main()
