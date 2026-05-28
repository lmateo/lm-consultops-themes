import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import Customer, Purchase, Template
from app.routers import public

client = TestClient(app)


def _get_template() -> Template:
    with SessionLocal() as db:
        template = db.scalar(select(Template).order_by(Template.id.asc()))
        assert template is not None
        return template


def test_purchase_requires_stripe_before_creating_records():
    template = _get_template()
    email = f"missing-stripe-{uuid.uuid4().hex[:8]}@example.com"
    original_secret = public.settings.stripe_secret_key
    public.settings.stripe_secret_key = ""
    try:
        response = client.post(
            f"/purchase/{template.slug}",
            data={
                "first_name": "Stripe",
                "last_name": "Missing",
                "email": email,
                "company": "QA",
                "license_type": "Standard",
                "agree_terms": "yes",
            },
            follow_redirects=False,
        )
        assert response.status_code == 503

        with SessionLocal() as db:
            customer = db.scalar(select(Customer).where(Customer.email == email))
            assert customer is None
    finally:
        public.settings.stripe_secret_key = original_secret


def test_purchase_success_page_renders_download_link(monkeypatch):
    template = _get_template()
    email = f"paid-user-{uuid.uuid4().hex[:8]}@example.com"

    with SessionLocal() as db:
        customer = Customer(name="Paid User", email=email, company="QA")
        db.add(customer)
        db.flush()

        purchase = Purchase(
            template_id=template.id,
            customer_id=customer.id,
            amount=template.price,
            license_type="Standard",
            status="pending",
        )
        db.add(purchase)
        db.commit()
        purchase_id = purchase.id

    original_secret = public.settings.stripe_secret_key
    public.settings.stripe_secret_key = "sk_test_local"
    monkeypatch.setattr(
        public.stripe.checkout.Session,
        "retrieve",
        lambda _session_id: {"payment_status": "paid", "metadata": {"purchase_id": str(purchase_id)}},
    )
    try:
        response = client.get(f"/purchase/{template.slug}?success=1&purchase_id={purchase_id}&session_id=cs_test_123")
        assert response.status_code == 200
        assert "Payment successful." in response.text
        assert f"/downloads/theme/{template.slug}?token=" in response.text

        with SessionLocal() as db:
            refreshed_purchase = db.get(Purchase, purchase_id)
            assert refreshed_purchase is not None
            assert refreshed_purchase.status == "paid"
    finally:
        public.settings.stripe_secret_key = original_secret


def test_purchase_page_shows_unavailable_state_when_stripe_not_configured():
    template = _get_template()
    original_secret = public.settings.stripe_secret_key
    original_publishable = public.settings.stripe_publishable_key
    public.settings.stripe_secret_key = ""
    public.settings.stripe_publishable_key = ""
    try:
        response = client.get(f"/purchase/{template.slug}")
        assert response.status_code == 200
        assert "Stripe checkout is temporarily unavailable" in response.text
        assert "disabled aria-disabled=\"true\"" in response.text
    finally:
        public.settings.stripe_secret_key = original_secret
        public.settings.stripe_publishable_key = original_publishable
