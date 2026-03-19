from pydantic import BaseModel
from typing import Optional

class Task(BaseModel):
    project_id: str
    day_number: int
    description: str
    proof_method: Optional[str] = "text"
    completed: bool = False
    title: Optional[str] = None
    estimated_duration: Optional[int] = None
    difficulty_level: Optional[str] = None
    order: Optional[int] = None
    completion_status: Optional[str] = None