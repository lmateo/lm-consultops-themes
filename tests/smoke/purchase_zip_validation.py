"""Validate downloadable theme ZIP bytes from a completed purchase."""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
from zipfile import ZipFile

from app.models import Template
from app.services.crafto_demos import get_crafto_demo_or_default
from app.services.theme_packages import build_theme_zip_bytes

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tiff")
TEXT_SUFFIXES = (".html", ".htm", ".css", ".js", ".json", ".txt", ".md", ".xml", ".map")
HREF_RE = re.compile(r"""\bhref\s*=\s*(["'])([^"']+)\1""", re.IGNORECASE)
BANNED_BRANDS = ("crafto", "themezaa")
REQUIRED_BRAND = "mateoconsultingtech"


def _zip_entry_hashes(zip_bytes: bytes) -> dict[str, str]:
    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        return {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in sorted(archive.namelist())
        }


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


def validate_purchase_zip_bytes(zip_bytes: bytes, template: Template) -> list[str]:
    """Return validation violations; empty list means the purchase ZIP looks correct."""
    violations: list[str] = []
    if not zip_bytes:
        return ["zip-empty"]

    try:
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
            if not names:
                return ["zip-has-no-entries"]

            root_prefix = f"{template.slug}-theme/"
            if not any(name.startswith(root_prefix) for name in names):
                violations.append(f"missing-root-prefix:{root_prefix}")

            required_files = (
                f"{root_prefix}README.md",
                f"{root_prefix}IMAGE_ASSETS_NOTICE.txt",
            )
            for required in required_files:
                if required not in names:
                    violations.append(f"missing-required-file:{required}")

            html_names = {name for name in names if name.lower().endswith((".html", ".htm"))}
            if not html_names:
                violations.append("missing-html-pages")

            mapping = get_crafto_demo_or_default(template.slug)
            allowed_html = {
                f"{root_prefix}{filename}"
                for filename in mapping.pages.values()
            }
            unexpected_html = sorted(html_names - allowed_html)
            if unexpected_html:
                violations.append(f"unexpected-theme-html:{unexpected_html[0]}")

            image_hits = [name for name in names if name.lower().endswith(IMAGE_SUFFIXES)]
            if image_hits:
                violations.append(f"image-assets-included:{image_hits[0]}")

            combined_text_parts: list[str] = []
            for name in names:
                if not name.lower().endswith(TEXT_SUFFIXES):
                    continue
                combined_text_parts.append(archive.read(name).decode("utf-8", errors="replace"))

            combined_text = "\n".join(combined_text_parts).lower()
            for brand in BANNED_BRANDS:
                if brand in combined_text:
                    violations.append(f"banned-brand-found:{brand}")
            if REQUIRED_BRAND not in combined_text:
                violations.append(f"required-brand-missing:{REQUIRED_BRAND}")

            for name in sorted(html_names):
                html = archive.read(name).decode("utf-8", errors="replace")
                for _, href in HREF_RE.findall(html):
                    if _is_external_or_special(href):
                        continue
                    href_path = href.split("?", 1)[0].split("#", 1)[0].strip()
                    if not href_path.lower().endswith((".html", ".htm")):
                        continue
                    resolved = _resolve_html_href(name, href_path)
                    if resolved not in html_names:
                        violations.append(f"broken-local-html-link:{name}->{href}")
    except Exception as exc:  # noqa: BLE001
        return [f"zip-invalid:{exc}"]

    expected_bytes, _filename = build_theme_zip_bytes(template)
    actual_hashes = _zip_entry_hashes(zip_bytes)
    expected_hashes = _zip_entry_hashes(expected_bytes)
    if set(actual_hashes) != set(expected_hashes):
        missing = sorted(set(expected_hashes) - set(actual_hashes))
        extra = sorted(set(actual_hashes) - set(expected_hashes))
        if missing:
            violations.append(f"expected-files-missing:{missing[:3]}")
        if extra:
            violations.append(f"unexpected-files:{extra[:3]}")
    for name in sorted(set(actual_hashes) & set(expected_hashes)):
        if name.endswith("README.md"):
            continue
        if actual_hashes[name] != expected_hashes[name]:
            violations.append(f"content-changed:{name}")

    return violations
