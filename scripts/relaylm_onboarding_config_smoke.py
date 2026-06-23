"""Focused onboarding smoke for Phase 6-C1-5 configuration defaults."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from relaylm.config import RelayLMConfig, load_config


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    example = Path(__file__).resolve().parents[1] / "config.example.yaml"
    raw = yaml.safe_load(example.read_text(encoding="utf-8")) or {}
    config = RelayLMConfig.model_validate(raw)
    require(config.relaymem_slp_protected_source_root is None, "protected source root must default off")
    require(
        config.relaymem_slp_protected_source_max_artifact_bytes == 256 * 1024,
        "protected source size default drift",
    )
    with TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text(
            example.read_text(encoding="utf-8"), encoding="utf-8"
        )
        loaded = load_config(config_path)
        require(loaded.relaymem_slp_protected_source_root is None, "config load root drift")
        require(
            loaded.relaymem_slp_protected_source_max_artifact_bytes == 256 * 1024,
            "config load size drift",
        )
    print("Phase 6-C1-5 onboarding config smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
