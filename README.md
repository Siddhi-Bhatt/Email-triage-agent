# Smart Email Classifier & Rewriter

A Gen-AI powered FastAPI microservice that classifies emails into **Work**, **Personal**, **Finance**, or **Spam**, and rewrites emails in any requested tone — built for the Gen-AI Internship Technical Case Study.

**Live demo:** [https://email-triage-agentzip--sb4083070.replit.app/](https://email-triage-agentzip--sb4083070.replit.app/)

---

## Overview

| | |
|---|---|
| **LLM Provider** | [Groq](https://groq.com) |
| **Model** | `llama-3.1-8b-instant` |
| **Framework** | FastAPI |
| **Endpoints** | `POST /classify_email`, `POST /rewrite_email` |
| **Extras** | Minimal HTML/JS console, structured logging, custom error handling |

---

## Project Structure

```
email-triage-agent/
├── app/
│   ├── main.py                 # FastAPI app, routes, middleware, error handlers
│   ├── config.py               # Settings loaded from .env (pydantic-settings)
│   ├── logging_config.py       # Console + rotating file logging setup
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response models
│   └── services/
│       ├── llm_client.py       # Groq API wrapper
│       └── templates.py        # Prompt templates + prompt-design rationale
├── frontend/
│   └── index.html               # Minimal bonus UI, served at /app
├── logs/                        # Rotating log files (created at runtime)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup & Run

### 1. Clone and install

```bash
git clone <your-repo-url>
cd email-triage-agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your API key

Copy the example env file and add your [Groq API key](https://console.groq.com/keys):

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

The API is now live at `http://127.0.0.1:8000`.

- Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`
- Minimal frontend console: `http://127.0.0.1:8000/app`

---

## APIs Used

**Groq API** (`groq` Python SDK) — chosen for its very low-latency inference, which keeps the classify/rewrite round trip fast enough for an interactive console. The service talks to Groq through a single wrapper function, `call_llm()` in `app/services/llm_client.py`, so the rest of the app stays provider-agnostic — swapping in OpenAI/Anthropic later would mean editing one file, not every route.

---

## Endpoints

### `POST /classify_email`

Classifies raw email text into exactly one of `Work`, `Personal`, `Finance`, `Spam`.

**Request**
```json
{
  "email_content": "Hi, this is Sarah from Accounts Payable. Your invoice #4521 for $1,240.00 is due on June 28th. Please confirm receipt."
}
```

**Response**
```json
{
  "category": "Finance",
  "confidence_note": "Predicted by LLM-based classification."
}
```

### `POST /rewrite_email`

Rewrites email content in a specified tone while preserving all facts and intent.

**Request**
```json
{
  "email_content": "hey can u send me the report asap, kinda need it now",
  "tone": "professional"
}
```

**Response**
```json
{
  "original_email": "hey can u send me the report asap, kinda need it now",
  "tone": "professional",
  "rewritten_email": "Hi, could you please send over the report at your earliest convenience? I need it as soon as possible. Thank you."
}
```

### `GET /`

Health check — returns service status and the configured LLM provider/model.

```json
{ "status": "ok", "llm_provider": "groq:llama-3.1-8b-instant" }
```

---

## Prompt Design

Prompts live in `app/services/templates.py`, separate from route logic, so they can be reviewed and iterated on independently of the API code. Both prompts follow the same four-part structure:

1. **Role** — frames the model as a specific kind of expert (e.g. "email triage assistant") before it sees the task, narrowing its behavior up front.
2. **Task** — one unambiguous instruction, never a compound ask.
3. **Constraints** — explicit rules on output format, allowed values, and edge cases, so responses stay machine-parseable.
4. **Output spec** — the exact response shape expected (e.g. "respond with only one word"), so the API layer can parse it without fragile regex.

**Classification prompt** gives the model a short definition of *intent* for each category (not just bare labels), explicitly instructs it to judge by dominant intent rather than isolated keywords (so an email mentioning "invoice" between coworkers is still `Work`, not `Finance`), and forbids any explanation in the output to keep responses parseable. The API layer also normalizes the raw response against the category enum, with a fallback substring match in case the model wraps the label in extra text.

**Rewrite prompt** treats tone as a free-text parameter (not a fixed enum) since the brief's "e.g. professional, friendly" implies an open-ended set, and gives the model a generic process — *preserve meaning → adjust register → tighten phrasing* — so it generalizes to tones beyond the ones anticipated (e.g. "apologetic", "urgent"). It explicitly instructs the model to preserve every factual detail (names, dates, numbers, deadlines) since fact-dropping is the most common failure mode in tone-rewriting tasks, and to skip any "Here's your rewritten email:" preamble.

---

## Error Handling & Logging

- A custom `LLMServiceError` is raised on any Groq API failure and mapped to a `502` response, so upstream provider issues are distinguishable from internal bugs (`500`).
- All requests are logged with method, path, status code, and latency via middleware in `main.py`.
- Logs write to both console and a rotating file (`logs/app.log`, 2MB per file, 3 backups) via `app/logging_config.py`.

---

## Bonus Features Implemented

- ✅ **Minimal frontend** — a single-page HTML/JS console (`frontend/index.html`, served at `/app`) for classifying and rewriting emails without touching `curl` or Swagger.
- ✅ **Logging & error handling** — structured request logging, rotating file logs, and dedicated exception handlers for LLM vs. unexpected errors.

---

## Tech Stack

`FastAPI` · `Pydantic v2` / `pydantic-settings` · `Groq SDK` · `Uvicorn`
