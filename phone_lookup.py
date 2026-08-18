"""
Phone number lookup.

Uses a licensed reverse-lookup API -- NumVerify or Twilio Lookup -- to get
carrier, line type (mobile/landline/VoIP), and country/location info.
Deliberately does NOT use scraped "people search" sites or breached-data
lookup services: those are a legal liability (data provenance is often
illegally sourced) and unsuitable for anything that ends up in a claims
file. If no API key is configured, runs in MOCK MODE.
"""
import time

import requests

import config
from modules.audit_log import log_query

NUMVERIFY_ENDPOINT = "http://apilayer.net/api/validate"
TWILIO_ENDPOINT_TMPL = "https://lookups.twilio.com/v2/PhoneNumbers/{number}"


def _mock_result(phone: str) -> dict:
    return {
        "phone": phone,
        "mock": True,
        "valid": None,
        "carrier": None,
        "line_type": None,
        "country": None,
        "note": "No live API key configured (NUMVERIFY_API_KEY / "
                "TWILIO_ACCOUNT_SID+TWILIO_AUTH_TOKEN) -- placeholder result.",
    }


def _lookup_numverify(phone: str) -> dict:
    params = {"access_key": config.NUMVERIFY_API_KEY, "number": phone}
    resp = requests.get(NUMVERIFY_ENDPOINT, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    return {
        "phone": phone,
        "mock": False,
        "valid": data.get("valid"),
        "carrier": data.get("carrier"),
        "line_type": data.get("line_type"),
        "country": data.get("country_name"),
        "location": data.get("location"),
    }


def _lookup_twilio(phone: str) -> dict:
    url = TWILIO_ENDPOINT_TMPL.format(number=phone)
    resp = requests.get(
        url,
        params={"Fields": "line_type_intelligence"},
        auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    line_info = data.get("line_type_intelligence") or {}
    return {
        "phone": phone,
        "mock": False,
        "valid": data.get("valid"),
        "carrier": line_info.get("carrier_name"),
        "line_type": line_info.get("type"),
        "country": data.get("country_code"),
    }


def lookup_phone(phone: str) -> dict:
    try:
        if config.NUMVERIFY_API_KEY:
            result = _lookup_numverify(phone)
            source = "numverify"
        elif config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
            result = _lookup_twilio(phone)
            source = "twilio_lookup"
        else:
            result = _mock_result(phone)
            source = "mock"
        summary = f"valid={result.get('valid')} carrier={result.get('carrier')}"
    except requests.RequestException as e:
        result = {"phone": phone, "mock": False, "error": str(e)}
        source = "error"
        summary = f"error: {e}"

    log_query(module="phone_lookup", query=phone, source=source, result_summary=summary,
               mock=result.get("mock", False))
    time.sleep(config.REQUEST_DELAY_SECONDS)
    return result


def lookup_phones(phones: list) -> list:
    return [lookup_phone(p) for p in phones]
