from io import BytesIO
import posixpath
import re
from zipfile import ZipFile

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Template
from app.services.crafto_demos import get_crafto_demo_or_default
from app.services.theme_packages import build_theme_zip_bytes

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tiff")
_TEXT_SUFFIXES = (".html", ".htm", ".css", ".js", ".json", ".txt", ".md", ".xml", ".map")
_HREF_RE = re.compile(r"""\bhref\s*=\s*(["'])([^"']+)\1""", re.IGNORECASE)


def _get_template() -> Template:
    with SessionLocal() as db:
        template = db.scalar(select(Template).order_by(Template.id.asc()))
        assert template is not None
        return template


def test_theme_zip_excludes_image_assets():
    template = _get_template()
    zip_bytes, filename = build_theme_zip_bytes(template)
    assert filename.endswith(".zip")

    with ZipFile(BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        assert names
        assert any(name.endswith(".html") for name in names)
        assert not any(name.lower().endswith(_IMAGE_SUFFIXES) for name in names)


def test_theme_zip_rewrites_crafto_brand_mentions():
    template = _get_template()
    zip_bytes, _filename = build_theme_zip_bytes(template)

    with ZipFile(BytesIO(zip_bytes)) as archive:
        text_entries = [name for name in archive.namelist() if name.lower().endswith(_TEXT_SUFFIXES)]
        assert text_entries

        combined_text = []
        for name in text_entries:
            raw = archive.read(name)
            combined_text.append(raw.decode("utf-8", errors="replace"))
        rendered = "\n".join(combined_text)

        lowered = rendered.lower()
        assert "crafto" not in lowered
        assert "themezaa" not in lowered
        assert "mateoconsultingtech" in lowered


def test_theme_zip_html_hrefs_resolve_to_packaged_html():
    template = _get_template()
    zip_bytes, _filename = build_theme_zip_bytes(template)

    with ZipFile(BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        html_names = {name for name in names if name.lower().endswith((".html", ".htm"))}
        assert html_names

        for name in html_names:
            html = archive.read(name).decode("utf-8", errors="replace")
            parent = posixpath.dirname(name)
            for _quote, href in _HREF_RE.findall(html):
                lowered = href.strip().lower()
                if not lowered or lowered.startswith(
                    ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "#")
                ):
                    continue
                href_path = href.split("?", 1)[0].split("#", 1)[0].strip()
                if not href_path.lower().endswith((".html", ".htm")):
                    continue

                if href_path.startswith("/"):
                    resolved = posixpath.normpath(href_path.lstrip("/"))
                else:
                    resolved = posixpath.normpath(posixpath.join(parent, href_path))

                assert resolved in html_names, f"{name} has broken html href: {href}"


def test_theme_zip_includes_only_purchased_html_pages():
    with SessionLocal() as db:
        template = db.scalar(select(Template).where(Template.slug == "wellness-local"))
    assert template is not None

    mapping = get_crafto_demo_or_default(template.slug)
    expected_html = set(mapping.pages.values())
    zip_bytes, _filename = build_theme_zip_bytes(template)

    with ZipFile(BytesIO(zip_bytes)) as archive:
        html_names = {
            posixpath.basename(name)
            for name in archive.namelist()
            if name.lower().endswith((".html", ".htm"))
        }
        assert html_names == expected_html
