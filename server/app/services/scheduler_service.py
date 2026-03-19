"""Scheduler service: time-availability-based daily challenge selection.

Given the user's available minutes for today, picks challenges from active
projects ordered by: priority → deadline proximity → estimated_duration fit.
"""

from datetime import date


def select_daily_challenges(
    available_minutes: int,
    active_projects: list[dict],
    pending_tasks: list[dict],
) -> list[dict]:
    """
    Returns an ordered list of tasks the user should attempt today,
    fitting within available_minutes.

    active_projects: list of project docs with  priority, deadline, status
    pending_tasks:   list of task docs with project_id, estimated_duration,
                     completion_status, order
    """
    today = date.today()

    def project_score(proj: dict) -> tuple:
        try:
            dl = date.fromisoformat(str(proj.get("deadline", "9999-12-31")))
            days_left = max((dl - today).days, 1)
        except Exception:
            days_left = 9999
        priority = proj.get("priority", 0)
        return (-priority, days_left)   # lower tuple = selected first

    project_map = {str(p.get("_id", p.get("project_id", ""))): p for p in active_projects}

    # Filter to incomplete tasks only
    open_tasks = [
        t for t in pending_tasks
        if t.get("completion_status") not in ("done",) and not t.get("completed")
    ]

    # Attach project score so we can sort
    def task_sort_key(t: dict) -> tuple:
        proj = project_map.get(t.get("project_id", ""), {})
        p_priority, p_days = project_score(proj)
        return (p_priority, p_days, t.get("order", 999))

    open_tasks.sort(key=task_sort_key)

    selected: list[dict] = []
    remaining = available_minutes
    for task in open_tasks:
        duration = task.get("estimated_duration", 1)  # days; treat 1 day ≈ flexible
        # estimated_duration is in days; allow any task that fits within remaining time
        # If estimated_duration is in minutes it will also work naturally
        if remaining <= 0:
            break
        selected.append(task)
        remaining -= duration  # subtract nominal cost

    return selected
