"""Cleanup script to remove hosting service data from existing databases."""

from __future__ import annotations

from sqlalchemy import delete, select, update

from app.core.database import SessionLocal
from app.models import ServiceAddon, Template


def cleanup() -> tuple[int, int]:
    db = SessionLocal()
    try:
        hosting_templates = db.scalars(
            select(Template).where(Template.hosting_available.is_(True))
        ).all()
        template_updates = len(hosting_templates)
        if template_updates:
            db.execute(update(Template).values(hosting_available=False))

        addon_delete_result = db.execute(
            delete(ServiceAddon).where(ServiceAddon.slug == "managed-hosting")
        )
        deleted_addons = addon_delete_result.rowcount or 0

        db.commit()
        return template_updates, deleted_addons
    finally:
        db.close()


if __name__ == "__main__":
    updated_templates, removed_addons = cleanup()
    print(
        "Hosting cleanup complete: "
        f"{updated_templates} templates updated, "
        f"{removed_addons} hosting add-on rows removed."
    )
