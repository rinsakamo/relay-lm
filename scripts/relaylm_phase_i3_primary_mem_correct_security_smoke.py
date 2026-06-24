"""Mutation access, token, scope, and schema security smoke for Phase I-3."""
from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE, OTHER_CHARACTER, OTHER_NAMESPACE
from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def preflight_body(revision: int, operation_id: str, *, summary: str = "corrected summary") -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_correct_preflight_request.v0",
        "expected_revision": revision,
        "corrected_title": "corrected title",
        "corrected_summary": summary,
        "reason": "explicit user correction",
        "operation_id": operation_id,
    }


def apply_body(revision: int, operation_id: str, token: str) -> dict[str, object]:
    return {
        "schema": "relaylm.lab.memory_correct_apply_request.v0",
        "operation_id": operation_id,
        "apply_token": token,
        "expected_revision": revision,
    }


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        queue = root / "queue"
        protected = root / "protected"
        store = root / "store"
        queue.mkdir()
        protected.mkdir()
        store.mkdir()
        scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
        other_value = resolve_relaymem_character_store_root(str(store), OTHER_CHARACTER)
        require(scoped_value is not None and other_value is not None, "scope")
        scoped = Path(scoped_value)
        other = Path(other_value)
        memory_a = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="phase-i3-security-a",
            title="original A",
            summary="original summary A",
        )
        memory_b = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="phase-i3-security-b",
            title="original B",
            summary="original summary B",
        )
        # Keep the wrong-character store structurally valid but empty.
        from relaylm_phase6c1_primary_worker_test_support import prepare_store
        prepare_store(other)

        config_path = root / "config.yaml"
        write_config(
            config_path,
            port=9,
            queue=queue,
            protected=protected,
            store=store,
            enqueue_enabled=False,
        )
        app = create_app(str(config_path))
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            base_a = f"/lab/api/characters/{CHARACTER}/memory/{memory_a}"
            query = f"?namespace={NAMESPACE}"

            valid = client.post(
                f"{base_a}/correct/preflight{query}",
                json=preflight_body(1, "security-valid"),
            )
            require(valid.status_code == 200, valid.text)
            require(valid.headers["cache-control"] == "no-store", valid.headers)
            require("access-control-allow-origin" not in valid.headers, valid.headers)
            token = valid.json()["apply_token"]

            missing_schema = preflight_body(1, "missing-schema")
            del missing_schema["schema"]
            response = client.post(f"{base_a}/correct/preflight{query}", json=missing_schema)
            require(response.status_code == 422, response.text)
            require(response.json() == {"detail": "invalid_request"}, response.json())

            unexpected = preflight_body(1, "unexpected")
            unexpected["filesystem_path"] = "/tmp/leak"
            response = client.post(f"{base_a}/correct/preflight{query}", json=unexpected)
            require(response.status_code == 422, response.text)
            require("/tmp/leak" not in response.text, response.text)

            form = client.post(
                f"{base_a}/correct/preflight{query}",
                data={"schema": "relaylm.lab.memory_correct_preflight_request.v0"},
            )
            require(form.status_code == 415, form.text)
            require(client.get(f"{base_a}/correct{query}").status_code == 405, "GET mutation")

            no_token = client.post(
                f"{base_a}/correct{query}",
                json={
                    "schema": "relaylm.lab.memory_correct_apply_request.v0",
                    "operation_id": "security-valid",
                    "expected_revision": 1,
                },
            )
            require(no_token.status_code == 422, no_token.text)

            tampered = client.post(
                f"{base_a}/correct{query}",
                json=apply_body(1, "security-valid", token + "x"),
            )
            require(tampered.status_code == 403, tampered.text)
            require(tampered.json() == {"detail": "token_invalid"}, tampered.json())

            wrong_operation = client.post(
                f"{base_a}/correct{query}",
                json=apply_body(1, "different-operation", token),
            )
            require(wrong_operation.status_code == 403, wrong_operation.text)

            wrong_memory = client.post(
                f"/lab/api/characters/{CHARACTER}/memory/{memory_b}/correct{query}",
                json=apply_body(1, "security-valid", token),
            )
            require(wrong_memory.status_code == 403, wrong_memory.text)

            wrong_character = client.post(
                f"/lab/api/characters/{OTHER_CHARACTER}/memory/{memory_a}/correct/preflight{query}",
                json=preflight_body(1, "wrong-character"),
            )
            require(wrong_character.status_code == 404, wrong_character.text)
            require(wrong_character.json() == {"detail": "not_found_or_wrong_scope"}, wrong_character.json())

            wrong_namespace = client.post(
                f"{base_a}/correct/preflight?namespace={OTHER_NAMESPACE}",
                json=preflight_body(1, "wrong-namespace"),
            )
            require(wrong_namespace.status_code == 404, wrong_namespace.text)

            applied = client.post(
                f"{base_a}/correct{query}",
                json=apply_body(1, "security-valid", token),
            )
            require(applied.status_code == 200, applied.text)
            require(applied.json()["result_revision"] == 2, applied.json())
            replay = client.post(
                f"{base_a}/correct{query}",
                json=apply_body(1, "security-valid", token),
            )
            require(replay.status_code == 200, replay.text)
            require(replay.json()["idempotent_replay"] is True, replay.json())

            # Two preflights for the same revision: at most one commit wins.
            base_b = f"/lab/api/characters/{CHARACTER}/memory/{memory_b}"
            first = client.post(
                f"{base_b}/correct/preflight{query}",
                json=preflight_body(1, "race-a", summary="corrected by A"),
            )
            second = client.post(
                f"{base_b}/correct/preflight{query}",
                json=preflight_body(1, "race-b", summary="corrected by B"),
            )
            require(first.status_code == second.status_code == 200, (first.text, second.text))
            winner = client.post(
                f"{base_b}/correct{query}",
                json=apply_body(1, "race-a", first.json()["apply_token"]),
            )
            require(winner.status_code == 200, winner.text)
            loser = client.post(
                f"{base_b}/correct{query}",
                json=apply_body(1, "race-b", second.json()["apply_token"]),
            )
            require(loser.status_code == 409, loser.text)
            require(loser.json()["detail"] in {"stale_revision", "operation_conflict"}, loser.json())

            history = client.get(f"{base_a}/corrections{query}")
            require(history.status_code == 200, history.text)
            serialized = history.text
            for forbidden in (
                "page_digest", "lineage", "store_root", "filesystem", "token_digest",
                "prior_physical_id", "result_physical_id",
            ):
                require(forbidden not in serialized, forbidden)

            require(client.get("/healthz").status_code == 200, "health regression")
            require(client.get("/v1/models").status_code == 200, "models regression")

        remote = TestClient(app, client=("192.0.2.10", 50000))
        spoofed = remote.post(
            f"/lab/api/characters/{CHARACTER}/memory/{memory_a}/correct/preflight?namespace={NAMESPACE}",
            json=preflight_body(2, "spoofed"),
            headers={
                "Host": "127.0.0.1",
                "Origin": "http://127.0.0.1",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        require(spoofed.status_code == 403, spoofed.text)

        remote_raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        remote_raw["listen"] = {"host": "0.0.0.0", "port": 8090}
        remote_path = root / "remote.yaml"
        remote_path.write_text(yaml.safe_dump(remote_raw, sort_keys=False), encoding="utf-8")
        remote_app = create_app(str(remote_path))
        with TestClient(remote_app, client=("127.0.0.1", 50000)) as client:
            refused = client.post(
                f"/lab/api/characters/{CHARACTER}/memory/{memory_a}/correct/preflight?namespace={NAMESPACE}",
                json=preflight_body(2, "remote-config"),
            )
            require(refused.status_code == 403, refused.text)

    print("Phase I-3 Primary MEM Correct security smoke passed")


if __name__ == "__main__":
    main()
