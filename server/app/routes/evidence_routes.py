from fastapi import APIRouter, HTTPException
from app.models.evidence import Evidence
from app.core.database import evidence_collection, tasks_collection, challenges_collection
from app.services.verification_engine import verify_task_completion
from app.services.progress_service import persist_project_progress
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()


def _resolve_challenge(evidence: Evidence):
    if evidence.challenge_id:
        try:
            challenge = challenges_collection.find_one({"_id": ObjectId(evidence.challenge_id)})
            if challenge:
                return challenge
        except Exception:
            pass

    # Fallback: latest challenge by task id
    if evidence.task_id:
        return challenges_collection.find_one(
            {"task_id": evidence.task_id},
            sort=[("_id", -1)],
        )
    return None


def _mark_task_done(task_id: str):
    # Tries ObjectId first, then legacy string key fallback.
    try:
        result = tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"completed": True, "completion_status": "done"}},
        )
        if result.modified_count:
            return
    except Exception:
        pass

    tasks_collection.update_one(
        {"_id": task_id},
        {"$set": {"completed": True, "completion_status": "done"}},
    )


def _mark_tasks_done(task_ids: list[str]):
    for task_id in task_ids:
        _mark_task_done(task_id)


def _extract_target_task_ids(challenge: dict | None) -> list[str]:
    if not challenge:
        return []

    if challenge and challenge.get("task_ids"):
        ids = [str(tid) for tid in challenge.get("task_ids", []) if tid]
        if ids:
            return ids

    if challenge.get("task_id"):
        return [str(challenge.get("task_id"))]
    return []


def _resolve_project_id_for_progress(challenge: dict | None, task_ids: list[str]) -> str | None:
    if challenge and challenge.get("project_id"):
        return str(challenge.get("project_id"))

    for task_id in task_ids:
        try:
            task_doc = tasks_collection.find_one({"_id": ObjectId(task_id)})
        except Exception:
            task_doc = tasks_collection.find_one({"_id": task_id})
        if task_doc and task_doc.get("project_id"):
            return str(task_doc.get("project_id"))
    return None

@router.post("/")
def submit_evidence(evidence: Evidence):
    challenge = _resolve_challenge(evidence)
    if not challenge:
        raise HTTPException(
            status_code=400,
            detail="Challenge context required. Submit evidence with challenge_id or a valid task-linked challenge.",
        )

    proof_types = []
    proof_scheme = ""
    if challenge:
        proof_types = challenge.get("proof_types") or []
        proof_scheme = challenge.get("proof_scheme") or challenge.get("proof_instructions", "")

    proof_entries = evidence.proof_entries or {}
    non_empty_entries = [v for v in proof_entries.values() if str(v or "").strip()]
    has_content = bool(str(evidence.proof_content or "").strip())
    if not evidence.no_evidence and not has_content and not non_empty_entries:
        raise HTTPException(
            status_code=400,
            detail="At least one proof method must be provided unless no_evidence is true.",
        )

    evidence_payload = evidence.dict()
    if not evidence_payload.get("submitted_at"):
        evidence_payload["submitted_at"] = datetime.now(timezone.utc)

    merged_content = str(evidence.proof_content or "").strip()
    if non_empty_entries:
        method_lines = [f"{k}: {v}" for k, v in proof_entries.items() if str(v or "").strip()]
        merged_content = (merged_content + "\n" + "\n".join(method_lines)).strip()

    verification_reason = ""

    if evidence.no_evidence:
        verification_result = False
        verification_reason = "No evidence submitted. Challenge marked as obstacle logged."
        evidence_payload["verification_status"] = "no_evidence"

        # Explicitly end active challenge session when user reports no evidence.
        if challenge:
            try:
                challenges_collection.update_one(
                    {"_id": challenge.get("_id")},
                    {
                        "$set": {
                            "status": "obstacle_logged",
                            "countdown_end": datetime.now(timezone.utc),
                            "interrupted_at": datetime.now(timezone.utc),
                        }
                    },
                )
            except Exception:
                pass
    else:
        try:
            verification_outcome = verify_task_completion(
                task_id=evidence.task_id or (challenge.get("task_id") if challenge else ""),
                proof_content=merged_content,
                expected_proof_types=proof_types,
                proof_scheme=proof_scheme,
                evidence_types=evidence.evidence_type,
                proof_files=evidence.proof_files,
            )
            verification_result = bool(verification_outcome.get("approved", False))
            verification_reason = str(verification_outcome.get("reason") or "").strip()
        except Exception as exc:
            verification_result = False
            verification_reason = f"Verification service error: {str(exc)}"
        evidence_payload["verification_status"] = "approved" if verification_result else "rejected"
    if verification_reason:
        evidence_payload["verification_reason"] = verification_reason
    evidence_payload["proof_content"] = merged_content
    result = evidence_collection.insert_one(evidence_payload)

    target_task_ids = _extract_target_task_ids(challenge)
    selected_completed_ids = [str(tid) for tid in (evidence.completed_task_ids or [])]
    task_ids_to_mark = selected_completed_ids or target_task_ids

    # Mark challenge tasks done only when proof is verified.
    if verification_result and task_ids_to_mark:
        _mark_tasks_done(task_ids_to_mark)

        try:
            challenges_collection.update_one(
                {"_id": challenge.get("_id")},
                {
                    "$set": {
                        "status": "completed",
                        "countdown_end": datetime.now(timezone.utc),
                        "completed_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception:
            pass

    # Recalculate project progress after verification
    progress = {}
    if verification_result:
        project_id = _resolve_project_id_for_progress(challenge, task_ids_to_mark)
        if project_id:
            progress = persist_project_progress(project_id)

    return {
        "evidence_id": str(result.inserted_id),
        "task_completed": verification_result,
        "completed_task_ids": task_ids_to_mark if verification_result else [],
        "verification_status": evidence_payload["verification_status"],
        "verification_reason": verification_reason,
        "progress": progress,
    }


@router.get("/challenge/{challenge_id}")
def get_evidence_by_challenge(challenge_id: str):
    records = list(evidence_collection.find({"challenge_id": challenge_id}))
    for record in records:
        record["_id"] = str(record["_id"])
    return records


@router.get("/{task_id}")
def get_evidence(task_id: str):
    evidences = list(evidence_collection.find({"task_id": task_id}))
    for e in evidences:
        e["_id"] = str(e["_id"])
    return evidences