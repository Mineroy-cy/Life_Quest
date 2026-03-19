"""Progress service: compute and persist project progress metrics."""

from app.core.database import tasks_collection, projects_collection
from bson import ObjectId


def calculate_project_progress(project_id: str) -> dict:
    """
    Returns a dict with:
      progress_percentage  — 0-100 float
      total_tasks          — int
      completed_tasks      — int
      completion_velocity  — tasks completed per total tasks (0-1 float)
    """
    all_tasks = list(tasks_collection.find({"project_id": project_id}))
    total = len(all_tasks)
    if total == 0:
        return {"progress_percentage": 0.0, "total_tasks": 0, "completed_tasks": 0, "completion_velocity": 0.0}

    done = sum(
        1 for t in all_tasks
        if t.get("completed") or t.get("completion_status") == "done"
    )
    pct = round((done / total) * 100, 2)
    velocity = round(done / total, 4)

    return {
        "progress_percentage": pct,
        "total_tasks": total,
        "completed_tasks": done,
        "completion_velocity": velocity,
    }


def persist_project_progress(project_id: str) -> dict:
    """Recalculate and write progress back to the project document."""
    stats = calculate_project_progress(project_id)
    status = "completed" if stats["progress_percentage"] >= 100.0 else "active"
    try:
        projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "progress_percentage": stats["progress_percentage"],
                "completion_velocity": stats["completion_velocity"],
                "status": status,
            }},
        )
    except Exception:
        projects_collection.update_one(
            {"_id": project_id},
            {"$set": {
                "progress_percentage": stats["progress_percentage"],
                "completion_velocity": stats["completion_velocity"],
                "status": status,
            }},
        )
    stats["status"] = status
    return stats
