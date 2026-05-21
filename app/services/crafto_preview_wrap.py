"""Serve Crafto demo HTML with Mateo preview chrome (no iframe)."""

from __future__ import annotations

import re
from pathlib import Path

from app.models import Template
from app.services.crafto_demos import DEMO_PAGES, CraftoDemoMapping, get_crafto_demo_or_default
from app.utils.templating import templates

CRAFTO_ROOT = Path(__file__).resolve().parent.parent.parent / "crafto-html-templates"

_HEAD_INJECT = """
<link rel="stylesheet" href="/static/css/preview-chrome.css" />
<base href="/crafto/" />
"""

_BODY_SCRIPT = '<script defer src="/static/js/preview-chrome.js"></script>'

_PLACEHOLDER_RE = re.compile(r"https://placehold\.co/\d+x\d+", re.IGNORECASE)
_CRAFTO_PHOTO_RE = re.compile(
    r"(?P<path>images/demo-(?!.*(?:logo|separator|favicon|apple-touch))[^\"')]+\.(?:jpe?g|png|webp))",
    re.IGNORECASE,
)
_CRAFTO_PHOTO_SKIP = re.compile(r"logo|separator|favicon|apple-touch|highlight-separator", re.IGNORECASE)

_PAGE_IMAGE_POOL: dict[str, tuple[str, ...]] = {
    "home": (
        "hero.webp",
        "preview.webp",
        "gallery-1.webp",
        "gallery-2.webp",
        "gallery-3.webp",
        "services.webp",
        "about.webp",
        "contact.webp",
    ),
    "about": (
        "about.webp",
        "hero.webp",
        "gallery-2.webp",
        "gallery-1.webp",
        "gallery-3.webp",
        "preview.webp",
        "services.webp",
    ),
    "services": (
        "services.webp",
        "gallery-1.webp",
        "gallery-2.webp",
        "gallery-3.webp",
        "hero.webp",
        "preview.webp",
        "about.webp",
    ),
    "contact": (
        "contact.webp",
        "hero.webp",
        "gallery-3.webp",
        "gallery-1.webp",
        "about.webp",
        "preview.webp",
    ),
}


def _preview_image_pool(page: str) -> tuple[str, ...]:
    return _PAGE_IMAGE_POOL.get(page, _PAGE_IMAGE_POOL["home"])


def inject_template_preview_images(html: str, slug: str, page: str) -> str:
    """Replace Crafto placeholders and stock photos with per-template WebP assets."""
    pool = _preview_image_pool(page)
    base = f"/static/images/templates/{slug}"
    counter = 0

    def next_url() -> str:
        nonlocal counter
        url = f"{base}/{pool[counter % len(pool)]}"
        counter += 1
        return url

    html = _PLACEHOLDER_RE.sub(lambda _: next_url(), html)

    def _replace_crafto_photo(match: re.Match[str]) -> str:
        path = match.group("path")
        if _CRAFTO_PHOTO_SKIP.search(path):
            return path
        return next_url()

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
    body_inject = f'{chrome}\n{_BODY_SCRIPT}'

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

    if re.search(r"</body>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"</body>",
            body_inject + "\n</body>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = html + body_inject

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
    return html


def load_wrapped_crafto_preview(template: Template, page: str = "home") -> str:
    normalized = page if page in DEMO_PAGES else "home"
    crafto = get_crafto_demo_or_default(template.slug)
    filename = crafto.pages.get(normalized, crafto.pages["home"])
    raw_html = _crafto_file_path(filename).read_text(encoding="utf-8-sig", errors="replace")
    raw_html = inject_template_preview_images(raw_html, template.slug, normalized)
    return wrap_crafto_html(
        raw_html,
        template=template,
        crafto=crafto,
        active_page=normalized,
    )
