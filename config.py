"""
Central config loader. Reads API keys from environment / .env file.
Any missing key means that module runs in MOCK MODE instead of failing.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BING_SEARCH_API_KEY = os.getenv("BING_SEARCH_API_KEY", "").strip()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()

NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "").strip()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

INVESTIGATOR_ID = os.getenv("INVESTIGATOR_ID", "unspecified").strip()
CASE_NUMBER = os.getenv("CASE_NUMBER", "unspecified").strip()

# Platforms checked for social profile discovery (search-operator based).
# This list only drives *search queries* (e.g. site:linkedin.com "John Doe"),
# it never logs into or scrapes these platforms directly.
SOCIAL_PLATFORMS = [
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "github.com",
    "reddit.com",
]

REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 1.5  # throttle between outbound calls per module
