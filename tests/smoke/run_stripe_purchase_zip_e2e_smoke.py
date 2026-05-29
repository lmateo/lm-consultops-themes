"""End-to-end smoke: client purchase form, fulfillment, and purchase ZIP validation.

Flow:
1) Playwright submits the real /purchase checkout form (client path)
2) Stripe checkout session metadata is read from the redirect URL
3) checkout.session.completed webhook marks the purchase paid
4) /downloads serves the purchase ZIP, which is validated against the expected package

Usage:
  py tests/smoke/run_stripe_purchase_zip_e2e_smoke.py
  py tests/smoke/run_stripe_purchase_zip_e2e_smoke.py --base-url http://localhost:8010
  py tests/smoke/run_stripe_purchase_zip_e2e_smoke.py --template-slug cloudcare-it --headed
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
import re
import string
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
import stripe
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from sqlalchemy import select
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models import Template
from app.routers import public
from app.utils.http_ssl import httpx_verify_option, inject_truststore
from tests.smoke.purchase_zip_validation import validate_purchase_zip_bytes

DOWNLOAD_LINK_RE = re.compile(r"/downloads/theme/([^?]+)\?token=([A-Za-z0-9_\-\.]+)")
SESSION_ID_RE = re.compile(r"(cs_(?:test|live)_[A-Za-z0-9]+)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Client purchase flow + purchase ZIP validation.")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--template-slug", default="cloudcare-it")
    parser.add_argument("--artifact-dir", default="artifacts/smoke")
    parser.add_argument("--timeout-ms", type=int, default=180_000)
    parser.add_argument("--headed", action="store_true")
    return parser


def _random_email(prefix: str) -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}-{token}@example.com"


def _select_template(slug: str) -> Template:
    with SessionLocal() as db:
        template = db.scalar(
            select(Template)
            .options(joinedload(Template.category), joinedload(Template.industry))
            .where(Template.slug == slug)
        )
        if template:
            return template
        fallback = db.scalar(select(Template).options(joinedload(Template.category), joinedload(Template.industry)))
        if not fallback:
            raise RuntimeError("No templates found in database.")
        return fallback


def _write_artifact(artifact_dir: str, template_slug: str, purchase_id: int, payload: bytes) -> Path:
    artifact_root = Path(artifact_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    artifact_path = artifact_root / f"{template_slug}-e2e-purchase-{purchase_id}-{stamp}.zip"
    artifact_path.write_bytes(payload)
    return artifact_path


def _stripe_signature_header(payload: str, webhook_secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(webhook_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _session_metadata_value(session: stripe.checkout.Session, key: str) -> str:
    metadata = session.metadata
    if metadata is None:
        return ""
    value = getattr(metadata, key, None)
    if value is None and hasattr(metadata, "get"):
        value = metadata.get(key)
    return str(value or "")


def _mark_paid_via_webhook(
    client: httpx.Client,
    base_url: str,
    *,
    purchase_id: int,
    template_slug: str,
) -> None:
    event_payload = {
        "id": f"evt_e2e_{int(time.time())}_{random.randint(1000, 9999)}",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_status": "paid",
                "metadata": {
                    "purchase_id": str(purchase_id),
                    "template_slug": template_slug,
                },
            }
        },
    }
    payload_json = json.dumps(event_payload)
    headers = {"Content-Type": "application/json"}
    if public.settings.stripe_webhook_secret:
        headers["stripe-signature"] = _stripe_signature_header(payload_json, public.settings.stripe_webhook_secret)

    response = client.post(f"{base_url.rstrip('/')}/webhooks/stripe", content=payload_json, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"webhook returned {response.status_code}: {response.text[:240]}")


def run(
    base_url: str,
    template_slug: str,
    artifact_dir: str,
    timeout_ms: int,
    *,
    headed: bool,
) -> int:
    stripe_secret = public.settings.stripe_secret_key.strip()
    if not stripe_secret:
        print("STRIPE_PURCHASE_ZIP_E2E_FAIL: STRIPE_SECRET_KEY is not configured.")
        return 1
    if stripe_secret.startswith("sk_live_"):
        print("STRIPE_PURCHASE_ZIP_E2E_FAIL: use sk_test_ key for automated checkout smoke.")
        return 1

    base = base_url.rstrip("/")
    template = _select_template(template_slug)
    email = _random_email("stripe-zip-e2e")
    purchase_url = f"{base}/purchase/{template.slug}"
    checkout_url = ""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(purchase_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("h1:has-text('Checkout')", timeout=timeout_ms)
            if page.locator("text=Stripe checkout is temporarily unavailable").count() > 0:
                print("STRIPE_PURCHASE_ZIP_E2E_FAIL: Stripe checkout unavailable.")
                return 1

            page.fill('input[name="first_name"]', "Stripe")
            page.fill('input[name="last_name"]', "Zip")
            page.fill('input[name="email"]', email)
            page.fill('input[name="company"]', "Smoke QA")
            page.check('input[name="agree_terms"]')

            with page.expect_navigation(url=re.compile(r"^https://checkout\.stripe\.com/"), timeout=timeout_ms):
                page.click('button[type="submit"]')
            checkout_url = page.url
        except PlaywrightTimeoutError as exc:
            print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: timeout {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: {exc}")
            return 1
        finally:
            context.close()
            browser.close()

    session_match = SESSION_ID_RE.search(checkout_url)
    if not session_match:
        print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: could not extract checkout session id from {checkout_url}")
        return 1
    session_id = session_match.group(1)

    try:
        inject_truststore()
        stripe.api_key = stripe_secret
        session = stripe.checkout.Session.retrieve(session_id)
        purchase_id = int(_session_metadata_value(session, "purchase_id") or 0)
        session_template_slug = _session_metadata_value(session, "template_slug") or template.slug
        if purchase_id <= 0:
            print("STRIPE_PURCHASE_ZIP_E2E_FAIL: checkout session metadata missing purchase_id")
            return 1
    except Exception as exc:  # noqa: BLE001
        print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: unable to read checkout session metadata: {exc}")
        return 1

    try:
        with httpx.Client(follow_redirects=True, timeout=60.0, verify=httpx_verify_option()) as client:
            _mark_paid_via_webhook(
                client,
                base,
                purchase_id=purchase_id,
                template_slug=session_template_slug,
            )
            downloads_response = client.get(f"{base}/downloads", params={"email": email})
            if downloads_response.status_code != 200:
                print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: downloads page returned {downloads_response.status_code}")
                return 1
            link_match = DOWNLOAD_LINK_RE.search(downloads_response.text)
            if not link_match:
                print("STRIPE_PURCHASE_ZIP_E2E_FAIL: downloads page missing purchase ZIP link")
                return 1
            download_url = urljoin(f"{base}/", link_match.group(0).lstrip("/"))
            download_response = client.get(download_url)
    except Exception as exc:  # noqa: BLE001
        print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: {exc}")
        return 1

    if download_response.status_code != 200:
        print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: download returned {download_response.status_code}")
        return 1
    content_type = download_response.headers.get("content-type", "")
    if "application/zip" not in content_type:
        print(f"STRIPE_PURCHASE_ZIP_E2E_FAIL: expected zip content-type, got {content_type}")
        return 1

    violations = validate_purchase_zip_bytes(download_response.content, template)
    if violations:
        print("STRIPE_PURCHASE_ZIP_E2E_FAIL: zip validation failed")
        print(f"zip_violations={json.dumps(violations)}")
        return 1

    artifact_path = _write_artifact(artifact_dir, template.slug, purchase_id, download_response.content)
    print("STRIPE_PURCHASE_ZIP_E2E_PASS")
    print(f"template={template.slug}")
    print(f"purchase_id={purchase_id}")
    print(f"email={email}")
    print(f"checkout_url={checkout_url}")
    print(f"download_url={download_url}")
    print(f"zip_artifact={artifact_path.as_posix()}")
    print(f"zip_bytes={len(download_response.content)}")
    print("purchase_zip_validation=pass")
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    return run(
        base_url=args.base_url,
        template_slug=args.template_slug,
        artifact_dir=args.artifact_dir,
        timeout_ms=args.timeout_ms,
        headed=args.headed,
    )


if __name__ == "__main__":
    sys.exit(main())
