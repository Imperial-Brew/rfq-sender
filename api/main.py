"""
FastAPI application entry point.

Run with:  uvicorn api.main:app --reload
The --reload flag restarts the server automatically when you save a file.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routers import auth, queue, specs, vendors

app = FastAPI(title="RFQ Sender API", version="1.0.0")

# In development the React dev server runs on :5173 and proxies /api → :8000.
# In production FastAPI serves the built React files directly, so CORS is only
# needed for the dev origin. FRONTEND_ORIGIN can be set to restrict further.
_dev_origin = "http://localhost:5173"
_extra = os.environ.get("FRONTEND_ORIGIN", "")
_origins = [_dev_origin] + ([_extra] if _extra else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
app.include_router(specs.router, prefix="/api/specs", tags=["specs"])
app.include_router(vendors.router, prefix="/api/vendors", tags=["vendors"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the React build in production.
# The build step (npm run build) outputs to frontend/dist/.
# StaticFiles serves /assets/* directly; the catch-all returns index.html so
# React Router handles client-side navigation (e.g. /queue, /vendors).
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(str(_dist / "index.html"))
