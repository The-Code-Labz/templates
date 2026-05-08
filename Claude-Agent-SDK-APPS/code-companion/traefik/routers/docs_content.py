import os
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/docs-content", tags=["docs"])

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")


@router.get("/list")
def list_docs():
    if not os.path.isdir(DOCS_DIR):
        return {"files": []}
    files = sorted(f for f in os.listdir(DOCS_DIR) if f.endswith(".md"))
    return {"files": files}


@router.get("/read")
def read_doc(name: str = Query(...)):
    if "/" in name or "\\" in name or not name.endswith(".md"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(DOCS_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Doc not found")
    with open(path, "r", errors="replace") as f:
        return {"name": name, "content": f.read()}
