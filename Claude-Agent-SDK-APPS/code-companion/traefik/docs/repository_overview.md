# Repository Overview

## What This Project Is

A Dockerized AI coding companion that exposes Claude Code's capabilities as a **REST API + browser UI**. It uses your existing Claude CLI subscription (no separate API key) and is designed to be called by other agents, automation scripts, and external projects — not just used directly in the browser.

---

## Directory Structure

```
claude-coding-companion/
│
├── main.py                     # FastAPI app: registers all routers, serves static UI
├── requirements.txt            # Python dependencies (no anthropic SDK — uses CLI)
├── Dockerfile                  # Python 3.12 + Node.js 22 + Claude CLI
├── docker-compose.yml          # Mounts workspace + ~/.claude credentials
├── .env                        # Your local config (CLAUDE_CONFIG_PATH, WORKSPACE_PATH)
├── .env.example                # Template for .env
├── AI_RULES.md                 # Rules and conventions for AI assistants
├── CLAUDE.md                   # Guidance for Claude Code when working in this repo
│
├── services/
│   ├── __init__.py
│   ├── claude_cli.py           # Core: subprocess wrapper around the Claude CLI
│   ├── sessions.py             # In-memory conversation session store
│   └── auth.py                 # Optional API key authentication middleware
│
├── routers/
│   ├── __init__.py
│   ├── chat.py                 # POST /chat — streaming chat with Claude
│   ├── agent.py                # POST /agent — agentic task runner
│   ├── commands.py             # POST /run — shell command execution
│   ├── files.py                # GET/POST/DELETE /files — file CRUD + upload
│   ├── sessions.py             # CRUD /sessions — conversation history
│   ├── search.py               # GET /search/grep + /search/glob
│   ├── debug.py                # GET /debug/claude — CLI diagnostics
│   └── docs_content.py         # GET /docs-content/* — serves markdown docs
│
├── static/
│   └── index.html              # Complete browser UI (single file, no build step)
│
├── docs/
│   ├── repository_overview.md  # This file — project structure and architecture
│   ├── explanation.md          # Feature-by-feature guide
│   └── api.md                  # Full API reference with examples
│
└── workspace/                  # Default host directory mounted as /workspace
```

---

## Key Files Explained

### `main.py`

The FastAPI application entry point. Loads environment variables from `.env`, registers all routers, adds the API key authentication middleware and CORS middleware, mounts the `static/` directory, and serves `index.html` at the root path. Exposes a `/health` endpoint for status checks.

### `services/claude_cli.py`

The heart of the project. Calls `claude -p "..." --output-format stream-json --verbose` as an async subprocess and parses the streaming JSON events into our internal event format. Two main functions:

- `stream_chat(messages, claude_session_id)` — for conversational chat
- `stream_agent(task, claude_session_id)` — for autonomous task execution

When a `claude_session_id` is available, it passes `--resume <id>` to continue conversations natively through the CLI's own session management.

### `services/sessions.py`

Simple in-memory dictionary of sessions. Each session stores:

- `messages` — conversation history (for context when no CLI session ID exists)
- `claude_session_id` — the Claude CLI's own session ID, used with `--resume` to continue conversations natively

Sessions are lost on container restart by design. No database is used.

### `services/auth.py`

Optional API key middleware. When the `API_KEY` environment variable is set, all non-public routes require the key via `X-API-Key` header or `Authorization: Bearer <key>`. Public routes (`/`, `/health`, `/docs`, `/static/*`) are always accessible. When `API_KEY` is blank, all requests pass through (dev mode).

### `routers/chat.py` and `routers/agent.py`

Both stream SSE events using `text/event-stream`. They look up the session's `claude_session_id` and pass `--resume <id>` to the CLI so the model maintains full conversation context on Claude's side.

### `routers/docs_content.py`

Serves the markdown documentation files from the `docs/` directory. Provides `GET /docs-content/list` to list available docs and `GET /docs-content/read?name=<file>` to read a specific doc. Used by the Docs tab in the browser UI.

### `static/index.html`

A single-file vanilla JS app with a futuristic terminal aesthetic. No framework, no build step. Uses vanilla JS with `fetch` + `ReadableStream` for SSE parsing. CDN-loaded libraries: `marked.js` for markdown rendering and `highlight.js` for syntax highlighting. Custom fonts: JetBrains Mono and Orbitron.

---

## Data Flow

```
Browser / External Agent
        │
        │  HTTP (REST + SSE)
        ▼
    FastAPI (main.py)
        │
    ┌───┴────────────────────────────────┐
    │  /chat   /agent   /run   /files    │
    │  /sessions  /search  /debug        │
    │  /docs-content                     │
    └───┬────────────────────────────────┘
        │
    services/claude_cli.py
        │
        │  subprocess (stdin/stdout/stderr)
        ▼
    Claude CLI (inside container)
        │
        │  OAuth (your subscription)
        ▼
    Anthropic API
```

---

## How Authentication Works

The Docker container mounts your host `~/.claude` directory (where the Claude CLI stores its OAuth token) to `/root/.claude` inside the container. The CLI reads credentials from there automatically — no API key needed, no login required inside the container.

If credentials are missing or expired, `GET /debug/claude` will show the error in stderr output.

The optional API key middleware (`services/auth.py`) is a separate layer that protects the web API itself — it does not affect Claude CLI authentication.

---

## Session Continuity

When you send a message through a named session:

1. First request: CLI runs fresh, returns a `session_id` in its result event
2. We store that `claude_session_id` in our session object
3. Next request: we pass `--resume <claude_session_id>` to the CLI
4. The CLI restores full conversation context from its own session store

This means the model sees the entire conversation history without us having to re-send it — the CLI manages the context window, compaction, and caching.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_CONFIG_PATH` | required | Path to your local `~/.claude` dir (e.g. `C:\Users\You\.claude` or `~/.claude`) |
| `WORKSPACE_PATH` | `./workspace` | Host path mounted as `/workspace` inside the container |
| `API_KEY` | (blank) | Optional API key to protect the web API. Blank = no auth (dev mode) |

---

## Docker Setup

The project runs via Docker Compose. The `docker-compose.yml` mounts three volumes:

- `.:/app` — the application code
- `${WORKSPACE_PATH}:/workspace` — the workspace directory
- `${CLAUDE_CONFIG_PATH}:/root/.claude` — your Claude CLI credentials

Traefik labels are included for optional reverse proxy / SSL termination. The app listens on port 8000 inside the container.