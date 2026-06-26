#!/usr/bin/env python3
"""I1-GE real SSE process-exit/fresh-restart validation."""
from __future__ import annotations

from _relaylm_i1ge_crash_validation import run_publication_matrix


if __name__ == "__main__":
    run_publication_matrix(stream=True)
    print("RelayLM I1-GE stream crash smoke passed")
