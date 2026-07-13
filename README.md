# ⚽ StadiumOps Copilot — AI Volunteer Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![FAISS](https://img.shields.io/badge/FAISS-005571?style=for-the-badge&logo=meta)](https://github.com/facebookresearch/faiss)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain)](https://python.langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**StadiumOps Copilot** is an AI-powered assistant for stadium volunteers and staff during large-scale tournament operations (FIFA World Cup 2026 scale). It uses **Retrieval-Augmented Generation (RAG)** to provide real-time, step-by-step guidance from 8 official Standard Operating Procedures, with automatic **escalation decisions** and **multilingual support** in 6 languages.

---

## 🏟️ Chosen Vertical

**Smart Stadiums & Tournament Operations** — Volunteer/staff assistant for FIFA World Cup 2026-style events.

Stadium volunteers face high-pressure, real-time decisions: a fan collapses, a child goes missing, a suspicious bag is found, a storm approaches. They need instant, accurate SOP guidance — not a 50-page manual. StadiumOps Copilot puts the right procedure in their hands within seconds, in their preferred language, with a clear escalation recommendation.

---

## 🧠 How GenAI Decision-Making Works

StadiumOps Copilot uses GenAI as the **core reasoning engine**, not just for text generation but for **structured decision-making**:

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────────┐
│ Volunteer's      │     │  Input       │     │  FAISS Vector     │
│ Question         │────▶│  Sanitizer   │────▶│  Search (Top-K)   │
│ + Zone/Role      │     │  (injection  │     │  (Gemini          │
│ + Language       │     │   guard)     │     │   Embeddings)     │
└─────────────────┘     └──────────────┘     └────────┬──────────┘
                                                       │
                                              Retrieved SOP Chunks
                                                       │
                                                       ▼
                                            ┌──────────────────────┐
                                            │  Gemini 2.0 Flash    │
                                            │  (Structured JSON)   │
                                            │                      │
                                            │  Generates:          │
                                            │  • Step-by-step      │
                                            │    answer             │
                                            │  • Escalation flag   │
                                            │  • Reasoning         │
                                            │  • Confidence        │
                                            └────────┬─────────────┘
                                                     │
                                          ┌──────────┴──────────┐
                                          │  Dual-Signal        │
                                          │  Escalation Logic   │
                                          │                     │
                                          │  Signal 1: Keyword  │
                                          │  scan of retrieved  │
                                          │  SOP chunks         │
                                          │                     │
                                          │  Signal 2: LLM's    │
                                          │  own assessment     │
                                          │                     │
                                          │  EITHER triggers    │
                                          │  → final: ESCALATE  │
                                          └──────────┬──────────┘
                                                     │
                                                     ▼
                                            ┌────────────────┐
                                            │  Response       │
                                            │  • Answer       │
                                            │  • Sources      │
                                            │  • Escalation   │
                                            │  • Confidence   │
                                            └────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Structured output** | Gemini `response_mime_type="application/json"` with schema | Reliable parsing of escalation flag — no regex on free text |
| **Dual-signal escalation** | Keyword scan + LLM assessment | Defense-in-depth: LLM might miss severity, keywords catch it; if either says escalate, we escalate |
| **Severity keywords** | 40+ curated terms from real SOPs | Medical (`unconscious`, `cardiac`), security (`weapon`, `bomb`), crowd (`crush`, `stampede`), weather (`tornado`, `evacuation`) |
| **Input sanitization** | Regex-based prompt-injection guard | Strips instruction overrides, role reassignment, system token injection |
| **API-only embeddings** | Gemini `text-embedding-004` (768-dim) | No local model weights → repo stays under 10MB |

---

## 📋 SOPs Covered

| # | SOP | Severity | Key Scenarios |
|---|-----|----------|---------------|
| 1 | Medical Emergency | 🔴 Critical | CPR/AED, collapse, seizure, anaphylaxis, heat stroke |
| 2 | Lost/Missing Child | 🔴 Critical | Code Adam, unaccompanied child, exit monitoring |
| 3 | Security Incident | 🔴 Critical | Suspicious package, active threat, bomb threat, altercation |
| 4 | Weather/Evacuation | 🔴 Critical | Lightning, tornado, extreme heat, full evacuation |
| 5 | Crowd Control | 🟠 High | Density levels, bottleneck, crowd surge, gate management |
| 6 | Accessibility | 🟡 Medium | Wheelchair dispatch, accessible routes, service animals |
| 7 | Lost & Found | 🟢 Low | Item logging, return procedures, high-value handoff |
| 8 | Fan Assistance | 🟢 Low | Wayfinding, seating, concessions, Wi-Fi, FAQ |

---

## 🛠️ Technology Stack

### Core Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **RAG Pipeline**: LangChain
- **Vector Database**: FAISS (local, fast, tiny footprint)
- **Embeddings**: Google Gemini API (`gemini-embedding-2`)
- **LLM Generation**: Groq API (`llama-3.3-70b-versatile` for blazing fast generation)
- **Frontend**: Vanilla HTML/CSS/JS (zero dependencies, glassmorphic UI)

---

## 📂 Project Structure

```text
StadiumOps-Copilot/
├── backend/
│   ├── __init__.py
│   ├── config.py           # .env configuration loader
│   ├── embeddings.py        # Gemini embedding wrapper (LangChain interface)
│   ├── ingest.py            # SOP markdown parser + chunker
│   ├── llm.py               # Gemini LLM client (structured output support)
│   ├── qa_chain.py          # RAG pipeline + dual-signal escalation logic
│   ├── sanitizer.py         # Prompt-injection guard
│   ├── vectorstore.py       # FAISS index management
│   └── routers/
│       ├── __init__.py
│       └── ask.py           # POST /api/ask endpoint
├── frontend/
│   ├── index.html           # Chat UI (ARIA, RTL-ready)
│   ├── style.css            # Glassmorphic dark theme (amber/gold)
│   └── app.js               # Chat logic, language selector, escalation
├── sop_documents/           # 8 pre-written SOP markdown files
├── tests/
│   ├── __init__.py
│   ├── test_qa_chain.py     # Retrieval + escalation tests (15 cases)
│   └── test_sanitizer.py    # Sanitizer tests (15 cases)
├── .env.example             # Environment template
├── .gitignore
├── requirements.txt
├── run.py                   # Server entry point
└── README.md
```

---

## ⚙️ Setup & Run

### Prerequisites

- **Python 3.9+**
- **Google Gemini API Key** — Get one from the [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
# Clone the repository
git clone https://github.com/vigneshwaran484/StadiumOps-Copilot
cd StadiumOps-Copilot

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run the Application

```bash
python run.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

On first launch, the app automatically ingests the 8 SOP documents into a FAISS vector index. This takes ~10 seconds and only happens once (the index is persisted to `vectorstore/`).

### API Documentation

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

---

## 🧪 Running Tests

```bash
# Run all unit tests (no API key required)
pytest tests/ -v

# Run only sanitizer tests
pytest tests/test_sanitizer.py -v

# Run only QA chain tests (mocked, no API needed)
pytest tests/test_qa_chain.py -v

# Run integration tests (requires GEMINI_API_KEY + built index)
pytest tests/ -v -m integration
```

### Test Coverage

| Test File | Cases | Type | API Required? |
|-----------|-------|------|---------------|
| `test_sanitizer.py` | 15 | Unit | ❌ No |
| `test_qa_chain.py` — keyword escalation | 8 | Unit | ❌ No |
| `test_qa_chain.py` — escalation scenarios | 5 | Unit (mocked) | ❌ No |
| `test_qa_chain.py` — retrieval relevance | 2 | Integration | ✅ Yes |

---

## 🔒 Security Considerations

1. **API Key Management**: Keys loaded from `.env` (never hardcoded), `.env` is in `.gitignore`
2. **Prompt-Injection Guard**: 15 regex patterns detect and strip:
   - Instruction overrides ("ignore previous instructions")
   - Role reassignment ("you are now", "pretend to be")
   - System token injection (`<|system|>`, `[INST]`, `<<SYS>>`)
   - Output manipulation ("output only", "respond with just")
3. **Input Validation**: Pydantic models enforce min/max length, language code allowlist
4. **XSS Prevention**: All user text is HTML-escaped before rendering in the frontend

---

## ♿ Accessibility Features

- `role="log"` and `aria-live="polite"` on the chat message area
- `aria-label` on all interactive elements (buttons, inputs, selectors)
- Keyboard-navigable: Tab through all controls, Enter to send, Escape to close modal
- Visible `:focus-visible` outlines (amber ring, WCAG AA compliant)
- Color contrast: all text meets 4.5:1 ratio minimum against backgrounds
- RTL layout support for Arabic (`dir="rtl"` toggled automatically)
- Screen-reader-only utility class (`.sr-only`) for labels

---

## 💡 Assumptions Made

1. **Pre-loaded SOPs**: The 8 SOP documents are committed to the repo and auto-ingested on startup. No runtime upload needed.
2. **No authentication**: This is a hackathon demo — no user accounts or sessions. In production, you'd add volunteer badge/ID auth.
3. **No persistent chat history**: Conversations are in-memory only. Each page refresh starts fresh.
4. **Single-tenant**: One shared FAISS index for all users. In production, you might partition by venue/event.
5. **LLM language capability**: We rely on Gemini's multilingual generation for non-English responses. Quality may vary by language.
6. **Mock escalation**: The "Escalate to Human" button shows a toast notification. In production, this would integrate with a radio dispatch or ticketing system.

---

## 📄 License

Distributed under the MIT License.

---

<p align="center">
  Built with ⚽ for the Hackathon by <a href="https://github.com/vigneshwaran484">Vigneshwaran</a>
</p>
