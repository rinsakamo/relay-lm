"""RelayLM OpenAI-compatible Memory Context Proxy."""

from . import audit_projection as _audit_projection
from .audit_projection_contracts import install_audit_projection_contracts as _install_audit_projection_contracts

_install_audit_projection_contracts(_audit_projection)

del _audit_projection
del _install_audit_projection_contracts

__version__ = "0.1.0"
