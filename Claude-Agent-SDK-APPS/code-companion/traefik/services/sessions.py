import uuid
from datetime import datetime, timezone
from typing import Optional

_sessions: dict[str, dict] = {}


def create_session(name: Optional[str] = None) -> dict:
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "name": name or f"Session {len(_sessions) + 1}",
        "messages": [],
        "claude_session_id": None,  # Claude CLI's own session ID for --resume
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _sessions[sid] = session
    return session


def get_session(sid: str) -> Optional[dict]:
    return _sessions.get(sid)


def list_sessions() -> list[dict]:
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "created_at": s["created_at"],
            "message_count": len(s["messages"]),
            "claude_session_id": s.get("claude_session_id"),
        }
        for s in _sessions.values()
    ]


def delete_session(sid: str) -> bool:
    if sid in _sessions:
        del _sessions[sid]
        return True
    return False


def append_message(sid: str, role: str, content: str) -> bool:
    session = _sessions.get(sid)
    if session is None:
        return False
    session["messages"].append({"role": role, "content": content})
    return True


def set_claude_session_id(sid: str, claude_sid: str) -> bool:
    """Store the Claude CLI session ID so we can resume with --resume."""
    session = _sessions.get(sid)
    if session is None:
        return False
    session["claude_session_id"] = claude_sid
    return True


def get_claude_session_id(sid: str) -> Optional[str]:
    session = _sessions.get(sid)
    return session.get("claude_session_id") if session else None
