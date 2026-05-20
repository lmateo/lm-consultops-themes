from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.models import Template


def _safe_template_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value.lower()).strip("-")


def _build_index_html(template: Template) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{template.title} - Home</title>
  <meta name="description" content="{template.description}" />
  <link rel="stylesheet" href="assets/css/styles.css" />
</head>
<body>
  <header class="site-header">
    <div class="container nav">
      <div class="brand">{template.title}</div>
      <nav>
        <a href="index.html">Home</a>
        <a href="about.html">About</a>
        <a href="services.html">Services</a>
        <a href="pricing.html">Pricing</a>
        <a href="contact.html">Contact</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="container hero-layout">
        <div>
          <p class="eyebrow">{template.category.name} Website Theme</p>
          <h1>Build a modern {template.industry.name.lower()} website in days, not months.</h1>
          <p>{template.description}</p>
          <div class="actions">
            <a class="btn btn-primary" href="contact.html">Get Started</a>
            <a class="btn btn-outline" href="pricing.html">View Pricing</a>
          </div>
        </div>
        <aside class="card">
          <h2>What's Included</h2>
          <ul>
            <li>Responsive landing page and service pages</li>
            <li>Fast, semantic HTML with clean structure</li>
            <li>Modern typography and conversion-focused sections</li>
            <li>Ready-to-edit styles and simple JavaScript</li>
          </ul>
        </aside>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <h2>Featured Capabilities</h2>
        <div class="grid">
          <article class="card"><h3>Conversion Focused</h3><p>Every section helps visitors become qualified leads faster.</p></article>
          <article class="card"><h3>Industry Fit</h3><p>Built for {template.industry.name.lower()} workflows and customer trust.</p></article>
          <article class="card"><h3>Performance Ready</h3><p>Lean assets and readable code for excellent Lighthouse results.</p></article>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">Copyright 2026 {template.title}. All rights reserved.</div>
  </footer>

  <script src="assets/js/main.js"></script>
</body>
</html>
"""


def _build_simple_page(template: Template, title: str, description: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{template.title} - {title}</title>
  <meta name="description" content="{description}" />
  <link rel="stylesheet" href="assets/css/styles.css" />
</head>
<body>
  <header class="site-header">
    <div class="container nav">
      <div class="brand">{template.title}</div>
      <nav>
        <a href="index.html">Home</a>
        <a href="about.html">About</a>
        <a href="services.html">Services</a>
        <a href="pricing.html">Pricing</a>
        <a href="contact.html">Contact</a>
      </nav>
    </div>
  </header>
  <main>
    <section class="section">
      <div class="container">
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="container">Copyright 2026 {template.title}. All rights reserved.</div>
  </footer>
  <script src="assets/js/main.js"></script>
</body>
</html>
"""


def _build_styles() -> str:
    return """* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, Arial, sans-serif; color: #111827; background: #f8fafc; line-height: 1.6; }
a { color: inherit; text-decoration: none; }
.container { width: min(1120px, 92%); margin: 0 auto; }
.site-header { position: sticky; top: 0; z-index: 20; border-bottom: 1px solid #e5e7eb; background: #ffffff; }
.nav { display: flex; align-items: center; justify-content: space-between; padding: 1rem 0; gap: 1rem; flex-wrap: wrap; }
.brand { font-weight: 800; color: #047857; }
nav { display: flex; gap: 1rem; flex-wrap: wrap; }
nav a { color: #6b7280; font-weight: 600; }
nav a:hover { color: #111827; }
.hero { padding: 4.5rem 0 3rem; background: linear-gradient(160deg, #ecfdf5, #ffffff); }
.hero-layout { display: grid; gap: 1.5rem; grid-template-columns: 1.7fr 1fr; align-items: start; }
.eyebrow { margin: 0 0 .75rem; color: #047857; font-weight: 700; text-transform: uppercase; font-size: .8rem; letter-spacing: .06em; }
h1 { margin: 0 0 .75rem; font-size: clamp(1.8rem, 3vw, 2.8rem); line-height: 1.2; }
h2 { margin-top: 0; font-size: clamp(1.25rem, 2vw, 1.8rem); }
.actions { margin-top: 1.2rem; display: flex; gap: .75rem; flex-wrap: wrap; }
.btn { padding: .72rem 1rem; border-radius: .65rem; font-weight: 700; display: inline-block; }
.btn-primary { background: #10b981; color: #ffffff; }
.btn-primary:hover { background: #047857; }
.btn-outline { border: 1px solid #d1d5db; background: #ffffff; color: #111827; }
.section { padding: 2.4rem 0; }
.grid { display: grid; gap: 1rem; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 1rem; padding: 1rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04); }
.card ul { margin: .5rem 0 0 1rem; padding: 0; }
.site-footer { margin-top: 2rem; padding: 1.5rem 0; border-top: 1px solid #e5e7eb; background: #ffffff; color: #6b7280; }
@media (max-width: 900px) {
  .hero-layout { grid-template-columns: 1fr; }
  .grid { grid-template-columns: 1fr; }
}
"""


def _build_script() -> str:
    return """document.addEventListener("DOMContentLoaded", () => {
  const yearNodes = document.querySelectorAll("[data-year]");
  const year = new Date().getFullYear();
  yearNodes.forEach((node) => {
    node.textContent = String(year);
  });
});
"""


def build_theme_zip_bytes(template: Template) -> tuple[bytes, str]:
    slug = _safe_template_name(template.slug)
    root = f"{slug}-theme/"
    filename = f"{slug}-v{template.version}.zip"

    readme = f"""# {template.title} Theme Package

Thanks for your purchase.

## Included Files
- `index.html`
- `about.html`
- `services.html`
- `pricing.html`
- `contact.html`
- `assets/css/styles.css`
- `assets/js/main.js`

## Quick Start
1. Unzip this package.
2. Open `index.html` in your browser.
3. Edit copy, styles, and branding as needed.

## Theme Metadata
- Category: {template.category.name}
- Industry: {template.industry.name}
- Version: {template.version}
- License: Commercial purchase required
"""

    memory_file = BytesIO()
    with ZipFile(memory_file, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{root}index.html", _build_index_html(template))
        archive.writestr(
            f"{root}about.html",
            _build_simple_page(template, "About", "Tell your story, team values, and mission in a trust-building format."),
        )
        archive.writestr(
            f"{root}services.html",
            _build_simple_page(template, "Services", "Present core offers with clear outcomes, proof, and call-to-action blocks."),
        )
        archive.writestr(
            f"{root}pricing.html",
            _build_simple_page(template, "Pricing", "List packages transparently so visitors can compare and choose quickly."),
        )
        archive.writestr(
            f"{root}contact.html",
            _build_simple_page(template, "Contact", "Capture inbound leads with clear next steps and response expectations."),
        )
        archive.writestr(f"{root}assets/css/styles.css", _build_styles())
        archive.writestr(f"{root}assets/js/main.js", _build_script())
        archive.writestr(f"{root}README.md", readme)
        archive.writestr(
            f"{root}assets/images/README.txt",
            "Replace this folder with your own optimized WebP/JPG assets.",
        )

    return memory_file.getvalue(), filename
