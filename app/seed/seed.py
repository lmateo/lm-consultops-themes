from datetime import datetime, timedelta
import re

from sqlalchemy import delete, select, update

from app.core.database import Base, SessionLocal, engine
from app.models import Category, Feature, Industry, ServiceAddon, Template, TemplateImage, TemplateVersion
from app.seed.data import DEFAULT_FEATURES, TEMPLATE_SEED


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def _sync_template_prices(db) -> int:
    """Apply catalog prices from TEMPLATE_SEED to existing templates by slug."""
    updated = 0
    for item in TEMPLATE_SEED:
        slug = slugify(item["title"])
        template = db.scalar(select(Template).where(Template.slug == slug))
        if template is None:
            continue
        price = float(item["price"])
        if template.price != price:
            template.price = price
            updated += 1
    return updated


def _cleanup_hosting_data(db) -> tuple[int, int]:
    templates_to_update = db.scalars(
        select(Template.id).where(Template.hosting_available.is_(True))
    ).all()
    template_updates = len(templates_to_update)
    if template_updates:
        db.execute(update(Template).values(hosting_available=False))

    addon_delete_result = db.execute(
        delete(ServiceAddon).where(ServiceAddon.slug == "managed-hosting")
    )
    deleted_addons = addon_delete_result.rowcount or 0
    return template_updates, deleted_addons


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(Template.id).limit(1))
        if existing:
            price_updates = _sync_template_prices(db)
            template_updates, deleted_addons = _cleanup_hosting_data(db)
            db.commit()
            print(
                "Seed skipped (existing templates). "
                f"Price sync applied: {price_updates} templates updated. "
                f"Hosting cleanup applied: {template_updates} templates updated, {deleted_addons} add-ons removed."
            )
            return

        categories = {}
        industries = {}

        for item in TEMPLATE_SEED:
            if item["category"] not in categories:
                cat = Category(name=item["category"], slug=slugify(item["category"]), description=f"{item['category']} templates")
                db.add(cat)
                categories[item["category"]] = cat
            if item["industry"] not in industries:
                ind = Industry(name=item["industry"], slug=slugify(item["industry"]), description=f"{item['industry']} templates")
                db.add(ind)
                industries[item["industry"]] = ind
        db.flush()

        for idx, item in enumerate(TEMPLATE_SEED, start=1):
            slug = slugify(item["title"])
            template = Template(
                title=item["title"],
                slug=slug,
                description=item["description"],
                category_id=categories[item["category"]].id,
                industry_id=industries[item["industry"]].id,
                price=float(item["price"]),
                rating=4.5 + (idx % 5) * 0.1,
                sales_count=80 * idx,
                last_updated=datetime.now() - timedelta(days=idx * 3),
                version=f"1.{idx}.0",
                is_featured=idx <= 6,
                is_best_seller=idx in (1, 2, 4, 8, 9),
                is_new=idx >= 7,
                preview_url=f"/preview-site/{slug}",
                thumbnail_url=f"/static/images/templates/{slug}/thumbnail.webp",
                demo_pages="Home, About, Services, Contact",
                tech_stack="HTML5, Crafto multipurpose base, Bootstrap 5, SCSS",
                features_text=", ".join(DEFAULT_FEATURES),
                setup_available=True,
                hosting_available=False,
                maintenance_available=True,
            )
            db.add(template)
            db.flush()

            gallery_urls = [
                f"/static/images/templates/{slug}/gallery-1.webp",
                f"/static/images/templates/{slug}/gallery-2.webp",
                f"/static/images/templates/{slug}/gallery-3.webp",
            ]
            for gidx, url in enumerate(gallery_urls, start=1):
                db.add(
                    TemplateImage(
                        template_id=template.id,
                        image_url=url,
                        alt_text=f"{template.title} gallery image {gidx}",
                        sort_order=gidx,
                    )
                )

            db.add(TemplateVersion(template_id=template.id, version=template.version, changelog="Initial release"))
            for feature in DEFAULT_FEATURES:
                db.add(Feature(template_id=template.id, label=feature))

        addons = [
            ("Setup Service", "setup-service", "Professional website setup and launch support", 249),
            ("Maintenance Plan", "maintenance-plan", "Monthly updates and issue resolution", 79),
            ("SEO Optimization", "seo-optimization", "Search-ready local SEO package", 199),
            ("Cloud Consulting", "cloud-consulting", "Architecture and optimization advisory", 299),
        ]
        for name, slug, desc, price in addons:
            db.add(ServiceAddon(name=name, slug=slug, description=desc, price=price))

        template_updates, deleted_addons = _cleanup_hosting_data(db)
        db.commit()
        print(
            "Seed completed. "
            f"Hosting cleanup applied: {template_updates} templates updated, {deleted_addons} add-ons removed."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed data created.")
