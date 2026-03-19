from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

class Evidence(BaseModel):
    task_id: Optional[str] = None
    completed: bool = True
    proof_content: Optional[str] = ""
    proof_entries: Optional[Dict[str, str]] = None
    no_evidence: Optional[bool] = False
    completed_task_ids: Optional[List[str]] = None
    obstacles: Optional[List[str]] = []
    challenge_id: Optional[str] = None
    evidence_type: Optional[List[str]] = None
    proof_files: Optional[List[Dict[str, Any]]] = None
    content: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verification_status: Optional[str] = None