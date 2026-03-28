import requests

API_URL = "https://scholarsync-chat-uh1x.onrender.com/api/connect/all?studentId=test-user-123"

def get_student_connections():
    print("[MCP] get_student_connections")
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()

        cleaned = []
        for item in data:
            expert = item.get("expert", {})
            cleaned.append({
                "name": expert.get("name"),
                "subject": expert.get("subject"),
                "description": expert.get("description"),
                "chat_url": item.get("fullUrl")
            })

        return {
            "status": "success",
            "connections": cleaned
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
