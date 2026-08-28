from __future__ import annotations

from importlib.metadata import version as distribution_version
from pathlib import Path

from relaylm import __version__
from relaylm.cli import RELAYLM_VERSION
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory


class _UnusedProvider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("release version test must not generate")


def test_installed_distribution_and_runtime_share_version_authority() -> None:
    assert distribution_version("relaylm") == __version__
    assert RELAYLM_VERSION == __version__


def test_fastapi_metadata_uses_package_version(tmp_path: Path) -> None:
    profile = CognitiveProfileRuntime(
        name="relaylm",
        package=CognitivePackageDirectory(tmp_path),
        provider=_UnusedProvider(),
        physical_model="version-test-model",
    )
    app = create_app(profiles=CognitiveProfileRegistry((profile,)))

    assert app.version == __version__
