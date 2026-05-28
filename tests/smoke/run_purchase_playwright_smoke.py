"""Playwright smoke test runner for purchase checkout flow.

Usage:
  py tests/smoke/run_purchase_playwright_smoke.py
  py tests/smoke/run_purchase_playwright_smoke.py --base-url http://localhost:8010
  py tests/smoke/run_purchase_playwright_smoke.py --template-slug cloudcare-it
  py tests/smoke/run_purchase_playwright_smoke.py --headed
"""

from __future__ import annotations

import argparse
import re
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Playwright smoke test for /purchase flow.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8010",
        help="Base URL where the app is running.",
    )
    parser.add_argument(
        "--template-slug",
        default="cloudcare-it",
        help="Template slug to test checkout flow.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=45000,
        help="Timeout in milliseconds for page actions.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (default is headless).",
    )
    return parser


def run(base_url: str, template_slug: str, timeout_ms: int, headed: bool) -> int:
    base = base_url.rstrip("/")
    purchase_url = f"{base}/purchase/{template_slug}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(purchase_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector("h1:has-text('Checkout')", timeout=timeout_ms)

            # If Stripe is not configured, verify fallback UX and pass smoke.
            if page.locator("text=Stripe checkout is temporarily unavailable").count() > 0:
                print("PLAYWRIGHT_PURCHASE_SMOKE_PASS: stripe_unavailable_fallback")
                return 0

            page.fill('input[name="first_name"]', "Playwright")
            page.fill('input[name="last_name"]', "Smoke")
            page.fill('input[name="email"]', "playwright.purchase.smoke@example.com")
            page.fill('input[name="company"]', "Smoke QA")
            page.check('input[name="agree_terms"]')

            with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_ms):
                page.click('button[type="submit"]')

            current_url = page.url
            if not re.match(r"^https://checkout\.stripe\.com/", current_url):
                print(f"PLAYWRIGHT_PURCHASE_SMOKE_FAIL: expected Stripe checkout redirect, got {current_url}")
                return 1

            print("PLAYWRIGHT_PURCHASE_SMOKE_PASS: stripe_redirect")
            return 0
        except PlaywrightTimeoutError as exc:
            print(f"PLAYWRIGHT_PURCHASE_SMOKE_FAIL: timeout {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"PLAYWRIGHT_PURCHASE_SMOKE_FAIL: {exc}")
            return 1
        finally:
            context.close()
            browser.close()


def main() -> int:
    args = _build_parser().parse_args()
    return run(
        base_url=args.base_url,
        template_slug=args.template_slug,
        timeout_ms=args.timeout_ms,
        headed=args.headed,
    )


if __name__ == "__main__":
    sys.exit(main())
