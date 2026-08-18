# SIU OSINT Cross-Reference Tool (Development Prototype)

A prototype for insurance Special Investigations Unit (SIU) work: given a
subject's name/username, phone number, and/or a domain, it runs open-source
lookups concurrently and produces a structured report plus an audit trail.

**Status: development only. Not cleared for use on real claimants until the
legal/compliance items below are signed off.**

## What it does

| Module | Source | What it pulls |
|---|---|---|
| `modules/social_search.py` | Bing Web Search API or SerpAPI (licensed search APIs, `site:` operator queries) | Public social profile URLs matching a name/username on major platforms |
| `modules/domain_lookup.py` | Public WHOIS | Domain registrar, creation date, name servers, registrant org (where not privacy-redacted) |
| `modules/phone_lookup.py` | NumVerify or Twilio Lookup (licensed reverse-lookup APIs) | Carrier, line type (mobile/landline/VoIP), country |

Every module falls back to **mock mode** (clearly labeled placeholder data,
no network calls) if its API key isn't set — so the pipeline is testable
without live credentials.

Every query is written to `logs/audit_log.jsonl` with timestamp,
investigator ID, case number, source, and a result summary — one line per
lookup, for the case file.

## Why it's built this way (read before extending)

- **No search-engine scraping.** Automating scraping of Google/Bing/social
  platform result pages (even with Playwright/Selenium) violates their
  Terms of Service and is legally shaky ground for a regulated insurer to
  ship. This tool calls licensed search APIs instead.
- **No breached-data / scraped "people search" services.** Phone lookups go
  through NumVerify or Twilio, both of which source data legitimately.
  Skip-tracing services built on leaked databases should not be plugged
  into this tool.
- **WHOIS is fine as-is** — domain registration data is publicly published
  by registrars by design.

## Before real deployment, get sign-off on:

1. **Investigator licensing** — many states require a PI license to conduct
   this kind of investigation professionally; requirements vary by state.
2. **FCRA applicability** — if results ever factor into a claim
   accept/deny/adjust decision, Fair Credit Reporting Act obligations
   (notice, dispute process, etc.) may apply. Insurer's compliance/legal
   team should confirm.
3. **Platform ToS for any new data source** you add — before wiring in a
   new lookup, check whether it's a licensed API or an unauthorized scrape.
4. **Data retention policy** — how long report JSON/CSV and audit logs are
   kept, and where subject PII is allowed to live at rest.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in whichever API keys you have; leave blank to run that module mocked
```

## Usage

```bash
python main.py --name "Jane Doe" --phone "+18135551234" --domain example.com --case CASE-2026-0142
python main.py --username janedoe123
```

Output lands in `output/<subject>_<timestamp>.json` and `.csv`.
Audit trail: `logs/audit_log.jsonl`.

## Extending

- Add platforms to `SOCIAL_PLATFORMS` in `config.py`.
- Add a new module under `modules/`, following the pattern in the existing
  ones: real API call behind an API-key check, mock-mode fallback, and a
  call to `modules.audit_log.log_query()` for every lookup performed.
