from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def call(url: str, payload: dict[str, Any] | None = None) -> tuple[int, str, dict[str, str]]:
    data = None
    method = "GET"
    headers = {"content-type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read().decode("utf-8"), dict(res.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers.items())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalized_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8090")
    parser.add_argument("--model", default="relaylm-default")
    parser.add_argument("--expected-mode", default="pass_through")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    status, body, _headers = call(f"{base_url}/healthz")
    require(status == 200, f"healthz failed: {status} {body}")
    require(json.loads(body).get("status") == "ok", f"bad healthz body: {body}")
    print("ok healthz")

    status, body, _headers = call(f"{base_url}/v1/models")
    require(status == 200, f"models failed: {status} {body}")
    model_ids = [item.get("id") for item in json.loads(body).get("data", [])]
    require(args.model in model_ids, f"missing model {args.model}; got {model_ids}")
    print("ok models")

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    status, body, headers = call(f"{base_url}/v1/chat/completions", payload)
    header_map = normalized_headers(headers)
    require("x-relaylm-request-id" in header_map, f"missing request id header: {headers}")
    require(header_map.get("x-relaylm-mode") == args.expected_mode, f"bad mode header: {headers}")
    require(status in {200, 400, 401, 404, 422, 500, 502, 503}, f"unexpected chat status: {status} {body}")
    print(f"ok chat status={status}")
    print("ok chat diagnostics headers")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
