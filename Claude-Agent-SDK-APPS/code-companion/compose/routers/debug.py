"""
Debug endpoints to diagnose Claude CLI issues.
GET /debug/claude  - runs `claude --version` and a test prompt, shows raw output
"""

import asyncio
import os
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/debug", tags=["debug"])

WORKSPACE = os.environ.get("WORKSPACE_PATH", "/workspace")


async def _run_raw(cmd: list[str], timeout: int = 15) -> dict:
    """Run a command and return stdout, stderr, returncode."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKSPACE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }
    except asyncio.TimeoutError:
        return {"cmd": " ".join(cmd), "error": f"timed out after {timeout}s"}
    except FileNotFoundError:
        return {"cmd": " ".join(cmd), "error": "command not found"}
    except Exception as e:
        return {"cmd": " ".join(cmd), "error": str(e)}


@router.get("/claude", response_class=PlainTextResponse)
async def debug_claude():
    """Check if claude CLI is available and working."""
    lines = []

    # 1. which claude
    r = await _run_raw(["which", "claude"])
    lines.append(f"=== which claude ===\n{r.get('stdout') or r.get('error', '')}\n")

    # 2. version
    r = await _run_raw(["claude", "--version"])
    lines.append(f"=== claude --version ===\nstdout: {r.get('stdout','')}\nstderr: {r.get('stderr','')}\n")

    # 3. .claude dir
    claude_dir = "/root/.claude"
    exists = os.path.isdir(claude_dir)
    contents = os.listdir(claude_dir) if exists else []
    lines.append(f"=== /root/.claude ===\nexists: {exists}\ncontents: {contents}\n")

    # 4. test prompt with text output (simplest possible)
    r = await _run_raw(["claude", "-p", "Say exactly: HELLO", "--output-format", "text"], timeout=30)
    lines.append(f"=== test prompt (text format) ===\nreturncode: {r.get('returncode')}\nstdout: {r.get('stdout','')}\nstderr: {r.get('stderr','')}\nerror: {r.get('error','')}\n")

    # 5. test prompt with stream-json output
    r = await _run_raw(["claude", "-p", "Say exactly: HELLO", "--output-format", "stream-json"], timeout=30)
    lines.append(f"=== test prompt (stream-json format) ===\nreturncode: {r.get('returncode')}\nstdout: {r.get('stdout','')[:2000]}\nstderr: {r.get('stderr','')}\nerror: {r.get('error','')}\n")

    return "\n".join(lines)
