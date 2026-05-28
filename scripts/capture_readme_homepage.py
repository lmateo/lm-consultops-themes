"""Capture the marketplace homepage for README documentation (Playwright).

Writes:
- homepage-readme-hero.png (zoomed, top section for readability)
- homepage-readme.png (full page, complete coverage)
- homepage.webp (archive)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "images"


def capture(
    base_url: str,
    viewport_width: int = 1600,
    viewport_height: int = 1000,
    device_scale_factor: float = 1.0,
    crop_height: int = 0,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    full_png = OUT_DIR / "homepage-full.png"
    readme_hero_png = OUT_DIR / "homepage-readme-hero.png"
    readme_png = OUT_DIR / "homepage-readme.png"
    webp_path = OUT_DIR / "homepage.webp"
    readme_width = min(viewport_width, 1400)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=device_scale_factor,
        )
        page.goto(f"{base_url.rstrip('/')}/", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(full_png), full_page=True)
        browser.close()

    with Image.open(full_png) as full_image:
        # Zoomed hero/top section for readability in README.
        hero_crop_height = min(1800, full_image.height)
        hero = full_image.crop((0, 0, full_image.width, hero_crop_height))
        if hero.width > readme_width:
            hero_h = int(hero.height * readme_width / hero.width)
            hero = hero.resize((readme_width, hero_h), Image.Resampling.LANCZOS)
        hero.save(readme_hero_png, "PNG", optimize=True)

        # Keep README image lossless (PNG) for text clarity, full-page.
        if full_image.width > readme_width:
            readme_h = int(full_image.height * readme_width / full_image.width)
            readme_im = full_image.resize((readme_width, readme_h), Image.Resampling.LANCZOS)
        else:
            readme_im = full_image
        readme_im.save(readme_png, "PNG", optimize=True)

        archive = full_image
        if crop_height > 0 and full_image.height > crop_height:
            archive = full_image.crop((0, 0, full_image.width, crop_height))
        if archive.width > readme_width:
            h = int(archive.height * readme_width / archive.width)
            archive = archive.resize((readme_width, h), Image.Resampling.LANCZOS)
        archive.save(webp_path, "WEBP", quality=88, method=6)

    full_png.unlink(missing_ok=True)
    print(f"Wrote {readme_hero_png} ({readme_width}px wide, top-section view)")
    print(f"Wrote {readme_png} ({readme_width}px wide, full-page capture)")
    print(f"Wrote {webp_path} (full-page archive unless --crop-height is set)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8010",
        help="App base URL (default: Docker port 8010)",
    )
    parser.add_argument("--viewport-width", type=int, default=1600)
    parser.add_argument("--viewport-height", type=int, default=1000)
    parser.add_argument("--device-scale-factor", type=float, default=1.0)
    parser.add_argument(
        "--crop-height",
        type=int,
        default=0,
        help="Max height for homepage.webp top crop (0 = full page)",
    )
    args = parser.parse_args()
    capture(
        args.base_url,
        args.viewport_width,
        args.viewport_height,
        args.device_scale_factor,
        args.crop_height,
    )


if __name__ == "__main__":
    main()
