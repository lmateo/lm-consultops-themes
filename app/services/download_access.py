import hashlib
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.models import DownloadGrant, Purchase
from app.utils.download_tokens import create_download_token, verify_download_token


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_download_token_for_purchase(
    db: Session,
    *,
    settings: Settings,
    purchase: Purchase,
    expires_in_seconds: int | None = None,
    max_downloads: int | None = None,
) -> str:
    ttl_seconds = max(60, int(expires_in_seconds or settings.download_link_ttl_seconds))
    allowed_downloads = max(1, int(max_downloads or settings.download_link_max_downloads))
    token = create_download_token(
        secret_key=settings.secret_key,
        purchase_id=purchase.id,
        template_slug=purchase.template.slug,
        customer_email=purchase.customer.email,
        expires_in_seconds=ttl_seconds,
    )
    grant = DownloadGrant(
        purchase_id=purchase.id,
        token_hash=_hash_token(token),
        expires_at=datetime.now() + timedelta(seconds=ttl_seconds),
        max_downloads=allowed_downloads,
        status="active",
    )
    db.add(grant)
    db.commit()
    return token


def validate_download_token_access(
    db: Session,
    *,
    settings: Settings,
    template_slug: str,
    token: str,
) -> Purchase:
    payload = verify_download_token(token, secret_key=settings.secret_key)
    if not payload:
        raise ValueError("Invalid or expired download token.")
    if payload.get("template_slug") != template_slug:
        raise ValueError("Download token does not match requested template.")

    purchase_id = int(payload.get("purchase_id", 0))
    customer_email = str(payload.get("customer_email", "")).strip().lower()
    purchase = db.scalar(
        select(Purchase)
        .options(joinedload(Purchase.customer), joinedload(Purchase.template))
        .where(Purchase.id == purchase_id)
    )
    if not purchase:
        raise LookupError("Purchase not found.")
    if purchase.status != "paid":
        raise PermissionError("Purchase is not in paid status.")
    if purchase.customer.email.lower().strip() != customer_email:
        raise PermissionError("Download token does not match this purchase.")
    if purchase.template.slug != template_slug:
        raise PermissionError("Purchased template mismatch.")

    token_hash = _hash_token(token)
    grant = db.scalar(
        select(DownloadGrant).where(
            DownloadGrant.purchase_id == purchase.id,
            DownloadGrant.token_hash == token_hash,
        )
    )
    if not grant:
        raise PermissionError("Download token is not recognized.")
    if grant.status != "active":
        raise PermissionError("Download token is no longer active.")
    if grant.expires_at < datetime.now():
        grant.status = "expired"
        db.commit()
        raise PermissionError("Download token has expired.")
    if grant.download_count >= grant.max_downloads:
        grant.status = "exhausted"
        db.commit()
        raise PermissionError("Download limit reached for this link.")

    grant.download_count += 1
    grant.last_downloaded_at = datetime.now()
    if grant.download_count >= grant.max_downloads:
        grant.status = "exhausted"
    db.commit()

    return purchase
