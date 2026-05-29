import base64
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import FulfillmentEmail, Purchase
from app.services.download_access import download_link_limits_email_display, issue_download_token_for_purchase
from app.utils.http_ssl import httpx_verify_option

_EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
_EMAIL_JINJA = Environment(
    loader=FileSystemLoader(str(_EMAIL_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_LOGO_CID = "mateo-logo"
_LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "images" / "logos" / "mateo-favicon.ico"
_BRAND_NAME = "Mateo Consulting Tech"


@dataclass(frozen=True)
class _InlineLogo:
    content_id: str
    filename: str
    mime_subtype: str
    data: bytes


def _inline_logo_attachment() -> _InlineLogo | None:
    if not _LOGO_PATH.is_file():
        return None
    suffix = _LOGO_PATH.suffix.lower()
    mime_subtype = "png" if suffix == ".png" else "x-icon"
    return _InlineLogo(
        content_id=_LOGO_CID,
        filename=f"mateo-logo{suffix or '.ico'}",
        mime_subtype=mime_subtype,
        data=_LOGO_PATH.read_bytes(),
    )


def _build_download_url(settings: Settings, purchase: Purchase, token: str) -> str:
    return f"{settings.base_url.rstrip('/')}/downloads/theme/{purchase.template.slug}?token={token}"


def _build_my_downloads_url(settings: Settings, purchase: Purchase) -> str:
    return f"{settings.base_url.rstrip('/')}/downloads?email={purchase.customer.email}"


def _logo_src(inline_logo: _InlineLogo | None) -> str:
    if inline_logo:
        return f"cid:{inline_logo.content_id}"
    return ""


def _build_email_context(
    purchase: Purchase,
    download_url: str,
    settings: Settings,
    *,
    inline_logo: _InlineLogo | None,
) -> dict[str, str]:
    return {
        "subject": f"Your {purchase.template.title} download is ready",
        "customer_name": purchase.customer.name,
        "template_title": purchase.template.title,
        "download_url": download_url,
        "limits_clause": download_link_limits_email_display(settings),
        "amount": f"{purchase.amount:.2f}",
        "my_downloads_url": _build_my_downloads_url(settings, purchase),
        "support_email": settings.fulfillment_support_email,
        "logo_src": _logo_src(inline_logo),
    }


def _build_email_html(
    purchase: Purchase,
    download_url: str,
    settings: Settings,
    *,
    inline_logo: _InlineLogo | None,
) -> str:
    template = _EMAIL_JINJA.get_template("download_fulfillment.html")
    return template.render(**_build_email_context(purchase, download_url, settings, inline_logo=inline_logo))


def _build_email_text(purchase: Purchase, download_url: str, settings: Settings) -> str:
    limits_clause = download_link_limits_email_display(settings)
    my_downloads_url = _build_my_downloads_url(settings, purchase)
    support_email = settings.fulfillment_support_email
    return (
        f"Hello {purchase.customer.name},\n\n"
        f"Thank you for purchasing {purchase.template.title}.\n"
        "Your full website theme package is ready for download.\n"
        "This package intentionally excludes stock image assets so you can safely add your own licensed media.\n\n"
        f"Download link ({limits_clause}):\n{download_url}\n\n"
        f"Amount: ${purchase.amount:.2f}\n\n"
        f"If your link expires, visit My Downloads ({my_downloads_url}) and request a new link using your purchase email.\n\n"
        "Best,\n"
        f"{_BRAND_NAME}\n"
        f"{support_email}\n\n"
        f"Questions? Reply to this email or contact us at {support_email}.\n"
        f"{_BRAND_NAME}\n"
    )


def _resolve_from_email(settings: Settings) -> str:
    if settings.resend_from_email.strip():
        return settings.resend_from_email.strip()
    return settings.smtp_from_email.strip()


def _send_via_resend(
    settings: Settings,
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
    *,
    inline_logo: _InlineLogo | None,
) -> None:
    api_key = settings.resend_api_key.strip()
    from_email = _resolve_from_email(settings)
    if not api_key or not from_email:
        raise RuntimeError("Resend is not configured.")

    payload: dict[str, object] = {
        "from": f"{_BRAND_NAME} <{from_email}>",
        "to": [recipient],
        "subject": subject,
        "html": html_body,
        "text": text_body,
        "reply_to": settings.fulfillment_support_email,
    }
    if inline_logo:
        payload["attachments"] = [
            {
                "filename": inline_logo.filename,
                "content": base64.b64encode(inline_logo.data).decode("ascii"),
                "content_id": inline_logo.content_id,
            }
        ]

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30.0,
        verify=httpx_verify_option(),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Resend API error ({response.status_code}): {response.text[:500]}")


def _send_via_smtp(
    settings: Settings,
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
    *,
    inline_logo: _InlineLogo | None,
) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured.")

    if inline_logo:
        message = MIMEMultipart("related")
        message["From"] = _resolve_from_email(settings)
        message["To"] = recipient
        message["Subject"] = subject
        message["Reply-To"] = settings.fulfillment_support_email

        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(text_body, "plain", "utf-8"))
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
        message.attach(alternative)

        image = MIMEImage(inline_logo.data, _subtype=inline_logo.mime_subtype)
        image.add_header("Content-ID", f"<{inline_logo.content_id}>")
        image.add_header("Content-Disposition", "inline", filename=inline_logo.filename)
        message.attach(image)
    else:
        message = EmailMessage()
        message["From"] = _resolve_from_email(settings)
        message["To"] = recipient
        message["Subject"] = subject
        message["Reply-To"] = settings.fulfillment_support_email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def _send_email(
    settings: Settings,
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
    *,
    inline_logo: _InlineLogo | None,
) -> None:
    if settings.resend_api_key.strip():
        _send_via_resend(
            settings,
            recipient,
            subject,
            html_body,
            text_body,
            inline_logo=inline_logo,
        )
        return
    _send_via_smtp(
        settings,
        recipient,
        subject,
        html_body,
        text_body,
        inline_logo=inline_logo,
    )


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
    inline_logo = _inline_logo_attachment()
    html_body = _build_email_html(purchase, download_url, settings, inline_logo=inline_logo)
    text_body = _build_email_text(purchase, download_url, settings)

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
            body=html_body,
            status="pending",
        )
        db.add(email_log)
        db.flush()
    elif email_log.status == "sent" and not force_retry:
        return email_log
    else:
        email_log.recipient = purchase.customer.email
        email_log.subject = subject
        email_log.body = html_body

    try:
        _send_email(
            settings,
            purchase.customer.email,
            subject,
            html_body,
            text_body,
            inline_logo=inline_logo,
        )
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


# Backward-compatible exports for tests.
def _build_email_body(purchase: Purchase, download_url: str, settings: Settings) -> str:
    return _build_email_html(purchase, download_url, settings, inline_logo=_inline_logo_attachment())
