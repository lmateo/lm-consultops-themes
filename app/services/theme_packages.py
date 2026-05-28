from __future__ import annotations

import re
import posixpath
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from app.models import Template
from app.services.crafto_demos import get_crafto_demo_or_default

CRAFTO_ROOT = Path(__file__).resolve().parent.parent.parent / "crafto-html-templates"

_TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".json", ".txt", ".md", ".xml", ".map"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tiff"}
_ASSET_ATTR_RE = re.compile(
    r"""\b(?:href|src|data-src|data-at2x|data-background|poster)\s*=\s*(["'])([^"']+)\1""",
    re.IGNORECASE,
)
_CSS_URL_RE = re.compile(r"""url\((['"]?)([^'")]+)\1\)""", re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\()?["']([^"')]+)["']\)?""", re.IGNORECASE)
_HREF_ATTR_RE = re.compile(r"""\bhref\s*=\s*(["'])([^"']+)\1""", re.IGNORECASE)
_BRAND_CRAFTO_RE = re.compile(r"Crafto", re.IGNORECASE)
_BRAND_THEMEZAA_RE = re.compile(r"ThemeZaa", re.IGNORECASE)
_MATEO_DOWNLOAD_BRAND = "MateoConsultingTech"


def _safe_template_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value.lower()).strip("-")


def _rewrite_brand_mentions(content: str) -> str:
    updated = _BRAND_CRAFTO_RE.sub(_MATEO_DOWNLOAD_BRAND, content)
    return _BRAND_THEMEZAA_RE.sub(_MATEO_DOWNLOAD_BRAND, updated)


def _is_external_or_special(ref: str) -> bool:
    lowered = ref.strip().lower()
    return (
        not lowered
        or lowered.startswith(("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "#"))
    )


def _resolve_local_ref(origin: Path, ref: str) -> Path | None:
    if _is_external_or_special(ref):
        return None
    ref_path = ref.split("?", 1)[0].split("#", 1)[0].strip()
    if not ref_path:
        return None

    candidate = (CRAFTO_ROOT / ref_path.lstrip("/")) if ref_path.startswith("/") else (origin.parent / ref_path)
    try:
        resolved = candidate.resolve()
        root_resolved = CRAFTO_ROOT.resolve()
    except OSError:
        return None

    if not str(resolved).startswith(str(root_resolved)):
        return None
    if not resolved.is_file():
        return None
    if resolved.suffix.lower() in _IMAGE_SUFFIXES:
        return None
    return resolved


def _collect_refs_from_text(source_path: Path, content: str) -> set[Path]:
    refs: set[Path] = set()
    for _, value in _ASSET_ATTR_RE.findall(content):
        resolved = _resolve_local_ref(source_path, value)
        if resolved:
            refs.add(resolved)
    for _, value in _CSS_URL_RE.findall(content):
        resolved = _resolve_local_ref(source_path, value)
        if resolved:
            refs.add(resolved)
    for value in _CSS_IMPORT_RE.findall(content):
        resolved = _resolve_local_ref(source_path, value)
        if resolved:
            refs.add(resolved)
    return refs


def _build_materials_readme(template: Template, included_files: list[str]) -> str:
    listed = "\n".join(f"- `{path}`" for path in sorted(included_files))
    category = template.__dict__.get("category")
    industry = template.__dict__.get("industry")
    category_name = category.name if category else "N/A"
    industry_name = industry.name if industry else "N/A"
    return f"""# {template.title} Theme Package

Thanks for your purchase.

## Package Contents
{listed}

## Image Assets
- Image assets are intentionally excluded from this package.
- Add only images and brand media that you own or have licensed.

## Branding Rewrite
- Legacy vendor brand mentions in downloadable text materials are rewritten to `{_MATEO_DOWNLOAD_BRAND}`.

## Quick Start
1. Unzip this package.
2. Open the included `demo-*.html` files in your browser.
3. Replace image placeholders and update content for production.

## Theme Metadata
- Category: {category_name}
- Industry: {industry_name}
- Version: {template.version}
- Purchase: Completed via Mateo ConsultOps Themes checkout
"""


def _split_ref_suffix(ref: str) -> tuple[str, str]:
    hash_index = ref.find("#")
    query_index = ref.find("?")
    cut_indices = [index for index in (query_index, hash_index) if index != -1]
    cut = min(cut_indices) if cut_indices else len(ref)
    return ref[:cut], ref[cut:]


def _resolve_archive_html_target(origin_rel_path: str, href_path: str) -> str | None:
    cleaned = href_path.strip()
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        candidate = posixpath.normpath(cleaned.lstrip("/"))
    else:
        origin_parent = PurePosixPath(origin_rel_path).parent.as_posix()
        candidate = posixpath.normpath(posixpath.join(origin_parent, cleaned))
    if candidate in {".", ""}:
        return None
    if candidate.startswith("../") or candidate == "..":
        return None
    return candidate


def _relative_href_between(origin_rel_path: str, target_rel_path: str) -> str:
    origin_parent = PurePosixPath(origin_rel_path).parent.as_posix()
    relative = posixpath.relpath(target_rel_path, start=origin_parent or ".")
    return relative if relative != "." else PurePosixPath(target_rel_path).name


def _rewrite_html_links_for_packaged_targets(
    rel_path: str,
    html: str,
    *,
    included_html_paths: set[str],
    fallback_html_path: str,
) -> str:
    def _replace_href(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        if _is_external_or_special(value):
            return match.group(0)
        href_path, suffix = _split_ref_suffix(value)
        if not href_path.lower().endswith((".html", ".htm")):
            return match.group(0)

        target = _resolve_archive_html_target(rel_path, href_path)
        if not target:
            return match.group(0)
        if target in included_html_paths:
            return match.group(0)

        rewritten = _relative_href_between(rel_path, fallback_html_path)
        return f'href={quote}{rewritten}{suffix}{quote}'

    return _HREF_ATTR_RE.sub(_replace_href, html)


def build_theme_zip_bytes(template: Template) -> tuple[bytes, str]:
    slug = _safe_template_name(template.slug)
    root = f"{slug}-theme/"
    filename = f"{slug}-v{template.version}.zip"
    mapping = get_crafto_demo_or_default(template.slug)
    page_files = [mapping.pages[page] for page in ("home", "about", "services", "contact") if page in mapping.pages]
    page_paths = [CRAFTO_ROOT / file_name for file_name in page_files]

    queue: list[Path] = [path.resolve() for path in page_paths if path.is_file()]
    seen: set[Path] = set()
    packaged_text: dict[str, str] = {}
    packaged_binary: dict[str, bytes] = {}

    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)

        suffix = current.suffix.lower()
        if suffix in _IMAGE_SUFFIXES or not current.is_file():
            continue

        rel_path = current.relative_to(CRAFTO_ROOT).as_posix()
        if suffix in _TEXT_SUFFIXES:
            text = current.read_text(encoding="utf-8-sig", errors="replace")
            text = _rewrite_brand_mentions(text)
            packaged_text[rel_path] = text
            for dependency in _collect_refs_from_text(current, text):
                if dependency not in seen:
                    queue.append(dependency)
        else:
            packaged_binary[rel_path] = current.read_bytes()

    fallback_html_path = page_files[0]
    included_html_paths = {
        rel_path for rel_path in packaged_text.keys() if rel_path.lower().endswith((".html", ".htm"))
    }
    if fallback_html_path not in included_html_paths and included_html_paths:
        fallback_html_path = sorted(included_html_paths)[0]
    for rel_path, text in list(packaged_text.items()):
        if rel_path.lower().endswith((".html", ".htm")):
            packaged_text[rel_path] = _rewrite_html_links_for_packaged_targets(
                rel_path,
                text,
                included_html_paths=included_html_paths,
                fallback_html_path=fallback_html_path,
            )

    included_files = sorted([*packaged_text.keys(), *packaged_binary.keys()])
    readme = _build_materials_readme(template, included_files)
    image_notice = (
        "Image assets are intentionally excluded from this package.\n"
        f"Brand mentions are normalized to {_MATEO_DOWNLOAD_BRAND} in text materials.\n"
    )

    memory_file = BytesIO()
    with ZipFile(memory_file, mode="w", compression=ZIP_DEFLATED) as archive:
        for rel_path, text in sorted(packaged_text.items()):
            archive.writestr(f"{root}{rel_path}", text)
        for rel_path, payload in sorted(packaged_binary.items()):
            archive.writestr(f"{root}{rel_path}", payload)
        archive.writestr(f"{root}README.md", readme)
        archive.writestr(f"{root}IMAGE_ASSETS_NOTICE.txt", image_notice)

    return memory_file.getvalue(), filename
