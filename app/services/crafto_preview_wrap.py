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
_MATEO_LOGO_SRC = "/static/images/logos/logo-black.png"
_MATEO_FAVICON_SRC = "/static/images/logos/mateo-favicon.ico"
_MATEO_LOGO_CLASS = "mkt-mateo-brand-logo"
_MATEO_BRAND_NAME = "Mateo Consulting Tech"
_MATEO_PREVIEW_TITLE = "Mateo Consulting Team - The Multipurpose HTML5 Template"

_PLACEHOLDER_RE = re.compile(r"https://placehold\.co/(?P<width>\d+)x(?P<height>\d+)", re.IGNORECASE)
_CRAFTO_PHOTO_RE = re.compile(
    r"(?P<path>images/demo-(?!.*(?:logo|separator|favicon|apple-touch))[^\"')]+\.(?:jpe?g|png|webp))",
    re.IGNORECASE,
)
_CRAFTO_PHOTO_SKIP = re.compile(r"logo|separator|favicon|apple-touch|highlight-separator", re.IGNORECASE)

_HREF_RE = re.compile(r"""href=(["'])([^"']*)\1""", re.IGNORECASE)
_SRC_RE = re.compile(r"""src=(["'])([^"']*)\1""", re.IGNORECASE)
_DATA_AT2X_RE = re.compile(r"""data-at2x=(["'])([^"']*)\1""", re.IGNORECASE)
_CRAFTO_VENDOR_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?"
    r"(?:craftohtml\.themezaa\.com|themezaa\.com|themeforest\.net|1\.envato\.market)",
    re.IGNORECASE,
)
_PLACEHOLDER_EXTERNAL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?"
    r"(?:facebook\.com|twitter\.com|instagram\.com|dribbble\.com|linkedin\.com|behance\.com|pinterest\.com|in\.pinterest\.com|domain\.com)",
    re.IGNORECASE,
)
_HEADER_BLOCK_RE = re.compile(r"<!-- start header -->(.*?)<!-- end header -->", re.IGNORECASE | re.DOTALL)
_FOOTER_BLOCK_RE = re.compile(r"<!-- start footer -->(.*?)<!-- end footer -->", re.IGNORECASE | re.DOTALL)
_HEADER_TAG_RE = re.compile(r"<header[^>]*>.*?</header>", re.IGNORECASE | re.DOTALL)
_FOOTER_TAG_RE = re.compile(r"<footer[^>]*>.*?</footer>", re.IGNORECASE | re.DOTALL)
_SKIP_HREF_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")
_KEEP_HREF_PREFIXES = ("/static/", "/preview/", "/templates/", "/purchase/", "/crafto/")
_PAGE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"contact", re.IGNORECASE), "contact"),
    (re.compile(r"about", re.IGNORECASE), "about"),
    (
        re.compile(
            r"service|services|menu|treatment|treatments|room|rooms|cause|causes|sell|pricing|package",
            re.IGNORECASE,
        ),
        "services",
    ),
)

_STATIC_ROOT = Path(__file__).resolve().parent.parent / "static" / "images" / "templates"

_TEMPLATE_IMAGE_SET: tuple[str, ...] = (
    "hero.webp",
    "hero-mobile.webp",
    "thumbnail.webp",
    "preview.webp",
    "about.webp",
    "services.webp",
    "contact.webp",
    "team.webp",
    "blog.webp",
    "feature.webp",
    "showcase.webp",
    *(f"gallery-{index}.webp" for index in range(1, 13)),
)

_CRAFTO_PATH_IMAGE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"about|our-story|who-we|mission", re.IGNORECASE), "about.webp"),
    (re.compile(r"contact|get-in-touch|reach-us", re.IGNORECASE), "contact.webp"),
    (
        re.compile(
            r"service|services|menu|treatment|treatments|room|rooms|cause|causes|sell|pricing|package",
            re.IGNORECASE,
        ),
        "services.webp",
    ),
    (re.compile(r"team|staff|doctor|vet|crew", re.IGNORECASE), "team.webp"),
    (re.compile(r"blog|news|article|post", re.IGNORECASE), "blog.webp"),
    (re.compile(r"feature|benefit|why-us", re.IGNORECASE), "feature.webp"),
    (re.compile(r"showcase|portfolio|project|case", re.IGNORECASE), "showcase.webp"),
    (re.compile(r"home|index|landing|banner", re.IGNORECASE), "hero.webp"),
)

_PAGE_PRIMARY_IMAGE: dict[str, str] = {
    "home": "hero.webp",
    "about": "about.webp",
    "services": "services.webp",
    "contact": "contact.webp",
}

_PAGE_WEIGHTED_SEQUENCE: dict[str, tuple[str, ...]] = {
    "home": (
        "hero.webp",
        "preview.webp",
        "preview.webp",
        "hero-mobile.webp",
        "gallery-1.webp",
        "gallery-2.webp",
        "gallery-3.webp",
        "gallery-4.webp",
        "services.webp",
        "thumbnail.webp",
        "feature.webp",
        "showcase.webp",
        "about.webp",
        "contact.webp",
    ),
    "about": (
        "about.webp",
        "team.webp",
        "gallery-5.webp",
        "gallery-2.webp",
        "gallery-1.webp",
        "thumbnail.webp",
        "hero.webp",
        "preview.webp",
        "gallery-6.webp",
        "contact.webp",
        "services.webp",
        "hero-mobile.webp",
    ),
    "services": (
        "services.webp",
        "feature.webp",
        "preview.webp",
        "gallery-1.webp",
        "gallery-3.webp",
        "gallery-4.webp",
        "gallery-7.webp",
        "hero.webp",
        "gallery-2.webp",
        "showcase.webp",
        "contact.webp",
        "about.webp",
        "hero-mobile.webp",
    ),
    "contact": (
        "contact.webp",
        "hero-mobile.webp",
        "thumbnail.webp",
        "about.webp",
        "gallery-8.webp",
        "hero.webp",
        "preview.webp",
        "gallery-1.webp",
        "services.webp",
        "gallery-2.webp",
    ),
}

_SLUG_IMAGE_WEIGHT_BOOSTS: dict[str, tuple[str, ...]] = {
    "pizza-local-eats": ("gallery-1.webp", "gallery-2.webp", "gallery-3.webp", "thumbnail.webp"),
    "mountain-lodge": ("hero.webp", "gallery-1.webp", "gallery-2.webp", "preview.webp"),
    "homebase-realty": ("thumbnail.webp", "gallery-1.webp", "about.webp", "preview.webp"),
    "cloudcare-it": ("services.webp", "preview.webp", "hero-mobile.webp"),
    "tradepro-local": ("services.webp", "preview.webp", "thumbnail.webp"),
    "autoworks-garage": ("services.webp", "gallery-3.webp", "preview.webp"),
    "community-impact": ("about.webp", "contact.webp", "gallery-3.webp"),
    "wellness-local": ("hero-mobile.webp", "about.webp", "gallery-2.webp"),
    "petcare-studio": ("hero-mobile.webp", "services.webp", "gallery-2.webp"),
    "greenfield-farm": ("hero.webp", "gallery-1.webp", "services.webp"),
}


def _discover_template_images(slug: str) -> tuple[str, ...]:
    folder = _STATIC_ROOT / slug
    if not folder.is_dir():
        return _TEMPLATE_IMAGE_SET
    discovered = tuple(
        sorted(
            {
                path.name
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() == ".webp"
            }
        )
    )
    return discovered or _TEMPLATE_IMAGE_SET


def _preview_image_pool(page: str, slug: str) -> tuple[str, ...]:
    primary = _PAGE_PRIMARY_IMAGE.get(page, _PAGE_PRIMARY_IMAGE["home"])
    weighted = list(_PAGE_WEIGHTED_SEQUENCE.get(page, _PAGE_WEIGHTED_SEQUENCE["home"]))
    if not weighted:
        weighted = [primary]
    if weighted[0] != primary:
        weighted.insert(0, primary)
    weighted.extend(_SLUG_IMAGE_WEIGHT_BOOSTS.get(slug, ()))
    available = set(_discover_template_images(slug))
    ordered = [image for image in weighted if image in available]
    remaining = [image for image in sorted(available) if image not in ordered]
    if not ordered:
        return tuple(remaining) if remaining else _TEMPLATE_IMAGE_SET
    return tuple(ordered + remaining)


def _image_for_crafto_path(path: str, pool: tuple[str, ...]) -> str | None:
    for pattern, preferred in _CRAFTO_PATH_IMAGE_HINTS:
        if pattern.search(path) and preferred in pool:
            return preferred
    gallery_match = re.search(r"gallery[_-]?(\d+)", path, flags=re.IGNORECASE)
    if gallery_match:
        preferred = f"gallery-{gallery_match.group(1)}.webp"
        if preferred in pool:
            return preferred
    return None


def _stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def _crafto_demo_stem(crafto: CraftoDemoMapping) -> str:
    home = crafto.pages["home"]
    if home.startswith("demo-") and home.endswith(".html"):
        return home[5:-5]
    return Path(home).stem


def _filename_to_page(filename: str, crafto: CraftoDemoMapping) -> str | None:
    file_to_page = {value: key for key, value in crafto.pages.items()}
    if filename in file_to_page:
        return file_to_page[filename]
    stem = _crafto_demo_stem(crafto)
    if not filename.startswith(f"demo-{stem}"):
        return None
    for pattern, page in _PAGE_HINTS:
        if pattern.search(filename):
            return page
    if filename == crafto.pages["home"]:
        return "home"
    return None


def _preview_url(slug: str, page: str) -> str:
    normalized = page if page in DEMO_PAGES else "home"
    return f"/preview/{slug}/{normalized}"


def _resolve_preview_href(raw_href: str, *, slug: str, crafto: CraftoDemoMapping) -> str:
    href = raw_href.strip()
    if not href:
        return href

    lowered = href.lower()
    if href == "#":
        return _preview_url(slug, "home")
    if lowered.startswith(_SKIP_HREF_PREFIXES):
        return href
    if any(lowered.startswith(prefix) for prefix in _KEEP_HREF_PREFIXES):
        return href
    if _CRAFTO_VENDOR_RE.match(href):
        return _preview_url(slug, "home")
    if _PLACEHOLDER_EXTERNAL_RE.match(href):
        return _preview_url(slug, "home")

    if lowered.startswith(("http://", "https://", "//")):
        return href

    path = href.split("?", 1)[0].split("#", 1)[0]
    filename = Path(path).name
    if not filename:
        return href

    if filename in {"index.html", "index.htm"}:
        return _preview_url(slug, "home")

    page = _filename_to_page(filename, crafto)
    if page:
        return _preview_url(slug, page)

    if filename.startswith("demo-") and filename.endswith(".html"):
        return _preview_url(slug, "home")

    return href


def rewrite_crafto_preview_links(html: str, *, slug: str, crafto: CraftoDemoMapping) -> str:
    """Point in-demo anchors at Mateo preview routes; neutralize vendor/Crafto hub links."""

    def _replace_href(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        resolved = _resolve_preview_href(value, slug=slug, crafto=crafto)
        return f"href={quote}{resolved}{quote}"

    return _HREF_RE.sub(_replace_href, html)


def _ensure_mateo_logo_class_on_imgs(html: str) -> str:
    """Tag Mateo logo images so preview CSS can apply consistent balanced sizing."""

    def _tag_img(match: re.Match[str]) -> str:
        tag = match.group(0)
        if _MATEO_LOGO_SRC not in tag:
            return tag
        if re.search(rf'\bclass=(["\'])[^"\']*\b{re.escape(_MATEO_LOGO_CLASS)}\b', tag, flags=re.IGNORECASE):
            return tag
        class_match = re.search(r'\bclass=(["\'])([^"\']*)\1', tag, flags=re.IGNORECASE)
        if class_match:
            quote, classes = class_match.group(1), class_match.group(2)
            return tag.replace(
                class_match.group(0),
                f'class={quote}{classes} {_MATEO_LOGO_CLASS}{quote}',
                1,
            )
        return tag[:-1] + f' class="{_MATEO_LOGO_CLASS}">'

    return re.sub(r"<img[^>]*>", _tag_img, html, flags=re.IGNORECASE)


def rewrite_crafto_brand_assets(html: str) -> str:
    """Replace demo favicon and primary logo lockups with Mateo brand assets."""
    # Normalize favicon and Apple touch icons to Mateo favicon.
    html = re.sub(
        r"""<link[^>]+rel=(["'])(?:shortcut icon|icon|apple-touch-icon)\1[^>]*>""",
        lambda m: _HREF_RE.sub(f'href="{_MATEO_FAVICON_SRC}"', m.group(0))
        if _HREF_RE.search(m.group(0))
        else m.group(0)[:-1] + f' href="{_MATEO_FAVICON_SRC}">',
        html,
        flags=re.IGNORECASE,
    )

    def _replace_logo_src(match: re.Match[str]) -> str:
        quote = match.group(1)
        return f"src={quote}{_MATEO_LOGO_SRC}{quote}"

    def _replace_logo_at2x(match: re.Match[str]) -> str:
        quote = match.group(1)
        return f"data-at2x={quote}{_MATEO_LOGO_SRC}{quote}"

    def _replace_any_crafto_logo_attr(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        lowered = value.lower()
        if lowered.startswith("/static/images/logos/"):
            return match.group(0)
        if "logo" in lowered and ("images/" in lowered or lowered.startswith("images")):
            return f'src={quote}{_MATEO_LOGO_SRC}{quote}'
        return match.group(0)

    def _replace_any_crafto_logo_at2x_attr(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        lowered = value.lower()
        if lowered.startswith("/static/images/logos/"):
            return match.group(0)
        if "logo" in lowered and ("images/" in lowered or lowered.startswith("images")):
            return f'data-at2x={quote}{_MATEO_LOGO_SRC}{quote}'
        return match.group(0)

    def _rewrite_brand_anchor_block(match: re.Match[str]) -> str:
        block = match.group(0)
        block = _SRC_RE.sub(_replace_logo_src, block)
        block = _DATA_AT2X_RE.sub(_replace_logo_at2x, block)
        return block

    # Normalize all images inside the primary header brand anchor.
    html = re.sub(
        r"""<a[^>]+class=(["'])[^"']*navbar-brand[^"']*\1[^>]*>.*?</a>""",
        _rewrite_brand_anchor_block,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Update known brand logo images used in Crafto headers/footers.
    html = re.sub(
        r"""(<img[^>]+class=(["'])[^"']*(?:default-logo|alt-logo|mobile-logo)\2[^>]*>)""",
        lambda m: _DATA_AT2X_RE.sub(
            _replace_logo_at2x,
            _SRC_RE.sub(_replace_logo_src, m.group(1), count=1),
            count=1,
        ),
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"""(<a[^>]+class=(["'])[^"']*footer-logo[^"']*\2[^>]*>\s*<img[^>]*>)""",
        lambda m: _DATA_AT2X_RE.sub(
            _replace_logo_at2x,
            _SRC_RE.sub(_replace_logo_src, m.group(1), count=1),
            count=1,
        ),
        html,
        flags=re.IGNORECASE,
    )
    # Catch any remaining in-page Crafto logo assets and normalize to Mateo logo.
    html = _SRC_RE.sub(_replace_any_crafto_logo_attr, html)
    html = _DATA_AT2X_RE.sub(_replace_any_crafto_logo_at2x_attr, html)
    return _ensure_mateo_logo_class_on_imgs(html)


def rewrite_crafto_brand_copy(html: str) -> str:
    """Replace visible Crafto/ThemeZaa text in header/footer with Mateo branding."""

    def _replace_brand_terms(block: str) -> str:
        block = re.sub(r"\bCrafto\b", _MATEO_BRAND_NAME, block, flags=re.IGNORECASE)
        block = re.sub(r"\bThemeZaa\b", _MATEO_BRAND_NAME, block, flags=re.IGNORECASE)
        return block

    def _replace_match(match: re.Match[str]) -> str:
        return _replace_brand_terms(match.group(0))

    html = _HEADER_BLOCK_RE.sub(_replace_match, html)
    html = _FOOTER_BLOCK_RE.sub(_replace_match, html)
    html = _HEADER_TAG_RE.sub(_replace_match, html)
    html = _FOOTER_TAG_RE.sub(_replace_match, html)
    return html


def rewrite_crafto_head_title(html: str) -> str:
    """Normalize live preview page title to Mateo title across all wrapped demos."""
    if re.search(r"<title[^>]*>", html, flags=re.IGNORECASE):
        return re.sub(
            r"<title[^>]*>.*?</title>",
            f"<title>{_MATEO_PREVIEW_TITLE}</title>",
            html,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        return re.sub(
            r"(<head[^>]*>)",
            r"\1\n" + f"<title>{_MATEO_PREVIEW_TITLE}</title>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return f"<title>{_MATEO_PREVIEW_TITLE}</title>\n" + html


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
    pool = _preview_image_pool(page, slug)
    if not pool:
        return html
    base = f"/static/images/templates/{slug}"
    assigned = 0
    primary_served = False
    shape_offsets = {"landscape": 0, "square": 2, "portrait": 4}

    def next_pool_image(*, key: str, forced: str | None = None) -> str:
        nonlocal assigned, primary_served
        if forced and forced in pool:
            filename = forced
        elif not primary_served:
            primary_served = True
            filename = pool[0]
        else:
            width = max(len(pool) - 1, 1)
            idx = 1 + _stable_index(f"{slug}:{page}:{assigned}:{key}", width)
            filename = pool[idx]
        assigned += 1
        return f"{base}/{filename}"

    def _replace_placeholder(match: re.Match[str]) -> str:
        nonlocal assigned
        width = int(match.group("width"))
        height = int(match.group("height"))
        if width >= height * 2:
            shape_hint = "landscape"
        elif height >= width * 2:
            shape_hint = "portrait"
        else:
            shape_hint = "square"
        offset = shape_offsets[shape_hint]
        filename = pool[(assigned + offset) % len(pool)]
        assigned += 1
        return f"{base}/{filename}"

    html = _PLACEHOLDER_RE.sub(_replace_placeholder, html)

    def _replace_crafto_photo(match: re.Match[str]) -> str:
        path = match.group("path")
        if _CRAFTO_PHOTO_SKIP.search(path):
            return path
        hinted = _image_for_crafto_path(path, pool)
        return next_pool_image(key=f"crafto-photo:{path}", forced=hinted)

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
    ordered_pages = tuple(
        ["home", *[page for page in crafto.pages.keys() if page != "home"]]
        if "home" in crafto.pages
        else crafto.pages.keys()
    )
    tpl = templates.env.get_template("components/preview_chrome.html")
    return tpl.render(
        template_slug=template.slug,
        template_title=template.title,
        crafto_demo_label=crafto.crafto_demo_label,
        demo_pages=ordered_pages,
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
    raw_html = rewrite_crafto_head_title(raw_html)
    raw_html = normalize_preview_viewport_meta(raw_html)
    raw_html = inject_template_preview_images(raw_html, template.slug, normalized)
    raw_html = rewrite_crafto_brand_assets(raw_html)
    raw_html = rewrite_crafto_preview_links(raw_html, slug=template.slug, crafto=crafto)
    raw_html = rewrite_crafto_brand_copy(raw_html)
    return wrap_crafto_html(
        raw_html,
        template=template,
        crafto=crafto,
        active_page=normalized,
    )
