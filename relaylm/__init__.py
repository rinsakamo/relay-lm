"""RelayLM OpenAI-compatible Memory Context Proxy."""

from .relaymem_primary_recall_runtime import (
    install_relaymem_primary_recall_runtime as _install_relaymem_primary_recall_runtime,
)
from .relaymem_retrieval_priority_runtime import (
    install_relaymem_retrieval_priority_runtime as _install_relaymem_retrieval_priority_runtime,
)

_install_relaymem_retrieval_priority_runtime()
_install_relaymem_primary_recall_runtime()

for _relaylm_init_cleanup_name in (
    "_install_relaymem_primary_recall_runtime",
    "_install_relaymem_retrieval_priority_runtime",
):
    globals().pop(_relaylm_init_cleanup_name, None)
del _relaylm_init_cleanup_name

__version__ = "0.1.0"
