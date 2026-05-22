"""Audit mapped demo pages for HTML/CSS/JS references and template includes."""

from __future__ import annotations

import re
from pathlib import Path

from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS
from app.services.crafto_preview_wrap import (
    CRAFTO_ROOT,
    rewrite_crafto_brand_assets,
    rewrite_crafto_brand_copy,
    rewrite_crafto_preview_links,
)

ATTR_RE = re.compile(r"""\b(?:href|src)=(["'])([^"']+)\1""", re.IGNORECASE)
LOGO_ATTR_RE = re.compile(r"""\b(?:href|src|data-at2x)=(["'])([^"']+)\1""", re.IGNORECASE)
INCLUDE_RE = re.compile(r"""\{\%\s*(?:include|extends|import)\s+["']([^"']+)["']""")
SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")
MATEO_LOGO = "/static/images/logos/mateo-logo_horizontal_transparent.png"
MATEO_FAVICON = "/static/images/logos/mateo-favicon.ico"
BRAND_TERM_RE = re.compile(r"\b(?:Crafto|ThemeZaa)\b", re.IGNORECASE)
HEADER_OR_FOOTER_RE = re.compile(
    r"(?:<!-- start header -->(.*?)<!-- end header -->|<!-- start footer -->(.*?)<!-- end footer -->|<header[^>]*>.*?</header>|<footer[^>]*>.*?</footer>)",
    re.IGNORECASE | re.DOTALL,
)


def _resolve_crafto_ref(file_path: Path, ref: str) -> Path:
    """Resolve demo-local path first, then Crafto-root absolute style paths."""
    local_candidate = (file_path.parent / ref).resolve()
    try:
        local_candidate.relative_to(CRAFTO_ROOT.resolve())
        return local_candidate
    except ValueError:
        return (CRAFTO_ROOT / ref.lstrip("/")).resolve()


def run() -> str:
    workspace = Path(__file__).resolve().parents[1]
    crafto_root = CRAFTO_ROOT.resolve()

    missing_html: list[tuple[str, str, str, str]] = []
    missing_assets: list[tuple[str, str, str, str]] = []
    missing_includes: list[tuple[str, str]] = []
    branding_hits: set[str] = set()
    logo_issues: list[tuple[str, str, str, str]] = []
    header_footer_brand_issues: list[tuple[str, str, str, str]] = []

    for slug, mapping in sorted(CRAFTO_TEMPLATE_DEMOS.items()):
        for page, filename in sorted(mapping.pages.items()):
            file_path = (crafto_root / filename).resolve()
            html = file_path.read_text(encoding="utf-8-sig", errors="replace")
            for _, raw_ref in ATTR_RE.findall(html):
                ref = raw_ref.strip()
                lowered = ref.lower()
                if not ref or lowered.startswith(SKIP_PREFIXES) or lowered.startswith(("http://", "https://", "//")):
                    continue
                ref = ref.split("?", 1)[0].split("#", 1)[0].strip()
                if not ref:
                    continue
                resolved = _resolve_crafto_ref(file_path, ref)
                exists = resolved.exists()
                if ref.lower().endswith((".html", ".htm")):
                    if not exists:
                        missing_html.append((slug, page, filename, ref))
                elif not exists:
                    missing_assets.append((slug, page, filename, ref))

            branded_html = rewrite_crafto_brand_assets(html)
            branded_html = rewrite_crafto_preview_links(branded_html, slug=slug, crafto=mapping)
            branded_html = rewrite_crafto_brand_copy(branded_html)
            if MATEO_FAVICON not in branded_html:
                logo_issues.append((slug, page, filename, "missing Mateo favicon in wrapped preview"))
            if MATEO_LOGO not in branded_html:
                logo_issues.append((slug, page, filename, "missing Mateo primary logo in wrapped preview"))
            remaining_brand_assets = [
                value
                for _, value in LOGO_ATTR_RE.findall(branded_html)
                if re.search(r"(?:demo-[^\"']*logo|favicon\.png|apple-touch-icon)", value, flags=re.IGNORECASE)
            ]
            if remaining_brand_assets:
                logo_issues.append(
                    (
                        slug,
                        page,
                        filename,
                        f"Crafto logo/favicon asset remains: {remaining_brand_assets[0]}",
                    )
                )

            for block_match in HEADER_OR_FOOTER_RE.finditer(branded_html):
                block = block_match.group(0)
                offending = BRAND_TERM_RE.search(block)
                if offending:
                    header_footer_brand_issues.append(
                        (slug, page, filename, f'header/footer still contains "{offending.group(0)}"')
                    )
                    break

    demo_templates_dir = workspace / "app" / "templates" / "demos"
    for template_file in demo_templates_dir.rglob("*.html"):
        text = template_file.read_text(encoding="utf-8", errors="replace")
        for include in INCLUDE_RE.findall(text):
            include_target = (workspace / "app" / "templates" / include.replace("/", "\\")).resolve()
            if not include_target.exists():
                missing_includes.append((str(template_file.relative_to(workspace)), include))

    branding_scan_roots = [
        workspace / "app" / "templates" / "demos",
        workspace / "app" / "templates" / "components",
        workspace / "app" / "services",
        workspace / "app" / "routers",
    ]
    for root in branding_scan_roots:
        for file_path in root.rglob("*"):
            if file_path.suffix.lower() not in {".html", ".py", ".js", ".css"}:
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if "Crafto" in text or "ThemeZaa" in text:
                branding_hits.add(str(file_path.relative_to(workspace)))

    lines = [
        "ASSET/LINK/COMPONENT AUDIT",
        f"mapped pages checked: {sum(len(m.pages) for m in CRAFTO_TEMPLATE_DEMOS.values())}",
        f"missing html refs: {len(missing_html)}",
        f"missing asset refs: {len(missing_assets)}",
        f"missing jinja includes: {len(missing_includes)}",
        f"logo/favicon issues in wrapped preview: {len(logo_issues)}",
        f"header/footer brand text issues in wrapped preview: {len(header_footer_brand_issues)}",
        f"branding mentions in app paths: {len(branding_hits)}",
    ]

    if missing_html:
        lines.append("\nMISSING HTML REFS (first 50)")
        lines.extend(" | ".join(row) for row in missing_html[:50])
    if missing_assets:
        lines.append("\nMISSING ASSET REFS (first 50)")
        lines.extend(" | ".join(row) for row in missing_assets[:50])
    if missing_includes:
        lines.append("\nMISSING JINJA INCLUDES")
        lines.extend(" | ".join(row) for row in missing_includes[:50])
    if logo_issues:
        lines.append("\nLOGO/FAVICON ISSUES")
        lines.extend(" | ".join(row) for row in logo_issues[:50])
    if header_footer_brand_issues:
        lines.append("\nHEADER/FOOTER BRAND TEXT ISSUES")
        lines.extend(" | ".join(row) for row in header_footer_brand_issues[:50])
    if branding_hits:
        lines.append("\nBRANDING MENTIONS (app paths)")
        lines.extend(sorted(branding_hits))

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(run(), end="")
