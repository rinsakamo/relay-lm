"""RelayLM OpenAI-compatible Memory Context Proxy."""

from . import audit_projection as _audit_projection
from .audit_projection_contracts import (
    install_audit_projection_contracts as _install_audit_projection_contracts,
)
from .relaymem_primary_recall_runtime import (
    install_relaymem_primary_recall_runtime as _install_relaymem_primary_recall_runtime,
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
_install_relaymem_primary_recall_runtime()

for _relaylm_init_cleanup_name in (
    "_audit_projection",
    "_install_audit_projection_contracts",
    "_install_relaymem_primary_recall_runtime",
    "_install_relaymem_retrieval_priority_runtime",
):
    globals().pop(_relaylm_init_cleanup_name, None)
del _relaylm_init_cleanup_name

__version__ = "0.1.0"
