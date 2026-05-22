"""Audit header/footer links in Crafto preview demo HTML files."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS
from app.services.crafto_preview_wrap import CRAFTO_ROOT, _resolve_preview_href

_HREF_RE = re.compile(
    r'<a\s+([^>]*?)href=(["\'])([^"\']*)\2([^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TEXT_RE = re.compile(r"<[^>]+>")
_HEADER_RE = re.compile(
    r"<!-- start header -->(.*?)<!-- end header -->",
    re.DOTALL | re.IGNORECASE,
)
_FOOTER_RE = re.compile(
    r"<!-- start footer -->(.*?)<!-- end footer -->",
    re.DOTALL | re.IGNORECASE,
)
_HEADER_TAG_RE = re.compile(r"<header[^>]*>(.*?)</header>", re.DOTALL | re.IGNORECASE)
_FOOTER_TAG_RE = re.compile(r"<footer[^>]*>(.*?)</footer>", re.DOTALL | re.IGNORECASE)


def extract_region(html: str, region: str) -> str:
    if region == "header":
        match = _HEADER_RE.search(html) or _HEADER_TAG_RE.search(html)
    else:
        match = _FOOTER_RE.search(html) or _FOOTER_TAG_RE.search(html)
    return match.group(1) if match else ""


def clean_text(raw: str) -> str:
    text = _TEXT_RE.sub(" ", raw)
    return " ".join(text.split())[:80]


def classify(raw: str, resolved: str) -> str:
    lowered = raw.lower()
    resolved_lower = resolved.lower()
    if resolved_lower == "#":
        return "disabled"
    if lowered.startswith(("mailto:", "tel:")):
        return "contact"
    if lowered.startswith("#"):
        return "anchor"
    if resolved_lower.startswith("/preview/"):
        return "preview-route"
    if resolved_lower.startswith(("/static/", "/crafto/", "/templates/", "/purchase/")):
        return "mateo-asset"
    if lowered.startswith(("http://", "https://", "//")):
        return "external"
    if raw != resolved:
        return "rewritten"
    return "unchanged"


def audit() -> tuple[list[dict], dict[str, dict[str, int]]]:
    rows: list[dict] = []
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for slug, crafto in sorted(CRAFTO_TEMPLATE_DEMOS.items()):
        for page, filename in sorted(crafto.pages.items()):
            path = CRAFTO_ROOT / filename
            html = path.read_text(encoding="utf-8-sig", errors="replace")
            for region in ("header", "footer"):
                chunk = extract_region(html, region)
                if not chunk:
                    rows.append(
                        {
                            "slug": slug,
                            "page": page,
                            "file": filename,
                            "region": region,
                            "status": "MISSING_REGION",
                        }
                    )
                    summary[region]["missing"] += 1
                    continue

                seen: set[str] = set()
                for match in _HREF_RE.finditer(chunk):
                    raw = match.group(3).strip()
                    if raw in seen:
                        continue
                    seen.add(raw)
                    resolved = _resolve_preview_href(raw, slug=slug, crafto=crafto)
                    label = clean_text(match.group(5))
                    category = classify(raw, resolved)
                    rows.append(
                        {
                            "slug": slug,
                            "page": page,
                            "file": filename,
                            "region": region,
                            "label": label,
                            "raw_href": raw,
                            "resolved_href": resolved,
                            "category": category,
                            "changed": raw != resolved,
                        }
                    )
                    summary[region][category] += 1
    return rows, summary


def main() -> None:
    rows, summary = audit()

    print("=" * 80)
    print("PREVIEW TEMPLATE HEADER/FOOTER LINK AUDIT")
    print(
        f"Templates: {len(CRAFTO_TEMPLATE_DEMOS)} | Pages each: 4 | Regions: header, footer"
    )
    print("=" * 80)

    for slug in sorted(CRAFTO_TEMPLATE_DEMOS.keys()):
        crafto = CRAFTO_TEMPLATE_DEMOS[slug]
        print(f"\n## {slug} ({crafto.crafto_demo_label})")
        for page in ("home", "about", "services", "contact"):
            page_rows = [row for row in rows if row["slug"] == slug and row["page"] == page]
            if not page_rows:
                continue
            filename = crafto.pages[page]
            print(f"\n### {page} — {filename}")
            for region in ("header", "footer"):
                region_rows = [row for row in page_rows if row.get("region") == region]
                print(f"\n**{region.upper()}** ({len(region_rows)} links)")
                if not region_rows:
                    print("  (none)")
                    continue
                for row in region_rows:
                    if row.get("status") == "MISSING_REGION":
                        print("  [!] Region not found in HTML")
                        continue
                    changed = " *" if row["changed"] else ""
                    print(f"  - [{row['category']}] {row['label'] or '(no text)'}")
                    print(f"      raw: {row['raw_href']}")
                    if row["changed"]:
                        print(f"      -> {row['resolved_href']}{changed}")

    print("\n" + "=" * 80)
    print("AGGREGATE SUMMARY (unique raw hrefs per region across all pages)")
    print("=" * 80)
    unique: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: {"raw": set(), "resolved": set(), "cats": set()}
    )
    for row in rows:
        if row.get("status"):
            continue
        key = (row["slug"], row["region"])
        unique[key]["raw"].add(row["raw_href"])
        unique[key]["resolved"].add(row["resolved_href"])
        unique[key]["cats"].add(row["category"])

    for slug in sorted(CRAFTO_TEMPLATE_DEMOS.keys()):
        print(f"\n{slug}:")
        for region in ("header", "footer"):
            key = (slug, region)
            if key not in unique:
                print(f"  {region}: no data")
                continue
            data = unique[key]
            print(
                f"  {region}: {len(data['raw'])} unique raw | "
                f"{len(data['resolved'])} unique resolved"
            )
            for category in sorted(data["cats"]):
                count = sum(
                    1
                    for row in rows
                    if row.get("slug") == slug
                    and row.get("region") == region
                    and row.get("category") == category
                )
                print(f"    - {category}: {count} link instances")

    print("\n" + "=" * 80)
    print("GLOBAL CATEGORY COUNTS (all header/footer link instances)")
    print("=" * 80)
    for region in ("header", "footer"):
        print(f"\n{region.upper()}:")
        for category, count in sorted(summary[region].items(), key=lambda item: -item[1]):
            print(f"  {category}: {count}")

    print("\n" + "=" * 80)
    print("PREVIEW CHROME (toolbar above wrapped demos)")
    print("=" * 80)
    chrome_links = [
        ("Back", "/templates/{slug}"),
        ("Home", "/preview/{slug}/home"),
        ("About", "/preview/{slug}/about"),
        ("Services", "/preview/{slug}/services"),
        ("Contact", "/preview/{slug}/contact"),
        ("Purchase", "/purchase/{slug}"),
    ]
    for label, href in chrome_links:
        print(f"  - {label}: {href}")

    issues: list[tuple[str, ...]] = []
    for row in rows:
        if row.get("status"):
            issues.append((row["slug"], row["page"], row["region"], "missing region"))
            continue
        if row["category"] == "external":
            issues.append((row["slug"], row["page"], row["region"], f"external: {row['raw_href']}"))
        if row["category"] == "unchanged" and row["raw_href"].endswith(".html"):
            issues.append(
                (row["slug"], row["page"], row["region"], f"unrewritten html: {row['raw_href']}")
            )
        if (
            "themezaa" in row["raw_href"].lower()
            and row["resolved_href"] not in {"#", f"/preview/{row['slug']}/home"}
        ):
            issues.append(
                (
                    row["slug"],
                    row["page"],
                    row["region"],
                    f"vendor not neutralized: {row['raw_href']} -> {row['resolved_href']}",
                )
            )

    print("\n" + "=" * 80)
    print(f"POTENTIAL ISSUES ({len(issues)})")
    print("=" * 80)
    for item in issues:
        print("  ", " | ".join(item))


if __name__ == "__main__":
    main()
