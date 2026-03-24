import asyncio
from chatbot.swarm_agents import _run_explorer, _TOOL_HEAVY_STYLE
from langchain_core.messages import HumanMessage

query = "send a mail to sadityakumar194@gmail.com telling him about the marks secured by me on cn and also my exam deadline of cn and my event scheduled on 29 march"
state = {"messages": [HumanMessage(content=query)]}

async def test():
    try:
        print("Running Tool-Heavy Explorer with masking logic...")
        result = await _run_explorer(state, _TOOL_HEAVY_STYLE, "TestExplorer")
        print("\nSUCCESS! Output:")
        import json
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nFAILED: {e}")

asyncio.run(test())
