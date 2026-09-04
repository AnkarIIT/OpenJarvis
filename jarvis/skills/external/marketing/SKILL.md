---
name: marketing
description: "Access jaredrhod's marketing playbook. Use when the user wants marketing work: copywriting, sales pages, ads, emails, lead magnets, content, or funnel strategy. Lists available playbooks, loads specific frameworks, and returns their content so the LLM can produce operator-grade marketing output."
version: 1.0.0
author: OpenJarvis
---

# Marketing Skill

Wrapper for the `ai-marketing-skills/jaredrhod-marketing/` playbook. It exposes the markdown frameworks as discoverable, loadable commands. The LLM should read the loaded playbook content before producing any marketing output.

## Source
- Base path: `ai-marketing-skills/jaredrhod-marketing/`
- Core principles: `jareds-takes.md` (always read first for marketing tasks)
- Playbooks: `marketing-copywriting.md`, `marketing-sales-letter.md`, `marketing-email.md`, `marketing-fb-ads.md`, `marketing-lead-magnets.md`, `marketing-content.md`, `marketing-analytics.md`
- Strategy: `the-fundamentals.md`
- Background: `about.md`, `the-thesis.md`

## Usage rule
Never produce marketing output cold. Load `jareds-takes.md` plus the matching playbook first, every single time.
