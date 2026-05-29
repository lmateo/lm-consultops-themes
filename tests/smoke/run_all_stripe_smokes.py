"""Run the full Stripe smoke suite, including purchase ZIP product validation.

Usage:
  py tests/smoke/run_all_stripe_smokes.py
  py tests/smoke/run_all_stripe_smokes.py --base-url http://localhost:8010
  py tests/smoke/run_all_stripe_smokes.py --skip-cli --skip-e2e
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.http_ssl import httpx_verify_option


@dataclass
class SmokeStep:
    name: str
    command: list[str]
    enabled: bool = True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run all Stripe smoke tests.")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--template-slug", default="cloudcare-it")
    parser.add_argument("--artifact-dir", default="artifacts/smoke")
    parser.add_argument("--skip-cli", action="store_true", help="Skip Stripe CLI webhook smoke.")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip Playwright checkout + ZIP E2E smoke.")
    parser.add_argument(
        "--sync-docker-webhook-secret",
        action="store_true",
        help="Sync stripe listen whsec into .env during CLI smoke.",
    )
    parser.add_argument("--headed-e2e", action="store_true", help="Run checkout E2E in headed browser mode.")
    parser.add_argument("--health-timeout-sec", type=int, default=120)
    return parser


def _wait_for_health(base_url: str, timeout_sec: int) -> None:
    target = f"{base_url.rstrip('/')}/health"
    deadline = time.time() + timeout_sec
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(target, timeout=10.0, verify=httpx_verify_option())
            response.raise_for_status()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2.0)
    raise RuntimeError(f"App not healthy at {target}: {last_error}")


def _run_step(step: SmokeStep) -> int:
    print("")
    print(f"== {step.name} ==")
    result = subprocess.run(step.command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        print(f"PASS: {step.name}")
    else:
        print(f"FAIL: {step.name} (exit {result.returncode})")
    return result.returncode


def run(
    base_url: str,
    template_slug: str,
    artifact_dir: str,
    *,
    skip_cli: bool,
    skip_e2e: bool,
    sync_docker_webhook_secret: bool,
    headed_e2e: bool,
    health_timeout_sec: int,
) -> int:
    py = sys.executable
    email = f"stripe-all-smoke-{random.randint(100000, 999999)}@example.com"
    steps: list[SmokeStep] = [
        SmokeStep(
            "Mocked fulfillment + ZIP validation",
            [
                py,
                "tests/smoke/run_stripe_download_fulfillment_smoke.py",
                "--mode",
                "mocked",
                "--template-slug",
                template_slug,
                "--artifact-dir",
                artifact_dir,
            ],
        ),
        SmokeStep(
            "Playwright checkout redirect",
            [
                py,
                "tests/smoke/run_purchase_playwright_smoke.py",
                "--base-url",
                base_url,
                "--template-slug",
                template_slug,
            ],
        ),
        SmokeStep(
            "Live fulfillment + ZIP validation",
            [
                py,
                "tests/smoke/run_stripe_download_fulfillment_smoke.py",
                "--mode",
                "live",
                "--base-url",
                base_url,
                "--template-slug",
                template_slug,
                "--email",
                email,
                "--artifact-dir",
                artifact_dir,
            ],
        ),
    ]

    if not skip_e2e:
        e2e_cmd = [
            py,
            "tests/smoke/run_stripe_purchase_zip_e2e_smoke.py",
            "--base-url",
            base_url,
            "--template-slug",
            template_slug,
            "--artifact-dir",
            artifact_dir,
        ]
        if headed_e2e:
            e2e_cmd.append("--headed")
        steps.append(SmokeStep("Playwright checkout + purchase ZIP E2E", e2e_cmd))

    if not skip_cli:
        cli_cmd = [
            py,
            "tests/smoke/run_stripe_cli_webhook_smoke.py",
            "--base-url",
            base_url,
            "--template-slug",
            template_slug,
        ]
        if sync_docker_webhook_secret:
            cli_cmd.append("--sync-docker-webhook-secret")
        steps.append(SmokeStep("Stripe CLI webhook delivery", cli_cmd))

    print("== Stripe Full Smoke Suite ==")
    print(f"base_url={base_url}")
    print(f"template_slug={template_slug}")
    print(f"artifact_dir={artifact_dir}")
    print(f"steps={len(steps)}")

    try:
        _wait_for_health(base_url, health_timeout_sec)
    except Exception as exc:  # noqa: BLE001
        print(f"STRIPE_ALL_SMOKES_FAIL: {exc}")
        return 1

    failures: list[str] = []
    for step in steps:
        code = _run_step(step)
        if code != 0:
            failures.append(step.name)

    print("")
    print("== Summary ==")
    if failures:
        print("STRIPE_ALL_SMOKES_FAIL")
        for name in failures:
            print(f"failed_step={name}")
        return 1

    print("STRIPE_ALL_SMOKES_PASS")
    print("zip_validation=covered_by_fulfillment_and_e2e")
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    return run(
        base_url=args.base_url,
        template_slug=args.template_slug,
        artifact_dir=args.artifact_dir,
        skip_cli=args.skip_cli,
        skip_e2e=args.skip_e2e,
        sync_docker_webhook_secret=args.sync_docker_webhook_secret,
        headed_e2e=args.headed_e2e,
        health_timeout_sec=args.health_timeout_sec,
    )


if __name__ == "__main__":
    sys.exit(main())
