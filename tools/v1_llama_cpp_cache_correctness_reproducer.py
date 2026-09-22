"""Fresh cache-correctness reproduction target for RelayLM v1 Issue #3006.

This target intentionally reuses the already-bounded installed-product cache-on
transport, but gives the new #3006 transaction a distinct physical target
identity.  It does not change RelayLM production cache policy, prompt semantics,
or the historical #2947 target identity.
"""

from __future__ import annotations

from collections.abc import Sequence

import tools.v1_installed_llama_cpp_cache_on_experiment as experiment


REPRODUCER_TARGET_NAME = "v1:llama-cpp-cache-correctness-reproducer"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one fresh ordinary Pass1 -> Pass2 cache-on reproduction subject."""

    return experiment.run_cache_on_experiment(
        argv,
        target_name=REPRODUCER_TARGET_NAME,
    )


if __name__ == "__main__":
    raise SystemExit(main())
