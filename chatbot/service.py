from langchain_core.messages import HumanMessage
from langsmith import traceable
from langchain_core.tracers.context import tracing_v2_enabled
import asyncio
import json

from . import memory
from .config import threads


def _extract_tool_result(messages, tool_name: str):
    """Scan message history for a ToolMessage from a given tool and return its content."""
    for msg in reversed(messages):
        msg_type = getattr(msg, "type", "")
        msg_name = getattr(msg, "name", "") or ""
        if msg_type == "tool" and tool_name in msg_name:
            try:
                return json.loads(msg.content)
            except Exception:
                return None
    return None


def _inject_ui_blocks(final_ai_message: str, messages: list) -> str:
    """If the LLM response is missing ui blocks, inject them from raw tool results."""
    injected = False
    result = ""

    # -------- Assignments --------
    if "```ui_assignments" not in final_ai_message:
        asgn_data = _extract_tool_result(messages, "get_assignments_tool")
        if asgn_data and isinstance(asgn_data, list) and len(asgn_data) > 0:
            ui_list = []
            for a in asgn_data:
                ui_list.append({
                    "title": a.get("title", "Untitled"),
                    "subject": a.get("subject", ""),
                    "description": a.get("description", ""),
                    "deadline": a.get("due_date", ""),
                    "assignmentDoc": a.get("document_url", "")
                })
            block = "```ui_assignments\n" + json.dumps(ui_list, indent=2) + "\n```"
            result = block
            injected = True

    # -------- Materials --------
    if "```ui_materials" not in final_ai_message:
        mat_data = _extract_tool_result(messages, "get_materials_tool")
        if mat_data and isinstance(mat_data, list) and len(mat_data) > 0:
            ui_list = []
            for m in mat_data:
                ui_list.append({
                    "title": m.get("title", "Untitled"),
                    "subject": m.get("subject", ""),
                    "description": m.get("description", ""),
                    "materialLink": m.get("document_url", "")
                })
            block = "```ui_materials\n" + json.dumps(ui_list, indent=2) + "\n```"
            result = block
            injected = True

    # If we injected a block, replace the full LLM text entirely (no duplicate text)
    if injected:
        return result

    # Otherwise keep the original (already has the block or is a normal reply)
    return final_ai_message


@traceable(name="ScholarSync Chat")
async def chat_stream(user_message: str, thread_id: str):

    if thread_id not in threads:
        threads[thread_id] = user_message[:30]

    state = {
        "messages": [HumanMessage(content=user_message)]
    }

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    with tracing_v2_enabled(project_name="ScholarSync"):

        # Snapshot how many messages exist BEFORE this turn so we only
        # scan NEW tool-call messages when injecting ui blocks.
        try:
            pre_state = await memory.chatbot.aget_state(config)
            prev_msg_count = len(pre_state.values.get("messages", [])) if pre_state and pre_state.values else 0
        except Exception:
            prev_msg_count = 0

        try:
            # Hard 90-second timeout — prevents infinite spinning
            final_state = await asyncio.wait_for(
                memory.chatbot.ainvoke(state, config=config),
                timeout=90
            )
        except asyncio.TimeoutError:
            yield "⚠️ The agent took too long to respond. Please try again or rephrase your question."
            return
        except Exception as e:
            yield f"⚠️ An error occurred: {str(e)[:200]}"
            return
        
        # Extract the final AI message (the one right before Critic's final APPROVE)
        final_ai_message = ""
        for msg in reversed(final_state["messages"]):
            if getattr(msg, "type", "") == "ai" and msg.content:
                # Skip the Critic's APPROVE message
                if "APPROVE" not in msg.content.upper() and "CRITIC FEEDBACK" not in msg.content:
                    final_ai_message = msg.content
                    break
                    
        if not final_ai_message:
            yield "⚠️ The agent was unable to produce a response. Please try again."
            return

        # Only look at messages added in THIS turn (not the full history)
        new_messages = final_state["messages"][prev_msg_count:]

        # Inject ui_assignments / ui_materials blocks if the LLM didn't format them
        final_ai_message = _inject_ui_blocks(final_ai_message, new_messages)

        yield f"\n\n🤖 **Agent Network**:\n"
        
        # Stream the approved text so the frontend UI types it out smoothly
        chunk_size = 15
        for i in range(0, len(final_ai_message), chunk_size):
            yield final_ai_message[i:i+chunk_size]
            await asyncio.sleep(0.01)
