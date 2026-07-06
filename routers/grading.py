"""
Mission grading endpoint.

Flow: verify Supabase JWT -> load the mission's grading_spec (service
role) -> enforce sequential unlock -> grade (re-simulating the circuit
server-side) -> record the attempt via the record_submission() SQL
function -> return the verdict with per-check feedback.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from auth import get_current_user_id
from grader import grade
from routers.quantum import BlockData
from supabase_admin import get_admin_client

router = APIRouter()


class SubmitRequest(BaseModel):
    mission_id: int
    blocks: List[BlockData]
    project_json: Optional[str] = None


class CheckResult(BaseModel):
    id: str
    type: str
    passed: bool
    feedback: str


class SubmitResponse(BaseModel):
    passed: bool
    checks: List[CheckResult]
    counts: Optional[Dict[str, int]] = None


def _find_previous_mission(admin, mission: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the mission immediately before this one in the global sequence."""
    prev_in_chapter = (
        admin.table("missions")
        .select("id, order_index")
        .eq("chapter_id", mission["chapter_id"])
        .lt("order_index", mission["order_index"])
        .order("order_index", desc=True)
        .limit(1)
        .execute()
    )
    if prev_in_chapter.data:
        return prev_in_chapter.data[0]

    # First mission of its chapter: the previous mission is the last one
    # of the previous chapter, if any.
    chapter = (
        admin.table("chapters")
        .select("order_index")
        .eq("id", mission["chapter_id"])
        .single()
        .execute()
    )
    prev_chapter = (
        admin.table("chapters")
        .select("id")
        .lt("order_index", chapter.data["order_index"])
        .order("order_index", desc=True)
        .limit(1)
        .execute()
    )
    if not prev_chapter.data:
        return None
    last_mission = (
        admin.table("missions")
        .select("id, order_index")
        .eq("chapter_id", prev_chapter.data[0]["id"])
        .order("order_index", desc=True)
        .limit(1)
        .execute()
    )
    return last_mission.data[0] if last_mission.data else None


@router.post("/api/grading/submit", response_model=SubmitResponse)
async def submit_mission(
    request: SubmitRequest,
    user_id: str = Depends(get_current_user_id),
):
    admin = get_admin_client()

    mission_result = (
        admin.table("missions")
        .select("id, chapter_id, order_index, grading_spec")
        .eq("id", request.mission_id)
        .execute()
    )
    if not mission_result.data:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission = mission_result.data[0]

    # Sequential unlock, server-enforced
    previous = _find_previous_mission(admin, mission)
    if previous is not None:
        progress = (
            admin.table("mission_progress")
            .select("status")
            .eq("user_id", user_id)
            .eq("mission_id", previous["id"])
            .execute()
        )
        if not progress.data or progress.data[0]["status"] != "passed":
            raise HTTPException(status_code=403, detail="Previous mission not passed yet")

    blocks = [{"opcode": b.opcode, "args": b.args} for b in request.blocks]

    # Aer simulation is blocking; keep the event loop free.
    result = await run_in_threadpool(grade, blocks, mission["grading_spec"])

    admin.rpc("record_submission", {
        "p_user_id": user_id,
        "p_mission_id": mission["id"],
        "p_passed": result["passed"],
        "p_result": {"checks": result["checks"], "counts": result["counts"]},
    }).execute()

    return SubmitResponse(
        passed=result["passed"],
        checks=result["checks"],
        counts=result["counts"],
    )
