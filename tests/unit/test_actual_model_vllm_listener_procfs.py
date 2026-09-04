from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_launch_preflight as launch_preflight
from relaylm.actual_model_vllm_launch_preflight import (
    RuntimeListenerEndpoint,
    RuntimeListenerObservation,
    RuntimeOwnershipError,
    snapshot_runtime_listeners,
)


_TCP_HEADER = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
)


def _expected_v4(port: int = 8000) -> RuntimeListenerEndpoint:
    return RuntimeListenerEndpoint(host="127.0.0.1", port=port)


def _proc_row(local_hex: str, port: int, *, inode: int, state: str = "0A") -> str:
    return (
        f"0: {local_hex}:{port:04X} 00000000:0000 {state} "
        f"00000000:00000000 00:00000000 00000000 1000 0 {inode} 1\n"
    )


def _write_tables(
    root: Path,
    *,
    tcp_rows: tuple[str, ...] = (),
    tcp6_rows: tuple[str, ...] = (),
) -> None:
    net = root / "net"
    net.mkdir(parents=True, exist_ok=True)
    (net / "tcp").write_text(_TCP_HEADER + "".join(tcp_rows), encoding="utf-8")
    (net / "tcp6").write_text(_TCP_HEADER + "".join(tcp6_rows), encoding="utf-8")


def _write_socket_fd(root: Path, *, pid: int, inode: int, fd: str = "3") -> None:
    fd_root = root / str(pid) / "fd"
    fd_root.mkdir(parents=True, exist_ok=True)
    (fd_root / fd).symlink_to(f"socket:[{inode}]")


def _netlink_failure(*args, **kwargs):
    del kwargs
    return subprocess.CompletedProcess(
        args=args[0],
        returncode=0,
        stdout="",
        stderr="Cannot open netlink socket: Operation not permitted\n",
    )


def _ss_success_with_pid(pid: int = 42):
    def run(*args, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=(
                'LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:* '
                f'users:(("python",pid={pid},fd=3))\n'
            ),
            stderr="",
        )

    return run


def _ss_success_without_pid(*args, **kwargs):
    del kwargs
    return subprocess.CompletedProcess(
        args=args[0],
        returncode=0,
        stdout="LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:*\n",
        stderr="",
    )


def test_netlink_error_empty_stdout_is_not_authoritative_absence(tmp_path: Path) -> None:
    with pytest.raises(RuntimeOwnershipError, match="PROCFS_TABLE_UNAVAILABLE"):
        snapshot_runtime_listeners(
            expected_endpoint=_expected_v4(),
            run=_netlink_failure,
            proc_root=tmp_path,
        )


def test_netlink_transport_failure_falls_back_to_procfs_absence(tmp_path: Path) -> None:
    _write_tables(tmp_path)

    assert snapshot_runtime_listeners(
        expected_endpoint=_expected_v4(),
        run=_netlink_failure,
        proc_root=tmp_path,
    ) == ()


def test_procfs_ipv4_listener_maps_inode_to_owner_pid(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )
    _write_socket_fd(tmp_path, pid=4242, inode=12345)

    assert launch_preflight._snapshot_runtime_listeners_procfs(
        expected_endpoint=_expected_v4(),
        proc_root=tmp_path,
    ) == (
        RuntimeListenerObservation(endpoint=_expected_v4(), pids=(4242,)),
    )


def test_procfs_unrelated_listener_does_not_satisfy_expected_endpoint(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 9000, inode=12345),),
    )
    _write_socket_fd(tmp_path, pid=4242, inode=12345)

    assert launch_preflight._snapshot_runtime_listeners_procfs(
        expected_endpoint=_expected_v4(),
        proc_root=tmp_path,
    ) == ()


def test_procfs_foreign_owner_is_preserved_as_observed_pid(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )
    _write_socket_fd(tmp_path, pid=7777, inode=12345)

    observation = launch_preflight._snapshot_runtime_listeners_procfs(
        expected_endpoint=_expected_v4(),
        proc_root=tmp_path,
    )

    assert observation == (
        RuntimeListenerObservation(endpoint=_expected_v4(), pids=(7777,)),
    )


def test_procfs_ambiguous_expected_socket_rows_fail_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(
            _proc_row("0100007F", 8000, inode=12345),
            _proc_row("0100007F", 8000, inode=12346),
        ),
    )

    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_inode_zero_fails_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=0),),
    )

    with pytest.raises(RuntimeOwnershipError, match="PROCFS_SOCKET_INODE_UNAVAILABLE"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_malformed_table_row_fails_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=("0: 0100007F:1F40 malformed\n",),
    )

    with pytest.raises(RuntimeOwnershipError, match="PROCFS_TABLE_ROW_MALFORMED"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_requires_both_tcp_tables_for_absence(tmp_path: Path) -> None:
    net = tmp_path / "net"
    net.mkdir(parents=True)
    (net / "tcp").write_text(_TCP_HEADER, encoding="utf-8")

    with pytest.raises(RuntimeOwnershipError, match="PROCFS_TABLE_UNAVAILABLE"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_unreadable_fd_directory_fails_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )
    pid_root = tmp_path / "4242"
    pid_root.mkdir()
    (pid_root / "fd").write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(RuntimeOwnershipError, match="PROCFS_FD_DIRECTORY_UNAVAILABLE"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_unreadable_fd_symlink_fails_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )
    fd_root = tmp_path / "4242" / "fd"
    fd_root.mkdir(parents=True)
    (fd_root / "3").mkdir()

    with pytest.raises(RuntimeOwnershipError, match="PROCFS_FD_SYMLINK_UNAVAILABLE"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_present_socket_without_provable_pid_fails_closed(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )

    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        launch_preflight._snapshot_runtime_listeners_procfs(
            expected_endpoint=_expected_v4(),
            proc_root=tmp_path,
        )


def test_procfs_ipv6_loopback_decodes_exactly(tmp_path: Path) -> None:
    expected = RuntimeListenerEndpoint(host="::1", port=8000)
    _write_tables(
        tmp_path,
        tcp6_rows=(
            _proc_row(
                "00000000000000000000000001000000",
                8000,
                inode=54321,
            ),
        ),
    )
    _write_socket_fd(tmp_path, pid=4343, inode=54321)

    assert launch_preflight._snapshot_runtime_listeners_procfs(
        expected_endpoint=expected,
        proc_root=tmp_path,
    ) == (RuntimeListenerObservation(endpoint=expected, pids=(4343,)),)


def test_successful_ss_path_does_not_require_procfs(tmp_path: Path) -> None:
    missing_proc_root = tmp_path / "missing"

    assert snapshot_runtime_listeners(
        expected_endpoint=_expected_v4(),
        run=_ss_success_with_pid(),
        proc_root=missing_proc_root,
    ) == (RuntimeListenerObservation(endpoint=_expected_v4(), pids=(42,)),)


def test_pidless_expected_ss_listener_is_not_rescued_by_procfs(tmp_path: Path) -> None:
    _write_tables(
        tmp_path,
        tcp_rows=(_proc_row("0100007F", 8000, inode=12345),),
    )
    _write_socket_fd(tmp_path, pid=4242, inode=12345)

    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        snapshot_runtime_listeners(
            expected_endpoint=_expected_v4(),
            run=_ss_success_without_pid,
            proc_root=tmp_path,
        )
