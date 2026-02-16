"""Security headers middleware.

Task card: G1-6
- HSTS (Strict-Transport-Security)
- CSP (Content-Security-Policy)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 0 (modern browsers use CSP instead)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restricted defaults

Dependencies: G0-1 (healthz), G1-5 (app factory)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecurityHeadersConfig:
    """Configuration for security headers."""

    hsts_max_age: int = 31_536_000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False
    frame_options: str = "DENY"
    content_type_options: str = "nosniff"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "camera=(), microphone=(), geolocation=()"
    csp_directives: dict[str, str] = field(
        default_factory=lambda: {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data:",
            "connect-src": "'self'",
            "font-src": "'self'",
            "object-src": "'none'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
        }
    )


class SecurityHeadersMiddleware:
    """Add security headers to all HTTP responses.

    Applied at the ASGI middleware level via FastAPI app factory.
    """

    def __init__(self, config: SecurityHeadersConfig | None = None) -> None:
        self._config = config or SecurityHeadersConfig()

    def get_headers(self) -> dict[str, str]:
        """Build the security headers dict.

        Returns:
            Dict of header name -> header value.
        """
        cfg = self._config
        headers: dict[str, str] = {}

        # HSTS
        hsts_value = f"max-age={cfg.hsts_max_age}"
        if cfg.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if cfg.hsts_preload:
            hsts_value += "; preload"
        headers["Strict-Transport-Security"] = hsts_value

        # CSP
        csp_parts = [f"{k} {v}" for k, v in cfg.csp_directives.items()]
        headers["Content-Security-Policy"] = "; ".join(csp_parts)

        # Other security headers
        headers["X-Content-Type-Options"] = cfg.content_type_options
        headers["X-Frame-Options"] = cfg.frame_options
        headers["X-XSS-Protection"] = "0"
        headers["Referrer-Policy"] = cfg.referrer_policy
        headers["Permissions-Policy"] = cfg.permissions_policy

        return headers
