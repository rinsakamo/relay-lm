# RelayLM 2.0 — #2211 calibration-v2 LM Studio execution entrypoint

The canonical physical LM Studio route for calibration v2 is:

```python
from tools.v2_cognitive_ir_calibration_v2_lmstudio import (
    run_lmstudio_calibration_v2_transaction,
)
```

This entrypoint exists to eliminate operator-side identity assembly drift. It constructs one transaction identity from fresh repository authority, one native loaded-model binding, and the exact reasoning-off OpenAI-compatible client built from the same requested model key.

Before the lower-level host is entered, it verifies:

```text
transport.model == native_binding.model
```

The same model key is then used for every subsequent native live-binding recheck. The lower-level host still independently rechecks repository commit/tree/clean state, transport identity, the frozen 72-call plan, reasoning-off verification, and live model/runtime binding before every provider request.

The entrypoint does not load, unload, reload, swap, or download a model. The already-loaded instance is authority. It also does not change context length or reasoning configuration.

A fresh physical run should therefore call only:

```python
run_lmstudio_calibration_v2_transaction(
    base_url="<freshly verified LM Studio base URL>",
    model="<freshly verified exact model key>",
    repository_root="<fresh clean v2 checkout>",
    artifact_root="<fresh empty repo-external path>",
)
```

No request-level reasoning field is added. Effective Thinking-off remains verified independently on every completed OpenAI-compatible response by the reused reasoning-off client.

Scientific status remains:

```text
claim_status = NON_CITABLE_S2_CALIBRATION_V2
citable      = false
P0-P6        = NOT RUN
S2           = BLOCKED unless the completed calibration selects one frozen regime
S3           = BLOCKED
architecture consequence = NONE
```
