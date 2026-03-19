"""Translated helpers from `react-router/lib/errors.ts`."""

from __future__ import annotations

import json
from typing import Any, Optional

from pyinkcli.packages.react_router.router import (
    DataWithResponseInit,
    ErrorResponseImpl,
    Response,
)

_ERROR_DIGEST_BASE = "REACT_ROUTER_ERROR"
_ERROR_DIGEST_REDIRECT = "REDIRECT"
_ERROR_DIGEST_ROUTE_ERROR_RESPONSE = "ROUTE_ERROR_RESPONSE"


def createRedirectErrorDigest(response: Response) -> str:
    return (
        f"{_ERROR_DIGEST_BASE}:{_ERROR_DIGEST_REDIRECT}:"
        f"{json.dumps(_redirect_payload(response), separators=(',', ':'))}"
    )


def decodeRedirectErrorDigest(digest: str) -> Optional[dict[str, Any]]:
    prefix = f"{_ERROR_DIGEST_BASE}:{_ERROR_DIGEST_REDIRECT}:"
    if digest.startswith(f"{prefix}{{"):
        try:
            parsed = json.loads(digest[len(prefix):])
            if (
                isinstance(parsed, dict)
                and isinstance(parsed.get("status"), int)
                and isinstance(parsed.get("statusText"), str)
                and isinstance(parsed.get("location"), str)
                and isinstance(parsed.get("reloadDocument"), bool)
                and isinstance(parsed.get("replace"), bool)
            ):
                return parsed
        except Exception:
            return None
    return None


def createRouteErrorResponseDigest(
    response: DataWithResponseInit | Response,
) -> str:
    status = 500
    status_text = ""
    data: Any = None

    if _isDataWithResponseInit(response):
        status = response.init.get("status", status) if response.init else status
        status_text = response.init.get("statusText", status_text) if response.init else status_text
        data = response.data
    else:
        status = response.status
        status_text = response.statusText
        data = None

    return (
        f"{_ERROR_DIGEST_BASE}:{_ERROR_DIGEST_ROUTE_ERROR_RESPONSE}:"
        f"{json.dumps({'status': status, 'statusText': status_text, 'data': data}, separators=(',', ':'))}"
    )


def decodeRouteErrorResponseDigest(digest: str) -> Optional[ErrorResponseImpl]:
    prefix = f"{_ERROR_DIGEST_BASE}:{_ERROR_DIGEST_ROUTE_ERROR_RESPONSE}:"
    if digest.startswith(f"{prefix}{{"):
        try:
            parsed = json.loads(digest[len(prefix):])
            if (
                isinstance(parsed, dict)
                and isinstance(parsed.get("status"), int)
                and isinstance(parsed.get("statusText"), str)
            ):
                return ErrorResponseImpl(
                    parsed["status"],
                    parsed["statusText"],
                    parsed.get("data"),
                )
        except Exception:
            return None
    return None


def _isDataWithResponseInit(value: Any) -> bool:
    return (
        isinstance(value, DataWithResponseInit)
        or (
            isinstance(value, dict)
            and value.get("type") == "DataWithResponseInit"
            and "data" in value
            and "init" in value
        )
        or (
            hasattr(value, "type")
            and getattr(value, "type", None) == "DataWithResponseInit"
            and hasattr(value, "data")
            and hasattr(value, "init")
        )
    )


def _redirect_payload(response: Response) -> dict[str, Any]:
    return {
        "status": response.status,
        "statusText": response.statusText,
        "location": response.headers.get("Location"),
        "reloadDocument": response.headers.get("X-Remix-Reload-Document") == "true",
        "replace": response.headers.get("X-Remix-Replace") == "true",
    }
