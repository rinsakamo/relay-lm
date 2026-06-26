#!/usr/bin/env python3
"""Parent-side assertions for I1-GE process-exit/fresh-restart validation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CHILD = SCRIPTS / "_relaylm_i1ge_crash_child.py"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from _relaylm_i1ge_crash_child import (  # noqa: E402
    EXIT_CODES,
    NONSTREAM_SEAMS,
    REPLAY_SEAMS,
    RETENTION_SEAMS,
    STREAM_SEAMS,
)
from relaylm.relaymem_slp_durable_finalization_isolation import (  # noqa: E402
    isolation_filename,
    parse_isolation_filename,
)
from relaylm.relaymem_slp_durable_finalization_replay import (  # noqa: E402
    completion_filename,
)
from relaylm.relaymem_slp_durable_finalization_store import (  # noqa: E402
    RelayMEMSLPDurableFinalizationStore,
)

PRIVATE_CANARIES = (
    "CANARY_I1GB_APP_USER_DO_NOT_LEAK",
    "CANARY_I1GB_APP_ASSISTANT_DO_NOT_LEAK",
    "CANARY_I1GB_APP_NAMESPACE_DO_NOT_LEAK",
    "slp-job-v0:",
    "slp-dispatch-v0:",
    "Traceback",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _env() -> dict[str, str]:
    env = dict(os.environ)
    paths = [str(ROOT), str(SCRIPTS)]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def run_child(
    action: str,
    root: Path,
    *,
    seam: str | None = None,
    result_name: str = "result",
    timeout: int = 30,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(CHILD),
        action,
        "--root",
        str(root.resolve()),
        "--result-name",
        result_name,
    ]
    if seam is not None:
        command.extend(("--seam", seam))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    require(
        completed.returncode == expected,
        {
            "command": command,
            "expected": expected,
            "actual": completed.returncode,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        },
    )
    return completed


def assert_content_free_process(completed: subprocess.CompletedProcess[str]) -> None:
    rendered = completed.stdout + "\n" + completed.stderr
    for token in PRIVATE_CANARIES:
        require(token not in rendered, (token, rendered))


def result_status(root: Path, name: str) -> str:
    value = json.loads((root / f".i1ge-{name}.json").read_text("utf-8"))
    require(set(value) == {"status"} and type(value["status"]) is str, value)
    return str(value["status"])


def locator(root: Path) -> str | None:
    finalization = root / "finalization"
    bases = sorted(finalization.glob("durable-finalization-v0-*.base.json"))
    if bases:
        require(len(bases) == 1, [path.name for path in bases])
        name = bases[0].name
        value = name[len("durable-finalization-v0-") : -len(".base.json")]
        require(
            len(value) == 64 and all(char in "0123456789abcdef" for char in value),
            value,
        )
        return value
    markers = sorted(
        finalization.glob("durable-finalization-v0-*.segment-isolation.json")
    )
    if not markers:
        return None
    require(len(markers) == 1, [path.name for path in markers])
    value = parse_isolation_filename(markers[0].name)
    require(value is not None, markers[0].name)
    return value


def _store(root: Path) -> RelayMEMSLPDurableFinalizationStore:
    return RelayMEMSLPDurableFinalizationStore(
        str((root / "finalization").resolve()),
        max_record_bytes=512 * 1024,
        max_segment_bytes=64 * 1024,
        max_segment_count=256,
        max_record_count=1024,
        operation_timeout_ms=5000,
    )


def canonical_evidence(root: Path):
    value = locator(root)
    if value is None:
        return None
    return _store(root).read_evidence(value)


def _count(root: Path, directory: str, pattern: str) -> int:
    path = root / directory
    return len(list(path.glob(pattern))) if path.exists() else 0


def downstream_counts(root: Path) -> tuple[int, int, int]:
    value = locator(root)
    completion = 0
    if value is not None:
        completion = int((root / "finalization" / completion_filename(value)).is_file())
    return (
        _count(root, "source", "protected-source-v0-*.json"),
        _count(root, "queue", "slp-dispatch-v0-*.json"),
        completion,
    )


def assert_source_before_queue(root: Path) -> None:
    source, queue, _ = downstream_counts(root)
    require(not queue or source == 1, (source, queue))
    require(source <= 1 and queue <= 1, (source, queue))


def assert_complete(root: Path) -> None:
    evidence = canonical_evidence(root)
    require(evidence is not None, "sealed_evidence_missing")
    require(evidence.status == "loaded" and evidence.replayable, evidence)
    require(downstream_counts(root) == (1, 1, 1), downstream_counts(root))
    assert_source_before_queue(root)


def production_snapshot(root: Path) -> tuple[tuple[str, int, str], ...]:
    rows: list[tuple[str, int, str]] = []
    for directory in ("finalization", "source", "queue"):
        base = root / directory
        if not base.exists():
            continue
        for path in sorted(item for item in base.iterdir() if item.is_file()):
            data = path.read_bytes()
            rows.append(
                (
                    f"{directory}/{path.name}",
                    len(data),
                    hashlib.sha256(data).hexdigest(),
                )
            )
    return tuple(rows)


def _recover_and_assert(root: Path, *, expect_complete: bool, name: str) -> None:
    run_child("recover", root, result_name=name)
    status = result_status(root, name)
    if expect_complete:
        require(status in {"completed", "no_eligible_work"}, status)
        assert_complete(root)
        before = production_snapshot(root)
        run_child("recover", root, result_name=f"{name}-duplicate")
        require(result_status(root, f"{name}-duplicate") == "no_eligible_work", status)
        require(production_snapshot(root) == before, (before, production_snapshot(root)))
    else:
        require(status == "no_eligible_work", status)
        require(downstream_counts(root) == (0, 0, 0), downstream_counts(root))


def run_publication_matrix(*, stream: bool) -> None:
    seams = STREAM_SEAMS if stream else NONSTREAM_SEAMS
    sealed = {
        "after_seal_publication_before_canonical_reread",
        "after_seal_canonical_reread_before_http_body_release",
        "after_protected_body_release_before_normal_finalizer",
        "during_normal_finalizer_before_c1_5",
        "after_seal_reread_before_terminal_sse_completion",
        "after_terminal_visible_completion_before_normal_finalizer",
    }
    action = "stream" if stream else "nonstream"
    for seam in seams:
        with TemporaryDirectory(prefix="relaylm-i1ge-publication-") as directory:
            root = Path(directory)
            crashed = run_child(
                action,
                root,
                seam=seam,
                expected=EXIT_CODES[seam],
            )
            assert_content_free_process(crashed)
            assert_source_before_queue(root)
            evidence = canonical_evidence(root)
            if seam in sealed:
                require(evidence is not None and evidence.status == "loaded", (seam, evidence))
                require(evidence.sealed and evidence.replayable, (seam, evidence))
            else:
                if evidence is not None:
                    require(evidence.status == "loaded", (seam, evidence))
                    require(not evidence.sealed and not evidence.replayable, (seam, evidence))
                require(_count(root, "finalization", "*.seal.json") == 0, seam)
            _recover_and_assert(root, expect_complete=seam in sealed, name="restart")


def run_replay_matrix() -> None:
    for seam in REPLAY_SEAMS:
        with TemporaryDirectory(prefix="relaylm-i1ge-replay-") as directory:
            root = Path(directory)
            run_child("prepare-sealed", root, result_name="prepare")
            require(result_status(root, "prepare") == "sealed", seam)
            crashed = run_child(
                "replay-crash",
                root,
                seam=seam,
                expected=EXIT_CODES[seam],
            )
            assert_content_free_process(crashed)
            assert_source_before_queue(root)
            run_child("replay-normal", root, result_name="restart")
            require(
                result_status(root, "restart") in {"completed", "already_complete", "exact_duplicate"},
                (seam, result_status(root, "restart")),
            )
            assert_complete(root)
            before = production_snapshot(root)
            run_child("replay-normal", root, result_name="duplicate")
            require(result_status(root, "duplicate") == "already_complete", seam)
            require(production_snapshot(root) == before, (seam, before, production_snapshot(root)))


def _assert_external_downstream_unchanged(
    root: Path,
    before: tuple[int, int, int],
    *,
    seam: str,
) -> None:
    current = downstream_counts(root)
    require(current[:2] == before[:2], (seam, before, current))


def run_retention_matrix() -> None:
    marker_delete_seams = {
        "during_final_isolation_marker_deletion",
        "after_marker_deletion_before_caller_return",
    }
    for seam in RETENTION_SEAMS:
        with TemporaryDirectory(prefix="relaylm-i1ge-retention-") as directory:
            root = Path(directory)
            prepare = (
                "prepare-isolated-expired"
                if seam in marker_delete_seams
                else "prepare-complete-expired"
            )
            run_child(prepare, root, result_name="prepare")
            before = downstream_counts(root)
            require(before[:2] == (1, 1), (seam, before))
            require(
                before[2] == (0 if seam in marker_delete_seams else 1),
                (seam, before),
            )
            value = locator(root)
            require(value is not None, seam)
            crashed = run_child(
                "retention-crash",
                root,
                seam=seam,
                expected=EXIT_CODES[seam],
            )
            assert_content_free_process(crashed)
            _assert_external_downstream_unchanged(root, before, seam=seam)
            run_child("retention-normal", root, result_name="restart")
            require(
                result_status(root, "restart") in {"maintenance_complete", "blocked"},
                (seam, result_status(root, "restart")),
            )
            _assert_external_downstream_unchanged(root, before, seam=seam)
            require(downstream_counts(root)[2] == 0, (seam, downstream_counts(root)))
            lock = root / "finalization" / f".durable-finalization-replay-v0-{value}.lock"
            require(lock.is_file(), (seam, [path.name for path in (root / "finalization").iterdir()]))
            marker = root / "finalization" / isolation_filename(value)
            if seam in marker_delete_seams:
                require(not marker.exists(), (seam, marker))
            else:
                require(marker.is_file(), (seam, marker))

    # A sealed-pending record remains replayable even when old and interrupted.
    with TemporaryDirectory(prefix="relaylm-i1ge-retention-sealed-") as directory:
        root = Path(directory)
        run_child("prepare-sealed", root, result_name="prepare")
        for path in (root / "finalization").iterdir():
            if path.is_file():
                old = time_value = max(1.0, path.stat().st_mtime - 7200)
                os.utime(path, (old, time_value), follow_symlinks=False)
        seam = "after_record_fence_before_root_mutation_lock"
        run_child(
            "retention-crash",
            root,
            seam=seam,
            expected=EXIT_CODES[seam],
        )
        run_child("retention-normal", root, result_name="sealed-restart")
        evidence = canonical_evidence(root)
        require(evidence is not None and evidence.replayable, evidence)
        require(downstream_counts(root) == (0, 0, 0), downstream_counts(root))


def run_existing_scripts(paths: Iterable[str], *, timeout: int = 180) -> None:
    for relative in paths:
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative)],
            cwd=ROOT,
            env=_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        require(
            completed.returncode == 0,
            (relative, completed.returncode, completed.stdout[-2000:], completed.stderr[-2000:]),
        )
