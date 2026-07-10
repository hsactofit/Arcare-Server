from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud, models
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta

router = APIRouter(
    prefix="/health",
    tags=["Health Sync"]
)

@router.post("/sync/{email}", response_model=List[schemas.DailyHealthDataResponse])
def sync_health_data(
    email: str = Path(..., description="The registered user's email address"),
    sync_list: List[schemas.DailyHealthData] = Body(..., description="List of daily health logs (up to 7 days)"),
    db: Session = Depends(get_db)
):
    """
    Syncs daily health data (steps, calories, sleep duration, water, workouts, heart rate) for a user.
    Supports a list containing up to the last 7 days of historical logs.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    if not user.health_permission or not user.health_permission.health_connect_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Health Connect/Apple Health permission is not enabled for this user."
        )

    updated_data = crud.sync_user_health_data(db=db, email=email, sync_list=sync_list)
    return updated_data

@router.get("/data/{email}", response_model=List[schemas.DailyHealthDataResponse])
def get_health_data(
    email: str = Path(..., description="The registered user's email address"),
    db: Session = Depends(get_db)
):
    """
    Fetches the synced health data history (last 7 entries) for a user.
    """
    health_data = crud.get_recent_user_health_data(db=db, email=email, limit=7)
    if not health_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health data found for user '{email}'."
        )
    return health_data


def generate_metric_feedback(metric: str, average: float, total: Optional[float], period: str) -> str:
    metric_clean = metric.lower()
    
    if "steps" in metric_clean:
        if average >= 10000:
            return f"Outstanding! You average {average:.0f} steps, maintaining a highly active lifestyle. Meeting this level consistently is excellent for cardiovascular health, weight management, and metabolic rate."
        elif average >= 7000:
            return f"Good progress! Your average is {average:.0f} steps. You are moderately active. Try to squeeze in a 10-15 minute walk after meals to hit the 10,000 steps goal!"
        else:
            return f"Your average steps ({average:.0f}) are currently below the recommended 7,000-10,000 steps. Regular walking boosts circulation, mood, and energy. Try taking short walks throughout your day."
            
    elif "calories" in metric_clean:
        if average >= 500:
            return f"Excellent energy expenditure! You average {average:.0f} kcal of active calorie burn. This supports cardiac conditioning and physical fitness."
        elif average >= 300:
            return f"Healthy calorie burn. Your average is {average:.0f} kcal. Consistently active days help maintain energy balance and core stability."
        else:
            return f"Your active calorie burn averages {average:.0f} kcal. Consider introducing more movement, such as walking, cycling, or light workouts, to increase your daily activity levels."
            
    elif "sleep" in metric_clean:
        if average >= 7.0 and average <= 9.0:
            return f"Fantastic sleep health! Your average sleep is {average:.1f} hours, which falls right in the optimal window for deep tissue recovery, hormonal balance, and cognitive function."
        elif average < 7.0:
            return f"Your sleep average is {average:.1f} hours. This is slightly below the recommended 7-9 hours. Getting sufficient rest is critical for muscle recovery, cognitive focus, and immune response."
        else:
            return f"You average {average:.1f} hours of sleep. While sleep needs vary, consistently sleeping more than 9 hours can sometimes be a sign of low-quality sleep or fatigue. Monitor how rested you feel."
            
    elif "water" in metric_clean:
        if average >= 2000:
            return f"Great hydration! Averaging {average:.0f} ml of water daily keeps your energy high, flushes toxins, and keeps your muscles hydrated. Keep it up!"
        else:
            return f"Your average daily hydration is {average:.0f} ml, which is below the recommended 2,000-2,500 ml. Proper hydration is vital for digestion, joint health, and cognitive performance."
            
    elif "workout" in metric_clean:
        if period == "days":
            text_period = "the past 7 days"
            target_work = 3
        elif period == "weeks":
            text_period = "the past 4 weeks"
            target_work = 12
        else:
            text_period = "the past 3 months"
            target_work = 36
            
        tot = total if total is not None else 0
        if tot >= target_work:
            return f"Amazing consistency! You've logged {tot:.0f} workouts over {text_period}. This dedication builds strong muscles, increases cardiovascular endurance, and enhances metabolism."
        elif tot > 0:
            return f"Good effort! You've completed {tot:.0f} workouts. Aiming for at least 3 workouts a week can help you progress further toward your fitness goals."
        else:
            return "No workouts recorded in this period yet. Try incorporating 20-30 minutes of strength or aerobic training twice a week to start building a regular habit."
            
    elif "heart" in metric_clean:
        if average >= 60 and average <= 80:
            return f"Your average resting heart rate is {average:.0f} bpm, which is in the healthy and efficient range for adults, showing good cardiovascular health."
        elif average > 80:
            return f"Your average resting heart rate is {average:.0f} bpm. An elevated heart rate can be linked to stress, lack of sleep, or dehydration. Focus on recovery and stress management."
        else:
            return f"Your average heart rate is {average:.0f} bpm. While typical for well-conditioned athletes, make sure you don't experience symptoms like dizziness or fatigue."
            
    return "Keep tracking your health metrics to receive personalized feedback and insights!"


@router.post("/metric/{email}", response_model=schemas.MetricLogResponse)
def log_metric(
    email: str = Path(..., description="The registered user's email address"),
    req: schemas.MetricLogRequest = Body(..., description="The health metric log payload"),
    db: Session = Depends(get_db)
):
    """
    Log or update a single health metric for a user.
    If the metric is steps, it also calculates and updates calories burned.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    # Validate metric
    metric_clean = req.metric.lower()
    metric_map = {
        "steps": "steps",
        "calories": "calories",
        "sleep": "sleep_duration_hours",
        "sleep_duration_hours": "sleep_duration_hours",
        "water": "water_intake_ml",
        "water_intake_ml": "water_intake_ml",
        "workouts": "workouts_count",
        "workouts_count": "workouts_count",
        "heart_rate": "heart_rate_bpm",
        "heart_rate_bpm": "heart_rate_bpm",
    }
    
    if metric_clean not in metric_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric '{req.metric}'. Valid choices: {list(metric_map.keys())}"
        )
        
    col_name = metric_map[metric_clean]
    log_date = req.date or date.today()
    
    # Get or create HealthData for this date
    db_health = db.query(models.HealthData).filter(
        models.HealthData.user_id == user.id,
        models.HealthData.date == log_date
    ).first()
    
    if not db_health:
        db_health = models.HealthData(
            user_id=user.id,
            date=log_date
        )
        db.add(db_health)
        
    # Set the value (ensure correct type)
    if col_name in ["steps", "calories", "water_intake_ml", "workouts_count", "heart_rate_bpm"]:
        setattr(db_health, col_name, int(req.value))
    else:
        setattr(db_health, col_name, float(req.value))
    
    # Calculate calories burned if steps
    calories_burned = None
    if col_name == "steps":
        weight = 70.0
        if user.profile and user.profile.weight:
            weight = user.profile.weight
        calories_burned = int(round(req.value * 0.0006125 * weight))
        db_health.calories = calories_burned
        
    db_health.updated_at = datetime.now(timezone.utc)
    crud.cleanup_old_user_data(db, user.id)
    db.commit()
    db.refresh(db_health)
    
    return schemas.MetricLogResponse(
        message=f"Successfully logged {req.metric} value of {req.value}",
        metric=req.metric,
        value=req.value,
        date=log_date,
        calories_burned=calories_burned,
        health_data=db_health
    )


@router.get("/graph/{email}", response_model=schemas.MetricGraphResponse)
def get_metric_graph(
    email: str = Path(..., description="The registered user's email address"),
    metric: str = Query(..., description="Health metric type: 'steps', 'calories', 'sleep', 'water', 'workouts', or 'heart_rate'"),
    period: str = Query("days", description="Aggregation period: 'days' (last 7 days daily), 'weeks' (last 4 weeks weekly), or 'month' (last 3 months monthly)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves health metric graph data for a user based on the period: 'days', 'weeks', or 'month'.
    Includes aggregated data, averages, totals, and personalized health feedback.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )
        
    weight = 70.0
    if user.profile and user.profile.weight:
        weight = user.profile.weight

    metric_clean = metric.lower()
    metric_map = {
        "steps": "steps",
        "calories": "calories",
        "sleep": "sleep_duration_hours",
        "sleep_duration_hours": "sleep_duration_hours",
        "water": "water_intake_ml",
        "water_intake_ml": "water_intake_ml",
        "workouts": "workouts_count",
        "workouts_count": "workouts_count",
        "heart_rate": "heart_rate_bpm",
        "heart_rate_bpm": "heart_rate_bpm",
    }
    
    if metric_clean not in metric_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric '{metric}'. Valid choices: {list(metric_map.keys())}"
        )
        
    col_name = metric_map[metric_clean]
    period_clean = period.lower()
    if period_clean in ["days", "day", "7_days"]:
        period_clean = "days"
    elif period_clean in ["weeks", "week", "4_weeks"]:
        period_clean = "weeks"
    elif period_clean in ["month", "months", "3_months"]:
        period_clean = "month"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Choose from 'days', 'weeks', or 'month'."
        )
        
    today = date.today()
    
    # Define time frame for efficiency
    if period_clean == "days":
        start_date = today - timedelta(days=6)
    elif period_clean == "weeks":
        start_date = today - timedelta(days=27)
    else:
        # First day of the month 2 months ago (total 3 months: current, current-1, current-2)
        current_year = today.year
        current_month = today.month
        target_month = current_month - 2
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        start_date = date(target_year, target_month, 1)
        
    health_logs = db.query(models.HealthData).filter(
        models.HealthData.user_id == user.id,
        models.HealthData.date >= start_date
    ).all()
    
    default_val = 70.0 if "heart_rate" in metric_clean else 0.0
    
    if period_clean == "days":
        # Last 7 days, daily data points
        data_dict = {(today - timedelta(days=i)).strftime("%Y-%m-%d"): default_val for i in range(7)}
        for r in health_logs:
            date_str = r.date.strftime("%Y-%m-%d")
            if date_str in data_dict:
                val = getattr(r, col_name)
                if val is not None:
                    data_dict[date_str] = float(val)
        
        sorted_data = sorted(data_dict.items())
        data_points = [schemas.MetricGraphDataPoint(label=k, value=v) for k, v in sorted_data]
        
    elif period_clean == "weeks":
        # Last 4 weeks (28 days), weekly aggregated data points
        # Each week is a 7-day block.
        week_ranges = []
        for i in range(4):
            w_start = start_date + timedelta(days=i*7)
            w_end = w_start + timedelta(days=6)
            label = w_start.strftime("%Y-%m-%d")
            week_ranges.append((w_start, w_end, label))
            
        data_dict = {label: [] for _, _, label in week_ranges}
        for r in health_logs:
            for w_start, w_end, label in week_ranges:
                if w_start <= r.date <= w_end:
                    val = getattr(r, col_name)
                    if val is not None:
                        data_dict[label].append(float(val))
                    break
                    
        data_points = []
        for _, _, label in week_ranges:
            vals = data_dict[label]
            if not vals:
                val = default_val
            else:
                if metric_clean in ["sleep", "sleep_duration_hours", "heart_rate", "heart_rate_bpm"]:
                    val = sum(vals) / len(vals)
                else:
                    val = sum(vals)
            data_points.append(schemas.MetricGraphDataPoint(label=label, value=round(val, 1)))
            
    elif period_clean == "month":
        # Last 3 months, monthly aggregated data points
        monthly_labels = []
        current_year = today.year
        current_month = today.month
        for i in range(3):
            m = current_month - i
            y = current_year
            while m <= 0:
                m += 12
                y -= 1
            monthly_labels.append(f"{y}-{m:02d}")
        monthly_labels.reverse()
        
        data_dict = {label: [] for label in monthly_labels}
        for r in health_logs:
            label = r.date.strftime("%Y-%m")
            if label in data_dict:
                val = getattr(r, col_name)
                if val is not None:
                    data_dict[label].append(float(val))
                    
        data_points = []
        for label in monthly_labels:
            vals = data_dict[label]
            if not vals:
                val = default_val
            else:
                if metric_clean in ["sleep", "sleep_duration_hours", "heart_rate", "heart_rate_bpm"]:
                    val = sum(vals) / len(vals)
                else:
                    val = sum(vals)
            data_points.append(schemas.MetricGraphDataPoint(label=label, value=round(val, 1)))
            

            
    # Calculate average and total
    average = sum(dp.value for dp in data_points) / len(data_points) if data_points else 0.0
    
    total = None
    if metric_clean not in ["heart_rate", "heart_rate_bpm"]:
        total = sum(dp.value for dp in data_points)
        
    feedback = generate_metric_feedback(metric_clean, average, total, period_clean)
    
    calories_total = None
    calories_average = None
    if metric_clean == "steps":
        calories_average = round(average * 0.0006125 * weight, 1)
        if total is not None:
            calories_total = round(total * 0.0006125 * weight, 1)
    
    return schemas.MetricGraphResponse(
        metric=metric,
        period=period_clean,
        data=data_points,
        feedback=feedback,
        average=round(average, 1),
        total=round(total, 1) if total is not None else None,
        calories_total=calories_total,
        calories_average=calories_average
    )

