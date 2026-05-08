import asyncio
import os
import shlex
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/run", tags=["commands"])

WORKSPACE = os.environ.get("WORKSPACE_PATH", "/workspace")
TIMEOUT = 30


class CommandRequest(BaseModel):
    command: str
    cwd: str = WORKSPACE


class CommandResult(BaseModel):
    stdout: str
    stderr: str
    returncode: int


@router.post("", response_model=CommandResult)
async def run_command(request: CommandRequest):
    cwd = os.path.realpath(request.cwd)
    workspace = os.path.realpath(WORKSPACE)

    if not cwd.startswith(workspace):
        raise HTTPException(status_code=400, detail="cwd must be inside workspace")

    try:
        proc = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
        return CommandResult(
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            returncode=proc.returncode,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(status_code=408, detail=f"Command timed out after {TIMEOUT}s")
