"""Fixed Hindsight v0.10.0 runtime used by the registered campaign binding.

This module is not a general-purpose launcher.  It accepts only the typed
deployment fields from ``HindsightLifecycleSpec`` and always starts the
repository's fixed HindsightServer integration.  The parent campaign owns the
process and terminates it in its cleanup boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import signal
import threading
from pathlib import Path
from typing import Any


# Hindsight reads this during import/configuration.  The zero-semantic
# rehearsal must never probe an answer model during deployment health.
os.environ.setdefault("HINDSIGHT_API_SKIP_LLM_VERIFICATION", "true")



def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file_tree(path: Path) -> str:
    entries = [
        {
            "path": child.relative_to(path).as_posix(),
            "sha256": _sha256_file(child),
        }
        for child in sorted(item for item in path.rglob("*") if item.is_file())
    ]
    if not entries:
        raise RuntimeError(f"tokenizer path is empty: {path}")
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_identity(
    path: Path,
    *,
    server: Any,
    profile: str,
    deployment_id: str,
    dependency_fingerprint: str,
    source_revision: str,
    source_tree: str,
    llm_model: str,
    llm_base_url: str,
    retain_max_completion_tokens: int,
    fail_on_extraction_errors: bool,
    embeddings_provider: str,
    reranker_provider: str,
    onnx_model_path: Path,
    onnx_tokenizer_path: Path,
) -> None:
    package_names = (
        "hindsight-all",
        "hindsight-api-slim",
        "hindsight-client",
        "hindsight-embed",
    )
    wheel_hashes: dict[str, str] = {}
    for name in package_names:
        distribution = importlib.metadata.distribution(name)
        direct_url = distribution.read_text("direct_url.json")
        if direct_url is None:
            raise RuntimeError(f"{name} has no exact direct_url.json")
        direct = json.loads(direct_url)
        archive_info = direct.get("archive_info")
        if not isinstance(archive_info, dict):
            raise RuntimeError(f"{name} direct_url.json has no archive_info")
        digest = archive_info.get("hashes", {}).get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise RuntimeError(f"{name} has no exact wheel sha256")
        wheel_hashes[name] = digest
    payload: dict[str, Any] = {
        "format_version": 1,
        "implementation": "hindsight",
        "version": importlib.metadata.version("hindsight-all"),
        "deployment_id": deployment_id,
        "dependency_fingerprint": dependency_fingerprint,
        "source_revision": source_revision,
        "source_tree": source_tree,
        "database_profile": profile,
        "host": server.host,
        "port": server.port,
        "pid": os.getpid(),
        "packages": {
            name: importlib.metadata.version(name) for name in package_names
        },
        "package_wheel_sha256": wheel_hashes,
        "llm_model": llm_model,
        "llm_base_url": llm_base_url,
        "retain_max_completion_tokens": retain_max_completion_tokens,
        "fail_on_extraction_errors": fail_on_extraction_errors,
        "embeddings_provider": embeddings_provider,
        "reranker_provider": reranker_provider,
        "embeddings_onnx_model_path": str(onnx_model_path),
        "embeddings_onnx_model_sha256": _sha256_file(onnx_model_path),
        "embeddings_onnx_tokenizer_path": str(onnx_tokenizer_path),
        "embeddings_onnx_tokenizer_tree_sha256": _sha256_file_tree(
            onnx_tokenizer_path
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--database-profile", required=True)
    parser.add_argument("--deployment-id", required=True)
    parser.add_argument("--dependency-fingerprint", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--llm-model", required=True)
    parser.add_argument("--llm-base-url", required=True)
    parser.add_argument("--retain-max-completion-tokens", required=True, type=int)
    parser.add_argument(
        "--fail-on-extraction-errors",
        required=True,
        choices=("true", "false"),
    )
    parser.add_argument("--embeddings-provider", required=True)
    parser.add_argument("--reranker-provider", required=True)
    parser.add_argument("--onnx-model-path", required=True)
    parser.add_argument("--onnx-tokenizer-path", required=True)
    parser.add_argument("--identity-path", required=True)
    args = parser.parse_args()

    if args.retain_max_completion_tokens <= 0:
        raise RuntimeError("Hindsight retain completion bound must be positive")
    os.environ["HINDSIGHT_API_RETAIN_MAX_COMPLETION_TOKENS"] = str(
        args.retain_max_completion_tokens
    )
    fail_on_extraction_errors = args.fail_on_extraction_errors == "true"
    os.environ["HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS"] = (
        "true" if fail_on_extraction_errors else "false"
    )
    os.environ["HINDSIGHT_API_EMBEDDINGS_PROVIDER"] = args.embeddings_provider
    os.environ["HINDSIGHT_API_RERANKER_PROVIDER"] = args.reranker_provider
    onnx_model_path = Path(args.onnx_model_path)
    onnx_tokenizer_path = Path(args.onnx_tokenizer_path)
    if not onnx_model_path.is_file() or not onnx_tokenizer_path.is_dir():
        raise RuntimeError("Hindsight ONNX paths are not the frozen local artifacts")
    os.environ["HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH"] = str(onnx_model_path)
    os.environ["HINDSIGHT_API_EMBEDDINGS_ONNX_TOKENIZER_NAME_OR_PATH"] = str(
        onnx_tokenizer_path
    )
    from hindsight import HindsightServer

    server = HindsightServer(
        db_url=f"pg0://{args.database_profile}",
        llm_provider="openai",
        llm_api_key="offline-health-probe",
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        host=args.host,
        port=args.port,
        mcp_enabled=False,
        log_level="warning",
    )
    stop_event = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.start(timeout=180.0)
    _write_identity(
        Path(args.identity_path),
        server=server,
        profile=args.database_profile,
        deployment_id=args.deployment_id,
        dependency_fingerprint=args.dependency_fingerprint,
        source_revision=args.source_revision,
        source_tree=args.source_tree,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        retain_max_completion_tokens=args.retain_max_completion_tokens,
        fail_on_extraction_errors=fail_on_extraction_errors,
        embeddings_provider=args.embeddings_provider,
        reranker_provider=args.reranker_provider,
        onnx_model_path=onnx_model_path,
        onnx_tokenizer_path=onnx_tokenizer_path,
    )
    try:
        stop_event.wait()
    finally:
        server.stop(timeout=30.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
