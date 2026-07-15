"""Generate and store simple meal illustration cards (SVG) on the server."""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

STATIC_ROOT = Path(__file__).resolve().parents[2] / "static" / "nutrition_images"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:80] or "meal"


def create_meal_svg(
    meal_name: str,
    *,
    meal_type: str | None = None,
    calories: Any = None,
    protein_g: Any = None,
    carbs_g: Any = None,
    fat_g: Any = None,
) -> str:
    """Return an SVG meal card string (no external deps)."""
    title = html.escape(str(meal_name)[:48])
    mtype = html.escape(str(meal_type or "meal").title())
    cal = html.escape(str(calories if calories is not None else "-"))
    protein = html.escape(str(protein_g if protein_g is not None else "-"))
    carbs = html.escape(str(carbs_g if carbs_g is not None else "-"))
    fat = html.escape(str(fat_g if fat_g is not None else "-"))

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#14532d"/>
      <stop offset="100%" stop-color="#064e3b"/>
    </linearGradient>
  </defs>
  <rect width="640" height="400" rx="24" fill="url(#bg)"/>
  <rect x="24" y="24" width="592" height="352" rx="18" fill="#052e1c" stroke="#34d399" stroke-width="2"/>

  <!-- plate icon -->
  <g transform="translate(90, 100)">
    <ellipse cx="90" cy="100" rx="85" ry="70" fill="#ecfdf5" stroke="#6ee7b7" stroke-width="4"/>
    <ellipse cx="90" cy="100" rx="50" ry="40" fill="#bbf7d0" opacity="0.7"/>
    <circle cx="70" cy="90" r="14" fill="#f59e0b"/>
    <circle cx="105" cy="95" r="12" fill="#ef4444"/>
    <ellipse cx="90" cy="120" rx="22" ry="12" fill="#22c55e"/>
  </g>

  <text x="280" y="110" fill="#a7f3d0" font-family="Arial, Helvetica, sans-serif" font-size="14" font-weight="600">{mtype}</text>
  <text x="280" y="150" fill="#f8fafc" font-family="Arial, Helvetica, sans-serif" font-size="26" font-weight="700">{title}</text>
  <text x="280" y="195" fill="#d1fae5" font-family="Arial, Helvetica, sans-serif" font-size="18">{cal} kcal</text>
  <text x="280" y="230" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="15">P {protein}g  ·  C {carbs}g  ·  F {fat}g</text>

  <rect x="280" y="270" width="170" height="36" rx="18" fill="#059669"/>
  <text x="365" y="294" text-anchor="middle" fill="#ecfdf5" font-family="Arial, Helvetica, sans-serif" font-size="14" font-weight="600">Meal Guide</text>
</svg>
'''


def save_meal_image(
    plan_id: int,
    meal_name: str,
    *,
    meal_type: str | None = None,
    calories: Any = None,
    protein_g: Any = None,
    carbs_g: Any = None,
    fat_g: Any = None,
) -> str:
    """
    Write an SVG meal card under static/nutrition_images/{plan_id}/.
    Returns public URL path e.g. /static/nutrition_images/1/oats.svg
    """
    plan_dir = STATIC_ROOT / str(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(meal_name)
    filename = f"{slug}.svg"
    path = plan_dir / filename
    counter = 2
    while path.exists():
        filename = f"{slug}-{counter}.svg"
        path = plan_dir / filename
        counter += 1

    svg = create_meal_svg(
        meal_name,
        meal_type=meal_type,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )
    path.write_text(svg, encoding="utf-8")
    return f"/static/nutrition_images/{plan_id}/{filename}"


def attach_images_to_nutrition_plan(plan_id: int, plan_data: dict[str, Any]) -> dict[str, Any]:
    """Attach image_url to meals (and snacks when needs_image is true)."""
    days = plan_data.get("days") or []
    for day in days:
        for meal in day.get("meals") or []:
            if not isinstance(meal, dict):
                continue
            if not meal.get("needs_image", True):
                continue
            meal["image_url"] = save_meal_image(
                plan_id,
                str(meal.get("name") or "Meal"),
                meal_type=str(meal.get("meal_type") or "meal"),
                calories=meal.get("calories"),
                protein_g=meal.get("protein_g"),
                carbs_g=meal.get("carbs_g"),
                fat_g=meal.get("fat_g"),
            )
        for snack in day.get("snacks") or []:
            if not isinstance(snack, dict):
                continue
            if not snack.get("needs_image", False):
                continue
            snack["image_url"] = save_meal_image(
                plan_id,
                str(snack.get("name") or "Snack"),
                meal_type="snack",
                calories=snack.get("calories"),
                protein_g=snack.get("protein_g"),
                carbs_g=snack.get("carbs_g"),
                fat_g=snack.get("fat_g"),
            )
    return plan_data
