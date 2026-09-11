from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from typing import Any


PREFLIGHT_SCHEMA = "relaylm-v1-llama-cpp-controller-preflight-v1"
BLOCKED_CLASSIFICATION = "PRE_WRAPPER_RUNTIME_BLOCKED"
_REQUIRES_PYTHON_PATTERN = re.compile(r"^>=\s*(\d+)\.(\d+)$")


class LlamaCppControllerPreflightError(RuntimeError):
    """The restartable controller environment is not ready to spend a one-shot."""


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LlamaCppControllerPreflightError(
            f"command failed before wrapper consumption: {' '.join(command)}: {detail}"
        )
    return completed.stdout.strip()


def _project_python_floor(repo_root: Path) -> tuple[int, int]:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        raise LlamaCppControllerPreflightError(
            f"pyproject.toml is missing from exact checkout: {pyproject}"
        )
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    try:
        requires_python = data["project"]["requires-python"]
    except (KeyError, TypeError) as exc:
        raise LlamaCppControllerPreflightError(
            "project.requires-python is missing from pyproject.toml"
        ) from exc
    if not isinstance(requires_python, str):
        raise LlamaCppControllerPreflightError(
            "project.requires-python must be a string"
        )
    match = _REQUIRES_PYTHON_PATTERN.fullmatch(requires_python.strip())
    if match is None:
        raise LlamaCppControllerPreflightError(
            "controller preflight only accepts the current simple >=X.Y requires-python floor"
        )
    return int(match.group(1)), int(match.group(2))


def _require_python_floor(floor: tuple[int, int]) -> None:
    current = sys.version_info[:2]
    if current < floor:
        raise LlamaCppControllerPreflightError(
            f"Python {floor[0]}.{floor[1]}+ is required; current is "
            f"{current[0]}.{current[1]}"
        )


def _require_repo_external_venv(repo_root: Path) -> Path:
    prefix = Path(sys.prefix).resolve()
    base_prefix = Path(sys.base_prefix).resolve()
    if prefix == base_prefix:
        raise LlamaCppControllerPreflightError(
            "one-shot controller must use a prepared virtual environment, not the base interpreter"
        )
    if prefix == repo_root or repo_root in prefix.parents:
        raise LlamaCppControllerPreflightError(
            f"controller virtual environment must be outside the repository: {prefix}"
        )
    return prefix


def _require_exact_clean_checkout(
    *,
    repo_root: Path,
    expected_head: str,
    expected_tree: str,
) -> tuple[str, str]:
    if not (repo_root / ".git").exists():
        raise LlamaCppControllerPreflightError(
            f"repo-root is not a git checkout: {repo_root}"
        )
    status = _run_text(["git", "status", "--porcelain"], cwd=repo_root)
    if status:
        raise LlamaCppControllerPreflightError(
            "controller preflight requires a clean exact checkout"
        )
    head = _run_text(["git", "rev-parse", "HEAD"], cwd=repo_root)
    tree = _run_text(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root)
    if head != expected_head:
        raise LlamaCppControllerPreflightError(
            f"checkout HEAD mismatch: expected {expected_head}, observed {head}"
        )
    if tree != expected_tree:
        raise LlamaCppControllerPreflightError(
            f"checkout tree mismatch: expected {expected_tree}, observed {tree}"
        )
    return head, tree


def _require_installed_runtime() -> dict[str, str]:
    try:
        relaylm_version = importlib.metadata.version("relaylm")
        httpx_version = importlib.metadata.version("httpx")
    except importlib.metadata.PackageNotFoundError as exc:
        name = exc.name or "required runtime package"
        raise LlamaCppControllerPreflightError(
            f"required installed distribution is missing: {name}"
        ) from exc
    _run_text([sys.executable, "-m", "pip", "check"])
    return {
        "relaylm": relaylm_version,
        "httpx": httpx_version,
    }


def _put_exact_checkout_first(repo_root: Path) -> tuple[Path, Path]:
    src_root = (repo_root / "src").resolve()
    if not src_root.is_dir():
        raise LlamaCppControllerPreflightError(
            f"exact checkout src directory is missing: {src_root}"
        )
    for value in (str(src_root), str(repo_root)):
        while value in sys.path:
            sys.path.remove(value)
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(src_root))
    return src_root, repo_root


def import_module_without_main(
    module_name: str,
    *,
    importer: Callable[[str], Any] = importlib.import_module,
) -> Any:
    if not isinstance(module_name, str) or not module_name.strip():
        raise LlamaCppControllerPreflightError("module name must be non-empty")
    try:
        return importer(module_name)
    except Exception as exc:
        raise LlamaCppControllerPreflightError(
            f"module import failed before wrapper consumption: {module_name}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _require_exact_relaylm_source(src_root: Path) -> str:
    module = import_module_without_main("relaylm")
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        raise LlamaCppControllerPreflightError(
            "relaylm import did not expose a filesystem origin"
        )
    origin = Path(module_file).resolve()
    if origin != src_root and src_root not in origin.parents:
        raise LlamaCppControllerPreflightError(
            f"relaylm import is not bound to exact checkout src: {origin}"
        )
    return str(origin)


def _require_wrapper_module(wrapper_module: str, repo_root: Path) -> str:
    try:
        spec = importlib.util.find_spec(wrapper_module)
    except (ImportError, AttributeError, ValueError) as exc:
        raise LlamaCppControllerPreflightError(
            f"wrapper module lookup failed: {wrapper_module}: {exc}"
        ) from exc
    if spec is None or not isinstance(spec.origin, str):
        raise LlamaCppControllerPreflightError(
            f"wrapper module is unavailable: {wrapper_module}"
        )
    origin = Path(spec.origin).resolve()
    if origin != repo_root and repo_root not in origin.parents:
        raise LlamaCppControllerPreflightError(
            f"wrapper module is not from exact checkout: {origin}"
        )
    return str(origin)


def _normalized_wrapper_args(values: Sequence[str]) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise LlamaCppControllerPreflightError(
            "wrapper args must be a sequence of strings"
        )
    normalized = list(values)
    if not all(isinstance(value, str) and "\x00" not in value for value in normalized):
        raise LlamaCppControllerPreflightError(
            "wrapper args must contain strings without NUL bytes"
        )
    return normalized


def one_shot_command(
    wrapper_module: str,
    *,
    executable: str | None = None,
    wrapper_args: Sequence[str] = (),
) -> list[str]:
    selected = executable or sys.executable
    return [
        selected,
        "-m",
        wrapper_module,
        *_normalized_wrapper_args(wrapper_args),
    ]


def validate_controller_environment(
    *,
    repo_root: Path,
    expected_head: str,
    expected_tree: str,
    inner_module: str,
    wrapper_module: str,
    wrapper_args: Sequence[str] = (),
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    floor = _project_python_floor(repo_root)
    _require_python_floor(floor)
    environment_root = _require_repo_external_venv(repo_root)
    head, tree = _require_exact_clean_checkout(
        repo_root=repo_root,
        expected_head=expected_head,
        expected_tree=expected_tree,
    )
    installed = _require_installed_runtime()
    src_root, _ = _put_exact_checkout_first(repo_root)
    relaylm_origin = _require_exact_relaylm_source(src_root)
    wrapper_origin = _require_wrapper_module(wrapper_module, repo_root)
    inner = import_module_without_main(inner_module)
    if not callable(getattr(inner, "main", None)):
        raise LlamaCppControllerPreflightError(
            f"selected inner transaction has no callable main: {inner_module}"
        )

    return {
        "schema": PREFLIGHT_SCHEMA,
        "classification": "READY",
        "controller_restartable": True,
        "wrapper_consumed": False,
        "server_calls": 0,
        "host_calls": 0,
        "provider_calls": 0,
        "semantic_calls": 0,
        "repo_root": str(repo_root),
        "head": head,
        "tree": tree,
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "required_floor": f">={floor[0]}.{floor[1]}",
            "environment_root": str(environment_root),
        },
        "installed_runtime": installed,
        "exact_src_root": str(src_root),
        "relaylm_origin": relaylm_origin,
        "wrapper_module": wrapper_module,
        "wrapper_origin": wrapper_origin,
        "inner_module": inner_module,
        "inner_main_called": False,
        "one_shot_command": one_shot_command(
            wrapper_module,
            wrapper_args=wrapper_args,
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the restartable Python/controller boundary before a v1 "
            "llama.cpp one-shot wrapper is consumed."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--inner-module", required=True)
    parser.add_argument("--wrapper-module", required=True)
    parser.add_argument(
        "--wrapper-args",
        nargs=argparse.REMAINDER,
        default=(),
        help=(
            "Opaque arguments appended to the emitted wrapper command; place this "
            "option last because it consumes the remaining command line."
        ),
    )
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    try:
        result = validate_controller_environment(
            repo_root=Path(args.repo_root),
            expected_head=args.expected_head,
            expected_tree=args.expected_tree,
            inner_module=args.inner_module,
            wrapper_module=args.wrapper_module,
            wrapper_args=args.wrapper_args,
        )
    except Exception as exc:
        payload = {
            "schema": PREFLIGHT_SCHEMA,
            "classification": BLOCKED_CLASSIFICATION,
            "controller_restartable": True,
            "wrapper_consumed": False,
            "server_calls": 0,
            "host_calls": 0,
            "provider_calls": 0,
            "semantic_calls": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
