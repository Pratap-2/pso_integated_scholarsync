from datetime import datetime

def current_time():

    print("[MCP] current_time")

    return {
        "result": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }