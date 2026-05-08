import os
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/files", tags=["files"])

WORKSPACE = os.environ.get("WORKSPACE_PATH", "/workspace")


def _safe(path: str) -> str:
    workspace = os.path.realpath(WORKSPACE)
    full = os.path.realpath(os.path.join(workspace, path.lstrip("/")))
    if not full.startswith(workspace):
        raise HTTPException(status_code=400, detail="Path outside workspace")
    return full


@router.get("")
def list_files(path: str = Query(default="")):
    target = _safe(path) if path else os.path.realpath(WORKSPACE)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Path not found")
    if not os.path.isdir(target):
        raise HTTPException(status_code=400, detail="Not a directory")
    entries = []
    for name in sorted(os.listdir(target)):
        fp = os.path.join(target, name)
        entries.append({
            "name": name,
            "type": "dir" if os.path.isdir(fp) else "file",
            "size": os.path.getsize(fp) if os.path.isfile(fp) else None,
        })
    return {"path": path or "/", "entries": entries}


@router.get("/read")
def read_file(path: str = Query(...)):
    target = _safe(path)
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="File not found")
    size = os.path.getsize(target)
    if size > 1_000_000:
        raise HTTPException(status_code=413, detail=f"File too large ({size} bytes)")
    with open(target, "r", errors="replace") as f:
        return {"path": path, "content": f.read()}


class WriteRequest(BaseModel):
    path: str
    content: str


@router.post("/write")
def write_file(request: WriteRequest):
    target = _safe(request.path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w") as f:
        f.write(request.content)
    return {"path": request.path, "written": True, "size": len(request.content)}


@router.delete("")
def delete_file(path: str = Query(...)):
    target = _safe(path)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Not found")
    if os.path.isdir(target):
        raise HTTPException(status_code=400, detail="Use bash to delete directories")
    os.remove(target)
    return {"path": path, "deleted": True}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: Optional[str] = Form(default=""),
):
    dest_dir = _safe(path) if path else os.path.realpath(WORKSPACE)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    if not os.path.isdir(dest_dir):
        raise HTTPException(status_code=400, detail="Upload path is not a directory")

    dest = os.path.join(dest_dir, os.path.basename(file.filename))
    content = await file.read()
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    rel = os.path.relpath(dest, os.path.realpath(WORKSPACE))
    return {"path": rel, "filename": file.filename, "size": len(content)}
