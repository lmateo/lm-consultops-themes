import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import Settings
from app.core.database import SessionLocal
from app.main import app
from app.models import Customer, DownloadGrant, Purchase, Template
from app.services.download_access import (
    download_link_limits_email_clause,
    download_link_limits_ui_sentence,
    format_download_link_ttl,
    issue_download_token_for_purchase,
    revoke_active_grants_for_purchase,
    validate_download_token_access,
)
from app.services.fulfillment import _build_email_body

client = TestClient(app)


def _test_settings(**overrides) -> Settings:
    defaults = {
        "secret_key": "test-secret",
        "base_url": "http://testserver",
        "download_link_ttl_seconds": 7200,
        "download_link_max_downloads": 5,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _create_paid_purchase() -> tuple[Purchase, Template]:
    with SessionLocal() as db:
        template = db.scalar(select(Template).order_by(Template.id.asc()))
        assert template is not None
        email = f"download-access-{uuid.uuid4().hex[:8]}@example.com"
        customer = Customer(name="Download Access QA", email=email, company="QA")
        db.add(customer)
        db.flush()

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
        db.refresh(template)
        return purchase, template


def test_format_download_link_ttl():
    assert format_download_link_ttl(3600) == "1 hour"
    assert format_download_link_ttl(7200) == "2 hours"
    assert format_download_link_ttl(300) == "5 minutes"
    assert format_download_link_ttl(45) == "45 seconds"


def test_download_link_limit_descriptions_use_settings():
    settings = _test_settings(download_link_ttl_seconds=7200, download_link_max_downloads=5)
    assert download_link_limits_email_clause(settings) == "expires in 2 hours, up to 5 uses"
    assert (
        download_link_limits_ui_sentence(settings)
        == "expire in 2 hours and allow up to 5 downloads each"
    )


def test_fulfillment_email_body_reflects_settings():
    purchase, _template = _create_paid_purchase()
    settings = _test_settings(download_link_ttl_seconds=3600, download_link_max_downloads=3)
    with SessionLocal() as db:
        purchase_db = db.scalar(
            select(Purchase)
            .options(joinedload(Purchase.customer), joinedload(Purchase.template))
            .where(Purchase.id == purchase.id)
        )
        assert purchase_db is not None
        body = _build_email_body(purchase_db, "http://testserver/downloads/theme/demo?token=abc", settings)
    assert "Download link (expires in 1 hour, limited uses):" in body
    assert "MESSAGE FROM" in body
    assert "Mateo Consulting Tech" in body
    assert "ConsultOps" in body
    assert "http://testserver/downloads/theme/demo?token=abc" in body


def test_issue_download_token_revokes_prior_active_grants():
    purchase, _template = _create_paid_purchase()
    settings = _test_settings()

    with SessionLocal() as db:
        purchase_db = db.get(Purchase, purchase.id)
        assert purchase_db is not None
        first_token = issue_download_token_for_purchase(db, settings=settings, purchase=purchase_db)
        first_hash = db.scalar(
            select(DownloadGrant.token_hash).where(
                DownloadGrant.purchase_id == purchase.id,
                DownloadGrant.status == "active",
            )
        )
        assert first_hash is not None

        second_token = issue_download_token_for_purchase(db, settings=settings, purchase=purchase_db)
        assert first_token != second_token

        grants = db.scalars(select(DownloadGrant).where(DownloadGrant.purchase_id == purchase.id)).all()
        statuses = {grant.token_hash: grant.status for grant in grants}
        assert statuses[first_hash] == "revoked"
        assert sum(1 for status in statuses.values() if status == "active") == 1


def test_revoked_download_token_is_rejected():
    purchase, template = _create_paid_purchase()
    settings = _test_settings()

    with SessionLocal() as db:
        purchase_db = db.get(Purchase, purchase.id)
        assert purchase_db is not None
        old_token = issue_download_token_for_purchase(db, settings=settings, purchase=purchase_db)
        issue_download_token_for_purchase(db, settings=settings, purchase=purchase_db)

        with pytest.raises(PermissionError, match="no longer active"):
            validate_download_token_access(
                db,
                settings=settings,
                template_slug=template.slug,
                token=old_token,
            )


def test_revoke_active_grants_for_purchase_only_affects_target_purchase():
    purchase_a, _template_a = _create_paid_purchase()
    purchase_b, _template_b = _create_paid_purchase()
    settings = _test_settings()

    with SessionLocal() as db:
        purchase_a_db = db.get(Purchase, purchase_a.id)
        purchase_b_db = db.get(Purchase, purchase_b.id)
        assert purchase_a_db is not None and purchase_b_db is not None

        issue_download_token_for_purchase(db, settings=settings, purchase=purchase_a_db)
        issue_download_token_for_purchase(db, settings=settings, purchase=purchase_b_db)

        revoked_count = revoke_active_grants_for_purchase(db, purchase_a.id)
        assert revoked_count == 1
        db.commit()

        grants = db.scalars(select(DownloadGrant).order_by(DownloadGrant.id.asc())).all()
        statuses_by_purchase = {}
        for grant in grants:
            statuses_by_purchase.setdefault(grant.purchase_id, []).append(grant.status)

        assert statuses_by_purchase[purchase_a.id] == ["revoked"]
        assert statuses_by_purchase[purchase_b.id] == ["active"]


def test_my_downloads_page_shows_dynamic_link_limits():
    purchase, _template = _create_paid_purchase()
    with SessionLocal() as db:
        customer = db.get(Customer, purchase.customer_id)
        assert customer is not None
        email = customer.email

    response = client.get(f"/downloads?email={email}")
    assert response.status_code == 200
    assert "expire in 2 hours and allow up to 5 downloads each" in response.text
    assert "Resending issues a fresh link and invalidates previous download links for this purchase." in response.text
