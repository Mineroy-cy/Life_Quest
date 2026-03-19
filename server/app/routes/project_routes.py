# app/routes/project_routes.py

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from datetime import date, datetime, timedelta
from math import ceil
from typing import Literal

from app.models.project import Project
from app.core.database import (
    projects_collection,
    tasks_collection,
    challenges_collection,
    evidence_collection,
    obstacles_collection,
)
from app.services.ai_service import split_project_into_tasks
from app.services.progress_service import persist_project_progress
from app.services.difficulty_engine import analyze_project_difficulty

router = APIRouter()
AI_SPLIT_TIMEOUT_SECONDS = 60


def _duration_to_minutes(duration_value: float | None, duration_unit: str | None) -> int | None:
    if duration_value is None or not duration_unit:
        return None
    try:
        value = float(duration_value)
    except Exception:
        return None
    if value <= 0:
        return None

    unit = str(duration_unit).lower()
    if unit == "days":
        return int(value * 24 * 60)
    if unit == "hours":
        return int(value * 60)
    if unit == "minutes":
        return int(value)
    return None


def _project_total_days(project: dict) -> int:
    try:
        if project.get("duration_minutes") is not None:
            return max(int(ceil(float(project.get("duration_minutes")) / (24 * 60))), 1)
    except Exception:
        pass

    try:
        duration_minutes = _duration_to_minutes(project.get("duration_value"), project.get("duration_unit"))
        if duration_minutes is not None:
            return max(int(ceil(duration_minutes / (24 * 60))), 1)
    except Exception:
        pass

    try:
        deadline = date.fromisoformat(str(project.get("deadline")))
        start = date.fromisoformat(str(project.get("start_date")))
        return max((deadline - start).days + 1, 1)
    except Exception:
        return 30


def _fallback_split_tasks(
    project_name: str,
    description: str,
    total_days: int,
    difficulty_level: str,
) -> list[dict]:
    """Deterministic local fallback when AI splitting is slow/unavailable."""
    days = max(int(total_days), 1)
    # Keep fallback concise: 1-3 chunks depending on timeline.
    chunk_count = 1 if days <= 2 else (2 if days <= 7 else 3)
    base = max(days // chunk_count, 1)
    remainder = max(days - (base * chunk_count), 0)

    tasks = []
    for i in range(1, chunk_count + 1):
        est = base + (1 if i <= remainder else 0)
        tasks.append(
            {
                "title": f"{project_name} - Phase {i}",
                "description": description,
                "estimated_duration": est,
                "difficulty_level": difficulty_level or "medium",
                "order": i,
                "proof_types": ["text"],
                "proof_instructions": "Summarize exactly what was completed in this phase.",
            }
        )
    return tasks


def _split_tasks_with_timeout(
    project_name: str,
    description: str,
    total_days: int,
    difficulty_level: str,
) -> tuple[list[dict], str | None]:
    """Run AI splitter with a hard timeout; always return a usable task list."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        split_project_into_tasks,
        project_name,
        description,
        total_days,
        difficulty_level,
    )
    try:
        task_dicts = future.result(timeout=AI_SPLIT_TIMEOUT_SECONDS)
        if task_dicts:
            return task_dicts, None
        return (
            _fallback_split_tasks(project_name, description, total_days, difficulty_level),
            "AI returned no tasks; local fallback applied.",
        )
    except TimeoutError:
        future.cancel()
        return (
            _fallback_split_tasks(project_name, description, total_days, difficulty_level),
            f"AI task splitting timed out after {AI_SPLIT_TIMEOUT_SECONDS}s; local fallback applied.",
        )
    except Exception as exc:
        return (
            _fallback_split_tasks(project_name, description, total_days, difficulty_level),
            f"AI task splitting failed: {str(exc)}. Local fallback applied.",
        )
    finally:
        # Do not block request completion waiting for a stuck AI call.
        executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# POST /projects/  — create project and auto-split into tasks via AI
# ---------------------------------------------------------------------------

@router.post("/")
def create_project(project: Project):
    try:
        project_data = project.dict()
        project_data["start_date"] = project.start_date.isoformat()
        project_data["deadline"] = project.deadline.isoformat()

        duration_minutes = _duration_to_minutes(project.duration_value, project.duration_unit)
        if duration_minutes is not None:
            project_data["duration_minutes"] = duration_minutes

        result = projects_collection.insert_one(project_data)
        project_id = str(result.inserted_id)

        if duration_minutes is not None:
            total_days = max(ceil(duration_minutes / (24 * 60)), 1)
        else:
            total_days = max((project.deadline - project.start_date).days + 1, 1)
        task_dicts, warning = _split_tasks_with_timeout(
            project_name=project.name,
            description=project.description,
            total_days=total_days,
            difficulty_level=project.difficulty_level or "medium",
        )

        # Persist tasks to the tasks collection
        task_ids = []
        for i, t in enumerate(task_dicts, start=1):
            task_doc = {
                "project_id": project_id,
                "title": t.get("title", f"Task {i}"),
                "description": t.get("description", ""),
                "estimated_duration": t.get("estimated_duration", 1),
                "difficulty_level": t.get("difficulty_level", "medium"),
                "order": t.get("order", i),
                "proof_types": t.get("proof_types", ["text"]),
                "proof_instructions": t.get("proof_instructions", ""),
                "day_number": i,
                "completed": False,
                "completion_status": "pending",
            }
            ins = tasks_collection.insert_one(task_doc)
            task_ids.append(str(ins.inserted_id))

        # Record task_ids on the project doc
        projects_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"task_ids": task_ids, "progress_percentage": 0.0}},
        )

        response = {"project_id": project_id, "tasks": task_dicts, "task_ids": task_ids}
        if warning:
            response["warning"] = warning
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /projects/{project_id}
# ---------------------------------------------------------------------------

@router.get("/{project_id}")
def get_project(project_id: str):
    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id)})
    except Exception:
        project = projects_collection.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["_id"] = str(project["_id"])
    return project


# ---------------------------------------------------------------------------
# GET /projects/  — list all projects
# ---------------------------------------------------------------------------

@router.get("/")
def list_projects():
    projects = list(projects_collection.find())
    projects.sort(key=lambda p: (-int(p.get("priority", 0)), str(p.get("deadline", "9999-12-31"))))
    for p in projects:
        p["_id"] = str(p["_id"])
    return projects


@router.delete("/{project_id}")
def delete_project(project_id: str):
    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id)})
        project_filter = {"_id": ObjectId(project_id)}
    except Exception:
        project = projects_collection.find_one({"_id": project_id})
        project_filter = {"_id": project_id}

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_id_str = str(project.get("_id"))

    tasks = list(tasks_collection.find({"project_id": project_id_str}))
    if not tasks:
        try:
            tasks = list(tasks_collection.find({"project_id": ObjectId(project_id)}))
        except Exception:
            tasks = []

    task_ids = [str(t.get("_id")) for t in tasks]

    tasks_collection.delete_many({"project_id": project_id_str})
    try:
        tasks_collection.delete_many({"project_id": ObjectId(project_id)})
    except Exception:
        pass

    challenges_collection.delete_many({"project_id": project_id_str})
    obstacles_collection.delete_many({"project_id": project_id_str})

    if task_ids:
        evidence_collection.delete_many({"task_id": {"$in": task_ids}})
        obstacles_collection.delete_many({"task_id": {"$in": task_ids}})

    projects_collection.delete_one(project_filter)

    return {
        "deleted": True,
        "project_id": project_id_str,
        "removed_tasks": len(task_ids),
    }


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/progress
# ---------------------------------------------------------------------------

@router.get("/{project_id}/progress")
def get_progress(project_id: str):
    return persist_project_progress(project_id)


# ---------------------------------------------------------------------------
# PATCH /projects/{project_id}/description — edit description, regenerate
# remaining (incomplete) tasks while keeping completed tasks untouched.
# ---------------------------------------------------------------------------

class DescriptionUpdate(BaseModel):
    description: str


class TimelineUpdate(BaseModel):
    start_date: date | None = None
    deadline: date | None = None
    duration_value: float | None = None
    duration_unit: Literal["days", "hours", "minutes"] | None = None


@router.patch("/{project_id}/description")
def update_project_description(project_id: str, payload: DescriptionUpdate):
    # Load project
    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id)})
    except Exception:
        project = projects_collection.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Identify already-completed tasks — these are frozen
    all_tasks = list(tasks_collection.find({"project_id": project_id}))
    completed_tasks = [t for t in all_tasks if t.get("completed") or t.get("completion_status") == "done"]
    completed_days_used = sum(t.get("estimated_duration", 1) for t in completed_tasks)

    # Compute remaining timeline budget from both delivered effort and remaining calendar time.
    total_days = _project_total_days(project)
    remaining_by_effort = max(total_days - completed_days_used, 1)

    try:
        deadline = date.fromisoformat(str(project.get("deadline")))
        remaining_by_calendar = max((deadline - date.today()).days + 1, 1)
    except Exception:
        remaining_by_calendar = remaining_by_effort

    remaining_days = max(min(remaining_by_effort, remaining_by_calendar), 1)

    # Delete only incomplete tasks
    incomplete_ids = [t["_id"] for t in all_tasks if not t.get("completed") and t.get("completion_status") != "done"]
    if incomplete_ids:
        tasks_collection.delete_many({"_id": {"$in": incomplete_ids}})

    # Regenerate incomplete tasks using new description
    new_tasks, warning = _split_tasks_with_timeout(
        project_name=project.get("name", ""),
        description=payload.description,
        total_days=remaining_days,
        difficulty_level=project.get("difficulty_level", "medium"),
    )

    # Offset order past completed tasks
    order_offset = len(completed_tasks)
    new_task_ids = []
    for i, t in enumerate(new_tasks, start=1):
        task_doc = {
            "project_id": project_id,
            "title": t.get("title", f"Task {order_offset + i}"),
            "description": t.get("description", ""),
            "estimated_duration": t.get("estimated_duration", 1),
            "difficulty_level": t.get("difficulty_level", "medium"),
            "order": order_offset + t.get("order", i),
            "proof_types": t.get("proof_types", ["text"]),
            "proof_instructions": t.get("proof_instructions", ""),
            "day_number": order_offset + i,
            "completed": False,
            "completion_status": "pending",
        }
        ins = tasks_collection.insert_one(task_doc)
        new_task_ids.append(str(ins.inserted_id))

    # Persist new description and updated task ids
    kept_ids = [str(t["_id"]) for t in completed_tasks]
    projects_collection.update_one(
        {"_id": project.get("_id")},
        {"$set": {"description": payload.description, "task_ids": kept_ids + new_task_ids}},
    )

    response = {
        "project_id": project_id,
        "kept_completed_tasks": len(completed_tasks),
        "regenerated_tasks": len(new_tasks),
        "new_task_ids": new_task_ids,
    }
    if warning:
        response["warning"] = warning
    return response


@router.patch("/{project_id}/timeline")
def update_project_timeline(project_id: str, payload: TimelineUpdate):
    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id)})
        project_filter = {"_id": ObjectId(project_id)}
    except Exception:
        project = projects_collection.find_one({"_id": project_id})
        project_filter = {"_id": project_id}

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_fields: dict = {}

    if payload.start_date is not None:
        update_fields["start_date"] = payload.start_date.isoformat()

    has_duration_value = payload.duration_value is not None
    has_duration_unit = payload.duration_unit is not None
    if has_duration_value != has_duration_unit:
        raise HTTPException(status_code=400, detail="duration_value and duration_unit must be provided together")

    effective_start = payload.start_date
    if effective_start is None:
        try:
            effective_start = date.fromisoformat(str(project.get("start_date")))
        except Exception:
            effective_start = date.today()

    if has_duration_value and has_duration_unit:
        duration_minutes = _duration_to_minutes(payload.duration_value, payload.duration_unit)
        if duration_minutes is None:
            raise HTTPException(status_code=400, detail="Duration must be a positive value")

        update_fields["duration_value"] = payload.duration_value
        update_fields["duration_unit"] = payload.duration_unit
        update_fields["duration_minutes"] = duration_minutes

        computed_deadline = datetime.combine(effective_start, datetime.min.time()) + timedelta(minutes=duration_minutes)
        update_fields["deadline"] = computed_deadline.date().isoformat()

    if payload.deadline is not None:
        update_fields["deadline"] = payload.deadline.isoformat()

    if not update_fields:
        raise HTTPException(status_code=400, detail="No timeline fields to update")

    projects_collection.update_one(project_filter, {"$set": update_fields})

    updated = projects_collection.find_one(project_filter)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated project")
    updated["_id"] = str(updated["_id"])
    return updated


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/difficulty-score
# ---------------------------------------------------------------------------

@router.get("/{project_id}/difficulty-score")
def get_difficulty_score(project_id: str):
    """
    Get difficulty metrics and adaptation recommendations for a project.
    
    Returns:
    {
        "completion_velocity": float,  # tasks/day
        "rejection_rate": float,       # % of evidence rejected
        "obstacle_count": int,
        "obstacle_patterns": dict,     # skill_gap, blocker, resource, motivation, other counts
        "suggested_difficulty": str,   # "easier", "maintain", "harder"
        "recommendation": str
    }
    """
    return analyze_project_difficulty(project_id)
