import smtplib
from datetime import datetime
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import FulfillmentEmail, Purchase
from app.services.download_access import download_link_limits_email_clause, issue_download_token_for_purchase


def _build_download_url(settings: Settings, purchase: Purchase, token: str) -> str:
    return f"{settings.base_url}/downloads/theme/{purchase.template.slug}?token={token}"


def _build_email_body(purchase: Purchase, download_url: str, settings: Settings) -> str:
    limits_clause = download_link_limits_email_clause(settings)
    return (
        f"Hello {purchase.customer.name},\n\n"
        f"Thank you for purchasing {purchase.template.title}.\n"
        "Your full website theme package is ready for download.\n"
        "This package intentionally excludes stock image assets so you can safely add your own licensed media.\n\n"
        f"Download link ({limits_clause}):\n{download_url}\n\n"
        f"Amount: ${purchase.amount:.2f}\n\n"
        "If your link expires, visit My Downloads and request a new link using your purchase email.\n"
    )


def _send_email(settings: Settings, recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured.")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def send_purchase_fulfillment_email(
    db: Session,
    purchase: Purchase,
    settings: Settings,
    *,
    force_retry: bool = False,
) -> FulfillmentEmail:
    subject = f"Your {purchase.template.title} download is ready"
    token = issue_download_token_for_purchase(
        db,
        settings=settings,
        purchase=purchase,
        expires_in_seconds=settings.download_link_ttl_seconds,
    )
    download_url = _build_download_url(settings, purchase, token)
    body = _build_email_body(purchase, download_url, settings)

    email_log = db.scalar(
        select(FulfillmentEmail).where(
            FulfillmentEmail.purchase_id == purchase.id,
            FulfillmentEmail.email_type == "download_access",
        )
    )
    if not email_log:
        email_log = FulfillmentEmail(
            purchase_id=purchase.id,
            email_type="download_access",
            recipient=purchase.customer.email,
            subject=subject,
            body=body,
            status="pending",
        )
        db.add(email_log)
        db.flush()
    elif email_log.status == "sent" and not force_retry:
        return email_log
    else:
        email_log.recipient = purchase.customer.email
        email_log.subject = subject
        email_log.body = body

    try:
        _send_email(settings, purchase.customer.email, subject, body)
        email_log.status = "sent"
        email_log.sent_at = datetime.now()
        email_log.last_error = ""
    except Exception as exc:  # noqa: BLE001
        email_log.status = "failed"
        email_log.last_error = str(exc)
    finally:
        email_log.attempts += 1
        db.commit()
        db.refresh(email_log)
    return email_log
