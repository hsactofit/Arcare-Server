"""Generate and store simple exercise illustration cards (SVG) on the server."""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

# Project root: app/services/workout_images.py -> ../../
STATIC_ROOT = Path(__file__).resolve().parents[2] / "static" / "workout_images"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:80] or "exercise"


def _muscle_label(muscles: list[str]) -> str:
    if not muscles:
        return "Full body"
    return ", ".join(muscles[:4])


def create_exercise_svg(
    exercise_name: str,
    *,
    muscle_groups: list[str] | None = None,
    sets: Any = None,
    reps: Any = None,
    equipment: str | None = None,
) -> str:
    """Return an SVG card string for an exercise (no external deps)."""
    title = html.escape(exercise_name[:48])
    muscles = html.escape(_muscle_label(muscle_groups or []))
    sets_reps = html.escape(
        f"{sets or '-'} sets × {reps or '-'} reps"
    )
    equip = html.escape((equipment or "bodyweight")[:40])

    # Simple stick-figure style silhouette + info card
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e3a5f"/>
    </linearGradient>
  </defs>
  <rect width="640" height="400" rx="24" fill="url(#bg)"/>
  <rect x="24" y="24" width="592" height="352" rx="18" fill="#0b1220" stroke="#334155" stroke-width="2"/>

  <!-- figure -->
  <g transform="translate(110, 95)" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" fill="none">
    <circle cx="80" cy="28" r="22" fill="#38bdf8" stroke="none"/>
    <path d="M80 55 L80 145"/>
    <path d="M80 75 L30 110"/>
    <path d="M80 75 L130 110"/>
    <path d="M80 145 L35 220"/>
    <path d="M80 145 L125 220"/>
  </g>

  <!-- text -->
  <text x="280" y="120" fill="#f8fafc" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700">{title}</text>
  <text x="280" y="165" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="16">Target: {muscles}</text>
  <text x="280" y="200" fill="#cbd5e1" font-family="Arial, Helvetica, sans-serif" font-size="18">{sets_reps}</text>
  <text x="280" y="235" fill="#64748b" font-family="Arial, Helvetica, sans-serif" font-size="15">Equipment: {equip}</text>

  <rect x="280" y="270" width="160" height="36" rx="18" fill="#0369a1"/>
  <text x="360" y="294" text-anchor="middle" fill="#e0f2fe" font-family="Arial, Helvetica, sans-serif" font-size="14" font-weight="600">Exercise Guide</text>
</svg>
'''


def save_exercise_image(
    plan_id: int,
    exercise_name: str,
    *,
    muscle_groups: list[str] | None = None,
    sets: Any = None,
    reps: Any = None,
    equipment: str | None = None,
) -> str:
    """
    Write an SVG exercise card under static/workout_images/{plan_id}/.
    Returns the public URL path (e.g. /static/workout_images/1/push-ups.svg).
    """
    plan_dir = STATIC_ROOT / str(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(exercise_name)
    filename = f"{slug}.svg"
    path = plan_dir / filename

    # Avoid clobbering duplicates in same plan
    counter = 2
    while path.exists():
        filename = f"{slug}-{counter}.svg"
        path = plan_dir / filename
        counter += 1

    svg = create_exercise_svg(
        exercise_name,
        muscle_groups=muscle_groups,
        sets=sets,
        reps=reps,
        equipment=equipment,
    )
    path.write_text(svg, encoding="utf-8")
    return f"/static/workout_images/{plan_id}/{filename}"


def attach_images_to_plan(plan_id: int, plan_data: dict[str, Any]) -> dict[str, Any]:
    """
    Walk plan days/exercises; generate images where needs_image is true
    (or for every main exercise) and set image_url on each exercise.
    """
    days = plan_data.get("days") or []
    for day in days:
        for exercise in day.get("exercises") or []:
            if not isinstance(exercise, dict):
                continue
            needs = exercise.get("needs_image", True)
            if not needs:
                continue
            url = save_exercise_image(
                plan_id,
                str(exercise.get("name") or "Exercise"),
                muscle_groups=list(exercise.get("muscle_groups") or []),
                sets=exercise.get("sets"),
                reps=exercise.get("reps"),
                equipment=exercise.get("equipment"),
            )
            exercise["image_url"] = url
    return plan_data
