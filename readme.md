# ScholarSync

ScholarSync is a **multi-agent AI academic assistant** that helps students manage assignments, study materials, scheduling, and interview preparation through cooperating AI agents.

The system uses **LangGraph-based orchestration**, where multiple specialized agents collaborate to solve tasks such as:

- answering questions from academic documents
- managing assignments
- scheduling calendar events
- sending emails
- performing web searches
- conducting AI-based technical interviews

ScholarSync demonstrates how **tool-augmented AI agents can automate academic workflows.**

---

# System Architecture

ScholarSync follows a **multi-agent architecture** where agents cooperate through a LangGraph orchestration layer.

```
User
 ↓
Web Interface
 ↓
LangGraph Agent Graph
 ↓
-----------------------------------
Planner Agent
Retrieval Agent
Tool Agent
Interview Agent
-----------------------------------
 ↓
MCP Tool Server
 ↓
External Services
• Google Calendar
• Email
• Web Search
• Document Retrieval
```

Each agent performs a specialized role while collaborating with other agents to complete complex workflows.

---

# Key Features

### Multi-Agent AI System
ScholarSync uses multiple agents instead of a single chatbot.  
Agents collaborate to execute tasks and interact with external tools.

### Document Question Answering
Users can upload academic documents and ask contextual questions.

### Assignment Intelligence
Assignments can be fetched, analyzed, and explained using AI.

### Calendar Automation
The system can create, update, delete, and list events using the Google Calendar API.

### Email Automation
Agents can generate and send emails automatically.

### Web Search Tool
Real-time web search capability integrated as a tool for the agent.

### AI Interviewer
Includes an **AI technical interview module** that simulates coding and conceptual interviews.

---

# AI Interviewer Module

The project includes an **AI Interviewer system** that helps students practice technical interviews.

Capabilities:

- Ask technical questions
- Conduct behavioral interviews
- Analyze student responses
- Provide feedback
- Simulate interview environments

Example interaction:

```
AI Interviewer: What is the difference between BFS and DFS?

Student: BFS explores nodes level by level using a queue.

AI Feedback:
Correct. BFS uses a queue while DFS typically uses a stack or recursion.
```

Future improvements:

- coding problem evaluation
- real-time code execution
- interview scoring system
- adaptive difficulty interviews

---

# MCP Tool Server

The MCP server provides **external tools for agents**.

Available tools:

```
calculator
check_calendar_free
create_calendar_event
current_time
delete_event_by_title
get_subject_professors
list_calendar_events
send_email
update_event_by_title
web_search
```

Example API request:

```
POST /tools/create_calendar_event
```

Input example:

```
{
"title": "Submit DSA Assignment",
"start_time": "2026-03-10T19:00:00",
"end_time": "2026-03-10T20:00:00"
}
```

---

# Sync System

The sync system periodically fetches academic data and keeps the system updated.

Functions:

- fetch assignment data
- maintain a local database
- schedule periodic updates
- synchronize academic information

Files:

```
sync/
fetch_api_data.py
scheduler.py
sync_worker.py
sync_db.json
```

---

# Tech Stack

### AI Framework
- LangGraph
- LangChain
- Groq API (LLaMA models)

### Backend
- Python
- FastAPI
- MCP Tool Server

### AI Processing
- Retrieval Augmented Generation (RAG)
- Vector embeddings
- Document parsing

### Integrations
- Google Calendar API
- Email tools
- Web search APIs

### Frontend
- HTML
- CSS
- JavaScript

### AI Interviewer
- Python backend
- React frontend
- Docker support

---

# Project Structure

```
LANGGRAPH
│
├── chatbot
│   ├── graph.py
│   ├── llm.py
│   ├── memory.py
│   ├── service.py
│   ├── state.py
│   ├── threads.py
│   └── tools.py
│
├── mcp_server
│   ├── mcp_server.py
│   ├── calendar_auth.py
│   ├── config.py
│   │
│   └── tools
│       ├── calculator.py
│       ├── check_calendar_free.py
│       ├── create_calendar_event.py
│       ├── current_time.py
│       ├── delete_event_by_title.py
│       ├── get_subject_professors.py
│       ├── list_calendar_events.py
│       ├── send_email.py
│       ├── update_event_by_title.py
│       └── web_search.py
│
├── sync
│   ├── fetch_api_data.py
│   ├── scheduler.py
│   ├── sync_worker.py
│   └── sync_db.json
│
├── ai_interviewer
│   ├── backend
│   │   ├── app
│   │   ├── main.py
│   │   ├── cv_parser.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── client
│       ├── public
│       ├── src
│       ├── package.json
│       └── Dockerfile
│
├── js
│   ├── chat.js
│   ├── main.js
│   ├── ui.js
│   ├── history.js
│   └── sidebar.js
│
├── data
├── generated_pdfs
│
├── index.html
├── scholar_sync.html
├── assignment_solver.html
├── analysis.html
│
├── chatbot.py
├── server.py
├── setup_db.py
│
├── styles.css
├── nstyle.css
│
├── requirements.txt
└── README.md
```

---

# Installation

### Clone Repository

```
git clone https://github.com/yourusername/scholarsync.git
cd scholarsync
```

---

### Create Virtual Environment

```
python -m venv myenv
```

Activate environment

Windows

```
myenv\Scripts\activate
```

Mac/Linux

```
source myenv/bin/activate
```

---

### Install Dependencies

```
pip install -r requirements.txt
```

---

### Configure Environment Variables

Create a `.env` file

```
GROQ_API_KEY=your_groq_api_key
```

---

# Running the System

### Start MCP Tool Server

```
python mcp_server/mcp_server.py
```

### Start Backend Server

```
python server.py
```

### Open Frontend

Open in browser:

```
index.html
```

---

# Running AI Interviewer

Navigate to the AI interviewer folder:

```
cd ai_interviewer/backend
pip install -r requirements.txt
python main.py
```

For frontend:

```
cd ai_interviewer/client
npm install
npm start
```

---

# Current Status

Fully Functional

- multi-agent orchestration
- document Q&A
- assignment solver
- calendar automation
- email automation
- web search integration

Partially Implemented

- AI coding interview environment
- automated interview scoring

Known Limitations

- no authentication system
- centralized MCP tool execution
- interview scoring still experimental

---

# Future Improvements

- authentication and user accounts
- distributed agent architecture
- AI coding interview IDE
- advanced agent memory
- interview analytics dashboard

---

# License

MIT License

---

# Author

Team:It’sWinTime

AI Systems • Multi-Agent Architectures • Full-Stack Development