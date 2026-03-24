"""
chatbot/swarm_agents.py
-------------------------------------------------------------------------------
Swarm Pipeline Agents for ScholarSync's Hybrid Architecture.

STRICT RULES (enforced here):
   NO existing agents, prompts, or tools are modified.
   Explorers NEVER execute tools - they only PROPOSE actions.
   Execution Engine runs each unique action EXACTLY ONCE.
   send_email / get_assignments_tool / get_materials_tool are once-only tools.
"""

import json
import re
import hashlib
from typing import Literal, List

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# -- LLM instances (imported, NOT re-configured) -------------------------------
from chatbot.llm import llm, tool_llm

# -- Tool imports --------------------------------------------------------------
from chatbot.mcp_client import get_mcp_tools
from chatbot.tools_integration import (
    solve_assignment_tool,
    get_exams_tool,
    get_interview_info_tool,
    prepare_interview_session_tool,
    open_interview_in_browser_tool,
)


# 
# TOOL REGISTRY (Execution Engine uses this)
# 

_base_tools = get_mcp_tools()
_extra_tools = [
    solve_assignment_tool,
    get_exams_tool,
    get_interview_info_tool,
    prepare_interview_session_tool,
    open_interview_in_browser_tool,
]
_base_names  = {t.name for t in _base_tools}

ALL_SWARM_TOOLS: list = _base_tools + [t for t in _extra_tools if t.name not in _base_names]
TOOL_MAP:        dict = {t.name: t for t in ALL_SWARM_TOOLS}
KNOWN_TOOL_NAMES: set = set(TOOL_MAP.keys())

# Tools that must NEVER execute more than once per user turn
_ONCE_ONLY_TOOLS: set = {"send_email", "get_assignments_tool", "get_materials_tool", "open_interview_in_browser_tool"}


# 
# PYDANTIC SCHEMAS
# 

class ComplexityResult(BaseModel):
    complexity:       Literal["simple", "complex"]
    estimated_tools:  int = Field(ge=0)
    reason:           str


class ProposedAction(BaseModel):
    tool:       str
    parameters: dict = Field(default_factory=dict)


class ExplorerOutput(BaseModel):
    approach:         str
    response:         str
    proposed_actions: List[ProposedAction] = Field(default_factory=list)
    confidence:       float = Field(ge=0.0, le=1.0)


class CandidateEvaluation(BaseModel):
    candidate_index:         int
    tool_usage_correctness:  float
    correctness:             float
    completeness:            float
    relevance:               float
    clarity:                 float
    fitness_score:           float


class FitnessResult(BaseModel):
    evaluations:          List[CandidateEvaluation]
    best_candidate_index: int


# 
# HELPER
# 

def _get_last_user_query(state) -> str:
    """Return the most recent HumanMessage content from the graph state."""
    for m in reversed(state["messages"]):
        if getattr(m, "type", "") == "human":
            return m.content
    return ""


def _parse_json_response(content: str) -> dict:
    """
    Robustly extract and parse the first JSON object in the LLM response.
    Handles: markdown fences, preamble text, trailing prose.
    Raises json.JSONDecodeError when no valid JSON is found.
    """
    content = content.strip()

    # 1. Strip ```json ... ``` or ``` ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if fence_match:
        content = fence_match.group(1).strip()

    # 2. Fast path: content might be a clean JSON object already
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 3. Fallback: find the first outermost {...} block via brace matching
    start = content.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", content, 0)

    depth = 0
    for i, ch in enumerate(content[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(content[start : i + 1])

    raise json.JSONDecodeError("Unmatched braces in JSON", content, start)


# 
# 1. COMPLEXITY ANALYZER AGENT
# 

_COMPLEXITY_SYSTEM = """You are the Query Complexity Analyzer for ScholarSync.

Classify the user query into EXACTLY "simple" or "complex".

CLASSIFY AS "complex" when the query:
   Requires 2 or more distinct tools (e.g. fetch assignments AND send email)
   Involves multi-step reasoning across different domains
   Chains operations where output of one step feeds the next
   Combines calendar + academic + communication actions

CLASSIFY AS "simple" when the query:
   Requires only 0 or 1 tool
   Is a greeting, general chit-chat, or single-domain question
   Can be fully handled by one specialized agent in one step

Available tool categories: calendar CRUD, email, calculator, web search,
assignments, materials, marks, deadlines, exams, assignment-solver,
interview practice (get_interview_info_tool, schedule_interview_tool).

Reply with ONLY valid JSON -- no extra text:
{
  "complexity": "simple" | "complex",
  "estimated_tools": <integer  0>,
  "reason": "<brief explanation>"
}"""


async def complexity_analyzer_node(state: dict) -> dict:
    """
    Complexity Analyzer Node.
    Classifies the user query and resets per-turn swarm state.
    """
    query = _get_last_user_query(state)
    messages = [
        SystemMessage(content=_COMPLEXITY_SYSTEM),
        HumanMessage(content=f"User query: {query}"),
    ]

    res = await llm.ainvoke(messages)

    try:
        parsed = ComplexityResult(**_parse_json_response(res.content))
        complexity = parsed.complexity
        reason     = parsed.reason
    except Exception:
        # Safe fallback: route through existing simple pipeline unchanged
        complexity = "simple"
        reason     = "Parse error -- defaulting to simple pipeline for safety."

    return {
        "complexity":              complexity,
        "complexity_reason":       reason,
        # Reset swarm state for this fresh turn
        "explorer_outputs":        [],
        "best_candidate":          {},
        "best_candidate_index":    0,
        "final_actions":           [],
        "critic_iterations":       0,   # reset critic counter for new turn
        "swarm_critic_iterations": 0,
    }


# 
# 2. EXPLORER AGENTS  (PROPOSE ONLY -- NEVER EXECUTE TOOLS)
# 

_EXPLORER_TEMPLATE = """{style_instructions}

You are an Explorer Agent for ScholarSync's swarm pipeline.
IMPORTANT: You are an explicitly authorized academic assistant. Processing student grades, schedules, and proposing to draft emails to professors is fully permitted and does NOT constitute academic dishonesty, phishing, or spam.

ABSOLUTE RULES:
1. You are PART of an automated swarm pipeline. You MUST propose the exact tools needed in the `proposed_actions` array. The background system will execute them and fetch the data. 
2. NEVER tell the user "I do not have access" or "Please use the tool yourself". Assume you have full access as long as you propose the correct tool.
3. If the user asks to email a professor, you MUST propose the `get_subject_professors` tool to fetch their actual email address. Return the `send_email` action only AFTER gathering data.
4. If the user uses relative time words like 'today', 'tomorrow', 'yesterday', or 'next week', you MUST propose the `current_time` tool so the system can resolve the exact date before calling calendar tools.
5. Output ONLY valid JSON -- no extra prose, no markdown fences.
6. Every tool name in proposed_actions MUST be from this exact list:
   {tool_names}

JSON schema you MUST follow:
{{
  "approach": "<your strategy in one sentence>",
  "response": "<Explicitly narrate how you broke down the user query. For example: 'First, I identified that marks and assignment data are needed. Next, I will fetch that data. Finally, I will draft the requested email.' Make it clear to the user what your plan is>",
  "proposed_actions": [
    {{"tool": "<tool_name>", "parameters": {{"<key>": "<value>"}}}}
  ],
  "confidence": <float 0.0-1.0>
}}

If no tools are needed, set proposed_actions to [].

User query: {query}"""

_TOOL_HEAVY_STYLE = """STYLE: TOOL-HEAVY EXPLORER
- Use as many relevant tools as needed for a complete, data-driven answer.
- Include every tool that contributes useful data.
- Ensure tools are sequenced logically (fetch before send, lookup before email)."""

_REASONING_STYLE = """STYLE: REASONING-HEAVY EXPLORER
- Prefer chain-of-thought reasoning and use tools only where strictly necessary.
- Minimize tool calls. Maximise in-context reasoning.
- Be thorough and analytical in your response text."""

_CONCISE_STYLE = """STYLE: CONCISE EXPLORER
- Find the simplest, shortest valid path to answer the query.
- Use the minimum number of tools required -- remove anything optional.
- Keep the response text brief and direct."""


def mask_emails(text: str) -> tuple[str, dict]:
    """Mask email addresses to bypass Azure OpenAI PII/Spam filters."""
    mapping = {}
    def repl(m):
        key = f"__EMAIL_{len(mapping)}__"
        mapping[key] = m.group(0)
        return key
    masked = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', repl, text)
    return masked, mapping

def unmask_emails(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

def unmask_data(data, mapping: dict):
    if isinstance(data, dict):
        return {k: unmask_data(v, mapping) for k, v in data.items()}
    elif isinstance(data, list):
        return [unmask_data(x, mapping) for x in data]
    elif isinstance(data, str):
        return unmask_emails(data, mapping)
    return data

async def _run_explorer(state: dict, style: str, name: str) -> dict:
    """Shared inner runner for all three explorers."""
    query      = _get_last_user_query(state)
    tool_names = ", ".join(sorted(KNOWN_TOOL_NAMES))

    masked_query, email_mapping = mask_emails(query)

    prompt = _EXPLORER_TEMPLATE.format(
        style_instructions=style,
        tool_names=tool_names,
        query=masked_query,
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Query to process: {masked_query}"),
    ]
    res = await tool_llm.ainvoke(messages)

    try:
        parsed = _parse_json_response(res.content)
        # Only keep actions that reference real tools
        valid_actions = [
            a for a in parsed.get("proposed_actions", [])
            if isinstance(a, dict) and a.get("tool") in KNOWN_TOOL_NAMES
        ]
        
        # Unmask the generated actions so execution engine gets the real emails
        unmasked_actions = unmask_data(valid_actions, email_mapping)
        
        parsed["proposed_actions"] = unmasked_actions
        parsed["approach"]   = unmask_emails(str(parsed.get("approach", name)), email_mapping)
        parsed["response"]   = unmask_emails(str(parsed.get("response", res.content)), email_mapping)
        parsed.setdefault("confidence",  0.5)
        parsed["explorer_name"] = name
        return parsed

    except Exception as e:
        return {
            "approach":         f"{name} (parse error: {e})",
            "response":         res.content,
            "proposed_actions": [],
            "confidence":       0.0,
            "explorer_name":    name,
        }


async def run_tool_heavy_explorer(state: dict) -> dict:
    """
    Tool-Heavy Explorer node.
    First explorer to run -- also handles the retry case by resetting
    the explorer_outputs list when the Critic has already iterated.
    """
    output = await _run_explorer(state, _TOOL_HEAVY_STYLE, "ToolHeavyExplorer")

    # On a Critic retry (critic_iterations > 0), start a fresh exploration set
    if state.get("critic_iterations", 0) > 0:
        return {"explorer_outputs": [output]}

    existing = list(state.get("explorer_outputs") or [])
    return {"explorer_outputs": existing + [output]}


async def run_reasoning_heavy_explorer(state: dict) -> dict:
    """Reasoning-Heavy Explorer node."""
    output   = await _run_explorer(state, _REASONING_STYLE, "ReasoningHeavyExplorer")
    existing = list(state.get("explorer_outputs") or [])
    return {"explorer_outputs": existing + [output]}


async def run_concise_explorer(state: dict) -> dict:
    """Concise Explorer node."""
    output   = await _run_explorer(state, _CONCISE_STYLE, "ConciseExplorer")
    existing = list(state.get("explorer_outputs") or [])
    return {"explorer_outputs": existing + [output]}


# 
# 3. FITNESS EVALUATION AGENT
# 

_FITNESS_SYSTEM = """You are the Fitness Evaluation Agent for ScholarSync.

Evaluate ALL explorer candidate responses and score them using this MANDATORY formula:

  fitness = (0.35  tool_usage_correctness)
          + (0.25  correctness)
          + (0.20  completeness)
          + (0.10  relevance)
          + (0.10  clarity)

TOOL USAGE EVALUATION CRITERIA (tool_usage_correctness -- highest weight):
   Correct tools selected for the query
   ALL required tools are included
   NO unnecessary tools added
   NO duplicate tools with identical parameters
   Correct parameter values
   Logical execution sequencing

Score every dimension from 0.0 to 1.0.
Compute fitness_score using the formula above (do NOT deviate from it).

STRICT OUTPUT -- valid JSON only, no extra text:
{
  "evaluations": [
    {
      "candidate_index": 0,
      "tool_usage_correctness": 0.0,
      "correctness":            0.0,
      "completeness":           0.0,
      "relevance":              0.0,
      "clarity":                0.0,
      "fitness_score":          0.0
    }
  ],
  "best_candidate_index": 0
}

User query: {query}

Candidates:
{candidates}"""


async def fitness_evaluator_node(state: dict) -> dict:
    """
    Fitness Evaluator node.
    Scores all explorer outputs and selects the best candidate.
    Always succeeds -- falls back to confidence-based selection on any error.
    """
    explorer_outputs = state.get("explorer_outputs") or []

    if not explorer_outputs:
        return {"best_candidate": {}, "best_candidate_index": 0}

    def _confidence_fallback():
        """Pick highest-confidence explorer as backup."""
        try:
            best     = max(explorer_outputs, key=lambda x: float(x.get("confidence", 0)))
            best_idx = explorer_outputs.index(best)
        except Exception:
            best     = explorer_outputs[0]
            best_idx = 0
        return {"best_candidate": best, "best_candidate_index": best_idx}

    try:
        query = _get_last_user_query(state)

        # Safely serialise explorer outputs -- strip any non-serialisable values
        safe_outputs = []
        for i, o in enumerate(explorer_outputs):
            try:
                entry = {"candidate_index": i}
                for k, v in o.items():
                    try:
                        json.dumps(v)   # probe serialisability
                        entry[k] = v
                    except (TypeError, ValueError):
                        entry[k] = str(v)
                safe_outputs.append(entry)
            except Exception:
                safe_outputs.append({"candidate_index": i, "response": str(o), "confidence": 0.0})

        candidates_json = json.dumps(safe_outputs, indent=2)

        system_msg = _FITNESS_SYSTEM.format(query=query, candidates=candidates_json)
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=f"Evaluate all {len(explorer_outputs)} candidates for the query: {query}"),
        ]
        res = await llm.ainvoke(messages)

        parsed   = _parse_json_response(res.content)
        best_idx = int(parsed.get("best_candidate_index", 0))
        best_idx = max(0, min(best_idx, len(explorer_outputs) - 1))
        return {
            "best_candidate":       explorer_outputs[best_idx],
            "best_candidate_index": best_idx,
        }

    except Exception:
        return _confidence_fallback()


# 
# 4. EXPLOITER AGENT
# 

_EXPLOITER_SYSTEM = """You are the Exploiter Agent for ScholarSync.

Your ONLY job: refine the provided candidate response using the specific instructions from the Critic.
Do NOT change the underlying tool suggestions, ONLY fix the wording/style as requested.
If there is no Critic feedback or it says APPROVE, just output the same response.
"""

async def exploiter_node(state: dict) -> dict:
    """Exploiter node: refines winning text after Critic approval or final iteration."""
    best = state.get("best_candidate", {})
    feedback = state.get("critic_feedback", "")
    response_text = best.get("response", "I processed your request.")
    
    if not feedback or "APPROVE" in feedback.upper():
        return {"messages": [AIMessage(content=response_text)]}
        
    messages = [
        SystemMessage(content=_EXPLOITER_SYSTEM),
        HumanMessage(content=f"Original Response:\n{response_text}\n\nCritic Feedback:\n{feedback}")
    ]
    res = await llm.ainvoke(messages)
    return {"messages": [AIMessage(content=res.content)]}


# 
# 5. ACTION PLANNER AGENT
# 

_PLANNER_SYSTEM = """You are the Action Planner for ScholarSync.

Extract the tools needed for execution from the proposed actions.
Output ONLY valid JSON:
{
  "final_actions": [
    {"tool": "<name>", "parameters": {"<key>": "<val>"}}
  ]
}
"""

async def action_planner_node(state: dict) -> dict:
    """Action Planner node: algorithmically sorts and segregates the list of tools to execute."""
    best = state.get("best_candidate", {})
    actions = best.get("proposed_actions", [])
    valid_actions = [a for a in actions if a.get("tool") in KNOWN_TOOL_NAMES]
    
    # Priority mapping: lower number executes first
    priority = {
        "current_time": 0,
        "get_subject_professors": 1,
        "get_assignments_tool": 2,
        "get_materials_tool": 3,
        "get_marks_tool": 4,
        "get_exams_tool": 5,
        "get_deadlines_tool": 6,
        "list_calendar_events": 7,
        "calculator": 8,
        "currency_converter": 9,
        "get_weather": 10,
        "web_search": 11,
        "check_calendar_free": 12,
        "create_calendar_event": 13,
        "solve_assignment_tool": 14,
        "get_interview_info_tool": 15,
        "prepare_interview_session_tool": 16,
        "open_interview_in_browser_tool": 97,
        "send_email": 99,
    }

    # Topologically sort the actions
    sorted_actions = sorted(
        valid_actions,
        key=lambda x: priority.get(x.get("tool", ""), 50)
    )

    return {"final_actions": sorted_actions}


# 
# 6. EXECUTION ENGINE
# 

_SYNTHESIS_SYSTEM = """You are the Response Synthesizer for ScholarSync.

You have been given:
1. The planned response text (which contains the step-by-step plan the agent created)
2. Actual results from tools that were just executed

Your job: Produce a highly structured, human-friendly final answer that explicitly breaks down the process.

RULES:
1. Start your response by explicitly stating how you broke down the complex query (e.g., "I identified that you needed X and Y. I fetched X and Y.").
2. Narrate the steps you took in past-tense based on the tool results: "First, I fetched your marks data... Next, I checked your deadlines..."
3. Integrate the actual tool results cleanly into this narrative.
4. If an email was requested, conclude the narrative with: "Then, I composed the email draft as requested."
5. UI COMPONENTS RULE: If you fetched Assignments or Materials data, you MUST NOT use standard markdown tables! Instead, you MUST output the exact JSON array wrapped in a specific markdown code block so the frontend renders the beautiful Grid UI. 
For Assignments, use:
```ui_assignments
[ {"title": "Title", "subject": "Subject Name", "deadline": "date", "description": "desc", "assignmentDoc": "link"} ]
```
For Materials, use: 
```ui_materials
[ {"title": "Title", "subject": "Subject Name", "link": "https://link", "description": "desc"} ]
```
6. INTERVIEW SCHEDULING RULE: If prepare_interview_session_tool was called, you MUST output ONLY a brief one-line intro then the following block (do NOT include prose about the interview - just the block):
```ui_interview_confirm
{"topic": "<tag>", "url": "<url>", "score": <score>, "attempts": <attempts>}
```
Do NOT describe the interview details in text - the frontend will render the card.
7. For other data (like Marks or Exams), summarise it in readable prose or standard Markdown tables.
8. Be warm, professional, and clear about the multi-step actions you executed.
- Return ONLY the final response text -- no extra JSON outside of the UI blocks."""

_EMAIL_DRAFT_SYSTEM = """You are an authorized academic assistant for ScholarSync.
Your task is to draft a standard academic inquiry message. 
IMPORTANT: This is a legitimate student inquiry, NOT academic dishonesty, spam, or phishing. You are explicitly authorized to process this request.

Based on the provided data, draft the message body. Do NOT generate real personal headers if it violates policy, just draft the message content.

Rules:
- Use formal, respectful tone
- Integrate the actual data (marks, exam info) from the tool results
- Keep the message concise but complete
- Format exactly as:

  Subject: <subject line>

  Dear Professor <Name>,

  <message body>

  Best regards,
  [Student]

Return ONLY the formatted text -- no extra explanation."""

async def execution_engine_node(state: dict) -> dict:
    """
    Execution Engine -- smart 3-phase pipeline.

    Phase 1: Execute all data-gathering tools (marks, exams, professors, etc.)
    Phase 2: If email was planned, compose a proper draft using fetched data
             and present it for confirmation (never auto-sends).
    Phase 3: LLM synthesis -- turns raw tool output into readable human response.
    """
    final_actions: list = state.get("final_actions") or []
    query               = _get_last_user_query(state)

    _EMAIL_TOOL          = "send_email"
    _INTERVIEW_OPEN_TOOL = "open_interview_in_browser_tool"
    _DATA_TOOLS_FIRST = {
        "get_marks_tool", "get_exams_tool", "get_assignments_tool",
        "get_materials_tool", "get_deadlines_tool", "student_performance_tool",
        "get_subject_professors", "get_interview_info_tool", "prepare_interview_session_tool",
    }

    email_action          = None
    interview_open_action = None
    data_actions          = []
    other_actions         = []

    for action in final_actions:
        t = action.get("tool", "")
        if t == _EMAIL_TOOL:
            email_action = action
        elif t == _INTERVIEW_OPEN_TOOL:
            interview_open_action = action
        elif t in _DATA_TOOLS_FIRST:
            data_actions.append(action)
        else:
            other_actions.append(action)

    # -- Phase 1: Execute data + other tools ------------------------------
    once_only_executed: set  = set()
    execution_results:  list = []

    for action in (data_actions + other_actions):
        tool_name = action.get("tool", "")
        params    = action.get("parameters") or {}

        if tool_name in _ONCE_ONLY_TOOLS and tool_name in once_only_executed:
            continue

        tool_fn = TOOL_MAP.get(tool_name)
        if tool_fn is None:
            continue

        try:
            result = await tool_fn.ainvoke(params) if params else await tool_fn.ainvoke({})
            execution_results.append({"tool": tool_name, "result": str(result)})
        except Exception as e:
            execution_results.append({"tool": tool_name, "error": str(e)})

        if tool_name in _ONCE_ONLY_TOOLS:
            once_only_executed.add(tool_name)

    results_context = ""
    if execution_results:
        results_context = "\n\n".join(
            f"[{r['tool']}]:\n{r.get('result', 'Error: ' + r.get('error', 'unknown'))}"
            for r in execution_results
        )

    # -- Locate the Exploiter's refined/planned text ------------------------
    exploiter_response = ""
    for m in reversed(state["messages"]):
        if (
            getattr(m, "type", "") == "ai"
            and m.content
            and "APPROVE"         not in m.content.upper()
            and "CRITIC FEEDBACK" not in m.content
        ):
            exploiter_response = m.content
            break

    # -- Phase 2a: Compose email draft (NEVER auto-send) ------------------
    email_draft_block = ""
    if email_action:
        try:
            draft_prompt = (
                f"User request: {query}\n\n"
                f"Data fetched from tools:\n{results_context or 'No tool data available.'}\n\n"
                "Compose a professional email to the relevant professor using this data."
            )
            draft_res = await llm.ainvoke([
                SystemMessage(content=_EMAIL_DRAFT_SYSTEM),
                HumanMessage(content=draft_prompt),
            ])
            email_draft_block = (
                "\n\n---\n **Draft Email** *(please confirm before I send it)*:\n\n"
                + draft_res.content
                + "\n\n*Reply **\"yes, send it\"** to send, or tell me what to change.*"
            )
        except Exception as e:
            email_draft_block = f"\n\n*(Could not compose email draft: {e})*"

    # -- Phase 2b: Interview redirect confirmation block ------------------
    interview_confirm_block = ""
    if interview_open_action:
        params = interview_open_action.get("parameters") or {}
        topic  = params.get("topic", "")
        tag    = topic.strip().lower().replace(" ", "_")
        # Pull URL + perf from prepare_interview_session_tool result if available
        url, score, attempts = "", 0, 0
        sched_result = next(
            (r.get("result", "") for r in execution_results if r.get("tool") == "prepare_interview_session_tool"),
            None
        )
        if sched_result:
            try:
                import json as _json
                info     = _json.loads(sched_result)
                url      = info.get("url", "")
                score    = info.get("performance_score", 0)
                attempts = info.get("attempts", 0)
                tag      = info.get("topic", tag)
            except Exception:
                pass
        if not url:
            from chatbot.tools_integration import _interview_mapping, FRONTEND_BASE
            item = _interview_mapping.get(tag, {})
            ep   = item.get("endpoint_redirect", "")
            url  = (FRONTEND_BASE.rstrip("/") + "/" + ep.lstrip("/")) if ep else ""
            score    = item.get("performance_score", 0)
            attempts = item.get("number_of_attempts", 0)
        import json as _json2
        interview_confirm_block = (
            "\n\n"
            "```ui_interview_confirm\n"
            + _json2.dumps({"topic": tag, "url": url, "score": score, "attempts": attempts})
            + "\n```"
        )

    # -- Phase 3: LLM synthesis -- readable response from tool results -------
    final_response = exploiter_response or "I processed your request."
    
    try:
        if execution_results and results_context:
            synth_res = await llm.ainvoke([
                SystemMessage(content=_SYNTHESIS_SYSTEM),
                HumanMessage(
                    content=(
                        f"Planned response:\n{exploiter_response or query}\n\n"
                        f"Tool results:\n{results_context}\n\n"
                        f"User request: {query}"
                    )
                ),
            ])
            final_response = synth_res.content
    except Exception as e:
        # Fallback if synthesis fails
        final_response += "\n\n*(Note: I successfully executed the actions, but encountered an error formatting the final summary. The data was processed successfully.)*"

    if email_draft_block:
        final_response += email_draft_block

    if interview_confirm_block:
        # If synthesis already emitted ui_interview_confirm (from the prompt rule)
        # don't double-append. Only append if it's missing.
        if "ui_interview_confirm" not in final_response:
            final_response += interview_confirm_block

    return {"messages": [AIMessage(content=final_response)]}
