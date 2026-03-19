from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class Obstacle(BaseModel):
    challenge_id: Optional[str] = None
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    category: str
    description: Optional[str] = None
    submitted_at: Optional[datetime] = None
    status: Optional[str] = "logged"
    ai_suggestion: Optional[str] = None
    suggested_skill_category: Optional[str] = None
    skill_category: Optional[str] = None
    completed_task_ids: Optional[List[str]] = None
    suggestion_status: Optional[str] = "pending_approval"
