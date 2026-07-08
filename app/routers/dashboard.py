from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timezone
from typing import List
from app.database import get_db
from app import schemas, crud, models

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


def calculate_wellness_metrics(goals: List[str], recent_health: list, user_weight: float = None):
    # Calculate 7-day average values
    if recent_health:
        num_records = len(recent_health)
        avg_steps = sum(r.steps for r in recent_health) / num_records
        avg_calories = sum(r.calories for r in recent_health) / num_records
        avg_sleep = sum(r.sleep_duration_hours for r in recent_health) / num_records
        avg_water = sum(r.water_intake_ml for r in recent_health) / num_records
        avg_workouts = sum(r.workouts_count for r in recent_health) / num_records
        avg_heart_rate = sum(r.heart_rate_bpm for r in recent_health) / num_records
    else:
        avg_steps, avg_calories, avg_sleep, avg_water = 0.0, 0.0, 0.0, 0.0
        avg_workouts, avg_heart_rate = 0.0, 70.0

    # Goals mapping
    step_goal = 10000.0 if "Stay Active" in goals or "Lose Weight" in goals else 8000.0
    sleep_goal = 8.0 if "Improve Sleep" in goals or "Reduce Stress" in goals else 7.0
    water_goal = 2500.0 if "Eat Healthier" in goals or "Stay Active" in goals else 2000.0
    
    calorie_goal = 500.0
    if user_weight:
        calorie_goal = float(int(user_weight * 6))
        if "Stay Active" in goals:
            calorie_goal += 150.0
            
    exercise_goal = 60.0 # Standard active/exercise minutes goal

    # Subscore calculations
    # 1. Active Subscore (Weight: 35%)
    # Inputs: Steps, Active Calories, and Exercise/Active Minutes (assume 30 mins per workout count)
    active_minutes = avg_workouts * 30.0
    steps_ratio = min(avg_steps / step_goal, 1.2)
    calories_ratio = min(avg_calories / calorie_goal, 1.2)
    exercise_ratio = min(active_minutes / exercise_goal, 1.2)
    active_subscore = int(min((0.50 * steps_ratio + 0.30 * calories_ratio + 0.20 * exercise_ratio) * 100.0, 100.0))

    # 2. Sleep Subscore (Weight: 25%)
    # Inputs: Sleep Hours, and Sleep Quality Estimate Q derived from heart rate
    duration_factor = max(0.0, 1.0 - 0.2 * abs(avg_sleep - sleep_goal))
    sleep_quality_q = max(0.0, min(1.0, 1.0 - abs(avg_heart_rate - 65.0) / 35.0))
    sleep_subscore = int(min((0.7 * duration_factor + 0.3 * sleep_quality_q) * 100.0, 100.0))

    # 3. Nutrition Subscore (Weight: 20%)
    # Inputs: Water Intake, Macro Balance Factor (assume 0.85 baseline if water > 0 else 0.5)
    water_ratio = min(avg_water / water_goal, 1.0)
    macro_balance = 0.85 if avg_water > 0 else 0.5
    nutrition_subscore = int(min((0.60 * water_ratio + 0.40 * macro_balance) * 100.0, 100.0))

    # 4. Mindfulness Subscore (Weight: 20%)
    # Inputs: Mindfulness Minutes (assume min(avg_workouts * 10.0, 15.0)), Resting Heart Rate Stability
    mindfulness_minutes = min(avg_workouts * 10.0, 15.0)
    mindfulness_ratio = min(mindfulness_minutes / 15.0, 1.0)
    hr_stability = max(0.0, min(1.0, 1.0 - abs(avg_heart_rate - 70.0) / 40.0))
    mindfulness_subscore = int(min((0.50 * mindfulness_ratio + 0.50 * hr_stability) * 100.0, 100.0))

    # Overall Wellness Score
    # Formula: min(0.35 * Active + 0.25 * Sleep + 0.20 * Nutri + 0.20 * Mind, 100)
    wellness_score = int(min(
        0.35 * active_subscore + 
        0.25 * sleep_subscore + 
        0.20 * nutrition_subscore + 
        0.20 * mindfulness_subscore, 
        100.0
    ))

    return {
        "wellness_score": wellness_score,
        "active_subscore": active_subscore,
        "sleep_subscore": sleep_subscore,
        "nutrition_subscore": nutrition_subscore,
        "mindfulness_subscore": mindfulness_subscore,
        "goals": {
            "step_goal": step_goal,
            "sleep_goal": sleep_goal,
            "water_goal": water_goal,
            "calorie_goal": calorie_goal,
            "exercise_goal": exercise_goal
        },
        "averages": {
            "steps": avg_steps,
            "calories": avg_calories,
            "sleep": avg_sleep,
            "water": avg_water,
            "workouts": avg_workouts,
            "heart_rate": avg_heart_rate
        }
    }

@router.get("/{email}", response_model=schemas.DashboardResponse)

def get_dashboard_data(email: str, db: Session = Depends(get_db)):
    """
    Retrieves dynamic dashboard details, widgets, wellness score, and customized tips
    for the user based on their profile, goals, and synchronized health data.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    # 1. Calculate Age
    age = None
    if user.profile and user.profile.dob:
        today = date.today()
        dob = user.profile.dob
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # 2. Extract Goals
    goals = [g.goal_name for g in user.goals]

    # 3. Retrieve Last 7 Days of Synced Health Data
    recent_health = crud.get_recent_user_health_data(db, email, limit=7)
    latest_data = recent_health[0] if recent_health else None
    last_synced_date = latest_data.date if latest_data else None

    # Establish baseline values for latest day's widgets
    steps = latest_data.steps if latest_data else 0
    calories = latest_data.calories if latest_data else 0
    sleep = latest_data.sleep_duration_hours if latest_data else 0.0
    water = latest_data.water_intake_ml if latest_data else 0
    workouts = latest_data.workouts_count if latest_data else 0
    heart_rate = latest_data.heart_rate_bpm if latest_data else 72

    user_weight = user.profile.weight if user.profile else None
    metrics = calculate_wellness_metrics(goals, recent_health, user_weight)
    
    wellness_score = metrics["wellness_score"]
    step_target = int(metrics["goals"]["step_goal"])
    sleep_target = metrics["goals"]["sleep_goal"]
    water_target = int(metrics["goals"]["water_goal"])
    calorie_target = int(metrics["goals"]["calorie_goal"])

    # Ensure minimum wellness score if health connect is not active yet
    if not user.health_permission or not user.health_permission.health_connect_connected:
        wellness_score = 65  # Base onboarding wellness score

    # 5. Generate Personalized Recommendations & Challenges
    recommendations = []
    challenges = []
    rewards_points = 50  # Onboarding signup reward points

    if "Lose Weight" in goals:
        recommendations.append("To support weight loss, focus on a high-protein breakfast and log your water intake early.")
        challenges.append("Calorie Burner Challenge (7 days)")
        rewards_points += 20
    if "Stay Active" in goals:
        recommendations.append("Aim for a 10-minute brisk walk every 2 hours to keep your metabolic rate elevated.")
        challenges.append("10K Steps Streak Challenge (5 days)")
        rewards_points += 15
    if "Eat Healthier" in goals:
        recommendations.append("Replace mid-day snacks with a handful of almonds and a fresh fruit to stabilize blood sugar.")
        challenges.append("Greens & Grains Prep (3 days)")
    if "Improve Sleep" in goals or "Reduce Stress" in goals:
        recommendations.append("Establish a screen-free wind-down routine 45 minutes before sleep to boost melatonin.")
        challenges.append("Restful Nights Routine (7 days)")

    # Default recommendation if empty
    if not recommendations:
        recommendations.append("Consistency is key! Start by tracking your steps and drinking 8 glasses of water today.")
    if not challenges:
        challenges.append("Healthy Habits Kickstart (7 days)")

    # 6. Compose Dashboard Widgets
    widgets = [
        schemas.DashboardWidget(
            title="Daily Steps",
            value=str(steps),
            target=str(step_target),
            unit="steps",
            status="Great" if steps >= step_target else "In Progress"
        ),
        schemas.DashboardWidget(
            title="Calories Burned",
            value=str(calories),
            target=str(calorie_target),
            unit="kcal",
            status="Active" if calories >= calorie_target else "Needs Movement"
        ),
        schemas.DashboardWidget(
            title="Sleep Duration",
            value=f"{sleep:.1f}",
            target=f"{sleep_target:.1f}",
            unit="hours",
            status="Optimal" if sleep >= sleep_target - 1 else "Rest Needed"
        ),
        schemas.DashboardWidget(
            title="Water Intake",
            value=str(water),
            target=str(water_target),
            unit="ml",
            status="Hydrated" if water >= water_target else "Dehydrated"
        ),
        schemas.DashboardWidget(
            title="Active Challenges",
            value=f"{len(challenges)} Active",
            target="None",
            unit="challenges",
            status="Ongoing"
        ),
        schemas.DashboardWidget(
            title="Rewards Points",
            value=str(rewards_points),
            target="500",
            unit="pts",
            status="Silver Tier"
        ),
        schemas.DashboardWidget(
            title="Heart Rate",
            value=str(heart_rate),
            target="60-100",
            unit="bpm",
            status="Normal"
        ),
        schemas.DashboardWidget(
            title="AI Wellness Buddy",
            value="Ready",
            target="Chat",
            unit="",
            status="Online"
        )
    ]

    gender_term = "female" if user.profile and user.profile.gender.lower() == "female" else "male"
    age_phrase = f"{age}-year old " if age else ""
    summary_text = (
        f"Hello {user.name}! As a {age_phrase}{gender_term} aiming to "
        f"{', '.join(goals).lower()}, your wellness dashboard is configured. "
        f"Your current daily wellness score is {wellness_score}%."
    )

    # Calculate today's manual water logs sum
    water_intake_today = db.query(func.sum(models.WaterLog.amount)).filter(
        models.WaterLog.user_id == user.id,
        func.date(models.WaterLog.timestamp) == datetime.now(timezone.utc).date()
    ).scalar() or 0

    return schemas.DashboardResponse(
        wellness_score=wellness_score,
        daily_summary=summary_text,
        recommendations=recommendations,
        widgets=widgets,
        water_intake_today=water_intake_today,
        last_synced_date=last_synced_date
    )


@router.post("/sync/{email}", response_model=schemas.DashboardSyncResponse)
def sync_dashboard_data(
    email: str,
    sync_list: List[schemas.DailyHealthData],
    db: Session = Depends(get_db)
):
    """
    Receives daily health metrics for the last 7 days, updates the backend database,
    and returns parsed dashboard wellness score, summary, recommendations, and AI buddy message.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    # 1. Update the backend database with the new health data
    crud.sync_user_health_data(db=db, email=email, sync_list=sync_list)

    # 2. Extract Goals
    goals = [g.goal_name for g in user.goals]

    # 3. Retrieve Last 7 Days of Synced Health Data (including the ones just synced)
    recent_health = crud.get_recent_user_health_data(db, email, limit=7)

    # 4. Compute Targets and Wellness Score based on Goals
    user_weight = user.profile.weight if user.profile else None
    metrics = calculate_wellness_metrics(goals, recent_health, user_weight)
    
    wellness_score = metrics["wellness_score"]
    step_target = int(metrics["goals"]["step_goal"])
    sleep_target = metrics["goals"]["sleep_goal"]
    water_target = int(metrics["goals"]["water_goal"])
    calorie_target = int(metrics["goals"]["calorie_goal"])

    # Ensure minimum wellness score if health connect is not active yet
    if not user.health_permission or not user.health_permission.health_connect_connected:
        wellness_score = 65  # Base onboarding wellness score

    # 5. Generate Personalized Recommendations & Challenges
    recommendations = []

    if "Lose Weight" in goals:
        recommendations.append("To support weight loss, focus on a high-protein breakfast and log your water intake early.")
    if "Stay Active" in goals:
        recommendations.append("Aim for a 10-minute brisk walk every 2 hours to keep your metabolic rate elevated.")
        recommendations.append("Try scheduling a brief 15-minute stretch routine during mid-day break.")
    if "Eat Healthier" in goals:
        recommendations.append("Replace mid-day snacks with a handful of almonds and a fresh fruit to stabilize blood sugar.")
    if "Improve Sleep" in goals or "Reduce Stress" in goals:
        recommendations.append("Establish a screen-free wind-down routine 45 minutes before sleep to boost melatonin.")

    if metrics["averages"]["water"] < water_target:
        recommendations.append("Increase your daily water intake by 500 ml to meet standard hydration guidelines.")

    # Default recommendation if empty
    if not recommendations:
        recommendations.append("Consistency is key! Start by tracking your steps and drinking 8 glasses of water today.")

    # 6. Compose dynamic daily summary and ai buddy message
    daily_summary = f"Incredible progress! You are average {int(metrics['averages']['steps']):,} steps daily and hitting your sleep goals. Keep tracking your hydration to increase your wellness metrics."
    ai_buddy_message = f"Hello Champion! I noticed you average {metrics['averages']['sleep']:.1f} hours of sleep this week, which is excellent. Let's aim to hit {step_target:,} steps today to secure your new streak record!"

    # Calculate today's manual water logs sum
    water_intake_today = db.query(func.sum(models.WaterLog.amount)).filter(
        models.WaterLog.user_id == user.id,
        func.date(models.WaterLog.timestamp) == datetime.now(timezone.utc).date()
    ).scalar() or 0

    return schemas.DashboardSyncResponse(
        wellness_score=wellness_score,
        active_subscore=metrics["active_subscore"],
        sleep_subscore=metrics["sleep_subscore"],
        nutrition_subscore=metrics["nutrition_subscore"],
        mindfulness_subscore=metrics["mindfulness_subscore"],
        daily_summary=daily_summary,
        recommendations=recommendations,
        ai_buddy_message=ai_buddy_message,
        water_intake_today=water_intake_today,
        goals=metrics["goals"]
    )

