from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import ceil

from bson import ObjectId

from app.core.database import projects_collection, tasks_collection, weekly_objectives_collection


DEFAULT_GOAL_COUNT = 3
DEFAULT_CHALLENGES_PER_GOAL = 6


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_project_id_variants(project_id: str):
    variants = [project_id]
    try:
        variants.append(ObjectId(project_id))
    except Exception:
        pass
    return variants


def _normalize_week_doc(doc: dict | None) -> dict | None:
    if not doc:
        return None
    out = dict(doc)
    out["_id"] = str(out.get("_id"))
    for goal in out.get("goals", []):
        goal["project_id"] = str(goal.get("project_id"))
        for ch in goal.get("challenges", []):
            if ch.get("source_task_id") is not None:
                ch["source_task_id"] = str(ch.get("source_task_id"))
    out["stale_project_ids"] = [str(pid) for pid in out.get("stale_project_ids", [])]
    return out


def _project_urgency_score(project: dict) -> float:
    priority = max(_safe_int(project.get("priority", 1), 1), 1)
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


def _task_minutes(task: dict) -> int:
    # Task estimated_duration in this app is day-like effort units; map unit to 30 min.
    return max(_safe_int(task.get("estimated_duration", 1), 1), 1) * 30


def _buffer_minutes_for_project(project: dict) -> int:
    unit = str(project.get("duration_unit", "days")).lower()
    if unit == "hours":
        return 60
    if unit == "minutes":
        return 10
    return 2 * 24 * 60


def _format_hours(minutes: int) -> float:
    return round(max(minutes, 0) / 60.0, 2)


def _project_warning_and_recommendations(project: dict, pending_tasks: list[dict]) -> dict:
    now = datetime.now(timezone.utc)

    try:
        deadline_date = date.fromisoformat(str(project.get("deadline")))
        deadline_dt = datetime.combine(deadline_date, datetime.max.time(), tzinfo=timezone.utc)
    except Exception:
        deadline_dt = now + timedelta(days=7)

    remaining_effort_minutes = sum(_task_minutes(task) for task in pending_tasks)
    buffer_minutes = _buffer_minutes_for_project(project)

    minutes_to_deadline = max(int((deadline_dt - now).total_seconds() // 60), 0)
    minutes_to_effective_deadline = max(minutes_to_deadline - buffer_minutes, 0)

    if remaining_effort_minutes <= 0:
        tier = "on_track"
        today_minutes = 0
        daily_minutes = 0
    elif minutes_to_effective_deadline <= 0:
        tier = "critical"
        today_minutes = remaining_effort_minutes
        daily_minutes = remaining_effort_minutes
    else:
        days_left_effective = max(minutes_to_effective_deadline / (24 * 60), 1 / 24)
        daily_minutes = max(int(ceil(remaining_effort_minutes / days_left_effective)), 1)

        if minutes_to_effective_deadline <= 24 * 60:
            tier = "critical"
            today_minutes = min(remaining_effort_minutes, max(daily_minutes, int(ceil(remaining_effort_minutes * 0.7))))
        elif minutes_to_effective_deadline <= 3 * 24 * 60:
            tier = "warning"
            today_minutes = min(remaining_effort_minutes, max(daily_minutes, int(ceil(daily_minutes * 1.15))))
        else:
            tier = "on_track"
            today_minutes = min(remaining_effort_minutes, daily_minutes)

    unit = str(project.get("duration_unit", "days")).lower()
    buffer_rule = "Finish at least 2 days before deadline."
    if unit == "hours":
        buffer_rule = "Finish at least 1 hour before deadline."
    elif unit == "minutes":
        buffer_rule = "Finish at least 10 minutes before deadline."

    return {
        "warning_tier": tier,
        "remaining_effort_minutes": remaining_effort_minutes,
        "recommended_today_minutes": today_minutes,
        "recommended_today_hours": _format_hours(today_minutes),
        "recommended_daily_minutes": daily_minutes,
        "recommended_daily_hours": _format_hours(daily_minutes),
        "buffer_minutes": buffer_minutes,
        "buffer_rule": buffer_rule,
        "minutes_to_effective_deadline": minutes_to_effective_deadline,
    }


def _display_challenges_from_tasks(pending_tasks: list[dict], per_goal: int) -> list[dict]:
    ordered = sorted(
        pending_tasks,
        key=lambda t: (t.get("day_number", 10_000), t.get("order", 10_000)),
    )
    if not ordered:
        return []

    display = []
    for i in range(per_goal):
        task = ordered[i % len(ordered)]
        repeated = i >= len(ordered)
        title = str(task.get("title") or f"Task {i + 1}").strip()
        if repeated:
            title = f"{title} (continue)"

        display.append(
            {
                "index": i + 1,
                "title": f"Day {i + 1}: {title}",
                "description": str(task.get("description") or "").strip(),
                "source_task_id": str(task.get("_id")),
                "status": "pending",
                "display_only": True,
            }
        )
    return display


def _candidate_projects_for_week() -> list[dict]:
    projects = list(projects_collection.find({"status": {"$ne": "completed"}}))
    projects.sort(key=lambda p: (-_project_urgency_score(p), str(p.get("deadline", "9999-12-31"))))
    return projects


def _build_weekly_goals(goal_count: int, challenges_per_goal: int) -> list[dict]:
    goals = []
    for project in _candidate_projects_for_week():
        if len(goals) >= goal_count:
            break

        project_id = str(project.get("_id"))
        pending_tasks = _load_pending_tasks(project_id)
        if not pending_tasks:
            continue

        recommendation = _project_warning_and_recommendations(project, pending_tasks)
        display_challenges = _display_challenges_from_tasks(pending_tasks, challenges_per_goal)
        if not display_challenges:
            continue

        goals.append(
            {
                "project_id": project_id,
                "project_name": project.get("name", "Project"),
                "priority": _safe_int(project.get("priority", 0), 0),
                "deadline": project.get("deadline"),
                "criteria": "priority + deadline closeness + progress + difficulty",
                "warning": recommendation,
                "challenges": display_challenges,
            }
        )

    return goals


def _current_week_range() -> tuple[str, str]:
    start = date.today()
    end = start + timedelta(days=5)
    return start.isoformat(), end.isoformat()


def get_active_weekly_objectives(refresh_if_stale: bool = True) -> dict | None:
    active = weekly_objectives_collection.find_one({"status": "active"}, sort=[("created_at", -1)])
    if not active:
        return None

    if refresh_if_stale and active.get("stale_project_ids"):
        return refresh_active_weekly_objectives()

    return _normalize_week_doc(active)


def get_weekly_priority_project_ids() -> list[str]:
    active = get_active_weekly_objectives(refresh_if_stale=True)
    if not active:
        return []
    return [str(goal.get("project_id")) for goal in active.get("goals", []) if goal.get("project_id")]


def start_weekly_objectives(goal_count: int = DEFAULT_GOAL_COUNT, challenges_per_goal: int = DEFAULT_CHALLENGES_PER_GOAL) -> dict:
    weekly_objectives_collection.update_many(
        {"status": "active"},
        {"$set": {"status": "ended", "ended_at": datetime.now(timezone.utc)}},
    )

    goals = _build_weekly_goals(max(goal_count, 1), max(challenges_per_goal, 1))
    week_start, week_end = _current_week_range()

    doc = {
        "status": "active",
        "week_start": week_start,
        "week_end": week_end,
        "created_at": datetime.now(timezone.utc),
        "goal_count": len(goals),
        "challenges_per_goal": max(challenges_per_goal, 1),
        "goals": goals,
        "stale_project_ids": [],
        "source": "split_tasks_of_priority_projects",
    }
    inserted = weekly_objectives_collection.insert_one(doc)
    doc["_id"] = inserted.inserted_id
    return _normalize_week_doc(doc)


def end_weekly_objectives() -> dict:
    active = weekly_objectives_collection.find_one({"status": "active"}, sort=[("created_at", -1)])
    if not active:
        return {"ended": False, "message": "No active week to end"}

    weekly_objectives_collection.update_one(
        {"_id": active.get("_id")},
        {"$set": {"status": "ended", "ended_at": datetime.now(timezone.utc)}},
    )
    return {"ended": True, "week_id": str(active.get("_id"))}


def refresh_active_weekly_objectives() -> dict | None:
    active = weekly_objectives_collection.find_one({"status": "active"}, sort=[("created_at", -1)])
    if not active:
        return None

    existing_done = set()
    for goal in active.get("goals", []):
        project_id = str(goal.get("project_id"))
        for ch in goal.get("challenges", []):
            if str(ch.get("status", "pending")) == "done":
                existing_done.add((project_id, str(ch.get("source_task_id")), str(ch.get("title"))))

    goal_count = _safe_int(active.get("goal_count", DEFAULT_GOAL_COUNT), DEFAULT_GOAL_COUNT)
    challenges_per_goal = _safe_int(active.get("challenges_per_goal", DEFAULT_CHALLENGES_PER_GOAL), DEFAULT_CHALLENGES_PER_GOAL)
    goals = _build_weekly_goals(max(goal_count, 1), max(challenges_per_goal, 1))

    for goal in goals:
        project_id = str(goal.get("project_id"))
        for ch in goal.get("challenges", []):
            key = (project_id, str(ch.get("source_task_id")), str(ch.get("title")))
            if key in existing_done:
                ch["status"] = "done"

    weekly_objectives_collection.update_one(
        {"_id": active.get("_id")},
        {
            "$set": {
                "goals": goals,
                "goal_count": len(goals),
                "updated_at": datetime.now(timezone.utc),
                "stale_project_ids": [],
            }
        },
    )

    updated = weekly_objectives_collection.find_one({"_id": active.get("_id")})
    return _normalize_week_doc(updated)


def mark_weekly_objective_stale(project_id: str | None):
    if not project_id:
        return

    weekly_objectives_collection.update_many(
        {"status": "active"},
        {"$addToSet": {"stale_project_ids": str(project_id)}},
    )


def mark_weekly_challenges_done(project_id: str | None, task_ids: list[str]):
    if not project_id or not task_ids:
        return

    active = weekly_objectives_collection.find_one({"status": "active"}, sort=[("created_at", -1)])
    if not active:
        return

    done_set = {str(tid) for tid in task_ids}
    changed = False
    goals = active.get("goals", [])

    for goal in goals:
        if str(goal.get("project_id")) != str(project_id):
            continue
        for ch in goal.get("challenges", []):
            if str(ch.get("source_task_id")) in done_set and str(ch.get("status")) != "done":
                ch["status"] = "done"
                changed = True

    if changed:
        weekly_objectives_collection.update_one(
            {"_id": active.get("_id")},
            {"$set": {"goals": goals, "updated_at": datetime.now(timezone.utc)}},
        )


def update_weekly_challenge_status(
    week_id: str,
    project_id: str,
    challenge_index: int,
    done: bool,
) -> dict | None:
    try:
        week_obj_id = ObjectId(week_id)
    except Exception:
        return None

    active = weekly_objectives_collection.find_one({"_id": week_obj_id, "status": "active"})
    if not active:
        return None

    target_status = "done" if done else "pending"
    changed = False
    goals = active.get("goals", [])

    for goal in goals:
        if str(goal.get("project_id")) != str(project_id):
            continue
        for challenge in goal.get("challenges", []):
            if _safe_int(challenge.get("index"), -1) == _safe_int(challenge_index, -1):
                if str(challenge.get("status", "pending")) != target_status:
                    challenge["status"] = target_status
                    changed = True
                break

    if changed:
        weekly_objectives_collection.update_one(
            {"_id": week_obj_id},
            {"$set": {"goals": goals, "updated_at": datetime.now(timezone.utc)}},
        )
        active["goals"] = goals

    return _normalize_week_doc(active)
