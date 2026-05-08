from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services import sessions as svc

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateRequest(BaseModel):
    name: Optional[str] = None


@router.post("")
def create_session(body: CreateRequest = CreateRequest()):
    return svc.create_session(body.name)


@router.get("")
def list_sessions():
    return svc.list_sessions()


@router.get("/{sid}")
def get_session(sid: str):
    session = svc.get_session(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{sid}")
def delete_session(sid: str):
    if not svc.delete_session(sid):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}
