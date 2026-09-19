"""Installed-RC history bridge for external qualification.

This module is launched with the Python interpreter from the accepted RelayLM
RC installation.  The current qualification checkout contributes only this
tools module and the benchmark adapter; every relaylm import resolves from the
installed accepted wheel.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import relaylm
from relaylm.cognitive import CognitionExecutionMode
from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.runtime_preflight import prepare_runtime
import tools.memconflict_adapter as memconflict_adapter\nfrom tools.memconflict_adapter import RelayLMReadOnlyQueryAdapter\n

PUBLIC_PROFILE = "relaylm-exact-rc"
PROTOCOL_VERSION = 1


class ExactRCAdapterBridgeError(RuntimeError):
    pass


@dataclass(slots=True)
class _AxisState:
    adapter: RelayLMReadOnlyQueryAdapter
    session_ids: list[str]
    question_count: int = 0


class ExactRCAdapterBridge:
    def __init__(self, *, config_path: Path, workspace_root: Path) -> None:
        if workspace_root.exists():
            raise ExactRCAdapterBridgeError("adapter workspace root must be fresh")
        workspace_root.mkdir(parents=True)
        self.workspace_root = workspace_root
        resolved = resolve_runtime_config(config_path=config_path)
        prepared = prepare_runtime(resolved)
        if prepared.assembly.cognition_mode is not CognitionExecutionMode.TWO_PASS:
            raise ExactRCAdapterBridgeError(
                "external qualification exact RC requires two_pass cognition"
            )
        profile = prepared.assembly.profiles.resolve(PUBLIC_PROFILE)
        if profile is None:
            raise ExactRCAdapterBridgeError(
                f"exact RC config must expose Cognitive Profile {PUBLIC_PROFILE!r}"
            )
        self.prepared = prepared
        self.profile = profile
        self.axes: dict[str, _AxisState] = {}

    def _axis(self, axis_id: str) -> _AxisState:
        if not isinstance(axis_id, str) or not axis_id.strip():
            raise ExactRCAdapterBridgeError("axis_id must be non-empty")
        existing = self.axes.get(axis_id)
        if existing is not None:
            return existing

        axis_token = hashlib.sha256(axis_id.encode("utf-8")).hexdigest()[:24]
        axis_root = self.workspace_root / f"axis-{axis_token}"
        if axis_root.exists():
            raise ExactRCAdapterBridgeError("exact RC axis package root is not fresh")
        shutil.copytree(self.profile.package.root, axis_root, symlinks=True)
        continuity = self.profile.continuity_runtime
        adapter = RelayLMReadOnlyQueryAdapter(
            package_root=axis_root,
            provider=self.profile.provider,
            mode="two_pass",
            memory_budget=self.prepared.assembly.memory_budget,
            event_budget=self.prepared.assembly.event_budget,
            continuity_context=None if continuity is None else continuity.context,
            continuity_lifetime_revisions=(
                4 if continuity is None else continuity.lifetime_revisions
            ),
            cognitive_budget=self.prepared.assembly.cognitive_budget,
            pass1_request=self.prepared.assembly.pass1_request,
            pass2_request=self.prepared.assembly.pass2_request,
        )
        state = _AxisState(adapter=adapter, session_ids=[])
        self.axes[axis_id] = state
        return state

    @staticmethod
    def _session(raw: object, expected_order: int) -> dict[str, object]:
        if not isinstance(raw, dict):
            raise ExactRCAdapterBridgeError("history session must be an object")
        if set(raw) != {"session_id", "order", "items"}:
            raise ExactRCAdapterBridgeError("history session keys are invalid")
        session_id = raw["session_id"]
        order = raw["order"]
        items = raw["items"]
        if not isinstance(session_id, str) or not session_id.strip():
            raise ExactRCAdapterBridgeError("history session_id must be non-empty")
        if order != expected_order:
            raise ExactRCAdapterBridgeError("history session order is not contiguous")
        if not isinstance(items, list) or not items:
            raise ExactRCAdapterBridgeError("history session items must be non-empty")
        normalized: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, dict) or set(item) != {"role", "content", "timestamp"}:
                raise ExactRCAdapterBridgeError("history item shape is invalid")
            role = item["role"]
            content = item["content"]
            timestamp = item["timestamp"]
            if role not in {"user", "assistant"}:
                raise ExactRCAdapterBridgeError("history role is invalid")
            if not isinstance(content, str) or not content.strip():
                raise ExactRCAdapterBridgeError("history content must be non-empty")
            if timestamp is not None and (
                not isinstance(timestamp, str) or not timestamp.strip()
            ):
                raise ExactRCAdapterBridgeError("history timestamp is invalid")
            normalized.append(
                {"role": role, "content": content, "timestamp": timestamp}
            )
        return {"session_id": session_id, "order": order, "items": normalized}

    def query(self, request: dict[str, object]) -> dict[str, object]:
        expected = {
            "protocol_version",
            "request_id",
            "axis_id",
            "question_id",
            "question",
            "sessions",
        }
        if set(request) != expected or request.get("protocol_version") != PROTOCOL_VERSION:
            raise ExactRCAdapterBridgeError("query request shape is invalid")
        request_id = request["request_id"]
        axis_id = request["axis_id"]
        question_id = request["question_id"]
        question = request["question"]
        sessions = request["sessions"]
        if not isinstance(request_id, str) or not request_id:
            raise ExactRCAdapterBridgeError("request_id must be non-empty")
        if not isinstance(question_id, str) or not question_id:
            raise ExactRCAdapterBridgeError("question_id must be non-empty")
        if not isinstance(question, str) or not question.strip():
            raise ExactRCAdapterBridgeError("question must be non-empty")
        if not isinstance(sessions, list) or not sessions:
            raise ExactRCAdapterBridgeError("sessions must be a non-empty list")

        state = self._axis(str(axis_id))
        normalized = [
            self._session(item, index) for index, item in enumerate(sessions)
        ]
        requested_ids = [str(item["session_id"]) for item in normalized]
        if requested_ids[: len(state.session_ids)] != state.session_ids:
            raise ExactRCAdapterBridgeError(
                "question history prefix regressed or drifted within exact RC axis"
            )

        before_evidence = len(state.adapter.dialogue_ingestion_evidence)
        previous_session_count = len(state.session_ids)
        for item in normalized[previous_session_count:]:
            state.adapter.ingest_session_dialogue(
                item["items"],
                session_id=str(item["session_id"]),
                session_index=int(item["order"]),
            )
            state.session_ids.append(str(item["session_id"]))
        new_ingestion = state.adapter.dialogue_ingestion_evidence[before_evidence:]

        state.question_count += 1
        with state.adapter.freeze() as snapshot:
            result = asyncio.run(
                snapshot.query(question, question_index=state.question_count)
            )
            snapshot_fingerprint = snapshot.snapshot_fingerprint

        def token_sum(name: str) -> int | None:
            values: list[int] = []
            completions = [
                entry.get("pass2_completion") for entry in new_ingestion
            ]
            completions.extend([result.pass1_completion, result.pass2_completion])
            for completion in completions:
                if completion is None:
                    continue
                value = (
                    completion.get(name)
                    if isinstance(completion, dict)
                    else getattr(completion, name, None)
                )
                if value is not None:
                    values.append(int(value))
            return sum(values) if values else None

        model_call_count = len(new_ingestion) + 2
        return {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "status": "ok",
            "answer": result.response,
            "external_evidence": result.to_external_evidence(),
            "snapshot_fingerprint": snapshot_fingerprint,
            "history_session_ids": requested_ids,
            "new_history_session_count": len(requested_ids) - previous_session_count,
            "new_history_pass2_calls": len(new_ingestion),
            "model_call_count": model_call_count,
            "prompt_tokens": token_sum("prompt_tokens"),
            "completion_tokens": token_sum("completion_tokens"),
        }

    def close(self) -> None:
        for state in self.axes.values():
            state.adapter.close()
        seen: set[int] = set()

        async def close_providers() -> None:
            for profile in self.prepared.assembly.profiles.profiles:
                provider_id = id(profile.provider)
                if provider_id in seen:
                    continue
                seen.add(provider_id)
                close = getattr(profile.provider, "aclose", None)
                if close is not None:
                    await close()

        asyncio.run(close_providers())


def _emit(value: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    bridge = ExactRCAdapterBridge(
        config_path=args.config.resolve(),
        workspace_root=args.workspace_root.resolve(),
    )
    _emit(
        {
            "protocol_version": PROTOCOL_VERSION,
            "status": "ready",
            "relaylm_version": relaylm.__version__,
            "relaylm_origin": str(Path(relaylm.__file__).resolve()),
            "adapter_origin": str(Path(memconflict_adapter.__file__).resolve()),
            "profile": PUBLIC_PROFILE,
        }
    )
    try:
        for line in sys.stdin:
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ExactRCAdapterBridgeError("request must be an object")
                if raw.get("op") == "close":
                    _emit(
                        {
                            "protocol_version": PROTOCOL_VERSION,
                            "status": "closed",
                        }
                    )
                    return 0
                if raw.get("op") != "query":
                    raise ExactRCAdapterBridgeError("unsupported bridge operation")
                request = dict(raw)
                request.pop("op")
                _emit(bridge.query(request))
            except Exception as exc:
                _emit(
                    {
                        "protocol_version": PROTOCOL_VERSION,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
    finally:
        bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
