"""Rich copy and structured blocks for theme demo inner pages (about, services, contact)."""

from __future__ import annotations

from typing import Any

# slug -> rich content dict used by demo page partials
RICH_DEMO_CONTENT: dict[str, dict[str, Any]] = {
    "greenfield-farm": {
        "about": {
            "story": [
                "GreenField Farm began as a twenty-acre apple orchard in 1986. Today we welcome families for u-pick weekends, farm-to-table dinners, and seasonal workshops led by our field team.",
                "We practice low-till soil management, pollinator-friendly borders, and partner with three regional food banks during peak harvest.",
            ],
            "timeline": [
                {"year": "1986", "title": "Orchard founded", "body": "The Ashford family plants the first Honeycrisp block."},
                {"year": "2004", "title": "Farm stand opens", "body": "Weekend market launches with cider, pies, and local honey."},
                {"year": "2018", "title": "Agritourism expands", "body": "Hayrides, wedding meadow, and CSA program go live."},
            ],
            "team": [
                {"name": "Mara Ashford", "role": "Farm Director", "bio": "Third-generation grower focused on sustainable orchard practices."},
                {"name": "Jon Ellis", "role": "Events Lead", "bio": "Coordinates tours, weddings, and school field days."},
                {"name": "Priya Nanda", "role": "Market Manager", "bio": "Runs the farm stand, CSA boxes, and wholesale accounts."},
            ],
            "principles": ["Certified organic blocks", "Zero-waste kitchen partnerships", "Accessible paths on all tour routes"],
        },
        "services": {
            "intro": "From spring blossom tours to autumn u-pick, every experience includes a guided intro and tasting flight.",
            "offerings": [
                {"title": "Weekend U-Pick", "price": "$18 / peck", "duration": "2 hours", "description": "Includes orchard map, baskets, and cider sample.", "bullets": ["Kids activity sheet", "Rain reschedule policy", "Peak season slots"]},
                {"title": "Farm Dinner Series", "price": "$85 / guest", "duration": "Evening", "description": "Chef-led five-course meal on the meadow terrace.", "bullets": ["Local wine pairings", "Dietary accommodations", "20 guest minimum"]},
                {"title": "CSA Harvest Box", "price": "$42 / week", "duration": "16 weeks", "description": "Seasonal produce, eggs, and pantry surprises.", "bullets": ["Pickup or delivery", "Swap items online", "Recipe cards included"]},
                {"title": "Private Orchard Tour", "price": "$240 / group", "duration": "90 min", "description": "Up to 12 guests with bee yard and cold-storage walkthrough.", "bullets": ["School discounts", "ASL interpreter on request", "Photo-friendly stops"]},
            ],
        },
        "contact": {
            "address": "2840 Orchard Lane, Millbrook, VT 05753",
            "phone": "(802) 555-0142",
            "email": "hello@greenfieldfarm.example",
            "hours": [
                {"days": "Farm stand", "time": "Fri–Sun 9am–5pm"},
                {"days": "Office", "time": "Mon–Fri 8am–4pm"},
                {"days": "Tours", "time": "By reservation"},
            ],
            "form_note": "Group visits need 72-hour notice. Tell us your party size and preferred date.",
            "faqs": [
                {"q": "Are dogs allowed?", "a": "Leashed dogs are welcome on paths; not in the farm stand."},
                {"q": "Do you host weddings?", "a": "Yes—meadow packages include tables, lighting, and coordinator support."},
                {"q": "Is the orchard wheelchair accessible?", "a": "Main routes are graded gravel with rest stops; contact us for mobility planning."},
            ],
        },
        "testimonials": [
            {"quote": "Our school field trip was organized, educational, and the kids loved the tasting flight.", "author": "L. Chen", "role": "4th Grade Teacher"},
            {"quote": "Best CSA we've joined—every box feels curated for the week ahead.", "author": "Marcus Reid", "role": "CSA Member"},
        ],
    },
    "tradepro-local": {
        "about": {
            "story": [
                "TradePro Local started in a two-truck garage and grew into a full-service trades company serving nine counties. We answer emergency calls in under 90 minutes and stand behind every install with a two-year workmanship warranty.",
                "Our crews cross-train on safety, code updates, and customer communication so your project stays on schedule and on budget.",
            ],
            "timeline": [
                {"year": "2009", "title": "Founded", "body": "HVAC and electrical services launch with three technicians."},
                {"year": "2016", "title": "Roofing division", "body": "Storm response team and commercial flat-roof unit added."},
                {"year": "2023", "title": "Fleet electrification", "body": "Hybrid service vans and paperless job tracking roll out."},
            ],
            "team": [
                {"name": "Elena Voss", "role": "Operations Director", "bio": "Licensed master electrician; oversees dispatch and QA."},
                {"name": "Chris Ortega", "role": "HVAC Lead", "bio": "NATE-certified with 15 years in commercial retrofit."},
                {"name": "Samira Holt", "role": "Customer Success", "bio": "Coordinates estimates, financing, and warranty claims."},
            ],
            "principles": ["Licensed & insured in all service counties", "Upfront pricing before work begins", "Background-checked field technicians"],
        },
        "services": {
            "intro": "Transparent scopes, photo-documented progress, and final walkthrough on every job.",
            "offerings": [
                {"title": "HVAC Tune-Up", "price": "From $129", "duration": "Same day", "description": "Seasonal maintenance for furnaces and heat pumps.", "bullets": ["Filter replacement", "Efficiency report", "Priority scheduling for members"]},
                {"title": "Panel Upgrade", "price": "From $1,850", "duration": "1–2 days", "description": "200-amp service upgrades with permit handling.", "bullets": ["Load calculation", "Generator interlock option", "Code compliance certificate"]},
                {"title": "Roof Replacement", "price": "Custom quote", "duration": "2–5 days", "description": "Architectural shingle and metal systems.", "bullets": ["Drone inspection", "Storm damage documentation", "Financing available"]},
                {"title": "Maintenance Plan", "price": "$29 / month", "duration": "Annual", "description": "Covers two seasonal visits and 10% off repairs.", "bullets": ["No trip fees", "Transferable to new homeowners", "24/7 phone support"]},
            ],
        },
        "contact": {
            "address": "1180 Industrial Park Dr, Dayton, OH 45414",
            "phone": "(937) 555-0198",
            "email": "dispatch@tradeprolocal.example",
            "hours": [
                {"days": "Dispatch", "time": "24 / 7"},
                {"days": "Showroom", "time": "Mon–Fri 7am–6pm"},
                {"days": "Estimates", "time": "Sat 8am–12pm"},
            ],
            "form_note": "For emergencies select 'Urgent'—we prioritize active leaks, no-heat, and safety hazards.",
            "faqs": [
                {"q": "Do you offer financing?", "a": "Yes—0% promotional plans on qualifying installs over $2,500."},
                {"q": "What areas do you serve?", "a": "Nine counties in southwest Ohio; enter your ZIP on the form to confirm."},
                {"q": "Are estimates free?", "a": "In-home estimates are complimentary for projects over $500."},
            ],
        },
        "testimonials": [
            {"quote": "They replaced our panel and coordinated the city inspection without us chasing paperwork.", "author": "D. Whitaker", "role": "Homeowner"},
            {"quote": "Our restaurant HVAC was back online before the lunch rush—true professionals.", "author": "Ana Ruiz", "role": "Restaurant Owner"},
        ],
    },
    "pizza-local-eats": {
        "about": {
            "story": [
                "Pizza & Local Eats fired up our first wood-burning oven in 2012. Dough proofs for 48 hours, sauce simmers from San Marzano tomatoes, and we source mozzarella from a creamery twelve miles up the road.",
                "Community nights, local brewery pairings, and a kids-make-your-own-pie hour keep the dining room full without losing the neighborhood feel.",
            ],
            "timeline": [
                {"year": "2012", "title": "Doors open", "body": "12-seat counter and takeout window launch on Main Street."},
                {"year": "2017", "title": "Second oven", "body": "Expanded dining room and weekend brunch menu."},
                {"year": "2024", "title": "Catering hub", "body": "Off-site events and corporate lunch program."},
            ],
            "team": [
                {"name": "Tony Marchetti", "role": "Head Chef", "bio": "Naples-trained pizzaiolo; develops seasonal specials."},
                {"name": "Jules Park", "role": "Front of House", "bio": "Runs reservations, events, and guest experience."},
                {"name": "Rico Alvarez", "role": "Beverage Director", "bio": "Curates local drafts, natural wine, and zero-proof pairings."},
            ],
            "principles": ["Dough made daily in-house", "Gluten-friendly crust on request", "Compostable takeout packaging"],
        },
        "services": {
            "intro": "Dine in, grab takeout, or book catering—every order starts in our open kitchen.",
            "offerings": [
                {"title": "Signature Pies", "price": "$16–$24", "duration": "15–20 min", "description": "Margherita, spicy soppressata, roasted veg, and white garlic.", "bullets": ["12\" or 16\"", "Half-and-half toppings", "Vegan cheese option"]},
                {"title": "Pasta & Salads", "price": "$14–$19", "duration": "12 min", "description": "Fresh-cut pasta, grain bowls, and seasonal greens.", "bullets": ["Add protein", "Family portions", "Allergy flags on tickets"]},
                {"title": "Catering Trays", "price": "From $120", "duration": "48 hr notice", "description": "Office lunches, birthdays, and brewery taproom pop-ups.", "bullets": ["Hot holding equipment", "Staff on request", "Custom menu PDF"]},
                {"title": "Private Dining", "price": "$65 / guest", "duration": "2 hours", "description": "Chef's table for up to 18 with wine pairings.", "bullets": ["Deposit holds date", "Dietary cards collected", "Amuse-bouche flight"]},
            ],
        },
        "contact": {
            "address": "402 Main Street, Asheville, NC 28801",
            "phone": "(828) 555-0173",
            "email": "reservations@pizzalocaleats.example",
            "hours": [
                {"days": "Kitchen", "time": "Tue–Thu 11am–9pm, Fri–Sat 11am–10pm"},
                {"days": "Brunch", "time": "Sun 10am–2pm"},
                {"days": "Closed", "time": "Monday"},
            ],
            "form_note": "Parties of 8+ please reserve. For catering include headcount and event date.",
            "faqs": [
                {"q": "Do you deliver?", "a": "Delivery within 4 miles via our partner; pickup is always available."},
                {"q": "Can I bring wine?", "a": "Corkage $15/bottle; we also offer a rotating local list."},
                {"q": "Is there parking?", "a": "Free lot behind the building; street parking after 6pm."},
            ],
        },
        "testimonials": [
            {"quote": "The 48-hour dough makes a difference—you can taste the patience.", "author": "Hannah Brooks", "role": "Regular Guest"},
            {"quote": "Catered our office launch—hot, on time, and the garlic knots disappeared first.", "author": "Devon Miles", "role": "Startup Founder"},
        ],
    },
    "cloudcare-it": {
        "about": {
            "story": [
                "CloudCare IT helps regional businesses migrate, secure, and support Microsoft 365 and Azure estates. Our engineers hold current Security+, Azure Administrator, and CISSP credentials.",
                "We publish quarterly benchmark reports for clients and maintain a 15-minute critical-incident response window on managed plans.",
            ],
            "timeline": [
                {"year": "2014", "title": "MSP founded", "body": "Break-fix support for professional services firms."},
                {"year": "2019", "title": "Security practice", "body": "SOC monitoring and MDR partnerships formalized."},
                {"year": "2025", "title": "AI governance", "body": "Copilot rollout playbooks and data classification kits."},
            ],
            "team": [
                {"name": "Jordan Pike", "role": "Principal Architect", "bio": "Designs hybrid cloud and zero-trust rollouts."},
                {"name": "Mei Tanaka", "role": "Security Lead", "bio": "Runs tabletop exercises and compliance roadmaps."},
                {"name": "Omar Diallo", "role": "Client Success", "bio": "Owns onboarding, QBRs, and executive reporting."},
            ],
            "principles": ["Documented runbooks for every client", "Transparent SLA dashboards", "No long-term lock-in contracts"],
        },
        "services": {
            "intro": "Pick a managed tier or bolt on projects—every plan includes onboarding and security baseline review.",
            "offerings": [
                {"title": "Managed Workplace", "price": "$89 / user", "duration": "Monthly", "description": "M365 admin, endpoint management, and helpdesk.", "bullets": ["8×5 or 24×7 desk", "Patch compliance", "License optimization"]},
                {"title": "Cloud Security", "price": "From $2,400 / mo", "duration": "Monthly", "description": "SIEM, MDR, and identity threat detection.", "bullets": ["Monthly posture report", "Incident runbooks", "Executive briefings"]},
                {"title": "Migration Sprint", "price": "Fixed scope", "duration": "4–8 weeks", "description": "Exchange to Exchange Online, file server to SharePoint.", "bullets": ["Cutover playbook", "Rollback plan", "User comms templates"]},
                {"title": "vCISO Advisory", "price": "Custom", "duration": "Quarterly", "description": "Policy, risk register, and board-ready metrics.", "bullets": ["Framework mapping", "Vendor review", "Insurance questionnaire support"]},
            ],
        },
        "contact": {
            "address": "900 Market Street, Suite 400, Portland, OR 97205",
            "phone": "(503) 555-0160",
            "email": "hello@cloudcareit.example",
            "hours": [
                {"days": "Helpdesk", "time": "24 / 7 for managed clients"},
                {"days": "Sales", "time": "Mon–Fri 8am–6pm PT"},
                {"days": "On-site", "time": "By appointment"},
            ],
            "form_note": "Request a free infrastructure assessment—include employee count and primary workloads.",
            "faqs": [
                {"q": "Do you support Google Workspace?", "a": "Yes—migration and coexistence projects are available."},
                {"q": "What is your average response time?", "a": "Critical: 15 minutes; standard: 1 business hour on managed plans."},
                {"q": "Can you work with our internal IT?", "a": "We offer co-managed models with shared ticketing and documentation."},
            ],
        },
        "testimonials": [
            {"quote": "CloudCare cut our ticket backlog by 60% in the first quarter.", "author": "VP Operations", "role": "Regional Law Firm"},
            {"quote": "Their migration sprint finished a week early with zero mail downtime.", "author": "IT Director", "role": "Manufacturing Co."},
        ],
    },
    "mountain-lodge": {
        "about": {
            "story": [
                "Mountain Lodge sits at 6,200 feet with views across the pine ridge. Built in 1972 and renovated in 2020, our 28 rooms blend timber warmth with quiet luxury—fireplaces, locally woven textiles, and sunrise-facing decks.",
                "We partner with alpine guides, spa therapists, and a farm-to-table kitchen team to craft stays that feel unhurried and rooted in place.",
            ],
            "timeline": [
                {"year": "1972", "title": "Lodge opens", "body": "Eight cabin rooms and a communal great room."},
                {"year": "2015", "title": "Spa wing", "body": "Hot stone therapy and cedar sauna added."},
                {"year": "2020", "title": "Full renovation", "body": "Energy-efficient heat, EV chargers, and accessible suites."},
            ],
            "team": [
                {"name": "Claire Whitmore", "role": "General Manager", "bio": "20 years in boutique hospitality across the Rockies."},
                {"name": "Ben Okonkwo", "role": "Head Concierge", "body": "Coordinates guides, transfers, and celebration dinners."},
                {"name": "Sofia Reyes", "role": "Executive Chef", "bio": "Seasonal menus from regional ranchers and foragers."},
            ],
            "principles": ["Leave-no-trace trail partnerships", "Carbon-neutral lodge operations", "Pet-friendly suites on request"],
        },
        "services": {
            "intro": "Rooms, packages, and on-mountain experiences—everything is coordinated through concierge.",
            "offerings": [
                {"title": "Ridge View Suite", "price": "From $289 / night", "duration": "Overnight", "description": "King bed, fireplace, soaking tub, and private deck.", "bullets": ["Late checkout Sundays", "In-room breakfast", "Gear drying closet"]},
                {"title": "Adventure Package", "price": "$420 / guest", "duration": "2 nights", "description": "Guided hike, packed lunches, and aprés spa credit.", "bullets": ["Beginner or advanced routes", "Poles and layers provided", "Weather backup plan"]},
                {"title": "Spa Half-Day", "price": "$195", "duration": "4 hours", "description": "Massage, cedar sauna, and herbal tea lounge.", "bullets": ["Couples room available", "CBD add-on", "Robes in-suite"]},
                {"title": "Wedding Weekend", "price": "Custom", "duration": "Fri–Sun", "description": "Ceremony meadow, guest blocks, and rehearsal dinner.", "bullets": ["Planner included", "AV for speeches", "Shuttle from airport"]},
            ],
        },
        "contact": {
            "address": "1 Timberline Road, Breckenridge, CO 80424",
            "phone": "(970) 555-0131",
            "email": "stay@mountainlodge.example",
            "hours": [
                {"days": "Front desk", "time": "24 / 7"},
                {"days": "Concierge", "time": "7am–9pm daily"},
                {"days": "Kitchen", "time": "Breakfast 7–10am, Dinner 5–9pm"},
            ],
            "form_note": "Share travel dates and group size—we'll hold availability for 24 hours while you confirm.",
            "faqs": [
                {"q": "Is there shuttle service?", "a": "Complimentary shuttle from the village gondola on the hour."},
                {"q": "What is the cancellation policy?", "a": "Flexible within 7 days for suites; packages vary by season."},
                {"q": "Are children welcome?", "a": "Yes—family suites include bunk rooms and early dining slots."},
            ],
        },
        "testimonials": [
            {"quote": "Woke up to snow on the ridge and coffee on the deck—exactly the reset we needed.", "author": "Evan & Priya", "role": "Anniversary Stay"},
            {"quote": "Concierge nailed every detail for our retreat, including dietary needs for twelve guests.", "author": "North Peak Nonprofit", "role": "Retreat Organizer"},
        ],
    },
    "petcare-studio": {
        "about": {
            "story": [
                "PetCare Studio is a fear-free certified clinic offering wellness exams, surgery, dentistry, grooming, and boarding under one roof. Our team spends extra time with anxious pets and sends home plain-language care summaries after every visit.",
                "We donate quarterly vaccine clinics to the county shelter and host junior vet days for local students.",
            ],
            "timeline": [
                {"year": "2010", "title": "Clinic opens", "body": "Two exam rooms and a part-time grooming tub."},
                {"year": "2018", "title": "Surgery suite", "body": "Digital X-ray and dental station added."},
                {"year": "2022", "title": "Boarding wing", "body": "Climate-controlled suites with webcam check-ins."},
            ],
            "team": [
                {"name": "Dr. Amy Cho", "role": "Medical Director", "bio": "DVM, special interest in senior pet mobility."},
                {"name": "Leo Martinez", "role": "Lead Groomer", "bio": "Fear-free grooming and breed-specific styling."},
                {"name": "Tessa Nguyen", "role": "Client Care", "bio": "Coordinates reminders, insurance forms, and boarding."},
            ],
            "principles": ["Fear-free handling protocols", "Transparent treatment estimates", "Same-day urgent slots for members"],
        },
        "services": {
            "intro": "Preventive care keeps tails wagging—choose a plan or book à la carte services.",
            "offerings": [
                {"title": "Wellness Exam", "price": "From $58", "duration": "30 min", "description": "Nose-to-tail exam with vaccine review.", "bullets": ["Puppy/kitten schedules", "Travel certificates", "Nutrition consult"]},
                {"title": "Dental Cleaning", "price": "From $420", "duration": "Same day", "description": "Pre-op bloodwork, anesthesia monitoring, polish.", "bullets": ["Digital dental chart", "Pain management plan", "Home care kit"]},
                {"title": "Groom & Spa", "price": "From $45", "duration": "1–2 hrs", "description": "Bath, trim, nail grind, and ear care.", "bullets": ["Hypoallergenic products", "Cat appointments", "De-shed treatment"]},
                {"title": "Boarding Suite", "price": "$55 / night", "duration": "Overnight", "description": "Private suite, three walks, webcam access.", "bullets": ["Medication administration", "Group play opt-in", "Late pickup Fridays"]},
            ],
        },
        "contact": {
            "address": "55 Maple Court, Madison, WI 53703",
            "phone": "(608) 555-0184",
            "email": "care@petcarestudio.example",
            "hours": [
                {"days": "Clinic", "time": "Mon–Fri 8am–6pm, Sat 9am–2pm"},
                {"days": "Grooming", "time": "Tue–Sat by appointment"},
                {"days": "Boarding", "time": "Drop-off 8–10am, pickup 4–6pm"},
            ],
            "form_note": "New patients: upload prior records if available. For urgent issues call instead of the form.",
            "faqs": [
                {"q": "Do you see exotic pets?", "a": "We care for rabbits and small mammals; reptiles by referral."},
                {"q": "What insurance do you accept?", "a": "We provide itemized receipts for all major pet insurers."},
                {"q": "Can I tour the boarding wing?", "a": "Yes—schedule a walkthrough before your first stay."},
            ],
        },
        "testimonials": [
            {"quote": "They coached us through our dog's anxiety meds—calm visits now.", "author": "Jenna & Milo", "role": "Golden Retriever Parents"},
            {"quote": "Boarding webcams let us check in during vacation—huge peace of mind.", "author": "Carlos M.", "role": "Cat Owner"},
        ],
    },
    "community-impact": {
        "about": {
            "story": [
                "Community Impact started as a weekend food drive and grew into a regional nonprofit serving 12,000 neighbors annually. We run mentorship labs, mobile pantries, and policy advocacy with transparent quarterly reporting.",
                "87 cents of every dollar goes directly to programs; audited financials are published every spring.",
            ],
            "timeline": [
                {"year": "2011", "title": "First food drive", "body": "200 meals distributed from a church parking lot."},
                {"year": "2017", "title": "501(c)(3) status", "body": "Formalized programs and volunteer training."},
                {"year": "2023", "title": "Regional expansion", "body": "Three counties, two mobile pantries, youth STEM lab."},
            ],
            "team": [
                {"name": "Rachel Boone", "role": "Executive Director", "bio": "Former educator; leads strategy and partnerships."},
                {"name": "Imani Brooks", "role": "Programs", "bio": "Runs mentorship, pantry routes, and volunteer training."},
                {"name": "Victor Hale", "role": "Development", "bio": "Stewardship, grants, and corporate sponsorships."},
            ],
            "principles": ["Community-led program design", "Published impact dashboards", "Volunteer background screening"],
        },
        "services": {
            "intro": "Programs are free to participants—your support funds supplies, staff, and safe spaces.",
            "offerings": [
                {"title": "Youth Mentorship Lab", "price": "Free", "duration": "School year", "description": "STEM, arts, and college prep for ages 12–18.", "bullets": ["Saturday sessions", "Mentor matching", "Transportation stipends"]},
                {"title": "Mobile Pantry", "price": "Free", "duration": "Weekly", "description": "Fresh produce and staples at four route stops.", "bullets": ["No ID required", "Diaper & hygiene kits", "Multilingual volunteers"]},
                {"title": "Advocacy Toolkit", "price": "Free", "duration": "Ongoing", "description": "Templates, office hours, and coalition meetings.", "bullets": ["Policy briefings", "Letter-writing nights", "Partner matchmaking"]},
                {"title": "Corporate Volunteer Days", "price": "Sponsorship", "duration": "1 day", "description": "Team builds, sorting shifts, and skills-based projects.", "bullets": ["Safety training", "Impact report", "Photo release handled"]},
            ],
        },
        "contact": {
            "address": "220 Hope Street, Columbus, OH 43215",
            "phone": "(614) 555-0110",
            "email": "hello@communityimpact.example",
            "hours": [
                {"days": "Office", "time": "Mon–Fri 9am–5pm"},
                {"days": "Pantry hotline", "time": "Tue & Thu 10am–2pm"},
                {"days": "Events", "time": "See calendar"},
            ],
            "form_note": "Choose how you'd like to help—donate, volunteer, or partner. We respond within one business day.",
            "faqs": [
                {"q": "Are donations tax-deductible?", "a": "Yes—EIN provided on receipt for U.S. donors."},
                {"q": "Can my company match gifts?", "a": "We participate in most workplace giving platforms."},
                {"q": "How do I volunteer?", "a": "Orientation is first Saturday monthly; background check for youth programs."},
            ],
        },
        "testimonials": [
            {"quote": "The mentorship lab changed my daughter's confidence—and her college list.", "author": "Parent Volunteer"},
            {"quote": "Transparent reporting made our corporate grant an easy yes.", "author": "Regional Bank CSR Lead"},
        ],
    },
    "homebase-realty": {
        "about": {
            "story": [
                "HomeBase Realty specializes in mountain cabins, lake properties, and in-town condos. Agents live in the markets they serve and publish monthly absorption and pricing snapshots for buyers and sellers.",
                "We negotiate with data-backed comps, local inspector relationships, and staging partners who know mountain buyers.",
            ],
            "timeline": [
                {"year": "2008", "title": "Brokerage founded", "body": "Focused on cabin and acreage listings."},
                {"year": "2016", "title": "Commercial desk", "body": "Retail and mixed-use expertise added."},
                {"year": "2024", "title": "Relocation team", "body": "Remote-work buyer program and virtual tours."},
            ],
            "team": [
                {"name": "Agent Carter", "role": "Listing Specialist", "bio": "Mountain cabins and acreage; 120+ closings."},
                {"name": "Agent Diaz", "role": "Buyer Advocate", "bio": "First-time and relocation buyers; bilingual service."},
                {"name": "Agent Kim", "role": "Commercial", "bio": "Mixed-use and small retail investments."},
            ],
            "principles": ["Local market reports included", "Drone and twilight media standard", "No dual-agency without disclosure"],
        },
        "services": {
            "intro": "Whether you're buying, selling, or investing, you get a clear playbook and weekly updates.",
            "offerings": [
                {"title": "Buyer Representation", "price": "Commission per MLS", "duration": "Varies", "description": "Search, showings, offer strategy, and closing coordination.", "bullets": ["Pre-approval partners", "Inspection negotiation", "Closing checklist"]},
                {"title": "Seller Launch", "price": "Custom marketing", "duration": "2–6 weeks", "description": "Pricing analysis, staging, media, and open houses.", "bullets": ["3D walkthrough", "Social ad kit", "Weekly showing report"]},
                {"title": "Home Valuation", "price": "Free", "duration": "48 hr", "description": "CMA with comp map and improvement ROI tips.", "bullets": ["No obligation", "Investor scenarios", "Rental potential snapshot"]},
                {"title": "Relocation Concierge", "price": "Included", "duration": "30 days", "description": "Schools, utilities, movers, and local introductions.", "bullets": ["Virtual tour package", "Temporary housing list", "Contractor referrals"]},
            ],
        },
        "contact": {
            "address": "88 Lakeview Drive, Traverse City, MI 49684",
            "phone": "(231) 555-0155",
            "email": "team@homebaserealty.example",
            "hours": [
                {"days": "Office", "time": "Mon–Sat 9am–6pm"},
                {"days": "Showings", "time": "7 days with appointment"},
                {"days": "Open houses", "time": "Weekends—see listings"},
            ],
            "form_note": "Tell us your timeline and budget—we'll match you with the right agent within one business day.",
            "faqs": [
                {"q": "Do you handle land and cabins?", "a": "Yes—septic, well, and road maintenance expertise on staff."},
                {"q": "Can you recommend lenders?", "a": "We partner with three local lenders familiar with vacation homes."},
                {"q": "How are commissions structured?", "a": "Discussed upfront per listing agreement; no hidden fees."},
            ],
        },
        "testimonials": [
            {"quote": "Agent Diaz walked us through a multiple-offer situation with calm, clear data.", "author": "The Nguyen Family", "role": "First-time Buyers"},
            {"quote": "Our cabin sold in nine days over ask—the media package made the difference.", "author": "Helen Price", "role": "Seller"},
        ],
    },
    "autoworks-garage": {
        "about": {
            "story": [
                "AutoWorks Garage is a family-owned shop with ASE-certified technicians, digital vehicle inspections, and text updates with photos at every milestone. We service daily drivers, classics, and light fleet vehicles.",
                "Community sponsorships include the high school automotive program and annual free brake checks for first responders.",
            ],
            "timeline": [
                {"year": "1998", "title": "Shop opens", "body": "Four bays and a focus on imports."},
                {"year": "2012", "title": "Fleet program", "body": "Maintenance contracts for local delivery companies."},
                {"year": "2021", "title": "EV ready", "body": "High-voltage safety training and battery health diagnostics."},
            ],
            "team": [
                {"name": "Mike Deluca", "role": "Shop Owner", "bio": "ASE Master; 30 years under the hood."},
                {"name": "Tara Singh", "role": "Service Advisor", "bio": "Translates inspections into plain-language options."},
                {"name": "Devon Lee", "role": "Lead Tech", "bio": "Brakes, suspension, and alignment specialist."},
            ],
            "principles": ["Digital inspections with photos", "OEM-grade parts available", "12-month / 12k mile workmanship warranty"],
        },
        "services": {
            "intro": "Upfront estimates, no surprise fees, and shuttle service within five miles.",
            "offerings": [
                {"title": "Oil & Filter", "price": "From $49", "duration": "30 min", "description": "Synthetic blend or full synthetic with multipoint check.", "bullets": ["Fluid top-off", "Tire pressure set", "Battery test"]},
                {"title": "Brake Service", "price": "From $189 / axle", "duration": "Same day", "description": "Pads, rotors, hardware, and road test.", "bullets": ["OEM or premium options", "Fleet pricing", "Warranty included"]},
                {"title": "Alignment", "price": "$99", "duration": "45 min", "description": "Four-wheel alignment with before/after printout.", "bullets": ["SUV/truck surcharge noted upfront", "Suspension inspection", "Road force balance add-on"]},
                {"title": "Fleet Maintenance", "price": "Custom", "duration": "Monthly", "description": "Scheduled service, pickups, and reporting dashboard.", "bullets": ["Consolidated invoicing", "Priority bays", "After-hours drop box"]},
            ],
        },
        "contact": {
            "address": "701 Motor Court, Reno, NV 89502",
            "phone": "(775) 555-0127",
            "email": "service@autoworksgarage.example",
            "hours": [
                {"days": "Shop", "time": "Mon–Fri 7:30am–6pm, Sat 8am–1pm"},
                {"days": "Fleet line", "time": "Mon–Fri 7am–5pm"},
                {"days": "Drop box", "time": "Keys accepted 24 / 7"},
            ],
            "form_note": "Include year/make/model and concern. We'll confirm appointment slots by text.",
            "faqs": [
                {"q": "Do you offer loaner cars?", "a": "Shuttle within 5 miles; loaners for major repairs when available."},
                {"q": "Can I supply my own parts?", "a": "Yes on labor-only jobs—warranty covers labor, not customer-supplied parts."},
                {"q": "Do you work on EVs?", "a": "Battery health, brakes, tires, and cabin filters—high-voltage repairs by partner."},
            ],
        },
        "testimonials": [
            {"quote": "They texted photos of worn pads before asking—no pressure, just clarity.", "author": "Jordan P.", "role": "Daily Commuter"},
            {"quote": "Our delivery vans stay on the road thanks to their fleet reporting.", "author": "QuickShip Logistics", "role": "Fleet Manager"},
        ],
    },
    "wellness-local": {
        "about": {
            "story": [
                "Wellness Local is an integrative clinic combining primary care, physical therapy, nutrition, and behavioral health. Visits are unhurried—30-minute minimums—and telehealth is available for follow-ups and coaching.",
                "We publish outcome metrics for pain reduction and diabetes management programs, and accept most major insurance plans.",
            ],
            "timeline": [
                {"year": "2015", "title": "Clinic founded", "body": "Two providers and a shared rehab gym."},
                {"year": "2020", "title": "Telehealth", "body": "Remote monitoring and virtual groups launched."},
                {"year": "2024", "title": "Corporate wellness", "body": "On-site screenings and ergonomics workshops."},
            ],
            "team": [
                {"name": "Dr. Rivera", "role": "Integrative Medicine", "bio": "Board-certified; focus on prevention and chronic care."},
                {"name": "Jamie Cho, PT", "role": "Physical Therapy", "bio": "Sports rehab, post-op, and balance programs."},
                {"name": "A. Morgan, RD", "role": "Nutrition", "bio": "Medical nutrition therapy and group classes."},
            ],
            "principles": ["Same-week new patient visits", "Sliding scale community classes", "HIPAA-secure patient portal"],
        },
        "services": {
            "intro": "Choose a care pathway or mix services—your chart is shared securely across the team.",
            "offerings": [
                {"title": "Primary Care", "price": "Copay per plan", "duration": "30–45 min", "description": "Preventive visits, labs, and chronic condition management.", "bullets": ["Evening hours Tue/Thu", "On-site phlebotomy", "Care plans in plain language"]},
                {"title": "Physical Therapy", "price": "Copay per plan", "duration": "45 min", "description": "Manual therapy, exercise prescription, and progress tracking.", "bullets": ["Open gym hours", "Post-surgical protocols", "Sports return-to-play"]},
                {"title": "Nutrition Coaching", "price": "$95 / session", "duration": "50 min", "description": "Personalized macros, gut health, and diabetes support.", "bullets": ["Meal planning apps", "Group classes monthly", "Telehealth follow-ups"]},
                {"title": "Corporate Wellness", "price": "Custom", "duration": "Contract", "description": "Screenings, ergonomics, and lunch-and-learn series.", "bullets": ["Aggregate reporting", "Flu shot clinics", "Stress management workshops"]},
            ],
        },
        "contact": {
            "address": "410 Harmony Lane, Boulder, CO 80301",
            "phone": "(303) 555-0191",
            "email": "frontdesk@wellnesslocal.example",
            "hours": [
                {"days": "Clinic", "time": "Mon–Fri 8am–6pm, Tue/Thu until 8pm"},
                {"days": "PT gym", "time": "Mon–Sat 7am–7pm"},
                {"days": "Telehealth", "time": "Mon–Fri 9am–5pm"},
            ],
            "form_note": "New patients: bring insurance card photo. For same-day urgent issues call the clinic line.",
            "faqs": [
                {"q": "Do you take my insurance?", "a": "We accept most major plans—verify with your member ID on the form."},
                {"q": "Is telehealth secure?", "a": "Yes—HIPAA-compliant video and messaging through our portal."},
                {"q": "Can I see multiple providers?", "a": "Yes—care teams coordinate through a shared chart with your consent."},
            ],
        },
        "testimonials": [
            {"quote": "Finally a clinic that doesn't rush—my PT and doctor actually talk to each other.", "author": "Sandra L.", "role": "Patient"},
            {"quote": "Our team's screening day was organized and the aggregate report was board-ready.", "author": "HR Director", "role": "Tech Company"},
        ],
    },
}


def get_rich_demo_content(slug: str) -> dict[str, Any]:
    """Return rich blocks for about/services/contact; empty dict sections if slug unknown."""
    return RICH_DEMO_CONTENT.get(slug, _default_rich_content(slug))


def _default_rich_content(slug: str) -> dict[str, Any]:
    title = slug.replace("-", " ").title()
    return {
        "about": {
            "story": [f"{title} is a modern local business website theme with room for your story and team."],
            "timeline": [{"year": "2020", "title": "Founded", "body": "Placeholder milestone—replace with your history."}],
            "team": [{"name": "Alex Morgan", "role": "Founder", "bio": "Leadership bio placeholder."}],
            "principles": ["Trust", "Quality", "Community"],
        },
        "services": {
            "intro": "Core offers and packages for your customers.",
            "offerings": [
                {"title": "Starter Package", "price": "From $99", "duration": "Flexible", "description": "Essential service bundle.", "bullets": ["Feature one", "Feature two"]},
            ],
        },
        "contact": {
            "address": "123 Main Street, Your City",
            "phone": "(555) 555-0100",
            "email": f"hello@{slug}.example",
            "hours": [{"days": "Weekdays", "time": "9am–5pm"}],
            "form_note": "We respond within one business day.",
            "faqs": [{"q": "Hours?", "a": "See schedule above."}],
        },
        "testimonials": [{"quote": "Great experience.", "author": "Customer", "role": "Local Client"}],
    }
