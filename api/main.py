"""
FastAPI application entry point.

Run with:  uvicorn api.main:app --reload
The --reload flag restarts the server automatically when you save a file.
"""

import sys
from pathlib import Path

# Make the project root importable so `from utils.auth import ...` works
# the same way it does inside the Streamlit pages.
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, queue, specs, vendors

app = FastAPI(title="RFQ Sender API", version="1.0.0")

# CORS (Cross-Origin Resource Sharing):
# Browsers enforce a security rule that JavaScript on one domain can't make
# HTTP requests to a different domain by default. During development your
# React app runs on localhost:5173 and this API runs on localhost:8000 —
# different ports count as different "origins." Adding this middleware
# tells the browser "yes, it's safe to let requests from localhost:5173 through."
#
# In production you'd replace localhost:5173 with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# "prefix" means every route inside auth.router is automatically prefixed.
# So a route defined as @router.post("/login") becomes POST /auth/login.
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(queue.router, prefix="/queue", tags=["queue"])
app.include_router(specs.router, prefix="/specs", tags=["specs"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])


@app.get("/health")
def health():
    """Quick check that the API is running. Hit /health in a browser to confirm."""
    return {"status": "ok"}
