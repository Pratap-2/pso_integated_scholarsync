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
    """Action Planner node: finalises the list of tools to execute."""
    best = state.get("best_candidate", {})
    actions = best.get("proposed_actions", [])
    
    # Simple pass-through for now since Explorer outputs are already validated
    valid_actions = [a for a in actions if a.get("tool") in KNOWN_TOOL_NAMES]
    return {"final_actions": valid_actions}


# 
# 6. EXECUTION ENGINE
# 

_SYNTHESIS_SYSTEM = """You are the Response Synthesizer for ScholarSync.

You have been given:
1. The planned response text (what the agent intended to say)
2. Actual results from tools that were just executed

Your job: Produce a single, clean, human-friendly final answer.

RULES:
- Integrate the tool results naturally into the response.
- DO NOT dump raw JSON -- summarise data in readable prose or a clean table.
- If marks data is present, format it as a concise subject-by-subject summary.
- If exam data is unavailable, say so clearly and briefly.
- Be warm, professional, and concise.
- Return ONLY the final response text -- no preamble, no JSON."""

_EMAIL_DRAFT_SYSTEM = """You are a professional email composer for ScholarSync.

Using the data provided, compose a professional email for the student to send to their professor.

Rules:
- Use formal, respectful tone
- Integrate the actual data (marks, exam info) from the tool results
- Keep the email concise but complete
- Format exactly as:

  Subject: <subject line>

  Dear Professor <Name>,

  <email body>

  Best regards,
  [Student]

Return ONLY the formatted email -- no extra explanation."""

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

    _EMAIL_TOOL       = "send_email"
    _DATA_TOOLS_FIRST = {
        "get_marks_tool", "get_exams_tool", "get_assignments_tool",
        "get_materials_tool", "get_deadlines_tool", "student_performance_tool",
        "get_subject_professors",
    }

    email_action  = None
    data_actions  = []
    other_actions = []

    for action in final_actions:
        t = action.get("tool", "")
        if t == _EMAIL_TOOL:
            email_action = action
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

    # -- Phase 2: Compose email draft (NEVER auto-send) --------------------
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
        pass

    if email_draft_block:
        final_response += email_draft_block

    return {"messages": [AIMessage(content=final_response)]}
