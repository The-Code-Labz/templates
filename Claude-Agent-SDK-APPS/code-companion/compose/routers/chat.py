import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from services.claude_cli import stream_chat
from services import sessions as session_svc

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: Optional[str] = None


@router.post("")
async def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]
    session = None
    claude_session_id = None

    if request.session_id:
        session = session_svc.get_session(request.session_id)
        if session:
            # Prepend stored history so context is maintained when no --resume available
            history = [{"role": m["role"], "content": m["content"]} for m in session["messages"]]
            messages = history + messages
            claude_session_id = session.get("claude_session_id")

    async def generate():
        collected_text = []

        async for event in stream_chat(messages, claude_session_id):
            etype = event["type"]

            if etype in ("thinking", "text", "error"):
                if etype == "text":
                    collected_text.append(event["text"])
                yield f"data: {json.dumps(event)}\n\n"

            elif etype == "done":
                new_cli_sid = event.get("claude_session_id")

                if request.session_id and session:
                    user_text = request.messages[-1].content
                    session_svc.append_message(request.session_id, "user", user_text)
                    session_svc.append_message(request.session_id, "assistant", "".join(collected_text))
                    if new_cli_sid:
                        session_svc.set_claude_session_id(request.session_id, new_cli_sid)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
