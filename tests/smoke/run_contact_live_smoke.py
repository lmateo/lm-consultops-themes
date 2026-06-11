"""Manual smoke runner for contact form integration.

Examples:
  py tests/smoke/run_contact_live_smoke.py --target proxy --base-url http://localhost:8010
  py tests/smoke/run_contact_live_smoke.py --target direct
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

import httpx


DEFAULT_CONTACTS_URL = "https://consultops.mateoconsultinginc.com/api/integrations/contacts"


def _now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test contact integration wiring.")
    parser.add_argument(
        "--target",
        choices=("proxy", "direct"),
        default="proxy",
        help="proxy: call your app /api/contact, direct: call contacts integration endpoint directly",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("BASE_URL", "http://localhost:8010"),
        help="Base URL for app endpoint when --target=proxy",
    )
    parser.add_argument(
        "--contacts-url",
        default=os.getenv("CONSULTOPS_CONTACTS_API_URL", DEFAULT_CONTACTS_URL),
        help="Contacts integration URL for --target=direct",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("INTEGRATION_API_KEY", ""),
        help="Integration API key (required for --target=direct)",
    )
    parser.add_argument("--name", default="Smoke Test", help="Contact name")
    parser.add_argument("--email", default="smoke.test@example.com", help="Contact email")
    parser.add_argument(
        "--message",
        default=f"Smoke test ping from lm-consultops-themes ({_now_stamp()})",
        help="Contact message/notes",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    return parser


def _post_via_proxy(client: httpx.Client, base_url: str, name: str, email: str, message: str, timeout: float) -> httpx.Response:
    # /api/contact validates honeypot + Turnstile when configured.
    return client.post(
        f"{base_url.rstrip('/')}/api/contact",
        data={
            "name": name,
            "email": email,
            "message": message,
            "website": "",
            "cf-turnstile-response": "smoke-test-token",
        },
        timeout=timeout,
    )


def _post_direct(client: httpx.Client, contacts_url: str, api_key: str, name: str, email: str, message: str, timeout: float) -> httpx.Response:
    if not api_key:
        raise ValueError("INTEGRATION_API_KEY is required for --target=direct")
    return client.post(
        contacts_url,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"name": name, "email": email, "notes": message},
        timeout=timeout,
    )


def main() -> int:
    args = _build_parser().parse_args()
    try:
        with httpx.Client(follow_redirects=True) as client:
            if args.target == "proxy":
                response = _post_via_proxy(
                    client=client,
                    base_url=args.base_url,
                    name=args.name,
                    email=args.email,
                    message=args.message,
                    timeout=args.timeout,
                )
            else:
                response = _post_direct(
                    client=client,
                    contacts_url=args.contacts_url,
                    api_key=args.api_key,
                    name=args.name,
                    email=args.email,
                    message=args.message,
                    timeout=args.timeout,
                )
    except (httpx.HTTPError, ValueError) as exc:
        print(f"[SMOKE FAIL] Request error: {exc}")
        return 1

    status = response.status_code
    print(f"[SMOKE] target={args.target} status={status}")
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:400]}
    print(body)

    if 200 <= status < 300:
        print("[SMOKE PASS] Contact integration responded successfully.")
        return 0

    print("[SMOKE FAIL] Non-success response.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
