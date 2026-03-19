from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Challenge(BaseModel):
    task_id: str
    description: str
    proof_instructions: str
    project_id: Optional[str] = None
    challenge_description: Optional[str] = None
    recommended_duration: Optional[int] = None
    accepted_at: Optional[datetime] = None
    countdown_end: Optional[datetime] = None
    # Supports one or many proof types, including user-defined values.
    proof_types: Optional[List[str]] = ["text"]
    # User-editable rubric/marking scheme for verification.
    proof_scheme: Optional[str] = None
    status: Optional[str] = "pending"