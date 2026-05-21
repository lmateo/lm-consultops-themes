from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal
from app.services.marketplace import list_categories, list_industries
from app.utils.query_params import format_compact_number, query_string_filter

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
templates.env.filters["query_string"] = query_string_filter
templates.env.filters["compact_number"] = format_compact_number


def _default_nav_context() -> dict:
    with SessionLocal() as db:
        return {
            "nav_categories": list_categories(db),
            "nav_industries": list_industries(db),
        }


def render(template_name: str, request, context: dict | None = None):
    context = context or {}
    if "nav_categories" not in context or "nav_industries" not in context:
        context.update(_default_nav_context())
    context.update({"request": request})
    return templates.TemplateResponse(request=request, name=template_name, context=context)
