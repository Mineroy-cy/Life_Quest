"""
Difficulty Engine Service - tracks velocity, rejection rate, obstacle patterns
and generates adaptive challenges for skill-gap obstacles.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bson.objectid import ObjectId
from app.core.database import (
    db,
    projects_collection,
    tasks_collection,
    challenges_collection,
    evidence_collection,
    obstacles_collection,
)
from app.services.task_splitter import _call_ai, _candidate_models

# Skill issue categories that trigger adaptation
SKILL_CATEGORIES = [
    "fundamental_concept",
    "technical_skill",
    "tool_proficiency", 
    "time_management",
    "domain_knowledge",
    "creative_thinking",
    "other",
]


def analyze_project_difficulty(project_id: str) -> dict:
    """
    Analyze project completion velocity, rejection rate, and obstacle patterns.
    
    Returns:
    {
        "completion_velocity": float,  # tasks completed per day
        "rejection_rate": float,       # % of submitted evidence rejected
        "obstacle_count": int,
        "obstacle_patterns": {
            "skill_gap": int,
            "blocker": int,
            "resource": int,
            "motivation": int,
            "other": int
        },
        "suggested_difficulty": str,   # "easier", "maintain", "harder"
        "recommendation": str
    }
    """
    try:
        project_doc = projects_collection.find_one({"_id": ObjectId(project_id)})
    except Exception:
        project_doc = projects_collection.find_one({"_id": project_id})
    
    if not project_doc:
        return {}
    
    # Calculate completion velocity
    all_tasks = list(tasks_collection.find({"project_id": project_id}))
    completed_tasks = [t for t in all_tasks if t.get("completed")]
    
    if not all_tasks:
        return {
            "completion_velocity": 0.0,
            "rejection_rate": 0.0,
            "obstacle_count": 0,
            "obstacle_patterns": {k: 0 for k in ["skill_gap", "blocker", "resource", "motivation", "other"]},
            "suggested_difficulty": "maintain",
            "recommendation": "No tasks yet"
        }
    
    # Days elapsed since project start
    start_date = project_doc.get("start_date")
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    days_elapsed = max(1, (datetime.now() - start_date).days) if start_date else 1
    
    completion_velocity = len(completed_tasks) / days_elapsed
    
    # Calculate rejection rate (evidence rejected / total evidence submitted)
    all_evidence = list(evidence_collection.find({"task_id": {"$in": [t["_id"] for t in all_tasks]}}))
    rejected_count = sum(1 for e in all_evidence if e.get("verification_status") == "rejected")
    rejection_rate = (rejected_count / len(all_evidence)) if all_evidence else 0.0
    
    # Analyze obstacle patterns
    all_obstacles = list(obstacles_collection.find({"project_id": project_id}))
    obstacle_patterns = {k: 0 for k in ["skill_gap", "blocker", "resource", "motivation", "other"]}
    for obs in all_obstacles:
        category = obs.get("category", "other").lower()
        if category in obstacle_patterns:
            obstacle_patterns[category] += 1
    
    # Recommend difficulty adjustment
    suggested_difficulty = "maintain"
    recommendation = "Project on track"
    
    if rejection_rate > 0.5:
        suggested_difficulty = "easier"
        recommendation = "High rejection rate - tasks may be too difficult. Consider easier variants."
    elif completion_velocity < 0.5 and obstacle_patterns["skill_gap"] > 2:
        suggested_difficulty = "easier"
        recommendation = "Slow completion with skill gaps - recommend targeted skill-building tasks."
    elif completion_velocity > 1.2 and rejection_rate < 0.1:
        suggested_difficulty = "harder"
        recommendation = "Strong performance - can increase challenge difficulty."
    
    return {
        "completion_velocity": round(completion_velocity, 2),
        "rejection_rate": round(rejection_rate, 2),
        "obstacle_count": len(all_obstacles),
        "obstacle_patterns": obstacle_patterns,
        "suggested_difficulty": suggested_difficulty,
        "recommendation": recommendation,
    }


def suggest_adaptive_challenges(
    project_id: str,
    skill_category: str,
    obstacle_description: str
) -> List[Dict]:
    """
    Generate adaptive challenges targeting a specific skill gap.
    Returns list of challenge templates (not yet persisted).
    """
    # Get project context
    try:
        project_doc = projects_collection.find_one({"_id": ObjectId(project_id)})
    except Exception:
        project_doc = projects_collection.find_one({"_id": project_id})
    
    if not project_doc:
        return []
    
    project_name = project_doc.get("name", "Project")
    project_description = project_doc.get("description", "")
    
    prompt = f"""
You are an adaptive learning AI. A user has encountered a skill gap while working on: "{project_name}"

Project: {project_description}
Skill Gap: {skill_category}
Obstacle Details: {obstacle_description}

Generate 2-3 focused, mini-challenges that directly address this skill gap. These should be:
1. Concrete and achievable within 30-60 minutes each
2. Progressively harder (first helps build foundation, second applies it, third extends knowledge)
3. Related to the main project but isolated as skill-builders

Format your response as JSON:
{{
  "challenges": [
    {{"title": "...", "description": "...", "proof_instructions": "...", "estimated_duration": 45}},
    ...
  ]
}}

Only output valid JSON, no other text.
"""
    
    try:
        response = _call_ai(prompt, model=_candidate_models()[0] if _candidate_models() else None)
        import json
        parsed = json.loads(response)
        return parsed.get("challenges", [])
    except Exception as e:
        print(f"Error generating adaptive challenges: {e}")
        return []


def generate_obstacle_suggestion(
    obstacle_description: str,
    task_context: str = ""
) -> Dict[str, str]:
    """
    AI-powered obstacle analysis and skill category recommendation.
    
    Returns: {"skill_category": str, "suggestion": str}
    """
    prompt = f"""
A user logged an obstacle while working on a task: "{task_context}"

Obstacle: {obstacle_description}

Analyze this obstacle and determine:
1. What category best describes it? Choose from:
   - "fundamental_concept" (missing foundational knowledge)
   - "technical_skill" (needs practice with a specific tool/technique)
   - "tool_proficiency" (software/framework unfamiliarity)
   - "time_management" (not enough time allocated)
   - "domain_knowledge" (lacks domain-specific expertise)
   - "creative_thinking" (needs more creative problem-solving)
   - "external_blocker" (blocked by external factors, not skill-based)
   - "other"

2. Provide a brief suggestion for addressing it (1-2 sentences).

Format your response as JSON:
{{
  "skill_category": "...",
  "suggestion": "..."
}}

Only output valid JSON, no other text.
"""
    
    try:
        response = _call_ai(prompt, model=_candidate_models()[0] if _candidate_models() else None)
        import json
        parsed = json.loads(response)
        return {
            "skill_category": parsed.get("skill_category", "other"),
            "suggestion": parsed.get("suggestion", "Review this obstacle carefully.")
        }
    except Exception as e:
        print(f"Error analyzing obstacle: {e}")
        return {
            "skill_category": "other",
            "suggestion": "Please review this obstacle and determine the underlying skill gap."
        }
