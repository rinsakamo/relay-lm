#!/usr/bin/env python3
"""I1-GE I1-GC/C1-5/B2/completion process-exit validation."""
from __future__ import annotations

from _relaylm_i1ge_crash_validation import run_replay_matrix


if __name__ == "__main__":
    run_replay_matrix()
    print("RelayLM I1-GE replay crash smoke passed")
