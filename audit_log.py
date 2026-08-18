"""
Audit logging for every outbound lookup this tool performs.

Insurance SIU work ends up in case files and sometimes in front of a
regulator or a court, so every query needs a record of: who ran it,
when, against what subject, hitting which data source, and what the
raw result was. This module is intentionally simple (append-only
JSONL) so a case supervisor can grep/diff it without special tooling.
"""
import json
import os
import threading
from datetime import datetime, timezone

import config

_LOCK = threading.Lock()
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_PATH = os.path.join(_LOG_DIR, "audit_log.jsonl")


def log_query(module: str, query: str, source: str, result_summary: str, mock: bool = False):
    """Append one audit record. Thread-safe (modules run concurrently)."""
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "investigator_id": config.INVESTIGATOR_ID,
        "case_number": config.CASE_NUMBER,
        "module": module,
        "query": query,
        "source": source,
        "mock_mode": mock,
        "result_summary": result_summary,
    }
    with _LOCK:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    return entry


def log_path() -> str:
    return _LOG_PATH
