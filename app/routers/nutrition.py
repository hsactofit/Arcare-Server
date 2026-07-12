from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import schemas, crud, models
from typing import List

from datetime import date, datetime, timedelta, timezone

router = APIRouter(
    prefix="/nutrition",
    tags=["Nutrition"]
)

@router.get("/logs/{email}", response_model=schemas.NutritionHistoryResponse)
def get_nutrition_logs(email: str, db: Session = Depends(get_db)):
    """
    Fetches the nutrition history (last 7 logs) for a user along with today's total intake of calories and macros.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    logs = crud.get_user_nutrition_logs(db=db, email=email, limit=7)
    
    # Calculate today's nutrition totals
    today = datetime.now(timezone.utc).date()
    totals = db.query(
        func.sum(models.NutritionLog.calories).label("calories"),
        func.sum(models.NutritionLog.protein).label("protein"),
        func.sum(models.NutritionLog.fat).label("fat"),
        func.sum(models.NutritionLog.carbs).label("carbs")
    ).filter(
        models.NutritionLog.user_id == user.id,
        func.date(models.NutritionLog.timestamp) == today
    ).first()

    calories_today = float(totals.calories or 0)
    protein_today = float(totals.protein or 0)
    fat_today = float(totals.fat or 0)
    carbs_today = float(totals.carbs or 0)

    return {
        "calories_today": calories_today,
        "protein_today": protein_today,
        "fat_today": fat_today,
        "carbs_today": carbs_today,
        "logs": logs
    }

@router.post("/log/{email}", response_model=schemas.NutritionLogSubmitResponse, status_code=status.HTTP_200_OK)
def add_nutrition_log(email: str, log_data: schemas.NutritionLogCreate, db: Session = Depends(get_db)):
    """
    Logs nutrition intake (food name, calories, macros, and optional timestamp) for a user.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    log = crud.create_nutrition_log(db=db, email=email, log_data=log_data)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create nutrition log."
        )
        
    from app.routers.challenges import sync_user_challenges_progress
    sync_user_challenges_progress(db, user.id)
    
    return {
        "id": log.id,
        "message": "Nutrition intake logged successfully",
        "food_name": log.food_name,
        "calories": log.calories,
        "protein": log.protein,
        "fat": log.fat,
        "carbs": log.carbs,
        "timestamp": log.timestamp
    }

@router.get("/graph/{email}", response_model=schemas.NutritionGraphResponse)
def get_nutrition_graph(email: str, period: str = "week", db: Session = Depends(get_db)):
    """
    Retrieves nutrition intake graph data for a user based on the period: 'day', 'week', or 'month'.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )
        
    period = period.lower()
    today = date.today()
    
    if period == "day":
        # Get all logs for today
        today_start = datetime.combine(today, datetime.min.time())
        logs = db.query(models.NutritionLog).filter(
            models.NutritionLog.user_id == user.id,
            models.NutritionLog.timestamp >= today_start
        ).all()
        
        # Initialize 24 hours
        hourly_data = {f"{h:02d}:00": {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0} for h in range(24)}
        for log in logs:
            hour_str = log.timestamp.strftime("%H:00")
            if hour_str in hourly_data:
                hourly_data[hour_str]["calories"] += log.calories
                hourly_data[hour_str]["protein"] += log.protein
                hourly_data[hour_str]["fat"] += log.fat
                hourly_data[hour_str]["carbs"] += log.carbs
                
        data_points = [
            schemas.NutritionGraphDataPoint(
                label=k,
                calories=v["calories"],
                protein=v["protein"],
                fat=v["fat"],
                carbs=v["carbs"]
            ) for k, v in hourly_data.items()
        ]
        
    elif period == "week":
        # Last 7 days
        start_date = today - timedelta(days=6)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        logs = db.query(models.NutritionLog).filter(
            models.NutritionLog.user_id == user.id,
            models.NutritionLog.timestamp >= start_datetime
        ).all()
        
        # Initialize last 7 days
        daily_data = {}
        for i in range(7):
            d = start_date + timedelta(days=i)
            daily_data[d.strftime("%Y-%m-%d")] = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
            
        for log in logs:
            date_str = log.timestamp.strftime("%Y-%m-%d")
            if date_str in daily_data:
                daily_data[date_str]["calories"] += log.calories
                daily_data[date_str]["protein"] += log.protein
                daily_data[date_str]["fat"] += log.fat
                daily_data[date_str]["carbs"] += log.carbs
                
        data_points = [
            schemas.NutritionGraphDataPoint(
                label=k,
                calories=v["calories"],
                protein=v["protein"],
                fat=v["fat"],
                carbs=v["carbs"]
            ) for k, v in daily_data.items()
        ]
        
    elif period == "month":
        # Last 30 days
        start_date = today - timedelta(days=29)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        logs = db.query(models.NutritionLog).filter(
            models.NutritionLog.user_id == user.id,
            models.NutritionLog.timestamp >= start_datetime
        ).all()
        
        # Initialize last 30 days
        daily_data = {}
        for i in range(30):
            d = start_date + timedelta(days=i)
            daily_data[d.strftime("%Y-%m-%d")] = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
            
        for log in logs:
            date_str = log.timestamp.strftime("%Y-%m-%d")
            if date_str in daily_data:
                daily_data[date_str]["calories"] += log.calories
                daily_data[date_str]["protein"] += log.protein
                daily_data[date_str]["fat"] += log.fat
                daily_data[date_str]["carbs"] += log.carbs
                
        data_points = [
            schemas.NutritionGraphDataPoint(
                label=k,
                calories=v["calories"],
                protein=v["protein"],
                fat=v["fat"],
                carbs=v["carbs"]
            ) for k, v in daily_data.items()
        ]
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Choose from 'day', 'week', or 'month'."
        )
        
    return schemas.NutritionGraphResponse(period=period, data=data_points)

@router.put("/log/{log_id}", response_model=schemas.NutritionLogSubmitResponse)
def update_log(log_id: int, log_data: schemas.NutritionLogCreate, db: Session = Depends(get_db)):
    """
    Updates a specific nutrition log's fields and/or timestamp.
    """
    db_log = crud.get_nutrition_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nutrition log with ID {log_id} not found."
        )
    log = crud.update_nutrition_log(db=db, db_log=db_log, log_data=log_data)
    
    from app.routers.challenges import sync_user_challenges_progress
    sync_user_challenges_progress(db, db_log.user_id)
    
    return {
        "id": log.id,
        "message": "Nutrition intake logged successfully",
        "food_name": log.food_name,
        "calories": log.calories,
        "protein": log.protein,
        "fat": log.fat,
        "carbs": log.carbs,
        "timestamp": log.timestamp
    }

@router.delete("/log/{log_id}", response_model=schemas.MessageResponse)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """
    Deletes a specific nutrition log.
    """
    db_log = crud.get_nutrition_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nutrition log with ID {log_id} not found."
        )
    crud.delete_nutrition_log(db=db, db_log=db_log)
    
    from app.routers.challenges import sync_user_challenges_progress
    sync_user_challenges_progress(db, db_log.user_id)
    
    return {"message": "Nutrition log deleted successfully"}
