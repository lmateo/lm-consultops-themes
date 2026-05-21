"""Serve Crafto demo HTML with Mateo preview chrome (no iframe)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.models import Template
from app.services.crafto_demos import DEMO_PAGES, CraftoDemoMapping, get_crafto_demo_or_default
from app.utils.templating import templates

CRAFTO_ROOT = Path(__file__).resolve().parent.parent.parent / "crafto-html-templates"

_HEAD_INJECT = """
<link rel="stylesheet" href="/static/css/preview-chrome.css" />
<link rel="stylesheet" href="/static/css/preview-mobile.css" />
<base href="/crafto/" />
"""

_CANVAS_OPEN = '<div id="mkt-preview-canvas" class="mkt-preview-canvas">'
_CANVAS_CLOSE = "</div><!-- /mkt-preview-canvas -->"

_BODY_SCRIPT = '<script defer src="/static/js/preview-chrome.js"></script>'

_PLACEHOLDER_RE = re.compile(r"https://placehold\.co/(?P<width>\d+)x(?P<height>\d+)", re.IGNORECASE)
_CRAFTO_PHOTO_RE = re.compile(
    r"(?P<path>images/demo-(?!.*(?:logo|separator|favicon|apple-touch))[^\"')]+\.(?:jpe?g|png|webp))",
    re.IGNORECASE,
)
_CRAFTO_PHOTO_SKIP = re.compile(r"logo|separator|favicon|apple-touch|highlight-separator", re.IGNORECASE)

_TEMPLATE_IMAGE_SET: tuple[str, ...] = (
    "hero.webp",
    "hero-mobile.webp",
    "thumbnail.webp",
    "preview.webp",
    "gallery-1.webp",
    "gallery-2.webp",
    "gallery-3.webp",
    "about.webp",
    "services.webp",
    "contact.webp",
)

_PAGE_PRIMARY_IMAGE: dict[str, str] = {
    "home": "hero.webp",
    "about": "about.webp",
    "services": "services.webp",
    "contact": "contact.webp",
}


def _preview_image_pool(page: str) -> tuple[str, ...]:
    primary = _PAGE_PRIMARY_IMAGE.get(page, _PAGE_PRIMARY_IMAGE["home"])
    return (primary,) + tuple(image for image in _TEMPLATE_IMAGE_SET if image != primary)


def _stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def normalize_preview_viewport_meta(html: str) -> str:
    """Ensure a single viewport meta the preview chrome can retarget for device simulation."""
    tag = '<meta name="viewport" id="mkt-preview-viewport" content="width=device-width, initial-scale=1.0" />'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, flags=re.IGNORECASE):
        return re.sub(
            r'<meta[^>]+name=["\']viewport["\'][^>]*>',
            tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        return re.sub(
            r"(<head[^>]*>)",
            r"\1\n" + tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return tag + "\n" + html


def inject_template_preview_images(html: str, slug: str, page: str) -> str:
    """Replace placeholders and stock photos with varied per-template WebP assets."""
    pool = _preview_image_pool(page)
    base = f"/static/images/templates/{slug}"
    assigned = 0
    primary_served = False

    def image_url_from_key(key: str) -> str:
        nonlocal assigned, primary_served
        if not primary_served:
            primary_served = True
            assigned += 1
            return f"{base}/{pool[0]}"
        # Keep mappings deterministic while spreading images across replacements.
        idx = 1 + _stable_index(f"{slug}:{page}:{assigned}:{key}", len(pool) - 1)
        assigned += 1
        return f"{base}/{pool[idx]}"

    def _replace_placeholder(match: re.Match[str]) -> str:
        width = int(match.group("width"))
        height = int(match.group("height"))
        if width >= height * 2:
            shape_hint = "landscape"
        elif height >= width * 2:
            shape_hint = "portrait"
        else:
            shape_hint = "square"
        key = f"placeholder:{shape_hint}:{match.group(0)}"
        return image_url_from_key(key)

    html = _PLACEHOLDER_RE.sub(_replace_placeholder, html)

    def _replace_crafto_photo(match: re.Match[str]) -> str:
        path = match.group("path")
        if _CRAFTO_PHOTO_SKIP.search(path):
            return path
        return image_url_from_key(f"crafto-photo:{path}")

    return _CRAFTO_PHOTO_RE.sub(_replace_crafto_photo, html)


def _crafto_file_path(filename: str) -> Path:
    path = CRAFTO_ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(f"Crafto demo not found: {filename}")
    return path


def _render_chrome(
    template: Template,
    crafto: CraftoDemoMapping,
    active_page: str,
) -> str:
    tpl = templates.env.get_template("components/preview_chrome.html")
    return tpl.render(
        template_slug=template.slug,
        template_title=template.title,
        crafto_demo_label=crafto.crafto_demo_label,
        demo_pages=tuple(crafto.pages.keys()),
        active_page=active_page,
    )


def wrap_crafto_html(
    html: str,
    *,
    template: Template,
    crafto: CraftoDemoMapping,
    active_page: str,
) -> str:
    chrome = _render_chrome(template, crafto, active_page)
    body_lead = f"\n{chrome}\n{_CANVAS_OPEN}\n"
    body_tail = f"\n{_CANVAS_CLOSE}\n{_BODY_SCRIPT}\n"

    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"(<head[^>]*>)",
            r"\1" + _HEAD_INJECT,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = _HEAD_INJECT + html

    def _append_body_class(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r'\bclass=["\']', tag, flags=re.IGNORECASE):
            return re.sub(
                r'class=(["\'])([^"\']*)\1',
                lambda m: f'class={m.group(1)}{m.group(2)} mkt-preview-active{m.group(1)}',
                tag,
                count=1,
                flags=re.IGNORECASE,
            )
        return tag[:-1] + ' class="mkt-preview-active">'

    if re.search(r"<body[^>]*>", html, flags=re.IGNORECASE):
        html = re.sub(r"<body[^>]*>", _append_body_class, html, count=1, flags=re.IGNORECASE)
        html = re.sub(
            r"(<body[^>]*>)",
            r"\1" + body_lead,
            html,
            count=1,
            flags=re.IGNORECASE,
        )

    if re.search(r"</body>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"</body>",
            body_tail + "</body>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = html + body_tail
    return html


def load_wrapped_crafto_preview(template: Template, page: str = "home") -> str:
    normalized = page if page in DEMO_PAGES else "home"
    crafto = get_crafto_demo_or_default(template.slug)
    filename = crafto.pages.get(normalized, crafto.pages["home"])
    raw_html = _crafto_file_path(filename).read_text(encoding="utf-8-sig", errors="replace")
    raw_html = normalize_preview_viewport_meta(raw_html)
    raw_html = inject_template_preview_images(raw_html, template.slug, normalized)
    return wrap_crafto_html(
        raw_html,
        template=template,
        crafto=crafto,
        active_page=normalized,
    )
