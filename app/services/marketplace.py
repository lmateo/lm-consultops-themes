from math import ceil

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Category, Industry, Template


def list_categories(db: Session) -> list[Category]:
    return db.scalars(select(Category).order_by(Category.name)).all()


def list_industries(db: Session) -> list[Industry]:
    return db.scalars(select(Industry).order_by(Industry.name)).all()


def get_template_by_slug(db: Session, slug: str) -> Template | None:
    query = (
        select(Template)
        .options(
            joinedload(Template.category),
            joinedload(Template.industry),
            joinedload(Template.images),
            joinedload(Template.features),
            joinedload(Template.reviews),
        )
        .where(Template.slug == slug)
    )
    return db.scalars(query).first()


def get_related_templates(db: Session, template: Template, limit: int = 3) -> list[Template]:
    query = (
        select(Template)
        .where(Template.category_id == template.category_id, Template.id != template.id)
        .order_by(Template.last_updated.desc())
        .limit(limit)
    )
    return db.scalars(query).all()


def filtered_template_query(
    category_slug: str | None = None,
    industry_slug: str | None = None,
    q: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "newest",
) -> Select[tuple[Template]]:
    query = select(Template).options(joinedload(Template.category), joinedload(Template.industry))

    if category_slug:
        query = query.join(Category).where(Category.slug == category_slug)
    if industry_slug:
        query = query.join(Industry).where(Industry.slug == industry_slug)
    if q:
        text = f"%{q.lower()}%"
        query = query.where(
            func.lower(Template.title).like(text) | func.lower(Template.description).like(text)
        )
    if min_price is not None:
        query = query.where(Template.price >= min_price)
    if max_price is not None:
        query = query.where(Template.price <= max_price)

    sort_map = {
        "newest": Template.last_updated.desc(),
        "price_low_high": Template.price.asc(),
        "price_high_low": Template.price.desc(),
    }
    return query.order_by(sort_map.get(sort, Template.last_updated.desc()))


def paginate_templates(db: Session, query: Select[tuple[Template]], page: int = 1, per_page: int = 12):
    count_query = select(func.count()).select_from(query.subquery())
    total_items = db.scalar(count_query) or 0
    page_count = max(1, ceil(total_items / per_page)) if total_items else 1
    page = max(1, min(page, page_count))
    items = db.scalars(query.offset((page - 1) * per_page).limit(per_page)).all()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "page_count": page_count,
    }
