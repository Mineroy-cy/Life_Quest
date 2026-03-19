"""Compatibility layer for AI helpers used by routes.

Re-exports both the legacy challenge generator and the new task splitter
so existing and new imports all resolve from this single module.
"""

from app.services.task_splitter import generate_daily_challenges, split_project_into_tasks

__all__ = ["generate_daily_challenges", "split_project_into_tasks"]
