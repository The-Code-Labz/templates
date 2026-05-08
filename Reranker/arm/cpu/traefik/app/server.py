import os
from typing import List, Union, Optional
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, field_validator
from sentence_transformers import CrossEncoder

MODEL_ID = os.getenv("MODEL_ID", "BAAI/bge-reranker-v2-m3")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
API_KEY = os.getenv("RERANK_API_KEY", "").strip()

# threading hints
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("INTRA_OP_THREADS", "1")
os.environ.setdefault("INTER_OP_THREADS", "1")
if HF_TOKEN:
    os.environ["HUGGING_FACE_HUB_TOKEN"] = HF_TOKEN

app = FastAPI(title="Local Reranker", version="1.0.0")
model = CrossEncoder(MODEL_ID, token=HF_TOKEN if HF_TOKEN else None)

class Doc(BaseModel):
    text: str

class RerankReq(BaseModel):
    query: str
    # Accept strings OR {"text": "..."} objects; include optional cohere-style fields
    documents: List[Union[str, Doc]]
    top_n: Optional[int] = None
    model: Optional[str] = None
    return_documents: Optional[bool] = None
    api_key: Optional[str] = None  # allow key in body as last resort

    @field_validator("documents", mode="before")
    @classmethod
    def coerce_documents(cls, v):
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            raise ValueError("documents must be a list of strings or objects with 'text'")
        return v

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "auth_required": bool(API_KEY)}

def check_api_key(
    authorization: Optional[str],
    x_api_key: Optional[str],
    query_key: Optional[str],
    body_key: Optional[str],
):
    """
    Accept any of:
      - Authorization: Bearer <key>
      - Authorization: <key>
      - X-API-Key: <key>
      - ?api_key=<key>
      - JSON body { "api_key": "<key>" }
    If RERANK_API_KEY is unset, auth is disabled.
    """
    if not API_KEY:
        return  # no auth enforced

    # Headers
    if authorization:
        val = authorization.strip()
        if val.lower().startswith("bearer "):
            token = val.split(" ", 1)[1].strip()
            if token == API_KEY:
                return
        # raw token (no Bearer)
        if val == API_KEY:
            return

    if x_api_key and x_api_key.strip() == API_KEY:
        return

    # Query/body
    if query_key and query_key.strip() == API_KEY:
        return
    if body_key and body_key.strip() == API_KEY:
        return

    raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/v1/rerank")
async def rerank(
    req: RerankReq,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    api_key: Optional[str] = None,  # query param (?api_key=)
):
    # query param
    q_key = api_key
    # body key (if provided)
    b_key = req.api_key

    check_api_key(authorization, x_api_key, q_key, b_key)

    # Normalize to list[str]
    docs_text: List[str] = []
    for d in req.documents:
        docs_text.append(d if isinstance(d, str) else d.text)

    pairs = [(req.query, d) for d in docs_text]
    scores = model.predict(pairs, batch_size=BATCH_SIZE)

    results = [{"index": i, "relevance_score": float(s)} for i, s in enumerate(scores)]
    if req.top_n is not None:
        results = sorted(results, key=lambda r: r["relevance_score"], reverse=True)[: max(0, req.top_n)]
    return {"results": results}
