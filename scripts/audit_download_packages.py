"""Audit downloadable theme packages for security and content policy compliance."""

from __future__ import annotations

import posixpath
import re
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models import Template
from app.services.theme_packages import build_theme_zip_bytes

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tiff")
TEXT_SUFFIXES = (".html", ".htm", ".css", ".js", ".json", ".txt", ".md", ".xml", ".map")
HREF_RE = re.compile(r"""\bhref\s*=\s*(["'])([^"']+)\1""", re.IGNORECASE)
BANNED_BRANDS = ("Crafto", "ThemeZaa")
REQUIRED_BRAND = "MateoConsultingTech"


def _is_external_or_special(href: str) -> bool:
    lowered = href.strip().lower()
    return not lowered or lowered.startswith(
        ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "#")
    )


def _resolve_html_href(origin: str, href: str) -> str:
    href_path = href.split("?", 1)[0].split("#", 1)[0].strip()
    if href_path.startswith("/"):
        return posixpath.normpath(href_path.lstrip("/"))
    parent = posixpath.dirname(origin)
    return posixpath.normpath(posixpath.join(parent, href_path))


def _audit_zip(zip_bytes: bytes, *, template_slug: str) -> list[str]:
    violations: list[str] = []
    with ZipFile(BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        html_names = {name for name in names if name.lower().endswith((".html", ".htm"))}

        image_hits = [name for name in names if name.lower().endswith(IMAGE_SUFFIXES)]
        for name in image_hits:
            violations.append(f"{template_slug} | image-asset-included | {name}")

        text_entries = [name for name in names if name.lower().endswith(TEXT_SUFFIXES)]
        combined_text_parts: list[str] = []

        for name in text_entries:
            decoded = archive.read(name).decode("utf-8", errors="replace")
            combined_text_parts.append(decoded)

            if name.lower().endswith((".html", ".htm")):
                for _, href in HREF_RE.findall(decoded):
                    if _is_external_or_special(href):
                        continue
                    href_path = href.split("?", 1)[0].split("#", 1)[0].strip()
                    if not href_path.lower().endswith((".html", ".htm")):
                        continue
                    resolved = _resolve_html_href(name, href_path)
                    if resolved not in html_names:
                        violations.append(f"{template_slug} | broken-local-html-link | {name} -> {href}")

        combined_text = "\n".join(combined_text_parts)
        lowered_text = combined_text.lower()
        for brand in BANNED_BRANDS:
            if brand.lower() in lowered_text:
                violations.append(f"{template_slug} | banned-brand-found | {brand}")
        if REQUIRED_BRAND.lower() not in lowered_text:
            violations.append(f"{template_slug} | required-brand-missing | {REQUIRED_BRAND}")
    return violations


def run() -> str:
    rows: list[str] = []
    total_templates = 0
    with SessionLocal() as db:
        templates = db.scalars(
            select(Template)
            .options(joinedload(Template.category), joinedload(Template.industry))
            .order_by(Template.slug.asc())
        ).all()
        total_templates = len(templates)
        for template in templates:
            zip_bytes, _filename = build_theme_zip_bytes(template)
            rows.extend(_audit_zip(zip_bytes, template_slug=template.slug))

    lines = [
        "DOWNLOAD PACKAGE AUDIT",
        f"templates checked: {total_templates}",
        f"violations: {len(rows)}",
    ]
    if rows:
        lines.append("\nVIOLATIONS")
        lines.extend(rows)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    report = run()
    print(report, end="")
    if "violations: 0" not in report:
        raise SystemExit(1)
