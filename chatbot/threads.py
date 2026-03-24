# chatbot/threads.py

from . import memory
import psycopg
import psycopg.rows


async def _get_conn():
    """Return a live connection, reconnecting if closed."""
    conn = memory.chatbot.checkpointer.conn
    if conn.closed:
        conninfo = conn.conninfo
        new_conn = await psycopg.AsyncConnection.connect(
            conninfo, row_factory=psycopg.rows.dict_row
        )
        memory.chatbot.checkpointer.conn = new_conn
        return new_conn
    return conn


async def get_all_threads():

    if memory.chatbot is None:
        return {}

    threads = {}

    try:
        conn = await _get_conn()

        async with conn.cursor() as cur:

            await cur.execute("""
                SELECT DISTINCT thread_id
                FROM checkpoints
                ORDER BY thread_id DESC
            """)

            rows = await cur.fetchall()

            for row in rows:

                thread_id = row["thread_id"]

                try:
                    state = await memory.chatbot.aget_state({
                        "configurable": {
                            "thread_id": thread_id
                        }
                    })

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

    except psycopg.OperationalError as e:
        print("DB connection error, retrying:", e)
        # Force a fresh connection and retry once
        conninfo = memory.chatbot.checkpointer.conn.conninfo
        memory.chatbot.checkpointer.conn = await psycopg.AsyncConnection.connect(
            conninfo, row_factory=psycopg.rows.dict_row
        )
        return await get_all_threads()

    return threads


async def delete_thread(thread_id: str):

    if memory.chatbot is None:
        return False

    try:
        conn = await _get_conn()

        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (thread_id,)
            )

        await conn.commit()

    except psycopg.OperationalError as e:
        print("DB connection error on delete, retrying:", e)
        conninfo = memory.chatbot.checkpointer.conn.conninfo
        memory.chatbot.checkpointer.conn = await psycopg.AsyncConnection.connect(
            conninfo, row_factory=psycopg.rows.dict_row
        )
        return await delete_thread(thread_id)

    return True