# API Reference

Base URL: `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

All endpoints accept and return JSON unless noted. Streaming endpoints use Server-Sent Events (`text/event-stream`).

---

## Authentication

API key auth is controlled by the `API_KEY` environment variable in `.env`.

- **`API_KEY` is blank** — auth disabled (local dev mode, all requests pass)
- **`API_KEY` is set** — every request must include the key or receive `401`

**Send the key in one of two ways:**

```
X-API-Key: your-secret-key
```

```
Authorization: Bearer your-secret-key
```

**Public routes** (no key needed even when auth is enabled): `GET /`, `GET /health`, `GET /docs`, `GET /redoc`, `GET /openapi.json`, `GET /static/*`

**Setting your key in the browser UI:** paste it into the "Auth" field in the top header — it saves to localStorage and is sent automatically on every request.

---

## Health

### `GET /health`

Check server status.

**Response:**

```json
{
  "status": "ok",
  "workspace": "/workspace",
  "claude_config": true
}
```

- `claude_config: false` means `/root/.claude` is missing — check your `CLAUDE_CONFIG_PATH` in `.env`.

---

## Chat

### `POST /chat`

Stream a conversational response from Claude. Returns Server-Sent Events.

**Request body:**

```json
{
  "messages": [
    {"role": "user", "content": "Explain async/await in Python"}
  ],
  "session_id": "optional-session-uuid"
}
```

- `messages` — array of message objects with `role` ("user" or "assistant") and `content`
- `session_id` — optional, links to a session for context continuity

**SSE event stream:**

Each line is `data: <json>\n\n`. Event types:

| `type` | Fields | Description |
|---|---|---|
| `thinking` | `text` | Claude's internal reasoning (extended thinking) |
| `text` | `text` | Response text chunk |
| `raw_text` | `text` | Non-JSON CLI output (usually harmless) |
| `error` | `text` | CLI error (stderr) |
| `done` | — | Stream complete |

**Example — curl:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}' \
  --no-buffer
```

**Example — Python:**

```python
import httpx
import json

def chat(message, session_id=None):
    body = {"messages": [{"role": "user", "content": message}]}
    if session_id:
        body["session_id"] = session_id

    with httpx.stream("POST", "http://localhost:8000/chat", json=body) as r:
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            if payload["type"] == "text":
                print(payload["text"], end="", flush=True)
            elif payload["type"] == "done":
                break
```

**Multi-turn with sessions:**

```python
import httpx

# Create a session once
session = httpx.post("http://localhost:8000/sessions", json={"name": "my-agent"}).json()
sid = session["id"]

# All subsequent calls maintain context
chat("My name is Alex", session_id=sid)
chat("What's my name?", session_id=sid)  # Claude remembers "Alex"
```

---

## Agent

### `POST /agent`

Run an autonomous task. Claude uses its built-in tools (bash, file ops, web search, etc.) in a loop until the task is complete. Returns Server-Sent Events.

**Request body:**

```json
{
  "task": "Create a Flask API with /health and /users endpoints, add pytest tests, run them",
  "session_id": "optional-session-uuid"
}
```

- `task` — description of the task for Claude to complete autonomously
- `session_id` — optional, links to a session for context continuity

**SSE event stream:**

| `type` | Fields | Description |
|---|---|---|
| `thinking` | `text` | Claude's reasoning before acting |
| `text` | `text` | Claude's response / summary text |
| `tool_start` | `name`, `input` | Claude is about to call a tool |
| `tool_result` | `name`, `output` | Tool execution result (truncated to 1500 chars) |
| `raw_text` | `text` | Non-JSON CLI output |
| `error` | `text` | CLI error |
| `done` | — | Agent finished |

**Example — curl:**

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a hello world Python script in /workspace"}' \
  --no-buffer
```

**Example — Python:**

```python
import httpx
import json

def run_agent(task, session_id=None):
    body = {"task": task}
    if session_id:
        body["session_id"] = session_id

    with httpx.stream("POST", "http://localhost:8000/agent", json=body, timeout=300) as r:
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            t = payload["type"]
            if t == "text":
                print(payload["text"], end="")
            elif t == "tool_start":
                print(f"\n[tool: {payload['name']}]")
            elif t == "tool_result":
                print(f"  -> {payload['output'][:200]}")
            elif t == "done":
                break

run_agent("Write a Python web scraper for news headlines")
```

---

## Commands

### `POST /run`

Run a shell command inside the workspace container.

**Request body:**

```json
{
  "command": "pytest tests/ -v",
  "cwd": "/"
}
```

- `command` — the shell command to execute
- `cwd` — working directory relative to `/workspace` (default: `/workspace` root)

**Response:**

```json
{
  "stdout": "collected 5 items\n...\n5 passed",
  "stderr": "",
  "returncode": 0
}
```

**Timeout:** 30 seconds. Returns HTTP 408 if exceeded.

**Path safety:** `cwd` must resolve to a path inside `/workspace`. Paths outside are rejected with HTTP 400.

**Examples:**

```bash
# Install a package
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"command": "pip install requests"}'

# Run git commands
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"command": "git log --oneline -10", "cwd": "myrepo"}'

# Run tests
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"command": "npm test", "cwd": "frontend"}'
```

---

## Files

### `GET /files`

List directory contents.

**Query params:**

- `path` — optional, relative to `/workspace` (default: workspace root)

**Response:**

```json
{
  "path": "myproject",
  "entries": [
    {"name": "src", "type": "dir", "size": null},
    {"name": "main.py", "type": "file", "size": 1234}
  ]
}
```

---

### `GET /files/read`

Read a file's contents.

**Query params:**

- `path` — required, relative to `/workspace`

**Response:**

```json
{
  "path": "myproject/main.py",
  "content": "def main():\n    print('hello')\n"
}
```

**Limit:** 1MB. Files larger than 1,000,000 bytes return HTTP 413. Use `/run` with `cat` or `head` for larger files.

---

### `POST /files/write`

Create or overwrite a file.

**Request body:**

```json
{
  "path": "myproject/config.json",
  "content": "{\"debug\": true}"
}
```

**Response:**

```json
{
  "path": "myproject/config.json",
  "written": true,
  "size": 14
}
```

Parent directories are created automatically.

---

### `DELETE /files`

Delete a file.

**Query params:**

- `path` — required, relative to `/workspace`

**Response:**

```json
{
  "path": "myproject/old.py",
  "deleted": true
}
```

Directories cannot be deleted via this endpoint. Use `POST /run` with `rm -rf` instead.

---

### `POST /files/upload`

Upload a file from your machine into the workspace.

**Request:** multipart form data

- `file` — the file to upload (required)
- `path` — destination directory relative to `/workspace` (optional, defaults to root)

**Response:**

```json
{
  "path": "data/dataset.csv",
  "filename": "dataset.csv",
  "size": 204800
}
```

**Example — curl:**

```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@./mydata.csv" \
  -F "path=data"
```

**Example — Python:**

```python
import httpx

with open("mydata.csv", "rb") as f:
    r = httpx.post(
        "http://localhost:8000/files/upload",
        files={"file": ("mydata.csv", f, "text/csv")},
        data={"path": "data"}
    )
print(r.json())
```

---

## Search

### `GET /search/grep`

Search file contents with a regex pattern.

**Query params:**

- `pattern` — required, regex pattern
- `path` — optional, subdirectory to search in (relative to `/workspace`)
- `recursive` — optional, default `true`
- `case_sensitive` — optional, default `true`

**Response:**

```json
{
  "matches": [
    "src/auth.py:42:def login(username, password):",
    "src/auth.py:67:def logout(session_id):"
  ],
  "total": 2,
  "truncated": false
}
```

Results are truncated at 500 matches. File paths in results are relative to `/workspace`.

**Examples:**

```bash
# Find all TODO comments
GET /search/grep?pattern=TODO

# Find function definitions (case-insensitive)
GET /search/grep?pattern=def%20.*&case_sensitive=false

# Search only in a subdirectory
GET /search/grep?pattern=import%20requests&path=src
```

---

### `GET /search/glob`

Find files by name pattern.

**Query params:**

- `pattern` — required, glob pattern (supports `**` for recursive matching)

**Response:**

```json
{
  "matches": ["src/main.py", "src/utils.py", "tests/test_main.py"],
  "total": 3,
  "truncated": false
}
```

Results are truncated at 500 matches.

**Examples:**

```bash
GET /search/glob?pattern=**/*.py        # all Python files
GET /search/glob?pattern=**/*.test.js   # all JS test files
GET /search/glob?pattern=**/config.*    # all config files
```

---

## Sessions

### `POST /sessions`

Create a new conversation session.

**Request body:**

```json
{
  "name": "feature-x-agent"
}
```

- `name` — optional, auto-generated if omitted (e.g. "Session 1")

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "feature-x-agent",
  "messages": [],
  "claude_session_id": null,
  "created_at": "2025-01-15T10:30:00+00:00"
}
```

---

### `GET /sessions`

List all sessions.

**Response:**

```json
[
  {
    "id": "550e8400-...",
    "name": "feature-x-agent",
    "message_count": 6,
    "claude_session_id": "abc123",
    "created_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `GET /sessions/{id}`

Get a session with full message history.

**Response:**

```json
{
  "id": "550e8400-...",
  "name": "feature-x-agent",
  "messages": [
    {"role": "user", "content": "Create a login endpoint"},
    {"role": "assistant", "content": "I'll create that for you..."}
  ],
  "claude_session_id": "abc123",
  "created_at": "2025-01-15T10:30:00+00:00"
}
```

---

### `DELETE /sessions/{id}`

Delete a session.

**Response:**

```json
{
  "deleted": true
}
```

---

## Docs Content

### `GET /docs-content/list`

List available markdown documentation files.

**Response:**

```json
{
  "files": ["api.md", "explanation.md", "repository_overview.md"]
}
```

---

### `GET /docs-content/read`

Read a documentation file.

**Query params:**

- `name` — required, filename (must end in `.md`, no path separators allowed)

**Response:**

```json
{
  "name": "api.md",
  "content": "# API Reference\n\n..."
}
```

---

## Debug

### `GET /debug/claude`

Diagnose Claude CLI setup. Returns **plain text** (not JSON) showing:

- Whether `claude` is in PATH (`which claude`)
- CLI version (`claude --version`)
- Contents of `/root/.claude` directory
- Raw output of a test prompt in text format
- Raw output of a test prompt in stream-json format

Use this when chat/agent returns nothing or errors.

---

## Integration Patterns

### Pattern 1: One-off task from another agent

```python
import httpx
import json

def delegate_task(task):
    """Send a task to the companion and wait for the full result."""
    result_text = []
    with httpx.stream("POST", "http://localhost:8000/agent",
                      json={"task": task}, timeout=300) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                ev = json.loads(line[6:])
                if ev["type"] == "text":
                    result_text.append(ev["text"])
    return "".join(result_text)

result = delegate_task("Refactor the authentication module to use JWT tokens")
```

### Pattern 2: Persistent coding session

```python
import httpx
import json

class CodingSession:
    def __init__(self, name, base_url="http://localhost:8000"):
        self.base = base_url
        r = httpx.post(f"{base_url}/sessions", json={"name": name})
        self.session_id = r.json()["id"]

    def chat(self, message):
        chunks = []
        body = {
            "messages": [{"role": "user", "content": message}],
            "session_id": self.session_id
        }
        with httpx.stream("POST", f"{self.base}/chat", json=body, timeout=120) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    ev = json.loads(line[6:])
                    if ev["type"] == "text":
                        chunks.append(ev["text"])
        return "".join(chunks)

    def run(self, command):
        return httpx.post(f"{self.base}/run", json={"command": command}).json()

    def write_file(self, path, content):
        httpx.post(f"{self.base}/files/write", json={"path": path, "content": content})

    def read_file(self, path):
        return httpx.get(f"{self.base}/files/read", params={"path": path}).json()["content"]

# Usage
session = CodingSession("my-project")
session.chat("I want to build a REST API in Python with FastAPI")
session.chat("Add authentication with JWT tokens")
result = session.run("pytest tests/ -v")
print(result["stdout"])
```

### Pattern 3: File-based handoff

```python
import httpx

# Another agent writes a spec file, this agent implements it
httpx.post("http://localhost:8000/files/write", json={
    "path": "TASK.md",
    "content": "## Task\nImplement the user registration endpoint as described in spec.md"
})

# Let the agent handle it
with httpx.stream("POST", "http://localhost:8000/agent", json={
    "task": "Read TASK.md and spec.md, implement everything described, run the tests"
}, timeout=300) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "text":
                print(ev["text"], end="")
```

---

## Complete Endpoint Summary

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `GET` | `/` | — | HTML UI |
| `GET` | `/health` | — | `{status, workspace, claude_config}` |
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
| `GET` | `/docs-content/list` | — | `{files}` |
| `GET` | `/docs-content/read` | `?name=` | `{name, content}` |
| `GET` | `/debug/claude` | — | plain text diagnostics |