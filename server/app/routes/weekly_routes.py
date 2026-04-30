from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.weekly_planner import (
    end_weekly_objectives,
    get_active_weekly_objectives,
    refresh_active_weekly_objectives,
    start_weekly_objectives,
    update_weekly_challenge_status,
)


router = APIRouter()


class StartWeekRequest(BaseModel):
    goal_count: int = 3
    challenges_per_goal: int = 6


class UpdateWeeklyChallengeStatusRequest(BaseModel):
    week_id: str
    project_id: str
    challenge_index: int
    done: bool = True


@router.post("/start")
def start_week(payload: StartWeekRequest):
    weekly = start_weekly_objectives(payload.goal_count, payload.challenges_per_goal)
    return {"started": True, "weekly": weekly}


@router.post("/end")
def end_week():
    return end_weekly_objectives()


@router.get("/active")
def get_active_week(refresh_if_stale: bool = Query(default=True)):
    weekly = get_active_weekly_objectives(refresh_if_stale=refresh_if_stale)
    return {"weekly": weekly}


@router.post("/refresh")
def refresh_week():
    refreshed = refresh_active_weekly_objectives()
    return {"weekly": refreshed}


@router.patch("/challenge-status")
def update_challenge_status(payload: UpdateWeeklyChallengeStatusRequest):
    weekly = update_weekly_challenge_status(
        week_id=payload.week_id,
        project_id=payload.project_id,
        challenge_index=payload.challenge_index,
        done=payload.done,
    )
    if not weekly:
        return {"updated": False, "message": "No active week/challenge match found", "weekly": None}
    return {"updated": True, "weekly": weekly}
