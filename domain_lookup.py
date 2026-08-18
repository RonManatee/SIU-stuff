"""
Domain / WHOIS lookup.

Pulls public domain registration data (registrar, creation date, name
servers, and registrant fields when not redacted by GDPR/privacy proxy).
This queries public WHOIS servers directly via the `python-whois`
library -- this data is publicly published by registrars by design, so
there's no ToS concern here the way there is with search-engine scraping.
"""
import time

import whois

import config
from modules.audit_log import log_query


def lookup_domain(domain: str) -> dict:
    domain = domain.strip().lower()
    try:
        w = whois.whois(domain)
        result = {
            "domain": domain,
            "mock": False,
            "registrar": w.get("registrar"),
            "creation_date": _stringify(w.get("creation_date")),
            "expiration_date": _stringify(w.get("expiration_date")),
            "name_servers": _stringify(w.get("name_servers")),
            "org": w.get("org"),
            "emails": _stringify(w.get("emails")),
            "raw_status": _stringify(w.get("status")),
        }
        summary = f"registrar={result['registrar']}"
        source = "public_whois"
    except Exception as e:
        result = {"domain": domain, "mock": False, "error": str(e)}
        summary = f"error: {e}"
        source = "public_whois"

    log_query(module="domain_lookup", query=domain, source=source, result_summary=summary)
    time.sleep(config.REQUEST_DELAY_SECONDS)
    return result


def _stringify(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    return str(value) if value is not None else None


def lookup_domains(domains: list) -> list:
    return [lookup_domain(d) for d in domains]
