"""
Wrapper around the Claude Code CLI subprocess.

The CLI uses the user's OAuth subscription (no API key needed).
Credentials are read from /root/.claude (mounted from the host ~/.claude dir).

Claude CLI print-mode syntax:
  claude -p "prompt"                          # -p IS the print flag + prompt
  claude -p "prompt" --output-format text     # plain text output
  claude -p "prompt" --output-format stream-json  # streaming JSON events

Stream-JSON event types:
  system     - init info (model, tools, session_id)
  assistant  - model output (content blocks: text, thinking, tool_use)
  tool       - tool execution result
  result     - final summary (session_id, cost, duration)
"""

import asyncio
import json
import logging
import os
from typing import AsyncIterator

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("WORKSPACE_PATH", "/workspace")
CLAUDE_CMD = "claude"


async def _run(args: list[str]) -> AsyncIterator[dict]:
    """
    Run `claude <args> --output-format stream-json` and yield parsed JSON events.
    Stderr is captured and emitted as {type: "error"} after the process exits.
    """
    # Note: -p already enables print mode AND takes the prompt argument.
    # Do NOT add --print again — it causes duplicate-flag errors.
    cmd = [CLAUDE_CMD] + args + ["--output-format", "stream-json", "--verbose"]
    log.info("Running: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKSPACE,
        )
    except FileNotFoundError:
        yield {"type": "error", "text": "claude CLI not found. Is it installed in the container?"}
        return

    async for raw in proc.stdout:
        line = raw.decode(errors="replace").strip()
        if not line:
            continue
        log.debug("CLI stdout: %s", line[:200])
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            # Non-JSON output (e.g. progress text) — surface as raw text
            yield {"type": "raw_text", "text": line}

    stderr_bytes = await proc.stderr.read()
    await proc.wait()

    stderr = stderr_bytes.decode(errors="replace").strip()
    if stderr:
        log.warning("CLI stderr: %s", stderr)
        yield {"type": "error", "text": stderr}

    log.info("CLI exited with code %d", proc.returncode)


async def stream_chat(messages: list[dict], claude_session_id: str | None = None) -> AsyncIterator[dict]:
    """
    Stream a chat response.

    Yields: {type: "thinking"|"text"|"raw_text"|"error"|"done", ...}
    """
    last_msg = messages[-1]["content"] if messages else ""

    if claude_session_id:
        args = ["--resume", claude_session_id, "-p", last_msg]
    else:
        history = messages[:-1]
        if history:
            hist_lines = []
            for m in history:
                role = "User" if m["role"] == "user" else "Assistant"
                hist_lines.append(f"{role}: {m['content']}")
            prompt = "<conversation_history>\n" + "\n\n".join(hist_lines) + "\n</conversation_history>\n\nUser: " + last_msg
        else:
            prompt = last_msg
        args = ["-p", prompt]

    new_cli_session_id = None

    async for event in _run(args):
        etype = event.get("type")

        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                btype = block.get("type")
                if btype == "thinking":
                    yield {"type": "thinking", "text": block.get("thinking", "")}
                elif btype == "text":
                    yield {"type": "text", "text": block.get("text", "")}

        elif etype == "result":
            new_cli_session_id = event.get("session_id")

        elif etype in ("error", "raw_text"):
            yield event

    yield {"type": "done", "claude_session_id": new_cli_session_id}


async def stream_agent(task: str, claude_session_id: str | None = None) -> AsyncIterator[dict]:
    """
    Run an agentic task using the Claude CLI's built-in agent loop.

    Yields: {type: "thinking"|"text"|"tool_start"|"tool_result"|"raw_text"|"error"|"done", ...}
    """
    if claude_session_id:
        args = ["--resume", claude_session_id, "-p", task]
    else:
        args = ["-p", task]

    new_cli_session_id = None

    async for event in _run(args):
        etype = event.get("type")

        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                btype = block.get("type")
                if btype == "thinking":
                    yield {"type": "thinking", "text": block.get("thinking", "")}
                elif btype == "text":
                    yield {"type": "text", "text": block.get("text", "")}
                elif btype == "tool_use":
                    yield {
                        "type": "tool_start",
                        "name": block.get("name", "tool"),
                        "input": block.get("input", {}),
                    }

        elif etype == "tool":
            name = event.get("name", "tool")
            result = event.get("result", {})
            content = result.get("content", [])
            if isinstance(content, list):
                output = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
            else:
                output = str(content)
            yield {"type": "tool_result", "name": name, "output": output[:1500]}

        elif etype == "result":
            new_cli_session_id = event.get("session_id")

        elif etype in ("error", "raw_text"):
            yield event

    yield {"type": "done", "claude_session_id": new_cli_session_id}
