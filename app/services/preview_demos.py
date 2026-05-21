"""Per-template live preview demo configuration and layout routing."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Template

DEMO_PAGES = frozenset({"home", "about", "services", "contact"})

# slug -> layout template key (under app/templates/demos/layouts/)
SLUG_LAYOUT_MAP: dict[str, str] = {
    "greenfield-farm": "agrarian",
    "tradepro-local": "contractor",
    "pizza-local-eats": "restaurant",
    "cloudcare-it": "saas-tech",
    "mountain-lodge": "lodge",
    "petcare-studio": "petcare",
    "community-impact": "nonprofit",
    "homebase-realty": "realty",
    "autoworks-garage": "garage",
    "wellness-local": "wellness",
}

DEFAULT_LAYOUT = "agrarian"


@dataclass(frozen=True)
class DemoNavItem:
    label: str
    page: str


@dataclass(frozen=True)
class DemoPageContent:
    eyebrow: str
    title: str
    lead: str
    highlights: tuple[str, ...]


@dataclass(frozen=True)
class PreviewDemoContext:
    layout: str
    page: str
    nav_items: tuple[DemoNavItem, ...]
    home: DemoPageContent
    about: DemoPageContent
    services: DemoPageContent
    contact: DemoPageContent
    service_cards: tuple[dict[str, str], ...]
    stats: tuple[dict[str, str], ...]
    cta_label: str
    cta_secondary: str


def _cards_for_industry(template: Template) -> tuple[dict[str, str], ...]:
    industry = template.industry.name.lower()
    category = template.category.name.lower()
    feature_labels = [f.label for f in template.features[:3]]
    defaults = [
        {"title": "Conversion-first Homepage", "body": "Hero, proof, and action blocks tuned for local buyers."},
        {"title": "Service Detail Pages", "body": "Clear offers, outcomes, and trust signals for every offer."},
        {"title": "Mobile-first Performance", "body": "Responsive sections that stay fast on every device."},
    ]
    if feature_labels:
        return tuple(
            {
                "title": label,
                "body": f"Built into {template.title} for modern {industry} websites.",
            }
            for label in feature_labels
        ) + tuple(defaults[: max(0, 3 - len(feature_labels))])
    return tuple(defaults)


def _stats_for_template(template: Template) -> tuple[dict[str, str], ...]:
    return (
        {"value": template.version, "label": "Theme version"},
        {"value": template.last_updated.strftime("%b %Y"), "label": "Last updated"},
        {"value": "Pre-launch", "label": "Availability"},
    )


def _content_pack(template: Template) -> dict[str, DemoPageContent]:
    title = template.title
    industry = template.industry.name
    slug_content: dict[str, dict[str, DemoPageContent]] = {
        "greenfield-farm": {
            "home": DemoPageContent(
                "Agritourism & Orchard Experiences",
                f"Grow visits with {title}",
                template.description,
                ("Seasonal u-pick calendar", "Farm stand ecommerce-ready blocks", "Event and tour booking sections"),
            ),
            "about": DemoPageContent(
                "Our Land, Our Story",
                "Family-run since 1986",
                "Share heritage, sustainable practices, and the people behind your harvest.",
                ("Timeline storytelling", "Team and steward bios", "Press and partner logos"),
            ),
            "services": DemoPageContent(
                "On-farm Experiences",
                "Pick, stay, and celebrate",
                "Package tours, wholesale partnerships, and seasonal workshops in one layout.",
                ("Orchard tours", "Wedding meadow rentals", "CSA membership funnel"),
            ),
            "contact": DemoPageContent(
                "Plan Your Visit",
                "Directions, hours, and group bookings",
                "Map embed area, seasonal hours table, and group inquiry form.",
                ("Interactive map block", "Group booking form", "Newsletter for harvest alerts"),
            ),
        },
        "tradepro-local": {
            "home": DemoPageContent(
                "Licensed Local Trades",
                f"{title} gets jobs booked faster",
                template.description,
                ("24/7 emergency strip", "Service area map", "Financing and warranty badges"),
            ),
            "about": DemoPageContent(
                "Built on Craftsmanship",
                "Licensed, insured, and local",
                "Crew credentials, safety certifications, and community involvement.",
                ("Owner message", "Certification grid", "Community project gallery"),
            ),
            "services": DemoPageContent(
                "Core Trades",
                "HVAC, electrical, roofing, and more",
                "Package each trade with pricing cues, timelines, and FAQ snippets.",
                ("Service tier cards", "Maintenance plans", "Seasonal promo banners"),
            ),
            "contact": DemoPageContent(
                "Book a Service Call",
                "Same-week scheduling",
                "Job-type selector, ZIP validator UI, and callback promise.",
                ("Estimator CTA", "Live chat placeholder", "Service guarantee panel"),
            ),
        },
        "pizza-local-eats": {
            "home": DemoPageContent(
                "Neighborhood Favorite",
                f"Welcome hungry guests with {title}",
                template.description,
                ("Tonight's specials carousel", "Order online CTA", "Reviews marquee"),
            ),
            "about": DemoPageContent(
                "Recipes & Roots",
                "Wood-fired since day one",
                "Chef story, sourcing partners, and community nights.",
                ("Kitchen timeline", "Ingredient partners", "Press quotes"),
            ),
            "services": DemoPageContent(
                "Menu Highlights",
                "Dine-in, takeout, and catering",
                "Category tabs for pies, pasta, desserts, and beverages.",
                ("Dietary filters UI", "Catering packages", "Gift card promo"),
            ),
            "contact": DemoPageContent(
                "Reserve & Order",
                "Pick a time, pick a pie",
                "Hours strip, parking note, and reservation form.",
                ("Open hours ticker", "Party size selector", "Delivery zone map"),
            ),
        },
        "cloudcare-it": {
            "home": DemoPageContent(
                "Managed IT & Security",
                f"{title} for modern MSP teams",
                template.description,
                ("SOC-ready trust badges", "Uptime metrics band", "Client logo wall"),
            ),
            "about": DemoPageContent(
                "Engineers First",
                "Cloud-native delivery",
                "Leadership bios, certifications, and delivery methodology.",
                ("Microsoft & AWS badges", "Case study metrics", "Partner ecosystem"),
            ),
            "services": DemoPageContent(
                "Service Catalog",
                "Cloud, security, and support",
                "Tiered packages with SLA callouts and comparison matrix.",
                ("Managed SOC", "Microsoft 365 rollout", "Disaster recovery playbooks"),
            ),
            "contact": DemoPageContent(
                "Book an Assessment",
                "Free infrastructure review",
                "Security questionnaire teaser and calendar embed area.",
                ("ROI calculator block", "Compliance checklist", "Executive briefing form"),
            ),
        },
        "mountain-lodge": {
            "home": DemoPageContent(
                "Alpine Retreat",
                f"Escape to {title}",
                template.description,
                ("Room carousel", "Seasonal activity grid", "Guest review slider"),
            ),
            "about": DemoPageContent(
                "At the Timberline",
                "Hospitality with altitude",
                "Lodge history, sustainability pledge, and concierge team.",
                ("Altitude facts", "Local guide partners", "Award features"),
            ),
            "services": DemoPageContent(
                "Stay & Experience",
                "Cabins, suites, and adventures",
                "Package ski passes, spa add-ons, and dining reservations.",
                ("Room comparison", "Activity booking", "Transportation options"),
            ),
            "contact": DemoPageContent(
                "Plan Your Stay",
                "Check-in made effortless",
                "Availability search UI, travel tips, and group retreat form.",
                ("Weather widget area", "Pet policy callout", "Wedding inquiry funnel"),
            ),
        },
        "petcare-studio": {
            "home": DemoPageContent(
                "Compassionate Pet Care",
                f"{title} keeps tails wagging",
                template.description,
                ("Online booking hero", "Vet team spotlight", "Emergency hotline bar"),
            ),
            "about": DemoPageContent(
                "Care You Can Trust",
                "Fear-free certified team",
                "Clinic story, accreditations, and community outreach.",
                ("Staff credentials", "Facility tour gallery", "Community events"),
            ),
            "services": DemoPageContent(
                "Clinic Services",
                "Wellness to specialty care",
                "Wellness plans, grooming, boarding, and dental packages.",
                ("Puppy plans", "Senior care program", "Telehealth option"),
            ),
            "contact": DemoPageContent(
                "Book an Appointment",
                "New patients welcome",
                "Pet profile form, insurance info, and parking map.",
                ("New client form", "Insurance partners", "After-hours instructions"),
            ),
        },
        "community-impact": {
            "home": DemoPageContent(
                "People-Powered Change",
                f"Amplify mission with {title}",
                template.description,
                ("Impact counter band", "Volunteer CTA", "Upcoming events list"),
            ),
            "about": DemoPageContent(
                "Our Mission",
                "Grassroots to regional",
                "Origin story, board highlights, and annual report teaser.",
                ("Theory of change", "Financial transparency", "Partner coalitions"),
            ),
            "services": DemoPageContent(
                "Programs",
                "Education, outreach, relief",
                "Program cards with outcomes, beneficiaries, and donation links.",
                ("Youth mentorship", "Food security drives", "Advocacy toolkit"),
            ),
            "contact": DemoPageContent(
                "Get Involved",
                "Donate, volunteer, partner",
                "Donation tiers, volunteer signup, and corporate sponsorship form.",
                ("Monthly giving", "In-kind donations", "Media contact"),
            ),
        },
        "homebase-realty": {
            "home": DemoPageContent(
                "Local Listings",
                f"Showcase properties with {title}",
                template.description,
                ("Listing search hero", "Featured properties grid", "Agent roster strip"),
            ),
            "about": DemoPageContent(
                "Neighborhood Experts",
                "Cabins to commercial",
                "Brokerage story, market reports, and client success metrics.",
                ("Market snapshots", "Agent achievements", "Community involvement"),
            ),
            "services": DemoPageContent(
                "Buyer & Seller Services",
                "Full-service representation",
                "Buyer guides, seller prep checklists, and mortgage partners.",
                ("Home valuation CTA", "Staging partners", "Relocation services"),
            ),
            "contact": DemoPageContent(
                "Schedule a Showing",
                "Talk with a local agent",
                "Property interest form, mortgage pre-qual link, and office map.",
                ("Mortgage partners", "Open house calendar", "Seller consultation"),
            ),
        },
        "autoworks-garage": {
            "home": DemoPageContent(
                "Precision Auto Care",
                f"{title} drives trust",
                template.description,
                ("Service bay status", "Fleet program CTA", "Certified technician row"),
            ),
            "about": DemoPageContent(
                "Garage Built on Integrity",
                "ASE-certified crew",
                "Shop history, equipment, and warranty policies.",
                ("Shop tour", "Certifications", "Community sponsorships"),
            ),
            "services": DemoPageContent(
                "Service Menu",
                "Maintenance to performance",
                "Transparent pricing table, inspection packages, and fleet plans.",
                ("Oil change tiers", "Brake & tire packages", "Detailing add-ons"),
            ),
            "contact": DemoPageContent(
                "Schedule Service",
                "Drop-off or wait lounge",
                "VIN-ready form, shuttle service note, and text updates opt-in.",
                ("Fleet intake", "Warranty claims", "Roadside partner info"),
            ),
        },
        "wellness-local": {
            "home": DemoPageContent(
                "Whole-Person Wellness",
                f"{title} welcomes new patients",
                template.description,
                ("Calm hero with booking", "Care pathway cards", "Insurance accepted list"),
            ),
            "about": DemoPageContent(
                "Care Philosophy",
                "Integrated mind and body",
                "Clinic values, practitioner bios, and holistic approach.",
                ("Treatment philosophy", "Credentials wall", "Patient stories"),
            ),
            "services": DemoPageContent(
                "Programs & Therapies",
                "Primary to specialty care",
                "Therapy types, group classes, and corporate wellness.",
                ("Physical therapy", "Nutrition coaching", "Corporate wellness"),
            ),
            "contact": DemoPageContent(
                "New Patient Intake",
                "Same-week appointments",
                "HIPAA-friendly form layout, telehealth option, and parking info.",
                ("Insurance verification", "Telehealth toggle", "Accessibility details"),
            ),
        },
    }
    pack = slug_content.get(
        template.slug,
        {
            "home": DemoPageContent(
                f"{industry} Website",
                title,
                template.description,
                ("Modern homepage", "Service pages", "Lead capture forms"),
            ),
            "about": DemoPageContent("About", f"About {title}", f"Learn about {title}.", ("Team", "Mission", "Values")),
            "services": DemoPageContent("Services", "What we offer", "Core offers and packages.", ("Package A", "Package B", "Package C")),
            "contact": DemoPageContent("Contact", "Get in touch", "Reach our team.", ("Form", "Map", "Hours")),
        },
    )
    return pack


def get_layout_key(slug: str) -> str:
    return SLUG_LAYOUT_MAP.get(slug, DEFAULT_LAYOUT)


def get_preview_demo(template: Template, page: str = "home") -> PreviewDemoContext:
    normalized_page = page if page in DEMO_PAGES else "home"
    content_pack = _content_pack(template)
    return PreviewDemoContext(
        layout=get_layout_key(template.slug),
        page=normalized_page,
        nav_items=(
            DemoNavItem("Home", "home"),
            DemoNavItem("About", "about"),
            DemoNavItem("Services", "services"),
            DemoNavItem("Contact", "contact"),
        ),
        home=content_pack["home"],
        about=content_pack["about"],
        services=content_pack["services"],
        contact=content_pack["contact"],
        service_cards=_cards_for_industry(template),
        stats=_stats_for_template(template),
        cta_label="Get Started",
        cta_secondary="View Services",
    )


def get_page_content(demo: PreviewDemoContext) -> DemoPageContent:
    return getattr(demo, demo.page)


def list_template_search_hints() -> list[dict[str, str]]:
    """Homepage template search datalist: title and slug per demo template."""
    return [
        {"title": slug.replace("-", " ").title(), "slug": slug}
        for slug in sorted(SLUG_LAYOUT_MAP.keys())
    ]
