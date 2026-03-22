"""Action-time helpers."""

from __future__ import annotations

from .router import Headers


def throwIfPotentialCSRFAttack(headers: Headers, allowedActionOrigins):
    originHeader = headers.get("origin")
    originDomain = None
    try:
        if isinstance(originHeader, str) and originHeader != "null":
            from urllib.parse import urlparse

            parsed = urlparse(originHeader)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("invalid origin")
            originDomain = parsed.netloc
        else:
            originDomain = originHeader
    except Exception as error:
        raise ValueError("`origin` header is not a valid URL. Aborting the action.") from error

    def parse_host_header():
        forwardedHostHeader = headers.get("x-forwarded-host")
        forwardedHostValue = forwardedHostHeader.split(",")[0].strip() if forwardedHostHeader else None
        hostHeader = headers.get("host")
        return (
            {"type": "x-forwarded-host", "value": forwardedHostValue}
            if forwardedHostValue
            else {"type": "host", "value": hostHeader}
            if hostHeader
            else None
        )

    def match_wildcard_domain(domain: str, pattern: str) -> bool:
        domain_parts = domain.split(".")
        pattern_parts = pattern.split(".")
        if not pattern_parts:
            return False
        if len(domain_parts) < len(pattern_parts):
            return False
        while pattern_parts:
            pattern_part = pattern_parts.pop()
            domain_part = domain_parts.pop()
            if pattern_part == "":
                return False
            if pattern_part == "*":
                if not domain_part:
                    return False
                continue
            if pattern_part == "**":
                if pattern_parts:
                    return False
                return domain_part is not None
            if domain_part != pattern_part:
                return False
        return not domain_parts

    def is_allowed_origin(origin_domain: str, allowed_action_origins=None):
        allowed_action_origins = allowed_action_origins or []
        return any(
            allowed_origin
            and (allowed_origin == origin_domain or match_wildcard_domain(origin_domain, allowed_origin))
            for allowed_origin in allowed_action_origins
        )

    host = parse_host_header()
    if originDomain and (not host or originDomain != host["value"]):
        if not is_allowed_origin(originDomain, allowedActionOrigins):
            if host:
                raise ValueError(
                    f"{host['type']} header does not match `origin` header from a forwarded action request. Aborting the action."
                )
            raise ValueError(
                "`x-forwarded-host` or `host` headers are not provided. One of these is needed to compare the `origin` header from a forwarded action request. Aborting the action."
            )


__all__ = ["throwIfPotentialCSRFAttack"]
