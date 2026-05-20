import json
import random
import re

import httpx
import stripe
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Customer, Purchase, StripeWebhookEvent, Template
from app.services.fulfillment import send_purchase_fulfillment_email
from app.services.marketplace import (
    filtered_template_query,
    get_related_templates,
    get_template_by_slug,
    list_categories,
    list_industries,
    paginate_templates,
)
from app.services.preview_demo_content import get_rich_demo_content
from app.services.preview_demos import DEMO_PAGES, get_page_content, get_preview_demo
from app.services.theme_packages import build_theme_zip_bytes
from app.utils.download_tokens import create_download_token, verify_download_token
from app.utils.query_params import OptionalFloatQuery
from app.utils.templating import render

router = APIRouter()
settings = get_settings()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PREVIEW_GRADIENTS = [
    ("#10B981", "#047857"),
    ("#047857", "#111827"),
    ("#0EA5E9", "#0F172A"),
    ("#14B8A6", "#047857"),
    ("#4F46E5", "#111827"),
]


def _configure_stripe() -> None:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured. Set STRIPE_SECRET_KEY.")
    stripe.api_key = settings.stripe_secret_key


def _mark_purchase_paid(db: Session, purchase: Purchase) -> None:
    if purchase.status == "paid":
        send_purchase_fulfillment_email(db, purchase, settings)
        return
    purchase.status = "paid"
    purchase.template.sales_count += 1
    db.commit()
    db.refresh(purchase)
    send_purchase_fulfillment_email(db, purchase, settings)


def _build_preview_branding(slug: str) -> dict[str, str]:
    palette = PREVIEW_GRADIENTS[abs(hash(slug)) % len(PREVIEW_GRADIENTS)]
    return {"accent_start": palette[0], "accent_end": palette[1]}


def _build_preview_sections(template: Template) -> list[dict[str, str]]:
    base_sections = [
        {
            "title": "Conversion-first Homepage",
            "description": "Structured hero, social proof, and action-focused sections built to turn visitors into leads.",
        },
        {
            "title": "Service and Offer Pages",
            "description": "Clear service blocks, pricing highlights, and trust content tailored for local business buyers.",
        },
        {
            "title": "Mobile-first Performance",
            "description": "Fast-loading layouts with responsive content blocks designed for every device size.",
        },
    ]
    dynamic_features = [feature.label for feature in template.features[:3]]
    for feature_label in dynamic_features:
        base_sections.append(
            {
                "title": feature_label,
                "description": f"Included in {template.title} to support a modern and scalable {template.industry.name.lower()} website.",
            }
        )
    return base_sections[:6]


def _build_preview_customizer_defaults(template: Template) -> dict[str, str | int]:
    branding = _build_preview_branding(template.slug)
    topology_by_category = {
        "technology": "split",
        "real-estate": "cards",
        "nonprofit": "minimal",
    }
    typography_by_industry = {
        "it-consulting": "geometric",
        "tourism": "classic",
        "hospitality": "classic",
    }
    density = "compact" if template.category.slug in {"technology", "services"} else "comfortable"
    return {
        "accent_start": branding["accent_start"],
        "accent_end": branding["accent_end"],
        "surface_bg": "#f8fafc",
        "text_color": "#0f172a",
        "radius": 18,
        "density": density,
        "typography": typography_by_industry.get(template.industry.slug, "modern"),
        "topology": topology_by_category.get(template.category.slug, "cards"),
    }


@router.get("/")
def homepage(request: Request, db: Session = Depends(get_db)):
    featured = db.scalars(select(Template).where(Template.is_featured.is_(True)).limit(6)).all()
    best_sellers = db.scalars(select(Template).where(Template.is_best_seller.is_(True)).limit(6)).all()
    new_templates = db.scalars(select(Template).where(Template.is_new.is_(True)).limit(6)).all()
    return render(
        "pages/home.html",
        request,
        {
            "featured_templates": featured,
            "best_sellers": best_sellers,
            "new_templates": new_templates,
            "categories": list_categories(db),
            "industries": list_industries(db),
            "meta_title": "Premium Website Templates for Local Businesses",
            "meta_description": "Launch faster with premium marketplace templates, setup services, and hosting.",
        },
    )


MARKETPLACE_SORTS = frozenset({"newest", "price_low_high", "price_high_low"})


@router.get("/marketplace")
def marketplace(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    min_price: OptionalFloatQuery = None,
    max_price: OptionalFloatQuery = None,
    sort: str = Query(default="newest"),
    page: int = Query(default=1),
):
    if sort not in MARKETPLACE_SORTS:
        sort = "newest"
    query = filtered_template_query(category, industry, q, min_price, max_price, sort)
    pagination = paginate_templates(db, query, page=page, per_page=9)
    return render(
        "pages/marketplace.html",
        request,
        {
            "pagination": pagination,
            "filters": {
                "q": q or "",
                "category": category or "",
                "industry": industry or "",
                "min_price": min_price if min_price is not None else "",
                "max_price": max_price if max_price is not None else "",
                "sort": sort,
            },
            "categories": list_categories(db),
            "industries": list_industries(db),
            "meta_title": "Browse Marketplace Templates",
            "meta_description": "Filter by category, industry, and pricing to find your perfect site template.",
        },
    )


@router.get("/categories/{slug}")
def category_page(request: Request, slug: str, db: Session = Depends(get_db), page: int = 1):
    pagination = paginate_templates(db, filtered_template_query(category_slug=slug), page=page, per_page=9)
    return render(
        "pages/category.html",
        request,
        {
            "pagination": pagination,
            "category_slug": slug,
            "categories": list_categories(db),
            "industries": list_industries(db),
            "meta_title": f"{slug.replace('-', ' ').title()} Templates",
            "meta_description": "Browse templates by category.",
        },
    )


@router.get("/industries/{slug}")
def industry_page(request: Request, slug: str, db: Session = Depends(get_db), page: int = 1):
    pagination = paginate_templates(db, filtered_template_query(industry_slug=slug), page=page, per_page=9)
    return render(
        "pages/industry.html",
        request,
        {
            "pagination": pagination,
            "industry_slug": slug,
            "categories": list_categories(db),
            "industries": list_industries(db),
            "meta_title": f"{slug.replace('-', ' ').title()} Website Templates",
            "meta_description": "Explore website templates by industry.",
        },
    )


@router.get("/templates/{slug}")
def template_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return render(
        "pages/template_detail.html",
        request,
        {
            "template_item": template,
            "related_templates": get_related_templates(db, template),
            "meta_title": f"{template.title} Template",
            "meta_description": template.description[:160],
        },
    )


@router.get("/preview/{slug}")
def live_preview(request: Request, slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return render(
        "pages/live_preview.html",
        request,
        {
            "template_item": template,
            "preview_customizer": _build_preview_customizer_defaults(template),
            "meta_title": f"Preview {template.title}",
            "meta_description": "Live preview",
        },
    )


def _render_preview_site(request: Request, template: Template, page: str = "home"):
    demo = get_preview_demo(template, page)
    return render(
        f"demos/layouts/{demo.layout}.html",
        request,
        {
            "template_item": template,
            "demo": demo,
            "demo_page_content": get_page_content(demo),
            "demo_rich": get_rich_demo_content(template.slug),
            "preview_customizer": _build_preview_customizer_defaults(template),
            "preview_sections": _build_preview_sections(template),
            "meta_title": f"{template.title} Demo — {page.title()}",
            "meta_description": f"Live website preview for {template.title}.",
        },
    )


@router.get("/preview-site/{slug}")
def preview_site(request: Request, slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _render_preview_site(request, template, "home")


@router.get("/preview-site/{slug}/{page}")
def preview_site_page(request: Request, slug: str, page: str, db: Session = Depends(get_db)):
    if page not in DEMO_PAGES or page == "home":
        raise HTTPException(status_code=404, detail="Demo page not found")
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _render_preview_site(request, template, page)


@router.get("/pricing")
def pricing_page(request: Request):
    return render(
        "pages/pricing.html",
        request,
        {
            "meta_title": "Licensing and Pricing",
            "meta_description": "Compare template licensing tiers and services.",
        },
    )


@router.get("/services/setup")
def setup_services(request: Request):
    return render(
        "pages/services_setup.html",
        request,
        {"meta_title": "Website Setup Services", "meta_description": "Fast-launch website setup services."},
    )


@router.get("/services/hosting")
def hosting_services(request: Request):
    return render(
        "pages/services_hosting.html",
        request,
        {"meta_title": "Managed Hosting Services", "meta_description": "Managed hosting for local businesses."},
    )


@router.get("/contact")
def contact_page(request: Request):
    captcha_a = random.randint(1, 9)
    captcha_b = random.randint(1, 9)
    return render(
        "pages/contact.html",
        request,
        {
            "meta_title": "Contact & Customization",
            "meta_description": "Request customization and consulting support.",
            "captcha_a": captcha_a,
            "captcha_b": captcha_b,
        },
    )


@router.post("/api/contact")
async def contact_submit(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    website: str = Form(""),
    captcha_a: int = Form(...),
    captcha_b: int = Form(...),
    captcha_answer: str = Form(...),
):
    """
    Receive contact form and proxy to ConsultOps integration API.
    Keeps INTEGRATION_API_KEY server-side only.
    Uses honeypot + math question to reduce spam.
    """
    if website and website.strip():
        raise HTTPException(status_code=400, detail="Invalid submission. Please try again or email us directly.")

    try:
        answer = int(captcha_answer.strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Please answer the math question correctly.")
    if answer != captcha_a + captcha_b:
        raise HTTPException(status_code=400, detail="Please answer the math question correctly.")

    if not settings.consultops_base_url or not settings.integration_api_key:
        raise HTTPException(
            status_code=503,
            detail="Contact form is not configured. Please try again later or email us directly.",
        )

    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    notes = message.strip()

    url = f"{settings.consultops_base_url.rstrip('/')}/api/integrations/contacts"
    payload = {"name": name.strip(), "email": email.strip(), "notes": notes}
    headers = {"Content-Type": "application/json", "X-API-Key": settings.integration_api_key}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail="Unable to submit. Please try again or email us directly.",
            ) from exc

    if not (200 <= response.status_code < 300):
        raise HTTPException(
            status_code=502,
            detail="Failed to submit. Please try again or email us directly.",
        )

    return JSONResponse(
        status_code=201,
        content={"success": True, "message": "Thank you. Your message was sent successfully."},
    )


@router.get("/faq")
def faq_page(request: Request):
    return render(
        "pages/faq.html",
        request,
        {"meta_title": "Frequently Asked Questions", "meta_description": "Answers for templates, licensing, and services."},
    )


@router.get("/about")
def about_page(request: Request):
    return render(
        "pages/about.html",
        request,
        {"meta_title": "About Mateo ConsultOps Themes", "meta_description": "Marketplace mission and business focus."},
    )


@router.get("/downloads")
def my_downloads_page(request: Request, db: Session = Depends(get_db), email: str = Query(default="")):
    normalized_email = email.strip().lower()
    purchases_with_tokens: list[dict] = []
    customer = None

    if normalized_email:
        customer = db.scalar(
            select(Customer)
            .options(joinedload(Customer.purchases).joinedload(Purchase.template))
            .where(Customer.email == normalized_email)
        )
        if customer:
            paid_purchases = sorted(
                [purchase for purchase in customer.purchases if purchase.status == "paid"],
                key=lambda purchase: purchase.created_at,
                reverse=True,
            )
            for purchase in paid_purchases:
                token = create_download_token(
                    secret_key=settings.secret_key,
                    purchase_id=purchase.id,
                    template_slug=purchase.template.slug,
                    customer_email=customer.email,
                    expires_in_seconds=7200,
                )
                purchases_with_tokens.append({"purchase": purchase, "download_token": token})

    return render(
        "pages/my_downloads.html",
        request,
        {
            "query_email": normalized_email,
            "customer": customer,
            "purchases_with_tokens": purchases_with_tokens,
            "meta_title": "My Downloads",
            "meta_description": "Access your paid template downloads.",
        },
    )


@router.post("/downloads/resend")
def resend_download_email(
    db: Session = Depends(get_db),
    purchase_id: int = Form(...),
    email: str = Form(...),
):
    normalized_email = email.strip().lower()
    purchase = db.scalar(
        select(Purchase)
        .options(joinedload(Purchase.customer), joinedload(Purchase.template))
        .where(Purchase.id == purchase_id)
    )
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found.")
    if purchase.customer.email.lower().strip() != normalized_email:
        raise HTTPException(status_code=403, detail="Purchase email mismatch.")
    if purchase.status != "paid":
        raise HTTPException(status_code=403, detail="Purchase is not paid.")

    send_purchase_fulfillment_email(db, purchase, settings, force_retry=True)
    return RedirectResponse(url=f"/downloads?email={normalized_email}", status_code=303)


@router.get("/purchase/{slug}")
def purchase_page(request: Request, slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    download_token = ""
    payment_verified = False
    payment_error = ""
    canceled = request.query_params.get("canceled") == "1"
    success = request.query_params.get("success") == "1"
    purchase_id = request.query_params.get("purchase_id")
    session_id = request.query_params.get("session_id")

    if success and purchase_id and session_id:
        try:
            purchase = db.get(Purchase, int(purchase_id))
        except ValueError:
            purchase = None
        if not purchase or purchase.template_id != template.id:
            payment_error = "Purchase record was not found for this template."
        else:
            try:
                _configure_stripe()
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                session_purchase_id = str(checkout_session.get("metadata", {}).get("purchase_id", ""))
                if checkout_session.get("payment_status") == "paid" and session_purchase_id == str(purchase.id):
                    _mark_purchase_paid(db, purchase)
                    download_token = create_download_token(
                        secret_key=settings.secret_key,
                        purchase_id=purchase.id,
                        template_slug=template.slug,
                        customer_email=purchase.customer.email,
                        expires_in_seconds=7200,
                    )
                    payment_verified = True
                else:
                    payment_error = "Payment is not confirmed yet. Please refresh in a few seconds."
            except stripe.error.StripeError as exc:
                payment_error = f"Stripe verification failed: {str(exc)}"

    return render(
        "pages/purchase.html",
        request,
        {
            "template_item": template,
            "download_token": download_token,
            "payment_verified": payment_verified,
            "payment_error": payment_error,
            "canceled": canceled,
            "stripe_publishable_key": settings.stripe_publishable_key,
            "meta_title": f"Purchase {template.title}",
            "meta_description": "Secure Stripe checkout with paid download access.",
        },
    )


@router.post("/purchase/{slug}")
def purchase_template(
    slug: str,
    db: Session = Depends(get_db),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    license_type: str = Form("Standard"),
    agree_terms: str | None = Form(default=None),
):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if agree_terms is None:
        raise HTTPException(status_code=400, detail="You must agree to terms before purchasing.")

    normalized_email = email.strip().lower()
    customer = db.scalar(select(Customer).where(Customer.email == normalized_email))
    full_name = f"{first_name.strip()} {last_name.strip()}".strip()

    if customer:
        customer.name = full_name
        customer.company = company.strip()
    else:
        customer = Customer(name=full_name, email=normalized_email, company=company.strip())
        db.add(customer)
        db.flush()

    purchase = Purchase(
        template_id=template.id,
        customer_id=customer.id,
        amount=template.price,
        license_type=license_type,
        status="pending",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    try:
        _configure_stripe()
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=normalized_email,
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(round(template.price * 100)),
                        "product_data": {
                            "name": f"{template.title} Theme License ({license_type})",
                            "description": template.description,
                        },
                    },
                }
            ],
            metadata={
                "purchase_id": str(purchase.id),
                "template_slug": template.slug,
            },
            success_url=f"{settings.base_url}/purchase/{template.slug}?success=1&purchase_id={purchase.id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.base_url}/purchase/{template.slug}?canceled=1",
        )
    except stripe.error.StripeError as exc:
        purchase.status = "failed"
        db.commit()
        raise HTTPException(status_code=502, detail=f"Stripe checkout session error: {str(exc)}") from exc

    return RedirectResponse(url=checkout_session.url, status_code=303)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    _configure_stripe()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
        else:
            event = stripe.Event.construct_from(json.loads(payload.decode("utf-8")), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError):
        return JSONResponse({"received": False}, status_code=400)

    event_id = str(event.get("id", ""))
    existing_event = db.scalar(select(StripeWebhookEvent).where(StripeWebhookEvent.event_id == event_id))
    if existing_event:
        return JSONResponse({"received": True, "duplicate": True})

    safe_event_id = event_id or f"unknown-{abs(hash(payload))}"
    webhook_log = StripeWebhookEvent(
        event_id=safe_event_id,
        event_type=str(event.get("type", "unknown")),
        payload=payload.decode("utf-8", errors="ignore"),
        status="received",
    )
    db.add(webhook_log)
    db.flush()

    if event.get("type") == "checkout.session.completed":
        session_data = event.get("data", {}).get("object", {})
        if session_data.get("payment_status") == "paid":
            metadata = session_data.get("metadata", {})
            try:
                purchase_id = int(metadata.get("purchase_id", 0))
            except (TypeError, ValueError):
                purchase_id = 0
            purchase = db.get(Purchase, purchase_id)
            if purchase and metadata.get("template_slug") == purchase.template.slug:
                _mark_purchase_paid(db, purchase)
                webhook_log.purchase_id = purchase.id
                webhook_log.status = "processed"
            else:
                webhook_log.status = "ignored"
                webhook_log.error_message = "purchase not found or template slug mismatch"
        else:
            webhook_log.status = "ignored"
            webhook_log.error_message = "payment status is not paid"
    else:
        webhook_log.status = "ignored"
        webhook_log.error_message = "unsupported event type"

    db.commit()
    return JSONResponse({"received": True})


@router.get("/downloads/theme/{slug}")
def download_theme_package(slug: str, token: str, db: Session = Depends(get_db)):
    payload = verify_download_token(token, secret_key=get_settings().secret_key)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid or expired download token.")
    if payload.get("template_slug") != slug:
        raise HTTPException(status_code=403, detail="Download token does not match requested template.")

    purchase_id = int(payload.get("purchase_id", 0))
    customer_email = str(payload.get("customer_email", "")).strip().lower()
    purchase = db.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found.")
    if purchase.status != "paid":
        raise HTTPException(status_code=403, detail="Purchase is not in paid status.")
    if purchase.customer.email.lower().strip() != customer_email:
        raise HTTPException(status_code=403, detail="Download token does not match this purchase.")
    if purchase.template.slug != slug:
        raise HTTPException(status_code=403, detail="Purchased template mismatch.")

    zip_bytes, filename = build_theme_zip_bytes(purchase.template)
    content = StreamingResponse(iter([zip_bytes]), media_type="application/zip")
    content.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return content
