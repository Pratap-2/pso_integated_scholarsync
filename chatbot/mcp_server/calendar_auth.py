import os
import json
import httplib2
import google_auth_httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "scholarsync26@gmail.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "service-account.json")

# Module-level cache — discovery doc is fetched only once per process lifetime.
_calendar_service = None


def get_calendar_service():
    global _calendar_service
    if _calendar_service is not None:
        return _calendar_service

    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if service_account_json:
        service_account_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
    else:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

    # Raised from 10 → 30s: token refresh + API call can easily exceed 10s
    authed_http = google_auth_httplib2.AuthorizedHttp(
        credentials,
        http=httplib2.Http(timeout=30)
    )

    _calendar_service = build("calendar", "v3", http=authed_http)
    return _calendar_service