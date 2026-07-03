"""RelayEMO runtime helpers.

ACG-5 keeps RelayEMO responsible for affect and expression only. The
implementation lives in relayemo_acg5 while this module preserves the historical
import path used by app.py and existing smoke scripts.
"""

from __future__ import annotations

from relaylm.relayemo_acg5 import *  # noqa: F401,F403
from relaylm.relayemo_acg5 import SCENE_HINT_TYPES, infer_scene_hint_type

# Deprecated compatibility aliases. These names are non-authoritative scene
# hints only and must not be consumed by RelaySCN or RelayMEM as scene policy.
SCENE_TYPES = SCENE_HINT_TYPES
infer_scene_type = infer_scene_hint_type
