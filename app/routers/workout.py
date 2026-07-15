"""Workout plans by date range: which exercises, how to do them, how much."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud
from app.config import get_now_naive
from app.services.tarqaai import generate_workout_plan_for_range, TarqaAIError
from app.services.workout_images import attach_images_to_plan

router = APIRouter(
    prefix="/workout",
    tags=["Workout Plans"],
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


def _empty_days(start: date, end: date) -> list[dict]:
    return [
        {
            "date": d.isoformat(),
            "focus": None,
            "is_rest_day": False,
            "notes": None,
            "exercises": [],
        }
        for d in _daterange(start, end)
    ]


def _serialize_days(days: list[Any] | None, start: date, end: date) -> list[dict]:
    """Normalize day payloads; fill missing dates in range with empty shells."""
    by_date: dict[str, dict] = {}
    if days:
        for day in days:
            if hasattr(day, "model_dump"):
                item = day.model_dump(mode="json", by_alias=True)
            elif isinstance(day, dict):
                item = dict(day)
                # accept either "date" or "day_date"
                raw_d = item.get("date") or item.get("day_date")
                if isinstance(raw_d, date):
                    item["date"] = raw_d.isoformat()
                elif raw_d is not None:
                    item["date"] = str(raw_d)[:10]
            else:
                continue
            # normalize exercises
            exercises = []
            for ex in item.get("exercises") or []:
                if hasattr(ex, "model_dump"):
                    exercises.append(ex.model_dump(mode="json", by_alias=True))
                else:
                    exercises.append(ex)
            item["exercises"] = exercises
            item.setdefault("is_rest_day", False)
            item.setdefault("focus", None)
            item.setdefault("notes", None)
            by_date[str(item.get("date") or item.get("day_date"))[:10]] = item

    result = []
    for d in _daterange(start, end):
        key = d.isoformat()
        if key in by_date:
            result.append(by_date[key])
        else:
            result.append(
                {
                    "date": key,
                    "focus": None,
                    "is_rest_day": False,
                    "notes": None,
                    "exercises": [],
                }
            )
    return result


def _attach_workout_images(plan_id: int, days: list[dict]) -> list[dict]:
    """Reuse image helper shaped as plan_data.days[].exercises."""
    plan_data = {"days": []}
    for day in days:
        plan_data["days"].append(
            {
                "exercises": [
                    {
                        **ex,
                        "needs_image": True,
                        "name": ex.get("name") or "Exercise",
                        "muscle_groups": ex.get("muscle_groups") or [],
                        "sets": ex.get("sets"),
                        "reps": ex.get("reps"),
                        "equipment": ex.get("equipment"),
                    }
                    for ex in (day.get("exercises") or [])
                    if not day.get("is_rest_day")
                ]
            }
        )
    attach_images_to_plan(plan_id, plan_data)
    # copy image_url back
    for day, pd in zip(days, plan_data["days"]):
        if day.get("is_rest_day"):
            continue
        for ex, pex in zip(day.get("exercises") or [], pd.get("exercises") or []):
            if pex.get("image_url"):
                ex["image_url"] = pex["image_url"]
    return days


def _day_from_plan(plan, on_date: date) -> dict | None:
    key = on_date.isoformat()
    for day in plan.days or []:
        if str(day.get("date", ""))[:10] == key:
            return day
    return None


@router.post(
    "/{email}",
    response_model=schemas.WorkoutPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_plan(
    email: str,
    body: schemas.WorkoutPlanCreate,
    db: Session = Depends(get_db),
):
    """
    Create a workout plan for a date range.
    Each day lists exercises: which one, how to do it, and how much (sets/reps/duration).
    """
    user = _require_user(db, email)
    _validate_date_range(body.start_date, body.end_date)
    days = _serialize_days(body.days, body.start_date, body.end_date)

    plan = crud.create_workout_plan(
        db,
        user.id,
        {
            "title": body.title,
            "goal": body.goal,
            "notes": body.notes,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "days": days,
        },
    )
    days = _attach_workout_images(plan.id, days)
    plan = crud.update_workout_plan(db, plan, {"days": days})
    return plan


@router.post(
    "/generate/{email}",
    response_model=schemas.WorkoutPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_workout_plan(
    email: str,
    body: schemas.WorkoutPlanGenerateRequest,
    db: Session = Depends(get_db),
):
    """AI-generate a workout plan for start_date → end_date (optional helper)."""
    user = _require_user(db, email)
    _validate_date_range(body.start_date, body.end_date)

    try:
        generated = await generate_workout_plan_for_range(
            start_date=body.start_date,
            end_date=body.end_date,
            goal=body.goal,
            experience_level=body.experience_level,
            location=body.location,
            equipment=body.equipment,
            focus_areas=body.focus_areas,
            session_duration_minutes=body.session_duration_minutes,
            notes=body.notes,
        )
    except TarqaAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    title = body.title or generated.get("title") or "Workout Plan"
    days = _serialize_days(generated.get("days"), body.start_date, body.end_date)

    plan = crud.create_workout_plan(
        db,
        user.id,
        {
            "title": str(title)[:255],
            "goal": body.goal or generated.get("goal"),
            "notes": body.notes or generated.get("notes"),
            "start_date": body.start_date,
            "end_date": body.end_date,
            "days": days,
        },
    )
    days = _attach_workout_images(plan.id, days)
    plan = crud.update_workout_plan(db, plan, {"days": days})
    return plan


@router.get("/{email}", response_model=schemas.WorkoutPlanListResponse)
def list_workout_plans(email: str, db: Session = Depends(get_db)):
    """List all workout plans for a user (newest start_date first)."""
    user = _require_user(db, email)
    plans = crud.list_workout_plans(db, user.id)
    return {"plans": plans, "total": len(plans)}


@router.get("/{email}/day/{on_date}", response_model=schemas.WorkoutDayScheduleResponse)
def get_workout_for_day(
    email: str,
    on_date: date,
    db: Session = Depends(get_db),
):
    """Get exercises scheduled for a specific date (from any covering plan)."""
    user = _require_user(db, email)
    plan = crud.get_workout_plan_covering_date(db, user.id, on_date)
    if not plan:
        return {
            "date": on_date,
            "plan_id": None,
            "plan_title": None,
            "focus": None,
            "is_rest_day": False,
            "notes": None,
            "exercises": [],
        }
    day = _day_from_plan(plan, on_date) or {
        "date": on_date.isoformat(),
        "focus": None,
        "is_rest_day": False,
        "notes": None,
        "exercises": [],
    }
    return {
        "date": on_date,
        "plan_id": plan.id,
        "plan_title": plan.title,
        "focus": day.get("focus"),
        "is_rest_day": bool(day.get("is_rest_day")),
        "notes": day.get("notes"),
        "exercises": day.get("exercises") or [],
    }


@router.get("/{email}/{plan_id}", response_model=schemas.WorkoutPlanResponse)
def get_workout_plan(email: str, plan_id: int, db: Session = Depends(get_db)):
    user = _require_user(db, email)
    plan = crud.get_workout_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Workout plan {plan_id} not found.")
    return plan


@router.put("/{email}/{plan_id}", response_model=schemas.WorkoutPlanResponse)
def update_workout_plan(
    email: str,
    plan_id: int,
    body: schemas.WorkoutPlanUpdate,
    db: Session = Depends(get_db),
):
    """Update title, dates, notes, or the full day/exercise schedule."""
    user = _require_user(db, email)
    plan = crud.get_workout_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Workout plan {plan_id} not found.")

    data = body.model_dump(exclude_unset=True)
    start = data.get("start_date", plan.start_date)
    end = data.get("end_date", plan.end_date)
    _validate_date_range(start, end)

    if "days" in data and data["days"] is not None:
        data["days"] = _serialize_days(body.days, start, end)
        data["days"] = _attach_workout_images(plan.id, data["days"])
    elif "start_date" in data or "end_date" in data:
        # re-align existing days to new range
        data["days"] = _serialize_days(plan.days, start, end)

    plan = crud.update_workout_plan(db, plan, data)
    return plan


@router.delete("/{email}/{plan_id}", status_code=status.HTTP_200_OK)
def delete_workout_plan(email: str, plan_id: int, db: Session = Depends(get_db)):
    user = _require_user(db, email)
    plan = crud.get_workout_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Workout plan {plan_id} not found.")
    crud.delete_workout_plan(db, plan)
    return {"message": "Workout plan deleted", "id": plan_id}
