"""
Quantum Backend API Server
FastAPI + Qiskit for Scratch Quantum blocks and mission grading
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import grading, quantum

app = FastAPI(
    title="Scratch Quantum API",
    description="Execute quantum circuits from Scratch blocks",
    version="1.1.0"
)

# Comma-separated allowed origins, e.g.
# CORS_ORIGINS=https://mission.example.app,https://scratch.example.app
# Auth uses bearer headers (not cookies), so credentials stay disabled.
cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quantum.router)
app.include_router(grading.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
