# Homepage capture for README

## Recommended: Playwright (works without Figma login)

This is the **default** for this repo because Figma MCP OAuth often fails in Cursor (browser never opens, callback not handled, or sign-in times out).

**Prerequisites:** app running with seed data.

| Environment | URL |
|-------------|-----|
| Docker | http://localhost:8010 |
| Local uvicorn | http://localhost:8000 |

```bash
playwright install chromium
py scripts/capture_readme_homepage.py
py scripts/capture_readme_homepage.py --base-url http://localhost:8000
```

Outputs:

- `docs/images/homepage.webp`
- `docs/images/homepage-readme.webp` (used in README)

---

## Optional: Figma MCP in Cursor

Only use this if OAuth completes successfully. Tools like `generate_figma_design` and `get_screenshot` require the remote Figma server (`plugin-figma-figma`).

### If sign-in does not work (common)

This is a **known Cursor + remote MCP OAuth issue**, not a problem with this project. Typical symptoms:

- **Connect** flashes then returns to **Connect** with no browser
- Browser login succeeds but Cursor never finishes (`cursor://` callback not handled)
- **`mcp_auth` times out** or you skip the prompt
- Only **`plugin-browse-browser`** appears in available MCP servers

**Things to try (in order):**

1. **Update Cursor** to the latest stable build (Settings → About → Check for updates).
2. **Manual auth URL:** View → Output → select **MCP: Figma** (or similar) in the dropdown. After clicking Connect, copy the `https://...authorize...` URL from the log and open it in Chrome/Edge yourself. Complete login; Cursor should pick up the session.
3. **Click “Needs authentication”** text (not only the Connect button)—some builds open the browser from there.
4. **Default browser:** Set a normal browser (Chrome/Edge) as default; disable “open links in app” blockers for `cursor://` URLs.
5. **Windows:** Install the native Cursor installer (not only a portable copy) so `cursor://` protocol handlers register correctly.
6. **Clear MCP auth cache:** Close Cursor completely → delete `%USERPROFILE%\.cursor\mcp_cache` (if present) → restart Cursor → try Connect once.
7. **Restart twice** after changing MCP settings (Cursor MCP connections cache aggressively).

**Limited alternative — local Figma MCP with API token** (fewer tools; no `generate_figma_design`):

Add to `.cursor/mcp.json` (user-level, not committed):

```json
{
  "mcpServers": {
    "Figma": {
      "command": "npx",
      "args": ["-y", "figma-developer-mcp", "--stdio"],
      "env": {
        "FIGMA_API_KEY": "your-personal-access-token"
      }
    }
  }
}
```

Create a token in Figma: **Settings → Security → Personal access tokens**. This path does **not** support live URL capture; use Playwright for README screenshots instead.

### Agent workflow (when Figma MCP is authenticated)

Server id: **`plugin-figma-figma`** (not `figma`).

1. `mcp_auth({})` if required
2. `generate_figma_design({ "url": "http://localhost:8010/" })`
3. `get_screenshot({ "fileKey": "...", "nodeId": "..." })` → save under `docs/images/`
4. Keep README image: `docs/images/homepage-readme.webp`

---

## Troubleshooting captures

| Symptom | Fix |
|---------|-----|
| Playwright `ERR_CONNECTION_REFUSED` | Start Docker (`.\docker.ps1 up`) or uvicorn |
| Empty homepage in screenshot | Run `python -m app.seed.seed` |
| Huge PNG in git | Script writes WebP only; do not commit raw full-page PNG |
