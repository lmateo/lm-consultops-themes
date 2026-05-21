# Crafto HTML demo mapping

Mateo marketplace templates are linked to Crafto multipurpose HTML demos under `crafto-html-templates/`.

| Mateo slug | Crafto demo | Home | About | Services | Contact |
|------------|-------------|------|-------|----------|---------|
| `greenfield-farm` | Green Energy | `demo-green-energy.html` | `demo-green-energy-about.html` | `demo-green-energy-services.html` | `demo-green-energy-contact.html` |
| `tradepro-local` | Business | `demo-business.html` | `demo-business-about.html` | `demo-business-services.html` | `demo-business-contact.html` |
| `pizza-local-eats` | Pizza Parlor | `demo-pizza-parlor.html` | `demo-pizza-parlor-about.html` | `demo-pizza-parlor-menu.html` | `demo-pizza-parlor-contact.html` |
| `cloudcare-it` | IT Business | `demo-it-business.html` | `demo-it-business-about.html` | `demo-it-business-services.html` | `demo-it-business-contact.html` |
| `mountain-lodge` | Hotel & Resort | `demo-hotel-and-resort.html` | `demo-hotel-and-resort-about-us.html` | `demo-hotel-and-resort-rooms.html` | `demo-hotel-and-resort-contact.html` |
| `petcare-studio` | Medical | `demo-medical.html` | `demo-medical-about.html` | `demo-medical-treatments.html` | `demo-medical-contact.html` |
| `community-impact` | Charity | `demo-charity.html` | `demo-charity-about.html` | `demo-charity-causes.html` | `demo-charity-contact.html` |
| `homebase-realty` | Real Estate | `demo-real-estate.html` | `demo-real-estate-about.html` | `demo-real-estate-sell.html` | `demo-real-estate-contact.html` |
| `autoworks-garage` | Logistics | `demo-logistics.html` | `demo-logistics-about-us.html` | `demo-logistics-our-services.html` | `demo-logistics-contact-us.html` |
| `wellness-local` | Spa Salon | `demo-spa-salon.html` | `demo-spa-salon-about.html` | `demo-spa-salon-treatments.html` | `demo-spa-salon-contact.html` |

## Runtime

- Static assets: `/crafto/` → `crafto-html-templates/`
- Live preview iframe: `/crafto/{demo-file}`
- Legacy routes `/preview-site/{slug}` redirect to the mapped Crafto file

Source of truth: `app/services/crafto_demos.py`
