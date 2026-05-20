from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    templates: Mapped[list["Template"]] = relationship(back_populates="category", cascade="all,delete")


class Industry(Base, TimestampMixin):
    __tablename__ = "industries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    templates: Mapped[list["Template"]] = relationship(back_populates="industry", cascade="all,delete")


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industries.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, default=49.0)
    rating: Mapped[float] = mapped_column(Float, default=4.8)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_best_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    preview_url: Mapped[str] = mapped_column(String(500), default="")
    thumbnail_url: Mapped[str] = mapped_column(String(500), default="")
    demo_pages: Mapped[str] = mapped_column(Text, default="")
    tech_stack: Mapped[str] = mapped_column(String(250), default="FastAPI, Jinja2, Tailwind")
    features_text: Mapped[str] = mapped_column(Text, default="")
    setup_available: Mapped[bool] = mapped_column(Boolean, default=True)
    hosting_available: Mapped[bool] = mapped_column(Boolean, default=True)
    maintenance_available: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped[Category] = relationship(back_populates="templates")
    industry: Mapped[Industry] = relationship(back_populates="templates")
    images: Mapped[list["TemplateImage"]] = relationship(back_populates="template", cascade="all,delete")
    versions: Mapped[list["TemplateVersion"]] = relationship(back_populates="template", cascade="all,delete")
    features: Mapped[list["Feature"]] = relationship(back_populates="template", cascade="all,delete")
    reviews: Mapped[list["Review"]] = relationship(back_populates="template", cascade="all,delete")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="template")
    live_previews: Mapped[list["LivePreview"]] = relationship(back_populates="template", cascade="all,delete")


class TemplateImage(Base, TimestampMixin):
    __tablename__ = "template_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[Template] = relationship(back_populates="images")


class TemplateVersion(Base, TimestampMixin):
    __tablename__ = "template_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    changelog: Mapped[str] = mapped_column(Text, default="")

    template: Mapped[Template] = relationship(back_populates="versions")


class Feature(Base, TimestampMixin):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    template: Mapped[Template] = relationship(back_populates="features")


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    comment: Mapped[str] = mapped_column(Text, default="")

    template: Mapped[Template] = relationship(back_populates="reviews")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    company: Mapped[str] = mapped_column(String(140), default="")

    purchases: Mapped[list["Purchase"]] = relationship(back_populates="customer")


class Purchase(Base, TimestampMixin):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    license_type: Mapped[str] = mapped_column(String(100), default="Standard")
    status: Mapped[str] = mapped_column(String(50), default="paid")

    template: Mapped[Template] = relationship(back_populates="purchases")
    customer: Mapped[Customer] = relationship(back_populates="purchases")
    webhook_events: Mapped[list["StripeWebhookEvent"]] = relationship(back_populates="purchase", cascade="all,delete")
    fulfillment_emails: Mapped[list["FulfillmentEmail"]] = relationship(back_populates="purchase", cascade="all,delete")


class Inquiry(Base, TimestampMixin):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(140), default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    template_slug: Mapped[str] = mapped_column(String(220), default="")


class ServiceAddon(Base, TimestampMixin):
    __tablename__ = "service_addons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float, default=99.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LivePreview(Base, TimestampMixin):
    __tablename__ = "live_previews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    device_mode: Mapped[str] = mapped_column(String(50), default="desktop")

    template: Mapped[Template] = relationship(back_populates="live_previews")


class StripeWebhookEvent(Base, TimestampMixin):
    __tablename__ = "stripe_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="received")
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("purchases.id"), nullable=True)
    payload: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")

    purchase: Mapped["Purchase | None"] = relationship(back_populates="webhook_events")


class FulfillmentEmail(Base, TimestampMixin):
    __tablename__ = "fulfillment_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), nullable=False, index=True)
    email_type: Mapped[str] = mapped_column(String(80), default="download_access")
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    purchase: Mapped["Purchase"] = relationship(back_populates="fulfillment_emails")
