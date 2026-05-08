import asyncio
import glob as _glob_mod
import os
from fastapi import APIRouter, Query

router = APIRouter(prefix="/search", tags=["search"])

WORKSPACE = os.environ.get("WORKSPACE_PATH", "/workspace")


def _safe(path: str) -> str:
    workspace = os.path.realpath(WORKSPACE)
    full = os.path.realpath(os.path.join(workspace, path.lstrip("/")))
    if not full.startswith(workspace):
        raise ValueError("Path outside workspace")
    return full


@router.get("/grep")
async def grep(
    pattern: str = Query(...),
    path: str = Query(default=""),
    recursive: bool = Query(default=True),
    case_sensitive: bool = Query(default=True),
):
    workspace = os.path.realpath(WORKSPACE)
    search_path = _safe(path) if path else workspace
    flags = ["-rn"] if recursive else ["-n"]
    if not case_sensitive:
        flags.append("-i")
    proc = await asyncio.create_subprocess_exec(
        "grep", *flags, pattern, search_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
    result = stdout.decode(errors="replace").replace(workspace + "/", "")
    lines = [l for l in result.strip().split("\n") if l]
    return {"matches": lines[:500], "total": len(lines), "truncated": len(lines) > 500}


@router.get("/glob")
def glob(pattern: str = Query(...)):
    workspace = os.path.realpath(WORKSPACE)
    matches = _glob_mod.glob(os.path.join(workspace, pattern), recursive=True)
    rel = sorted(os.path.relpath(m, workspace) for m in matches)
    return {"matches": rel[:500], "total": len(rel), "truncated": len(rel) > 500}
