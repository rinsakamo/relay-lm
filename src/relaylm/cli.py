from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO

from relaylm import __version__
from relaylm.runtime_assembly import RuntimeAssemblyError, TokenCounterCapability
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)
from relaylm.runtime_preflight import (
    PreparedRuntime,
    RuntimePreflightError,
    prepare_runtime,
)
from relaylm.server import create_app


RELAYLM_VERSION = __version__
ServeRunner = Callable[..., None]


class _CLIExit(Exception):
    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(status)


class _ArgumentParser(argparse.ArgumentParser):
    def __init__(
        self,
        *args: object,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        **kwargs: object,
    ) -> None:
        self._stdout = sys.stdout if stdout is None else stdout
        self._stderr = sys.stderr if stderr is None else stderr
        super().__init__(*args, **kwargs)

    def _print_message(self, message: str | None, file: TextIO | None = None) -> None:
        if not message:
            return
        target = self._stdout if file is None or file is sys.stdout else self._stderr
        target.write(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._stderr.write(message)
        raise _CLIExit(status)

    def error(self, message: str) -> None:
        self.print_usage(self._stderr)
        self.exit(2, f"relaylm: error: {_summary_value(message)}\n")


def main() -> None:
    raise SystemExit(run_cli(sys.argv[1:]))


def run_cli(
    argv: Sequence[str],
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    serve_runner: ServeRunner | None = None,
    token_counter_capabilities: Mapping[str, TokenCounterCapability] | None = None,
) -> int:
    """Execute the bounded release CLI and return a process-style exit code."""

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    environ = os.environ if environ is None else environ
    parser = _build_parser(stdout=stdout, stderr=stderr)
    try:
        args = parser.parse_args(list(argv))
        if args.version and args.command is not None:
            parser.error("--version cannot be combined with a command")
    except _CLIExit as exc:
        return exc.status

    if args.version:
        stdout.write(f"relaylm {RELAYLM_VERSION}\n")
        return 0

    if args.command is None:
        parser.print_help(stdout)
        return 0

    try:
        resolved = resolve_runtime_config(
            config_path=args.config,
            overrides=_overrides_from_args(args),
            environ=environ,
        )
        prepared = prepare_runtime(
            resolved,
            token_counter_capabilities=token_counter_capabilities,
        )
    except (RuntimeConfigResolutionError, RuntimeAssemblyError, RuntimePreflightError) as exc:
        stderr.write(f"error: {_summary_value(str(exc))}\n")
        return 2

    if args.command == "doctor":
        try:
            if args.json:
                stdout.write(
                    json.dumps(
                        prepared.doctor_report(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            else:
                _print_doctor_summary(prepared, stdout)
            return 0
        finally:
            _close_provider(prepared)

    assert args.command == "serve"
    _print_serve_summary(prepared, stdout)
    runner = _default_serve_runner if serve_runner is None else serve_runner
    try:
        runner(
            create_app(**prepared.assembly.app_kwargs()),
            host=prepared.resolved.config.server.host,
            port=prepared.resolved.config.server.port,
        )
    finally:
        _close_provider(prepared)
    return 0


def _build_parser(*, stdout: TextIO, stderr: TextIO) -> _ArgumentParser:
    parser = _ArgumentParser(
        prog="relaylm",
        description="RelayLM 1.0 release runtime",
        stdout=stdout,
        stderr=stderr,
    )
    parser.add_argument(
        "--version",
        action="store_true",
    )
    subcommands = parser.add_subparsers(
        dest="command",
        parser_class=lambda *args, **kwargs: _ArgumentParser(
            *args,
            stdout=stdout,
            stderr=stderr,
            **kwargs,
        ),
    )

    serve = subcommands.add_parser(
        "serve",
        help="validate configuration and start the OpenAI-compatible service",
    )
    _add_runtime_arguments(serve)

    doctor = subcommands.add_parser(
        "doctor",
        help="run non-generative, non-mutating runtime preflight",
    )
    _add_runtime_arguments(doctor)
    doctor.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable content-free diagnostics",
    )
    return parser


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config")
    parser.add_argument("--character", dest="character_directory")
    parser.add_argument("--provider-adapter")
    parser.add_argument("--provider-base-url")
    parser.add_argument("--provider-model")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--host", dest="server_host")
    parser.add_argument("--port", dest="server_port", type=int)
    parser.add_argument("--profile")
    parser.add_argument("--cognition-mode")


def _overrides_from_args(args: argparse.Namespace) -> RuntimeConfigOverrides:
    return RuntimeConfigOverrides(
        character_directory=args.character_directory,
        provider_adapter=args.provider_adapter,
        provider_base_url=args.provider_base_url,
        provider_model=args.provider_model,
        provider_api_key_env=args.provider_api_key_env,
        server_host=args.server_host,
        server_port=args.server_port,
        profile=args.profile,
        cognition_mode=args.cognition_mode,
    )


def _print_doctor_summary(prepared: PreparedRuntime, stdout: TextIO) -> None:
    config = prepared.resolved.config
    stdout.write(f"RelayLM {RELAYLM_VERSION} doctor: ok\n")
    stdout.write(f"character: {_summary_value(config.character.directory)}\n")
    stdout.write(
        f"provider: {_summary_value(config.provider.adapter)} "
        f"backend={_summary_value(config.provider.backend.value)} "
        f"model={_summary_value(config.provider.model)} "
        f"base_url={_summary_value(config.provider.base_url)}\n"
    )
    stdout.write(
        f"server: {_summary_value(config.server.host)}:{config.server.port}\n"
    )
    stdout.write(_runtime_layers_summary(prepared) + "\n")


def _print_serve_summary(prepared: PreparedRuntime, stdout: TextIO) -> None:
    config = prepared.resolved.config
    stdout.write(f"RelayLM {RELAYLM_VERSION} preflight: ok\n")
    stdout.write(f"character: {_summary_value(config.character.directory)}\n")
    stdout.write(
        f"provider: {_summary_value(config.provider.adapter)} "
        f"backend={_summary_value(config.provider.backend.value)} "
        f"model={_summary_value(config.provider.model)} "
        f"base_url={_summary_value(config.provider.base_url)}\n"
    )
    stdout.write(
        f"listen: {_summary_value(config.server.host)}:{config.server.port}\n"
    )
    stdout.write(_runtime_layers_summary(prepared) + "\n")


def _summary_value(value: str) -> str:
    pieces: list[str] = []
    for character in value:
        if character.isprintable():
            pieces.append(character)
            continue
        codepoint = ord(character)
        if codepoint <= 0xFF:
            pieces.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            pieces.append(f"\\u{codepoint:04x}")
        else:
            pieces.append(f"\\U{codepoint:08x}")
    return "".join(pieces)


def _runtime_layers_summary(prepared: PreparedRuntime) -> str:
    assembly = prepared.assembly
    memory = "on" if assembly.memory_budget is not None else "off"
    event = "on" if assembly.event_budget is not None else "off"
    continuity = "on" if assembly.continuity_runtime is not None else "off"
    cognitive = "on" if assembly.cognitive_budget is not None else "off"
    return (
        "runtime: "
        f"cognition={assembly.cognition_mode.value} "
        f"memory={memory} event={event} continuity={continuity} cognitive_budget={cognitive}"
    )


def _default_serve_runner(app: object, *, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


def _close_provider(prepared: PreparedRuntime) -> None:
    close = getattr(prepared.assembly.provider, "aclose", None)
    if close is None:
        return
    asyncio.run(close())
