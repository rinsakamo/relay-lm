"""Bounded #3013 CUDA qualification target for the repaired resident-SWA path.

Preparation is execution-free. A future queue invocation must present a live
owner comment granting the exact descriptor hash before it starts either arm.
Every llama.cpp POST is journaled and fsynced immediately before one send.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import stat
import subprocess
from threading import RLock
from typing import Any
from urllib.parse import urlsplit

import tools.cache_correctness_repair_runtime as candidate_runtime
import tools.v1_installed_llama_cpp_cache_on_experiment as cache_experiment
import tools.v1_installed_llama_cpp_transaction as transaction


TARGET_ID = "diagnostic:3006-cache-correctness-repair-qualification"
TARGET_NAME = "#3013 repaired cache correctness CUDA qualification"
OWNER_BRANCH = "research/3013-cache-correctness-repair-qualification"
EXECUTION_BRANCH = "v1"
OWNER_ISSUE = 3013
PRODUCTION_REPAIR_ISSUE = 3006
ATTEMPT_ID = "cache-correctness-repair-qualification-20260927-b"
QUEUE_RESOURCE = "llama-cpp:local-gpu"
MODEL_FACING_MAXIMUM = 32
GENERATION_MAXIMUM = 8
INPUT_COUNT_MAXIMUM = 24
PUBLIC_COMPLETION_MAXIMUM = 4
ARM_ORDER = ("cold", "reused")
REQUEST_ORDER = (
    "buffered_pass1",
    "buffered_pass2",
    "streaming_pass1",
    "streaming_pass2",
)
PHASE_INPUT_OPERATIONS = ("buffered_pass1", "buffered_pass2", "streaming_pass1", "streaming_pass2")
MODEL_FACING_REQUEST_ORDER = tuple(transaction.CANONICAL_PROVIDER_SEQUENCE)
REQUIRED_DESCRIPTOR_FIELDS = {
    "format_version",
    "authority_mode",
    "repository",
    "owner_branch",
    "attempt_id",
    "target_id",
    "resource_key",
    "source_manifest",
    "model",
    "queue_receipt_path",
    "roots",
    "ports",
    "server_policy",
    "request_policy",
    "failure_policy",
    "execution_authority_policy",
}
FORBIDDEN_IDENTIFIERS = {
    "diagnostic:3006-projection-provenance",
    "v1:llama-cpp-cache-correctness-reproducer",
    "relay-self:#259",
    "--swa-full",
    "projection-attempt-a",
}


class QualificationTargetError(RuntimeError):
    """The qualification cannot continue without violating its frozen gates."""


class DurableRequestJournal:
    """Fail-closed durable pre-send record and first-failure latch for one arm."""

    def __init__(
        self,
        *,
        root: Path,
        arm: str,
        before_send: Any,
    ) -> None:
        if arm not in ARM_ORDER:
            raise QualificationTargetError("unknown arm identity")
        self.root = root.resolve()
        self.arm = arm
        self.before_send = before_send
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        _fsync_directory(self.root.parent)
        self._lock = RLock()
        self._post_lock = RLock()
        self._stopped = False
        self._failure: dict[str, Any] | None = None
        self._durable_ids: list[str] = []

    @property
    def stopped(self) -> bool:
        with self._lock:
            return self._stopped

    @property
    def attempt_consumed(self) -> bool:
        with self._lock:
            return bool(self._durable_ids)

    def ensure_send_allowed(self) -> None:
        with self._lock:
            if self._stopped:
                raise QualificationTargetError("first-failure stop latch is set")

    def begin_serialized_post(self) -> None:
        self._post_lock.acquire()

    def end_serialized_post(self) -> None:
        self._post_lock.release()

    def recheck_before_send(self) -> None:
        with self._lock:
            self.ensure_send_allowed()
            self.before_send()

    def durable_record(
        self,
        *,
        entry: dict[str, Any],
        path: str,
        product_body: bytes,
        upstream_body: bytes,
        treatment: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            self.ensure_send_allowed()
            self.before_send()
            call_index = entry.get("call_index")
            if isinstance(call_index, bool) or not isinstance(call_index, int):
                raise QualificationTargetError("provider ledger omitted an integer request order")
            expected_index = len(self._durable_ids) + 1
            if call_index != expected_index:
                raise QualificationTargetError("durable request order is not contiguous")
            request_id = f"{self.arm}-{call_index:02d}"
            directory = self.root / f"{call_index:02d}-{entry.get('kind', 'unknown')}"
            directory.mkdir(mode=0o700, exist_ok=False)
            _fsync_directory(self.root)

            product_path = directory / "product-request.body"
            upstream_path = directory / "upstream-request.body"
            _write_new_file(product_path, product_body)
            _write_new_file(upstream_path, upstream_body)
            _fsync_directory(directory)

            record = {
                "format_version": 1,
                "request_id": request_id,
                "arm": self.arm,
                "call_index": call_index,
                "request_kind": entry.get("kind"),
                "generation_phase": entry.get("phase", entry.get("generation_phase")),
                "generation_index": entry.get("generation_index"),
                "logical_operation_index": entry.get("logical_operation_index"),
                "endpoint": path,
                "product_body_path": str(product_path),
                "product_body_sha256": _sha256_bytes(product_body),
                "product_body_bytes": len(product_body),
                "upstream_body_path": str(upstream_path),
                "upstream_body_sha256": _sha256_bytes(upstream_body),
                "upstream_body_bytes": len(upstream_body),
                "treatment": treatment,
                "durable_before_send": True,
                "send_attempt_count": 0,
                "consumption_boundary": "durable-record-written-and-fsynced-before-one-upstream-POST",
            }
            record_path = directory / "durable-record.json"
            _write_new_file(record_path, _canonical_json(record))
            _fsync_directory(directory)
            _fsync_directory(self.root)

            # The successful return is the exact point at which this POST is consumed.
            self._durable_ids.append(request_id)
            return record

    def mark_send_attempted(self, record: dict[str, Any]) -> None:
        record["send_attempt_count"] = 1
        record["send_attempted"] = True
        record_path = Path(record["product_body_path"]).parent / "durable-record.json"
        _replace_json_durable(record_path, record)

    def stop(self, *, reason: str, request_id: str | None = None) -> None:
        with self._lock:
            self._stopped = True
            if self._failure is not None:
                return
            self._failure = {
                "format_version": 1,
                "arm": self.arm,
                "reason": _bounded(reason),
                "failed_request_id": request_id,
                "attempt_consumed": bool(self._durable_ids),
                "durable_request_ids": list(self._durable_ids),
                "automatic_retry": False,
                "replay": False,
                "reseed": False,
                "fallback": False,
                "later_arm_started": False,
            }
            try:
                path = self.root / "first-failure-stop.json"
                _write_new_file(path, _canonical_json(self._failure))
                _fsync_directory(self.root)
            except FileExistsError:
                pass

    def evidence(self) -> dict[str, Any]:
        with self._lock:
            return {
                "format_version": 1,
                "arm": self.arm,
                "attempt_consumed": bool(self._durable_ids),
                "durable_request_count": len(self._durable_ids),
                "durable_request_ids": list(self._durable_ids),
                "stopped": self._stopped,
                "first_failure": copy.deepcopy(self._failure),
                "retry_count": 0,
                "replay_count": 0,
                "reseed_count": 0,
                "fallback_count": 0,
            }


class _DurableTreatmentHandler(transaction._ProxyRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - stdlib server contract
        journal: DurableRequestJournal = self.server.journal  # type: ignore[attr-defined]
        journal.begin_serialized_post()
        try:
            self._do_serialized_post(journal)
        except Exception as exc:
            journal.stop(reason=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            journal.end_serialized_post()

    def _do_serialized_post(self, journal: DurableRequestJournal) -> None:
        ledger = self.server.ledger  # type: ignore[attr-defined]
        if self.path not in transaction.PROXY_PATHS:
            ledger.reject(path=self.path, body=b"", reason="unsupported model-facing endpoint")
            journal.stop(reason=f"unsupported model-facing endpoint: {self.path}")
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > 8 * 1024 * 1024:
            ledger.reject(path=self.path, body=b"", reason="invalid model-facing request length")
            journal.stop(reason="invalid model-facing request length")
            self.send_error(413)
            return
        body = self.rfile.read(length)
        entry: dict[str, Any] | None = None
        connection: http.client.HTTPConnection | None = None
        try:
            journal.ensure_send_allowed()
            if self.headers.get("Authorization") is not None:
                raise QualificationTargetError("provider authorization headers are not configured")
            entry = ledger.begin(path=self.path, body=body)
            upstream_body, treatment = _prepare_arm_request(
                arm=journal.arm,
                path=self.path,
                body=body,
            )
            _verify_request_treatment(
                arm=journal.arm,
                path=self.path,
                product_body=body,
                upstream_body=upstream_body,
                treatment=treatment,
            )
            entry["cache_treatment_request"] = bool(treatment["applied"])
            entry["cache_treatment"] = treatment
            record = journal.durable_record(
                entry=entry,
                path=self.path,
                product_body=body,
                upstream_body=upstream_body,
                treatment=treatment,
            )

            parsed_origin = urlsplit(self.server.origin)  # type: ignore[attr-defined]
            connection = http.client.HTTPConnection(
                parsed_origin.hostname,
                parsed_origin.port,
                timeout=transaction.REQUEST_TIMEOUT_SECONDS,
            )
            journal.mark_send_attempted(record)
            journal.recheck_before_send()
            connection.request(
                "POST",
                f"{parsed_origin.path.rstrip('/')}{self.path}",
                body=upstream_body,
                headers={
                    "Accept": self.headers.get("Accept", "application/json"),
                    "Content-Type": self.headers.get("Content-Type", "application/json"),
                    "Content-Length": str(len(upstream_body)),
                },
            )
            upstream = connection.getresponse()
            if upstream.status != 200:
                journal.stop(
                    reason=f"upstream returned HTTP {upstream.status}",
                    request_id=record["request_id"],
                )
            product_payload = transaction._parse_json_object(body, "product provider request")
            if bool(product_payload.get("stream")):
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
            if entry is None:
                ledger.reject(path=self.path, body=body, reason=str(exc))
            else:
                ledger.fail(entry, reason=str(exc))
            journal.stop(
                reason=f"{type(exc).__name__}: {exc}",
                request_id=None if entry is None else f"{journal.arm}-{entry.get('call_index', 0):02d}",
            )
            try:
                self._send_json_error(502, "qualification transaction stopped after first failure")
            except OSError:
                self.close_connection = True
        finally:
            if connection is not None:
                connection.close()


class _DurableProxyServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        address: tuple[str, int],
        *,
        origin: str,
        ledger: transaction.RequestLedger,
        journal: DurableRequestJournal,
    ) -> None:
        self.origin = origin
        self.ledger = ledger
        self.journal = journal
        super().__init__(address, _DurableTreatmentHandler)


class DurableTreatmentProxy(transaction._ForwardingProxy):
    def __init__(
        self,
        *,
        origin: str,
        ledger: transaction.RequestLedger,
        journal: DurableRequestJournal,
    ) -> None:
        self.origin = origin.rstrip("/")
        self.ledger = ledger
        self.journal = journal
        self.server = _DurableProxyServer(
            ("127.0.0.1", 0),
            origin=self.origin,
            ledger=ledger,
            journal=journal,
        )
        self.thread = None


def _prepare_arm_request(
    *,
    arm: str,
    path: str,
    body: bytes,
) -> tuple[bytes, dict[str, Any]]:
    payload = transaction._parse_json_object(body, "product request")
    if path == "/v1/chat/completions/input_tokens":
        upstream, evidence = cache_experiment._prepare_upstream_body(path, body)
        if upstream != body or evidence.get("applied") is not False:
            raise QualificationTargetError("input-token request treatment is not byte-identical")
        evidence["arm"] = arm
        return upstream, evidence
    if path != "/v1/chat/completions":
        raise QualificationTargetError("unsupported model-facing endpoint")
    if payload.get("cache_prompt") is not False:
        raise QualificationTargetError("RelayLM product request must keep cache_prompt=false")
    if arm == "reused":
        upstream, evidence = cache_experiment._prepare_upstream_body(path, body)
        evidence["arm"] = arm
        return upstream, evidence
    controls = transaction._wire_controls(payload)
    return body, {
        "applied": False,
        "arm": arm,
        "endpoint_class": "generation",
        "product_policy": "disabled",
        "forwarding": "byte_identical",
        "product_request_sha256": _sha256_bytes(body),
        "upstream_request_sha256": _sha256_bytes(body),
        "product_controls": controls,
        "upstream_controls": controls,
        "normalized_delta": {"changed_keys": [], "all_other_fields_equal": True},
    }


def _verify_request_treatment(
    *,
    arm: str,
    path: str,
    product_body: bytes,
    upstream_body: bytes,
    treatment: dict[str, Any],
) -> None:
    if arm not in ARM_ORDER:
        raise QualificationTargetError("request treatment has an unknown arm")
    if path == "/v1/chat/completions/input_tokens":
        if product_body != upstream_body or treatment.get("applied") is not False:
            raise QualificationTargetError(
                "input-token treatment must be byte-identical in both arms"
            )
        return
    product = transaction._parse_json_object(product_body, "product treatment proof")
    upstream = transaction._parse_json_object(upstream_body, "upstream treatment proof")
    if product.get("cache_prompt") is not False:
        raise QualificationTargetError("RelayLM product cache policy changed from cache-off")
    if arm == "cold":
        if product_body != upstream_body or treatment.get("applied") is not False:
            raise QualificationTargetError("cold/cache-off arm changed the product request")
        return
    if upstream.get("cache_prompt") is not True:
        raise QualificationTargetError("reused arm omitted the authorized cache-on treatment")
    normalized_product = copy.deepcopy(product)
    normalized_upstream = copy.deepcopy(upstream)
    normalized_product.pop("cache_prompt", None)
    normalized_upstream.pop("cache_prompt", None)
    delta = treatment.get("normalized_delta")
    if (
        normalized_product != normalized_upstream
        or not isinstance(delta, dict)
        or delta.get("changed_keys") != ["cache_prompt"]
        or delta.get("all_other_fields_equal") is not True
    ):
        raise QualificationTargetError(
            "cache-on treatment changed a request field beyond cache_prompt"
        )


def validate_descriptor(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise QualificationTargetError("descriptor must be a JSON object")
    if set(payload) != REQUIRED_DESCRIPTOR_FIELDS:
        missing = sorted(REQUIRED_DESCRIPTOR_FIELDS - set(payload))
        extra = sorted(set(payload) - REQUIRED_DESCRIPTOR_FIELDS)
        raise QualificationTargetError(f"descriptor schema mismatch; missing={missing}; extra={extra}")
    if payload["format_version"] != 1:
        raise QualificationTargetError("unsupported descriptor format version")
    if payload["authority_mode"] != "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY":
        raise QualificationTargetError("descriptor authority mode is invalid")
    if payload["attempt_id"] != ATTEMPT_ID:
        raise QualificationTargetError("descriptor attempt id does not match frozen #3013 planning id")
    if payload["target_id"] != TARGET_ID or payload["resource_key"] != QUEUE_RESOURCE:
        raise QualificationTargetError("descriptor target or canonical resource does not match #3013")
    if payload["owner_branch"] != OWNER_BRANCH:
        raise QualificationTargetError("descriptor owner branch identity mismatch")
    repository = payload["repository"]
    if not isinstance(repository, dict) or set(repository) != {
        "name",
        "execution_branch",
        "head",
        "tree",
    }:
        raise QualificationTargetError("descriptor repository pin is malformed")
    if repository["name"] != "rinsakamo/relay-lm" or repository["execution_branch"] != EXECUTION_BRANCH:
        raise QualificationTargetError("descriptor must execute on repository v1")

    source = payload["source_manifest"]
    if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
        raise QualificationTargetError("descriptor source manifest pin is malformed")
    if not isinstance(source["path"], str) or not _valid_sha256(source["sha256"]):
        raise QualificationTargetError("descriptor source manifest pin is invalid")
    model = payload["model"]
    if model != {"path": str(candidate_runtime.MODEL_PATH), "sha256": candidate_runtime.MODEL_SHA256}:
        raise QualificationTargetError("descriptor model identity or quantization is not canonical")

    if not isinstance(payload["queue_receipt_path"], str) or not payload["queue_receipt_path"].strip():
        raise QualificationTargetError("queue receipt path must be a non-empty frozen path")
    roots = payload["roots"]
    if not isinstance(roots, dict) or set(roots) != {
        "preflight",
        "output",
        "cold",
        "reused",
    }:
        raise QualificationTargetError("descriptor root map is malformed")
    root_paths = {key: Path(value).expanduser().resolve() for key, value in roots.items()}
    if root_paths["cold"] != root_paths["output"] / "cold":
        raise QualificationTargetError("cold root must be the frozen output child")
    if root_paths["reused"] != root_paths["output"] / "reused":
        raise QualificationTargetError("reused root must be the frozen output child")
    if root_paths["preflight"] == root_paths["output"]:
        raise QualificationTargetError("preflight and output roots must be distinct")
    if root_paths["preflight"].parent != root_paths["output"].parent:
        raise QualificationTargetError("preflight and output roots must be distinct siblings")
    ports = payload["ports"]
    if ports != {"llama_cpp": 1234, "relaylm": 18090}:
        raise QualificationTargetError("descriptor must freeze the sole supported port pair")
    server_policy = payload["server_policy"]
    if server_policy != {
        "fresh_process_per_arm": True,
        "slots": 1,
        "candidate_model_load_maximum": 2,
        "slot_state_within_arm": "retained-across-buffered-then-streaming-request-order",
        "between_arm_state": "separate-fresh-server-and-fresh-profile-copies-per-arm-no-state-shared",
        "context_tokens": 8192,
        "gpu_layers": 999,
        "swa_full": False,
        "checkpointing_disabled": False,
    }:
        raise QualificationTargetError("server/slot lifetime policy is not exact")
    request_policy = payload["request_policy"]
    if request_policy != {
        "order": list(REQUEST_ORDER),
        "model_facing_request_order": [list(item) for item in MODEL_FACING_REQUEST_ORDER],
        "cold_generation_cache_prompt": False,
        "reused_generation_cache_prompt": True,
        "count_endpoint_treatment": "byte-identical-cache_prompt-false",
        "product_cache_policy": "disabled",
        "reasoning_effort": "none",
        "temperature": 0,
        "top_p": 1,
        "seed_policy": "seed-field-omitted-backend-default",
        "max_tokens": 256,
        "generation_request_maximum": GENERATION_MAXIMUM,
        "input_count_request_maximum": INPUT_COUNT_MAXIMUM,
        "model_facing_post_maximum": MODEL_FACING_MAXIMUM,
        "public_completion_maximum": PUBLIC_COMPLETION_MAXIMUM,
        "dynamic_identity": "each-exact-body-fsynced-and-hashed-before-one-send",
    }:
        raise QualificationTargetError("request/treatment policy is not exact")
    failure_policy = payload["failure_policy"]
    if failure_policy != {
        "stop_on_first_failure": True,
        "retry": False,
        "replay": False,
        "reseed": False,
        "fallback": False,
        "alternate_port": False,
        "alternate_output_root": False,
        "manual_arm_completion": False,
        "new_attempt_after_preparation_failure": False,
    }:
        raise QualificationTargetError("failure/no-retry policy is not exact")
    authority_policy = payload["execution_authority_policy"]
    if authority_policy != {
        "required_issue": OWNER_ISSUE,
        "required_author": "rinsakamo",
        "required_marker": "EXECUTION_AUTHORITY_GRANTED",
        "comment_must_name_descriptor_sha256": True,
        "comment_must_name_attempt_and_target": True,
        "fresh_issue_comment_check_before_each_model_facing_post": True,
        "fresh_v1_head_check_before_each_model_facing_post": True,
    }:
        raise QualificationTargetError("external execution-authority gate is not exact")
    forbidden = _deep_string_values(payload) & FORBIDDEN_IDENTIFIERS
    if forbidden:
        raise QualificationTargetError(f"descriptor contains forbidden historical identity: {sorted(forbidden)}")
    return {
        "payload": payload,
        "roots": root_paths,
        "descriptor_sha256": None,
    }


def verify_descriptor_runtime(
    *,
    descriptor_path: Path,
    repo_root: Path,
    validated: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    payload = validated["payload"]
    descriptor_hash = _sha256_file(descriptor_path)
    repo = payload["repository"]
    head = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    branch = _git(repo_root, "branch", "--show-current")
    if head != repo["head"] or tree != repo["tree"] or branch != EXECUTION_BRANCH:
        raise QualificationTargetError("current v1 checkout does not match frozen descriptor head/tree")
    status = _git(repo_root, "status", "--porcelain")
    if status:
        raise QualificationTargetError("physical target requires the exact clean merged v1 checkout")

    manifest_path = Path(payload["source_manifest"]["path"]).expanduser().resolve()
    if not manifest_path.is_file() or _sha256_file(manifest_path) != payload["source_manifest"]["sha256"]:
        raise QualificationTargetError("candidate runtime manifest hash mismatch")
    manifest = _read_json_object(manifest_path)
    _verify_candidate_runtime_manifest(manifest)
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise QualificationTargetError("candidate runtime manifest lacks source identity")
    expected_patch_hashes = candidate_runtime.verify_patch_hashes()
    _validate_candidate_source_identity(source, expected_patch_hashes)
    build_root = Path(manifest["build"]["build_root"]).expanduser().resolve()
    server_binary = Path(manifest["server"]["path"]).expanduser().resolve()
    if _sha256_file(server_binary).removeprefix("sha256:") != manifest["server"]["sha256"]:
        raise QualificationTargetError("candidate llama-server hash changed after build")
    if candidate_runtime._stat_identity(server_binary) != manifest["server"].get("identity"):
        raise QualificationTargetError("candidate llama-server object identity changed after build")
    if Path(manifest["model"]["path"]).resolve() != candidate_runtime.MODEL_PATH.resolve():
        raise QualificationTargetError("runtime manifest model path mismatch")
    if manifest["model"].get("sha256") != candidate_runtime.MODEL_SHA256:
        raise QualificationTargetError("runtime manifest model digest mismatch")
    try:
        candidate_runtime.validate_model_identity(
            model_path=candidate_runtime.MODEL_PATH,
            observed_sha256=_sha256_file(candidate_runtime.MODEL_PATH).removeprefix("sha256:"),
        )
    except candidate_runtime.RuntimePinError as exc:
        raise QualificationTargetError(str(exc)) from exc

    source_checkout = Path(manifest["build"]["source_output"]).expanduser().resolve()
    try:
        candidate_runtime.verify_qualification_source_tree(source_checkout)
    except candidate_runtime.RuntimePinError as exc:
        raise QualificationTargetError("candidate source checkout changed after build") from exc
    actual_closure = candidate_runtime.collect_static_library_closure(build_root)
    if actual_closure != manifest["build"]["shared_libraries"]:
        raise QualificationTargetError("candidate shared-library closure changed after build")
    actual_wsl_driver_closure = candidate_runtime.collect_wsl_cuda_driver_closure(actual_closure)
    if actual_wsl_driver_closure != manifest["build"].get("wsl_cuda_driver_closure"):
        raise QualificationTargetError("WSL CUDA driver object closure changed after manifest creation")
    _verify_live_gpu_identity(manifest)
    if not _port_is_free(1234) or not _port_is_free(18090):
        raise QualificationTargetError("one of the sole frozen ports is occupied; no alternate is allowed")
    for key in ("preflight", "output", "cold", "reused"):
        if validated["roots"][key].exists():
            raise QualificationTargetError(f"frozen {key} root already exists")

    source_env = _candidate_server_environment(manifest)
    identity = {
        "descriptor_sha256": descriptor_hash,
        "repository_head": head,
        "repository_tree": tree,
        "source_manifest_sha256": payload["source_manifest"]["sha256"],
        "source_revision": source["revision"],
        "source_base_tree": source["base_tree"],
        "production_patch_sha256": source["production_patch_sha256"],
        "production_repair_tree": source["production_repair_tree"],
        "qualification_observability_patch_sha256": source["observability_patch_sha256"],
        "qualification_observability_tree": source["qualification_observability_tree"],
        "server_binary": str(server_binary),
        "server_sha256": manifest["server"]["sha256"],
        "shared_library_closure": manifest["build"]["shared_libraries"],
        "wsl_cuda_driver_closure": manifest["build"]["wsl_cuda_driver_closure"],
        "model_path": manifest["model"]["path"],
        "model_sha256": manifest["model"]["sha256"],
        "runtime_environment": {
            key: source_env.get(key)
            for key in (
                "PATH",
                "HOME",
                "USER",
                "LANG",
                "LC_ALL",
                "TZ",
                "CUDA_HOME",
                "CUDA_VISIBLE_DEVICES",
                "LD_LIBRARY_PATH",
                "LD_PRELOAD",
            )
        },
    }
    return manifest, {"server_binary": str(server_binary), "build_root": str(build_root), **identity}


def _validate_candidate_source_identity(
    source: dict[str, Any],
    expected_patch_hashes: dict[str, str],
) -> None:
    if (
        source.get("revision") != candidate_runtime.BASE_REVISION
        or source.get("base_tree") != candidate_runtime.BASE_TREE
        or source.get("production_patch_sha256") != candidate_runtime.PRODUCTION_PATCH_SHA256
        or source.get("production_repair_tree") != candidate_runtime.PRODUCTION_TREE
        or source.get("observability_patch_sha256")
        != expected_patch_hashes["observability_patch_sha256"]
        or source.get("qualification_observability_tree")
        != candidate_runtime.OBSERVABILITY_TREE
    ):
        raise QualificationTargetError("candidate source base/tree/patch identity mismatch")


def _verify_candidate_runtime_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("format_version") != 2 or manifest.get("kind") != "relaylm-3013-repaired-cuda-candidate":
        raise QualificationTargetError("candidate runtime manifest kind or schema is invalid")
    source = manifest.get("source")
    build = manifest.get("build")
    server = manifest.get("server")
    model = manifest.get("model")
    if not all(isinstance(item, dict) for item in (source, build, server, model)):
        raise QualificationTargetError("candidate runtime manifest is incomplete")
    if source.get("repository") != candidate_runtime.UPSTREAM_REPOSITORY:
        raise QualificationTargetError("candidate source repository is not canonical")
    if build.get("cmake_arguments") != list(candidate_runtime.CMAKE_ARGS):
        raise QualificationTargetError("candidate CMake invocation differs from the reviewed CUDA build")
    if build.get("targets") != list(candidate_runtime.BUILD_TARGETS):
        raise QualificationTargetError("candidate build target set differs from the reviewed CUDA build")
    if build.get("cuda_toolkit") != "12.8" or build.get("cuda_architectures") != [86]:
        raise QualificationTargetError("candidate CUDA toolkit or architecture identity is invalid")
    if build.get("build_type") != "Release":
        raise QualificationTargetError("candidate build is not a Release CUDA build")
    wsl_driver_closure = build.get("wsl_cuda_driver_closure")
    if wsl_driver_closure is not None and (
        not isinstance(wsl_driver_closure, dict)
        or wsl_driver_closure.get("schema_version") != 1
        or wsl_driver_closure.get("contract")
        != "wsl-cuda-driver-shim-and-package-payload-v1"
        or wsl_driver_closure.get("logical_dependency") != "libcuda.so.1"
    ):
        raise QualificationTargetError("candidate manifest has a malformed WSL CUDA driver object contract")

    build_root = Path(str(build.get("build_root", ""))).expanduser().resolve()
    server_path = (build_root / "bin" / "llama-server").resolve()
    if Path(str(server.get("path", ""))).expanduser().resolve() != server_path:
        raise QualificationTargetError("candidate server path is outside the pinned build root")
    if server.get("identity") != candidate_runtime._stat_identity(server_path):
        raise QualificationTargetError("candidate server object identity is not the sealed build object")
    if server.get("swa_full") is not False or server.get("checkpointing_disabled") is not False:
        raise QualificationTargetError("candidate server manifest disables SWA or checkpointing")
    if server.get("server_slots") != 1:
        raise QualificationTargetError("candidate server manifest does not pin one slot")
    expected_argv = [
        str(server_path),
        "-m",
        str(candidate_runtime.MODEL_PATH),
        "--host",
        "127.0.0.1",
        "--port",
        "<descriptor-port>",
        "-ngl",
        "999",
        "-c",
        "8192",
        "-np",
        "1",
        "--no-context-shift",
        "-lv",
        "4",
        "--log-timestamps",
        "--log-file",
        "<arm-evidence-root>/llama-server.log",
    ]
    if server.get("startup_argv_template") != expected_argv:
        raise QualificationTargetError("candidate startup argv template differs from the reviewed runtime geometry")

    cache_path = build_root / "CMakeCache.txt"
    expected_cache_hash = build.get("cmake_cache_sha256")
    if (
        not cache_path.is_file()
        or expected_cache_hash != f"sha256:{candidate_runtime.sha256_file(cache_path)}"
    ):
        raise QualificationTargetError("candidate CMake cache changed after its build manifest was written")
    try:
        candidate_runtime._validate_cmake_configuration(candidate_runtime.read_cmake_cache(build_root))
        flags_path, flags_hash = candidate_runtime._cuda_architecture_flags(build_root)
    except candidate_runtime.RuntimePinError as exc:
        raise QualificationTargetError("candidate CUDA build configuration no longer validates") from exc
    architecture_record = build.get("cuda_architecture_flags")
    if architecture_record != {
        "path": flags_path,
        "sha256": f"sha256:{flags_hash}",
        "effective_architectures": [86],
    }:
        raise QualificationTargetError("candidate CUDA architecture flags differ from the pinned manifest")
    _verify_candidate_test_binaries(manifest)


def _verify_candidate_test_binaries(manifest: dict[str, Any]) -> None:
    build = manifest.get("build")
    if not isinstance(build, dict):
        raise QualificationTargetError("candidate build manifest is malformed")
    build_root = Path(str(build.get("build_root", ""))).expanduser().resolve()
    observed = build.get("test_binaries")
    expected_names = candidate_runtime.BUILD_TARGETS[1:]
    if not isinstance(observed, dict) or set(observed) != set(expected_names):
        raise QualificationTargetError("candidate source-regression binary set is incomplete")
    for name in expected_names:
        record = observed.get(name)
        expected_path = (build_root / "bin" / name).resolve()
        if not isinstance(record, dict) or Path(str(record.get("path", ""))).resolve() != expected_path:
            raise QualificationTargetError(f"candidate source-regression path changed: {name}")
        if (
            not expected_path.is_file()
            or not os.access(expected_path, os.X_OK)
            or record.get("sha256") != candidate_runtime.sha256_file(expected_path)
        ):
            raise QualificationTargetError(f"candidate source-regression binary changed: {name}")


def _verify_live_gpu_identity(manifest: dict[str, Any]) -> None:
    try:
        observed = candidate_runtime.run_text(
            candidate_runtime.GPU_QUERY_COMMAND
        )
    except candidate_runtime.RuntimePinError as exc:
        raise QualificationTargetError("fresh CUDA GPU identity lookup failed") from exc
    expected = manifest.get("build", {}).get("gpu")
    if not isinstance(expected, str) or observed != expected:
        raise QualificationTargetError("live CUDA GPU identity differs from the frozen candidate build")


def verify_exact_execution_authority(
    *,
    comment_id: int,
    descriptor_path: Path,
    descriptor_sha256: str,
) -> dict[str, Any]:
    if isinstance(comment_id, bool) or not isinstance(comment_id, int) or comment_id <= 0:
        raise QualificationTargetError("an exact #3013 authority comment id is required")
    issue_response = subprocess.run(
        ["gh", "api", f"repos/rinsakamo/relay-lm/issues/{OWNER_ISSUE}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if issue_response.returncode != 0:
        raise QualificationTargetError("fresh #3013 owner lookup failed")
    try:
        issue = json.loads(issue_response.stdout)
    except json.JSONDecodeError as exc:
        raise QualificationTargetError("fresh #3013 owner response is malformed") from exc
    if (
        not isinstance(issue, dict)
        or issue.get("number") != OWNER_ISSUE
        or issue.get("state") != "open"
        or not isinstance(issue.get("user"), dict)
        or issue["user"].get("login") != "rinsakamo"
    ):
        raise QualificationTargetError("#3013 owner or open-issue identity changed")
    response = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/rinsakamo/relay-lm/issues/{OWNER_ISSUE}/comments?per_page=100",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if response.returncode != 0:
        raise QualificationTargetError("fresh #3013 authority comment lookup failed")
    comments: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    offset = 0
    response_text = response.stdout
    while offset < len(response_text):
        while offset < len(response_text) and response_text[offset].isspace():
            offset += 1
        if offset >= len(response_text):
            break
        try:
            page, offset = decoder.raw_decode(response_text, offset)
        except json.JSONDecodeError as exc:
            raise QualificationTargetError("fresh #3013 authority response is malformed") from exc
        if isinstance(page, list) and all(isinstance(item, dict) for item in page):
            comments.extend(page)
        elif isinstance(page, dict):
            comments.append(page)
        else:
            raise QualificationTargetError("fresh #3013 comments pagination is malformed")
    selected = next(
        (
            comment
            for comment in comments
            if isinstance(comment, dict) and comment.get("id") == comment_id
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise QualificationTargetError("exact #3013 execution-authority comment is unavailable")
    selected_comment_id = selected.get("id")
    if isinstance(selected_comment_id, bool) or not isinstance(selected_comment_id, int):
        raise QualificationTargetError("exact #3013 authority comment omitted its numeric identity")
    if not isinstance(selected.get("user"), dict) or selected["user"].get("login") != "rinsakamo":
        raise QualificationTargetError("execution-authority comment is not from the issue owner")
    body = selected.get("body")
    if not isinstance(body, str):
        raise QualificationTargetError("execution-authority comment body is malformed")
    required = (
        "EXECUTION_AUTHORITY_GRANTED",
        descriptor_sha256,
        ATTEMPT_ID,
        TARGET_ID,
        candidate_runtime.BASE_REVISION,
        candidate_runtime.PRODUCTION_TREE,
        candidate_runtime.MODEL_SHA256,
    )
    if any(value not in body for value in required):
        raise QualificationTargetError("execution-authority comment does not bind the exact frozen transaction")
    if "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY" in body:
        raise QualificationTargetError("proposal-only comment cannot authorize physical execution")
    selected_created = str(selected.get("created_at", ""))
    for comment in comments:
        if not isinstance(comment, dict) or not isinstance(comment.get("user"), dict):
            continue
        if comment["user"].get("login") != "rinsakamo":
            continue
        later_comment_id = comment.get("id")
        later_by_id = (
            not isinstance(later_comment_id, bool)
            and isinstance(later_comment_id, int)
            and later_comment_id > selected_comment_id
        )
        later_by_time = str(comment.get("created_at", "")) > selected_created
        if later_by_id or later_by_time:
            later_body = comment.get("body")
            if isinstance(later_body, str) and any(
                marker in later_body
                for marker in (
                    "EXECUTION_AUTHORITY_REVOKED",
                    "STOP #3013",
                    "STOP EXACT TRANSACTION",
                )
            ):
                raise QualificationTargetError("a later owner comment revoked the transaction")
    del descriptor_path
    return {
        "comment_id": comment_id,
        "author": "rinsakamo",
        "owner_issue": OWNER_ISSUE,
        "owner_issue_state": "open",
        "descriptor_sha256": descriptor_sha256,
        "attempt_id": ATTEMPT_ID,
        "target_id": TARGET_ID,
        "fresh_lookup": True,
    }


def verify_live_v1_head(expected_head: str, repo_root: Path) -> None:
    output = _run_text(["git", "ls-remote", "--heads", "origin", "refs/heads/v1"], cwd=repo_root)
    entries = [line.split("\t", 1) for line in output.splitlines() if line.strip()]
    if len(entries) != 1 or len(entries[0]) != 2 or entries[0][1] != "refs/heads/v1":
        raise QualificationTargetError("fresh origin/v1 lookup was malformed")
    if entries[0][0] != expected_head:
        raise QualificationTargetError("origin/v1 moved after the frozen descriptor")
    if (
        _git(repo_root, "rev-parse", "HEAD") != expected_head
        or _git(repo_root, "branch", "--show-current") != EXECUTION_BRANCH
        or _git(repo_root, "status", "--porcelain")
    ):
        raise QualificationTargetError("local v1 checkout changed after the frozen descriptor")


def run_target(
    *,
    descriptor_path: Path,
    repo_root: Path,
    authority_comment_id: int,
) -> int:
    descriptor_path = descriptor_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()
    payload = _read_json_object(descriptor_path)
    validated = validate_descriptor(payload)
    manifest, runtime_identity = verify_descriptor_runtime(
        descriptor_path=descriptor_path,
        repo_root=repo_root,
        validated=validated,
    )
    descriptor_hash = runtime_identity["descriptor_sha256"]
    roots: dict[str, Path] = validated["roots"]

    authority = verify_exact_execution_authority(
        comment_id=authority_comment_id,
        descriptor_path=descriptor_path,
        descriptor_sha256=descriptor_hash,
    )
    expected_head = payload["repository"]["head"]

    roots["preflight"].mkdir(mode=0o700, parents=True, exist_ok=False)
    _fsync_directory(roots["preflight"].parent)
    preflight = {
        "format_version": 1,
        "state": "preflight_passed",
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_hash,
        "runtime_identity": runtime_identity,
        "authority": authority,
        "transaction_calls": 0,
        "candidate_model_loads": 0,
        "generation_requests": 0,
        "input_count_requests": 0,
        "attempt_consumed": False,
    }
    _atomic_json(roots["preflight"] / "preflight.json", preflight)
    try:
        _run_candidate_static_checks(manifest, roots["preflight"])
    except Exception as exc:
        preflight["state"] = "preexecution_block"
        preflight["failure"] = {"type": type(exc).__name__, "message": _bounded(str(exc))}
        preflight["transaction_calls"] = 0
        preflight["candidate_model_loads"] = 0
        preflight["generation_requests"] = 0
        preflight["input_count_requests"] = 0
        preflight["attempt_consumed"] = False
        _atomic_json(roots["preflight"] / "preflight.json", preflight)
        _seal_directory(roots["preflight"])
        verify_evidence_manifest(roots["preflight"])
        return 2
    _seal_directory(roots["preflight"])
    verify_evidence_manifest(roots["preflight"])

    roots["output"].mkdir(mode=0o700, parents=True, exist_ok=False)
    _fsync_directory(roots["output"].parent)
    attempt_summary: dict[str, Any] = {
        "format_version": 1,
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_hash,
        "authority": authority,
        "state": "running",
        "arm_order": list(ARM_ORDER),
        "server_launch_count": 0,
        "candidate_model_load_attempts": 0,
        "generation_request_count": 0,
        "input_count_request_count": 0,
        "model_facing_post_count": 0,
        "attempt_consumed": False,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "repair_generation_count": 0,
        "later_arm_started": False,
        "product_cache_policy": "disabled",
        "failure": None,
        "arms": {},
    }
    server_env = _candidate_server_environment(manifest)
    tx_args_base = {
        "repo_root": str(repo_root),
        "llama_cpp_root": str(Path(manifest["build"]["source_output"]).resolve()),
        "target_path": str(transaction.DEFAULT_TARGET_PATH),
        "artifact_path": str(candidate_runtime.MODEL_PATH),
        "llama_port": payload["ports"]["llama_cpp"],
        "relay_port": payload["ports"]["relaylm"],
        "scenario_id": transaction.CANONICAL_SCENARIO_ID,
    }

    for arm_index, arm in enumerate(ARM_ORDER):
        try:
            verify_exact_execution_authority(
                comment_id=authority_comment_id,
                descriptor_path=descriptor_path,
                descriptor_sha256=descriptor_hash,
            )
            verify_live_v1_head(expected_head, repo_root)
            arm_root = roots[arm]
            arm_root.mkdir(mode=0o700, parents=False, exist_ok=False)
            _fsync_directory(roots["output"])
            server_process_state: dict[str, Any] = {}
            expected_server_argv = _expected_server_argv(
                manifest=manifest,
                port=payload["ports"]["llama_cpp"],
                arm_root=arm_root,
            )

            def attest_server_process(
                process: subprocess.Popen[str],
                binary: Path,
            ) -> dict[str, Any]:
                _verify_candidate_server_controls(
                    process=process,
                    expected_argv=expected_server_argv,
                    expected_environment=server_env,
                )
                observed = _verify_loaded_library_closure(
                    process=process,
                    binary=binary,
                    manifest=manifest,
                )
                server_process_state["process"] = process
                server_process_state["binary"] = binary.resolve()
                server_process_state["initial_closure"] = observed
                return observed

            def before_send() -> None:
                _check_send_authority(
                    authority_comment_id=authority_comment_id,
                    descriptor_path=descriptor_path,
                    descriptor_sha256=descriptor_hash,
                    expected_head=expected_head,
                    repo_root=repo_root,
                )
                server_process_state["latest_closure"] = _verify_candidate_process_identity(
                    process=server_process_state.get("process"),
                    binary=server_process_state.get("binary"),
                    manifest=manifest,
                    expected_argv=expected_server_argv,
                    expected_environment=server_env,
                    previous_attestation=server_process_state.get("latest_closure")
                    or server_process_state.get("initial_closure"),
                )

            journal = DurableRequestJournal(
                root=arm_root / "model-facing-requests",
                arm=arm,
                before_send=before_send,
            )
            def proxy_factory(
                *,
                origin: str,
                ledger: transaction.RequestLedger,
                selected_journal: DurableRequestJournal = journal,
            ) -> DurableTreatmentProxy:
                return DurableTreatmentProxy(
                    origin=origin,
                    ledger=ledger,
                    journal=selected_journal,
                )
            args = argparse.Namespace(**tx_args_base)
            observation_path = arm_root / "observer" / "continuity-materialization.json"
            result_code = transaction._run_transaction(
                args,
                evidence_root=arm_root,
                target_name=TARGET_ID,
                server_binary_override=Path(runtime_identity["server_binary"]),
                server_env=server_env,
                proxy_factory=proxy_factory,
                serve_runner_module="tools.v1_cache_correctness_qualification_serve",
                continuity_observation_path=observation_path,
                server_closure_gate=attest_server_process,
            )
            arm_summary = _read_json_object(arm_root / "transaction-summary.json")
            if server_process_state.get("latest_closure") is not None:
                arm_summary.setdefault("server", {})["loaded_library_closure"] = server_process_state[
                    "latest_closure"
                ]
                _atomic_json(arm_root / "transaction-summary.json", arm_summary)
            if arm == "reused" and int(arm_summary.get("server_launch_count", 0)) > 0:
                attempt_summary["later_arm_started"] = True
            arm_summary["durable_request_journal"] = journal.evidence()
            _atomic_json(arm_root / "durable-request-accounting.json", journal.evidence())
            attempt_summary["server_launch_count"] += int(arm_summary.get("server_launch_count", 0))
            attempt_summary["candidate_model_load_attempts"] += int(
                arm_summary.get("server_launch_count", 0)
            )
            ledger_path = arm_root / "provider-request-ledger.json"
            if ledger_path.is_file():
                provider_evidence = _read_json_object(ledger_path)
                calls = provider_evidence.get("calls", [])
                generation_count = sum(
                    1 for call in calls if isinstance(call, dict) and call.get("kind") == "generation"
                )
                count_count = sum(
                    1
                    for call in calls
                    if isinstance(call, dict) and call.get("kind") == "input_token_count"
                )
                attempt_summary["generation_request_count"] += generation_count
                attempt_summary["input_count_request_count"] += count_count
            attempt_summary["model_facing_post_count"] += journal.evidence()["durable_request_count"]
            attempt_summary["attempt_consumed"] = bool(attempt_summary["model_facing_post_count"])
            attempt_summary["arms"][arm] = {
                "exit_code": result_code,
                "summary_path": str(arm_root / "transaction-summary.json"),
                "phase": arm_summary.get("phase"),
                "disposition": arm_summary.get("disposition"),
                "durable_request_journal": journal.evidence(),
            }
            if result_code != 0 or arm_summary.get("disposition") != transaction.PHYSICAL_EVIDENCE_DISPOSITION:
                attempt_summary["state"] = "stopped_first_failure"
                attempt_summary["failure"] = arm_summary.get("failure") or {
                    "message": f"{arm} arm returned non-success disposition",
                    "exit_code": result_code,
                }
                if arm_index == 0:
                    attempt_summary["later_arm_started"] = False
                break
            _validate_arm_success(
                arm=arm,
                arm_root=arm_root,
                arm_summary=arm_summary,
                expected_server_binary=Path(runtime_identity["server_binary"]),
                expected_server_sha256=manifest["server"]["sha256"],
                expected_server_argv=expected_server_argv,
            )
            _seal_directory(arm_root)

        except Exception as exc:
            failed_journal = locals().get("journal")
            journal_evidence = failed_journal.evidence() if isinstance(failed_journal, DurableRequestJournal) and failed_journal.arm == arm else None
            attempt_summary["state"] = "stopped_first_failure"
            attempt_summary["failure"] = {"type": type(exc).__name__, "message": _bounded(str(exc))}
            attempt_summary["arms"].setdefault(arm, {"state": "stopped_first_failure", "durable_request_journal": journal_evidence})
            if arm_index == 0:
                attempt_summary["later_arm_started"] = False
            break

    if attempt_summary["state"] == "running":
        try:
            _validate_matched_arms(roots["cold"], roots["reused"])
            attempt_summary["state"] = "CACHE_CORRECTNESS_REPAIR_CUDA_QUALIFICATION_PASS"
        except Exception as exc:
            attempt_summary["state"] = "stopped_first_failure"
            attempt_summary["failure"] = {"type": type(exc).__name__, "message": _bounded(str(exc))}
    durable_records: list[dict[str, Any]] = []
    for arm in ARM_ORDER:
        arm_journal_root = roots[arm] / "model-facing-requests"
        if arm_journal_root.is_dir():
            durable_records.extend(_durable_records(arm_journal_root))
    attempt_summary["model_facing_post_count"] = len(durable_records)
    attempt_summary["generation_request_count"] = sum(
        record.get("request_kind") == "generation" for record in durable_records
    )
    attempt_summary["input_count_request_count"] = sum(
        record.get("request_kind") == "input_token_count" for record in durable_records
    )
    attempt_summary["attempt_consumed"] = bool(durable_records)
    arm_summaries = [
        _read_json_object(roots[arm] / "transaction-summary.json")
        for arm in ARM_ORDER
        if (roots[arm] / "transaction-summary.json").is_file()
    ]
    attempt_summary["server_launch_count"] = sum(
        int(item.get("server_launch_count", 0)) for item in arm_summaries
    )
    attempt_summary["candidate_model_load_attempts"] = attempt_summary["server_launch_count"]
    attempt_summary["arms_completed"] = list(attempt_summary["arms"])
    attempt_summary["maximums"] = {
        "candidate_model_loads": 2,
        "generation_requests": GENERATION_MAXIMUM,
        "input_count_requests": INPUT_COUNT_MAXIMUM,
        "model_facing_posts": MODEL_FACING_MAXIMUM,
    }
    attempt_summary["product_cache_policy"] = "disabled"
    for arm in ARM_ORDER:
        arm_root = roots[arm]
        if arm_root.is_dir():
            _seal_directory(arm_root)
            verify_evidence_manifest(arm_root)
    _atomic_json(roots["output"] / "attempt-summary.json", attempt_summary)
    _seal_directory(roots["output"])
    verify_evidence_manifest(roots["output"])
    return 0 if attempt_summary["state"] == "CACHE_CORRECTNESS_REPAIR_CUDA_QUALIFICATION_PASS" else 2


def _check_send_authority(
    *,
    authority_comment_id: int,
    descriptor_path: Path,
    descriptor_sha256: str,
    expected_head: str,
    repo_root: Path,
) -> None:
    if _sha256_file(descriptor_path) != descriptor_sha256:
        raise QualificationTargetError("descriptor changed after freeze")
    verify_exact_execution_authority(
        comment_id=authority_comment_id,
        descriptor_path=descriptor_path,
        descriptor_sha256=descriptor_sha256,
    )
    verify_live_v1_head(expected_head, repo_root)


def _run_candidate_static_checks(manifest: dict[str, Any], evidence_root: Path) -> None:
    _verify_candidate_test_binaries(manifest)
    build_root = Path(manifest["build"]["build_root"]).resolve()
    test_environment = candidate_runtime.candidate_build_environment()
    test_environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [str((build_root / "bin").resolve()), "/usr/local/cuda-12.8/lib64", "/usr/lib/wsl/lib"]
    )
    ctest_path = shutil.which("ctest", path=test_environment["PATH"])
    if ctest_path is None:
        raise QualificationTargetError("pinned Linux CUDA environment cannot locate CTest")
    command = [
        ctest_path,
        "--test-dir",
        str(build_root),
        "--output-on-failure",
        "--verbose",
        "-R",
        "^(test-chat|test-batch-alloc|test-arg-parser)$",
    ]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env=test_environment,
    )
    payload = {
        "format_version": 1,
        "non_generative": True,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }
    _atomic_json(evidence_root / "candidate-source-regression.json", payload)
    if completed.returncode != 0:
        raise QualificationTargetError("frozen candidate source regression failed before model load")
    required_restore_control = _validate_required_history_restore_control(completed.stdout)
    payload["required_history_restore_control"] = {
        "source_test": "tests/test-chat.cpp::test_prompt_checkpoint_restore",
        "missing_history_cases": list(required_restore_control),
        "passed": True,
    }
    _atomic_json(evidence_root / "candidate-source-regression.json", payload)


def _validate_required_history_restore_control(output: str) -> tuple[str, str]:
    markers = (
        "next=8 min=1 swa=16 new=1 restore=1",
        "next=24 min=9 swa=16 new=1 restore=1",
    )
    if any(marker not in output for marker in markers):
        raise QualificationTargetError(
            "candidate source regression did not prove missing required history still restores"
        )
    return markers


def _verify_loaded_library_closure(
    *,
    process: subprocess.Popen[str],
    binary: Path,
    manifest: dict[str, Any],
    require_cuda: bool = False,
    previous_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pid = process.pid
    maps_path = Path(f"/proc/{pid}/maps")
    if not maps_path.is_file():
        raise QualificationTargetError("cannot inspect candidate server loaded-library closure")
    roots = manifest["build"]["shared_libraries"]
    expected_paths: set[str] = set()
    expected_records: dict[str, dict[str, Any]] = {}

    def add_expected_file(path_value: Any, digest: Any, identity: Any) -> None:
        if not isinstance(path_value, str) or not isinstance(digest, str) or not isinstance(identity, dict):
            raise QualificationTargetError("candidate manifest has an incomplete sealed library identity")
        resolved = str(Path(path_value).resolve())
        if resolved != path_value:
            raise QualificationTargetError("candidate manifest library path is not canonical")
        existing = expected_records.get(resolved)
        record = {"sha256": digest, "identity": identity}
        if existing is not None and existing != record:
            raise QualificationTargetError(f"candidate manifest conflicts on one file identity: {resolved}")
        expected_records[resolved] = record
        expected_paths.add(resolved)

    binary_path = str(Path(binary).resolve())
    add_expected_file(binary_path, manifest["server"].get("sha256"), manifest["server"].get("identity"))
    for root, record in roots.items():
        add_expected_file(root, record.get("sha256"), record.get("identity"))
        dependencies = record.get("dependencies")
        if not isinstance(dependencies, dict):
            raise QualificationTargetError("candidate manifest dependency closure is malformed")
        for value in dependencies.values():
            if isinstance(value, dict):
                add_expected_file(value.get("path"), value.get("sha256"), value.get("identity"))

    wsl_driver_closure = manifest["build"].get("wsl_cuda_driver_closure")
    accepted_wsl_paths: set[str] = set()
    if wsl_driver_closure is not None:
        if (
            not isinstance(wsl_driver_closure, dict)
            or wsl_driver_closure.get("contract") != "wsl-cuda-driver-shim-and-package-payload-v1"
            or wsl_driver_closure.get("logical_dependency") != "libcuda.so.1"
        ):
            raise QualificationTargetError("candidate WSL CUDA driver closure contract is malformed")
        accepted_objects = wsl_driver_closure.get("accepted_mapped_objects")
        if not isinstance(accepted_objects, list) or not accepted_objects:
            raise QualificationTargetError("candidate WSL CUDA driver object set is empty")
        for item in accepted_objects:
            if not isinstance(item, dict) or item.get("path") != item.get("realpath"):
                raise QualificationTargetError("candidate WSL CUDA mapped object is not an exact regular path")
            add_expected_file(item.get("path"), item.get("sha256"), item.get("identity"))
            accepted_wsl_paths.add(item["path"])

    loaded_paths: set[str] = set()
    mapped_file_ids: dict[str, set[tuple[int, int, int]]] = {}
    for line in maps_path.read_text(encoding="utf-8").splitlines():
        mapped = _parse_mapped_file_record(line)
        if mapped is None:
            continue
        path, map_identity, deleted = mapped
        if deleted:
            if ".so" in Path(path).name or Path(path).name == binary.name:
                raise QualificationTargetError("candidate server mapped a deleted executable or library")
            continue
        normalized = path
        if normalized in expected_paths or ".so" in Path(normalized).name or normalized == str(binary.resolve()):
            if normalized not in expected_paths:
                raise QualificationTargetError(f"candidate server mapped an undeclared library: {normalized}")
            loaded_paths.add(normalized)
            mapped_file_ids.setdefault(normalized, set()).add(map_identity)
    if binary_path not in loaded_paths:
        raise QualificationTargetError("candidate server binary is absent from its process maps")
    previous_identities = (
        previous_attestation.get("file_identities", {})
        if isinstance(previous_attestation, dict)
        else {}
    )
    if isinstance(previous_attestation, dict):
        previous_paths = set(previous_attestation.get("loaded_libraries", {}))
        if previous_paths != loaded_paths:
            raise QualificationTargetError("candidate server loaded-library mapping changed after attestation")
    loaded: dict[str, str] = {}
    file_identities: dict[str, dict[str, int]] = {}
    for path in sorted(loaded_paths):
        expected_record = expected_records.get(path)
        if expected_record is None:
            raise QualificationTargetError(f"loaded library is outside frozen closure: {path}")
        if path in accepted_wsl_paths:
            lexical_path = Path(path)
            try:
                lexical_identity = lexical_path.lstat()
                canonical_path = lexical_path.resolve(strict=True)
            except OSError as exc:
                raise QualificationTargetError(
                    f"sealed WSL CUDA library path is unavailable: {path}"
                ) from exc
            if not stat.S_ISREG(lexical_identity.st_mode) or str(canonical_path) != path:
                raise QualificationTargetError(
                    f"sealed WSL CUDA library path is no longer a direct regular file: {path}"
                )
        try:
            identity = candidate_runtime._stat_identity(Path(path))
        except candidate_runtime.RuntimePinError as exc:
            raise QualificationTargetError(f"sealed candidate library is unavailable: {path}") from exc
        if identity != expected_record["identity"]:
            raise QualificationTargetError(f"sealed candidate library object identity changed: {path}")
        expected_map_identity = (
            os.major(identity["device"]),
            os.minor(identity["device"]),
            identity["inode"],
        )
        if mapped_file_ids.get(path) != {expected_map_identity}:
            raise QualificationTargetError(
                f"candidate server mapping no longer names the attested file identity: {path}"
            )
        prior_identity = previous_identities.get(path)
        if prior_identity is not None and prior_identity != identity:
            raise QualificationTargetError(f"candidate server library identity drifted between POSTs: {path}")
        digest = _sha256_file(Path(path))
        if digest.removeprefix("sha256:") != expected_record["sha256"]:
            raise QualificationTargetError(f"loaded library digest is outside frozen closure: {path}")
        loaded[path] = digest
        file_identities[path] = identity
    if require_cuda:
        _require_cuda_library_set(list(loaded))
        if wsl_driver_closure is not None:
            if not isinstance(wsl_driver_closure, dict):
                raise QualificationTargetError("candidate WSL CUDA driver package closure is malformed")
            driver_package = wsl_driver_closure.get("driver_package")
            payload = driver_package.get("payload") if isinstance(driver_package, dict) else None
            payload_path = payload.get("path") if isinstance(payload, dict) else None
            if (
                not isinstance(payload_path, str)
                or payload_path not in accepted_wsl_paths
                or payload_path not in loaded_paths
                or expected_records.get(payload_path)
                != {"sha256": payload.get("sha256"), "identity": payload.get("identity")}
            ):
                raise QualificationTargetError("candidate server did not map its sealed WSL CUDA driver payload")
    return {
        "pid": pid,
        "process_start_ticks": _process_start_ticks(pid),
        "loaded_libraries": dict(sorted(loaded.items())),
        "file_identities": file_identities,
        "wsl_cuda_driver_objects": sorted(loaded_paths & accepted_wsl_paths),
        "loaded_closure_matches_manifest": True,
        "binary_sha256": f"sha256:{manifest['server']['sha256']}",
    }


def _parse_mapped_file_record(
    line: str,
) -> tuple[str, tuple[int, int, int], bool] | None:
    fields = line.split()
    if len(fields) < 6 or not fields[5].startswith("/"):
        return None
    raw_path = " ".join(fields[5:])
    deleted = raw_path.endswith(" (deleted)")
    if deleted:
        raw_path = raw_path[: -len(" (deleted)")]
    try:
        major_raw, minor_raw = fields[3].split(":", maxsplit=1)
        identity = (
            int(major_raw, 16),
            int(minor_raw, 16),
            int(fields[4], 10),
        )
    except (IndexError, ValueError) as exc:
        raise QualificationTargetError("candidate process map file identity is malformed") from exc
    return raw_path, identity, deleted


def _require_cuda_library_set(loaded_paths: list[str]) -> None:
    basenames = {Path(path).name for path in loaded_paths}
    required_cuda_libraries = (
        "libggml-cuda.so",
        "libcudart.so",
        "libcublas.so",
        "libcuda.so",
    )
    missing = [
        required
        for required in required_cuda_libraries
        if not any(name.startswith(required) for name in basenames)
    ]
    if missing:
        raise QualificationTargetError(
            f"candidate runtime did not map its required CUDA library closure: {missing}"
        )


def _process_start_ticks(pid: int) -> int:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields_after_comm = raw.rsplit(")", 1)[1].split()
        return int(fields_after_comm[19])
    except (OSError, IndexError, ValueError) as exc:
        raise QualificationTargetError("candidate server process start identity is unavailable") from exc


def _verify_candidate_process_identity(
    *,
    process: Any,
    binary: Any,
    manifest: dict[str, Any],
    expected_argv: list[str],
    expected_environment: dict[str, str],
    previous_attestation: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(process, subprocess.Popen) or not isinstance(binary, Path):
        raise QualificationTargetError(
            "candidate server process was not attested before a model-facing POST"
        )
    if process.poll() is not None:
        raise QualificationTargetError("candidate server exited before a model-facing POST")
    expected_binary = Path(manifest["server"]["path"]).resolve()
    if binary.resolve() != expected_binary:
        raise QualificationTargetError(
            "candidate server process binary differs from its frozen manifest"
        )
    _verify_candidate_server_controls(
        process=process,
        expected_argv=expected_argv,
        expected_environment=expected_environment,
    )

    source_checkout = Path(manifest["build"]["source_output"]).resolve()
    try:
        candidate_runtime.verify_qualification_source_tree(source_checkout)
    except candidate_runtime.RuntimePinError as exc:
        raise QualificationTargetError(
            "candidate source tree changed after descriptor qualification"
        ) from exc
    return _verify_loaded_library_closure(
        process=process,
        binary=binary,
        manifest=manifest,
        require_cuda=True,
        previous_attestation=previous_attestation,
    )


def _expected_server_argv(
    *,
    manifest: dict[str, Any],
    port: int,
    arm_root: Path,
) -> list[str]:
    return [
        item.replace("<descriptor-port>", str(port)).replace(
            "<arm-evidence-root>", str(arm_root.resolve())
        )
        for item in manifest["server"]["startup_argv_template"]
    ]


def _verify_candidate_server_controls(
    *,
    process: subprocess.Popen[str],
    expected_argv: list[str],
    expected_environment: dict[str, str],
) -> None:
    pid = process.pid
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    environment_path = Path(f"/proc/{pid}/environ")
    if not cmdline_path.is_file() or not environment_path.is_file():
        raise QualificationTargetError("candidate server process controls are not inspectable")
    actual_argv = [
        item.decode("utf-8", errors="strict")
        for item in cmdline_path.read_bytes().split(b"\0")
        if item
    ]
    if actual_argv != expected_argv:
        raise QualificationTargetError("candidate server argv differs from the frozen CUDA startup")
    actual_environment: dict[str, str] = {}
    for item in environment_path.read_bytes().split(b"\0"):
        if not item:
            continue
        name, separator, value = item.decode("utf-8", errors="strict").partition("=")
        if separator:
            actual_environment[name] = value
    if actual_environment != expected_environment:
        raise QualificationTargetError("candidate server environment differs from the frozen closure")
    if any(
        name.startswith("LLAMA_ARG_") or name.startswith("GGML_")
        for name in actual_environment
    ):
        raise QualificationTargetError("candidate server inherited an unreviewed llama.cpp override")


def _validate_provider_request_order(observed: list[tuple[Any, Any, Any]]) -> None:
    if observed != list(transaction.CANONICAL_PROVIDER_SEQUENCE):
        raise QualificationTargetError("arm provider request order differs from frozen topology")


def _validate_arm_success(
    *,
    arm: str,
    arm_root: Path,
    arm_summary: dict[str, Any],
    expected_server_binary: Path,
    expected_server_sha256: str,
    expected_server_argv: list[str],
) -> None:
    if arm_summary.get("target") != TARGET_ID:
        raise QualificationTargetError("transaction summary target identity mismatch")
    cleanup = arm_summary.get("cleanup")
    if not isinstance(cleanup, dict) or not (
        cleanup.get("all_owned_processes_terminated") is True
        and cleanup.get("proxy_closed") is True
        and cleanup.get("errors") == []
    ):
        raise QualificationTargetError("arm did not fully terminate its owned server and proxy")
    server = arm_summary.get("server")
    if not isinstance(server, dict) or arm_summary.get("server_launch_count") != 1:
        raise QualificationTargetError("arm server identity is missing")
    if Path(server.get("binary", "")).resolve() != expected_server_binary.resolve():
        raise QualificationTargetError("arm launched a binary outside the frozen CUDA candidate")
    if server.get("loaded_library_closure", {}).get("binary_sha256", "").removeprefix(
        "sha256:"
    ) != expected_server_sha256:
        raise QualificationTargetError("loaded candidate executable hash differs from the frozen manifest")
    try:
        launch_tokens = shlex.split(str(server.get("launch_command", "")))
    except ValueError as exc:
        raise QualificationTargetError("candidate startup argv is malformed") from exc
    if launch_tokens != expected_server_argv or "--swa-full" in launch_tokens:
        raise QualificationTargetError("candidate startup argv changed frozen runtime geometry")
    closure = server.get("loaded_library_closure")
    if not isinstance(closure, dict) or closure.get("loaded_closure_matches_manifest") is not True:
        raise QualificationTargetError("candidate server loaded-library closure was not attested")
    loaded_libraries = closure.get("loaded_libraries")
    if not isinstance(loaded_libraries, dict):
        raise QualificationTargetError("candidate server omitted its loaded-library identities")
    _require_cuda_library_set(list(loaded_libraries))
    runtime_config = arm_summary.get("runtime_config", {}).get("mapping", {})
    cache_policy = (
        runtime_config.get("provider", {})
        .get("llama_cpp", {})
        .get("cache_policy")
    )
    if cache_policy != transaction.LLAMA_CPP_CACHE_POLICY_DISABLED:
        raise QualificationTargetError("RelayLM product cache policy is not disabled")
    if arm_summary.get("semantic_generation_count") != 4:
        raise QualificationTargetError("arm did not complete exactly four generations")
    if arm_summary.get("semantic_retry_count") != 0:
        raise QualificationTargetError("arm recorded a semantic retry")
    provider = _read_json_object(arm_root / "provider-request-ledger.json")
    calls = provider.get("calls")
    if not isinstance(calls, list) or len(calls) != GENERATION_MAXIMUM // 2 + INPUT_COUNT_MAXIMUM // 2:
        raise QualificationTargetError("arm model-facing request ledger count is not 16")
    observed = [
        (call.get("kind"), call.get("generation_index"), call.get("framing_role"))
        for call in calls
        if isinstance(call, dict)
    ]
    _validate_provider_request_order(observed)
    for call in calls:
        controls = call.get("controls") if isinstance(call, dict) else None
        if not isinstance(controls, dict) or (
            controls.get("temperature") != 0
            or controls.get("top_p") != 1
            or controls.get("max_tokens") != 256
            or controls.get("cache_prompt") is not False
            or controls.get("reasoning_effort") != "none"
        ):
            raise QualificationTargetError("a product generation/count control differs from frozen settings")
    generations = [call for call in calls if call.get("kind") == "generation"]
    if len(generations) != 4:
        raise QualificationTargetError("arm generation request count is not four")
    for call, expected_phase in zip(generations, REQUEST_ORDER, strict=True):
        if call.get("phase") != expected_phase:
            raise QualificationTargetError("buffered/streaming Pass1/Pass2 order mismatch")
        controls = call.get("controls")
        response = call.get("response")
        if not isinstance(controls, dict) or not isinstance(response, dict):
            raise QualificationTargetError("generation evidence is incomplete")
        if (
            controls.get("cache_prompt") is not False
            or controls.get("reasoning_effort") != "none"
            or controls.get("temperature") != 0
            or controls.get("top_p") != 1
            or controls.get("max_tokens") != 256
            or controls.get("seed") not in (None, "absent")
        ):
            raise QualificationTargetError("product generation controls differ from frozen settings")
        if response.get("status") != 200 or response.get("finish_reason") != "stop":
            raise QualificationTargetError("generation did not finish with native finish_reason=stop")
        if expected_phase.endswith("pass2"):
            structured = response.get("native_structured_output")
            if not isinstance(structured, dict) or not (
                structured.get("valid_json_object") is True
                and structured.get("required_keys_present") is True
            ):
                raise QualificationTargetError("native Pass2 structured output did not parse")

    durable_root = arm_root / "model-facing-requests"
    records = _durable_records(durable_root)
    if len(records) != INPUT_COUNT_MAXIMUM // 2 + GENERATION_MAXIMUM // 2:
        raise QualificationTargetError("durable request record count is not 16")
    for record, call in zip(records, calls, strict=True):
        product = (durable_root / f"{record['call_index']:02d}-{record['request_kind']}" / "product-request.body").read_bytes()
        upstream = (durable_root / f"{record['call_index']:02d}-{record['request_kind']}" / "upstream-request.body").read_bytes()
        if _sha256_bytes(product) != record["product_body_sha256"] or _sha256_bytes(upstream) != record["upstream_body_sha256"]:
            raise QualificationTargetError("durable request bytes differ from sealed hashes")
        treatment = record["treatment"]
        if call["kind"] == "input_token_count":
            if product != upstream or treatment.get("applied") is not False:
                raise QualificationTargetError("cache treatment changed an input-token request")
        elif arm == "cold":
            if product != upstream or treatment.get("applied") is not False:
                raise QualificationTargetError("cold arm did not stay cache-off")
        else:
            if treatment.get("applied") is not True:
                raise QualificationTargetError("reused arm omitted cache-on treatment")
            delta = treatment.get("normalized_delta")
            if not isinstance(delta, dict) or delta.get("changed_keys") != ["cache_prompt"]:
                raise QualificationTargetError("reused arm treatment changed fields beyond cache_prompt")

    trace = _parse_runtime_trace((arm_root / "llama-server.log").read_text(encoding="utf-8", errors="replace"))
    if len(trace["decisions"]) != 4 or len(trace["results"]) != 4 or len(trace["prompt_results"]) != 4:
        raise QualificationTargetError("candidate runtime trace is incomplete for the four generations")
    if any(item["slot_id"] != 0 or item["n_swa"] <= 0 for item in trace["decisions"]):
        raise QualificationTargetError("runtime did not use the one live single-slot SWA path")
    first_decision, first_result, first_prompt_result = (
        trace["decisions"][0],
        trace["results"][0],
        trace["prompt_results"][0],
    )
    if (
        first_decision.get("decision_state") != "empty-slot"
        or first_decision["lcp"] != 0
        or first_decision["n_past_before"] != 0
        or first_result["outcome"] != "empty-slot-full-prompt"
        or first_result["selected_checkpoint"] != "NONE"
        or first_result["n_past_after"] != 0
        or first_prompt_result["cache_n"] != 0
        or first_prompt_result["prompt_eval_tokens"] != first_prompt_result["input_tokens"]
    ):
        raise QualificationTargetError("first generation did not prove a fresh empty slot and full prompt eval")
    if arm == "reused":
        if any(item["cache_n"] <= 0 for item in trace["prompt_results"][1:]):
            raise QualificationTargetError("applicable cache-on cells did not reuse prompt tokens")
        if not any(
            decision["live_pos_min"] == decision["pos_min_thold"]
            and result["outcome"] == "resident-prefix-retained"
            and result["selected_checkpoint"] == "NONE"
            and result["n_past_after"] == decision["n_past_before"]
            for decision, result in zip(trace["decisions"], trace["results"], strict=True)
        ):
            raise QualificationTargetError("repaired resident-SWA equality boundary was not observed")
    elif any(item["cache_n"] != 0 for item in trace["prompt_results"]):
        raise QualificationTargetError("cold/cache-off arm unexpectedly reports reused prompt tokens")

    observables: list[dict[str, Any]] = []
    request_records_by_index = {record["call_index"]: record for record in records}
    generation_records = [record for record in records if record["request_kind"] == "generation"]
    continuity = _read_json_object(arm_root / "continuity-materialization.json")
    continuity_requests = continuity.get("requests")
    if not isinstance(continuity_requests, list) or len(continuity_requests) != 2:
        raise QualificationTargetError("public State/Continuity observations are incomplete")
    public_by_kind = {
        "buffered": continuity_requests[0],
        "streaming": continuity_requests[1],
    }
    for record, decision, result, prompt_result, generation in zip(
        generation_records,
        trace["decisions"],
        trace["results"],
        trace["prompt_results"],
        generations,
        strict=True,
    ):
        kind = "buffered" if record["generation_phase"].startswith("buffered_") else "streaming"
        public_response = public_by_kind[kind]
        profile_name = "installed-buffered" if kind == "buffered" else "installed-streaming"
        profile_observation = public_response.get("profiles", {}).get(profile_name, {})
        observables.append(
            {
                "request_id": request_records_by_index[record["call_index"]]["request_id"],
                "request_order": record["call_index"],
                "phase": record["generation_phase"],
                "llama_task_id": decision["task_id"],
                "slot_id": decision["slot_id"],
                "input_token_count": decision["input_tokens"],
                "lcp": decision["lcp"],
                "live_pos_min": decision["live_pos_min"],
                "live_pos_max": decision["live_pos_max"],
                "effective_n_swa": decision["n_swa"],
                "pos_min_thold": decision["pos_min_thold"],
                "candidate_checkpoint_set": decision.get("candidate_checkpoints", []),
                "selected_checkpoint": result["selected_checkpoint"],
                "selected_checkpoint_pos_min": result["selected_pos_min"],
                "selected_checkpoint_pos_max": result["selected_pos_max"],
                "n_past_before_decision": decision["n_past_before"],
                "n_past_after_decision": result["n_past_after"],
                "prompt_eval_token_count": prompt_result["prompt_eval_tokens"],
                "cache_n_reused": prompt_result["cache_n"],
                "finish_reason": generation["response"]["finish_reason"],
                "native_structured_output": generation["response"].get("native_structured_output"),
                "provider_parse_result": {
                    "public_response_http_status": 200,
                    "pass2_schema_parse_completed": (
                        generation["response"].get("native_structured_output", {}).get("valid_json_object") is True
                        if record["generation_phase"].endswith("pass2")
                        else None
                    ),
                },
                "state_materialization": {
                    "state_file_present": profile_observation.get("state_file_present"),
                    "state_schema_valid": profile_observation.get("state_schema_valid"),
                    "state_record_count": profile_observation.get("state_record_count"),
                    "event_record_count": profile_observation.get("event_record_count"),
                },
                "continuity_materialization": profile_observation.get("continuity"),
            }
        )
    _atomic_json(
        arm_root / "qualification-observables.json",
        {"format_version": 1, "arm": arm, "generations": observables},
    )

    if continuity.get("request_count") != PUBLIC_COMPLETION_MAXIMUM // 2:
        raise QualificationTargetError("public state/continuity observer did not see both completions")
    if continuity.get("semantic_payloads_serialized") is not False:
        raise QualificationTargetError("continuity observer exposed semantic payloads")
    for request in continuity.get("requests", []):
        if request.get("status_code") != 200:
            raise QualificationTargetError("RelayLM provider parse/materialization response failed")
        for observed_profile in request.get("profiles", {}).values():
            state = observed_profile.get("state_schema_valid") is True
            continuity_state = observed_profile.get("continuity")
            if not state or not isinstance(continuity_state, dict) or not continuity_state.get("within_bound"):
                raise QualificationTargetError("State or in-process Continuity materialization is invalid")
    journal = _read_json_object(arm_root / "durable-request-accounting.json")
    if journal.get("durable_request_count") != 16 or journal.get("retry_count") != 0:
        raise QualificationTargetError("durable consumption accounting is incomplete")
    if journal.get("replay_count") or journal.get("reseed_count") or journal.get("fallback_count"):
        raise QualificationTargetError("forbidden retry/replay/reseed/fallback was observed")


def _validate_matched_arms(cold_root: Path, reused_root: Path) -> None:
    cold_summary = _read_json_object(cold_root / "transaction-summary.json")
    reused_summary = _read_json_object(reused_root / "transaction-summary.json")
    cold_closure = cold_summary.get("server", {}).get("loaded_library_closure", {})
    reused_closure = reused_summary.get("server", {}).get("loaded_library_closure", {})
    if (
        cold_summary.get("server_launch_count") != 1
        or reused_summary.get("server_launch_count") != 1
        or not isinstance(cold_closure, dict)
        or not isinstance(reused_closure, dict)
        or (cold_closure.get("pid"), cold_closure.get("process_start_ticks"))
        == (reused_closure.get("pid"), reused_closure.get("process_start_ticks"))
    ):
        raise QualificationTargetError(
            "cold and reused arms did not use distinct, fresh single-server lifetimes"
        )
    cold_records = _durable_records(cold_root / "model-facing-requests")
    reused_records = _durable_records(reused_root / "model-facing-requests")
    if len(cold_records) != len(reused_records):
        raise QualificationTargetError("cold and reused arms have different request counts")
    for cold, reused in zip(cold_records, reused_records, strict=True):
        if (
            cold["request_kind"] != reused["request_kind"]
            or cold.get("generation_phase") != reused.get("generation_phase")
            or cold.get("logical_operation_index") != reused.get("logical_operation_index")
        ):
            raise QualificationTargetError("cold/reused request identities are not mechanically matched")
        cold_dir = cold_root / "model-facing-requests" / f"{cold['call_index']:02d}-{cold['request_kind']}"
        reused_dir = reused_root / "model-facing-requests" / f"{reused['call_index']:02d}-{reused['request_kind']}"
        cold_body = (cold_dir / "product-request.body").read_bytes()
        reused_body = (reused_dir / "product-request.body").read_bytes()
        if _normalize_dynamic_pass2(cold_body, cold.get("generation_phase")) != _normalize_dynamic_pass2(
            reused_body, reused.get("generation_phase")
        ):
            raise QualificationTargetError("cold/reused product request changed outside Pass1-dependent Pass2 content")
        cold_upstream = (cold_dir / "upstream-request.body").read_bytes()
        reused_upstream = (reused_dir / "upstream-request.body").read_bytes()
        if cold["request_kind"] == "generation":
            cold_payload = transaction._parse_json_object(cold_upstream, "cold upstream")
            reused_payload = transaction._parse_json_object(reused_upstream, "reused upstream")
            if cold_payload.get("cache_prompt") is not False or reused_payload.get("cache_prompt") is not True:
                raise QualificationTargetError("arm treatment delta is not exactly cache_prompt false-to-true")
            if _normalized_generation_payload(cold_payload) != _normalized_generation_payload(reused_payload):
                raise QualificationTargetError("cache-on arm changed an upstream generation field beyond treatment/state")
        elif _normalize_dynamic_pass2(cold_upstream, cold.get("generation_phase")) != _normalize_dynamic_pass2(
            reused_upstream, reused.get("generation_phase")
        ):
            raise QualificationTargetError("input-count treatment differs beyond the Pass1-dependent Pass2 input")

    cold_observables = _read_json_object(cold_root / "qualification-observables.json")["generations"]
    reused_observables = _read_json_object(reused_root / "qualification-observables.json")["generations"]
    for index, (cold, reused) in enumerate(
        zip(cold_observables, reused_observables, strict=True)
    ):
        if cold.get("phase") != reused.get("phase"):
            raise QualificationTargetError("cold/reused observable order is not matched")
        if index == 0:
            if (
                cold["cache_n_reused"] != 0
                or reused["cache_n_reused"] != 0
                or cold["prompt_eval_token_count"] != cold["input_token_count"]
                or reused["prompt_eval_token_count"] != reused["input_token_count"]
            ):
                raise QualificationTargetError(
                    "first generation did not begin from an empty slot in both arms"
                )
            continue
        if cold["cache_n_reused"] != 0 or cold["prompt_eval_token_count"] != cold["input_token_count"]:
            raise QualificationTargetError("cold arm did not process its full prompt")
        if (
            reused["cache_n_reused"] <= 0
            or reused["prompt_eval_token_count"] >= reused["input_token_count"]
        ):
            raise QualificationTargetError(
                "cache-on arm did not reduce processed prompt tokens for a reusable prefix"
            )


def _normalized_generation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    normalized.pop("cache_prompt", None)
    if isinstance(normalized.get("messages"), list):
        for message in normalized["messages"]:
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                message["content"] = _replace_pass1_dependency(message["content"])
    return normalized


def _normalize_dynamic_pass2(body: bytes, phase: object) -> bytes:
    payload = transaction._parse_json_object(body, "matched arm product request")
    if isinstance(phase, str) and phase.endswith("pass2"):
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise QualificationTargetError("Pass2 request is missing messages")
        dynamic_count = 0
        for message in messages:
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                message["content"], count = _replace_pass1_dependency_with_count(message["content"])
                dynamic_count += count
        if dynamic_count > 1 or (dynamic_count == 0 and not transaction._is_framing_payload(payload)):
            raise QualificationTargetError("Pass2 request does not have one explicit Pass1 dependency")
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _contains_pair(tokens: list[str], key: str, value: str) -> bool:
    try:
        index = tokens.index(key)
    except ValueError:
        return False
    return index + 1 < len(tokens) and tokens[index + 1] == value


def _replace_pass1_dependency(value: str) -> str:
    normalized, count = _replace_pass1_dependency_with_count(value)
    return normalized if count else value


def _replace_pass1_dependency_with_count(value: str) -> tuple[str, int]:
    pattern = re.compile(r"<PASS_1_RESPONSE_JSON>\n(.*?)\n</PASS_1_RESPONSE_JSON>", re.DOTALL)
    matches = list(pattern.finditer(value))
    if len(matches) != 1:
        return value, 0
    match = matches[0]
    try:
        dependency = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise QualificationTargetError("Pass1-dependent Pass2 input is malformed") from exc
    if not isinstance(dependency, dict) or set(dependency) != {"content"} or not isinstance(
        dependency["content"], str
    ):
        raise QualificationTargetError("Pass2 dynamic dependency shape changed")
    replacement = '<PASS_1_RESPONSE_JSON>\n{"content":"<PASS1_OUTPUT>"}\n</PASS_1_RESPONSE_JSON>'
    return value[: match.start()] + replacement + value[match.end() :], 1


def _parse_runtime_trace(log_text: str) -> dict[str, list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    prompt_results: list[dict[str, Any]] = []
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for line in log_text.splitlines():
        if "3013 reuse-decision " in line:
            decisions.append(_parse_key_value_record(line.split("3013 reuse-decision ", 1)[1]))
        elif "3013 reuse-result " in line:
            results.append(_parse_key_value_record(line.split("3013 reuse-result ", 1)[1]))
        elif "3013 prompt-result " in line:
            prompt_results.append(_parse_key_value_record(line.split("3013 prompt-result ", 1)[1]))
        elif "3013 checkpoint-candidate " in line:
            item = _parse_key_value_record(line.split("3013 checkpoint-candidate ", 1)[1])
            key = (str(item.get("task_id")), str(item.get("slot_id")))
            candidates.setdefault(key, []).append(item)
    for collection in (decisions, results, prompt_results):
        for item in collection:
            for key in (
                "task_id",
                "slot_id",
                "input_tokens",
                "lcp",
                "live_pos_min",
                "live_pos_max",
                "n_swa",
                "pos_min_thold",
                "n_past_before",
                "n_past_after",
                "prompt_eval_tokens",
                "cache_n",
                "index",
                "pos_min",
                "pos_max",
                "n_tokens",
            ):
                if key in item:
                    try:
                        item[key] = int(item[key])
                    except (TypeError, ValueError) as exc:
                        raise QualificationTargetError("malformed integer in #3013 runtime trace") from exc
    for decision in decisions:
        key = (str(decision.get("task_id")), str(decision.get("slot_id")))
        decision["candidate_checkpoints"] = candidates.get(key, [])
    return {"decisions": decisions, "results": results, "prompt_results": prompt_results}


def _parse_key_value_record(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for token in text.strip().split():
        key, separator, value = token.partition("=")
        if separator:
            result[key] = value
    return result


def _durable_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for directory in sorted(root.iterdir()):
        record_path = directory / "durable-record.json"
        if not record_path.is_file():
            continue
        record = _read_json_object(record_path)
        if record.get("durable_before_send") is not True:
            raise QualificationTargetError("request record does not prove durability before send")
        records.append(record)
    return records


def _candidate_server_environment(manifest: dict[str, Any]) -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TZ")
        if name in os.environ
    }
    build_bin = str(Path(manifest["build"]["build_root"]).resolve() / "bin")
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [build_bin, "/usr/local/cuda-12.8/lib64", "/usr/lib/wsl/lib"]
    )
    environment["CUDA_HOME"] = "/usr/local/cuda-12.8"
    environment["CUDA_PATH"] = "/usr/local/cuda-12.8"
    gpu_line = manifest["build"]["gpu"].splitlines()[0]
    fields = [field.strip() for field in gpu_line.split(",")]
    if len(fields) >= 2:
        environment["CUDA_VISIBLE_DEVICES"] = fields[1]
    return environment


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationTargetError(f"could not read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise QualificationTargetError(f"JSON object required: {path}")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _replace_json_durable(path, value)


def _replace_json_durable(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = _canonical_json(value)
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _write_new_file(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(fd, payload[offset:])
        if written <= 0:
            raise OSError("short write while sealing qualification evidence")
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _seal_directory(root: Path) -> dict[str, Any]:
    manifest_path = root / "evidence-manifest.json"
    if manifest_path.exists():
        raise QualificationTargetError("evidence root is already sealed")
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        files[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    payload = {"format_version": 1, "files": files, "file_count": len(files)}
    _atomic_json(manifest_path, payload)
    _fsync_directory(root)
    return payload


def verify_evidence_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "evidence-manifest.json"
    manifest = _read_json_object(manifest_path)
    expected = manifest.get("files")
    if not isinstance(expected, dict):
        raise QualificationTargetError("sealed evidence manifest lacks file entries")
    actual: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        actual[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    if actual != expected or manifest.get("file_count") != len(actual):
        raise QualificationTargetError("sealed evidence tree no longer matches its manifest")
    return manifest


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _deep_string_values(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        result: set[str] = set()
        for key, nested in value.items():
            if isinstance(key, str):
                result.add(key)
            result.update(_deep_string_values(nested))
        return result
    if isinstance(value, list):
        result = set()
        for nested in value:
            result.update(_deep_string_values(nested))
        return result
    return set()


def _git(repo_root: Path, *args: str) -> str:
    return _run_text(["git", "-C", str(repo_root), *args], cwd=repo_root)


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise QualificationTargetError(
            f"command failed: {' '.join(command)}: {(completed.stderr or completed.stdout).strip()}"
        )
    return completed.stdout.strip()


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _bounded(value: str) -> str:
    return value[:512]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor", required=True, type=Path)
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--authority-comment-id", required=True, type=int)
    args = parser.parse_args(argv)
    return run_target(
        descriptor_path=args.descriptor,
        repo_root=args.repo_root,
        authority_comment_id=args.authority_comment_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
