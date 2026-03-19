from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId

from app.core.database import tasks_collection, projects_collection
from app.services.scheduler_service import select_daily_challenges
from app.services.ai_service import split_project_into_tasks

router = APIRouter()


@router.get("/grouped")
def get_tasks_grouped_by_project():
    projects = list(projects_collection.find())
    projects.sort(key=lambda p: (-int(p.get("priority", 0)), str(p.get("deadline", "9999-12-31"))))

    grouped = []
    for project in projects:
        project_id = str(project.get("_id"))
        tasks = list(tasks_collection.find({"project_id": project_id}))
        if not tasks:
            try:
                tasks = list(tasks_collection.find({"project_id": ObjectId(project_id)}))
            except Exception:
                tasks = []

        tasks.sort(key=lambda t: (t.get("order", 9999), t.get("day_number", 9999)))
        normalized_tasks = []
        for task in tasks:
            task["_id"] = str(task["_id"])
            task["project_id"] = str(task.get("project_id", project_id))
            task["is_done"] = bool(task.get("completed") or task.get("completion_status") == "done")
            normalized_tasks.append(task)

        grouped.append(
            {
                "project": {
                    "_id": project_id,
                    "name": project.get("name"),
                    "priority": project.get("priority", 0),
                    "deadline": project.get("deadline"),
                    "status": project.get("status", "active"),
                    "progress_percentage": project.get("progress_percentage", 0),
                },
                "task_count": len(normalized_tasks),
                "completed_count": sum(1 for t in normalized_tasks if t.get("is_done")),
                "tasks": normalized_tasks,
            }
        )

    return grouped


# ---------------------------------------------------------------------------
# GET /tasks/{project_id} — display how a project was split into tasks
# ---------------------------------------------------------------------------

@router.get("/{project_id}")
def get_tasks(project_id: str):
    # Try both string and ObjectId project_id formats for backward compatibility.
    tasks = list(tasks_collection.find({"project_id": project_id}))
    if not tasks:
        try:
            tasks = list(tasks_collection.find({"project_id": ObjectId(project_id)}))
        except Exception:
            tasks = []

    # If task split is missing, rebuild it from project description so downstream
    # daily-challenge curation always has source tasks.
    if not tasks:
        try:
            project = projects_collection.find_one({"_id": ObjectId(project_id)})
        except Exception:
            project = projects_collection.find_one({"_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        try:
            deadline = date.fromisoformat(str(project.get("deadline")))
            start = date.fromisoformat(str(project.get("start_date")))
            total_days = max((deadline - start).days + 1, 1)
        except Exception:
            total_days = 30

        generated = split_project_into_tasks(
            project_name=project.get("name", "Project"),
            description=project.get("description", ""),
            total_days=total_days,
            difficulty_level=project.get("difficulty_level", "medium"),
        )

        task_ids: list[str] = []
        for i, t in enumerate(generated, start=1):
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

        projects_collection.update_one(
            {"_id": project.get("_id")},
            {"$set": {"task_ids": task_ids}},
        )
        tasks = list(tasks_collection.find({"project_id": project_id}))

    for t in tasks:
        t["_id"] = str(t["_id"])
    return tasks


# ---------------------------------------------------------------------------
# POST /tasks/time-allocation — today's challenges within available time
# ---------------------------------------------------------------------------

class TimeAllocationRequest(BaseModel):
    available_minutes: int


@router.post("/time-allocation")
def allocate_daily_challenges(payload: TimeAllocationRequest):
    """
    The user inputs how many minutes they have available today.
    Returns an ordered list of tasks from active projects that fit.
    """
    if payload.available_minutes <= 0:
        raise HTTPException(status_code=400, detail="available_minutes must be > 0")

    active_projects = list(projects_collection.find({"status": {"$ne": "completed"}}))
    project_ids = [str(p["_id"]) for p in active_projects]

    pending_tasks = list(
        tasks_collection.find({
            "project_id": {"$in": project_ids},
            "completion_status": {"$ne": "done"},
            "completed": {"$ne": True},
        })
    )

    # Normalise _id fields for the scheduler
    for p in active_projects:
        p["_id"] = str(p["_id"])
    for t in pending_tasks:
        t["_id"] = str(t["_id"])

    selected = select_daily_challenges(
        available_minutes=payload.available_minutes,
        active_projects=active_projects,
        pending_tasks=pending_tasks,
    )

    return {
        "available_minutes": payload.available_minutes,
        "selected_task_count": len(selected),
        "tasks": selected,
    }


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id}/completion — manually mark or unmark a task
# ---------------------------------------------------------------------------

class TaskCompletionUpdate(BaseModel):
    completed: bool


@router.patch("/{task_id}/completion")
def set_task_completion(task_id: str, payload: TaskCompletionUpdate):
    """Manually mark or unmark a single task as done/pending."""
    update = {
        "completed": payload.completed,
        "completion_status": "done" if payload.completed else "pending",
    }
    try:
        result = tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": update})
    except Exception:
        result = tasks_collection.update_one({"_id": task_id}, {"$set": update})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"updated": True, "task_id": task_id, "completed": payload.completed}
