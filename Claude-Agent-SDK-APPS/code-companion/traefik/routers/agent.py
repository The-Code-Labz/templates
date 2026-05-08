import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from services.claude_cli import stream_agent
from services import sessions as session_svc

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    task: str
    session_id: Optional[str] = None


@router.post("")
async def agent(request: AgentRequest):
    session = None
    claude_session_id = None

    if request.session_id:
        session = session_svc.get_session(request.session_id)
        if session:
            claude_session_id = session.get("claude_session_id")

    async def generate():
        collected_text = []

        async for event in stream_agent(request.task, claude_session_id):
            etype = event["type"]

            if etype == "text":
                collected_text.append(event["text"])
                yield f"data: {json.dumps(event)}\n\n"

            elif etype in ("thinking", "tool_start", "tool_result", "error"):
                yield f"data: {json.dumps(event)}\n\n"

            elif etype == "done":
                new_cli_sid = event.get("claude_session_id")

                if request.session_id and session:
                    session_svc.append_message(request.session_id, "user", request.task)
                    if collected_text:
                        session_svc.append_message(request.session_id, "assistant", "".join(collected_text))
                    if new_cli_sid:
                        session_svc.set_claude_session_id(request.session_id, new_cli_sid)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
