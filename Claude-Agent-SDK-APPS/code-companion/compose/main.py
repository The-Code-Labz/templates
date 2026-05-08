from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import chat, commands, files, agent, sessions, search, debug, docs_content
from services.auth import ApiKeyMiddleware
import os

app = FastAPI(
    title="Claude Coding Companion",
    version="1.0.0",
    description="AI coding companion powered by the Claude CLI subscription. Full REST API for agent ecosystem integration.",
)

# API key auth — must be added before CORS so preflight OPTIONS also pass through
app.add_middleware(ApiKeyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(commands.router)
app.include_router(files.router)
app.include_router(agent.router)
app.include_router(sessions.router)
app.include_router(search.router)
app.include_router(debug.router)
app.include_router(docs_content.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "workspace": os.environ.get("WORKSPACE_PATH", "/workspace"),
        "claude_config": os.path.exists("/root/.claude"),
    }


@app.get("/")
def index():
    return FileResponse("static/index.html")
