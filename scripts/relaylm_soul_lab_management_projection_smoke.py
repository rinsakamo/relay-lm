from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from fastapi.testclient import TestClient

from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_management import (
    build_lab_characters_projection,
    build_lab_settings_projection,
)
from relaylm.config import RelayLMConfig


def _raw_config() -> dict[str, object]:
    return {
        "mode": "memory_light",
        "listen": {"host": "127.0.0.1", "port": 8090},
        "trace": {"enabled": True, "path": "/private/raw-trace.jsonl"},
        "backends": {
            "local": {
                "type": "openai_compatible",
                "base_url": "http://relay-user:super-secret@127.0.0.1:1234/v1?token=hidden#fragment",
                "api_key": "top-secret-api-key",
                "default_model": "local-default-model",
            }
        },
        "model_routes": {
            "relaylm-companion": {
                "backend": "local",
                "backend_model": "qwen-local",
                "character_id": "rina",
                "memory_namespace": "rina-memory",
            },
            "relaylm-orphan": {
                "backend": "local",
                "character_id": "orphan",
                "mode": "pass_through",
            },
        },
        "characters": {
            "rina": {
                "soul": "/private/persona/RINA_SOUL.md",
                "output_policy": "/private/persona/OUTPUT_POLICY.md",
                "relationship_anchor": "/private/persona/RELATIONSHIP_ANCHOR.md",
                "memory_seed_path": "/private/memory/seed.md",
                "stable_memory_summary": "/private/memory/stable.md",
            }
        },
    }


def _assert_secret_free(payload: object) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden = (
        "top-secret-api-key",
        "super-secret",
        "relay-user",
        "token=hidden",
        "raw-trace.jsonl",
        "RINA_SOUL.md",
        "OUTPUT_POLICY.md",
        "RELATIONSHIP_ANCHOR.md",
        "seed.md",
        "stable.md",
    )
    for value in forbidden:
        assert value not in serialized, value


def main() -> None:
    raw = _raw_config()
    config = RelayLMConfig.model_validate(raw)

    settings = build_lab_settings_projection(config).model_dump(mode="json")
    assert settings["schema_version"] == "relaylm.lab.settings.v0"
    assert settings["projection_kind"] == "read_only"
    assert settings["content_free"] is True
    assert settings["settings_write_supported"] is False
    assert settings["network_probe_performed"] is False
    assert settings["credential_boundary"] == {
        "owner": "relaylm_server",
        "browser_loaded": False,
        "credential_fields_included": False,
    }
    assert settings["diagnostics"]["mode"] == "content_free"
    assert settings["diagnostics"]["source_content_included"] is False
    assert settings["listen"]["loopback_only"] is True

    backend = next(
        component
        for component in settings["runtime_components"]
        if component["component_id"] == "backend:local"
    )
    assert backend["endpoint"] == "http://127.0.0.1:1234/v1"
    assert backend["model_labels"] == ["local-default-model", "qwen-local"]
    assert backend["network_probe_performed"] is False
    assert {
        component["component_id"]: component["state"]
        for component in settings["runtime_components"]
    }["tts"] == "unconfigured"

    characters = build_lab_characters_projection(config).model_dump(mode="json")
    assert characters["schema_version"] == "relaylm.lab.characters.v0"
    assert characters["persistent_registry_mutation_supported"] is False
    assert characters["source_content_included"] is False
    by_id = {item["character_id"]: item for item in characters["characters"]}
    assert by_id["rina"]["source_complete"] is True
    assert by_id["rina"]["route_models"] == ["relaylm-companion"]
    assert by_id["rina"]["memory_namespaces"] == ["rina-memory"]
    assert by_id["orphan"]["source_complete"] is False
    assert by_id["rina"]["source_content_included"] is False
    assert by_id["rina"]["source_paths_included"] is False

    _assert_secret_free(settings)
    _assert_secret_free(characters)

    with TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.yaml"
        config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        client = TestClient(create_app(str(config_path)))

        settings_response = client.get("/lab/api/settings")
        assert settings_response.status_code == 200
        assert settings_response.headers["cache-control"] == "no-store"
        assert settings_response.json() == settings

        characters_response = client.get("/lab/api/characters")
        assert characters_response.status_code == 200
        assert characters_response.headers["cache-control"] == "no-store"
        assert characters_response.json() == characters

        assert client.patch("/lab/api/settings", json={}).status_code == 405
        assert client.post("/lab/api/characters", json={}).status_code == 405
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/v1/models").status_code == 200

        _assert_secret_free(settings_response.json())
        _assert_secret_free(characters_response.json())

    print("SOUL Lab management projection smoke passed")


if __name__ == "__main__":
    main()
