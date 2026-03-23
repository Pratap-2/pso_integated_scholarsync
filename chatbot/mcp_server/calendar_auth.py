import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():

    creds = None
    workspace_dir = r"c:\Users\HP\OneDrive\Desktop\scholar_sync"
    token_path = os.path.join(workspace_dir, "token.pickle")
    creds_path = os.path.join(workspace_dir, "credentials.json")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            if not os.path.exists(creds_path):
                creds_path = os.path.join(workspace_dir, "chatbot", "credentials.json")
                print("Loading credentials from:", creds_path)
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)
