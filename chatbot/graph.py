import operator
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END

from chatbot.agents import (
    planner_agent, retriever_agent, executor_agent,
    critic_node, supervisor_node
)

class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    next_node: str
    critic_feedback: str
    critic_iterations: int

async def run_planner(state: MultiAgentState):
    res = await planner_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}

async def run_retriever(state: MultiAgentState):
    res = await retriever_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}

async def run_executor(state: MultiAgentState):
    res = await executor_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}

def route_from_supervisor(state: MultiAgentState):
    if state.get("next_node") == "FINISH":
        return END
    return state["next_node"]

def route_from_critic(state: MultiAgentState):
    feedback = state.get("critic_feedback", "")
    iterations = state.get("critic_iterations", 0)
    # Hard cap: after 2 retries always finish to prevent infinite loops
    if iterations >= 2 or "APPROVE" in feedback.upper():
        return END
    return "Supervisor"

builder = StateGraph(MultiAgentState)

builder.add_node("Supervisor", supervisor_node)
builder.add_node("Planner", run_planner)
builder.add_node("Retriever", run_retriever)
builder.add_node("Executor", run_executor)
builder.add_node("Critic", critic_node)

builder.add_edge(START, "Supervisor")

builder.add_conditional_edges(
    "Supervisor",
    route_from_supervisor,
    {"Planner": "Planner", "Retriever": "Retriever", "Executor": "Executor", "Critic": "Critic", END: END}
)

builder.add_edge("Planner", "Critic")
builder.add_edge("Retriever", "Critic")
builder.add_edge("Executor", "Critic")

builder.add_conditional_edges(
    "Critic",
    route_from_critic,
    {"Supervisor": "Supervisor", END: END}
)

graph = builder.compile()