"""Smoke test: send a real download fulfillment email to the test client.

Uses Resend (preferred) or SMTP from environment settings and an existing paid
purchase when available, otherwise creates a temporary paid purchase row.

Usage:
  py tests/smoke/run_download_email_smoke.py
  py tests/smoke/run_download_email_smoke.py --template-slug cloudcare-it
  py tests/smoke/run_download_email_smoke.py --email lmateo@mateoconsultinginc.com
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Customer, Purchase, Template
from app.services.fulfillment import send_purchase_fulfillment_email

DEFAULT_TEST_CLIENT_EMAIL = "lmateo@mateoconsultinginc.com"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a download fulfillment email smoke test.")
    parser.add_argument("--template-slug", default="cloudcare-it")
    parser.add_argument(
        "--email",
        default=os.getenv("SMOKE_TEST_CLIENT_EMAIL", DEFAULT_TEST_CLIENT_EMAIL),
        help="Test client inbox that should receive the fulfillment email.",
    )
    parser.add_argument(
        "--customer-name",
        default="Smoke Tester",
        help="Customer name rendered in the email greeting.",
    )
    return parser


def _select_template(db, slug: str) -> Template:
    template = db.scalar(
        select(Template)
        .options(joinedload(Template.category), joinedload(Template.industry))
        .where(Template.slug == slug)
    )
    if template:
        return template
    fallback = db.scalar(select(Template).order_by(Template.id.asc()))
    if not fallback:
        raise RuntimeError("No templates found in database.")
    return fallback


def _find_or_create_paid_purchase(db, template: Template, email: str, customer_name: str) -> Purchase:
    purchase = db.scalar(
        select(Purchase)
        .options(joinedload(Purchase.customer), joinedload(Purchase.template))
        .where(Purchase.template_id == template.id)
        .where(Purchase.customer.has(email=email))
        .where(Purchase.status == "paid")
        .order_by(Purchase.id.desc())
    )
    if purchase:
        if purchase.customer.name != customer_name:
            purchase.customer.name = customer_name
            db.commit()
            db.refresh(purchase)
        return purchase

    customer = db.scalar(select(Customer).where(Customer.email == email))
    if not customer:
        customer = Customer(name=customer_name, email=email, company="QA")
        db.add(customer)
        db.flush()
    else:
        customer.name = customer_name

    purchase = Purchase(
        template_id=template.id,
        customer_id=customer.id,
        amount=template.price,
        license_type="Theme",
        status="paid",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    db.refresh(customer)
    purchase.customer = customer
    purchase.template = template
    return purchase


def run(template_slug: str, email: str, customer_name: str) -> int:
    settings = get_settings()
    if not settings.resend_api_key.strip() and not (
        settings.smtp_host and settings.smtp_username and settings.smtp_password
    ):
        print("SMOKE_FAIL: configure RESEND_API_KEY or SMTP credentials in .env")
        return 1

    with SessionLocal() as db:
        template = _select_template(db, template_slug)
        purchase = _find_or_create_paid_purchase(db, template, email.strip(), customer_name.strip())
        template_slug_value = template.slug
        purchase_id = purchase.id
        email_log = send_purchase_fulfillment_email(db, purchase, settings, force_retry=True)

    if email_log.status != "sent":
        print("SMOKE_FAIL: fulfillment email was not sent")
        if email_log.last_error:
            print(f"SMOKE_FAIL_DETAIL: {email_log.last_error}")
        return 1

    print("DOWNLOAD_EMAIL_SMOKE_PASS")
    print(f"template={template_slug_value}")
    print(f"purchase_id={purchase_id}")
    print(f"recipient={email.strip()}")
    print(f"provider={'resend' if settings.resend_api_key.strip() else 'smtp'}")
    print("email_layout=download_fulfillment.html")
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    return run(args.template_slug, args.email, args.customer_name)


if __name__ == "__main__":
    sys.exit(main())
