"""Playwright smoke test runner for contact form submission.

Usage:
  py tests/smoke/run_contact_playwright_smoke.py
  py tests/smoke/run_contact_playwright_smoke.py --base-url http://localhost:8000
  py tests/smoke/run_contact_playwright_smoke.py --headed
"""

from __future__ import annotations

import argparse
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Playwright smoke test for /contact flow.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8010",
        help="Base URL where the app is running.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=60000,
        help="Timeout in milliseconds for page actions.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (default is headless).",
    )
    return parser


def run(base_url: str, timeout_ms: int, headed: bool) -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        page = browser.new_page()
        try:
            page.goto(f"{base_url.rstrip('/')}/contact", wait_until="networkidle", timeout=timeout_ms)

            page.fill('input[name="name"]', "Playwright Smoke")
            page.fill('input[name="email"]', "playwright.smoke@example.com")
            page.fill("textarea[name=\"message\"]", "Playwright smoke test for contact form integration")

            turnstile = page.locator(".cf-turnstile")
            if turnstile.count() > 0:
                page.wait_for_function(
                    "() => document.querySelector('input[name=\"cf-turnstile-response\"]')?.value",
                    timeout=timeout_ms,
                )

            page.click('button[type="submit"]')

            page.wait_for_selector("text=Thank you. Your message was sent successfully.", timeout=timeout_ms)
            print("PLAYWRIGHT_SMOKE_PASS")
            return 0
        except (PlaywrightTimeoutError, ValueError) as exc:
            print(f"PLAYWRIGHT_SMOKE_FAIL: {exc}")
            return 1
        finally:
            browser.close()


def main() -> int:
    args = _build_parser().parse_args()
    return run(base_url=args.base_url, timeout_ms=args.timeout_ms, headed=args.headed)


if __name__ == "__main__":
    sys.exit(main())
