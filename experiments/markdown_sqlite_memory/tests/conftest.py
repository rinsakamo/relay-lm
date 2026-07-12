import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mdsqlite_spike import cache, fixtures  # noqa: E402
from mdsqlite_spike.slp import SpikeEnv  # noqa: E402


class FakeClock:
    """Deterministic ISO timestamps for reproducible fixtures."""

    def __init__(self) -> None:
        self.tick = 0

    def __call__(self) -> str:
        self.tick += 1
        return f"2026-07-12T00:00:{self.tick % 60:02d}+00:00#{self.tick}"


@pytest.fixture
def env(tmp_path) -> SpikeEnv:
    spike_env = SpikeEnv(tmp_path / "spike", clock=FakeClock())
    spike_env.pages_dir.mkdir(parents=True)
    return spike_env


@pytest.fixture
def seeded_env(env) -> SpikeEnv:
    fixtures.init_fixture(env, pages=3, blocks_per_page=4, seed=7)
    conn = env.open_cache()
    cache.build_from_markdown(conn, env.pages_dir)
    conn.close()
    return env
