from __future__ import annotations

import argparse
import sys

from relaylm.config import load_config
from relaylm.routing import (
    RouteConfigurationError,
    RouteNotFoundError,
    list_model_ids,
    resolve_route,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.example.yaml")
    parser.add_argument("--model", default="relaylm-default")
    args = parser.parse_args()

    config = load_config(args.config)
    model_ids = list_model_ids(config)
    require(args.model in model_ids, f"missing model {args.model}; got {model_ids}")
    print("ok list_model_ids")

    route = resolve_route(config, args.model)
    require(route.route_model == args.model, f"bad route_model: {route.route_model}")
    require(route.backend_name == "local_backend", f"bad backend_name: {route.backend_name}")
    require(route.backend_model == "local-model", f"bad backend_model: {route.backend_model}")
    require(route.mode_applied == "pass_through", f"bad mode: {route.mode_applied}")
    require(route.character_id == "default", f"bad character_id: {route.character_id}")
    require(route.cache_namespace == "character/default", f"bad cache_namespace: {route.cache_namespace}")
    require(route.memory_namespace == "character/default", f"bad memory_namespace: {route.memory_namespace}")
    print("ok resolve_route")

    try:
        resolve_route(config, "missing-model")
    except RouteNotFoundError:
        print("ok missing model error")
    else:
        raise AssertionError("missing model did not raise RouteNotFoundError")

    broken_config = config.model_copy(deep=True)
    broken_config.backends.pop(route.backend_name)
    try:
        resolve_route(broken_config, args.model)
    except RouteConfigurationError:
        print("ok missing backend error")
    else:
        raise AssertionError("missing backend did not raise RouteConfigurationError")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
