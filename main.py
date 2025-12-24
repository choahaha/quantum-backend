"""
Quantum Backend API Server
FastAPI + Qiskit for Scratch Quantum blocks
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from executor import QuantumExecutor, create_histogram

app = FastAPI(
    title="Scratch Quantum API",
    description="Execute quantum circuits from Scratch blocks",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize executor
executor = QuantumExecutor()


class BlockData(BaseModel):
    opcode: str
    args: Dict[str, Any] = {}


class ExecuteRequest(BaseModel):
    blocks: List[BlockData]
    shots: int = 1024


class ExecuteResponse(BaseModel):
    success: bool
    counts: Optional[Dict[str, int]] = None
    result_text: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class HistogramRequest(BaseModel):
    data: str  # JSON string: "{'00': 512, '11': 512}"


class HistogramResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Scratch Quantum API", "status": "running"}


@app.get("/api/quantum/health")
async def health_check():
    return {
        "status": "ok",
        "service": "quantum-backend",
        "qiskit_available": executor.is_available()
    }


@app.post("/api/quantum/execute", response_model=ExecuteResponse)
async def execute_circuit(request: ExecuteRequest):
    """Execute quantum circuit from block data"""

    # Validate request
    if not request.blocks:
        raise HTTPException(status_code=400, detail="No blocks provided")

    if request.shots < 1 or request.shots > 10000:
        raise HTTPException(status_code=400, detail="Shots must be between 1 and 10000")

    # Convert BlockData to dict
    blocks = [{"opcode": b.opcode, "args": b.args} for b in request.blocks]

    # Execute
    result = executor.execute(blocks, request.shots)

    return ExecuteResponse(**result)


@app.post("/api/visualization/histogram", response_model=HistogramResponse)
async def create_histogram_chart(request: HistogramRequest):
    """Create histogram from quantum measurement data"""
    try:
        image_base64 = create_histogram(request.data)
        return HistogramResponse(success=True, image_base64=image_base64)
    except Exception as e:
        return HistogramResponse(success=False, error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
