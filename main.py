#!/usr/bin/env python3
"""
SIU OSINT Investigation Tool (development prototype)

Cross-references a subject's name, phone number, and associated domain
across open-source data sources, running all lookups concurrently, and
writes a structured JSON + CSV report plus an audit log entry per query.

USAGE:
    python main.py --name "Jane Doe" --phone "+18135551234" --domain example.com
    python main.py --name "Jane Doe" --username janedoe123

NOTE: this is a development-phase prototype. See README.md for the legal/
compliance items (licensing, FCRA, platform ToS) that need sign-off before
any real deployment against real claimants.
"""
import argparse
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.social_search import search_social_profiles
from modules.domain_lookup import lookup_domain
from modules.phone_lookup import lookup_phone
from modules.audit_log import log_path
import config

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_investigation(name: str = None, username: str = None, phone: str = None, domain: str = None) -> dict:
    subject_query = username or name
    if not subject_query and not phone and not domain:
        raise ValueError("Provide at least one of --name/--username, --phone, or --domain")

    tasks = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        if subject_query:
            tasks["social_profiles"] = executor.submit(search_social_profiles, subject_query)
        if phone:
            tasks["phone"] = executor.submit(lookup_phone, phone)
        if domain:
            tasks["domain"] = executor.submit(lookup_domain, domain)

        results = {key: future.result() for key, future in tasks.items()}

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investigator_id": config.INVESTIGATOR_ID,
        "case_number": config.CASE_NUMBER,
        "subject_input": {"name": name, "username": username, "phone": phone, "domain": domain},
        "results": results,
    }
    return report


def write_report(report: dict, basename: str):
    json_path = os.path.join(OUTPUT_DIR, f"{basename}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    csv_path = os.path.join(OUTPUT_DIR, f"{basename}.csv")
    rows = []
    for category, data in report["results"].items():
        if category == "social_profiles":
            for platform_result in data:
                for hit in platform_result.get("results", []):
                    rows.append({
                        "category": "social_profile",
                        "platform_or_source": platform_result.get("platform"),
                        "field": hit.get("title"),
                        "value": hit.get("url"),
                        "mock": platform_result.get("mock"),
                    })
        elif category == "phone":
            for k, v in data.items():
                rows.append({"category": "phone", "platform_or_source": "phone_lookup",
                             "field": k, "value": v, "mock": data.get("mock")})
        elif category == "domain":
            for k, v in data.items():
                rows.append({"category": "domain", "platform_or_source": "whois",
                             "field": k, "value": v, "mock": data.get("mock", False)})

    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["category", "platform_or_source", "field", "value", "mock"])
            writer.writeheader()
            writer.writerows(rows)

    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description="SIU OSINT cross-reference tool (dev prototype)")
    parser.add_argument("--name", help="Subject full name")
    parser.add_argument("--username", help="Known username/handle (overrides --name for social search)")
    parser.add_argument("--phone", help="Phone number, e.g. +18135551234")
    parser.add_argument("--domain", help="Domain to WHOIS-lookup")
    parser.add_argument("--case", help="Case number for this run (overrides .env CASE_NUMBER)")
    args = parser.parse_args()

    if args.case:
        config.CASE_NUMBER = args.case

    report = run_investigation(name=args.name, username=args.username, phone=args.phone, domain=args.domain)

    safe_subject = (args.username or args.name or args.phone or args.domain or "subject")
    safe_subject = "".join(c if c.isalnum() else "_" for c in safe_subject)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = f"{safe_subject}_{timestamp}"

    json_path, csv_path = write_report(report, basename)

    print(f"Report written:\n  {json_path}\n  {csv_path}")
    print(f"Audit log: {log_path()}")


if __name__ == "__main__":
    main()
