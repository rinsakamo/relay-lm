#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.character_store_bootstrap import (  # noqa: E402
    PROJECTION_SCHEMA,
    REQUEST_SCHEMA,
    CharacterStoreBootstrapRequest,
    execute_character_store_bootstrap,
)
from relaylm.character_store_bootstrap_cli import main as cli_main  # noqa: E402
from relaylm.config import load_config  # noqa: E402
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root  # noqa: E402


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_config(
    path: Path,
    *,
    root_path: str,
    character_id: str = "default",
    store_enabled: bool = True,
    route_namespace: str | None = "character/default",
    extra_routes: dict[str, Any] | None = None,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["memory"]["root_path"] = root_path
    cfg["memory"]["store_enabled"] = store_enabled
    cfg["model_routes"]["relaylm-default"]["character_id"] = character_id
    cfg["model_routes"]["relaylm-default"]["memory_namespace"] = route_namespace
    cfg["characters"] = {
        character_id: {
            "soul": "examples/profiles/default/SOUL.md",
            "output_policy": "examples/profiles/default/style.md",
        }
    }
    if extra_routes:
        cfg["model_routes"].update(extra_routes)
    path.write_text(yaml.safe_dump(cfg, sort_keys=True), encoding="utf-8")


def _run(path: Path, *, character_id: str = "default", apply: bool = False) -> Any:
    return execute_character_store_bootstrap(
        CharacterStoreBootstrapRequest(
            schema_version=REQUEST_SCHEMA,
            runtime_private=True,
            content_included=False,
            config=load_config(path),
            character_id=character_id,
            apply=apply,
        )
    )


def _public_json(result: Any) -> str:
    payload = result.to_public_dict()
    require(payload["schema_version"] == PROJECTION_SCHEMA, payload)
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _assert_projection_safe(result: Any, *, root: Path) -> None:
    text = _public_json(result)
    require(str(root) not in text, text)
    forbidden = (
        '"queue_job_id"',
        '"dispatch_id"',
        '"lease_token"',
        '"source_text"',
        '"snippet_text"',
        '"raw_exception"',
    )
    for item in forbidden:
        require(item not in text, text)
    payload = result.to_public_dict()
    for key in (
        "path_values_included",
        "digest_values_included",
        "character_value_included",
        "namespace_value_included",
        "timestamp_values_included",
        "raw_exception_included",
        "queue_authority_used",
        "worker_authority_used",
        "scheduler_authority_used",
        "semantic_memory_content_created",
        "memory_pages_mutated",
    ):
        require(payload[key] is False, payload)


def _scoped_root(store_root: Path, character_id: str = "default") -> Path:
    scoped = resolve_relaymem_character_store_root(str(store_root), character_id)
    require(scoped is not None, "character scope did not resolve")
    return Path(scoped)


def _assert_minimum_layout(scoped: Path) -> None:
    for relative in (
        "memory/mem/primary/projects",
        "memory/mem/primary/relationships",
        "memory/mem/primary/sessions",
        "memory/mem/primary/scenes",
    ):
        require((scoped / relative).is_dir(), relative)
    require((scoped / "memory/mem/index.md").read_text(encoding="utf-8") == "# Index\n", "index header")
    require((scoped / "memory/mem/log.md").read_text(encoding="utf-8") == "# Log\n", "log header")


def _create_minimum_layout(scoped: Path) -> None:
    for relative in (
        "memory/mem/primary/projects",
        "memory/mem/primary/relationships",
        "memory/mem/primary/sessions",
        "memory/mem/primary/scenes",
    ):
        (scoped / relative).mkdir(parents=True, exist_ok=True)
    (scoped / "memory/mem/index.md").write_text("# Index\n", encoding="utf-8")
    (scoped / "memory/mem/log.md").write_text("# Log\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        store_root = work / "store"
        store_root.mkdir()
        cfg_path = work / "cfg.yaml"
        _write_config(cfg_path, root_path=str(store_root))

        dry = _run(cfg_path, apply=False)
        require(dry.status == "dry_run_missing", dry)
        require(dry.mutated is False, dry)
        require(dry.missing_directory_count > 0, dry)
        require(dry.missing_control_file_count == 2, dry)
        require(not (store_root / "characters").exists(), "dry-run created character root")
        _assert_projection_safe(dry, root=store_root)
        print("ok dry-run reports missing layout without filesystem mutation")

        applied = _run(cfg_path, apply=True)
        require(applied.status == "applied_ready", applied)
        require(applied.ready is True, applied)
        require(applied.mutated is True, applied)
        require(applied.created_control_file_count == 2, applied)
        scoped = _scoped_root(store_root)
        _assert_minimum_layout(scoped)
        _assert_projection_safe(applied, root=store_root)
        print("ok apply creates the minimum Primary MEM store layout")

        page_path = scoped / "memory/mem/primary/projects/existing.md"
        page_text = "---\nnot: a real page\n---\nbody\n"
        page_path.write_text(page_text, encoding="utf-8")
        index_before = (scoped / "memory/mem/index.md").read_text(encoding="utf-8")
        log_before = (scoped / "memory/mem/log.md").read_text(encoding="utf-8")
        again = _run(cfg_path, apply=True)
        require(again.status == "already_ready", again)
        require(again.ready is True, again)
        require(again.mutated is False, again)
        require((scoped / "memory/mem/index.md").read_text(encoding="utf-8") == index_before, "index changed")
        require((scoped / "memory/mem/log.md").read_text(encoding="utf-8") == log_before, "log changed")
        require(page_path.read_text(encoding="utf-8") == page_text, "existing page changed")
        _assert_projection_safe(again, root=store_root)
        print("ok repeated apply is idempotent and preserves existing files")

        ready_dry = _run(cfg_path, apply=False)
        require(ready_dry.status == "dry_run_ready", ready_dry)
        require(ready_dry.ready is True, ready_dry)
        require(ready_dry.mutated is False, ready_dry)
        print("ok dry-run reports ready state after bootstrap")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        store_root = work / "malformed-store"
        store_root.mkdir()
        cfg_path = work / "cfg.yaml"
        _write_config(cfg_path, root_path=str(store_root))
        scoped = _scoped_root(store_root)
        _create_minimum_layout(scoped)
        (scoped / "memory/mem/index.md").write_text("# Wrong\n", encoding="utf-8")
        malformed = _run(cfg_path, apply=True)
        require(malformed.status == "invalid_input", malformed)
        require("character_store_bootstrap_control_file_header_mismatch" in malformed.reason_ids, malformed)
        require((scoped / "memory/mem/index.md").read_text(encoding="utf-8") == "# Wrong\n", "malformed index rewritten")
        print("ok malformed existing control file fails closed")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        cfg_path = work / "cfg.yaml"
        _write_config(cfg_path, root_path="relative-store")
        relative = _run(cfg_path, apply=True)
        require(relative.status == "invalid_input", relative)
        require("character_store_bootstrap_root_not_absolute" in relative.reason_ids, relative)

        missing_root_cfg = work / "missing-root.yaml"
        _write_config(missing_root_cfg, root_path=str(work / "missing"))
        missing_root = _run(missing_root_cfg, apply=True)
        require(missing_root.status == "invalid_input", missing_root)
        require("character_store_bootstrap_root_missing" in missing_root.reason_ids, missing_root)

        unknown_character = _run(missing_root_cfg, character_id="other", apply=True)
        require(unknown_character.status == "invalid_input", unknown_character)
        require("character_store_bootstrap_character_not_configured" in unknown_character.reason_ids, unknown_character)
        print("ok relative, missing, and cross-character scopes fail closed")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        store_root = work / "ambiguous-store"
        store_root.mkdir()
        cfg_path = work / "cfg.yaml"
        _write_config(
            cfg_path,
            root_path=str(store_root),
            extra_routes={
                "other-default": {
                    "backend": "local_backend",
                    "backend_model": "local-model",
                    "character_id": "default",
                    "memory_namespace": "other-default",
                }
            },
        )
        ambiguous = _run(cfg_path, apply=True)
        require(ambiguous.status == "invalid_input", ambiguous)
        require("character_store_bootstrap_route_scope_ambiguous" in ambiguous.reason_ids, ambiguous)
        require(not (store_root / "characters").exists(), "ambiguous route mutated filesystem")
        print("ok ambiguous route scope fails closed")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        store_root = work / "symlink-store"
        outside = work / "outside"
        store_root.mkdir()
        outside.mkdir()
        cfg_path = work / "cfg.yaml"
        _write_config(cfg_path, root_path=str(store_root))
        scoped = _scoped_root(store_root)
        (scoped / "memory/mem/primary").mkdir(parents=True)
        try:
            (scoped / "memory/mem/primary/projects").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            print("ok symlink layout smoke skipped on unsupported platform")
        else:
            symlinked = _run(cfg_path, apply=True)
            require(symlinked.status == "invalid_input", symlinked)
            require("character_store_bootstrap_layout_symlink_or_escape_blocked" in symlinked.reason_ids, symlinked)
            print("ok symlinked layout entry fails closed")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        store_root = work / "cli-store"
        store_root.mkdir()
        cfg_path = work / "cfg.yaml"
        _write_config(cfg_path, root_path=str(store_root))
        require(cli_main(["--config", str(cfg_path), "--character-id", "default", "--dry-run"]) == 0, "cli dry-run failed")
        require(cli_main(["--config", str(cfg_path), "--character-id", "default", "--apply"]) == 0, "cli apply failed")
        print("ok CLI supports dry-run-first and explicit apply")

    module_text = (REPO_ROOT / "relaylm" / "character_store_bootstrap.py").read_text(encoding="utf-8")
    forbidden_imports = (
        "local_worker_once",
        "execute_local_worker",
        "relaymem_local_scheduler",
        "claim_relaymem",
        "retry_release",
        "terminal_commit",
        "durable_enqueue",
        "protected_source_root",
    )
    for forbidden in forbidden_imports:
        require(forbidden not in module_text, f"forbidden authority reference present: {forbidden}")
    print("ok bootstrap module does not import queue, worker, scheduler, or source authorities")

    print("RelayLM E1-R2 character-store bootstrap smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
