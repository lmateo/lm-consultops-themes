"""Capture the marketplace homepage for README documentation (Playwright).

Figma MCP is optional when Cursor OAuth works — see docs/figma-mcp-homepage-capture.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "images"


def capture(base_url: str, viewport_width: int = 1440) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = OUT_DIR / "homepage.png"
    webp_path = OUT_DIR / "homepage.webp"
    readme_path = OUT_DIR / "homepage-readme.webp"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": viewport_width, "height": 900})
        page.goto(f"{base_url.rstrip('/')}/", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()

    with Image.open(png_path) as image:
        if image.width > 1280:
            height = int(image.height * 1280 / image.width)
            image = image.resize((1280, height), Image.Resampling.LANCZOS)
        image.save(webp_path, "WEBP", quality=82, method=6)
        image.save(readme_path, "WEBP", quality=78, method=6)

    png_path.unlink(missing_ok=True)
    print(f"Wrote {webp_path} and {readme_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8010",
        help="App base URL (default: Docker port 8010)",
    )
    parser.add_argument("--viewport-width", type=int, default=1440)
    args = parser.parse_args()
    capture(args.base_url, args.viewport_width)


if __name__ == "__main__":
    main()
