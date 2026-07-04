#!/usr/bin/env python3
"""E2 value smoke harness: RelayLM vs direct-backend comparison transcripts.

This harness runs one fixed scenario twice with the same user turns, the
same model, and the same sampling parameters:

- Run A sends each turn through RelayLM ``/v1/chat/completions`` on a
  character-bound managed route. Conversation history follows the current
  RelayLM default (the client stacks its own user/assistant history).
- Run B sends the same turns directly to the same backend and model as a
  naive frontend baseline: full raw history stacked as-is, no system
  message, and no RelayLM-derived persona or memory injection.

It then writes ONE comparison artifact under ``local/value_smoke/`` with a
deliberately blank human-judgment section. The harness never asserts,
scores, or auto-evaluates response quality: whether RelayLM produced a
felt difference is judged only by a human reading the artifact.

Boundary exception: the artifact intentionally contains conversation
bodies. It must stay under ``local/value_smoke/`` (gitignored) and must
never flow into ``docs/``, traces, audit output, or any content-free
diagnostic path. This script acts as an HTTP client only; it does not
touch MEM/SOUL/SLP persistence and does not bypass any RelayLM gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, default_config_path, load_config

LOCAL_ARTIFACT_ROOT = REPO_ROOT / "local"
ARTIFACT_DIR = LOCAL_ARTIFACT_ROOT / "value_smoke"

MIN_SCENARIO_TURNS = 2
MAX_SCENARIO_TURNS = 64

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 512
DEFAULT_TIMEOUT_SECONDS = 120.0

BASELINE_DEFINITION = (
    "Run B(直結ベースライン)は「素朴なフロントエンド」を模す: "
    "同一バックエンド・同一モデルに対し、同じuserターンを送り、"
    "自分のuser/assistant全履歴をそのまま積むだけ。"
    "systemメッセージなし、RelayLM由来のpersona注入なし、記憶注入なし。"
)

JUDGMENT_INVALID_IF_BLANK_NOTE = (
    "注記: この判定欄が空欄のままのartifactは、E2の証拠として無効である。"
)

JUDGMENT_FIELD_LINES = (
    "- 判定 (A / B / 差なし):",
    "- 根拠:",
    "- RelayLMは体感できる差を生んだか (yes / no / unclear):",
)

ARTIFACT_REQUIRED_SECTIONS = (
    "# E2 Value Smoke Comparison",
    "## 1. Metadata",
    "## 2. Baseline definition (Run B)",
    "## 3. Turn-by-turn comparison",
    "## 4. Human judgment (blank at generation)",
    "### 4.1 記憶想起の体感差",
    "### 4.2 人格安定性の体感差",
    "### 4.3 総合判定",
)


class E2ValueSmokeError(RuntimeError):
    """Bounded harness failure with a content-free message."""


@dataclass(frozen=True)
class ScenarioTurn:
    index: int
    user: str
    probe: str


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    title: str
    description: str
    path: Path
    turns: tuple[ScenarioTurn, ...]


@dataclass(frozen=True)
class RunSettings:
    label: str
    base_url: str
    model: str
    api_key: str | None


@dataclass(frozen=True)
class E2ValueSmokeResult:
    artifact_path: Path
    scenario_id: str
    turn_count: int
    run_a_turn_count: int
    run_b_turn_count: int


def load_scenario(path: Path) -> Scenario:
    if not path.is_file():
        raise E2ValueSmokeError(f"scenario file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise E2ValueSmokeError(f"scenario must be a YAML mapping: {path}")
    scenario_id = raw.get("scenario_id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise E2ValueSmokeError("scenario_id is required")
    safe_id = scenario_id.strip()
    if not all(ch.isalnum() or ch in "_-" for ch in safe_id):
        raise E2ValueSmokeError("scenario_id must use [A-Za-z0-9_-] only")
    raw_turns = raw.get("turns")
    if not isinstance(raw_turns, list):
        raise E2ValueSmokeError("turns must be a list")
    if not MIN_SCENARIO_TURNS <= len(raw_turns) <= MAX_SCENARIO_TURNS:
        raise E2ValueSmokeError(
            f"turn count {len(raw_turns)} outside "
            f"[{MIN_SCENARIO_TURNS}, {MAX_SCENARIO_TURNS}]"
        )
    turns: list[ScenarioTurn] = []
    for position, entry in enumerate(raw_turns, start=1):
        if not isinstance(entry, dict):
            raise E2ValueSmokeError(f"turn {position} must be a mapping")
        user = entry.get("user")
        probe = entry.get("probe")
        if not isinstance(user, str) or not user.strip():
            raise E2ValueSmokeError(f"turn {position} requires a non-empty user text")
        if not isinstance(probe, str) or not probe.strip():
            raise E2ValueSmokeError(f"turn {position} requires a non-empty probe note")
        turns.append(ScenarioTurn(index=position, user=user.strip(), probe=probe.strip()))
    return Scenario(
        scenario_id=safe_id,
        title=str(raw.get("title") or safe_id),
        description=str(raw.get("description") or "").strip(),
        path=path,
        turns=tuple(turns),
    )


def resolve_route_id(config: RelayLMConfig, requested: str | None) -> str:
    if requested is not None:
        if requested not in config.model_routes:
            raise E2ValueSmokeError(f"route not found in config: {requested}")
        return requested
    character_routes = [
        route_id
        for route_id, route in config.model_routes.items()
        if route.character_id
    ]
    if len(character_routes) == 1:
        return character_routes[0]
    if not character_routes:
        raise E2ValueSmokeError("no character-bound route in config; pass --route")
    raise E2ValueSmokeError(
        "multiple character-bound routes in config; pass --route "
        f"(candidates: {', '.join(sorted(character_routes))})"
    )


def _normalized_base_url(base_url: object) -> str:
    # Accepts str or pydantic HttpUrl (config-loaded backend base_url).
    return str(base_url).rstrip("/")


def chat_completion(
    settings: RunSettings,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    seed: int | None,
    timeout_seconds: float,
) -> str:
    payload: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if seed is not None:
        payload["seed"] = seed
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = f"{_normalized_base_url(settings.base_url)}/chat/completions"
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"content-type": "application/json"},
    )
    if settings.api_key:
        request.add_header("authorization", f"Bearer {settings.api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read(300).decode("utf-8", errors="replace")
        raise E2ValueSmokeError(
            f"{settings.label}: HTTP {error.code} from {url}: {detail}"
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise E2ValueSmokeError(f"{settings.label}: request to {url} failed: {error}") from error
    try:
        parsed = json.loads(raw.decode("utf-8"))
        content = parsed["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise E2ValueSmokeError(
            f"{settings.label}: unexpected chat completion response shape from {url}"
        ) from error
    if not isinstance(content, str):
        raise E2ValueSmokeError(f"{settings.label}: response content is not a string")
    return content


def run_conversation(
    settings: RunSettings,
    scenario: Scenario,
    *,
    temperature: float,
    max_tokens: int,
    seed: int | None,
    timeout_seconds: float,
) -> list[str]:
    """Run the scenario as a naive history-stacking client and return replies."""
    history: list[dict[str, str]] = []
    replies: list[str] = []
    for turn in scenario.turns:
        history.append({"role": "user", "content": turn.user})
        reply = chat_completion(
            settings,
            history,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout_seconds=timeout_seconds,
        )
        history.append({"role": "assistant", "content": reply})
        replies.append(reply)
        print(
            f"[{settings.label}] turn {turn.index}/{len(scenario.turns)} "
            f"ok ({len(reply)} chars)"
        )
    return replies


def _resolve_artifact_path(scenario_id: str, timestamp: str) -> Path:
    artifact_path = (ARTIFACT_DIR / f"e2_{scenario_id}_{timestamp}.md").resolve()
    local_root = LOCAL_ARTIFACT_ROOT.resolve()
    if local_root not in artifact_path.parents:
        raise E2ValueSmokeError(
            "artifact path escaped local/value_smoke; refusing to write"
        )
    return artifact_path


def render_artifact(
    scenario: Scenario,
    *,
    generated_at: str,
    route_id: str,
    character_id: str,
    backend_id: str,
    backend_model: str,
    relaylm_base_url: str,
    backend_base_url: str,
    temperature: float,
    max_tokens: int,
    seed: int | None,
    config_path: Path,
    config_sha256: str,
    run_a_replies: list[str],
    run_b_replies: list[str],
) -> str:
    if len(run_a_replies) != len(scenario.turns) or len(run_b_replies) != len(scenario.turns):
        raise E2ValueSmokeError("run reply counts do not match scenario turn count")
    lines: list[str] = []
    lines.append("# E2 Value Smoke Comparison")
    lines.append("")
    lines.append(
        "このファイルは会話本文を含む。`local/value_smoke/` の外へコピー・転記・コミットしないこと。"
    )
    lines.append("")
    lines.append("## 1. Metadata")
    lines.append("")
    lines.append(f"- generated_at: {generated_at}")
    lines.append(f"- scenario_id: {scenario.scenario_id}")
    lines.append(f"- scenario_title: {scenario.title}")
    lines.append(f"- scenario_path: {scenario.path.as_posix()}")
    lines.append(f"- turns: {len(scenario.turns)}")
    lines.append(f"- relaylm_route: {route_id}")
    lines.append(f"- character_id: {character_id}")
    lines.append(f"- backend_id: {backend_id}")
    lines.append(f"- backend_model: {backend_model}")
    lines.append(f"- run_a_base_url: {relaylm_base_url}")
    lines.append(f"- run_b_base_url: {backend_base_url}")
    lines.append(f"- temperature: {temperature}")
    lines.append(f"- max_tokens: {max_tokens}")
    lines.append(f"- seed: {seed if seed is not None else '(not set)'}")
    lines.append(f"- config_path: {config_path.as_posix()}")
    lines.append(f"- config_sha256: {config_sha256}")
    lines.append("")
    lines.append("## 2. Baseline definition (Run B)")
    lines.append("")
    lines.append(BASELINE_DEFINITION)
    lines.append("")
    lines.append(
        "Run A(RelayLM経由)は同じuserターン列を同じ素朴な履歴積みで "
        f"RelayLM route `{route_id}` に送る。両Runは同一モデル・同一サンプリング"
        "パラメータで統制されており、差はRelayLMを経由するか否かのみ。"
    )
    lines.append("")
    lines.append("## 3. Turn-by-turn comparison")
    for turn, reply_a, reply_b in zip(scenario.turns, run_a_replies, run_b_replies):
        lines.append("")
        lines.append(f"### Turn {turn.index}")
        lines.append("")
        lines.append(f"- probe: {turn.probe}")
        lines.append("")
        lines.append("**User:**")
        lines.append("")
        lines.append(turn.user)
        lines.append("")
        lines.append("**Run A (RelayLM):**")
        lines.append("")
        lines.append(reply_a)
        lines.append("")
        lines.append("**Run B (direct baseline):**")
        lines.append("")
        lines.append(reply_b)
    lines.append("")
    lines.append("## 4. Human judgment (blank at generation)")
    lines.append("")
    lines.append("このセクションは人間(Rin)が読後に手書きで埋める。ハーネスは判定しない。")
    lines.append("")
    lines.append(JUDGMENT_INVALID_IF_BLANK_NOTE)
    lines.append("")
    lines.append("### 4.1 記憶想起の体感差")
    lines.append("")
    lines.append("- 判定 (A / B / 差なし):")
    lines.append("- 根拠:")
    lines.append("")
    lines.append("### 4.2 人格安定性の体感差")
    lines.append("")
    lines.append("- 判定 (A / B / 差なし):")
    lines.append("- 根拠:")
    lines.append("")
    lines.append("### 4.3 総合判定")
    lines.append("")
    lines.append("- RelayLMは体感できる差を生んだか (yes / no / unclear):")
    lines.append("- 根拠:")
    lines.append("")
    return "\n".join(lines)


def run_value_smoke(
    scenario_path: Path,
    *,
    config_path: Path | None = None,
    route: str | None = None,
    relaylm_base_url: str | None = None,
    backend_base_url: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    seed: int | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> E2ValueSmokeResult:
    scenario = load_scenario(scenario_path)
    config = load_config(config_path)
    resolved_config_path = (
        Path(config_path) if config_path is not None else default_config_path()
    )
    config_sha256 = hashlib.sha256(resolved_config_path.read_bytes()).hexdigest()

    route_id = resolve_route_id(config, route)
    route_config = config.model_routes[route_id]
    character_id = route_config.character_id or "(none)"
    backend_id = route_config.backend
    backend = config.backends.get(backend_id)
    if backend is None:
        raise E2ValueSmokeError(f"route backend not found in config: {backend_id}")
    backend_model = route_config.backend_model or backend.default_model
    if not backend_model:
        raise E2ValueSmokeError(
            f"route {route_id} has no backend_model and backend {backend_id} "
            "has no default_model"
        )

    resolved_relaylm_base_url = _normalized_base_url(
        relaylm_base_url
        or f"http://{config.listen.host}:{config.listen.port}/v1"
    )
    resolved_backend_base_url = _normalized_base_url(
        backend_base_url or backend.base_url
    )

    run_a = RunSettings(
        label="run-a-relaylm",
        base_url=resolved_relaylm_base_url,
        model=route_id,
        api_key=None,
    )
    run_b = RunSettings(
        label="run-b-direct",
        base_url=resolved_backend_base_url,
        model=backend_model,
        api_key=backend.api_key,
    )

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    artifact_path = _resolve_artifact_path(scenario.scenario_id, timestamp)

    shared = dict(
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )
    run_a_replies = run_conversation(run_a, scenario, **shared)
    run_b_replies = run_conversation(run_b, scenario, **shared)

    artifact = render_artifact(
        scenario,
        generated_at=generated_at,
        route_id=route_id,
        character_id=character_id,
        backend_id=backend_id,
        backend_model=backend_model,
        relaylm_base_url=resolved_relaylm_base_url,
        backend_base_url=resolved_backend_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        config_path=resolved_config_path,
        config_sha256=config_sha256,
        run_a_replies=run_a_replies,
        run_b_replies=run_b_replies,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact, encoding="utf-8")
    return E2ValueSmokeResult(
        artifact_path=artifact_path,
        scenario_id=scenario.scenario_id,
        turn_count=len(scenario.turns),
        run_a_turn_count=len(run_a_replies),
        run_b_turn_count=len(run_b_replies),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="scenario YAML (e.g. examples/value_smoke/scenario_01_memory_recall.yaml)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="RelayLM config path (default: RELAYLM_CONFIG or config.yaml)",
    )
    parser.add_argument(
        "--route",
        default=None,
        help="model route ID (default: the single character-bound route)",
    )
    parser.add_argument(
        "--relaylm-base-url",
        default=None,
        help="Run A base URL (default: http://<listen.host>:<listen.port>/v1)",
    )
    parser.add_argument(
        "--backend-base-url",
        default=None,
        help="Run B base URL (default: the route backend base_url)",
    )
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS
    )
    args = parser.parse_args(argv)

    try:
        result = run_value_smoke(
            args.scenario,
            config_path=args.config,
            route=args.route,
            relaylm_base_url=args.relaylm_base_url,
            backend_base_url=args.backend_base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            seed=args.seed,
            timeout_seconds=args.timeout_seconds,
        )
    except E2ValueSmokeError as error:
        print(f"E2 value smoke failed: {error}", file=sys.stderr)
        return 1
    print(
        f"E2 value smoke completed: scenario={result.scenario_id} "
        f"turns={result.turn_count} (run A={result.run_a_turn_count}, "
        f"run B={result.run_b_turn_count})"
    )
    print(f"comparison artifact: {result.artifact_path}")
    print("判定欄は空欄で生成されている。人間が読んで判定を記入するまでE2の証拠にならない。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
