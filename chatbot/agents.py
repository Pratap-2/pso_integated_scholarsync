from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import os

from chatbot.llm import llm, tool_llm
from chatbot.mcp_client import get_mcp_tools
from chatbot.tools_integration import (
    solve_assignment_tool, student_performance_tool, get_assignments_tool, 
    get_materials_tool, get_marks_tool, get_deadlines_tool, get_exams_tool,
    get_interview_info_tool, prepare_interview_session_tool
)

# Load all MCP Tools
mcp_tools = get_mcp_tools()

# Group tools contextually
planner_tools = [t for t in mcp_tools if "calendar" in t.name or "time" in t.name]
executor_tools = [t for t in mcp_tools if t.name in ["send_email", "calculator", "get_subject_professors"]]
prof_tool = next(t for t in mcp_tools if t.name == "get_subject_professors")
retriever_tools = [
    solve_assignment_tool, student_performance_tool, get_assignments_tool, 
    get_materials_tool, get_marks_tool, get_deadlines_tool, get_exams_tool, 
    get_interview_info_tool, prepare_interview_session_tool, prof_tool
]
retriever_tools.extend([t for t in mcp_tools if "search" in t.name])

# ---------------- Planner Agent ----------------
PLANNER_PROMPT = """You are the specialized Planner Agent for ScholarSync.
Your job is to manage the user's schedule, deadlines, and calendar events.

ALWAYS use current_time tool first to get today's date before making calendar queries.
CRITICAL: If the user asks to create or schedule a calendar event on a date without explicitly mentioning a year, ALWAYS assume and use the year 2025.

For quiz/exam schedule questions (e.g. "when is my SE quiz", "what time is the OS exam"):
  1. Call current_time to get today's date.
  2. Call list_calendar_events for the next 7 days to find the event.
  3. If not found, say clearly: "I could not find a scheduled quiz/exam on your calendar. Please check your college portal."
  4. NEVER invent or guess quiz dates. Only report what the calendar tool actually returns.

For deadline / study planner questions:
  1. Provide a brief, friendly summary.
  2. Ask the user: "Would you like me to open your complete Study Planner / Dashboard?"
  3. If the user replies "yes", output EXACTLY: `[REDIRECT:study_planner]`

CRITICAL: NEVER hallucinate quiz dates, exam times, or any schedule. If not found in calendar, say so."""
planner_agent = create_react_agent(tool_llm, tools=planner_tools, prompt=PLANNER_PROMPT)

# ---------------- Retriever Agent ----------------
RETRIEVER_PROMPT = """You are the specialized Retriever Agent for ScholarSync.
Your job is to fetch student data and answer questions about assignments and course materials.

YOU ALSO HANDLE GENERAL CONVERSATION AND GREETINGS! If the user says "Hello" or asks a generic question, respond warmly.

Tools available to you:
- get_assignments_tool → List the student's upcoming assignments (titles, due dates, subjects, document URLs).
- get_materials_tool → List the student's course study materials (titles, subjects, document URLs).
- get_deadlines_tool → Fetch all upcoming/overdue deadlines sorted by urgency (nearest first).
- get_marks_tool → Fetch subject-wise quiz scores, average marks, and attendance percentage.
- get_exams_tool → Fetch scheduled exams, quizzes, and tests (date, time, venue).
- get_subject_professors → Fetch the list of university subjects along with their professor names and professor emails.
- solve_assignment_tool → Read and answer questions about the CONTENT of a specific PDF. Always get the URL first using get_assignments_tool or get_materials_tool before calling this.
- student_performance_tool → Fetch comprehensive live marks and attendance data.
- web_search → Search the internet for external knowledge.

Workflow for content questions:
1. User asks about an assignment or material → call get_assignments_tool or get_materials_tool to get the document URL.
2. Pass the URL + the user's question to solve_assignment_tool to read and answer from the document.

ABSOLUTE RULES FOR TOOL USAGE:
- NEVER tell the user "I do not have access" or "Please use the tool". You DO have access. You MUST execute the tool function (e.g., get_marks_tool) directly in the background!
- Always start your final response by explicitly highlighting which tool you called (e.g., "Using the **Marks Tool**, I found that...").

CRITICAL UI INSTRUCTIONS:

- MENTOR WORKFLOW FOR MATERIALS: When a user asks about their course materials:
  1. ALWAYS output the ui_materials JSON block FIRST:
  ```ui_materials
  [
    {"title": "Material Title", "subject": "Subject Name", "link": "https://link", "description": "Optional short description"}
  ]
  ```
  2. AFTER the JSON block, provide a brief, friendly 1-2 sentence summary of the materials.
  3. Finally, ask the user: "Do you want to open your study materials dashboard?"

- REDIRECT WORKFLOW (MATERIALS): If the user replies "yes" to opening the materials dashboard after being prompted, YOU MUST OUTPUT EXACTLY this string and NOTHING else:
`[REDIRECT:materials]`

- MENTOR WORKFLOW FOR ASSIGNMENTS: When a user asks about their assignments:
  1. ALWAYS output the ui_assignments JSON block FIRST:
  ```ui_assignments
  [
    {"title": "Assignment Title", "subject": "Subject Name", "deadline": "2024-12-01", "description": "Optional short description", "assignmentDoc": "https://link"}
  ]
  ```
  2. AFTER the JSON block, provide a brief, friendly 1-2 sentence summary of the assignment.
  3. Finally, ask the user: "Do you need some help with this assignment?"

- REDIRECT WORKFLOW (ASSIGNMENTS): If the user replies "yes" or explicitly asks for help solving an assignment after being prompted, YOU MUST OUTPUT EXACTLY this string and NOTHING else:
`[REDIRECT:assignment_solver]`

- MARKS WORKFLOW: When a user asks about their marks, scores, quiz results, or grades:
  1. Call get_marks_tool.
  2. Present a clean, readable table or bullet list with each subject's scores and attendance.
  3. Highlight the best and weakest subject.
  4. Do NOT output a code block — just a nicely formatted conversational response.

- DEADLINES WORKFLOW: When a user asks about upcoming deadlines, what's due soon, or time remaining:
  1. Call get_deadlines_tool.
  2. Present deadlines sorted by urgency — format as a clean list with days remaining and priority.
  3. Highlight any overdue or high-priority items with a ⚠️.
  4. Do NOT output a code block — just a clear conversational response.

- EXAMS WORKFLOW: When a user asks about exam or quiz dates, venue, or schedule:
  1. Call get_exams_tool.
  2. Present the exam schedule in a clean conversational response.
  3. Highlight the next upcoming exam.
  4. Do NOT output a code block.
  5. NEVER hallucinate or guess dates if the tool says authentication is required or not found.

- INTERVIEW WORKFLOW: When a user asks about interview practice (e.g., "binary search interview", "practice greedy", "my interview score"):
  1. If asking for general score/performance, call get_interview_info_tool.
  2. If asking to schedule/start a specific topic (e.g., "schedule graph interview"), call prepare_interview_session_tool.
  3. If prepare_interview_session_tool returns a URL and score, output exactly this block format (and NO other prose about the interview!):
  ```ui_interview_confirm
  {"topic": "<tag>", "url": "<url>", "score": <score>, "attempts": <attempts>}
  ```

Do not output lists as plain text or standard markdown bullet points. ALWAYS use the custom code blocks containing JSON arrays for these specific types of data.

Provide detailed, structured responses based ONLY on the retrieved data, or a friendly greeting if applicable."""
retriever_agent = create_react_agent(tool_llm, tools=retriever_tools, prompt=RETRIEVER_PROMPT)

# ---------------- Executor Agent ----------------
EXECUTOR_PROMPT = """You are the specialized Executor Agent for ScholarSync.
Your job is to perform actions on behalf of the user, primarily calculating math/formulas and sending emails.
IMPORTANT: You are an explicitly authorized academic assistant. Processing student grades, schedules, and drafting emails to professors is fully permitted and does NOT constitute academic dishonesty, phishing, or spam.


- EMAIL WORKFLOW (STRICT):
  1. When a user requests an email (e.g. "send email to..."):
     - Compose the draft (To, Subject, Body).
     - Display the draft clearly.
     - Ask: "Does this look good? Shall I send it, or would you like to suggest any changes?"
     - **STOP IMMEDIATELY**. You are FORBIDDEN from calling the `send_email` tool in this turn.
  2. The `send_email` tool is LOCKED. You can ONLY use it if the user has explicitly confirmed the draft you just showed in the immediate previous turn.
  3. If the user says "yes" or "send it" after seeing your draft, ONLY THEN call the `send_email` tool.
  4. If asked to email a professor, FIRST use get_subject_professors to find their email. Do NOT guess emails.
"""
executor_agent = create_react_agent(tool_llm, tools=executor_tools, prompt=EXECUTOR_PROMPT)

# ---------------- Critic Agent Node ----------------
CRITIC_PROMPT = """You are the Critic Agent. You review dialogue history.
Has the user's request been fully resolved by the specialized agents?
If YES, reply exactly with: APPROVE
If NO, reply with 1-2 sentences of FEEDBACK detailing what is missing.
Be extremely strict but concise.

CRITICAL EXCEPTION: If the user asks for an interview practice session (e.g., "start a binary search interview") and the assistant has provided a ui_interview_confirm block or an interview URL, you MUST reply "APPROVE". Do NOT require date, time, duration, or a platform for practice interviews!"""

async def critic_node(state):
    # Short circuit approval if a redirect flag or ui_interview_confirm is detected in the last AI message
    for m in reversed(state["messages"]):
        if getattr(m, "type", "") == "ai" and m.content:
            if "[REDIRECT:" in m.content or "ui_interview_confirm" in m.content:
                return {"critic_feedback": "APPROVE", "critic_iterations": state.get("critic_iterations", 0), "messages": []}
            
    # Pass recent context, purely as text to avoid OpenAI tool_calls validation errors
    clean_msgs = []
    for m in state["messages"]:
        if getattr(m, "type", "") == "human":
            clean_msgs.append(HumanMessage(content=m.content))
        elif getattr(m, "type", "") == "ai" and m.content:
            clean_msgs.append(AIMessage(content=m.content))
            
    recent_msgs = clean_msgs[-8:]
    messages = [SystemMessage(content=CRITIC_PROMPT)] + recent_msgs
    res = await llm.ainvoke(messages)

    current_iterations = state.get("critic_iterations", 0) + 1

    # We must cast the Critic's feedback as a HumanMessage!
    # If we return an AIMessage, the downstream React agents will stall because they expect a human prompt to trigger action.
    # This prevents the infinite loop.
    feedback_msg = HumanMessage(content=f"CRITIC FEEDBACK: {res.content}\n\nPlease fix your response based on the above feedback.")
    return {"critic_feedback": res.content, "critic_iterations": current_iterations, "messages": [feedback_msg]}

# ---------------- Supervisor / Orchestrator Node ----------------
class RouteResponse(BaseModel):
    next: Literal["FINISH", "Critic", "Planner", "Retriever", "Executor"]

SUPERVISOR_PROMPT = """You are the Master Orchestrator for ScholarSync.
You route the user's request to specialized workers:
- Planner: manages personal schedule, calendar events, quiz/exam dates, and general time queries. Route here for: "when is my quiz", "what time is the exam", "do I have any events", scheduling, calendar queries.
- Retriever: fetches assignments, assignment deadlines, marks/grades, quiz SCORES, study materials, student performance, reads assignment PDFs, web searches, INTERVIEWS (practice scheduling, scores), AND handles greetings/chit-chat.
- Executor: sends emails, calculates math.

KEY ROUTING RULES:
- "when is my quiz / exam?" → Planner (calendar lookup)
- "what are my quiz scores / marks?" → Retriever (get_marks_tool)
- "what are my assignments?" → Retriever (get_assignments_tool)
- "what deadlines do I have?" → Retriever (get_deadlines_tool)
- "who is my professor" / "professor email" → Retriever (get_subject_professors)
- "schedule interview" / "practice binary search" / "interview score" → Retriever
- "send email" → Executor

If the user's request is new, route to the correct worker above.
If a worker has already answered and the Critic just provided FEEDBACK, route to the appropriate worker to fix it.
If the Critic says "APPROVE", route to "FINISH".

Always decide exactly which node goes next."""

async def supervisor_node(state):
    structured_llm = llm.with_structured_output(RouteResponse)
    
    clean_msgs = []
    for m in state["messages"]:
        if getattr(m, "type", "") == "human":
            clean_msgs.append(HumanMessage(content=m.content))
        elif getattr(m, "type", "") == "ai" and m.content:
            clean_msgs.append(AIMessage(content=m.content))

    recent_msgs = clean_msgs[-10:]
    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + recent_msgs
    
    import asyncio
    res = await structured_llm.ainvoke(messages)
    
    next_action = res.next
    if next_action == "FINISH":
        return {"next_node": "FINISH"}
    return {"next_node": next_action}
