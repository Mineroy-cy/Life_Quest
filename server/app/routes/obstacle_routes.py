from datetime import datetime
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional
from app.models.obstacle import Obstacle
from app.core.database import obstacles_collection, tasks_collection, challenges_collection, projects_collection
from app.services.difficulty_engine import generate_obstacle_suggestion, suggest_adaptive_challenges
from bson import ObjectId

router = APIRouter()


class SuggestionUpdate(BaseModel):
    approved: bool
    skill_category: Optional[str] = None


@router.post("/")
def create_obstacle(obstacle: Obstacle):
    """Create obstacle and generate AI suggestion for root cause."""
    data = obstacle.dict()
    if not data.get("submitted_at"):
        data["submitted_at"] = datetime.utcnow()

    # Get task context for AI analysis
    task_context = ""
    if obstacle.task_id:
        try:
            task_doc = tasks_collection.find_one({"_id": ObjectId(obstacle.task_id)})
        except Exception:
            task_doc = tasks_collection.find_one({"_id": obstacle.task_id})
        if task_doc:
            task_context = task_doc.get("description", "")

    # Generate AI suggestion
    ai_analysis = generate_obstacle_suggestion(
        obstacle.description or "",
        task_context=task_context
    )
    data["ai_suggestion"] = ai_analysis["suggestion"]
    data["suggested_skill_category"] = ai_analysis["skill_category"]

    # Inherit project_id from challenge/task when omitted.
    if not data.get("project_id") and data.get("challenge_id"):
        try:
            challenge_doc = challenges_collection.find_one({"_id": ObjectId(data.get("challenge_id"))})
        except Exception:
            challenge_doc = challenges_collection.find_one({"_id": data.get("challenge_id")})
        if challenge_doc and challenge_doc.get("project_id"):
            data["project_id"] = str(challenge_doc.get("project_id"))
    if not data.get("project_id") and data.get("task_id"):
        try:
            task_doc = tasks_collection.find_one({"_id": ObjectId(data.get("task_id"))})
        except Exception:
            task_doc = tasks_collection.find_one({"_id": data.get("task_id")})
        if task_doc and task_doc.get("project_id"):
            data["project_id"] = str(task_doc.get("project_id"))

    # If user indicates partial completion, mark those specific tasks done.
    completed_task_ids = [str(tid) for tid in (data.get("completed_task_ids") or [])]
    for task_id in completed_task_ids:
        try:
            tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"completed": True, "completion_status": "done"}},
            )
        except Exception:
            tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"completed": True, "completion_status": "done"}},
            )

    result = obstacles_collection.insert_one(data)

    # Stop timer and mark challenge as interrupted when obstacle is logged.
    if data.get("challenge_id"):
        try:
            challenges_collection.update_one(
                {"_id": ObjectId(data.get("challenge_id"))},
                {
                    "$set": {
                        "status": "obstacle_logged",
                        "countdown_end": datetime.utcnow(),
                        "interrupted_at": datetime.utcnow(),
                    }
                },
            )
        except Exception:
            challenges_collection.update_one(
                {"_id": data.get("challenge_id")},
                {
                    "$set": {
                        "status": "obstacle_logged",
                        "countdown_end": datetime.utcnow(),
                        "interrupted_at": datetime.utcnow(),
                    }
                },
            )

    return {
        "obstacle_id": str(result.inserted_id),
        "status": data.get("status", "logged"),
        "ai_suggestion": data["ai_suggestion"],
        "suggested_skill_category": data["suggested_skill_category"],
        "suggestion_status": "pending_approval",
        "completed_task_ids_applied": completed_task_ids,
    }


@router.get("/{task_id}")
def get_obstacles(task_id: str):
    """Get obstacles for a task."""
    records = list(obstacles_collection.find({"task_id": task_id}))
    for record in records:
        record["_id"] = str(record["_id"])
    return records


@router.patch("/{obstacle_id}/suggestion")
def update_suggestion_status(
    obstacle_id: str,
    update: SuggestionUpdate = Body(...)
):
    """
    Update obstacle suggestion status.
    If approved, generates adaptive challenges for remaining tasks.
    
    Body:
    {
        "approved": bool,
        "skill_category": str (user-confirmed skill category)
    }
    """
    # Fetch the obstacle
    try:
        obstacle_doc = obstacles_collection.find_one({"_id": ObjectId(obstacle_id)})
    except Exception:
        obstacle_doc = obstacles_collection.find_one({"_id": obstacle_id})
    
    if not obstacle_doc:
        return {"error": "Obstacle not found"}
    
    if update.approved and update.skill_category:
        # Fetch project to get remaining tasks
        project_id = obstacle_doc.get("project_id")
        if not project_id:
            return {"error": "No project_id on obstacle"}
        
        # Get all incomplete tasks in the project
        try:
            project_obj = projects_collection.find_one({"_id": ObjectId(project_id)})
        except Exception:
            project_obj = projects_collection.find_one({"_id": project_id})
        
        if not project_obj:
            return {"error": "Project not found"}
        
        incomplete_tasks = list(tasks_collection.find({
            "project_id": project_id,
            "completed": {"$ne": True}
        }))
        
        # Generate adaptive challenges
        adaptive_challenges = suggest_adaptive_challenges(
            project_id,
            update.skill_category,
            obstacle_doc.get("description", "")
        )
        
        # Create challenge docs for each remaining task
        created_count = 0
        for task in incomplete_tasks:
            for challenge_template in adaptive_challenges:
                challenge_doc = {
                    "task_id": str(task["_id"]),
                    "project_id": project_id,
                    "description": challenge_template.get("description", ""),
                    "proof_instructions": challenge_template.get("proof_instructions", ""),
                    "challenge_description": f"[Skill-Adaptive] {challenge_template.get('title', '')}",
                    "recommended_duration": challenge_template.get("estimated_duration", 45),
                    "proof_types": ["text"],
                    "proof_scheme": f"Demonstrate understanding of {update.skill_category}",
                    "status": "pending",
                    "created_from_obstacle": obstacle_id,
                    "created_at": datetime.utcnow(),
                }
                challenges_collection.insert_one(challenge_doc)
                created_count += 1
        
        # Update obstacle
        obstacles_collection.update_one(
            {"_id": ObjectId(obstacle_id) if isinstance(obstacle_id, str) else obstacle_id},
            {
                "$set": {
                    "suggestion_status": "approved",
                    "skill_category": update.skill_category,
                    "approved_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "obstacle_id": obstacle_id,
            "approved": True,
            "skill_category": update.skill_category,
            "adaptive_challenges_created": created_count,
            "message": f"Generated {created_count} skill-adaptive challenges for remaining tasks"
        }
    
    else:
        # Rejection path
        obstacles_collection.update_one(
            {"_id": ObjectId(obstacle_id) if isinstance(obstacle_id, str) else obstacle_id},
            {"$set": {"suggestion_status": "rejected"}}
        )
        return {
            "obstacle_id": obstacle_id,
            "approved": False,
            "message": "Obstacle suggestion rejected"
        }
