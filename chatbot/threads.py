# chatbot/threads.py

# IMPORTANT: import module, NOT variable
from . import memory


async def get_all_threads():

    # Ensure chatbot is initialized
    if memory.chatbot is None:
        return {}

    threads = {}

    conn = memory.chatbot.checkpointer.conn

    async with conn.cursor() as cur:

        # Fetch all thread IDs
        await cur.execute("""
            SELECT DISTINCT thread_id
            FROM checkpoints
            ORDER BY thread_id DESC
        """)

        rows = await cur.fetchall()

        for row in rows:

            thread_id = row["thread_id"]

            try:

                # Load conversation state
                state = await memory.chatbot.aget_state({
                    "configurable": {
                        "thread_id": thread_id
                    }
                })

                # Extract first message as title
                if (
                    state
                    and state.values
                    and "messages" in state.values
                    and len(state.values["messages"]) > 0
                ):
                    first_msg = state.values["messages"][0].content

                    threads[thread_id] = first_msg[:40]

                else:
                    threads[thread_id] = "New Chat"

            except Exception as e:

                print("Thread load error:", e)

                threads[thread_id] = "New Chat"

    return threads


async def delete_thread(thread_id: str):

    if memory.chatbot is None:
        return False

    conn = memory.chatbot.checkpointer.conn

    async with conn.cursor() as cur:

        await cur.execute(
            "DELETE FROM checkpoints WHERE thread_id = %s",
            (thread_id,)
        )

    await conn.commit()

    return True
