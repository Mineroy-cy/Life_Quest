from pydantic import BaseModel
from datetime import date
from typing import Optional, Literal

class Project(BaseModel):
    name: str
    description: str
    priority: int
    start_date: date
    deadline: date
    duration_value: Optional[float] = None
    duration_unit: Optional[Literal["days", "hours", "minutes"]] = None
    status: Optional[str] = "active"
    difficulty_level: Optional[str] = "medium"
    progress_percentage: Optional[float] = 0.0