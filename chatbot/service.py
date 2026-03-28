"""
chatbot/service.py
─────────────────────────────────────────────────────────────────────────────
Streaming chat service — planner-driven UI injection.

Changes from previous version:
  - Response read from state["final_response"] (set by PresentationAgent)
    instead of scanning messages for the last AI message.
  - UI blocks injected deterministically from state["ui_requirement"]
    + state["execution_results"] via ui_builders.py.
  - Old _inject_ui_blocks / _extract_tool_result helpers removed.
"""

import asyncio
import json

from langchain_core.messages import HumanMessage
from langsmith import traceable
from langchain_core.tracers.context import tracing_v2_enabled

from . import memory
from .config import threads
from .ui_builders import build_ui_block, get_ui_tool_name


@traceable(name="ScholarSync Chat")
async def chat_stream(user_message: str, thread_id: str):
    if thread_id not in threads:
        threads[thread_id] = user_message[:30]

    state  = {"messages": [HumanMessage(content=user_message)]}
    config = {"configurable": {"thread_id": thread_id}}

    with tracing_v2_enabled(project_name="ScholarSync"):

        try:
            final_state = await asyncio.wait_for(
                memory.chatbot.ainvoke(state, config=config),
                timeout=200,
            )
        except asyncio.TimeoutError:
            yield "⚠️ The agent took too long to respond. Please try again."
            return
        except Exception as e:
            yield f"⚠️ An error occurred: {str(e)[:200]}"
            return

        # ── 1. Read the formatted response from PresentationAgent ────────────
        final_response: str = final_state.get("final_response", "")

        if not final_response:
            yield "⚠️ The agent was unable to produce a response. Please try again."
            return

        # ── 2. Planner-driven UI injection ───────────────────────────────────
        ui_req  = final_state.get("ui_requirement") or {}
        ui_block = ""

        if ui_req.get("required", False):
            ui_type   = ui_req.get("type", "none")
            tool_name = get_ui_tool_name(ui_type)

            raw_data = None
            for r in final_state.get("execution_results", []):
                if r.get("tool") == tool_name and not r.get("skipped"):
                    raw_data = r.get("result")
                    break

            if raw_data is not None:
                ui_block = build_ui_block(ui_type, raw_data)

        # Build final streamed text — UI block first, then formatted response
        output_text = (ui_block + "\n\n" + final_response).strip() if ui_block else final_response

        # ── 3. Stream in chunks ──────────────────────────────────────────────
        yield "\n\n**Agent Network**:\n"
        chunk_size = 15
        for i in range(0, len(output_text), chunk_size):
            yield output_text[i: i + chunk_size]
            await asyncio.sleep(0.01)