"""
chatbot/graph.py
───────────────────────────────────────────────────────────────────────────────
Dual-path Hybrid LangGraph Architecture for ScholarSync.

PIPELINE A – SIMPLE  (≤ 1 tool / no multi-step reasoning)
  START → ComplexityAnalyzer → Supervisor → {Planner|Retriever|Executor}
        → Critic → Supervisor | END

PIPELINE B – COMPLEX (≥ 2 tools / multi-step reasoning)
  START → ComplexityAnalyzer
        → ToolHeavyExplorer → ReasoningHeavyExplorer → ConciseExplorer
        → FitnessEvaluator → Critic → Exploiter
        → ActionPlanner → ExecutionEngine → END

STRICT GUARANTEES:
  • Existing agents, prompts, and tools are NOT modified.
  • Simple pipeline behaviour is EXACTLY unchanged.
  • Explorers NEVER execute tools.
  • Execution Engine runs each unique action EXACTLY ONCE.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END

# ── Existing agents/nodes (UNCHANGED – imported, never re-defined) ────────────
from chatbot.agents import (
    planner_agent,
    retriever_agent,
    executor_agent,
    critic_node,        # shared by both pipelines
    supervisor_node,
)

# ── New swarm nodes ───────────────────────────────────────────────────────────
from chatbot.swarm_agents import (
    complexity_analyzer_node,
    run_tool_heavy_explorer,
    run_reasoning_heavy_explorer,
    run_concise_explorer,
    fitness_evaluator_node,
    exploiter_node,
    action_planner_node,
    execution_engine_node,
)


# ══════════════════════════════════════════════════════════════════════════════
# STATE DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

class MultiAgentState(TypedDict):
    # ── EXISTING fields (DO NOT CHANGE) ──────────────────────────────────────
    messages:           Annotated[list[BaseMessage], operator.add]
    next_node:          str
    critic_feedback:    str
    critic_iterations:  int

    # ── NEW swarm fields ──────────────────────────────────────────────────────
    complexity:              str    # "simple" | "complex" | ""
    complexity_reason:       str    # human-readable reason from analyzer
    explorer_outputs:        list   # accumulated list of 3 explorer dicts
    best_candidate:          dict   # winning explorer output (fitness winner)
    best_candidate_index:    int    # index of winner in explorer_outputs
    final_actions:           list   # deduplicated, ordered actions to execute
    swarm_critic_iterations: int    # reserved for future swarm-specific logic


# ══════════════════════════════════════════════════════════════════════════════
# EXISTING AGENT RUNNER WRAPPERS  (unchanged logic – only wrapped in async fns)
# ══════════════════════════════════════════════════════════════════════════════

async def run_planner(state: MultiAgentState):
    res = await planner_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}


async def run_retriever(state: MultiAgentState):
    res = await retriever_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}


async def run_executor(state: MultiAgentState):
    res = await executor_agent.ainvoke({"messages": state["messages"]})
    return {"messages": res["messages"][len(state["messages"]):]}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def route_from_complexity(state: MultiAgentState):
    """
    Route after Complexity Analyzer.
      complex → swarm pipeline (ToolHeavyExplorer is always first)
      simple  → existing pipeline (Supervisor)
    """
    if state.get("complexity") == "complex":
        return "ToolHeavyExplorer"
    return "Supervisor"


def route_from_supervisor(state: MultiAgentState):
    """
    Existing supervisor routing — completely unchanged logic.
    """
    if state.get("next_node") == "FINISH":
        return END
    return state["next_node"]


def route_from_critic_hybrid(state: MultiAgentState):
    """
    Unified Critic routing that covers BOTH pipelines.

    Simple pipeline  → mirrors original route_from_critic exactly:
        APPROVE / cap → END
        retry         → Supervisor

    Complex pipeline → swarm variant:
        APPROVE / cap → Exploiter  (begin post-processing)
        retry         → ToolHeavyExplorer  (re-run all three explorers)
    """
    feedback    = state.get("critic_feedback", "")
    iterations  = state.get("critic_iterations", 0)
    complexity  = state.get("complexity", "simple")

    # Hard cap at 2 iterations (same rule as original system)
    approved = (iterations >= 2) or ("APPROVE" in feedback.upper())

    if complexity == "complex":
        return "Exploiter" if approved else "ToolHeavyExplorer"
    else:
        # ── Original simple-path logic (preserved verbatim) ────────────────
        return END if approved else "Supervisor"


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

builder = StateGraph(MultiAgentState)

# ── Register existing nodes (names identical to original graph) ───────────────
builder.add_node("Supervisor",          supervisor_node)
builder.add_node("Planner",             run_planner)
builder.add_node("Retriever",           run_retriever)
builder.add_node("Executor",            run_executor)
builder.add_node("Critic",              critic_node)       # SHARED by both paths

# ── Register new swarm nodes ─────────────────────────────────────────────────
builder.add_node("ComplexityAnalyzer",       complexity_analyzer_node)
builder.add_node("ToolHeavyExplorer",        run_tool_heavy_explorer)
builder.add_node("ReasoningHeavyExplorer",   run_reasoning_heavy_explorer)
builder.add_node("ConciseExplorer",          run_concise_explorer)
builder.add_node("FitnessEvaluator",         fitness_evaluator_node)
builder.add_node("Exploiter",                exploiter_node)
builder.add_node("ActionPlanner",            action_planner_node)
builder.add_node("ExecutionEngine",          execution_engine_node)

# ── Entry point ───────────────────────────────────────────────────────────────
builder.add_edge(START, "ComplexityAnalyzer")

# ── Complexity branching ──────────────────────────────────────────────────────
builder.add_conditional_edges(
    "ComplexityAnalyzer",
    route_from_complexity,
    {
        "Supervisor":        "Supervisor",        # simple path
        "ToolHeavyExplorer": "ToolHeavyExplorer", # complex path
    },
)

# ── Simple pipeline edges (IDENTICAL to original graph) ──────────────────────
builder.add_conditional_edges(
    "Supervisor",
    route_from_supervisor,
    {
        "Planner":   "Planner",
        "Retriever": "Retriever",
        "Executor":  "Executor",
        "Critic":    "Critic",
        END:         END,
    },
)
builder.add_edge("Planner",   "Critic")
builder.add_edge("Retriever", "Critic")
builder.add_edge("Executor",  "Critic")

# ── Swarm explorer chain (sequential — each appends to explorer_outputs) ──────
builder.add_edge("ToolHeavyExplorer",      "ReasoningHeavyExplorer")
builder.add_edge("ReasoningHeavyExplorer", "ConciseExplorer")
builder.add_edge("ConciseExplorer",        "FitnessEvaluator")

# ── Fitness Evaluator → Critic (shared node) ──────────────────────────────────
builder.add_edge("FitnessEvaluator", "Critic")

# ── Unified Critic routing (handles both simple and complex paths) ─────────────
builder.add_conditional_edges(
    "Critic",
    route_from_critic_hybrid,
    {
        # Simple path destinations
        "Supervisor":        "Supervisor",
        END:                 END,
        # Complex path destinations
        "ToolHeavyExplorer": "ToolHeavyExplorer",
        "Exploiter":         "Exploiter",
    },
)

# ── Swarm post-processing chain ───────────────────────────────────────────────
builder.add_edge("Exploiter",      "ActionPlanner")
builder.add_edge("ActionPlanner",  "ExecutionEngine")
builder.add_edge("ExecutionEngine", END)

# ── Compile ───────────────────────────────────────────────────────────────────
graph = builder.compile()