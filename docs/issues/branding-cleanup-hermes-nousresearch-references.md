# Branding Cleanup: Remove All Hermes/NousResearch References, Update to Jarvis/AnkarIIT

**Status:** Completed  
**Branch:** `main`  
**Commits:** Multiple commits across the session  
**Scope:** README.md, source code, assets, URLs, badges, references

---

## Summary

This issue tracks the complete branding cleanup performed to remove all traces of "hermes" and "NousResearch" references from the codebase and replace them with "jarvis" and "AnkarIIT" branding. The work covered README.md, source code files, asset images, URLs, badges, User-Agent strings, and documentation links.

---

## Changes Made

### 1. README.md — Comprehensive URL and Branding Updates

#### 1.1 Install URL Updates
- **Before:** `curl -fsSL https://jarvis-agent.nousresearch.com/install.sh | bash`
- **After:** `curl -fsSL https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/install.sh | bash`

- **Before:** `iex (irm https://jarvis-agent.nousresearch.com/install.ps1)`
- **After:** `iex (irm https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/install.ps1)`

Both Linux/macOS and Windows PowerShell installation commands now point to the GitHub repository's raw content.

#### 1.2 Documentation Links Updated
All documentation URLs changed from `jarvis-agent.nousresearch.com/docs/...` to `github.com/AnkarIIT/OpenJarvis/wiki/...`:

| Section | Before | After |
|---------|--------|-------|
| Quickstart | `.../docs/getting-started/quickstart` | `.../wiki/Quickstart` |
| CLI Usage | `.../docs/user-guide/cli` | `.../wiki/CLI-Usage` |
| Configuration | `.../docs/user-guide/configuration` | `.../wiki/Configuration` |
| Messaging Gateway | `.../docs/user-guide/messaging` | `.../wiki/Messaging-Gateway` |
| Security | `.../docs/user-guide/security` | `.../wiki/Security` |
| Tools & Toolsets | `.../docs/user-guide/features/tools` | `.../wiki/Tools-and-Toolsets` |
| Skills System | `.../docs/user-guide/features/skills` | `.../wiki/Skills-System` |
| Memory | `.../docs/user-guide/features/memory` | `.../wiki/Memory` |
| MCP Integration | `.../docs/user-guide/features/mcp` | `.../wiki/MCP-Integration` |
| Cron Scheduling | `.../docs/user-guide/features/cron` | `.../wiki/Cron-Scheduling` |
| Context Files | `.../docs/user-guide/features/context-files` | `.../wiki/Context-Files` |
| Architecture | `.../docs/developer-guide/architecture` | `.../wiki/Architecture` |
| Contributing | `.../docs/developer-guide/contributing` | `.../wiki/Contributing` |
| CLI Reference | `.../docs/reference/cli-commands` | `.../wiki/CLI-Reference` |
| Environment Variables | `.../docs/reference/environment-variables` | `.../wiki/Environment-Variables` |

#### 1.3 Badge Updates
- **Documentation Badge:** Changed from `Docs-jarvis--agent.nousresearch.com-FFD700` to `Docs-GitHub-FFD700`
- **Community Discord Badge:** Changed from `Discord-5865F2` linking to `discord.gg/NousResearch` to `Community-Discord-5865F2` linking to `github.com/AnkarIIT/OpenJarvis`

#### 1.4 Title and Header Updates
- Main title: `# Jarvis Agent ☤ v0.21.3` — removed "Built by Nous Research" attribution
- Header links: Changed from `jarvis-agent.nousresearch.com` to `github.com/AnkarIIT/OpenJarvis`
- Description text: Removed "built by Nous Research" reference
- Providers list: Removed "Nous Portal" from the list of providers
- Removed entire "Skip the API-key collection — Nous Portal" section

#### 1.5 Footer Cleanup
- Removed "Built by [Nous Research](https://nousresearch.com)." footer line

---

### 2. Banner Image Replacement

- **File:** `assets/banner.png`
- **Before:** Old banner with "HERMES-AGENT" text and "jarvis-agent.nousresearch.com" button
- **After:** User-provided pixel-art banner — 2172x369 pixels, RGBA mode, deep near-black background (`RGB(11, 16, 23)`), centered "JARVIS-AGENT" text in bright cyan with glow effect, "v0.21.3" version text in gray, "View on GitHub" button in dark gray with cyan border

The new banner is clean with no NousResearch references and points to GitHub.

---

### 3. Source Code Branding Updates

#### 3.1 `jarvis_cli/auth_constants.py`
- **Line 59:** Changed `DEFAULT_NOUS_CLIENT_ID = "hermes-cli"` → `DEFAULT_NOUS_CLIENT_ID = "jarvis-cli"`

#### 3.2 `tools/xai_http.py`
- **Line 61:** Updated compat alias comment: `plugins importing ``hermes_xai_user_agent``` → `plugins importing ``jarvis_xai_user_agent```
- Note: The actual compat alias variable `hermes_xai_user_agent = jarvis_xai_user_agent` is preserved for backward compatibility

#### 3.3 `plugins/plugin_storage.py`
- **Line 1:** Docstring updated: `<hermes home>` → `<jarvis home>`
- **Line 3:** Docstring updated: `<hermes home>/plugins/` → `<jarvis home>/plugins/`
- **Line 17 (around):** Comment updated: `hermes plugins install` → `jarvis plugins install`
- **Line 27 (around):** Docstring updated: `<hermes home>` → `<jarvis home>`

#### 3.4 `tools/skills_hub_official.py`
- **Line 35:** Changed "Nous-maintained" → "AnkarIIT-maintained" in class docstring
- **Line 41:** Changed `OFFICIAL_REPO = "NousResearch/jarvis-agent"` → `OFFICIAL_REPO = "AnkarIIT/OpenJarvis"`

#### 3.5 `tools/discord_tool.py`
- **Line 66:** Updated User-Agent header:
  - **Before:** `"User-Agent": "Jarvis-Agent (https://github.com/NousResearch/jarvis-agent)"`
  - **After:** `"User-Agent": "Jarvis-Agent (https://github.com/AnkarIIT/OpenJarvis)"`

#### 3.6 `tools/skills_hub_search.py`
- **Line 27:** Updated JARVIS_INDEX_URL:
  - **Before:** `https://jarvis-agent.nousresearch.com/docs/api/skills-index.json`
  - **After:** `https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/tools/skills-index.json`

---

### 4. Files NOT Modified (Intentional)

The following were intentionally NOT changed as they represent functional provider integrations, not branding:

- **`jarvis_cli/anon_auth.py`** — Nous free tier authentication system (functional provider integration)
- **`jarvis_cli/auth.py`** — Nous auth helpers and OAuth flows (functional)
- **`tools/managed_tool_gateway.py`** — Nous tool gateway (functional provider)
- **`tools/tool_backend_helpers.py`** — `NOUS_MANAGED_PROVIDER = "nous"` (functional provider config)
- **Image generation, TTS, STT, browser gateway files** — "nous" provider options (functional)
- **Skills sync client files** — Nous admin gate (functional)

These files contain "nous" references that are part of the provider/integration layer, not branding. Removing them would break functionality.

---

## Backward Compatibility Notes

Several "hermes" references were intentionally preserved as backward-compatibility aliases:

1. **`tools/xai_http.py`** — `hermes_xai_user_agent = jarvis_xai_user_agent` (compat re-export)
2. **`jarvis_cli/env_loader.py`** — `load_hermes_dotenv()` function (backward-compat alias)
3. **`jarvis_cli/profiles.py`** — `_get_default_hermes_home()` function (backward-compat alias)
4. **`jarvis_cli/auth_constants.py`** — Previously had `DEFAULT_NOUS_CLIENT_ID = "hermes-cli"` (now updated to `jarvis-cli`)

These aliases ensure existing external plugins and in-flight code don't break. The function names remain but comments/docstrings were updated to note they're aliases.

---

## Verification

### README Verification
```bash
# Check for any remaining "hermes" references (should return 0)
grep -ci "hermes" README.md

# Check for any remaining "nous" references (should return only Discord badge if still present)
grep -ci "nous" README.md
```

### Remote Verification
```bash
# Verify remote README has no old branding
curl -s https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/README.md | grep -i "hermes-agent.nousresearch.com"
curl -s https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/README.md | grep -i "Built by Nous"
```

### Asset Verification
```python
from PIL import Image
img = Image.open('assets/banner.png')
print(f"Size: {img.size}, Mode: {img.mode}")  # Expected: (2172, 369), RGBA
```

---

## Remaining Notes

### External URLs That Point to NousResearch Infrastructure
Some URLs in the codebase still point to NousResearch infrastructure because they represent functional service endpoints, not branding:

- `welcome-api.nousresearch.com` — Nous free tier welcome API (in `auth_constants.py`)
- `portal.nousresearch.com` — Nous Portal (in auth.py)
- `gateway-gateway.nousresearch.com` — Skills sync gateway (in skills_sync_client.py)
- `nousresearch.github.io` — GitHub Pages docs site (in mcp_oauth.py)

These are service endpoints that would need replacement infrastructure to change. They are not branding references but actual API/service URLs.

### Discord Community Link
The Discord badge now points to `github.com/AnkarIIT/OpenJarvis` instead of `discord.gg/NousResearch`. If a Discord community server is needed, a new invite link should be configured.

---

## Files Modified Summary

| File | Change Type | Lines Modified |
|------|-------------|----------------|
| `README.md` | URL updates, badge changes, text cleanup | ~50+ lines affected |
| `assets/banner.png` | Image replacement (binary) | Replaced entirely |
| `jarvis_cli/auth_constants.py` | Client ID string update | 1 line |
| `tools/xai_http.py` | Comment update | 1 line |
| `plugins/plugin_storage.py` | Docstring/comment updates | 4+ lines |
| `tools/skills_hub_official.py` | Attribution + repo name | 2 lines |
| `tools/discord_tool.py` | User-Agent string | 1 line |
| `tools/skills_hub_search.py` | Index URL | 1 line |

---

## Checklist

- [x] All "hermes" references removed from README.md
- [x] All "NousResearch" branding removed from README.md  
- [x] All install URLs updated to GitHub raw content
- [x] All documentation links updated to GitHub wiki
- [x] Badges updated (Docs, Community/Discord)
- [x] "Built by Nous Research" footer removed
- [x] "Nous Portal" section removed from README
- [x] Banner image replaced with user-provided pixel-art version
- [x] Source code docstrings updated (hermes home → jarvis home)
- [x] Source code comments updated (hermes → jarvis)
- [x] User-Agent string updated
- [x] Skills hub official repo name updated
- [x] Skills hub index URL updated
- [x] Auth client ID updated (hermes-cli → jarvis-cli)
- [x] Backward-compat aliases preserved where needed
- [x] Functional provider integrations left intact
- [x] Commits pushed to main branch

---

## Related Issues

- Initial branding cleanup to remove Hermes references
- URL replacement from jarvis-agent.nousresearch.com to GitHub

---

**Created:** 2026-09-27  
**Author:** Hermes Agent (automated session)
