"""Task splitter: AI-powered project-to-task decomposition.

Separates two concerns:
  split_project_into_tasks  — logical subdivisions of a project (persisted as Task docs)
  generate_daily_challenges — single-day actionable commitments from a task (legacy shim kept)
"""

import json
import math
import os

from openai import OpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Fallback model order — use only models valid on the configured provider.
# deepseek-chat / deepseek-reasoner are DeepSeek-direct names; they're invalid
# on NVIDIA NIM and cause instant 404 errors, so we don't list them here.
# Add any extra NVIDIA NIM models you want to fall back to if v3.2 fails.
_PREFERRED_MODELS: list[str] = []


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


def _generate_text(prompt: str, model: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        timeout=120,
    )
    return (response.choices[0].message.content or "").strip()


def _call_ai(prompt: str, model: str | None = None) -> str:
    if model:
        return _generate_text(prompt, model)

    last_error = None
    for model_name in _candidate_models():
        try:
            return _generate_text(prompt, model_name)
        except Exception as exc:
            msg = str(exc)
            # Quota exhausted — all models share the same quota; stop immediately.
            if "429" in msg and ("RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()):
                raise RuntimeError(
                    f"DeepSeek API quota exhausted (429 RESOURCE_EXHAUSTED). "
                    f"Check your plan/billing on your DeepSeek account. "
                    f"Original error: {exc}"
                ) from exc
            last_error = exc
    raise RuntimeError(f"All configured DeepSeek models failed: {last_error}")


# ---------------------------------------------------------------------------
# Primary function: split a project into logical tasks (Phase 2)
# ---------------------------------------------------------------------------

def split_project_into_tasks(
    project_name: str,
    description: str,
    total_days: int,
    difficulty_level: str = "medium",
) -> list[dict]:
    """
    Returns a list of task dicts, each with:
      title, description, estimated_duration (days), difficulty_level, order,
      proof_types (list), proof_instructions
    """
    # Minimum tasks = 25% of total days (at least 1, capped at 50 for sanity)
    min_tasks = max(1, min(math.ceil(total_days * 0.25), 50))

    prompt = f"""You are a senior project planner.
Break the following project into practical, execution-ready tasks.

Project: {project_name}
Description: {description}
Total days available: {total_days}
Difficulty: {difficulty_level}
MINIMUM tasks required: {min_tasks}

Return ONLY a JSON array (no markdown, no explanation) where each item has:
  "title": short task title
    "description": detailed implementation scope and expected output for this task
  "estimated_duration": integer number of days for this task
  "difficulty_level": one of easy/medium/hard
  "order": integer starting from 1
    "proof_types": array of one or more of ["text","image"]
    "proof_instructions": specific evidence required to verify completion

Quality requirements:
- Use concrete tasks, not vague tasks like "understand requirements" or "familiarize yourself".
- Each description should be specific and actionable (roughly 18+ words).
- Reference key modules/features from the project description in the task descriptions.
- Include meaningful proof instructions per task (roughly 10+ words).
- Keep task order logical and build-oriented.
- Use enough tasks to cover the project phases; avoid oversimplified 3-step plans unless the project is tiny.
- You MUST return at least {min_tasks} tasks (25% of {total_days} days).

The sum of estimated_duration values should approximately equal {total_days}.
Return only valid JSON."""

    def _parse_tasks(raw: str) -> list[dict] | None:
        text = raw.strip()
        # Strip markdown code fences if the model wraps output
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        # Find the first '[' in case of any leading prose
        bracket = text.find("[")
        if bracket != -1:
            text = text[bracket:]
        try:
            tasks = json.loads(text)
            if isinstance(tasks, list) and tasks:
                return tasks
        except Exception:
            pass
        return None

    def _is_low_detail(tasks: list[dict]) -> bool:
        if not tasks:
            return True
        if total_days >= 14 and len(tasks) < 5:
            return True
        # Enforce 25% minimum task count
        if len(tasks) < min_tasks:
            return True

        generic_phrases = (
            "understand the task",
            "familiarize",
            "read and understand",
            "create a reading plan",
            "overview",
        )

        low_detail_count = 0
        for task in tasks:
            title = str(task.get("title", "")).lower()
            desc = str(task.get("description", "")).strip()
            proof = str(task.get("proof_instructions", "")).strip()

            desc_words = len(desc.split())
            proof_words = len(proof.split())

            if any(p in title or p in desc.lower() for p in generic_phrases):
                low_detail_count += 1
                continue
            if desc_words < 12 or proof_words < 6:
                low_detail_count += 1

        # If at least half the tasks are weak, ask model to regenerate with detail.
        return low_detail_count >= max(1, len(tasks) // 2)

    def _normalize_tasks(tasks: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for i, task in enumerate(tasks, start=1):
            proof_types = task.get("proof_types")
            if not isinstance(proof_types, list) or not proof_types:
                proof_types = ["text"]

            normalized.append(
                {
                    "title": str(task.get("title") or f"Task {i}").strip(),
                    "description": str(task.get("description") or "").strip(),
                    "estimated_duration": int(task.get("estimated_duration") or 1),
                    "difficulty_level": str(task.get("difficulty_level") or difficulty_level or "medium").strip(),
                    "order": int(task.get("order") or i),
                    "proof_types": proof_types,
                    "proof_instructions": str(task.get("proof_instructions") or "Provide clear completion evidence.").strip(),
                }
            )
        return normalized

    # First attempt
    result = _parse_tasks(_call_ai(prompt))
    if result is not None and not _is_low_detail(result):
        return _normalize_tasks(result)

    # Second attempt: force richer rewrite when output is vague/coarse.
    richer_prompt = f"""Return ONLY a raw JSON array.
Rewrite and improve the task plan below so it is detailed, concrete, and implementation-ready.

Project: {project_name}
Description: {description}
Total days: {total_days}
Difficulty: {difficulty_level}
MINIMUM tasks required: {min_tasks}

Current plan to improve:
{json.dumps(result or [], ensure_ascii=True)}

Rules:
- No vague steps (e.g., understand/familiarize/overview).
- Each description must be concrete and specific (18+ words).
- Each proof_instructions must be specific and verifiable (10+ words).
- Preserve valid structure and ordering keys.
- Keep the total duration approximately {total_days}.
- Return at least {min_tasks} tasks.

Output fields per task:
  "title", "description", "estimated_duration", "difficulty_level", "order",
  "proof_types", "proof_instructions"."""

    result = _parse_tasks(_call_ai(richer_prompt))
    if result is not None and not _is_low_detail(result):
        return _normalize_tasks(result)

    # Final attempt: strict JSON fallback
    strict_prompt = f"""Return ONLY a raw JSON array, starting with [ and ending with ].
No prose, no markdown, no code fences. Just the JSON array.

Break this project into tasks:
Project: {project_name}
Description: {description}
Total days: {total_days}
Difficulty: {difficulty_level}

Each element must have these keys:
  "title", "description", "estimated_duration" (int days), "difficulty_level",
    "order" (int from 1), "proof_types" (array of text/image),
  "proof_instructions"

The sum of estimated_duration values should approximately equal {total_days}."""

    result = _parse_tasks(_call_ai(strict_prompt))
    if result is not None:
        return _normalize_tasks(result)

    # AI failed twice — surface the error instead of silently degrading
    raise RuntimeError(
        "AI task splitting failed to return valid JSON after two attempts. "
        "Check your DEEPSEEK_API_KEY and model availability."
    )


# ---------------------------------------------------------------------------
# Legacy shim: kept so existing challenge-generation callers still work
# ---------------------------------------------------------------------------

def generate_daily_challenges(project_name: str, description: str, total_days: int) -> list[str]:
    """Generate plain-text daily challenge strings (legacy format)."""
    prompt = f"""Create {total_days} daily challenges for this project: {project_name}.
Description: {description}
Format each as:
Day <number>: <challenge description>
Proof: <how to verify completion>"""

    text = _call_ai(prompt)
    return [f"Day {t.strip()}" for t in text.split("Day ")[1:]]