from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Template
from app.services.theme_packages import build_theme_zip_bytes
from tests.smoke.purchase_zip_validation import validate_purchase_zip_bytes


def test_validate_purchase_zip_bytes_accepts_expected_package():
    with SessionLocal() as db:
        template = db.scalar(select(Template).order_by(Template.id.asc()))
    assert template is not None

    zip_bytes, _filename = build_theme_zip_bytes(template)
    violations = validate_purchase_zip_bytes(zip_bytes, template)
    assert violations == []


def test_validate_purchase_zip_bytes_rejects_empty_payload():
    with SessionLocal() as db:
        template = db.scalar(select(Template).order_by(Template.id.asc()))
    assert template is not None

    violations = validate_purchase_zip_bytes(b"", template)
    assert violations == ["zip-empty"]
