"""
chatbot/graph.py
─────────────────────────────────────────────────────────────────────────────
Dual-path LangGraph StateGraph — production multi-LLM architecture.

SIMPLE PATH:
  START → ComplexityAnalyzer → SimpleRetriever → ExecutorNode
        → ExploiterNode → PresentationAgent → Critic → END

COMPLEX PATH:
  START → ComplexityAnalyzer → Planner(GPT-4o)
        → ToolHeavyExplorer → MinimalExplorer → BalancedExplorer
        → FitnessEvaluator → ExecutorNode
        → ExploiterNode → PresentationAgent → Critic → END

Critic RETRY routes back to ExploiterNode (tools NOT re-run).
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END

from chatbot.agents import critic_node
from chatbot.swarm_agents import (
    complexity_analyzer_node,
    simple_retriever_node,
    planner_node,
    run_tool_heavy_explorer,
    run_minimal_explorer,
    run_balanced_explorer,
    fitness_evaluator_node,
    executor_node,
    exploiter_node,
    presentation_agent_node,
)


# ══════════════════════════════════════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════════════════════════════════════

class MultiAgentState(TypedDict):
    # ── Core conversation ────────────────────────────────────────────────────
    messages:           Annotated[list[BaseMessage], operator.add]

    # ── Complexity classification ────────────────────────────────────────────
    complexity:         str       # "simple" | "complex"
    complexity_reason:  str

    # ── Simple path ──────────────────────────────────────────────────────────
    simple_tool_call:   dict      # raw output from SimpleRetriever

    # ── Complex path — Planner ───────────────────────────────────────────────
    planner_goal:       str
    planner_steps:      list      # structured steps from Planner

    # ── Shared: execution plan (set by SimpleRetriever OR FitnessEvaluator) ──
    execution_plan:     list      # [{tool, parameters, order, requires_confirmation, use_output_as}]

    # ── UI requirement (set by SimpleRetriever OR Planner) ───────────────────
    ui_requirement:     dict      # {required: bool, type: str}

    # ── Pending confirmations (persisted across turns) ───────────────────────
    pending_email:          dict      # {to, subject, body} — set when draft shown; cleared after send
    pending_interview_topic: str      # set when interview card shown; cleared after open

    # ── Explorer outputs ─────────────────────────────────────────────────────
    explorer_outputs:   list      # 3 explorer dicts [{plan: [...], explorer: name}]

    # ── Execution results (cached across retries) ───────────────────────────
    execution_results:  list      # [{tool, skipped, result, result_str, use_output_as}]

    # ── Synthesis ────────────────────────────────────────────────────────────
    exploiter_text:     str       # logical text from ExploiterNode
    final_response:     str       # formatted text from PresentationAgent

    # ── Critic ───────────────────────────────────────────────────────────────
    critic_feedback:    str
    critic_iterations:  int


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def route_complexity(state: MultiAgentState):
    if state.get("complexity") == "complex":
        return "Planner"
    return "SimpleRetriever"


def route_critic(state: MultiAgentState):
    feedback:   str = state.get("critic_feedback", "") or ""  # type: ignore[assignment]
    iterations: int = state.get("critic_iterations", 0) or 0  # type: ignore[assignment]
    approved   = iterations >= 2 or "APPROVE" in feedback.upper()
    return END if approved else "ExploiterNode"


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

builder = StateGraph(MultiAgentState)

# ── Nodes ─────────────────────────────────────────────────────────────────────
builder.add_node("ComplexityAnalyzer",   complexity_analyzer_node)
builder.add_node("SimpleRetriever",      simple_retriever_node)
builder.add_node("Planner",              planner_node)
builder.add_node("ToolHeavyExplorer",    run_tool_heavy_explorer)
builder.add_node("MinimalExplorer",      run_minimal_explorer)
builder.add_node("BalancedExplorer",     run_balanced_explorer)
builder.add_node("FitnessEvaluator",     fitness_evaluator_node)
builder.add_node("ExecutorNode",         executor_node)
builder.add_node("ExploiterNode",        exploiter_node)
builder.add_node("PresentationAgent",    presentation_agent_node)
builder.add_node("Critic",               critic_node)

# ── Entry ─────────────────────────────────────────────────────────────────────
builder.add_edge(START, "ComplexityAnalyzer")

# ── Complexity branching ────────────────────────────────────────────────────
builder.add_conditional_edges(
    "ComplexityAnalyzer",
    route_complexity,
    {"SimpleRetriever": "SimpleRetriever", "Planner": "Planner"},
)

# ── Simple path ──────────────────────────────────────────────────────────────
builder.add_edge("SimpleRetriever", "ExecutorNode")

# ── Complex path: Planner → sequential explorers → fitness → executor ────────
builder.add_edge("Planner",            "ToolHeavyExplorer")
builder.add_edge("ToolHeavyExplorer",  "MinimalExplorer")
builder.add_edge("MinimalExplorer",    "BalancedExplorer")
builder.add_edge("BalancedExplorer",   "FitnessEvaluator")
builder.add_edge("FitnessEvaluator",   "ExecutorNode")

# ── Shared tail: execution → synthesis → presentation → critic ───────────────
builder.add_edge("ExecutorNode",       "ExploiterNode")
builder.add_edge("ExploiterNode",      "PresentationAgent")
builder.add_edge("PresentationAgent",  "Critic")

# ── Critic routing ────────────────────────────────────────────────────────────
builder.add_conditional_edges(
    "Critic",
    route_critic,
    {"ExploiterNode": "ExploiterNode", END: END},
)

# ── Compile (checkpointer injected at runtime by memory.py) ──────────────────
graph = builder.compile()