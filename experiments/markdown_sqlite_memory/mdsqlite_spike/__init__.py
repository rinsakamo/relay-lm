"""Markdown-authority / SQLite-projection memory spike.

EXPERIMENT ONLY. This package is an isolated architecture spike and is not
wired into the relay-lm production runtime. It must never be imported from
``relaylm`` modules. See experiments/markdown_sqlite_memory/README.md.
"""

from . import slp as slp
from . import lifecycle as lifecycle
from . import search as search
from . import durable_usage as durable_usage

lifecycle.install(slp)
durable_usage.install(search)

__all__ = ["SPIKE_NAME", "slp", "search"]

SPIKE_NAME = "markdown_sqlite_memory"
