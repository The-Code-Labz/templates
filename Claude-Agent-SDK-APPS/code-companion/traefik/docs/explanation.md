# Feature Explanation

How each part of the app works, end to end.

---

## Chat

**Purpose:** Conversational back-and-forth with Claude. Maintains context across turns.

**How it works:**

1. You type a message and press Enter (or POST to `/chat`)
2. The browser opens a streaming `fetch` to `POST /chat`
3. The server calls `stream_chat()` which runs:
   ```
   claude -p "your message" --output-format stream-json --verbose
   ```
   Or with an existing session:
   ```
   claude --resume <session_id> -p "your message" --output-format stream-json --verbose
   ```
4. The CLI streams JSON events line by line. We parse each line and re-emit it as SSE
5. The browser receives `data: {"type":"text","text":"..."}` chunks and appends them to the message bubble in real time
6. Thinking blocks arrive as `{"type":"thinking","text":"..."}` and are shown collapsed with a toggle

**Session continuity:**

- Without a session: messages are stateless (each request is independent)
- With a session: the first response gives us a `claude_session_id`; subsequent messages use `--resume` so Claude remembers the full conversation
- You can create/switch sessions via the dropdown in the header

**Keyboard shortcuts:**

- `Enter` — send message
- `Shift+Enter` — newline

---

## Agent

**Purpose:** Give Claude a complex task and let it work autonomously — writing files, running commands, searching code, browsing the web.

**How it works:**

1. You describe a task in the Agent tab and press Execute (or POST to `/agent`)
2. The server calls `stream_agent()` which runs the same `claude -p "task"` command
3. The Claude CLI runs its own internal agent loop — this is the full Claude Code engine. It uses all its built-in tools: bash, file reading/writing, web search, grep, glob, etc.
4. As it works, it emits structured JSON events. We parse these and re-emit them as SSE:
   - `tool_start` — Claude is about to use a tool (shown as a collapsible card)
   - `tool_result` — the tool's output (shown inside the card, truncated to 1500 chars)
   - `thinking` — Claude's reasoning (shown collapsed by default)
   - `text` — Claude's final response text
5. When the agent finishes, the file tree auto-refreshes so you see any new/changed files

**What tools the agent has:**

Everything the Claude Code CLI has: bash, read/write/edit files, glob, grep, web fetch, web search, and more. You don't configure these — they're built into the CLI.

**Key difference from Chat:**

In Chat, Claude just responds with text. In Agent mode, Claude can take actions: create files, run tests, install packages, call APIs. It loops until the task is complete.

**Keyboard shortcuts:**

- `Ctrl+Enter` — execute task

---

## Explorer (File Tree)

**Purpose:** Browse and manage files in the `/workspace` directory.

**How it works:**

- On page load, calls `GET /files` to list the workspace root
- Folder items: clicking expands/collapses them by calling `GET /files?path=<dir>` and inserting child items indented below
- File items: clicking opens the file in the Editor tab
- Expand state is tracked in a `Set` so re-renders preserve open folders
- The refresh button (⟳) re-renders from root

**Uploading files:**

- Click the "↑ upload files" area to pick files from your machine
- Or drag files directly onto the sidebar
- Both call `POST /files/upload` (multipart form)
- Files land in `/workspace` root (or a subdirectory if specified via the API)

---

## Editor

**Purpose:** View and edit any file in the workspace directly in the browser.

**How it works:**

- **Open:** type a path in the top bar and click Open, or click any file in the Explorer
  - Calls `GET /files/read?path=<path>` and fills the textarea
- **Save:** click Save or press `Ctrl+S`
  - Calls `POST /files/write` with `{path, content}`
  - The file is written inside the Docker container's `/workspace`
  - Parent directories are created automatically
- **New file:** click New, type a path, write content, save

**Keyboard shortcuts:**

- `Tab` — inserts 2 spaces (doesn't move focus away)
- `Ctrl+S` / `Cmd+S` — saves the file

**Status bar:** Shows current line/column position, character count, and file extension.

**Limitations:**

- Plain textarea — no syntax highlighting in the editor itself
- Files over 1MB are rejected by the API (use the terminal for large files)

---

## Terminal

**Purpose:** Run shell commands directly inside the workspace container.

**How it works:**

- You type a command and press Enter (or click Run)
- Calls `POST /run {command, cwd}`
- The server runs it as a subprocess inside the container, in the directory you specify
- Stdout appears in white, stderr in red, exit code shown below
- 30-second timeout per command

**Working directory (cwd):**

- The cwd input field (left of the command box) is relative to `/workspace`
- Default is `/` which means `/workspace` root
- Type `myproject` to run in `/workspace/myproject`

**Command history:**

- Arrow Up/Down cycles through previous commands (current browser session only)

**What you can do:**

Anything available in the container: Python, Node.js, git, curl, wget, build tools, package managers, etc.

---

## Search

**Purpose:** Search across all files in the workspace.

**Two modes:**

**grep** — search file contents by regex pattern

- Calls `GET /search/grep?pattern=<regex>`
- Returns matching lines with filename and line number
- Click any result to open that file in the Editor
- Options: recursive (default true), case-sensitive (default true)
- Results truncated at 500 matches

**glob** — find files by name pattern

- Calls `GET /search/glob?pattern=<glob>`
- Returns matching file paths
- Click to open in Editor
- Supports recursive patterns with `**`
- Results truncated at 500 matches

---

## Docs

**Purpose:** Browse the project's markdown documentation directly in the browser.

**How it works:**

- On first visit, calls `GET /docs-content/list` to get available `.md` files from the `docs/` directory
- Selecting a doc calls `GET /docs-content/read?name=<file>` and renders it with `marked.js`
- Code blocks are syntax-highlighted with `highlight.js` (when available)
- The "API ↗" link in the sidebar header opens FastAPI's auto-generated Swagger UI at `/docs`

**Available documents:**

- **Repository Overview** — project structure and architecture
- **Feature Guide** — this document, explaining each feature
- **API Reference** — full endpoint documentation with examples

---

## Sessions

**Purpose:** Maintain conversation history across multiple chat/agent requests.

**How it works:**

- Sessions are named containers for conversation history
- Create one via the "+ new" button in the header
- Select it from the dropdown before sending messages
- The first Claude response gives us a `claude_session_id` which maps to the CLI's own session store
- Subsequent messages in that session use `--resume <claude_session_id>` so the model has full context

**Important:** Sessions are stored in-memory and are lost when the container restarts.

**API use:**

When calling from external agents, pass `session_id` in the request body to maintain context:

```json
POST /chat
{"messages": [{"role": "user", "content": "hello"}], "session_id": "your-session-uuid"}
```

Create a session first via `POST /sessions`, store the returned `id`, reuse it across calls.

---

## Authentication

**Purpose:** Optionally protect the web API with an API key.

**How it works:**

- Set the `API_KEY` environment variable in your `.env` file
- When set, all non-public routes require the key
- Send it via `X-API-Key` header or `Authorization: Bearer <key>`
- In the browser UI, paste the key into the "Auth" field in the header — it saves to localStorage
- When `API_KEY` is blank (default), all requests pass through without auth

**Public routes** (always accessible): `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/static/*`