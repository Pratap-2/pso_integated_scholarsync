from ..calendar_auth import get_calendar_service
from datetime import datetime, timezone


def delete_event_by_title(data):

    title = data["title"].strip().lower()

    print("[MCP] delete_event_by_title ->", title)

    try:

        service = get_calendar_service()

        # Get upcoming events
        events_result = service.events().list(
            calendarId="primary",
            timeMin=datetime.now(timezone.utc).isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        for event in events:

            summary = event.get("summary", "").strip().lower()

            # Debug print
            print("Checking event:", summary)

            if title in summary:

                event_id = event.get("id")

                service.events().delete(
                    calendarId="primary",
                    eventId=event_id
                ).execute()

                print("Deleted event:", summary)

                return {
                    "status": "success",
                    "message": f"Event '{event.get('summary')}' deleted successfully"
                }

        return {
            "status": "not_found",
            "message": "No matching event found"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }