from datetime import datetime, timedelta
import re

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.models import Category, Feature, Industry, ServiceAddon, Template, TemplateImage, TemplateVersion
from app.seed.data import DEFAULT_FEATURES, TEMPLATE_SEED


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(Template.id).limit(1))
        if existing:
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
                price=59 + idx * 7,
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
                tech_stack="FastAPI, Jinja2, Tailwind CSS, Alpine.js",
                features_text=", ".join(DEFAULT_FEATURES),
                setup_available=True,
                hosting_available=True,
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
            ("Managed Hosting", "managed-hosting", "Secure, monitored hosting plan", 49),
            ("Maintenance Plan", "maintenance-plan", "Monthly updates and issue resolution", 79),
            ("SEO Optimization", "seo-optimization", "Search-ready local SEO package", 199),
            ("Cloud Consulting", "cloud-consulting", "Architecture and optimization advisory", 299),
        ]
        for name, slug, desc, price in addons:
            db.add(ServiceAddon(name=name, slug=slug, description=desc, price=price))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed data created.")
