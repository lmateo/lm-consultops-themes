from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.utils.query_params import format_compact_number, query_string_filter

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
templates.env.filters["query_string"] = query_string_filter
templates.env.filters["compact_number"] = format_compact_number


def render(template_name: str, request, context: dict | None = None):
    context = context or {}
    context.update({"request": request})
    return templates.TemplateResponse(request=request, name=template_name, context=context)
