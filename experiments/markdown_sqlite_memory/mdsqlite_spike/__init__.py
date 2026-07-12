"""Markdown-authority / SQLite-projection memory spike.

EXPERIMENT ONLY. This package is an isolated architecture spike and is not
wired into the relay-lm production runtime. It must never be imported from
``relaylm`` modules. See experiments/markdown_sqlite_memory/README.md.
"""

__all__ = ["SPIKE_NAME"]

SPIKE_NAME = "markdown_sqlite_memory"
