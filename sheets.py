"""Google Sheets integration via Google Apps Script Web App webhook.

Uses the requests library to send POST requests (with redirects) to append rows,
and GET requests to retrieve recent history and test runs.

Strictly enforces an 11-column contract for both Results and Tests tabs:
1. Timestamp
2. Topic
3. Prompt Version
4. Scope
5. Resources
6. Sources
7. Outcomes
8. Total
9. Verdict
10. Validation
11. Notes
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

EXPECTED_HEADERS = [
    "Timestamp", "Topic", "Prompt Version", "Scope", "Resources",
    "Sources", "Outcomes", "Total", "Verdict", "Validation", "Notes"
]


def get_apps_script_config() -> Tuple[str, str]:
    """Retrieves APPS_SCRIPT_URL and APPS_SCRIPT_SECRET strictly from .env."""
    url = os.getenv("APPS_SCRIPT_URL", "").strip()
    secret = os.getenv("APPS_SCRIPT_SECRET", "").strip()
    return url, secret


def save_row(tab: str, row: List[Any]) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Appends a row to the specified tab ('Results' or 'Tests') via Google Apps Script Web App.
    Guarantees exactly 11 columns in standard header order.
    Returns (ok, row_number, error_message).
    """
    url, secret = get_apps_script_config()
    if not url:
        return False, None, "APPS_SCRIPT_URL is not configured in .env"

    # Enforce exactly 11 columns
    if len(row) != 11:
        return False, None, f"Contract violation: Expected exactly 11 columns, received {len(row)}"

    payload = {
        "secret": secret,
        "tab": tab,
        "row": row
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=20
        )

        if response.status_code == 403:
            return False, None, "HTTP 403 Access Denied. In Google Apps Script, set Deploy > Manage deployments > 'Who has access: Anyone'."

        if response.status_code != 200:
            return False, None, f"HTTP {response.status_code}: {response.text[:120]}"

        try:
            data = response.json()
        except Exception:
            return False, None, f"Invalid JSON response: {response.text[:120]}"

        if data.get("ok") is True:
            row_num = data.get("row")
            return True, row_num, None
        else:
            err = data.get("error") or data.get("message") or "Unknown Apps Script error"
            return False, None, str(err)

    except requests.exceptions.Timeout:
        return False, None, "Webhook connection timed out after 20 seconds"
    except requests.exceptions.RequestException as e:
        return False, None, f"Webhook network error: {str(e)}"


def read_rows(tab: str, limit: int = 10) -> Tuple[bool, List[List[Any]], Optional[str]]:
    """
    Reads rows from the specified tab via Google Apps Script Web App.
    Returns (ok, rows_list, error_message).
    """
    url, secret = get_apps_script_config()
    if not url:
        return False, [], "APPS_SCRIPT_URL is not configured in .env"

    params = {
        "secret": secret,
        "tab": tab,
        "limit": limit
    }

    try:
        response = requests.get(
            url,
            params=params,
            allow_redirects=True,
            timeout=20
        )

        if response.status_code == 403:
            return False, [], "HTTP 403 Access Denied. Set Apps Script deployment access to 'Anyone'."

        if response.status_code != 200:
            return False, [], f"HTTP {response.status_code}: {response.text[:120]}"

        try:
            data = response.json()
        except Exception:
            return False, [], f"Invalid JSON response: {response.text[:120]}"

        if data.get("ok") is True:
            return True, data.get("rows", []), None
        else:
            err = data.get("error") or data.get("message") or "Unknown error"
            return False, [], str(err)

    except requests.exceptions.Timeout:
        return False, [], "Webhook connection timed out"
    except requests.exceptions.RequestException as e:
        return False, [], f"Webhook network error: {str(e)}"


def check_webhook_health() -> Tuple[bool, str]:
    """Tests if the Apps Script webhook is reachable and returns valid JSON."""
    url, secret = get_apps_script_config()
    if not url:
        return False, "APPS_SCRIPT_URL is missing in .env"

    try:
        response = requests.get(
            url,
            params={"secret": secret, "tab": "Results", "limit": 1},
            allow_redirects=True,
            timeout=10
        )

        if response.status_code == 403:
            return False, "Access Denied (HTTP 403). In Google Apps Script, Deploy > Manage deployments > 'Who has access: Anyone'."

        if response.status_code != 200:
            return False, f"HTTP status {response.status_code}: {response.text[:100]}"

        data = response.json()
        if data.get("ok") is True:
            return True, "Reachable and operational"
        else:
            return False, data.get("error", "Returned ok: false")

    except requests.exceptions.RequestException as e:
        return False, f"Unreachable: {str(e)}"


def append_to_results(
    topic: str,
    version: str,
    scoring: Optional[Dict[str, Any]] = None,
    validation_status: str = "Passed",
    notes: str = ""
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Builds the 11-column row and sends to Results tab."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    scope_val = scoring.get("scope", {}).get("score", "") if scoring else ""
    res_val = scoring.get("resources", {}).get("score", "") if scoring else ""
    src_val = scoring.get("sources", {}).get("score", "") if scoring else ""
    out_val = scoring.get("outcomes", {}).get("score", "") if scoring else ""
    total_val = scoring.get("total", "") if scoring else ""
    verdict_val = scoring.get("verdict", "") if scoring else ""

    row = [
        timestamp,
        topic,
        version,
        str(scope_val),
        str(res_val),
        str(src_val),
        str(out_val),
        str(total_val),
        str(verdict_val),
        validation_status,
        notes
    ]

    return save_row("Results", row)


def append_to_tests(
    test_id: str,
    topic: str,
    version: str,
    scoring: Optional[Dict[str, Any]] = None,
    validation_status: str = "Passed",
    notes: str = ""
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Builds the exact 11-column row and sends to Tests tab (test_id stored in Notes)."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    scope_val = scoring.get("scope", {}).get("score", "") if scoring else ""
    res_val = scoring.get("resources", {}).get("score", "") if scoring else ""
    src_val = scoring.get("sources", {}).get("score", "") if scoring else ""
    out_val = scoring.get("outcomes", {}).get("score", "") if scoring else ""
    total_val = scoring.get("total", "") if scoring else ""
    verdict_val = scoring.get("verdict", "") if scoring else ""

    combined_notes = f"[{test_id}] {notes}" if notes else f"[{test_id}]"

    # Strictly 11 columns matching Results schema
    row = [
        timestamp,
        topic,
        version,
        str(scope_val),
        str(res_val),
        str(src_val),
        str(out_val),
        str(total_val),
        str(verdict_val),
        validation_status,
        combined_notes
    ]

    return save_row("Tests", row)


def get_history(limit: int = 10) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Fetches last N rows from Results tab and maps to dictionary."""
    ok, rows, err = read_rows("Results", limit=limit)
    if not ok:
        return False, [], err

    records = []
    data_rows = rows
    if data_rows and len(data_rows) > 0 and data_rows[0] and data_rows[0][0] == "Timestamp":
        data_rows = data_rows[1:]

    for r in reversed(data_rows):
        if len(r) >= 9:
            records.append({
                "timestamp": r[0] if len(r) > 0 else "",
                "topic": r[1] if len(r) > 1 else "",
                "version": r[2] if len(r) > 2 else "",
                "scope": r[3] if len(r) > 3 else "",
                "resources": r[4] if len(r) > 4 else "",
                "sources": r[5] if len(r) > 5 else "",
                "outcomes": r[6] if len(r) > 6 else "",
                "total": r[7] if len(r) > 7 else "",
                "verdict": r[8] if len(r) > 8 else "",
                "validation": r[9] if len(r) > 9 else "",
                "notes": r[10] if len(r) > 10 else ""
            })
            if len(records) >= limit:
                break

    return True, records, None


def get_tests_history(limit: int = 50) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Fetches rows from Tests tab and maps to dictionary."""
    ok, rows, err = read_rows("Tests", limit=limit)
    if not ok:
        return False, [], err

    records = []
    data_rows = rows
    if data_rows and len(data_rows) > 0 and data_rows[0] and data_rows[0][0] == "Timestamp":
        data_rows = data_rows[1:]

    for r in data_rows:
        if len(r) >= 9:
            notes_str = r[10] if len(r) > 10 else ""
            test_id = ""
            if notes_str.startswith("[") and "]" in notes_str:
                test_id = notes_str[1:notes_str.index("]")]
                notes_clean = notes_str[notes_str.index("]") + 1:].strip()
            else:
                notes_clean = notes_str

            records.append({
                "timestamp": r[0] if len(r) > 0 else "",
                "test_id": test_id,
                "topic": r[1] if len(r) > 1 else "",
                "version": r[2] if len(r) > 2 else "",
                "scope": r[3] if len(r) > 3 else "",
                "resources": r[4] if len(r) > 4 else "",
                "sources": r[5] if len(r) > 5 else "",
                "outcomes": r[6] if len(r) > 6 else "",
                "total": r[7] if len(r) > 7 else "",
                "verdict": r[8] if len(r) > 8 else "",
                "validation": r[9] if len(r) > 9 else "",
                "notes": notes_clean
            })

    return True, records, None
