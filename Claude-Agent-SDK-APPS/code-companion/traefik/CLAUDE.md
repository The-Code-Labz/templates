# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A full-stack AI coding companion: a FastAPI server running in Docker that exposes both a browser UI and a complete REST API. Powered by the **Claude Code CLI** (uses your Claude subscription — no API key needed). The UI replicates Claude Code's core features (chat, agentic task runner, file editor, terminal, search). The API is designed for integration with external agents and automation pipelines.

## Commands

```bash
# Start with Docker (primary)
cp .env.example .env        # set CLAUDE_CONFIG_PATH to your ~/.claude dir
docker compose up --build

# Start locally (no Docker — workspace ops will use ./workspace)
pip install -r requirements.txt
uvicorn main:app --reload

# API at http://localhost:8000
# UI  at http://localhost:8000/
# Docs at http://localhost:8000/docs
```

## Architecture

```
main.py                  FastAPI app entry point, mounts all routers + static UI
services/
  claude_cli.py          Claude CLI subprocess wrapper: stream_chat() and stream_agent()
  sessions.py            In-memory session store; stores claude_session_id for --resume
routers/
  chat.py                POST /chat         — streaming SSE chat with optional session
  agent.py               POST /agent        — agentic loop with tools, streaming SSE
  commands.py            POST /run          — shell command execution in workspace
  files.py               GET/POST/DELETE    — file CRUD + multipart upload
  search.py              GET /search/grep   — regex search
                         GET /search/glob   — file pattern search
  sessions.py            CRUD /sessions     — conversation history management
static/
  index.html             Single-file web UI (no build step, vanilla JS)
workspace/               Volume-mounted at /workspace inside container
```

**Claude CLI integration:** `services/claude_cli.py` calls `claude -p "prompt" --output-format stream-json --print` as an async subprocess. The CLI uses your OAuth credentials from the mounted `~/.claude` directory. For subsequent turns in a session, `--resume <claude_session_id>` is passed so the CLI maintains full conversation history on its side.

**Agent mode:** the CLI's own agent loop handles all tool execution (bash, file ops, web search, etc.) internally. `stream_agent()` parses the `stream-json` events and re-emits them as our SSE format — so external consumers can see tool calls and results.

**Tool safety for file/terminal endpoints:** all Python-side file and command operations resolve paths with `os.path.realpath()` and assert the result starts with the workspace root before executing.

**Streaming format (SSE):** all streaming endpoints emit `data: {type, ...}\n\n` events. Chat and agent share the same event types:
- `{type: "thinking", text: "..."}` — adaptive thinking delta
- `{type: "text", text: "..."}` — response text delta
- `{type: "tool_start", name: "..."}` — agent tool invocation beginning
- `{type: "tool_result", name: "...", output: "..."}` — tool result preview (≤1000 chars)
- `{type: "done"}` — stream complete

## Agent Tools

The agent uses the **Claude Code CLI's built-in tools** — the same set available in the `claude` CLI: bash, file read/write/edit, glob, grep, web search/fetch, and more. No custom tool implementation needed; the CLI handles its own tool loop.

## Full API Reference

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `GET` | `/` | — | HTML UI |
| `GET` | `/health` | — | `{status, workspace}` |
| `POST` | `/chat` | `{messages, session_id?}` | SSE stream |
| `POST` | `/agent` | `{task, session_id?}` | SSE stream |
| `POST` | `/run` | `{command, cwd?}` | `{stdout, stderr, returncode}` |
| `GET` | `/files` | `?path=` | directory listing |
| `GET` | `/files/read` | `?path=` | `{path, content}` |
| `POST` | `/files/write` | `{path, content}` | `{path, written, size}` |
| `DELETE` | `/files` | `?path=` | `{path, deleted}` |
| `POST` | `/files/upload` | multipart `file`, `path?` | `{path, filename, size}` |
| `GET` | `/search/grep` | `?pattern=&path?=&recursive?=&case_sensitive?=` | `{matches, total, truncated}` |
| `GET` | `/search/glob` | `?pattern=` | `{matches, total, truncated}` |
| `POST` | `/sessions` | `{name?}` | session object |
| `GET` | `/sessions` | — | list of session summaries |
| `GET` | `/sessions/{id}` | — | session with full message history |
| `DELETE` | `/sessions/{id}` | — | `{deleted}` |

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_CONFIG_PATH` | required | Path to your local `~/.claude` dir (e.g. `C:\Users\You\.claude`) |
| `WORKSPACE_PATH` | `./workspace` | Host path mounted as `/workspace` inside the container |

## Key Constraints

- Sessions are **in-memory** — they reset on container restart. Add Redis/SQLite if persistence is needed.
- File operations enforce a **workspace boundary** — paths outside `/workspace` are rejected with 400.
- Agent tool results are **truncated to 1000 chars** in SSE previews; full output goes to Claude's context.
- Large files (>1MB via `/files/read`, >500KB via agent `read_file`) are rejected — use `grep` or `bash` instead.
- Command timeout is **60s** for agent bash tool, **30s** for `/run` endpoint.
