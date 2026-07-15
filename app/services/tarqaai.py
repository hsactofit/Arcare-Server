"""TarqaAI client — OpenAI-compatible chat completions gateway."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from app.config import settings


class TarqaAIError(Exception):
    """Raised when the TarqaAI API call fails."""


def _extract_message(data: dict[str, Any]) -> str:
    """Support both TarqaAI simplified and OpenAI-compatible response shapes."""
    if isinstance(data.get("message"), str) and data["message"].strip():
        return data["message"]

    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    parts.append(part)
            joined = "".join(parts).strip()
            if joined:
                return joined

    # Some gateways nest under data
    nested = data.get("data")
    if isinstance(nested, dict):
        return _extract_message(nested)

    raise TarqaAIError(f"Unexpected TarqaAI response shape: {list(data.keys())}")


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.6,
    timeout: float = 90.0,
) -> str:
    """
    Call TarqaAI POST /v1/chat/completions and return the assistant text.
    Docs: https://app.tarqaai.com/docs/chat-api
    """
    api_key = (settings.TARQAAI_API_KEY or "").strip()
    if not api_key:
        raise TarqaAIError(
            "TARQAAI_API_KEY is not configured. Add it to the server .env file."
        )

    base = settings.TARQAAI_BASE_URL.rstrip("/")
    url = f"{base}/v1/chat/completions"
    payload = {
        "model": model or settings.TARQAAI_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.RequestError as exc:
        raise TarqaAIError(f"Failed to reach TarqaAI: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:500]
        raise TarqaAIError(
            f"TarqaAI error {response.status_code}: {detail}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise TarqaAIError("TarqaAI returned non-JSON response") from exc

    return _extract_message(data)


def parse_json_from_llm(text: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM reply (handles markdown fences)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    # Try direct parse first
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fall back to first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(cleaned[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    raise TarqaAIError("Could not parse plan JSON from AI response")


async def generate_workout_plan_for_range(
    *,
    start_date,
    end_date,
    goal: str | None = None,
    experience_level: str | None = None,
    location: str | None = None,
    equipment: list[str] | None = None,
    focus_areas: list[str] | None = None,
    session_duration_minutes: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Generate a date-range workout plan: which exercise, how_to, sets/reps."""
    system = (
        "You are an expert certified personal trainer. "
        "Create practical day-by-day workout schedules. "
        "Respond with ONLY valid JSON — no markdown."
    )
    prefs = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "goal": goal,
        "experience_level": experience_level,
        "location": location,
        "equipment": equipment,
        "focus_areas": focus_areas,
        "session_duration_minutes": session_duration_minutes,
        "notes": notes,
    }
    user_prompt = f"""
Create a workout plan from {start_date} to {end_date} (inclusive).

Preferences:
{json.dumps(prefs, indent=2)}

Return JSON:
{{
  "title": "plan title",
  "goal": "goal text",
  "notes": "optional notes",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "focus": "e.g. Upper body / Legs / Rest",
      "is_rest_day": false,
      "notes": null,
      "exercises": [
        {{
          "name": "Push-ups",
          "how_to": "Keep body straight, lower chest, push up",
          "sets": 3,
          "reps": "10-12",
          "duration_minutes": null,
          "rest_seconds": 60,
          "equipment": "bodyweight",
          "muscle_groups": ["chest", "triceps"]
        }}
      ]
    }}
  ]
}}

Rules:
- Include EVERY calendar date from start_date through end_date.
- Rest days: is_rest_day true and exercises [].
- Training days: 4-8 exercises with clear how_to, sets, reps (or duration_minutes for timed work).
- Match equipment and experience level.
""".strip()

    raw = await chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        timeout=120.0,
    )
    return parse_json_from_llm(raw)


async def generate_nutrition_plan_for_range(
    *,
    start_date,
    end_date,
    goal: str | None = None,
    dietary_preference: str | None = None,
    allergies: list[str] | None = None,
    meals_per_day: int = 3,
    cuisine: str | None = None,
    daily_calories_target: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Generate a date-range meal plan: what to eat, how_to, portion/macros."""
    system = (
        "You are an expert dietitian. Create practical day-by-day meal plans. "
        "Respect allergies. Respond with ONLY valid JSON — no markdown."
    )
    prefs = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "goal": goal,
        "dietary_preference": dietary_preference,
        "allergies": allergies,
        "meals_per_day": meals_per_day,
        "cuisine": cuisine,
        "daily_calories_target": daily_calories_target,
        "notes": notes,
    }
    user_prompt = f"""
Create a nutrition plan from {start_date} to {end_date} (inclusive).

Preferences:
{json.dumps(prefs, indent=2)}

Return JSON:
{{
  "title": "plan title",
  "goal": "goal text",
  "notes": "optional notes",
  "daily_calories_target": 2000,
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "notes": null,
      "meals": [
        {{
          "meal_type": "breakfast",
          "name": "Oats with banana",
          "how_to": "Cook oats, top with banana slices",
          "portion": "1 bowl (350g)",
          "calories": 400,
          "protein_g": 15,
          "carbs_g": 60,
          "fat_g": 10,
          "ingredients": ["oats", "banana", "milk"]
        }}
      ]
    }}
  ]
}}

Rules:
- Include EVERY calendar date from start_date through end_date.
- Each day has about {meals_per_day} meals (meal_type: breakfast/lunch/dinner/snack).
- Every meal needs name, how_to, portion (how much), and macros when possible.
- Strictly avoid allergies.
""".strip()

    raw = await chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        timeout=120.0,
    )
    return parse_json_from_llm(raw)
