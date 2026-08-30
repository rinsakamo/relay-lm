from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
import shutil


@dataclass(frozen=True, slots=True)
class StarterPackage:
    """One first-party Starter Cognitive Package shipped with RelayLM."""

    name: str
    family: str
    summary: str


_STARTERS = (
    StarterPackage(
        name="blank",
        family="characters",
        summary="Minimal neutral starting point for user authoring.",
    ),
    StarterPackage(
        name="relm",
        family="characters",
        summary="Complete first-party Character example.",
    ),
    StarterPackage(
        name="fact-summarizer",
        family="machines",
        summary="Non-personal general fact summarization role.",
    ),
    StarterPackage(
        name="relaylm-faq",
        family="machines",
        summary="Source-bounded RelayLM onboarding and reference role.",
    ),
)
_STARTERS_BY_NAME = {starter.name: starter for starter in _STARTERS}


def list_starter_packages() -> tuple[StarterPackage, ...]:
    """Return the stable first-party Starter catalog."""

    return _STARTERS


def get_starter_package(name: str) -> StarterPackage:
    """Resolve one first-party Starter by its public catalog name."""

    try:
        return _STARTERS_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"unknown starter package: {name!r}") from exc


def materialize_starter_package(name: str, destination: str | Path) -> Path:
    """Copy one bundled Starter to a new ordinary filesystem root."""

    starter = get_starter_package(name)
    destination_path = Path(destination)
    if destination_path.exists():
        raise FileExistsError(destination_path)

    source = files(__package__).joinpath(starter.family, starter.name)
    destination_path.mkdir(parents=True)
    try:
        for child in source.iterdir():
            _copy_resource(child, destination_path / child.name)
    except Exception:
        shutil.rmtree(destination_path, ignore_errors=True)
        raise
    return destination_path


def _copy_resource(source: Traversable, destination: Path) -> None:
    if source.is_dir():
        destination.mkdir()
        for child in source.iterdir():
            _copy_resource(child, destination / child.name)
        return

    with source.open("rb") as source_handle, destination.open("wb") as destination_handle:
        shutil.copyfileobj(source_handle, destination_handle)
