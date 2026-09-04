from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path


class ProcfsListenerSnapshotError(RuntimeError):
    """The procfs listener namespace cannot prove the requested endpoint safely."""

    def __init__(self, message: str, *, code: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class ProcfsListenerObservation:
    host: str
    port: int
    pids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _ProcfsSocketRow:
    host: str
    port: int
    inode: int


_SOCKET_TARGET = re.compile(r"^socket:\[(\d+)\]$")


def snapshot_procfs_listener(
    *,
    expected_host: str,
    expected_port: int,
    proc_root: str | Path = "/proc",
) -> tuple[ProcfsListenerObservation, ...]:
    """Prove one endpoint through procfs TCP tables and socket-inode ownership."""

    if not isinstance(expected_host, str) or not expected_host.strip():
        raise TypeError("expected_host must be non-empty")
    if isinstance(expected_port, bool) or not isinstance(expected_port, int):
        raise TypeError("expected_port must be an integer")
    if expected_port < 1 or expected_port > 65535:
        raise ValueError("expected_port must be in 1..65535")

    root = Path(proc_root)
    rows: list[_ProcfsSocketRow] = []
    for table_name, family in (("tcp", socket.AF_INET), ("tcp6", socket.AF_INET6)):
        table = root / "net" / table_name
        try:
            text = table.read_text(encoding="ascii")
        except (OSError, UnicodeError) as exc:
            raise ProcfsListenerSnapshotError(
                f"cannot read {table_name} listener table",
                code="PROCFS_TABLE_UNAVAILABLE",
            ) from exc
        rows.extend(
            _parse_procfs_tcp_table(
                text,
                family=family,
                expected_host=expected_host,
                expected_port=expected_port,
            )
        )

    matching = tuple(
        row
        for row in rows
        if row.port == expected_port and _listener_hosts_match(expected_host, row.host)
    )
    if not matching:
        return ()
    if len(matching) != 1:
        raise ProcfsListenerSnapshotError(
            "expected endpoint has an ambiguous procfs LISTEN socket set",
            code="PROCESS_OWNERSHIP_UNPROVEN",
        )
    row = matching[0]
    if row.inode <= 0:
        raise ProcfsListenerSnapshotError(
            "expected listener has no positive socket inode",
            code="PROCFS_SOCKET_INODE_UNAVAILABLE",
        )

    pids = _map_socket_inode_to_pids(root, row.inode)
    if not pids:
        raise ProcfsListenerSnapshotError(
            "expected listener socket inode has no provable owning PID",
            code="PROCESS_OWNERSHIP_UNPROVEN",
        )
    return (
        ProcfsListenerObservation(
            host=expected_host,
            port=expected_port,
            pids=pids,
        ),
    )


def _parse_procfs_tcp_table(
    text: str,
    *,
    family: int,
    expected_host: str,
    expected_port: int,
) -> tuple[_ProcfsSocketRow, ...]:
    if not isinstance(text, str):
        raise TypeError("procfs table text must be a string")
    lines = text.splitlines()
    if not lines:
        raise ProcfsListenerSnapshotError(
            "procfs listener table is empty",
            code="PROCFS_TABLE_UNAVAILABLE",
        )

    rows: list[_ProcfsSocketRow] = []
    for line_number, raw_line in enumerate(lines[1:], start=2):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) < 2:
            raise ProcfsListenerSnapshotError(
                f"procfs listener row {line_number} has no local endpoint",
                code="PROCFS_TABLE_ROW_MALFORMED",
            )

        local_value = fields[1]
        if ":" not in local_value:
            raise ProcfsListenerSnapshotError(
                f"procfs listener row {line_number} has malformed local endpoint",
                code="PROCFS_TABLE_ROW_MALFORMED",
            )
        _, port_hex = local_value.rsplit(":", 1)
        try:
            port = int(port_hex, 16)
        except ValueError as exc:
            raise ProcfsListenerSnapshotError(
                f"procfs listener row {line_number} has malformed local port",
                code="PROCFS_TABLE_ROW_MALFORMED",
            ) from exc
        if port != expected_port:
            continue
        if len(fields) < 4:
            raise ProcfsListenerSnapshotError(
                f"relevant procfs listener row {line_number} is incomplete",
                code="PROCFS_TABLE_ROW_MALFORMED",
            )
        if fields[3].upper() != "0A":
            continue

        local = _decode_local_endpoint(
            local_value,
            family=family,
            line_number=line_number,
        )
        if local is None:
            continue
        host, port = local
        if not _listener_hosts_match(expected_host, host):
            continue
        if len(fields) < 10:
            raise ProcfsListenerSnapshotError(
                f"relevant procfs listener row {line_number} is incomplete",
                code="PROCFS_TABLE_ROW_MALFORMED",
            )
        try:
            inode = int(fields[9], 10)
        except ValueError as exc:
            raise ProcfsListenerSnapshotError(
                f"relevant procfs listener row {line_number} has invalid inode",
                code="PROCFS_TABLE_ROW_MALFORMED",
            ) from exc
        if inode <= 0:
            raise ProcfsListenerSnapshotError(
                "expected listener has no positive socket inode",
                code="PROCFS_SOCKET_INODE_UNAVAILABLE",
            )
        rows.append(_ProcfsSocketRow(host=host, port=port, inode=inode))
    return tuple(rows)


def _decode_local_endpoint(
    value: str,
    *,
    family: int,
    line_number: int,
) -> tuple[str, int] | None:
    if ":" not in value:
        raise ProcfsListenerSnapshotError(
            f"procfs listener row {line_number} has malformed local endpoint",
            code="PROCFS_TABLE_ROW_MALFORMED",
        )
    address_hex, port_hex = value.rsplit(":", 1)
    try:
        port = int(port_hex, 16)
        raw = bytes.fromhex(address_hex)
    except ValueError as exc:
        raise ProcfsListenerSnapshotError(
            f"procfs listener row {line_number} has malformed local endpoint",
            code="PROCFS_TABLE_ROW_MALFORMED",
        ) from exc
    try:
        if family == socket.AF_INET:
            if len(raw) != 4:
                raise ValueError("invalid IPv4 width")
            packed = raw[::-1]
        elif family == socket.AF_INET6:
            if len(raw) != 16:
                raise ValueError("invalid IPv6 width")
            packed = b"".join(raw[index : index + 4][::-1] for index in range(0, 16, 4))
        else:
            raise ValueError("unsupported address family")
        host = socket.inet_ntop(family, packed)
    except (OSError, ValueError) as exc:
        raise ProcfsListenerSnapshotError(
            f"procfs listener row {line_number} has undecodable local address",
            code="PROCFS_TABLE_ROW_MALFORMED",
        ) from exc
    if port < 1 or port > 65535:
        return None
    return host, port


def _map_socket_inode_to_pids(root: Path, inode: int) -> tuple[int, ...]:
    try:
        entries = tuple(root.iterdir())
    except OSError as exc:
        raise ProcfsListenerSnapshotError(
            "cannot inspect procfs process namespace",
            code="PROCFS_FD_DIRECTORY_UNAVAILABLE",
        ) from exc

    target = f"socket:[{inode}]"
    pids: list[int] = []
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        fd_root = entry / "fd"
        try:
            fds = tuple(fd_root.iterdir())
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ProcfsListenerSnapshotError(
                "cannot inspect required procfs fd directory",
                code="PROCFS_FD_DIRECTORY_UNAVAILABLE",
            ) from exc
        for fd in fds:
            try:
                observed = os.readlink(fd)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ProcfsListenerSnapshotError(
                    "cannot inspect required procfs fd symlink",
                    code="PROCFS_FD_SYMLINK_UNAVAILABLE",
                ) from exc
            match = _SOCKET_TARGET.fullmatch(observed)
            if match is None:
                continue
            try:
                observed_inode = int(match.group(1), 10)
            except ValueError:
                continue
            if observed_inode == inode and observed == target:
                pids.append(int(entry.name, 10))
    return tuple(sorted(set(pids)))


def _listener_hosts_match(expected_host: str, observed_host: str) -> bool:
    expected = expected_host.strip().lower()
    observed = observed_host.strip().lower()
    if expected == observed:
        return True
    if observed in {"*", "0.0.0.0", "::", "[::]"}:
        return True
    if expected == "localhost" and observed in {"127.0.0.1", "::1", "[::1]"}:
        return True
    return False
