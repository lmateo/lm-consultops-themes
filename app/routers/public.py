import json
import re
import httpx
import stripe
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Customer, Purchase, StripeWebhookEvent, Template
from app.services.fulfillment import send_purchase_fulfillment_email
from app.services.download_access import (
    download_link_limits_ui_sentence,
    issue_download_token_for_purchase,
    validate_download_token_access,
)
from app.services.marketplace import (
    TEMPLATE_SORTS,
    filtered_template_query,
    get_categories_with_counts,
    get_category_by_slug,
    get_industry_by_slug,
    get_featured_studios,
    get_popular_by_category_sections,
    get_related_templates,
    get_template_by_slug,
    list_categories,
    list_industries,
    paginate_templates,
)
from app.utils.query_params import build_page_urls
from app.services.crafto_demos import DEMO_PAGES, get_crafto_demo_or_default
from app.services.crafto_preview_wrap import load_wrapped_crafto_preview
from app.services.preview_demos import list_template_search_hints
from app.services.theme_packages import build_theme_zip_bytes
from app.services.turnstile import turnstile_enabled, verify_turnstile_token
from app.utils.query_params import OptionalFloatQuery
from app.utils.templating import render

router = APIRouter()
settings = get_settings()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_PURCHASE_TYPE = "Theme"

PREVIEW_GRADIENTS = [
    ("#10B981", "#047857"),
    ("#047857", "#111827"),
    ("#0EA5E9", "#0F172A"),
    ("#14B8A6", "#047857"),
    ("#4F46E5", "#111827"),
]


def _event_as_dict(event: object) -> dict:
    if isinstance(event, dict):
        return event
    to_dict_recursive = getattr(event, "to_dict_recursive", None)
    if callable(to_dict_recursive):
        try:
            converted = to_dict_recursive()
            if isinstance(converted, dict):
                return converted
            nested = getattr(converted, "to_dict_recursive", None)
            if callable(nested):
                converted_nested = nested()
                if isinstance(converted_nested, dict):
                    return converted_nested
        except Exception:  # noqa: BLE001
            pass
    to_dict = getattr(event, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return converted
        except Exception:  # noqa: BLE001
            pass
    raw_data = getattr(event, "_data", None)
    if isinstance(raw_data, dict):
        return raw_data
    try:
        maybe = dict(event)  # type: ignore[arg-type]
        if isinstance(maybe, dict):
            return maybe
    except Exception:  # noqa: BLE001
        pass
    return {}


def _resolve_contacts_api_url() -> str:
    configured_url = (settings.consultops_contacts_api_url or "").strip()
    if configured_url:
        return configured_url
    base_url = (settings.consultops_base_url or "").strip()
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/api/integrations/contacts"


def _configure_stripe() -> None:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured. Set STRIPE_SECRET_KEY.")
    stripe.api_key = settings.stripe_secret_key


def _mark_purchase_paid(db: Session, purchase: Purchase) -> None:
    if purchase.status == "paid":
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
    featured = db.scalars(
        select(Template)
        .options(joinedload(Template.category), joinedload(Template.industry))
        .where(Template.is_featured.is_(True))
        .order_by(Template.sales_count.desc())
        .limit(6)
    ).all()
    best_sellers = db.scalars(
        select(Template)
        .options(joinedload(Template.category), joinedload(Template.industry))
        .order_by(Template.sales_count.desc())
        .limit(6)
    ).all()
    new_templates = db.scalars(
        select(Template)
        .options(joinedload(Template.category), joinedload(Template.industry))
        .where(Template.is_new.is_(True))
        .order_by(Template.last_updated.desc())
        .limit(6)
    ).all()
    popular_sections = get_popular_by_category_sections(db, per_category=4, sort="bestselling")
    return render(
        "pages/home.html",
        request,
        {
            "featured_templates": featured,
            "best_sellers": best_sellers,
            "new_templates": new_templates,
            "popular_sections": popular_sections,
            "categories": list_categories(db),
            "industries": list_industries(db),
            "template_search_hints": list_template_search_hints(),
            "meta_title": "Premium Website Templates for Local Businesses",
            "meta_description": "Launch faster with premium website templates and setup services.",
        },
    )


@router.get("/popular")
def popular_by_category(
    request: Request,
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    q: str | None = Query(default=None),
    min_price: OptionalFloatQuery = None,
    max_price: OptionalFloatQuery = None,
    sort: str = Query(default="bestselling"),
    page: int = Query(default=1),
):
    if sort not in TEMPLATE_SORTS:
        sort = "bestselling"

    active_category = get_category_by_slug(db, category) if category else None
    query = filtered_template_query(category, industry, q, min_price, max_price, sort)
    pagination = paginate_templates(db, query, page=page, per_page=30)
    filter_params = {
        "q": q or "",
        "category": category or "",
        "industry": industry or "",
        "min_price": min_price if min_price is not None else "",
        "max_price": max_price if max_price is not None else "",
        "sort": sort,
    }
    page_urls = build_page_urls("/popular", pagination["page_count"], pagination["page"], **filter_params)

    if active_category:
        page_title = f"Featured {active_category.name} Templates"
        meta_title = f"Featured {active_category.name} Website Templates"
    else:
        page_title = "Featured Website Templates"
        meta_title = "Featured Website Templates by Category"

    return render(
        "pages/popular.html",
        request,
        {
            "active_category": active_category,
            "pagination": pagination,
            "page_urls": page_urls,
            "filters": filter_params,
            "categories": list_categories(db),
            "categories_with_counts": get_categories_with_counts(db),
            "industries": list_industries(db),
            "featured_studios": get_featured_studios(db),
            "sort": sort,
            "page_title": page_title,
            "meta_title": meta_title,
            "meta_description": "Browse featured website templates with live previews.",
        },
    )


@router.get("/marketplace")
def marketplace_redirect(request: Request):
    query = request.url.query
    target = f"/popular?{query}" if query else "/popular"
    return RedirectResponse(url=target, status_code=301)


@router.get("/categories/{slug}")
def category_page(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    page: int = 1,
    sort: str = Query(default="bestselling"),
):
    category = get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if sort not in TEMPLATE_SORTS:
        sort = "bestselling"

    pagination = paginate_templates(
        db, filtered_template_query(category_slug=slug, sort=sort), page=page, per_page=30
    )
    page_urls = build_page_urls(f"/categories/{slug}", pagination["page_count"], pagination["page"], sort=sort)
    return render(
        "pages/category.html",
        request,
        {
            "pagination": pagination,
            "page_urls": page_urls,
            "category": category,
            "sort": sort,
            "categories_with_counts": get_categories_with_counts(db),
            "featured_studios": get_featured_studios(db),
            "meta_title": f"{category.name} Templates",
            "meta_description": category.description or f"Browse popular {category.name.lower()} website templates.",
        },
    )


@router.get("/industries/{slug}")
def industry_page(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    page: int = 1,
    sort: str = Query(default="bestselling"),
):
    industry = get_industry_by_slug(db, slug)
    if not industry:
        raise HTTPException(status_code=404, detail="Industry not found")
    if sort not in TEMPLATE_SORTS:
        sort = "bestselling"

    pagination = paginate_templates(
        db, filtered_template_query(industry_slug=slug, sort=sort), page=page, per_page=9
    )
    page_urls = build_page_urls(f"/industries/{slug}", pagination["page_count"], pagination["page"], sort=sort)
    return render(
        "pages/industry.html",
        request,
        {
            "pagination": pagination,
            "page_urls": page_urls,
            "industry": industry,
            "sort": sort,
            "meta_title": f"{industry.name} Website Templates",
            "meta_description": industry.description or f"Explore website templates for {industry.name.lower()}.",
        },
    )


@router.get("/templates/{slug}")
def template_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    crafto = get_crafto_demo_or_default(template.slug)
    return render(
        "pages/template_detail.html",
        request,
        {
            "template_item": template,
            "related_templates": get_related_templates(db, template),
            "crafto_demo": crafto,
            "meta_title": f"{template.title} Template",
            "meta_description": template.description[:160],
        },
    )


def _preview_page_redirect(slug: str, page: str = "home") -> RedirectResponse:
    return RedirectResponse(url=f"/preview/{slug}/{page}", status_code=302)


@router.get("/preview/{slug}")
def live_preview(slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _preview_page_redirect(template.slug, "home")


@router.get("/preview/{slug}/{page}")
def live_preview_page(slug: str, page: str, db: Session = Depends(get_db)):
    if page not in DEMO_PAGES:
        raise HTTPException(status_code=404, detail="Demo page not found")
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        html = load_wrapped_crafto_preview(template, page)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Crafto demo file not found") from exc
    return HTMLResponse(content=html)


@router.get("/preview-site/{slug}")
def preview_site(slug: str, db: Session = Depends(get_db)):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _preview_page_redirect(template.slug, "home")


@router.get("/preview-site/{slug}/{page}")
def preview_site_page(slug: str, page: str, db: Session = Depends(get_db)):
    if page not in DEMO_PAGES or page == "home":
        raise HTTPException(status_code=404, detail="Demo page not found")
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _preview_page_redirect(template.slug, page)


@router.get("/pricing")
def pricing_page(request: Request):
    return render(
        "pages/pricing.html",
        request,
        {
            "meta_title": "Theme Pricing",
            "meta_description": "Compare template prices and optional launch services.",
        },
    )


@router.get("/services/setup")
def setup_services(request: Request):
    return render(
        "pages/services_setup.html",
        request,
        {"meta_title": "Website Setup Services", "meta_description": "Fast-launch website setup services."},
    )


@router.get("/contact")
def contact_page(request: Request):
    return render(
        "pages/contact.html",
        request,
        {
            "meta_title": "Contact & Customization",
            "meta_description": "Request customization and consulting support.",
            "turnstile_site_key": settings.turnstile_site_key if turnstile_enabled() else "",
        },
    )


@router.get("/health/contact-config")
def contact_config_health():
    contacts_api_url = _resolve_contacts_api_url()
    has_contacts_api_url = bool(contacts_api_url)
    has_integration_api_key = bool((settings.integration_api_key or "").strip())
    has_turnstile = turnstile_enabled()

    return JSONResponse(
        status_code=200,
        content={
            "contact_form_ready": has_contacts_api_url and has_integration_api_key and has_turnstile,
            "has_contacts_api_url": has_contacts_api_url,
            "has_integration_api_key": has_integration_api_key,
            "has_turnstile": has_turnstile,
        },
    )


@router.post("/api/contact")
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    website: str = Form(""),
    cf_turnstile_response: str = Form("", alias="cf-turnstile-response"),
):
    """
    Receive contact form and proxy to ConsultOps integration API.
    Keeps INTEGRATION_API_KEY server-side only.
    Uses honeypot + Cloudflare Turnstile to reduce spam.
    """
    if website and website.strip():
        raise HTTPException(status_code=400, detail="Invalid submission. Please try again or email us directly.")

    if turnstile_enabled():
        remote_ip = request.client.host if request.client else None
        if not await verify_turnstile_token(cf_turnstile_response, remote_ip=remote_ip):
            raise HTTPException(status_code=400, detail="Security verification failed. Please try again.")

    contacts_api_url = _resolve_contacts_api_url()
    if not contacts_api_url or not settings.integration_api_key:
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

    payload = {"name": name.strip(), "email": email.strip(), "notes": notes}
    headers = {"Content-Type": "application/json", "X-API-Key": settings.integration_api_key}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(contacts_api_url, headers=headers, json=payload, timeout=30.0)
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
        {"meta_title": "Frequently Asked Questions", "meta_description": "Answers for templates, pricing, and services."},
    )


@router.get("/about")
def about_page(request: Request):
    return render(
        "pages/about.html",
        request,
        {"meta_title": "About Mateo ConsultOps Themes", "meta_description": "Our mission and business focus."},
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
                token = issue_download_token_for_purchase(
                    db,
                    settings=settings,
                    purchase=purchase,
                    expires_in_seconds=settings.download_link_ttl_seconds,
                )
                purchases_with_tokens.append({"purchase": purchase, "download_token": token})

    return render(
        "pages/my_downloads.html",
        request,
        {
            "query_email": normalized_email,
            "customer": customer,
            "purchases_with_tokens": purchases_with_tokens,
            "download_link_limits_ui_sentence": download_link_limits_ui_sentence(settings),
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

    stripe_configured = bool(settings.stripe_secret_key)
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
                    download_token = issue_download_token_for_purchase(
                        db,
                        settings=settings,
                        purchase=purchase,
                        expires_in_seconds=settings.download_link_ttl_seconds,
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
            "stripe_configured": stripe_configured,
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
    agree_terms: str | None = Form(default=None),
):
    template = get_template_by_slug(db, slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if agree_terms is None:
        raise HTTPException(status_code=400, detail="You must agree to terms before purchasing.")

    normalized_first_name = first_name.strip()
    normalized_last_name = last_name.strip()
    normalized_email = email.strip().lower()
    normalized_company = company.strip()

    if not normalized_first_name or not normalized_last_name:
        raise HTTPException(status_code=400, detail="First name and last name are required.")
    if not normalized_email or not EMAIL_REGEX.match(normalized_email):
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    # Validate Stripe credentials before writing pending purchase records.
    _configure_stripe()

    customer = db.scalar(select(Customer).where(Customer.email == normalized_email))
    full_name = f"{normalized_first_name} {normalized_last_name}".strip()

    if customer:
        customer.name = full_name
        customer.company = normalized_company
    else:
        customer = Customer(name=full_name, email=normalized_email, company=normalized_company)
        db.add(customer)
        db.flush()

    purchase = Purchase(
        template_id=template.id,
        customer_id=customer.id,
        amount=template.price,
        license_type=DEFAULT_PURCHASE_TYPE,
        status="pending",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    try:
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
                            "name": f"{template.title} Theme",
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
    except (stripe.error.StripeError, Exception) as exc:  # noqa: BLE001
        purchase.status = "failed"
        db.commit()
        detail = "Stripe checkout session error"
        if isinstance(exc, stripe.error.StripeError):
            detail = f"{detail}: {str(exc)}"
        raise HTTPException(status_code=502, detail=detail) from exc

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

    event_data = _event_as_dict(event)
    event_id = str(event_data.get("id", ""))
    existing_event = db.scalar(select(StripeWebhookEvent).where(StripeWebhookEvent.event_id == event_id))
    if existing_event:
        return JSONResponse({"received": True, "duplicate": True})

    safe_event_id = event_id or f"unknown-{abs(hash(payload))}"
    webhook_log = StripeWebhookEvent(
        event_id=safe_event_id,
        event_type=str(event_data.get("type", "unknown")),
        payload=payload.decode("utf-8", errors="ignore"),
        status="received",
    )
    db.add(webhook_log)
    db.flush()

    if event_data.get("type") == "checkout.session.completed":
        session_data = event_data.get("data", {}).get("object", {})
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
    try:
        purchase = validate_download_token_access(
            db,
            settings=get_settings(),
            template_slug=slug,
            token=token,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    zip_bytes, filename = build_theme_zip_bytes(purchase.template)
    content = StreamingResponse(iter([zip_bytes]), media_type="application/zip")
    content.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return content
