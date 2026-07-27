from __future__ import annotations

import json
from typing import Any
from urllib import error, request

import streamlit as st


def log_usage_event(payload: dict[str, Any]) -> tuple[bool, str]:
    """
    Send one generation record to the private Google Sheet through
    the Google Apps Script web app.

    Logging failures never stop DXF/PDF generation.
    """
    try:
        analytics_secrets = st.secrets["analytics"]
        logger_url = str(analytics_secrets["logger_url"]).strip()
        logger_token = str(analytics_secrets["logger_token"])
    except Exception:
        return False, "Google Sheets analytics is not configured in Streamlit Secrets."

    if not logger_url:
        return False, "The Google Apps Script URL is empty."

    body = {
        **payload,
        "token": logger_token,
    }

    http_request = request.Request(
        logger_url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MGALS-Trimline-App/1.0",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=10) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        return False, f"Google Sheets logger returned HTTP {exc.code}."
    except error.URLError as exc:
        return False, f"Could not contact Google Sheets logger: {exc.reason}"
    except TimeoutError:
        return False, "Google Sheets logger timed out."
    except Exception as exc:
        return False, f"Unexpected Google Sheets logging error: {exc}"

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        return False, "Google Sheets logger returned an invalid response."

    if result.get("ok") is True:
        return True, ""

    return False, str(result.get("error", "Unknown Google Sheets logger error."))
