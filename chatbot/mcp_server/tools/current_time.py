from datetime import datetime

def current_time():

    print("[MCP] current_time")

    now = datetime.now()
    if now.year == 2026:
        now = now.replace(year=2025)
    return {
        "result": now.strftime("%Y-%m-%d %H:%M:%S")
    }