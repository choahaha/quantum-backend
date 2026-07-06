"""
Quantum execution and visualization endpoints.

Paths must not change: the Scratch VM patch
(patches/scratch-vm/blocks/scratch3_quantum.js) hard-codes them.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from executor import QuantumExecutor, create_histogram, create_circuit_diagram

router = APIRouter()

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
    shots_detail: Optional[list] = None
    result_text: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class HistogramRequest(BaseModel):
    data: str  # JSON string: "{'00': 512, '11': 512}"


class HistogramResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None


class CircuitDiagramRequest(BaseModel):
    blocks: List[BlockData]


class CircuitDiagramResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None


@router.get("/")
async def root():
    return {"message": "Scratch Quantum API", "status": "running"}


@router.get("/api/quantum/health")
async def health_check():
    return {
        "status": "ok",
        "service": "quantum-backend",
        "qiskit_available": executor.is_available()
    }


@router.post("/api/quantum/execute", response_model=ExecuteResponse)
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


@router.post("/api/visualization/histogram", response_model=HistogramResponse)
async def create_histogram_chart(request: HistogramRequest):
    """Create histogram from quantum measurement data"""
    try:
        image_base64 = create_histogram(request.data)
        return HistogramResponse(success=True, image_base64=image_base64)
    except Exception as e:
        return HistogramResponse(success=False, error=str(e))


@router.post("/api/visualization/circuit-diagram", response_model=CircuitDiagramResponse)
async def create_circuit_diagram_chart(request: CircuitDiagramRequest):
    """Create circuit diagram from quantum blocks"""
    try:
        blocks = [{"opcode": b.opcode, "args": b.args} for b in request.blocks]
        image_base64 = create_circuit_diagram(blocks)
        return CircuitDiagramResponse(success=True, image_base64=image_base64)
    except Exception as e:
        return CircuitDiagramResponse(success=False, error=str(e))
