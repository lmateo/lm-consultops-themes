"""HTTP TLS helpers for environments with incomplete Python CA bundles (common on Windows)."""

from __future__ import annotations

import ssl
from typing import Any


def httpx_verify_option(*, insecure: bool = False) -> bool | str | ssl.SSLContext:
    """Return an httpx-compatible ``verify`` value with OS trust store support."""
    if insecure:
        return False

    if inject_truststore():
        return True

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return True


def inject_truststore() -> bool:
    """Inject OS certificate store into Python SSL (safe to call repeatedly)."""
    try:
        import truststore  # type: ignore[import-untyped]

        truststore.inject_into_ssl()
        return True
    except ImportError:
        return False
