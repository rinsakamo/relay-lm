"""Fixed identity probe for the isolated accepted RelayLM RC runtime."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout-root", required=True)
    args = parser.parse_args()
    spec = importlib.util.find_spec("relaylm")
    if spec is None or spec.origin is None:
        raise SystemExit("relaylm import origin is unavailable")
    origin = Path(spec.origin).resolve()
    checkout = Path(args.checkout_root).resolve()
    if origin == checkout or checkout in origin.parents:
        raise SystemExit("relaylm import resolved to the qualification checkout")
    print(
        json.dumps(
            {
                "version": importlib.metadata.version("relaylm"),
                "origin": str(origin),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
