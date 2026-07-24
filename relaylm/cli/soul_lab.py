"""Installed RelayLM launcher for the SOUL Lab management ASGI app."""
from __future__ import annotations

import argparse
import os

import uvicorn

from ..config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RelayLM with SOUL Lab management API")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        os.environ["RELAYLM_CONFIG"] = args.config

    config = load_config(args.config)
    uvicorn.run(
        "relaylm.soul_lab_app:create_app",
        factory=True,
        host=config.listen.host,
        port=config.listen.port,
    )
