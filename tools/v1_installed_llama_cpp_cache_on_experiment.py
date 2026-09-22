"""Evaluation-only cache-on transport treatment for the installed llama.cpp path.

The installed RelayLM product remains authoritative and emits the qualified
``cache_prompt=false`` request.  This module substitutes only the repository
qualification proxy for the dedicated experimental physical target, proves an
exact one-field JSON delta, and forwards ``cache_prompt=true`` to llama-server.
It is not a production provider/runtime capability.
"""

from __future__ import annotations

import copy
import hashlib
import http.client
import http.server
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

import tools.v1_installed_llama_cpp_transaction as transaction


EXPERIMENT_TARGET_NAME = "v1:installed-llama-cpp-cache-on-experiment"
SUPPORTED_LLAMA_CPP_REVISION = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"

# Static source proof for the exact supported llama.cpp revision.  At this
# revision the generation path consults cache_prompt only after ``input_tokens``
# already exists, to choose common-prefix KV reuse.  The count endpoint's
# ``handle_count_tokens`` renders/tokenizes the prompt directly and has no
# cache_prompt branch.  The experiment therefore leaves input-token requests
# byte-identical while treating generation requests only.
COUNT_RENDERING_EQUIVALENCE = {
    "status": "proven_for_supported_revision",
    "llama_cpp_revision": SUPPORTED_LLAMA_CPP_REVISION,
    "generation_source": "tools/server/server-context.cpp",
    "generation_fact": (
        "cache_prompt gates common-prefix KV reuse after request input_tokens exist"
    ),
    "count_source": "tools/server/server-context.cpp::handle_count_tokens",
    "count_fact": (
        "chat input-token counting renders/tokenizes the prompt without a cache_prompt branch"
    ),
}


class CacheTreatmentError(transaction.RequestLedgerError):
    """The experimental transport cannot prove the exact treatment delta."""


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _json_body(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _prove_exact_cache_delta(
    product: Mapping[str, Any],
    treatment: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed unless cache_prompt false->true is the only JSON delta."""

    if set(product) != set(treatment):
        raise CacheTreatmentError("cache treatment changed the request member set")
    changed = sorted(key for key in product if product[key] != treatment[key])
    if changed != ["cache_prompt"]:
        raise CacheTreatmentError(
            "cache treatment must change exactly cache_prompt and no second field"
        )
    if product.get("cache_prompt") is not False:
        raise CacheTreatmentError(
            "cache treatment requires product-side cache_prompt=false"
        )
    if treatment.get("cache_prompt") is not True:
        raise CacheTreatmentError(
            "cache treatment requires upstream cache_prompt=true"
        )
    return {
        "changed_keys": changed,
        "cache_prompt": {"from": False, "to": True},
        "all_other_fields_equal": True,
    }


def _generation_treatment(body: bytes) -> tuple[bytes, dict[str, Any]]:
    product = transaction._parse_json_object(body, "product generation request")
    if "cache_prompt" not in product:
        raise CacheTreatmentError(
            "cache treatment requires explicit product-side cache_prompt=false"
        )
    if product["cache_prompt"] is not False:
        raise CacheTreatmentError(
            "cache treatment refuses a product request that is not cache_prompt=false"
        )

    treatment = copy.deepcopy(product)
    treatment["cache_prompt"] = True
    normalized_delta = _prove_exact_cache_delta(product, treatment)
    upstream_body = _json_body(treatment)
    return upstream_body, {
        "applied": True,
        "endpoint_class": "generation",
        "product_policy": "disabled",
        "experimental_transport_treatment": "generation cache_prompt=true",
        "product_request_sha256": _sha256_bytes(body),
        "upstream_treatment_request_sha256": _sha256_bytes(upstream_body),
        "product_request_bytes": len(body),
        "upstream_treatment_request_bytes": len(upstream_body),
        "product_controls": transaction._wire_controls(product),
        "upstream_controls": transaction._wire_controls(treatment),
        "normalized_delta": normalized_delta,
        "input_token_rendering_equivalence": COUNT_RENDERING_EQUIVALENCE,
    }


def _prepare_upstream_body(path: str, body: bytes) -> tuple[bytes, dict[str, Any]]:
    """Return the exact upstream body plus auditable treatment evidence."""

    if path == "/v1/chat/completions":
        return _generation_treatment(body)
    if path == "/v1/chat/completions/input_tokens":
        transaction._parse_json_object(body, "product input-token request")
        return body, {
            "applied": False,
            "endpoint_class": "input_token_count",
            "forwarding": "byte_identical",
            "product_request_sha256": _sha256_bytes(body),
            "upstream_request_sha256": _sha256_bytes(body),
            "input_token_rendering_equivalence": COUNT_RENDERING_EQUIVALENCE,
        }
    raise CacheTreatmentError(f"unsupported cache-treatment proxy path: {path}")


class _CacheOnProxyRequestHandler(transaction._ProxyRequestHandler):
    """Installed-path proxy handler with one bounded generation-field treatment."""

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path not in transaction.PROXY_PATHS:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > 8 * 1024 * 1024:
            self.send_error(413)
            return

        body = self.rfile.read(length)
        ledger = self.server.ledger  # type: ignore[attr-defined]
        try:
            entry = ledger.begin(path=self.path, body=body)
            upstream_body, treatment_evidence = _prepare_upstream_body(self.path, body)
            entry["cache_treatment_request"] = bool(treatment_evidence["applied"])
            entry["cache_treatment"] = treatment_evidence
        except Exception as exc:
            ledger.reject(path=self.path, body=body, reason=str(exc))
            self._send_json_error(400, str(exc))
            return

        parsed_origin = urlsplit(self.server.origin)  # type: ignore[attr-defined]
        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(
                parsed_origin.hostname,
                parsed_origin.port,
                timeout=transaction.REQUEST_TIMEOUT_SECONDS,
            )
            headers = {
                "Accept": self.headers.get("Accept", "application/json"),
                "Content-Type": self.headers.get("Content-Type", "application/json"),
                "Content-Length": str(len(upstream_body)),
            }
            authorization = self.headers.get("Authorization")
            if authorization:
                headers["Authorization"] = authorization
            connection.request(
                "POST",
                f"{parsed_origin.path.rstrip('/')}{self.path}",
                body=upstream_body,
                headers=headers,
            )
            upstream = connection.getresponse()
            streaming = bool(
                transaction._parse_json_object(body, "product provider request").get(
                    "stream"
                )
            )
            if streaming:
                self._forward_stream(upstream, entry, ledger)
            else:
                response_body = upstream.read()
                ledger.complete(
                    entry,
                    status=upstream.status,
                    body=response_body,
                    streaming=False,
                )
                self.send_response(upstream.status)
                self.send_header(
                    "Content-Type",
                    upstream.getheader("Content-Type", "application/json"),
                )
                self.send_header("Content-Length", str(len(response_body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(response_body)
                self.close_connection = True
        except Exception as exc:
            ledger.fail(entry, reason=str(exc))
            self._send_json_error(502, "cache-treatment proxy forwarding failed")
        finally:
            if connection is not None:
                connection.close()


class _CacheOnProxyServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        origin: str,
        ledger: transaction.RequestLedger,
    ) -> None:
        self.origin = origin
        self.ledger = ledger
        super().__init__(address, _CacheOnProxyRequestHandler)


class CacheOnForwardingProxy(transaction._ForwardingProxy):
    """Dedicated experimental proxy; ordinary installed target remains unchanged."""

    def __init__(self, *, origin: str, ledger: transaction.RequestLedger) -> None:
        self.origin = origin.rstrip("/")
        self.ledger = ledger
        self.server = _CacheOnProxyServer(
            ("127.0.0.1", 0),
            origin=self.origin,
            ledger=ledger,
        )
        self.thread = None


def run_cache_on_experiment(
    argv: Sequence[str] | None = None,
    *,
    target_name: str = EXPERIMENT_TARGET_NAME,
) -> int:
    """Run the installed cache-on treatment under one explicit target identity."""

    if not isinstance(target_name, str) or not target_name.strip():
        raise CacheTreatmentError("cache treatment target name must be non-empty")

    original_proxy = transaction._ForwardingProxy
    original_target = transaction.TARGET_NAME
    try:
        transaction._ForwardingProxy = CacheOnForwardingProxy
        transaction.TARGET_NAME = target_name
        return transaction.main(argv)
    finally:
        transaction._ForwardingProxy = original_proxy
        transaction.TARGET_NAME = original_target


def main(argv: Sequence[str] | None = None) -> int:
    """Run the historical cache-on experiment target."""

    return run_cache_on_experiment(argv)


if __name__ == "__main__":
    raise SystemExit(main())
