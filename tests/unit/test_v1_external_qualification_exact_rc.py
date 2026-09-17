from __future__ import annotations

from pathlib import Path

import pytest

from tools.v1_external_qualification_exact_rc import ExactRCError, install_exact_rc


def test_replaced_wheel_at_frozen_path_is_rejected_before_runtime_creation(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl"
    wheel.write_bytes(b"replacement-bytes")
    runtime_root = tmp_path / "exact-rc-runtime"

    with pytest.raises(ExactRCError, match="SHA256 drifted"):
        install_exact_rc(
            wheel_path=wheel,
            wheel_sha256="0" * 64,
            expected_version="1.0.0rc1",
            expected_distribution="relaylm",
            checkout_root=tmp_path / "qualification-checkout",
            runtime_root=runtime_root,
        )

    assert not runtime_root.exists()
