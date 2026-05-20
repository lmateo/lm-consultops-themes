"""Live HTTP smoke test for contact form (run against local uvicorn or Docker)."""

import re
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"


def main() -> int:
    failures = 0
    with httpx.Client(base_url=BASE, timeout=15.0) as client:
        page = client.get("/contact")
        print(f"GET /contact: {page.status_code}")
        if page.status_code != 200:
            failures += 1
        match_a = re.search(r'name="captcha_a"\s+value="(\d+)"', page.text)
        match_b = re.search(r'name="captcha_b"\s+value="(\d+)"', page.text)
        if not match_a or not match_b:
            print("  FAIL: captcha hidden fields missing")
            failures += 1
            return failures
        captcha_a, captcha_b = int(match_a.group(1)), int(match_b.group(1))
        print(f"  captcha: {captcha_a} + {captcha_b}")
        if "/api/contact" not in page.text:
            print("  FAIL: form does not post to /api/contact")
            failures += 1

        wrong = client.post(
            "/api/contact",
            data={
                "name": "Smoke",
                "email": "smoke@test.com",
                "message": "hi",
                "captcha_a": captcha_a,
                "captcha_b": captcha_b,
                "captcha_answer": "0",
            },
        )
        print(f"POST wrong captcha: {wrong.status_code} — {wrong.json().get('detail', '')}")
        if wrong.status_code != 400:
            failures += 1

        honeypot = client.post(
            "/api/contact",
            data={
                "name": "Smoke",
                "email": "smoke@test.com",
                "message": "hi",
                "website": "http://spam.test",
                "captcha_a": captcha_a,
                "captcha_b": captcha_b,
                "captcha_answer": str(captcha_a + captcha_b),
            },
        )
        print(f"POST honeypot: {honeypot.status_code} — {honeypot.json().get('detail', '')}")
        if honeypot.status_code != 400:
            failures += 1

        valid = client.post(
            "/api/contact",
            data={
                "name": "Smoke",
                "email": "smoke@test.com",
                "message": "Live smoke test",
                "captcha_a": captcha_a,
                "captcha_b": captcha_b,
                "captcha_answer": str(captcha_a + captcha_b),
            },
        )
        detail = valid.json().get("detail") or valid.json().get("message", "")
        print(f"POST valid payload: {valid.status_code} — {detail}")
        if valid.status_code not in (201, 503):
            print(f"  FAIL: expected 201 (configured) or 503 (unconfigured), got {valid.status_code}")
            failures += 1

    print("PASS" if failures == 0 else f"FAIL ({failures} checks)")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
