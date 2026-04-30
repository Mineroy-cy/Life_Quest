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
    """
    Efficiently retrieve tasks grouped by project using aggregation pipeline.
    Replaces N+1 query pattern with a single aggregation.
    """
    # Get all projects and sort them
    projects = list(projects_collection.find())
    projects_map = {}
    for p in projects:
        projects_map[str(p.get("_id"))] = {
            "_id": str(p.get("_id")),
            "name": p.get("name"),
            "priority": int(p.get("priority", 0)),
            "deadline": p.get("deadline"),
            "status": p.get("status", "active"),
            "progress_percentage": p.get("progress_percentage", 0),
        }
    
    # Sort projects by priority and deadline
    sorted_project_ids = sorted(
        projects_map.keys(),
        key=lambda pid: (-projects_map[pid]["priority"], str(projects_map[pid].get("deadline", "9999-12-31")))
    )
    
    # Use aggregation to get all tasks with their projects in one query
    pipeline = [
        {
            "$addFields": {
                "project_id_str": {"$toString": "$project_id"},
                "is_done": {
                    "$in": [
                        {"$getField": "completion_status"},
                        ["done"]
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$project_id_str",
                "tasks": {
                    "$push": {
                        "_id": {"$toString": "$_id"},
                        "project_id": "$project_id_str",
                        "title": "$title",
                        "description": "$description",
                        "order": "$order",
                        "day_number": "$day_number",
                        "completed": "$completed",
                        "is_done": {
                            "$or": [
                                {"$eq": ["$completed", True]},
                                {"$eq": ["$completion_status", "done"]}
                            ]
                        },
                        "difficulty": "$difficulty",
                        "time_estimate_minutes": "$time_estimate_minutes"
                    }
                },
                "task_count": {"$sum": 1},
                "completed_count": {
                    "$sum": {
                        "$cond": [
                            {
                                "$or": [
                                    {"$eq": ["$completed", True]},
                                    {"$eq": ["$completion_status", "done"]}
                                ]
                            },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    
    task_groups = list(tasks_collection.aggregate(pipeline))
    
    # Build grouped result preserving project order
    grouped = []
    for project_id in sorted_project_ids:
        if project_id not in projects_map:
            continue
        
        project_data = projects_map[project_id]
        task_group = next((g for g in task_groups if g["_id"] == project_id), None)
        
        tasks = []
        task_count = 0
        completed_count = 0
        
        if task_group:
            tasks = sorted(
                task_group["tasks"],
                key=lambda t: (t.get("order", 9999), t.get("day_number", 9999))
            )
            task_count = task_group["task_count"]
            completed_count = task_group["completed_count"]
        
        grouped.append({
            "project": project_data,
            "task_count": task_count,
            "completed_count": completed_count,
            "tasks": tasks,
        })
    
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
