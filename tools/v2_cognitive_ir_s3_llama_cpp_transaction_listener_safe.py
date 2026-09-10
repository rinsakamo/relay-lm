from __future__ import annotations

from collections.abc import Sequence
import errno
import socket

import tools.v2_cognitive_ir_s3_llama_cpp_transaction as transaction


LISTENER_PROBE_TIMEOUT_SECONDS = 1.0


def _port_has_no_listener(host: str, port: int) -> bool:
    """Return true only when loopback actively refuses a TCP connection.

    The frozen S3 transaction historically used a fresh ``bind()`` as a proxy
    for listener absence. After a request-heavy shard, recently closed TCP
    connection state can make that bind fail even though the llama-server
    process and LISTEN socket are already gone. A connect probe asks the exact
    lifecycle question instead: is anything still accepting on this endpoint?

    For the fixed loopback S3 endpoint, ECONNREFUSED is the only accepted
    evidence of listener absence. Every other socket outcome fails closed.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(LISTENER_PROBE_TIMEOUT_SECONDS)
        result = probe.connect_ex((host, port))
    if result == 0:
        return False
    if result == errno.ECONNREFUSED:
        return True
    raise transaction.S3TransactionError(
        f"cannot establish S3 listener absence for {host}:{port}: "
        f"connect_ex={result} ({errno.errorcode.get(result, 'UNKNOWN')})"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen transaction with listener-specific lifecycle checks.

    This is a mechanical compatibility envelope only. It changes no S3 calls,
    prompts, seeds, scoring, retry policy, material attestation, or evidence
    semantics. The child process is dedicated to one transaction invocation,
    so replacing the historical bind-based predicate is process-local.
    """

    transaction._port_is_free = _port_has_no_listener
    return transaction.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
