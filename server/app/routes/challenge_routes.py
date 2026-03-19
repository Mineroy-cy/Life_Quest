from datetime import date, datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, HTTPException, Query
from app.models.challenge import Challenge
from app.core.database import (
    challenges_collection,
    projects_collection,
    tasks_collection,
    obstacles_collection,
)
from bson import ObjectId
from pydantic import BaseModel

from app.services.difficulty_engine import analyze_project_difficulty
from app.services.ai_service import split_project_into_tasks
from app.services.task_splitter import _call_ai
import json


ACTIVE_CHALLENGE_STATUSES = ["active", "partial_completed"]


class ProofConfigUpdate(BaseModel):
    # Supports one or many types, including custom user-defined values.
    proof_types: list[str]
    # User description of how proof should be evaluated.
    proof_scheme: str = ""


class AcceptChallengeRequest(BaseModel):
    proof_types: list[str] | None = None
    proof_scheme: str | None = None
    challenge_description: str | None = None
    proof_instructions: str | None = None
    recommended_duration_minutes: int | None = None


class TaskStatusUpdate(BaseModel):
    completed_task_ids: list[str] = []
    keep_pending_task_ids: list[str] = []


def _project_total_days(project: dict) -> int:
    try:
        duration_value = project.get("duration_value")
        duration_unit = str(project.get("duration_unit", "")).lower()
        if duration_value is not None and duration_unit:
            value = float(duration_value)
            if value > 0:
                if duration_unit == "days":
                    return max(int(ceil(value)), 1)
                if duration_unit == "hours":
                    return max(int(ceil(value / 24.0)), 1)
                if duration_unit == "minutes":
                    return max(int(ceil(value / (24.0 * 60.0))), 1)
    except Exception:
        pass

    try:
        deadline = date.fromisoformat(str(project.get("deadline")))
        start = date.fromisoformat(str(project.get("start_date")))
        return max((deadline - start).days + 1, 1)
    except Exception:
        return 30


def _ai_generate_challenge_description(
    project: dict,
    tasks: list[dict],
    effective_difficulty: str,
    days_left: int,
    available_minutes: int | None,
) -> dict:
    """
    Ask the AI to write a clear, motivating challenge description and estimate the
    time needed, given the selected task bundle.
    Returns dict with keys: description (str), estimated_minutes (int).
    Falls back to a template string on any error.
    """
    task_lines = "\n".join(
        [f"- {t.get('title', 'Task')}: {t.get('description', '')[:250]}" for t in tasks]
    )
    time_hint = f" Available time today: ~{available_minutes} minutes." if available_minutes else ""
    prompt = f"""You are a productivity coach writing a challenge brief for today's work session.

Project: {project.get('name', 'Project')}
Deadline in {days_left} days. Difficulty: {effective_difficulty}.{time_hint}

Tasks bundled for today:
{task_lines}

Write a focused 2-3 sentence challenge description that:
1. Names each task specifically.
2. States the concrete output expected by end of session.
3. Motivates the user to commit.

Then estimate how many minutes these tasks should realistically take.

Respond ONLY with valid JSON (no markdown, no prose outside the JSON):
{{"description": "...", "estimated_minutes": <integer>}}"""

    try:
        raw = _call_ai(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        bracket = raw.find("{")
        if bracket != -1:
            raw = raw[bracket:]
        data = json.loads(raw)
        return {
            "description": str(data.get("description", "")).strip(),
            "estimated_minutes": max(int(data.get("estimated_minutes", 30)), 1),
        }
    except Exception:
        return {}


router = APIRouter()


def _get_project(project_id: str):
    try:
        return projects_collection.find_one({"_id": ObjectId(project_id)})
    except Exception:
        return projects_collection.find_one({"_id": project_id})


def _load_pending_tasks(project_id: str) -> list[dict]:
    pending = list(
        tasks_collection.find(
            {
                "project_id": project_id,
                "completion_status": {"$ne": "done"},
                "completed": {"$ne": True},
            }
        )
    )
    if pending:
        return pending
    try:
        return list(
            tasks_collection.find(
                {
                    "project_id": ObjectId(project_id),
                    "completion_status": {"$ne": "done"},
                    "completed": {"$ne": True},
                }
            )
        )
    except Exception:
        return []


def _ensure_split_tasks_for_project(project_id: str, project: dict) -> list[dict]:
    pending = _load_pending_tasks(project_id)
    if pending:
        return pending

    # Self-heal missing task split directly from project context.
    total_days = _project_total_days(project)

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

    return _load_pending_tasks(project_id)


def _effort_units(task: dict) -> int:
    raw = task.get("estimated_duration", 1)
    try:
        return max(int(raw), 1)
    except Exception:
        return 1


def _to_project_id_variants(project_id: str):
    variants = [project_id]
    try:
        variants.append(ObjectId(project_id))
    except Exception:
        pass
    return variants


def _normalize_challenge_doc(challenge: dict) -> dict:
    doc = dict(challenge)
    doc["_id"] = str(doc.get("_id"))
    if doc.get("project_id") is not None:
        doc["project_id"] = str(doc.get("project_id"))
    if doc.get("task_id") is not None:
        doc["task_id"] = str(doc.get("task_id"))
    if doc.get("task_ids"):
        doc["task_ids"] = [str(t) for t in doc.get("task_ids", [])]
    return doc


def _find_any_active_challenge(exclude_id: str | None = None):
    query = {"status": {"$in": ACTIVE_CHALLENGE_STATUSES}}
    active = challenges_collection.find_one(query, sort=[("accepted_at", -1), ("_id", -1)])
    if not active:
        return None

    if exclude_id and str(active.get("_id")) == str(exclude_id):
        return None
    return active


def _project_urgency_score(project: dict) -> float:
    priority = max(int(project.get("priority", 1)), 1)
    progress = float(project.get("progress_percentage", 0.0) or 0.0)
    difficulty = str(project.get("difficulty_level", "medium")).lower()
    difficulty_bonus = {"easy": 0.0, "medium": 8.0, "hard": 16.0}.get(difficulty, 8.0)

    try:
        deadline = date.fromisoformat(str(project.get("deadline")))
        days_left = max((deadline - date.today()).days + 1, 1)
    except Exception:
        days_left = 30

    deadline_pressure = 120.0 / days_left
    remaining_work = max(0.0, 100.0 - progress)

    return (priority * 25.0) + deadline_pressure + (remaining_work * 0.4) + difficulty_bonus


def _allocate_minutes_by_priority(projects: list[dict], available_minutes: int) -> list[tuple[dict, int]]:
    if not projects or available_minutes <= 0:
        return []

    weighted = []
    total_weight = 0.0
    for project in projects:
        weight = max(_project_urgency_score(project), 1.0)
        weighted.append((project, weight))
        total_weight += weight

    # Keep allocations practical for one challenge session.
    min_slot = 20
    allocations: list[tuple[dict, int]] = []
    for project, weight in weighted:
        share = int(round((weight / total_weight) * available_minutes)) if total_weight else 0
        minutes = max(min_slot, share)
        allocations.append((project, minutes))

    # Adjust to match exact available minutes.
    total_alloc = sum(minutes for _, minutes in allocations)
    if total_alloc > available_minutes:
        overflow = total_alloc - available_minutes
        i = len(allocations) - 1
        while overflow > 0 and i >= 0:
            project, minutes = allocations[i]
            reducible = max(minutes - min_slot, 0)
            if reducible > 0:
                cut = min(reducible, overflow)
                allocations[i] = (project, minutes - cut)
                overflow -= cut
            i -= 1

    # If min-slot still exceeds budget, keep top projects until budget fits.
    final_alloc: list[tuple[dict, int]] = []
    consumed = 0
    for project, minutes in allocations:
        if consumed + minutes > available_minutes and final_alloc:
            continue
        if consumed + minutes > available_minutes:
            minutes = max(1, available_minutes - consumed)
        if minutes <= 0:
            continue
        final_alloc.append((project, minutes))
        consumed += minutes
        if consumed >= available_minutes:
            break

    return final_alloc


def _get_or_create_daily_challenge(project_id: str, available_minutes: int | None = None):
    today = date.today().isoformat()

    project_variants = _to_project_id_variants(project_id)
    existing = challenges_collection.find_one(
        {"project_id": {"$in": project_variants}, "daily_date": today},
        sort=[("_id", -1)],
    )
    if existing:
        existing_status = str(existing.get("status", "pending")).lower()
        # Reuse only in-flight challenges. Completed/obstacle outcomes should allow a fresh pick.
        if existing_status in {"pending", "active", "partial_completed"}:
            return {"source": "existing", "challenge": _normalize_challenge_doc(existing)}

    project = _get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pending_tasks = _ensure_split_tasks_for_project(project_id, project)
    if not pending_tasks:
        raise HTTPException(status_code=404, detail="No pending tasks found for this project")

    pending_tasks.sort(key=lambda t: (t.get("day_number", 10_000), t.get("order", 10_000)))

    diff = analyze_project_difficulty(project_id)
    suggested_diff = diff.get("suggested_difficulty", "maintain")
    performance_recommendation = diff.get("recommendation", "")

    obstacle_patterns = diff.get("obstacle_patterns", {})
    non_skill_pressure = (
        int(obstacle_patterns.get("blocker", 0))
        + int(obstacle_patterns.get("resource", 0))
        + int(obstacle_patterns.get("motivation", 0))
    )

    approved_skill_obstacles = list(
        obstacles_collection.find(
            {
                "project_id": project_id,
                "suggestion_status": "approved",
                "skill_category": {"$exists": True, "$ne": ""},
            }
        )
    )
    approved_skill_categories = sorted({o.get("skill_category", "") for o in approved_skill_obstacles if o.get("skill_category")})
    pending_suggestions = []
    for obstacle in obstacles_collection.find({"project_id": project_id, "suggestion_status": "pending_approval"}):
        pending_suggestions.append(
            {
                "obstacle_id": str(obstacle.get("_id")),
                "category": obstacle.get("category"),
                "description": obstacle.get("description"),
                "ai_suggestion": obstacle.get("ai_suggestion"),
                "suggested_skill_category": obstacle.get("suggested_skill_category"),
            }
        )

    base_difficulty = str(project.get("difficulty_level", "medium")).lower()
    effective_difficulty = base_difficulty
    if suggested_diff == "easier" or non_skill_pressure >= 3:
        if base_difficulty == "hard":
            effective_difficulty = "medium"
        elif base_difficulty == "medium":
            effective_difficulty = "easy"
        else:
            effective_difficulty = "easy"
    elif suggested_diff == "harder" and non_skill_pressure == 0:
        if base_difficulty == "easy":
            effective_difficulty = "medium"
        elif base_difficulty == "medium":
            effective_difficulty = "hard"
        else:
            effective_difficulty = "hard"

    try:
        deadline = date.fromisoformat(str(project.get("deadline")))
        days_left = max((deadline - date.today()).days + 1, 1)
    except Exception:
        days_left = max(len(pending_tasks), 1)

    total_effort_remaining = sum(_effort_units(t) for t in pending_tasks)
    base_daily_effort = max(ceil(total_effort_remaining / days_left), 1)

    if effective_difficulty == "easy":
        base_daily_effort = max(base_daily_effort - 1, 1)
    elif effective_difficulty == "hard":
        base_daily_effort = base_daily_effort + 1

    if non_skill_pressure >= 3:
        base_daily_effort = max(base_daily_effort - 1, 1)

    if available_minutes is not None:
        time_budget_units = max(ceil(available_minutes / 30), 1)
        base_daily_effort = min(base_daily_effort, time_budget_units)

    selected_tasks: list[dict] = []
    used_effort = 0
    for task in pending_tasks:
        effort = _effort_units(task)
        if selected_tasks and used_effort + effort > base_daily_effort:
            continue
        selected_tasks.append(task)
        used_effort += effort
        if used_effort >= base_daily_effort:
            break

    if not selected_tasks:
        selected_tasks = [pending_tasks[0]]

    primary_task = selected_tasks[0]
    combined_description = "\n".join(
        [f"- {t.get('title', 'Task')}: {t.get('description', '')}" for t in selected_tasks]
    )
    merged_proof_types = sorted(
        {
            str(p).lower()
            for t in selected_tasks
            for p in t.get("proof_types", ["text"])
            if str(p).lower() in {"text", "image"}
        }
    ) or ["text"]
    total_recommended_duration_minutes = sum(_effort_units(t) for t in selected_tasks) * 30

    skill_focus_line = ""
    if approved_skill_categories:
        skill_focus_line = f" Focus extra attention on skill gaps: {', '.join(approved_skill_categories)}."

    # Generate AI challenge description
    ai_result = _ai_generate_challenge_description(
        project, selected_tasks, effective_difficulty, days_left, available_minutes
    )
    ai_description = ai_result.get("description", "")
    ai_minutes = ai_result.get("estimated_minutes")
    if ai_minutes:
        total_recommended_duration_minutes = ai_minutes

    # Fall back to template description if AI returned nothing
    if not ai_description:
        ai_description = (
            f"Today: {len(selected_tasks)} task(s) bundled for {project.get('name', 'project')}"
            f". Keep pace toward deadline with {effective_difficulty} intensity."
            f"{skill_focus_line}"
        ).strip()

    challenge_doc = {
        "task_id": str(primary_task.get("_id")),
        "task_ids": [str(t.get("_id")) for t in selected_tasks],
        "project_id": project_id,
        "description": combined_description,
        "challenge_description": ai_description,
        "proof_instructions": "\n".join(
            [
                f"- {t.get('title', 'Task')}: {t.get('proof_instructions', 'Submit concrete proof for this task.')}"
                for t in selected_tasks
            ]
        ),
        "proof_types": merged_proof_types,
        "proof_scheme": (
            f"Assess based on completion quality, clarity, and relevance to today's objective. "
            f"Difficulty guidance: {effective_difficulty}. {performance_recommendation}"
        ).strip(),
        "recommended_duration": total_recommended_duration_minutes,
        "recommended_duration_minutes": total_recommended_duration_minutes,
        "ai_suggested_duration_minutes": int(ai_minutes) if ai_minutes else None,
        "duration_source": "ai" if ai_minutes else "heuristic",
        "duration_unit": "minutes",
        "status": "pending",
        "daily_date": today,
        "curated": True,
        "difficulty_applied": effective_difficulty,
        "skill_focus": approved_skill_categories,
        "pending_suggestions": pending_suggestions,
        "bundle_size": len(selected_tasks),
        "effort_budget": base_daily_effort,
    }

    insert_result = challenges_collection.insert_one(challenge_doc)
    challenge_doc["_id"] = str(insert_result.inserted_id)
    return {"source": "generated", "challenge": challenge_doc}

@router.post("/")
def create_challenge(challenge: Challenge):
    result = challenges_collection.insert_one(challenge.dict())
    return {"challenge_id": str(result.inserted_id)}

@router.get("/project/{project_id}/daily")
def get_project_daily_challenge(
    project_id: str,
    available_minutes: int | None = Query(default=None, ge=1),
):
    """
    Returns exactly one curated challenge per project per day.
    Selection is based on:
    - split tasks stored for the project
    - project deadline pressure
    - difficulty signal from performance + non-skill obstacles
    - approved skill-gap obstacles to carry into next challenge focus
    """
    return _get_or_create_daily_challenge(project_id, available_minutes)


@router.get("/daily-priority")
def get_daily_priority_challenges(available_minutes: int = Query(..., ge=1)):
    projects = list(projects_collection.find({"status": {"$ne": "completed"}}))
    projects.sort(key=lambda p: (-_project_urgency_score(p), str(p.get("deadline", "9999-12-31"))))

    # Distribute today's minutes across prioritized projects.
    allocations = _allocate_minutes_by_priority(projects, available_minutes)

    results = []
    for project, project_minutes in allocations:
        project_id = str(project.get("_id"))
        challenge_payload = _get_or_create_daily_challenge(project_id, project_minutes)
        results.append(
            {
                "project": {
                    "_id": project_id,
                    "name": project.get("name"),
                    "priority": project.get("priority", 0),
                    "deadline": project.get("deadline"),
                    "status": project.get("status", "active"),
                },
                "allocated_minutes": project_minutes,
                "challenge": challenge_payload.get("challenge"),
            }
        )

    return {
        "available_minutes": available_minutes,
        "project_count": len(results),
        "items": results,
    }


@router.get("/active-by-project")
def list_active_challenges_by_project():
    projects = list(projects_collection.find({"status": {"$ne": "completed"}}))
    projects.sort(key=lambda p: (-int(p.get("priority", 0)), str(p.get("deadline", "9999-12-31"))))

    rows = []
    for project in projects:
        pid = str(project.get("_id"))
        challenge = challenges_collection.find_one(
            {
                "project_id": {"$in": _to_project_id_variants(pid)},
                "status": {"$in": ACTIVE_CHALLENGE_STATUSES},
            },
            sort=[("accepted_at", -1), ("_id", -1)],
        )
        if challenge:
            rows.append(
                {
                    "project": {
                        "_id": pid,
                        "name": project.get("name"),
                        "priority": project.get("priority", 0),
                        "deadline": project.get("deadline"),
                    },
                    "challenge": _normalize_challenge_doc(challenge),
                }
            )

    return rows


@router.patch("/{challenge_id}/accept")
def accept_challenge(challenge_id: str, payload: AcceptChallengeRequest):
    try:
        challenge = challenges_collection.find_one({"_id": ObjectId(challenge_id)})
        challenge_filter = {"_id": ObjectId(challenge_id)}
    except Exception:
        challenge = challenges_collection.find_one({"_id": challenge_id})
        challenge_filter = {"_id": challenge_id}

    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Enforce one accepted/active challenge at a time across all projects.
    other_active = _find_any_active_challenge(exclude_id=challenge_id)
    if other_active:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Finish and verify the current active challenge before accepting a new one.",
                "active_challenge_id": str(other_active.get("_id")),
                "active_project_id": str(other_active.get("project_id")) if other_active.get("project_id") else None,
            },
        )

    duration_minutes = payload.recommended_duration_minutes or challenge.get("recommended_duration_minutes") or challenge.get("recommended_duration") or 30
    duration_minutes = max(int(duration_minutes), 1)
    accepted_at = datetime.now(timezone.utc)
    countdown_end = accepted_at + timedelta(minutes=duration_minutes)

    update_doc = {
        "status": "active",
        "accepted_at": accepted_at,
        "countdown_end": countdown_end,
        "recommended_duration": duration_minutes,
        "recommended_duration_minutes": duration_minutes,
        "duration_unit": "minutes",
    }
    if payload.proof_types is not None:
        update_doc["proof_types"] = payload.proof_types or ["text"]
    if payload.proof_scheme is not None:
        update_doc["proof_scheme"] = payload.proof_scheme
    if payload.challenge_description is not None:
        update_doc["challenge_description"] = payload.challenge_description
    if payload.proof_instructions is not None:
        update_doc["proof_instructions"] = payload.proof_instructions

    challenges_collection.update_one(challenge_filter, {"$set": update_doc})
    updated = challenges_collection.find_one(challenge_filter)
    return {"accepted": True, "challenge": _normalize_challenge_doc(updated)}


@router.patch("/{challenge_id}/tasks-status")
def update_challenge_tasks_status(challenge_id: str, payload: TaskStatusUpdate):
    try:
        challenge = challenges_collection.find_one({"_id": ObjectId(challenge_id)})
    except Exception:
        challenge = challenges_collection.find_one({"_id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    done_ids = [str(tid) for tid in payload.completed_task_ids]
    keep_pending = [str(tid) for tid in payload.keep_pending_task_ids]

    for task_id in done_ids:
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

    for task_id in keep_pending:
        try:
            tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"completed": False, "completion_status": "pending"}},
            )
        except Exception:
            tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"completed": False, "completion_status": "pending"}},
            )

    challenge_update = {
        "status": "partial_completed" if done_ids and keep_pending else "active",
    }
    try:
        challenges_collection.update_one(
            {"_id": ObjectId(challenge_id)},
            {"$set": challenge_update},
        )
    except Exception:
        challenges_collection.update_one(
            {"_id": challenge_id},
            {"$set": challenge_update},
        )

    return {
        "updated": True,
        "completed_task_ids": done_ids,
        "pending_task_ids": keep_pending,
    }


@router.patch("/{challenge_id}/proof-config")
def update_proof_config(challenge_id: str, payload: ProofConfigUpdate):
    update = {
        "proof_types": payload.proof_types,
        "proof_scheme": payload.proof_scheme,
    }
    result = challenges_collection.update_one(
        {"_id": ObjectId(challenge_id)},
        {"$set": update},
    )
    return {
        "updated": result.modified_count > 0,
        "proof_types": payload.proof_types,
        "proof_scheme": payload.proof_scheme,
    }