#!/usr/bin/env python3
"""I1-GE I1-GC/C1-5/B2/completion process-exit validation."""
from __future__ import annotations

from pathlib import Path

import _relaylm_i1ge_crash_validation as validation


REPLAY_CHILD = Path(__file__).with_name("_relaylm_i1ge_replay_crash_child.py")


if __name__ == "__main__":
    validation.CHILD = REPLAY_CHILD
    validation.run_replay_matrix()
    print("RelayLM I1-GE replay crash smoke passed")
