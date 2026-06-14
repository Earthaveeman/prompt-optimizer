import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from optimizer import get_optimizer, list_providers

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env", override=True)

app = FastAPI(title="Prompt Optimizer", version="1.0.0")

# Templates & static files
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- Request / Response models ---

class OptimizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    provider: str | None = Field(None, description="Provider key, e.g. 'nvidia'")
    model: str | None = Field(None, description="Model ID, e.g. 'openai/gpt-oss-120b'")


class OptimizeResponse(BaseModel):
    optimized: str
    provider: str


# --- Routes ---

@app.get("/", include_in_schema=False)
async def index(request: Request):
    """Serve the web UI."""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/providers")
async def get_providers():
    """List available provider × model combinations."""
    return [
        {
            "provider": p.provider,
            "model_id": p.model_id,
            "label": p.label,
            "configured": p.configured,
        }
        for p in list_providers()
    ]


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_prompt(req: OptimizeRequest):
    """Optimize a prompt."""
    optimizer = _get_optimizer_safe(req.provider, req.model)
    if optimizer is None:
        provider = req.provider or os.getenv("LLM_PROVIDER", "claude")
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not available. Check your API key configuration.",
        )

    try:
        optimized = await optimizer.optimize(req.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {e}")

    return OptimizeResponse(optimized=optimized, provider=optimizer.provider_name)


# --- Helpers ---

def _get_optimizer_safe(provider: str | None = None, model: str | None = None):
    """Try to create an optimizer; return None if not configured."""
    try:
        return get_optimizer(provider, model)
    except (ValueError, KeyError):
        return None


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port)
