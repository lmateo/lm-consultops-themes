from math import ceil

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Category, Industry, Template

TEMPLATE_SORTS = frozenset({"newest", "price_low_high", "price_high_low", "bestselling", "top_rated"})


def list_categories(db: Session) -> list[Category]:
    return db.scalars(select(Category).order_by(Category.name)).all()


def list_industries(db: Session) -> list[Industry]:
    return db.scalars(select(Industry).order_by(Industry.name)).all()


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    return db.scalars(select(Category).where(Category.slug == slug)).first()


def get_industry_by_slug(db: Session, slug: str) -> Industry | None:
    return db.scalars(select(Industry).where(Industry.slug == slug)).first()


def get_categories_with_counts(db: Session) -> list[dict]:
    rows = db.execute(
        select(Category, func.count(Template.id).label("template_count"))
        .outerjoin(Template, Template.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    ).all()
    return [{"category": row[0], "template_count": row[1]} for row in rows]


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
        .options(joinedload(Template.category), joinedload(Template.industry))
        .where(Template.category_id == template.category_id, Template.id != template.id)
        .order_by(Template.sales_count.desc(), Template.rating.desc())
        .limit(limit)
    )
    return db.scalars(query).all()


def _sort_order(sort: str):
    sort_map = {
        "newest": Template.last_updated.desc(),
        "price_low_high": Template.price.asc(),
        "price_high_low": Template.price.desc(),
        "bestselling": Template.sales_count.desc(),
        "top_rated": Template.rating.desc(),
    }
    return sort_map.get(sort, Template.last_updated.desc())


def filtered_template_query(
    category_slug: str | None = None,
    industry_slug: str | None = None,
    q: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "newest",
) -> Select[tuple[Template]]:
    query = select(Template).options(*_template_list_loads())

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

    return query.order_by(_sort_order(sort))


def _template_list_loads():
    return (
        joinedload(Template.category),
        joinedload(Template.industry),
        joinedload(Template.images),
    )


def get_featured_studios(db: Session, limit: int = 5) -> list[dict]:
    rows = db.execute(
        select(
            Industry,
            func.count(Template.id).label("template_count"),
            func.coalesce(func.sum(Template.sales_count), 0).label("total_sales"),
        )
        .join(Template, Template.industry_id == Industry.id)
        .group_by(Industry.id)
        .order_by(func.sum(Template.sales_count).desc(), func.count(Template.id).desc())
        .limit(limit)
    ).all()
    return [
        {"industry": row[0], "template_count": row[1], "total_sales": row[2]}
        for row in rows
    ]


def review_count_for_template(template: Template) -> int:
    if template.reviews:
        return len(template.reviews)
    return max(1, template.sales_count // 4)


def get_popular_by_category_sections(
    db: Session,
    *,
    per_category: int = 4,
    category_slug: str | None = None,
    sort: str = "bestselling",
) -> list[dict]:
    if sort not in TEMPLATE_SORTS:
        sort = "bestselling"
    order = _sort_order(sort)

    categories = list_categories(db)
    if category_slug:
        categories = [category for category in categories if category.slug == category_slug]

    sections: list[dict] = []
    for category in categories:
        templates = db.scalars(
            select(Template)
            .options(*_template_list_loads())
            .where(Template.category_id == category.id)
            .order_by(order)
            .limit(per_category)
        ).unique().all()
        if not templates:
            continue
        total_count = db.scalar(select(func.count()).select_from(Template).where(Template.category_id == category.id)) or 0
        sections.append({"category": category, "templates": templates, "total_count": total_count})
    return sections


def paginate_templates(db: Session, query: Select[tuple[Template]], page: int = 1, per_page: int = 12):
    count_query = select(func.count()).select_from(query.subquery())
    total_items = db.scalar(count_query) or 0
    page_count = max(1, ceil(total_items / per_page)) if total_items else 1
    page = max(1, min(page, page_count))
    items = db.scalars(query.offset((page - 1) * per_page).limit(per_page)).unique().all()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "page_count": page_count,
    }
