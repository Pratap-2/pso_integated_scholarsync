import os
import sys
import asyncio
from dotenv import load_dotenv

# Load env first
load_dotenv()

# LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ScholarSync"

# Windows async fix (skip on Linux/Docker)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DATABASE_URL = os.getenv("DATABASE_URL")

# Thread title cache
threads = {}
