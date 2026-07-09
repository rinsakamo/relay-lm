"""Harness-proof smoke test: the app boots and serves its basic routes.

This intentionally stays shallow. It only proves that ``create_app`` can be
constructed from a minimal config and that the non-backend-dependent routes
respond. Exercising /v1/chat/completions requires a running backend and is
left to a later PR.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from relaylm.app import create_app

MINIMAL_CONFIG_YAML = """
backends:
  local_backend:
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
"""


def _write_minimal_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(MINIMAL_CONFIG_YAML, encoding="utf-8")
    return config_path


def test_healthz_returns_ok(tmp_path: Path) -> None:
    config_path = _write_minimal_config(tmp_path)
    app = create_app(str(config_path))
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_lists_configured_routes(tmp_path: Path) -> None:
    config_path = _write_minimal_config(tmp_path)
    app = create_app(str(config_path))
    client = TestClient(app)

    response = client.get("/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    model_ids = [entry["id"] for entry in body["data"]]
    assert model_ids == ["relaylm-default"]
