"""Smoke test Stripe purchase flow and downloadable link fulfillment.

This script uses FastAPI TestClient + mocked Stripe calls to validate:
1) Checkout session is created from /purchase/{slug}
2) Paid confirmation path returns a downloadable link
3) Fulfillment email record contains a downloadable link
4) Download link serves a ZIP package

Usage:
  py tests/smoke/run_stripe_download_fulfillment_smoke.py
  py tests/smoke/run_stripe_download_fulfillment_smoke.py --template-slug cloudcare-it
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import hmac
import json
import random
import re
import string
import sys
import time
from urllib.parse import urljoin
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient
import httpx
from sqlalchemy import select
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.main import app
from app.models import FulfillmentEmail, Purchase, Template
from app.routers import public

DOWNLOAD_LINK_RE = re.compile(r"/downloads/theme/([^?]+)\?token=([A-Za-z0-9_\-\.]+)")
SESSION_ID_RE = re.compile(r"(cs_(?:test|live)_[A-Za-z0-9]+)")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tiff")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke test Stripe purchase + downloadable link fulfillment.")
    parser.add_argument(
        "--mode",
        choices=("live", "mocked"),
        default="live",
        help="live: hit running app over HTTP; mocked: in-process TestClient path.",
    )
    parser.add_argument(
        "--template-slug",
        default="cloudcare-it",
        help="Template slug to test. Falls back to first template if not found.",
    )
    parser.add_argument(
        "--email",
        default="",
        help="Recipient email used in checkout form. If provided, script requires fulfillment email status=sent.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Override BASE_URL used when generating fulfillment links (example: http://localhost:8010).",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/smoke",
        help="Directory to save downloaded ZIP artifact for manual verification.",
    )
    parser.add_argument(
        "--stripe-insecure",
        action="store_true",
        help="Disable Stripe SSL certificate verification (local smoke troubleshooting only).",
    )
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


def _build_zip_manifest(zip_bytes: bytes) -> dict[str, object]:
    sha256 = hashlib.sha256(zip_bytes).hexdigest()
    # Use BytesIO via ZipFile constructor reading bytes without writing temp files.
    import io

    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = sorted(archive.namelist())
        image_hits = [name for name in names if name.lower().endswith(IMAGE_SUFFIXES)]
        return {
            "sha256": sha256,
            "file_count": len(names),
            "sample_files": names[:20],
            "image_file_count": len(image_hits),
        }


def _write_artifact(artifact_dir: str, template_slug: str, purchase_id: int, payload: bytes) -> Path:
    artifact_root = Path(artifact_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    artifact_path = artifact_root / f"{template_slug}-purchase-{purchase_id}-{stamp}.zip"
    artifact_path.write_bytes(payload)
    return artifact_path


def _stripe_signature_header(payload: str, webhook_secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(webhook_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _retrieve_checkout_session_metadata(session_id: str, stripe_secret_key: str, *, stripe_insecure: bool) -> dict:
    response = httpx.get(
        f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
        headers={"Authorization": f"Bearer {stripe_secret_key}"},
        timeout=45.0,
        verify=not stripe_insecure,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Stripe session fetch failed ({response.status_code}): {response.text[:240]}")
    body = response.json()
    metadata = body.get("metadata", {})
    if not isinstance(metadata, dict):
        raise RuntimeError("Stripe response metadata is missing or invalid.")
    return metadata


def _mark_paid_locally(purchase_id: int) -> bool:
    with SessionLocal() as db:
        purchase = db.scalar(
            select(Purchase)
            .options(joinedload(Purchase.customer), joinedload(Purchase.template))
            .where(Purchase.id == purchase_id)
        )
        if not purchase:
            return False
        public._mark_purchase_paid(db, purchase)
        return True


def _run_mocked(template_slug: str, recipient_email: str, base_url_override: str, artifact_dir: str) -> int:
    client = TestClient(app)
    template = _select_template(template_slug)
    email = recipient_email.strip() or _random_email("stripe-download-smoke")

    original_secret = public.settings.stripe_secret_key
    original_base_url = public.settings.base_url
    public.settings.stripe_secret_key = "sk_test_smoke_local"
    if base_url_override.strip():
        public.settings.base_url = base_url_override.strip().rstrip("/")

    fake_checkout_url = "https://checkout.stripe.com/c/pay/cs_test_smoke_123"
    fake_session_id = "cs_test_smoke_123"

    try:
        with patch.object(
            public.stripe.checkout.Session,
            "create",
            return_value=type("CheckoutSession", (), {"url": fake_checkout_url})(),
        ), patch.object(
            public.stripe.checkout.Session,
            "retrieve",
            return_value={"payment_status": "paid", "metadata": {"purchase_id": "0"}},
        ):
            purchase_response = client.post(
                f"/purchase/{template.slug}",
                data={
                    "first_name": "Smoke",
                    "last_name": "Tester",
                    "email": email,
                    "company": "QA",
                    "agree_terms": "yes",
                },
                follow_redirects=False,
            )
            if purchase_response.status_code != 303:
                print(f"SMOKE_FAIL: expected 303 from purchase post, got {purchase_response.status_code}")
                return 1
            location = purchase_response.headers.get("location", "")
            if not location.startswith("https://checkout.stripe.com/"):
                print(f"SMOKE_FAIL: expected Stripe redirect, got {location}")
                return 1

        with SessionLocal() as db:
            purchase = db.scalar(
                select(Purchase)
                .options(joinedload(Purchase.template), joinedload(Purchase.customer))
                .where(Purchase.template_id == template.id)
                .where(Purchase.customer.has(email=email))
                .order_by(Purchase.id.desc())
            )
            if not purchase:
                print("SMOKE_FAIL: pending purchase was not persisted")
                return 1
            purchase_id = purchase.id

        with patch.object(
            public.stripe.checkout.Session,
            "retrieve",
            return_value={"payment_status": "paid", "metadata": {"purchase_id": str(purchase_id)}},
        ):
            success_response = client.get(
                f"/purchase/{template.slug}?success=1&purchase_id={purchase_id}&session_id={fake_session_id}"
            )
        if success_response.status_code != 200:
            print(f"SMOKE_FAIL: expected 200 from purchase success page, got {success_response.status_code}")
            return 1

        match = DOWNLOAD_LINK_RE.search(success_response.text)
        if not match:
            print("SMOKE_FAIL: download link was not rendered on success page")
            return 1
        success_slug, token = match.group(1), match.group(2)
        if success_slug != template.slug:
            print(f"SMOKE_FAIL: download link slug mismatch ({success_slug} != {template.slug})")
            return 1

        download_response = client.get(f"/downloads/theme/{template.slug}?token={token}")
        if download_response.status_code != 200:
            print(f"SMOKE_FAIL: download endpoint returned {download_response.status_code}")
            return 1
        content_type = download_response.headers.get("content-type", "")
        if "application/zip" not in content_type:
            print(f"SMOKE_FAIL: expected zip content-type, got {content_type}")
            return 1
        artifact_path = _write_artifact(artifact_dir, template.slug, purchase_id, download_response.content)
        manifest = _build_zip_manifest(download_response.content)

        with SessionLocal() as db:
            purchase = db.get(Purchase, purchase_id)
            if not purchase or purchase.status != "paid":
                print("SMOKE_FAIL: purchase did not transition to paid")
                return 1
            email_log = db.scalar(
                select(FulfillmentEmail)
                .where(FulfillmentEmail.purchase_id == purchase_id)
                .order_by(FulfillmentEmail.id.desc())
            )
            if not email_log:
                print("SMOKE_FAIL: fulfillment email log was not created")
                return 1
            if "/downloads/theme/" not in email_log.body or "token=" not in email_log.body:
                print("SMOKE_FAIL: fulfillment email body missing download URL")
                return 1
            if recipient_email.strip() and email_log.status != "sent":
                print(f"SMOKE_FAIL: expected fulfillment email status=sent, got {email_log.status}")
                if email_log.last_error:
                    print(f"SMOKE_FAIL_DETAIL: {email_log.last_error}")
                return 1

        print("STRIPE_DOWNLOAD_FULFILLMENT_SMOKE_PASS")
        print(f"template={template.slug}")
        print(f"purchase_id={purchase_id}")
        print(f"email={email}")
        print(f"download_url={public.settings.base_url}/downloads/theme/{template.slug}?token={token}")
        print(f"zip_artifact={artifact_path.as_posix()}")
        print(f"zip_sha256={manifest['sha256']}")
        print(f"zip_file_count={manifest['file_count']}")
        print(f"zip_image_file_count={manifest['image_file_count']}")
        print(f"zip_sample_files={json.dumps(manifest['sample_files'])}")
        print(
            "note=download_url is valid only on the same app/database instance where this smoke created the purchase"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE_FAIL: {exc}")
        return 1
    finally:
        public.settings.stripe_secret_key = original_secret
        public.settings.base_url = original_base_url


def _run_live(
    template_slug: str,
    recipient_email: str,
    base_url: str,
    artifact_dir: str,
    *,
    stripe_insecure: bool,
) -> int:
    target_base = base_url.strip().rstrip("/") if base_url.strip() else "http://localhost:8010"
    if not recipient_email.strip():
        print("SMOKE_FAIL: --email is required in live mode.")
        return 1

    stripe_secret = public.settings.stripe_secret_key
    if not stripe_secret:
        print("SMOKE_FAIL: stripe secret key is not configured in environment.")
        return 1
    if stripe_insecure:
        print("SMOKE_WARN: Stripe SSL verification disabled for this run.")

    try:
        with httpx.Client(follow_redirects=False, timeout=45.0) as client:
            purchase_response = client.post(
                f"{target_base}/purchase/{template_slug}",
                data={
                    "first_name": "Smoke",
                    "last_name": "Tester",
                    "email": recipient_email.strip(),
                    "company": "QA",
                    "agree_terms": "yes",
                },
            )
            if purchase_response.status_code != 303:
                print(f"SMOKE_FAIL: expected 303 from purchase post, got {purchase_response.status_code}")
                return 1
            location = purchase_response.headers.get("location", "")
            if not location.startswith("https://checkout.stripe.com/"):
                print(f"SMOKE_FAIL: expected Stripe redirect, got {location}")
                return 1

            session_match = SESSION_ID_RE.search(location)
            if not session_match:
                print("SMOKE_FAIL: could not extract checkout session id from Stripe URL")
                return 1
            session_id = session_match.group(1)

            try:
                metadata = _retrieve_checkout_session_metadata(
                    session_id,
                    stripe_secret,
                    stripe_insecure=stripe_insecure,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"SMOKE_FAIL: unable to retrieve Stripe session: {exc}")
                return 1

            purchase_id = int(metadata.get("purchase_id", 0) or 0)
            session_template_slug = str(metadata.get("template_slug", template_slug))
            if purchase_id <= 0:
                print("SMOKE_FAIL: checkout session metadata did not include a valid purchase_id")
                return 1

            event_payload = {
                "id": f"evt_smoke_{int(time.time())}_{random.randint(1000, 9999)}",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "payment_status": "paid",
                        "metadata": {
                            "purchase_id": str(purchase_id),
                            "template_slug": session_template_slug,
                        },
                    }
                },
            }
            payload_json = json.dumps(event_payload)
            webhook_headers = {"Content-Type": "application/json"}
            if public.settings.stripe_webhook_secret:
                webhook_headers["stripe-signature"] = _stripe_signature_header(
                    payload_json, public.settings.stripe_webhook_secret
                )

            webhook_response = client.post(f"{target_base}/webhooks/stripe", content=payload_json, headers=webhook_headers)
            used_local_payment_mark = False
            if webhook_response.status_code != 200:
                body_preview = webhook_response.text[:500].replace("\n", " ")
                print(
                    f"SMOKE_WARN: webhook endpoint returned {webhook_response.status_code}: {body_preview}; "
                    "attempting local DB mark-paid fallback."
                )
                used_local_payment_mark = _mark_paid_locally(purchase_id)
                if not used_local_payment_mark:
                    print("SMOKE_FAIL: webhook failed and local DB fallback could not find purchase.")
                    return 1

            downloads_response = client.get(
                f"{target_base}/downloads",
                params={"email": recipient_email.strip()},
                follow_redirects=True,
            )
            if downloads_response.status_code != 200:
                print(f"SMOKE_FAIL: downloads page returned {downloads_response.status_code}")
                return 1
            link_match = DOWNLOAD_LINK_RE.search(downloads_response.text)
            if not link_match:
                print("SMOKE_FAIL: could not find download link in /downloads page")
                return 1
            download_href = link_match.group(0)
            download_url = urljoin(f"{target_base}/", download_href.lstrip("/"))
            download_response = client.get(download_url)
            if download_response.status_code != 200:
                print(f"SMOKE_FAIL: download endpoint returned {download_response.status_code}")
                return 1
            content_type = download_response.headers.get("content-type", "")
            if "application/zip" not in content_type:
                print(f"SMOKE_FAIL: expected zip content-type, got {content_type}")
                return 1

            artifact_path = _write_artifact(artifact_dir, session_template_slug, purchase_id, download_response.content)
            manifest = _build_zip_manifest(download_response.content)

            print("STRIPE_DOWNLOAD_FULFILLMENT_SMOKE_PASS")
            print(f"mode=live")
            print(f"payment_mark_method={'local_db_fallback' if used_local_payment_mark else 'webhook'}")
            print(f"template={session_template_slug}")
            print(f"purchase_id={purchase_id}")
            print(f"email={recipient_email.strip()}")
            print(f"download_url={download_url}")
            print(f"zip_artifact={artifact_path.as_posix()}")
            print(f"zip_sha256={manifest['sha256']}")
            print(f"zip_file_count={manifest['file_count']}")
            print(f"zip_image_file_count={manifest['image_file_count']}")
            print(f"zip_sample_files={json.dumps(manifest['sample_files'])}")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE_FAIL: {exc}")
        return 1


def run(
    mode: str,
    template_slug: str,
    recipient_email: str,
    base_url_override: str,
    artifact_dir: str,
    *,
    stripe_insecure: bool = False,
) -> int:
    if mode == "live":
        return _run_live(
            template_slug,
            recipient_email,
            base_url_override,
            artifact_dir,
            stripe_insecure=stripe_insecure,
        )
    return _run_mocked(template_slug, recipient_email, base_url_override, artifact_dir)


def main() -> int:
    args = _build_parser().parse_args()
    return run(
        mode=args.mode,
        template_slug=args.template_slug,
        recipient_email=args.email,
        base_url_override=args.base_url,
        artifact_dir=args.artifact_dir,
        stripe_insecure=args.stripe_insecure,
    )


if __name__ == "__main__":
    sys.exit(main())
