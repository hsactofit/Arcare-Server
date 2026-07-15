"""Nutrition plans by date range: what to eat, how to prepare, how much."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud
from app.services.tarqaai import generate_nutrition_plan_for_range, TarqaAIError
from app.services.nutrition_images import attach_images_to_nutrition_plan

router = APIRouter(
    prefix="/nutrition-plan",
    tags=["Nutrition Plans"],
)

MAX_PLAN_DAYS = 90


def _require_user(db: Session, email: str):
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found.",
        )
    return user


def _validate_date_range(start: date, end: date) -> None:
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )
    span = (end - start).days + 1
    if span > MAX_PLAN_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan range cannot exceed {MAX_PLAN_DAYS} days (got {span}).",
        )


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _serialize_days(days: list[Any] | None, start: date, end: date) -> list[dict]:
    by_date: dict[str, dict] = {}
    if days:
        for day in days:
            if hasattr(day, "model_dump"):
                item = day.model_dump(mode="json", by_alias=True)
            elif isinstance(day, dict):
                item = dict(day)
                raw_d = item.get("date") or item.get("day_date")
                if isinstance(raw_d, date):
                    item["date"] = raw_d.isoformat()
                elif raw_d is not None:
                    item["date"] = str(raw_d)[:10]
            else:
                continue
            meals = []
            for m in item.get("meals") or []:
                if hasattr(m, "model_dump"):
                    meals.append(m.model_dump(mode="json", by_alias=True))
                else:
                    meals.append(m)
            item["meals"] = meals
            item.setdefault("notes", None)
            by_date[str(item.get("date") or item.get("day_date"))[:10]] = item

    result = []
    for d in _daterange(start, end):
        key = d.isoformat()
        if key in by_date:
            result.append(by_date[key])
        else:
            result.append({"date": key, "notes": None, "meals": []})
    return result


def _attach_meal_images(plan_id: int, days: list[dict]) -> list[dict]:
    plan_data = {"days": []}
    for day in days:
        meals = []
        for m in day.get("meals") or []:
            meals.append(
                {
                    **m,
                    "needs_image": True,
                    "name": m.get("name") or "Meal",
                    "meal_type": m.get("meal_type") or "meal",
                    "calories": m.get("calories"),
                    "protein_g": m.get("protein_g"),
                    "carbs_g": m.get("carbs_g"),
                    "fat_g": m.get("fat_g"),
                }
            )
        plan_data["days"].append({"meals": meals, "snacks": []})

    attach_images_to_nutrition_plan(plan_id, plan_data)
    for day, pd in zip(days, plan_data["days"]):
        for m, pm in zip(day.get("meals") or [], pd.get("meals") or []):
            if pm.get("image_url"):
                m["image_url"] = pm["image_url"]
    return days


def _day_from_plan(plan, on_date: date) -> dict | None:
    key = on_date.isoformat()
    for day in plan.days or []:
        if str(day.get("date", ""))[:10] == key:
            return day
    return None


@router.post(
    "/{email}",
    response_model=schemas.NutritionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_plan(
    email: str,
    body: schemas.NutritionPlanCreate,
    db: Session = Depends(get_db),
):
    """
    Create a nutrition plan for a date range.
    Each day lists meals: what to eat, how to prepare, and how much (portion/macros).
    """
    user = _require_user(db, email)
    _validate_date_range(body.start_date, body.end_date)
    days = _serialize_days(body.days, body.start_date, body.end_date)

    plan = crud.create_nutrition_plan(
        db,
        user.id,
        {
            "title": body.title,
            "goal": body.goal,
            "notes": body.notes,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "daily_calories_target": body.daily_calories_target,
            "days": days,
        },
    )
    days = _attach_meal_images(plan.id, days)
    plan = crud.update_nutrition_plan(db, plan, {"days": days})
    return plan


@router.post(
    "/generate/{email}",
    response_model=schemas.NutritionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_nutrition_plan(
    email: str,
    body: schemas.NutritionPlanGenerateRequest,
    db: Session = Depends(get_db),
):
    """AI-generate a nutrition plan for start_date → end_date (optional helper)."""
    user = _require_user(db, email)
    _validate_date_range(body.start_date, body.end_date)

    try:
        generated = await generate_nutrition_plan_for_range(
            start_date=body.start_date,
            end_date=body.end_date,
            goal=body.goal,
            dietary_preference=body.dietary_preference,
            allergies=body.allergies,
            meals_per_day=body.meals_per_day or 3,
            cuisine=body.cuisine,
            daily_calories_target=body.daily_calories_target,
            notes=body.notes,
        )
    except TarqaAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    title = body.title or generated.get("title") or "Nutrition Plan"
    days = _serialize_days(generated.get("days"), body.start_date, body.end_date)

    plan = crud.create_nutrition_plan(
        db,
        user.id,
        {
            "title": str(title)[:255],
            "goal": body.goal or generated.get("goal"),
            "notes": body.notes or generated.get("notes"),
            "start_date": body.start_date,
            "end_date": body.end_date,
            "daily_calories_target": body.daily_calories_target
            or generated.get("daily_calories_target"),
            "days": days,
        },
    )
    days = _attach_meal_images(plan.id, days)
    plan = crud.update_nutrition_plan(db, plan, {"days": days})
    return plan


@router.get("/{email}", response_model=schemas.NutritionPlanListResponse)
def list_nutrition_plans(email: str, db: Session = Depends(get_db)):
    user = _require_user(db, email)
    plans = crud.list_nutrition_plans(db, user.id)
    return {"plans": plans, "total": len(plans)}


@router.get("/{email}/day/{on_date}", response_model=schemas.NutritionDayScheduleResponse)
def get_nutrition_for_day(
    email: str,
    on_date: date,
    db: Session = Depends(get_db),
):
    """Get meals scheduled for a specific date (from any covering plan)."""
    user = _require_user(db, email)
    plan = crud.get_nutrition_plan_covering_date(db, user.id, on_date)
    if not plan:
        return {
            "date": on_date,
            "plan_id": None,
            "plan_title": None,
            "notes": None,
            "meals": [],
        }
    day = _day_from_plan(plan, on_date) or {
        "date": on_date.isoformat(),
        "notes": None,
        "meals": [],
    }
    return {
        "date": on_date,
        "plan_id": plan.id,
        "plan_title": plan.title,
        "notes": day.get("notes"),
        "meals": day.get("meals") or [],
    }


@router.get("/{email}/{plan_id}", response_model=schemas.NutritionPlanResponse)
def get_nutrition_plan(email: str, plan_id: int, db: Session = Depends(get_db)):
    user = _require_user(db, email)
    plan = crud.get_nutrition_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Nutrition plan {plan_id} not found.")
    return plan


@router.put("/{email}/{plan_id}", response_model=schemas.NutritionPlanResponse)
def update_nutrition_plan(
    email: str,
    plan_id: int,
    body: schemas.NutritionPlanUpdate,
    db: Session = Depends(get_db),
):
    user = _require_user(db, email)
    plan = crud.get_nutrition_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Nutrition plan {plan_id} not found.")

    data = body.model_dump(exclude_unset=True)
    start = data.get("start_date", plan.start_date)
    end = data.get("end_date", plan.end_date)
    _validate_date_range(start, end)

    if "days" in data and data["days"] is not None:
        data["days"] = _serialize_days(body.days, start, end)
        data["days"] = _attach_meal_images(plan.id, data["days"])
    elif "start_date" in data or "end_date" in data:
        data["days"] = _serialize_days(plan.days, start, end)

    plan = crud.update_nutrition_plan(db, plan, data)
    return plan


@router.delete("/{email}/{plan_id}", status_code=status.HTTP_200_OK)
def delete_nutrition_plan(email: str, plan_id: int, db: Session = Depends(get_db)):
    user = _require_user(db, email)
    plan = crud.get_nutrition_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Nutrition plan {plan_id} not found.")
    crud.delete_nutrition_plan(db, plan)
    return {"message": "Nutrition plan deleted", "id": plan_id}
