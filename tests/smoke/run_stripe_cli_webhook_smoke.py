"""Automated Stripe CLI webhook delivery smoke test.

Starts ``stripe listen``, fires ``checkout.session.completed`` via Stripe CLI,
and verifies the event was forwarded to ``/webhooks/stripe``.

Usage:
  py tests/smoke/run_stripe_cli_webhook_smoke.py
  py tests/smoke/run_stripe_cli_webhook_smoke.py --base-url http://localhost:8010
  py tests/smoke/run_stripe_cli_webhook_smoke.py --sync-docker-webhook-secret
  py tests/smoke/run_stripe_cli_webhook_smoke.py --full-checkout
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routers import public
from app.utils.http_ssl import httpx_verify_option

WHSEC_RE = re.compile(r"whsec_[A-Za-z0-9]+")
COMPLETED_RE = re.compile(r"checkout\.session\.completed")
WEBHOOK_PATH_RE = re.compile(r"/webhooks/stripe")
SUCCESS_RE = re.compile(r"(HTTP/1\.1|HTTP/2)\s+2\d\d|status=\s*2\d\d|\[200\]\s+POST|succeeded|success", re.IGNORECASE)
FAILURE_RE = re.compile(
    r"(HTTP/1\.1|HTTP/2)\s+[45]\d\d|status=\s*[45]\d\d|\[(?:400|401|403|404|500)\]\s+POST|"
    r"signature verification failed|webhook signature verification failed|"
    r"Webhook signature verification failed",
    re.IGNORECASE,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated Stripe CLI webhook delivery smoke test.")
    parser.add_argument("--base-url", default="http://localhost:8010", help="App base URL.")
    parser.add_argument("--template-slug", default="cloudcare-it", help="Template slug for checkout.")
    parser.add_argument("--log-file", default="artifacts/stripe-listen.log", help="Stripe listen log path.")
    parser.add_argument("--timeout-sec", type=int, default=120, help="Max wait for webhook log evidence.")
    parser.add_argument(
        "--sync-docker-webhook-secret",
        action="store_true",
        help="Write listen whsec into .env and restart docker compose before testing.",
    )
    parser.add_argument(
        "--full-checkout",
        action="store_true",
        help="Open purchase page in browser for manual 4242 test payment instead of stripe trigger.",
    )
    parser.add_argument("--headed", action="store_true", help="Run Playwright in headed mode (--full-checkout only).")
    return parser


def _resolve_stripe_cli() -> str:
    cli = shutil.which("stripe")
    if cli:
        return cli
    for candidate in (
        Path(os.environ.get("LOCALAPPDATA", "")) / "stripe" / "stripe.exe",
        Path("C:/Program Files/Stripe/stripe.exe"),
        Path("C:/ProgramData/chocolatey/bin/stripe.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError(
        "Stripe CLI is not installed or not on PATH. Install from https://docs.stripe.com/stripe-cli"
    )


def _wait_for_health(base_url: str, timeout_sec: int = 90) -> None:
    deadline = time.time() + timeout_sec
    last_error: Exception | None = None
    target = f"{base_url.rstrip('/')}/health"
    while time.time() < deadline:
        try:
            response = httpx.get(target, timeout=10.0, verify=httpx_verify_option())
            response.raise_for_status()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2.0)
    raise RuntimeError(f"App did not become healthy at {target}: {last_error}")


def _health_ok(base_url: str) -> None:
    _wait_for_health(base_url, timeout_sec=15)


def _stripe_api_key() -> str:
    secret = public.settings.stripe_secret_key.strip()
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured in environment.")
    return secret


def _stripe_listen_command(stripe_cli: str, forward_url: str, api_key: str) -> list[str]:
    command = [stripe_cli, "listen", "--forward-to", forward_url, "--log-level", "debug"]
    if api_key.startswith("sk_test_"):
        command.extend(["--api-key", api_key])
        return command
    if api_key.startswith("sk_live_"):
        command.append("--live")
        return command
    if api_key.startswith("rk_live_") or api_key.startswith("rk_test_"):
        command.extend(["--api-key", api_key])
        if api_key.startswith("rk_live_"):
            command.append("--live")
        return command
    command.extend(["--api-key", api_key])
    return command


def _stripe_trigger_command(stripe_cli: str, api_key: str) -> list[str]:
    command = [stripe_cli, "trigger", "checkout.session.completed"]
    if api_key.startswith("sk_test_"):
        return [*command, "--api-key", api_key]
    if api_key.startswith("sk_live_"):
        return [*command, "--live"]
    if api_key.startswith("rk_live_") or api_key.startswith("rk_test_"):
        args = [*command, "--api-key", api_key]
        if api_key.startswith("rk_live_"):
            args.append("--live")
        return args
    return [*command, "--api-key", api_key]


def _start_stripe_listen(stripe_cli: str, forward_url: str, log_file: Path, *, api_key: str) -> subprocess.Popen[str]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("", encoding="utf-8")
    command = _stripe_listen_command(stripe_cli, forward_url, api_key)
    with log_file.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT,
        )
    return process


def _wait_for_listen_secret(log_file: Path, timeout_sec: int) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if log_file.exists():
            match = WHSEC_RE.search(log_file.read_text(encoding="utf-8", errors="ignore"))
            if match:
                return match.group(0)
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for Stripe listen webhook secret in {log_file}")


def _sync_env_webhook_secret(whsec: str) -> str | None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return None
    original = env_path.read_text(encoding="utf-8")
    if re.search(r"^STRIPE_WEBHOOK_SECRET=.*$", original, flags=re.MULTILINE):
        updated = re.sub(r"^STRIPE_WEBHOOK_SECRET=.*$", f"STRIPE_WEBHOOK_SECRET={whsec}", original, count=1, flags=re.MULTILINE)
    else:
        updated = original.rstrip() + f"\nSTRIPE_WEBHOOK_SECRET={whsec}\n"
    env_path.write_text(updated, encoding="utf-8")
    return original


def _restore_env_webhook_secret(original: str | None) -> None:
    if original is None:
        return
    (PROJECT_ROOT / ".env").write_text(original, encoding="utf-8")


def _restart_docker() -> None:
    docker_ps1 = PROJECT_ROOT / "docker.ps1"
    if not docker_ps1.is_file():
        raise RuntimeError("docker.ps1 not found; cannot restart docker stack.")
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(docker_ps1), "restart"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    _wait_for_health("http://localhost:8010", timeout_sec=120)


def _trigger_checkout_completed(stripe_cli: str, *, api_key: str) -> None:
    result = subprocess.run(
        _stripe_trigger_command(stripe_cli, api_key),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"stripe trigger checkout.session.completed failed: {detail}")


def _open_manual_checkout(base_url: str, template_slug: str) -> None:
    purchase_url = f"{base_url.rstrip('/')}/purchase/{template_slug}"
    if sys.platform == "win32":
        os.startfile(purchase_url)  # noqa: S606
    else:
        subprocess.run(["xdg-open", purchase_url], check=False)
    print(f"Opened purchase page: {purchase_url}")
    print("Complete payment with card 4242 4242 4242 4242, then wait for webhook log evidence...")


def _complete_checkout_with_playwright(base_url: str, template_slug: str, *, headed: bool, timeout_ms: int = 120_000) -> None:
    from playwright.sync_api import sync_playwright

    purchase_url = f"{base_url.rstrip('/')}/purchase/{template_slug}"
    email = f"stripe-cli-smoke-{int(time.time())}@example.com"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(purchase_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("h1:has-text('Checkout')", timeout=timeout_ms)
            if page.locator("text=Stripe checkout is temporarily unavailable").count() > 0:
                raise RuntimeError("Stripe checkout unavailable on purchase page.")

            page.fill('input[name="first_name"]', "Stripe")
            page.fill('input[name="last_name"]', "CLI")
            page.fill('input[name="email"]', email)
            page.fill('input[name="company"]', "Smoke QA")
            page.check('input[name="agree_terms"]')

            with page.expect_navigation(url=re.compile(r"^https://checkout\.stripe\.com/"), timeout=timeout_ms):
                page.click('button[type="submit"]')

            print("Stripe Checkout opened. Complete payment manually with card 4242 4242 4242 4242.")
            page.wait_for_timeout(min(timeout_ms, 120_000))
        finally:
            context.close()
            browser.close()


def _analyze_log(log_file: Path) -> tuple[bool, dict[str, bool]]:
    content = log_file.read_text(encoding="utf-8", errors="ignore") if log_file.is_file() else ""
    summary = {
        "completed": bool(COMPLETED_RE.search(content)),
        "webhook_path": bool(WEBHOOK_PATH_RE.search(content)),
        "success": bool(SUCCESS_RE.search(content)),
        "failure": bool(FAILURE_RE.search(content)),
    }
    passed = summary["completed"] and summary["webhook_path"] and summary["success"] and not summary["failure"]
    return passed, summary


def _wait_for_log_evidence(log_file: Path, timeout_sec: int) -> tuple[bool, dict[str, bool]]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        passed, summary = _analyze_log(log_file)
        if passed or summary["failure"]:
            return passed, summary
        time.sleep(1.0)
    return _analyze_log(log_file)


def run(
    base_url: str,
    template_slug: str,
    log_file: str,
    timeout_sec: int,
    *,
    sync_docker_webhook_secret: bool,
    full_checkout: bool,
    headed: bool,
) -> int:
    base = base_url.rstrip("/")
    log_path = (PROJECT_ROOT / log_file).resolve()
    stripe_cli = _resolve_stripe_cli()
    stripe_api_key = _stripe_api_key()
    _health_ok(base)

    listener: subprocess.Popen[str] | None = None
    restored_env: str | None = None
    try:
        listener = _start_stripe_listen(
            stripe_cli,
            f"{base}/webhooks/stripe",
            log_path,
            api_key=stripe_api_key,
        )
        time.sleep(2.0)
        if listener.poll() is not None:
            log_tail = log_path.read_text(encoding="utf-8", errors="ignore")[-1200:] if log_path.exists() else ""
            print("SMOKE_FAIL: Stripe listener exited immediately.")
            if public.settings.stripe_secret_key.startswith("sk_live_"):
                print(
                    "hint=Live secret keys cannot be passed to `stripe listen`. "
                    "Run `stripe login` once, or use an sk_test_/rk_* key for local webhook smoke."
                )
            if log_tail.strip():
                print(f"listener_log_tail={log_tail.strip()}")
            return 1

        whsec = _wait_for_listen_secret(log_path, timeout_sec=30)
        print(f"Stripe listen whsec detected: {whsec[:12]}...")

        if sync_docker_webhook_secret:
            restored_env = _sync_env_webhook_secret(whsec)
            print("Syncing docker webhook secret and restarting stack...")
            _restart_docker()

        if full_checkout:
            print(f"Opening checkout flow for /purchase/{template_slug} ...")
            if headed:
                _complete_checkout_with_playwright(base, template_slug, headed=True)
            else:
                _open_manual_checkout(base, template_slug)
        else:
            print("Triggering checkout.session.completed via Stripe CLI...")
            _trigger_checkout_completed(stripe_cli, api_key=stripe_api_key)
            time.sleep(3.0)

        print(f"Waiting up to {timeout_sec}s for webhook delivery evidence...")
        passed, summary = _wait_for_log_evidence(log_path, timeout_sec)
        print("== Delivery Summary ==")
        print(f"checkout.session.completed seen: {summary['completed']}")
        print(f"Webhook path seen: {summary['webhook_path']}")
        print(f"Success indicators seen: {summary['success']}")
        print(f"Failure indicators seen: {summary['failure']}")

        if passed:
            print("STRIPE_CLI_WEBHOOK_SMOKE_PASS")
            return 0
        if summary["failure"]:
            print("STRIPE_CLI_WEBHOOK_SMOKE_FAIL: failure indicators in stripe listen log")
            if not sync_docker_webhook_secret:
                print(
                    "hint=retry with --sync-docker-webhook-secret so docker uses the listen whsec "
                    "(Stripe CLI signs forwarded events with its own secret)."
                )
            return 2
        print("STRIPE_CLI_WEBHOOK_SMOKE_FAIL: not enough webhook evidence yet")
        return 3
    except Exception as exc:  # noqa: BLE001
        print(f"STRIPE_CLI_WEBHOOK_SMOKE_FAIL: {exc}")
        return 1
    finally:
        if listener and listener.poll() is None:
            listener.terminate()
            try:
                listener.wait(timeout=5)
            except subprocess.TimeoutExpired:
                listener.kill()
        if sync_docker_webhook_secret and restored_env is not None:
            _restore_env_webhook_secret(restored_env)
            try:
                _restart_docker()
            except Exception:
                pass


def main() -> int:
    args = _build_parser().parse_args()
    return run(
        base_url=args.base_url,
        template_slug=args.template_slug,
        log_file=args.log_file,
        timeout_sec=args.timeout_sec,
        sync_docker_webhook_secret=args.sync_docker_webhook_secret,
        full_checkout=args.full_checkout,
        headed=args.headed,
    )


if __name__ == "__main__":
    sys.exit(main())
