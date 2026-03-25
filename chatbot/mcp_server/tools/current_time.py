from datetime import datetime

def current_time():

    print("[MCP] current_time")

    now = datetime.now()
    return {
        "result": now.strftime("%Y-%m-%d %H:%M:%S")
    }