from openai import OpenAI
from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import os
import json
import re
from typing import Optional

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

_PREFERRED_MODELS = []


def _normalize_model_name(name: str) -> str:
    model_name = name.strip()
    return model_name


def _candidate_models() -> list[str]:
    configured = os.getenv("DEEPSEEK_MODEL", DEEPSEEK_MODEL).strip()
    requested = [_normalize_model_name(m) for m in configured.split(",") if m.strip()]

    candidates = []
    for name in requested:
        if name not in candidates:
            candidates.append(name)
    for name in _PREFERRED_MODELS:
        if name not in candidates:
            candidates.append(name)
    return candidates


def _extract_response_text(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""

    first = choices[0]
    message = getattr(first, "message", None)
    if not message:
        return ""

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    # Some providers may return structured content blocks.
    if isinstance(content, list):
        parts = []
        for block in content:
            text_value = ""
            if isinstance(block, dict):
                text_value = str(block.get("text") or "")
            else:
                text_value = str(getattr(block, "text", "") or "")
            if text_value:
                parts.append(text_value)
        return "\n".join(parts).strip()

    return str(content or "").strip()


def _generate_text(prompt: str, model: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        timeout=60,
    )
    return _extract_response_text(response)


def _generate_multimodal(prompt: str, image_urls: list[str], model: str) -> str:
    user_content = [{"type": "text", "text": prompt}]
    for image_url in image_urls[:3]:
        user_content.append({"type": "image_url", "image_url": {"url": image_url}})

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": user_content}],
        temperature=0.0,
        timeout=90,
    )
    return _extract_response_text(response)


def _extract_verdict_and_reason(response_text: str) -> tuple[bool, str]:
    text = (response_text or "").strip()
    if not text:
        return False, "No model response returned for verification."

    # Prefer strict JSON. If the model wraps JSON in prose, extract the first object block.
    json_candidate = text
    try:
        parsed = json.loads(json_candidate)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        parsed = None
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None

    if isinstance(parsed, dict):
        approved = bool(parsed.get("approved", False))
        reason = str(parsed.get("reason") or "").strip()
        if not reason:
            reason = "Verification did not include an explanation."
        return approved, reason

    lowered = text.lower()
    approved = "true" in lowered and "false" not in lowered
    reason = text if text else "Verification did not include an explanation."
    return approved, reason

def verify_task_completion(
    task_id: str,
    proof_content: str,
    expected_proof_types: Optional[list[str]] = None,
    proof_scheme: str = "",
    evidence_types: Optional[list[str]] = None,
    proof_files: Optional[list[dict]] = None,
) -> dict:
    """
    Verify if a submitted proof satisfies the task.
    Returns a dict: {"approved": bool, "reason": str, "raw_answer": str}
    """
    expected_types_text = ", ".join(expected_proof_types or []) or "not specified"
    provided_types_text = ", ".join(evidence_types or []) or "not specified"

    prompt = f"""
    You are a verification AI.
    Task ID: {task_id}
    Task proof: {proof_content}
    Expected proof types: {expected_types_text}
    Provided evidence types: {provided_types_text}
    Proof marking scheme/instructions: {proof_scheme or 'not specified'}

    Evaluate using BOTH:
    1) Whether the evidence content indicates completion.
    2) Whether provided evidence types and format align with expected proof types and scheme.

        Return STRICT JSON only, no markdown:
        {{
            "approved": true/false,
            "reason": "one concise sentence explaining why accepted or rejected"
        }}
    """

    image_urls: list[str] = []
    for file_entry in proof_files or []:
        method = str(file_entry.get("method", "")).lower()
        if method != "image":
            continue
        url = str(file_entry.get("url") or file_entry.get("data_url") or "").strip()
        if url:
            image_urls.append(url)

    last_error = None
    response = None
    for model_name in _candidate_models():
        try:
            if image_urls:
                response = _generate_multimodal(prompt, image_urls, model_name)
            else:
                response = _generate_text(prompt, model_name)
            break
        except Exception as exc:  # pragma: no cover
            last_error = exc

    if response is None:
        raise RuntimeError(f"All configured DeepSeek models failed: {last_error}")
    
    approved, reason = _extract_verdict_and_reason(response)
    return {
        "approved": approved,
        "reason": reason,
        "raw_answer": response,
    }