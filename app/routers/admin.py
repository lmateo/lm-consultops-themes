from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import (
    Category,
    Customer,
    FulfillmentEmail,
    Inquiry,
    Industry,
    Purchase,
    Review,
    ServiceAddon,
    StripeWebhookEvent,
    Template,
)
from app.services.fulfillment import send_purchase_fulfillment_email
from app.core.config import get_settings
from app.utils.templating import render

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _safe_return_to(return_to: str) -> str:
    return return_to if return_to.startswith("/admin") else "/admin"


@router.get("/")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    webhook_status: str = Query(default="unresolved"),
    email_status: str = Query(default="failed"),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
):
    stats = {
        "templates": db.scalar(select(func.count()).select_from(Template)) or 0,
        "categories": db.scalar(select(func.count()).select_from(Category)) or 0,
        "industries": db.scalar(select(func.count()).select_from(Industry)) or 0,
        "reviews": db.scalar(select(func.count()).select_from(Review)) or 0,
        "purchases": db.scalar(select(func.count()).select_from(Purchase)) or 0,
        "customers": db.scalar(select(func.count()).select_from(Customer)) or 0,
        "inquiries": db.scalar(select(func.count()).select_from(Inquiry)) or 0,
        "addons": db.scalar(select(func.count()).select_from(ServiceAddon)) or 0,
        "featured_templates": db.scalar(
            select(func.count()).select_from(Template).where(Template.is_featured.is_(True))
        )
        or 0,
        "best_sellers": db.scalar(
            select(func.count()).select_from(Template).where(Template.is_best_seller.is_(True))
        )
        or 0,
        "failed_webhooks": db.scalar(
            select(func.count()).select_from(StripeWebhookEvent).where(StripeWebhookEvent.status != "processed")
        )
        or 0,
        "failed_fulfillment_emails": db.scalar(
            select(func.count()).select_from(FulfillmentEmail).where(FulfillmentEmail.status == "failed")
        )
        or 0,
    }
    recent_templates = db.scalars(select(Template).order_by(Template.updated_at.desc()).limit(8)).all()
    start_dt = _parse_date(start_date)
    end_dt_raw = _parse_date(end_date)
    end_dt = end_dt_raw + timedelta(days=1) if end_dt_raw else None

    webhook_query = select(StripeWebhookEvent).order_by(StripeWebhookEvent.created_at.desc())
    if webhook_status == "unresolved":
        webhook_query = webhook_query.where(
            StripeWebhookEvent.status.in_(["received", "ignored", "failed"])
        )
    elif webhook_status != "all":
        webhook_query = webhook_query.where(StripeWebhookEvent.status == webhook_status)
    if start_dt:
        webhook_query = webhook_query.where(StripeWebhookEvent.created_at >= start_dt)
    if end_dt:
        webhook_query = webhook_query.where(StripeWebhookEvent.created_at < end_dt)
    failed_webhook_events = db.scalars(webhook_query.limit(30)).all()

    email_query = (
        select(FulfillmentEmail)
        .options(joinedload(FulfillmentEmail.purchase).joinedload(Purchase.template))
        .order_by(FulfillmentEmail.updated_at.desc())
    )
    if email_status != "all":
        email_query = email_query.where(FulfillmentEmail.status == email_status)
    if start_dt:
        email_query = email_query.where(FulfillmentEmail.updated_at >= start_dt)
    if end_dt:
        email_query = email_query.where(FulfillmentEmail.updated_at < end_dt)
    failed_fulfillment_emails = db.scalars(email_query.limit(30)).all()

    return_to = "/admin"
    if request.url.query:
        return_to = f"/admin?{request.url.query}"

    return render(
        "pages/admin_dashboard.html",
        request,
        {
            "stats": stats,
            "recent_templates": recent_templates,
            "failed_webhook_events": failed_webhook_events,
            "failed_fulfillment_emails": failed_fulfillment_emails,
            "webhook_filters": {
                "status": webhook_status,
                "start_date": start_date,
                "end_date": end_date,
            },
            "email_filters": {
                "status": email_status,
                "start_date": start_date,
                "end_date": end_date,
            },
            "return_to": return_to,
            "meta_title": "Admin Dashboard",
            "meta_description": "Marketplace admin operations overview.",
        },
    )


@router.post("/webhooks/resolve")
def resolve_webhook_event(
    db: Session = Depends(get_db),
    webhook_event_id: int = Form(...),
    return_to: str = Form("/admin"),
):
    webhook_event = db.get(StripeWebhookEvent, webhook_event_id)
    if not webhook_event:
        raise HTTPException(status_code=404, detail="Webhook event not found.")

    webhook_event.status = "resolved"
    if not webhook_event.error_message:
        webhook_event.error_message = "Manually resolved from admin dashboard."
    db.commit()
    return RedirectResponse(url=_safe_return_to(return_to), status_code=303)


@router.post("/fulfillment/retry")
def retry_fulfillment_email(
    db: Session = Depends(get_db),
    fulfillment_email_id: int = Form(...),
    return_to: str = Form("/admin"),
):
    email_log = db.scalar(
        select(FulfillmentEmail)
        .options(joinedload(FulfillmentEmail.purchase).joinedload(Purchase.customer), joinedload(FulfillmentEmail.purchase).joinedload(Purchase.template))
        .where(FulfillmentEmail.id == fulfillment_email_id)
    )
    if not email_log:
        raise HTTPException(status_code=404, detail="Fulfillment email log not found.")

    send_purchase_fulfillment_email(db, email_log.purchase, settings, force_retry=True)
    return RedirectResponse(url=_safe_return_to(return_to), status_code=303)
