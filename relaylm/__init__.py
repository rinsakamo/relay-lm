"""RelayLM OpenAI-compatible Memory Context Proxy."""

from . import audit_projection as _audit_projection
from .audit_projection_contracts import (
    install_audit_projection_contracts as _install_audit_projection_contracts,
)
from .relaymem_retrieval_priority_runtime import (
    install_relaymem_retrieval_priority_runtime as _install_relaymem_retrieval_priority_runtime,
)

_install_audit_projection_contracts(_audit_projection)
_audit_projection.TOP_LEVEL_PROJECTORS[
    "projection_dropped_field_count"
] = _audit_projection._non_negative_int
_audit_projection.TOP_LEVEL_PROJECTORS[
    "projection_unsupported_artifact_count"
] = _audit_projection._non_negative_int
_install_relaymem_retrieval_priority_runtime()

del _audit_projection
del _install_audit_projection_contracts
del _install_relaymem_retrieval_priority_runtime

__version__ = "0.1.0"
