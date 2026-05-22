"""Audit wrapped previews for /crafto/# or bare # links."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.crafto_demos import CRAFTO_TEMPLATE_DEMOS

client = TestClient(app)
HREF_RE = re.compile(r"""href=(["'])([^"']*)\1""", re.IGNORECASE)


def run() -> str:
    rows: list[tuple[str, str, str]] = []
    total_pages = 0
    for slug in sorted(CRAFTO_TEMPLATE_DEMOS.keys()):
        for page in ("home", "about", "services", "contact"):
            total_pages += 1
            response = client.get(f"/preview/{slug}/{page}")
            if response.status_code != 200:
                rows.append((slug, page, f"non-200 response: {response.status_code}"))
                continue
            html = response.text
            for _, href in HREF_RE.findall(html):
                value = href.strip()
                if value in {"/crafto/#", "#"}:
                    rows.append((slug, page, value))

    lines = [
        "CRAFTO HASH LINK AUDIT",
        f"pages checked: {total_pages}",
        f"matches: {len(rows)}",
    ]
    if rows:
        lines.append("\nMATCHES")
        lines.extend(" | ".join(item) for item in rows)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(run(), end="")
