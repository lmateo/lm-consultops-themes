"""Maps Mateo marketplace templates to Crafto HTML demo files."""

from __future__ import annotations

from dataclasses import dataclass

DEMO_PAGES = frozenset({"home", "about", "services", "contact"})

CRAFTO_STATIC_PREFIX = "/crafto"


@dataclass(frozen=True)
class CraftoDemoMapping:
    slug: str
    crafto_demo_key: str
    crafto_demo_label: str
    pages: dict[str, str]
    layout_key: str

    def page_path(self, page: str) -> str:
        normalized = page if page in DEMO_PAGES else "home"
        filename = self.pages.get(normalized) or self.pages["home"]
        return f"{CRAFTO_STATIC_PREFIX}/{filename}"

    def page_url(self, page: str) -> str:
        return self.page_path(page)


# slug -> Crafto demo association (home + inner pages aligned to marketplace IA)
CRAFTO_TEMPLATE_DEMOS: dict[str, CraftoDemoMapping] = {
    "greenfield-farm": CraftoDemoMapping(
        slug="greenfield-farm",
        crafto_demo_key="green-energy",
        crafto_demo_label="Green Energy",
        layout_key="agrarian",
        pages={
            "home": "demo-green-energy.html",
            "about": "demo-green-energy-about.html",
            "services": "demo-green-energy-services.html",
            "contact": "demo-green-energy-contact.html",
        },
    ),
    "tradepro-local": CraftoDemoMapping(
        slug="tradepro-local",
        crafto_demo_key="business",
        crafto_demo_label="Business",
        layout_key="contractor",
        pages={
            "home": "demo-business.html",
            "about": "demo-business-about.html",
            "services": "demo-business-services.html",
            "contact": "demo-business-contact.html",
        },
    ),
    "pizza-local-eats": CraftoDemoMapping(
        slug="pizza-local-eats",
        crafto_demo_key="pizza-parlor",
        crafto_demo_label="Pizza Parlor",
        layout_key="restaurant",
        pages={
            "home": "demo-pizza-parlor.html",
            "about": "demo-pizza-parlor-about.html",
            "services": "demo-pizza-parlor-menu.html",
            "contact": "demo-pizza-parlor-contact.html",
        },
    ),
    "cloudcare-it": CraftoDemoMapping(
        slug="cloudcare-it",
        crafto_demo_key="it-business",
        crafto_demo_label="IT Business",
        layout_key="saas-tech",
        pages={
            "home": "demo-it-business.html",
            "about": "demo-it-business-about.html",
            "services": "demo-it-business-services.html",
            "contact": "demo-it-business-contact.html",
        },
    ),
    "mountain-lodge": CraftoDemoMapping(
        slug="mountain-lodge",
        crafto_demo_key="hotel-and-resort",
        crafto_demo_label="Hotel & Resort",
        layout_key="lodge",
        pages={
            "home": "demo-hotel-and-resort.html",
            "about": "demo-hotel-and-resort-about-us.html",
            "services": "demo-hotel-and-resort-rooms.html",
            "contact": "demo-hotel-and-resort-contact.html",
        },
    ),
    "petcare-studio": CraftoDemoMapping(
        slug="petcare-studio",
        crafto_demo_key="medical",
        crafto_demo_label="Medical",
        layout_key="petcare",
        pages={
            "home": "demo-medical.html",
            "about": "demo-medical-about.html",
            "services": "demo-medical-treatments.html",
            "contact": "demo-medical-contact.html",
        },
    ),
    "community-impact": CraftoDemoMapping(
        slug="community-impact",
        crafto_demo_key="charity",
        crafto_demo_label="Charity",
        layout_key="nonprofit",
        pages={
            "home": "demo-charity.html",
            "about": "demo-charity-about.html",
            "services": "demo-charity-causes.html",
            "contact": "demo-charity-contact.html",
        },
    ),
    "homebase-realty": CraftoDemoMapping(
        slug="homebase-realty",
        crafto_demo_key="real-estate",
        crafto_demo_label="Real Estate",
        layout_key="realty",
        pages={
            "home": "demo-real-estate.html",
            "about": "demo-real-estate-about.html",
            "services": "demo-real-estate-sell.html",
            "contact": "demo-real-estate-contact.html",
        },
    ),
    "autoworks-garage": CraftoDemoMapping(
        slug="autoworks-garage",
        crafto_demo_key="logistics",
        crafto_demo_label="Logistics",
        layout_key="garage",
        pages={
            "home": "demo-logistics.html",
            "about": "demo-logistics-about-us.html",
            "services": "demo-logistics-our-services.html",
            "contact": "demo-logistics-contact-us.html",
        },
    ),
    "wellness-local": CraftoDemoMapping(
        slug="wellness-local",
        crafto_demo_key="spa-salon",
        crafto_demo_label="Spa Salon",
        layout_key="wellness",
        pages={
            "home": "demo-spa-salon.html",
            "about": "demo-spa-salon-about.html",
            "services": "demo-spa-salon-treatments.html",
            "contact": "demo-spa-salon-contact.html",
        },
    ),
}


def get_crafto_demo(slug: str) -> CraftoDemoMapping | None:
    return CRAFTO_TEMPLATE_DEMOS.get(slug)


def get_crafto_demo_or_default(slug: str) -> CraftoDemoMapping:
    return CRAFTO_TEMPLATE_DEMOS.get(slug) or CRAFTO_TEMPLATE_DEMOS["greenfield-farm"]


def list_crafto_demo_catalog() -> list[dict[str, str]]:
    return [
        {
            "slug": mapping.slug,
            "crafto_demo_key": mapping.crafto_demo_key,
            "crafto_demo_label": mapping.crafto_demo_label,
            "home_file": mapping.pages["home"],
        }
        for mapping in CRAFTO_TEMPLATE_DEMOS.values()
    ]
