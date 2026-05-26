import hashlib
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.utils.query_params import format_compact_number, query_string_filter

_STATIC_IMG_ROOT = Path(__file__).resolve().parent.parent / "static" / "images" / "templates"
_CACHE_BUSTERS: dict[str, str] = {}


def _template_image_version(slug: str) -> str:
    """Short hash of image mtimes for URL cache-busting on marketplace pages."""
    if slug in _CACHE_BUSTERS:
        return _CACHE_BUSTERS[slug]
    folder = _STATIC_IMG_ROOT / slug
    if not folder.is_dir():
        _CACHE_BUSTERS[slug] = ""
        return ""
    mtimes = sorted(
        f"{p.name}:{int(p.stat().st_mtime)}"
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".webp"
    )
    version = hashlib.sha1("|".join(mtimes).encode()).hexdigest()[:8] if mtimes else ""
    _CACHE_BUSTERS[slug] = version
    return version


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
templates.env.filters["query_string"] = query_string_filter
templates.env.filters["compact_number"] = format_compact_number
templates.env.globals["image_version"] = _template_image_version


def render(template_name: str, request, context: dict | None = None):
    context = context or {}
    context.update({"request": request})
    return templates.TemplateResponse(request=request, name=template_name, context=context)
