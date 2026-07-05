"""Compatibility shim for the former audit projection contracts installer.

The field contracts this module used to install onto the ``audit_projection``
registry at import time now live directly in the canonical registry
definitions in ``relaylm.audit_projection``. This module is kept only so
existing imports and calls keep working; it performs no registry mutation.
"""

from __future__ import annotations

from typing import Any

__all__ = ["install_audit_projection_contracts"]


def install_audit_projection_contracts(ap: Any | None = None) -> None:
    """Compatibility no-op.

    Audit projection contracts are now part of the canonical registry in
    ``relaylm.audit_projection``.
    """

    return None
