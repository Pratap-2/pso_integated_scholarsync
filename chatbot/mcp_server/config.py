import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
#SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
#EMAIL_SENDER = os.getenv("EMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)