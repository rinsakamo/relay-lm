#!/usr/bin/env python3
"""I1-GE I1-GD isolation/cleanup process-exit validation."""
from __future__ import annotations

from _relaylm_i1ge_crash_validation import run_retention_matrix


if __name__ == "__main__":
    run_retention_matrix()
    print("RelayLM I1-GE retention crash smoke passed")
