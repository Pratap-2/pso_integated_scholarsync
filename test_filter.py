import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from chatbot.llm import llm, tool_llm
from chatbot.swarm_agents import _COMPLEXITY_SYSTEM, _EXPLORER_TEMPLATE, _EMAIL_DRAFT_SYSTEM
from chatbot.agents import SUPERVISOR_PROMPT

query = "send a mail to sadityakumar194@gmail.com telling him about the marks secured by me on cn and also my exam deadline of cn and my event scheduled on 29 march"

async def test_llm():
    print("1. Testing Complexity Analyzer prompt...")
    try:
        await llm.ainvoke([SystemMessage(content=_COMPLEXITY_SYSTEM), HumanMessage(content=f"User query: {query}")])
        print("   -> Success")
    except Exception as e:
        print(f"   -> FAILED: {e}")

    print("\n2. Testing Supervisor prompt...")
    try:
        from chatbot.agents import RouteResponse
        structured = llm.with_structured_output(RouteResponse)
        await structured.ainvoke([SystemMessage(content=SUPERVISOR_PROMPT), HumanMessage(content=query)])
        print("   -> Success")
    except Exception as e:
        print(f"   -> FAILED: {e}")

    print("\n3. Testing Explorer prompt...")
    try:
        from chatbot.swarm_agents import _TOOL_HEAVY_STYLE, KNOWN_TOOL_NAMES
        sys_msg = _EXPLORER_TEMPLATE.format(style_instructions=_TOOL_HEAVY_STYLE, tool_names=", ".join(KNOWN_TOOL_NAMES), query=query)
        await tool_llm.ainvoke([SystemMessage(content=sys_msg), HumanMessage(content=f"Query to process: {query}")])
        print("   -> Success")
    except Exception as e:
        print(f"   -> FAILED: {e}")

    print("\n4. Testing Email Draft prompt...")
    try:
        draft_prompt = f"User request: {query}\n\nData fetched from tools:\nNone\n\nCompose a professional email to the relevant professor using this data."
        await llm.ainvoke([SystemMessage(content=_EMAIL_DRAFT_SYSTEM), HumanMessage(content=draft_prompt)])
        print("   -> Success")
    except Exception as e:
        print(f"   -> FAILED: {e}")

asyncio.run(test_llm())
