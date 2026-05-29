"""Audit downloadable theme packages for security and content policy compliance."""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models import Template
from app.services.theme_packages import (
    FAST_AUDIT_CANARY_SLUG,
    ThemePackageFiles,
    collect_theme_package_files,
)

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


def _audit_package(package: ThemePackageFiles) -> list[str]:
    violations: list[str] = []
    template_slug = package.slug
    html_names = {
        rel_path for rel_path in package.text_files.keys() if rel_path.lower().endswith((".html", ".htm"))
    }
    combined_text_parts: list[str] = [package.readme, package.image_notice]

    for rel_path, decoded in package.text_files.items():
        combined_text_parts.append(decoded)
        if rel_path.lower().endswith((".html", ".htm")):
            for _, href in HREF_RE.findall(decoded):
                if _is_external_or_special(href):
                    continue
                href_path = href.split("?", 1)[0].split("#", 1)[0].strip()
                if not href_path.lower().endswith((".html", ".htm")):
                    continue
                resolved = _resolve_html_href(rel_path, href_path)
                if resolved not in html_names:
                    violations.append(f"{template_slug} | broken-local-html-link | {rel_path} -> {href}")

    for rel_path in package.binary_files.keys():
        if rel_path.lower().endswith(IMAGE_SUFFIXES):
            violations.append(f"{template_slug} | image-asset-included | {rel_path}")

    combined_text = "\n".join(combined_text_parts)
    lowered_text = combined_text.lower()
    for brand in BANNED_BRANDS:
        if brand.lower() in lowered_text:
            violations.append(f"{template_slug} | banned-brand-found | {brand}")
    if REQUIRED_BRAND.lower() not in lowered_text:
        violations.append(f"{template_slug} | required-brand-missing | {REQUIRED_BRAND}")
    return violations


def _resolve_fast_audit_slugs(all_slugs: list[str]) -> tuple[list[str], str]:
    if not all_slugs:
        return [], "fast-empty"
    canary = FAST_AUDIT_CANARY_SLUG if FAST_AUDIT_CANARY_SLUG in all_slugs else all_slugs[0]
    return [canary], f"fast-canary:{canary}"


def _load_templates(slugs: list[str] | None = None) -> list[Template]:
    with SessionLocal() as db:
        query = (
            select(Template)
            .options(joinedload(Template.category), joinedload(Template.industry))
            .order_by(Template.slug.asc())
        )
        templates = db.scalars(query).all()
    if slugs is None:
        return templates
    slug_set = set(slugs)
    return [template for template in templates if template.slug in slug_set]


def _audit_template(template: Template) -> list[str]:
    package = collect_theme_package_files(template)
    return _audit_package(package)


def _audit_templates_parallel(templates: list[Template], workers: int) -> list[str]:
    del workers  # Reserved for future parallel backends; sequential is fastest on Windows today.
    rows: list[str] = []
    for template in templates:
        rows.extend(_audit_template(template))
    return rows


def run(
    *,
    mode: str,
    slugs: list[str] | None,
    workers: int,
) -> str:
    started = time.perf_counter()
    all_templates = _load_templates()
    all_slugs = [template.slug for template in all_templates]

    if slugs:
        selected_slugs = slugs
        audit_mode = f"explicit:{','.join(slugs)}"
    elif mode == "full":
        selected_slugs = all_slugs
        audit_mode = "full"
    else:
        selected_slugs, audit_mode = _resolve_fast_audit_slugs(all_slugs)

    templates = [template for template in all_templates if template.slug in set(selected_slugs)]
    missing = sorted(set(selected_slugs) - {template.slug for template in templates})
    if missing:
        raise SystemExit(f"Unknown template slug(s): {', '.join(missing)}")

    rows = _audit_templates_parallel(templates, workers=workers)
    elapsed = time.perf_counter() - started

    lines = [
        "DOWNLOAD PACKAGE AUDIT",
        f"mode: {audit_mode}",
        f"workers: {min(workers, max(1, len(templates)))}",
        f"templates checked: {len(templates)}",
        f"elapsed_seconds: {elapsed:.2f}",
        f"violations: {len(rows)}",
    ]
    if rows:
        lines.append("\nVIOLATIONS")
        lines.extend(rows)
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("fast", "full"),
        default="fast",
        help="fast audits one canary template (default); full audits every template in parallel",
    )
    parser.add_argument(
        "--slugs",
        default="",
        help="Comma-separated template slugs to audit (overrides --mode)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel workers for template audits (default: 4)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    slug_list = [slug.strip() for slug in args.slugs.split(",") if slug.strip()] or None
    report = run(mode=args.mode, slugs=slug_list, workers=max(1, args.workers))
    print(report, end="")
    if "violations: 0" not in report:
        raise SystemExit(1)
