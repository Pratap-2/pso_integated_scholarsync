from datetime import datetime
import pytz
from ..calendar_auth import get_calendar_service

IST = pytz.timezone("Asia/Kolkata")


def create_calendar_event(data):

    title = data["title"]
    start_time = data["start_time"]
    end_time = data["end_time"]

    print("[MCP] create_calendar_event ->", title)

    try:

        service = get_calendar_service()

        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        if start_dt.tzinfo is None:
            start_dt = IST.localize(start_dt)

        if end_dt.tzinfo is None:
            end_dt = IST.localize(end_dt)

        event = {
            "summary": title,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            }
        }

        event = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()

        return {
            "status": "success",
            "event_id": event.get("id"),
            "event_url": event.get("htmlLink")
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }