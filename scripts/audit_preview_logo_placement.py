"""Audit live preview headers for logo placement before Home link.

This script opens each mapped preview home page using Playwright, captures a screenshot,
and verifies:
1) header navbar exists
2) navbar-brand exists
3) Home link exists
4) brand appears before Home in document order
5) brand and Home do not overlap visually
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS


OUT_DIR = Path("artifacts/live-preview-audit")
BASE_URL = "http://localhost:8010"


def run() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900})

        for slug in sorted(CRAFTO_TEMPLATE_DEMOS.keys()):
            url = f"{BASE_URL}/preview/{slug}/home"
            page.goto(url, wait_until="networkidle", timeout=30000)

            data = page.evaluate(
                """
() => {
  const nav = document.querySelector('.mkt-preview-canvas header .navbar');
  const brand = nav ? nav.querySelector('.navbar-brand') : null;
  const home = nav
    ? Array.from(nav.querySelectorAll('a.nav-link, a'))
        .find((a) => a.textContent.trim().toLowerCase() === 'home')
    : null;
  const brandRect = brand ? brand.getBoundingClientRect() : null;
  const homeRect = home ? home.getBoundingClientRect() : null;
  const brandBeforeHome = !!(
    brand &&
    home &&
    (brand.compareDocumentPosition(home) & Node.DOCUMENT_POSITION_FOLLOWING)
  );
  const overlaps = !!(
    brandRect &&
    homeRect &&
    !(
      brandRect.right <= homeRect.left ||
      homeRect.right <= brandRect.left ||
      brandRect.bottom <= homeRect.top ||
      homeRect.bottom <= brandRect.top
    )
  );
  return {
    hasNav: !!nav,
    hasBrand: !!brand,
    hasHome: !!home,
    brandBeforeHome,
    overlaps,
    brandRect,
    homeRect
  };
}
                """
            )

            screenshot = OUT_DIR / f"{slug}-home.png"
            page.screenshot(path=str(screenshot), full_page=False)

            status = "pass"
            if not (
                data["hasNav"]
                and data["hasBrand"]
                and data["hasHome"]
                and data["brandBeforeHome"]
                and not data["overlaps"]
            ):
                status = "fail"

            results.append(
                {
                    "slug": slug,
                    "url": url,
                    "status": status,
                    "screenshot": str(screenshot),
                    **data,
                }
            )

        browser.close()

    report = {
        "total": len(results),
        "passes": sum(1 for r in results if r["status"] == "pass"),
        "fails": sum(1 for r in results if r["status"] == "fail"),
        "results": results,
    }
    report_path = OUT_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"PREVIEW LOGO PLACEMENT AUDIT")
    print(f"report: {report_path}")
    print(f"passes: {report['passes']}")
    print(f"fails: {report['fails']}")
    print(f"total: {report['total']}")
    for row in report["results"]:
        if row["status"] == "fail":
            print(
                "FAIL",
                row["slug"],
                f"hasNav={row['hasNav']}",
                f"hasBrand={row['hasBrand']}",
                f"hasHome={row['hasHome']}",
                f"brandBeforeHome={row['brandBeforeHome']}",
                f"overlaps={row['overlaps']}",
            )
    return 0 if report["fails"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
