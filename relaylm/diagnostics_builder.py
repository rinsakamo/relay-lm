"""Diagnostics builder helpers for RelayLM pipeline separation."""

from __future__ import annotations

from typing import Any

from relaylm.diagnostics import RequestDiagnostics


def build_base_request_diagnostics(**kwargs: Any) -> RequestDiagnostics:
    """Build the base request diagnostics artifact.

    This helper is intentionally thin for the first diagnostics-builder split.
    Keeping the argument shape identical to RequestDiagnostics lets app.py move
    diagnostics construction behind a stable module boundary without changing
    runtime behavior.
    """

    return RequestDiagnostics(**kwargs)
