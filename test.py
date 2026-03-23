import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from chatbot.memory import init_chatbot
from chatbot.service import chat_stream

async def main():
    await init_chatbot()
    print("Chatbot initialized. Streaming:")
    async for chunk in chat_stream("Hello, who are you?", "test_thread_02"):
        print(chunk, end='', flush=True)

if __name__ == "__main__":
    asyncio.run(main())
