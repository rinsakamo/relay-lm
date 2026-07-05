"""Package import purity smoke.

Guards against `relaylm/__init__.py` regressing into a runtime installer:
`import relaylm` must stay metadata-only and must not mutate the audit
projection registries, patch RelayMEM store/retrieval function objects, or
otherwise diverge from direct canonical-module import.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm import audit_projection
from relaylm import relaymem_retrieval
from relaylm import relaymem_store


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    store_discover_before = relaymem_store.discover_relaymem_page_candidates
    retrieval_before = relaymem_retrieval.build_relaymem_retrieval_dry_run_artifact
    top_projectors_before = dict(audit_projection.TOP_LEVEL_PROJECTORS)
    node_projectors_before = dict(audit_projection.PIPELINE_NODE_PROJECTORS)

    import relaylm

    require(bool(relaylm.__version__), "relaylm.__version__ must be set")
    require(
        relaymem_store.discover_relaymem_page_candidates is store_discover_before,
        "package import must not replace discover_relaymem_page_candidates",
    )
    require(
        relaymem_retrieval.build_relaymem_retrieval_dry_run_artifact is retrieval_before,
        "package import must not replace build_relaymem_retrieval_dry_run_artifact",
    )
    require(
        audit_projection.TOP_LEVEL_PROJECTORS == top_projectors_before,
        "package import must not mutate TOP_LEVEL_PROJECTORS",
    )
    require(
        audit_projection.PIPELINE_NODE_PROJECTORS == node_projectors_before,
        "package import must not mutate PIPELINE_NODE_PROJECTORS",
    )
    print("ok import relaylm is metadata-only")

    for legacy_alias in (
        "install_audit_projection_contracts",
        "install_relaymem_primary_recall_runtime",
        "install_relaymem_retrieval_priority_runtime",
        "install_relaymem_primary_recall_candidate_bridge_runtime",
    ):
        require(
            legacy_alias not in relaylm.__dict__,
            f"relaylm.__dict__ must not re-export {legacy_alias}",
        )
    print("ok relaylm namespace has no legacy installer aliases")

    from relaylm.audit_projection_contracts import install_audit_projection_contracts
    from relaylm.relaymem_primary_recall_runtime import (
        install_relaymem_primary_recall_runtime,
    )
    from relaylm.relaymem_retrieval_priority_runtime import (
        install_relaymem_retrieval_priority_runtime,
    )
    from relaylm.relaymem_primary_recall_candidate_bridge_runtime import (
        install_relaymem_primary_recall_candidate_bridge_runtime,
    )

    install_audit_projection_contracts(audit_projection)
    install_relaymem_primary_recall_runtime()
    install_relaymem_retrieval_priority_runtime()
    install_relaymem_primary_recall_candidate_bridge_runtime()

    require(
        relaymem_store.discover_relaymem_page_candidates is store_discover_before,
        "no-op installer must not replace discover_relaymem_page_candidates",
    )
    require(
        relaymem_retrieval.build_relaymem_retrieval_dry_run_artifact is retrieval_before,
        "no-op installer must not replace build_relaymem_retrieval_dry_run_artifact",
    )
    require(
        audit_projection.TOP_LEVEL_PROJECTORS == top_projectors_before,
        "no-op installer must not mutate TOP_LEVEL_PROJECTORS",
    )
    require(
        audit_projection.PIPELINE_NODE_PROJECTORS == node_projectors_before,
        "no-op installer must not mutate PIPELINE_NODE_PROJECTORS",
    )
    print("ok explicit no-op installers leave canonical state unchanged")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
