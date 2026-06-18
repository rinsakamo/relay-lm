#!/usr/bin/env python3
"""Full-width space accounting regression for Phase 5-D1."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.token_budget import estimate_text_tokens_detailed, fits_token_budget


def main() -> int:
    text = chr(0x3000) * 8
    estimate = estimate_text_tokens_detailed(text)
    assert estimate.cjk_characters == 8
    assert estimate.whitespace_characters == 0
    assert estimate.cjk_tokens == 8
    assert estimate.estimated_tokens == 8
    assert not fits_token_budget(text, token_budget=7)
    assert fits_token_budget(text, token_budget=8)
    print("relaylm_fullwidth_space_token_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
