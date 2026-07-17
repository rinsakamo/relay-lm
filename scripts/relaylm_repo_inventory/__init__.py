"""Non-destructive repository and storage inventory tooling for RelayLM.

This package produces deterministic, evidence-backed inventories of storage
artifacts, invocation roots, and configuration/dependency surfaces. It makes
no removal, migration, or dead-code determination of any kind: every storage
record defaults to an "unclassified" state, and every inferred field is
explicitly labeled as heuristic so a human reviewer can weigh it accordingly.
"""
from __future__ import annotations

TOOL_VERSION = "1.3.0"
