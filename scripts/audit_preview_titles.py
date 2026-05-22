"""Audit wrapped preview page titles for required Mateo value."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS

EXPECTED_TITLE = "Mateo Consulting Team - The Multipurpose HTML5 Template"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

client = TestClient(app)


def run() -> str:
    total_pages = 0
    mismatches: list[tuple[str, str, str]] = []
    for slug in sorted(CRAFTO_TEMPLATE_DEMOS.keys()):
        for page in ("home", "about", "services", "contact"):
            total_pages += 1
            response = client.get(f"/preview/{slug}/{page}")
            if response.status_code != 200:
                mismatches.append((slug, page, f"non-200 response: {response.status_code}"))
                continue
            match = TITLE_RE.search(response.text)
            if not match:
                mismatches.append((slug, page, "missing <title>"))
                continue
            title = " ".join(match.group(1).split())
            if title != EXPECTED_TITLE:
                mismatches.append((slug, page, title))

    lines = [
        "PREVIEW TITLE AUDIT",
        f"pages checked: {total_pages}",
        f"mismatches: {len(mismatches)}",
        f"expected: {EXPECTED_TITLE}",
    ]
    if mismatches:
        lines.append("\nMISMATCHES")
        lines.extend(" | ".join(item) for item in mismatches)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(run(), end="")
