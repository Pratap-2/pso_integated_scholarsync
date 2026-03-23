# 🤖 AI Interview Platform

> An end-to-end AI-powered technical interview simulation platform that evaluates candidates on competitive coding problems with real-time voice tutoring, resume-based personalisation, and detailed post-interview analytics.

---

## 🔗 Repository

**GitHub:** [github.com/Aditya5240/code-ide](https://github.com/Aditya5240/code-ide)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Resume Parsing** | Upload PDF/DOCX → personalised dashboard with skills pie chart, bar chart, project/experience cards |
| 🧠 **AI Interviewer** | Voice-enabled AI tutor powered by LLaMA 3.3 70B (via Groq) giving hints, periodic nudges, final evaluation |
| 💬 **Multi-turn Chat** | Stateful conversation history per session — AI remembers context across turns |
| 📚 **CS Concept Teaching** | Keyword-based detection (`"what is"`, `"explain"`, etc.) — concept questions taught purely, not anchored to the problem |
| 🎙️ **Voice Input (STT)** | Azure Cognitive Services Speech-to-Text for microphone input |
| 🔊 **Voice Output (TTS)** | Azure Cognitive Services Text-to-Speech for AI responses |
| ⛶ **Fullscreen Editor** | One-click fullscreen code editor that hides all side panels |
| 💬 **Collapsible Chat** | Toggle the AI tutor panel on/off; floating 💬 button restores it |
| 🌙 **Dark / ☀️ Light Mode** | Theme toggle that updates all UI elements and Monaco editor |
| ⚡ **Resume Cache** | MD5 hash cache — re-uploading the same resume returns instant results |
| 📊 **Post-Interview Analysis** | Score graph over time, final AI evaluation, session history |
| 🔄 **Persistent History** | Unified `userId` (localStorage) tracks performance across multiple interviews in a single trajectory |
| 📉 **ML Performance Radar** | Radar charts visualizing Coding, Communication, Logic, and Speed metrics |

---

## 🏗️ Architecture

```
code-ide/                        ← This repo
│
├── client/                      # React frontend
│   └── src/
│       └── pages/
│           ├── Landing.js       # Resume upload + candidate dashboard
│           ├── Interview.js     # Code editor + AI chat + timer
│           └── Analysis.js      # Post-interview report
│
└── backend/                     # FastAPI backend
    ├── main.py                  # All API routes
    ├── cv_parser.py             # Resume parsing (PyPDF2 / python-docx)
    ├── requirements.txt
    └── app/
        ├── schemas.py           # Pydantic models
        ├── problems.py          # Coding problems bank
        ├── graph_builder.py     # LangGraph pipeline
        ├── state.py             # Shared state schema
        ├── nodes/               # LangGraph nodes
        │   ├── interviewer_node.py
        │   ├── hint_node.py
        │   ├── evaluator_node.py
        │   ├── feedback_node.py
        │   ├── tracker_node.py
        │   └── wrapup_node.py
        └── services/
            ├── llm.py           # Groq LLM (chat=0.7, analysis=0.4)
            ├── speech_service.py    # Azure TTS
            ├── session_store.py    # Azure Cosmos DB sessions
            └── cosmos_services.py  # Cosmos DB helpers
```

> ℹ️ The React frontend (`client/`) communicates with the FastAPI backend at `http://localhost:8000`.

---

## 🛠️ Tech Stack

### Frontend
| Library | Purpose |
|---|---|
| React 18 | UI framework |
| `@monaco-editor/react` | VS Code-style code editor |
| `recharts` | Charts for resume dashboard |
| `axios` | HTTP client |
| `react-router-dom` | SPA routing |

### Backend
| Library | Purpose |
|---|---|
| FastAPI | REST API framework |
| LangChain + LangGraph | LLM orchestration pipeline |
| `langchain-groq` | LLaMA 3.3 70B via Groq API |
| `azure-cognitiveservices-speech` | Text-to-Speech + Speech-to-Text |
| `azure-search-documents` | Vector search for resume embeddings |
| `azure-cosmos` | Session state persistence |
| `PyPDF2` / `python-docx` | Resume file parsing |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- `g++` on PATH (for C++ code execution)
- API keys (see below)
- **Docker** & **Docker Compose** (for containerised deployment)

---

### 1. Clone the repository

```bash
git clone https://github.com/Aditya5240/code-ide.git
cd code-ide
```

---

### 2. Docker Deployment (Recommended)

To run both the frontend and backend together using Docker Compose:

```bash
docker-compose up --build
```

> **App:** `http://localhost:3000`  
> **API:** `http://localhost:8000`

---

### 3. Manual Backend Setup

```bash
# From inside code-ide/ — create and activate virtual environment
python -m venv ms
.\ms\Scripts\Activate.ps1          # Windows PowerShell
# source ms/bin/activate           # macOS / Linux

# Move into backend and install dependencies
cd backend
pip install -r requirements.txt
```

#### Environment Variables

Create a `.env` file inside `backend/`:

```env
# Groq (LLM)
GROQ_API_KEY=your_groq_api_key

# Google (Embeddings)
GOOGLE_API_KEY=your_google_api_key

# Azure AI Search (Vector Store)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your_azure_search_key
AZURE_SEARCH_INDEX=your_index_name

# Azure Speech (TTS + STT)
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=eastus

# Azure Cosmos DB (Session Store)
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE=interview_db
COSMOS_CONTAINER=sessions
```

#### Start the backend

```bash
# From inside code-ide/backend/ with venv active:
uvicorn main:app --port 8000 --reload
```

> API: `http://localhost:8000`  
> Interactive docs: `http://localhost:8000/docs`

---

### 4. Manual Frontend Setup

Open a **new terminal**, navigate back to `code-ide/` and run:

```bash
cd client
npm install
npm start
```

> App opens at `http://localhost:3000`

---

## 🗺️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/problem/{id}` | Fetch problem (solution hidden) |
| `POST` | `/run` | Compile & run C++ code |
| `POST` | `/ai/parse_resume` | Parse uploaded CV (MD5 cached) |
| `POST` | `/ai/welcome` | Welcome audio for interview start |
| `POST` | `/ai/chat` | Multi-turn chat with concept detection |
| `POST` | `/ai/hint` | Progressive hints (5 levels) |
| `POST` | `/ai/periodic` | Periodic progress nudge (every 60s) |
| `POST` | `/ai/evaluation` | Final code evaluation |
| `POST` | `/ai/stt` | Speech-to-Text (audio → transcript) |
| `POST` | `/update_code` | Sync code + run LangGraph pipeline |
| `GET` | `/session/{id}/analysis` | Post-interview analysis + scores |

---

## 🎮 How to Use

### 1. Upload Resume
- Go to `http://localhost:3000`
- Upload your resume (PDF or DOCX)
- View personalised dashboard with skills, projects, and experience

### 2. Start Interview
- Click **Start Interview** — AI tutor greets you and introduces the problem

### 3. During the Interview

| Action | How |
|---|---|
| Write code | Monaco editor (centre panel) |
| Run tests | **▶ Run Tests** |
| Ask a question | Type in chat OR 🎙️ voice input |
| Get a hint | **💡 I'm Stuck** (5 progressive levels) |
| Fullscreen | **⛶ Full** toolbar button |
| Hide/show chat | **💬 Hide Chat** toolbar button |
| Toggle theme | **☀️ / 🌙** toolbar button |
| End early | **🛑 End** → goes to analysis |
| Submit | **✅ Submit** → final AI eval → analysis |

### 4. Analysis Page
- **Performance Trajectory**: LineChart plotting your growth across the last 5 attempts.
- **Skill Radar Profile**: RadarChart mapping Coding, Communication, Problem Solving, and Efficiency.
- **AI Coaching Summary**: Narrative feedback synthesized from your session history.

---

## 🔑 Key Design Decisions

### Chat Route Ordering
`/ai/chat` is declared **before** `/ai/{ai_type}` — FastAPI matches routes in order; the wildcard would otherwise intercept chat requests.

### Concept Question Detection
Messages scanned for keywords (`"what is"`, `"explain"`, `"difference between"`, etc.) before calling LLM. Concept questions sent without problem context — model teaches purely.

### Resume Caching
File bytes hashed (MD5) before parsing. Same resume returns cached results instantly from in-memory dict.

### Dual LLM Temperature
- `chat`: `temperature=0.7` — creative, educational  
- `analysis`: `temperature=0.4` — deterministic, consistent

---

## 🙋 Author

**Aditya Pratap Singh**  and **ADITYA JAIN**
IIT (ISM) Dhanbad  

