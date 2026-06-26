#!/usr/bin/env python3
"""O1B filesystem hardening, canonical grammar, and leakage smoke."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gc_durable_finalization_replay_smoke as gc  # noqa: E402
from relaylm.relaymem_slp_scheduler_contract import SchedulerGates  # noqa: E402
from relaylm.relaymem_slp_scheduler_replay_lane import (  # noqa: E402
    build_relaymem_slp_scheduler_replay_lane_node_result,
    run_relaymem_slp_scheduler_replay_lane_once,
)

LEAK_CANARY = "O1B_SECURITY_RAW_EXCEPTION_CANARY"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def gates() -> SchedulerGates:
    return SchedulerGates(
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
        replay_lane_enabled=True,
        queue_lane_enabled=True,
    )


def run(config, *, limit=None, fault=None):
    return run_relaymem_slp_scheduler_replay_lane_once(
        config=config,
        gates=gates(),
        discovery_max_entries=limit,
        fault_injector=fault,
    )


def sealed_fixture(root: Path):
    config = gc._config(root, dry_run=True)
    base, _, _, _ = gc._publish_sealed(root)
    locator = str(base["locator_digest"])
    return config, locator


def assert_unsafe(result) -> None:
    require(result.status == "unsafe_state", result)
    require(result.unsafe, result)
    require(not result.delegation_attempted, result)


def assert_no_leak(result, locator: str | None = None) -> None:
    node = build_relaymem_slp_scheduler_replay_lane_node_result(result)
    text = repr(result) + repr(node) + json.dumps(node.to_log_dict(), default=str, sort_keys=True)
    forbidden = [
        gc.gb.USER_CANARY,
        gc.gb.ASSISTANT_CANARY,
        gc.gb.NAMESPACE_CANARY,
        gc.gb.RUN_ID,
        gc.gb.SESSION_ID,
        gc.gb.REQUEST_ID,
        LEAK_CANARY,
        "slp-job-v0:",
        "slp-dispatch-v0:",
        "/finalization",
        ".base.json",
        ".seal.json",
    ]
    if locator:
        forbidden.append(locator)
    for token in forbidden:
        require(token not in text, (token, text))


def test_root_and_object_types() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "real"
        config, _ = sealed_fixture(target)
        link = root / "link"
        link.symlink_to(target / "finalization", target_is_directory=True)
        unsafe_config = config.model_copy(update={
            "relaymem_slp_durable_finalization_root": str(link.resolve(strict=False))
        })
        # resolve(strict=False) follows the final symlink, so use the literal absolute link.
        unsafe_config = unsafe_config.model_copy(update={
            "relaymem_slp_durable_finalization_root": str(link.absolute())
        })
        assert_unsafe(run(unsafe_config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        seal = finalization / f"durable-finalization-v0-{locator}.seal.json"
        original = seal.read_bytes()
        seal.unlink()
        target = finalization / "outside-seal"
        target.write_bytes(original)
        seal.symlink_to(target)
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        seal = finalization / f"durable-finalization-v0-{locator}.seal.json"
        copy = root / "hardlink-source"
        copy.write_bytes(seal.read_bytes())
        seal.unlink()
        os.link(copy, seal)
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, _, _ = gc.gb._records()
        locator = str(base["locator_digest"])
        path = root / "finalization" / f"durable-finalization-v0-{locator}.base.json"
        os.mkfifo(path)
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        sock_path = root / "finalization" / "unexpected.sock"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(sock_path))
            assert_unsafe(run(config))
        finally:
            sock.close()

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        (root / "finalization" / "nested").mkdir()
        assert_unsafe(run(config))


def mutate_base(root: Path, data: bytes):
    config, locator = sealed_fixture(root)
    path = root / "finalization" / f"durable-finalization-v0-{locator}.base.json"
    path.write_bytes(data)
    return config, locator


def test_encoding_json_and_size() -> None:
    cases = (
        b"\xff\xfe",
        b"{",
        b'{"a":1,"a":2}',
        b'{ "a": 1 }',
        b'{"a":NaN}',
    )
    for data in cases:
        with TemporaryDirectory() as directory:
            config, locator = mutate_base(Path(directory), data)
            result = run(config)
            assert_unsafe(result)
            assert_no_leak(result, locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        path = root / "finalization" / f"durable-finalization-v0-{locator}.base.json"
        path.write_bytes(b"x" * (config.relaymem_slp_durable_finalization_max_record_bytes + 1))
        assert_unsafe(run(config))


def test_grammar_chain_and_unknown_entries() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        base = finalization / f"durable-finalization-v0-{locator}.base.json"
        base.rename(finalization / f"durable-finalization-v0-{locator.upper()}.base.json")
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        segment0 = finalization / f"durable-finalization-v0-{locator}.segment-000000.json"
        if segment0.exists():
            segment0.rename(finalization / f"durable-finalization-v0-{locator}.segment-000001.json")
        else:
            # The non-stream fixture may have no segments; create a canonical-looking gap.
            (finalization / f"durable-finalization-v0-{locator}.segment-000001.json").write_text("{}", encoding="utf-8")
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        base = finalization / f"durable-finalization-v0-{locator}.base.json"
        base.unlink()
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, segments, seal = gc.gb._records()
        locator = str(base["locator_digest"])
        store = gc.gb._store(root / "finalization")
        require(store.publish_base(base).status == "published_new", base)
        for segment in segments:
            require(store.publish_segment(segment).status == "published_new", segment)
        require(store.publish_seal(seal).status == "published_new", seal)
        (root / "finalization" / f"durable-finalization-v1-{locator}.base.json").write_text("{}", encoding="utf-8")
        assert_unsafe(run(config))

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        (root / "finalization" / f"durable-finalization-v0-{locator}.seal.json.extra").write_text("x", encoding="utf-8")
        assert_unsafe(run(config))


def test_inode_change_and_fault_leakage() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        changed = False

        def replace(stage: str) -> None:
            nonlocal changed
            if stage == "after_selection_before_reread" and not changed:
                changed = True
                path = finalization / f"durable-finalization-v0-{locator}.base.json"
                data = path.read_bytes()
                replacement = finalization / ".replacement"
                replacement.write_bytes(data)
                os.replace(replacement, path)

        result = run(config, fault=replace)
        require(result.status == "candidate_changed", result)
        require(not result.delegation_attempted, result)
        assert_no_leak(result, locator)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)

        def fail(stage: str) -> None:
            if stage == "during_inventory":
                raise RuntimeError(LEAK_CANARY)

        result = run(config, fault=fail)
        require(result.status == "failed", result)
        assert_no_leak(result, locator)


def test_known_controls_and_cap_counting() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        (finalization / f".durable-finalization-replay-v0-{locator}.lock").write_bytes(b"")
        known = run(config)
        require(known.status == "delegated", known)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config, locator = sealed_fixture(root)
        finalization = root / "finalization"
        for index in range(8):
            (finalization / f".durable-finalization-{index:032x}.tmp").write_bytes(b"")
        capped = run(config, limit=4)
        assert_unsafe(capped)


def main() -> None:
    test_root_and_object_types()
    test_encoding_json_and_size()
    test_grammar_chain_and_unknown_entries()
    test_inode_change_and_fault_leakage()
    test_known_controls_and_cap_counting()
    print("RelayLM O1B sealed replay-lane security smoke passed.")


if __name__ == "__main__":
    main()
