"""Translated helpers from `react-router/lib/actions.ts`."""

from __future__ import annotations

from urllib.parse import urlparse

from pyinkcli.packages.react_router.router import Headers


def throwIfPotentialCSRFAttack(
    headers: Headers,
    allowedActionOrigins: list[str] | None,
) -> None:
    origin_header = headers.get("origin")
    origin_domain: str | None = None

    try:
        origin_domain = (
            urlparse(origin_header).netloc
            if isinstance(origin_header, str) and origin_header != "null"
            else origin_header
        )
    except Exception as error:  # pragma: no cover - urlparse itself does not raise
        raise Error("`origin` header is not a valid URL. Aborting the action.") from error

    if isinstance(origin_header, str) and origin_header not in ("", "null") and not origin_domain:
        raise Error("`origin` header is not a valid URL. Aborting the action.")

    host = _parseHostHeader(headers)

    if (
        origin_domain
        and (not host or origin_domain != host["value"])
        and not _isAllowedOrigin(origin_domain, allowedActionOrigins)
    ):
        if host:
            raise Error(
                f"{host['type']} header does not match `origin` header from a "
                "forwarded action request. Aborting the action."
            )
        raise Error(
            "`x-forwarded-host` or `host` headers are not provided. One of these "
            "is needed to compare the `origin` header from a forwarded action "
            "request. Aborting the action."
        )


class Error(Exception):
    """Match the upstream file's generic Error throws."""


def _matchWildcardDomain(domain: str, pattern: str) -> bool:
    domain_parts = domain.split(".")
    pattern_parts = pattern.split(".")

    if len(pattern_parts) < 1:
        return False

    if len(domain_parts) < len(pattern_parts):
        return False

    while pattern_parts:
        pattern_part = pattern_parts.pop()
        domain_part = domain_parts.pop() if domain_parts else None

        if pattern_part == "":
            return False
        if pattern_part == "*":
            if domain_part:
                continue
            return False
        if pattern_part == "**":
            if pattern_parts:
                return False
            return domain_part is not None
        if domain_part != pattern_part:
            return False

    return len(domain_parts) == 0


def _isAllowedOrigin(
    originDomain: str,
    allowedActionOrigins: list[str] | None = None,
) -> bool:
    return any(
        allowed_origin
        and (
            allowed_origin == originDomain
            or _matchWildcardDomain(originDomain, allowed_origin)
        )
        for allowed_origin in (allowedActionOrigins or [])
    )


def _parseHostHeader(headers: Headers) -> dict[str, str] | None:
    forwarded_host_header = headers.get("x-forwarded-host")
    forwarded_host_value = (
        forwarded_host_header.split(",")[0].strip()
        if forwarded_host_header
        else None
    )
    host_header = headers.get("host")

    if forwarded_host_value:
        return {
            "type": "x-forwarded-host",
            "value": forwarded_host_value,
        }
    if host_header:
        return {
            "type": "host",
            "value": host_header,
        }
    return None
