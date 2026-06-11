"""Cloudflare Turnstile verification for public forms."""

from __future__ import annotations

import httpx

from app.core.config import get_settings

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_enabled() -> bool:
    settings = get_settings()
    return bool((settings.turnstile_site_key or "").strip() and (settings.turnstile_secret_key or "").strip())


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """Verify a Turnstile response token with Cloudflare."""
    settings = get_settings()
    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        return True

    cleaned = (token or "").strip()
    if not cleaned:
        return False

    payload: dict[str, str] = {"secret": secret, "response": cleaned}
    if remote_ip:
        payload["remoteip"] = remote_ip

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(TURNSTILE_VERIFY_URL, data=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return False

    return bool(data.get("success"))
