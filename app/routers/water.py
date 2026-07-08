from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import schemas, crud, models
from typing import List

from datetime import date, datetime, timedelta, timezone

router = APIRouter(
    prefix="/water",
    tags=["Hydration"]
)

@router.get("/logs/{email}", response_model=schemas.HydrationHistoryResponse)
def get_water_logs(email: str, db: Session = Depends(get_db)):
    """
    Fetches the hydration history (last 7 logs) for a user along with today's total intake.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    logs = crud.get_user_water_logs(db=db, email=email, limit=7)
    
    # Calculate today's manual water logs sum
    water_intake_today = db.query(func.sum(models.WaterLog.amount)).filter(
        models.WaterLog.user_id == user.id,
        func.date(models.WaterLog.timestamp) == datetime.now(timezone.utc).date()
    ).scalar() or 0


    return {
        "water_intake_today": water_intake_today,
        "logs": logs
    }

@router.post("/log/{email}", response_model=schemas.WaterLogSubmitResponse, status_code=status.HTTP_200_OK)
def add_water_log(email: str, log_data: schemas.WaterLogCreate, db: Session = Depends(get_db)):
    """
    Logs water intake (amount in ml and optional timestamp) for a user.
    """
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )

    log = crud.create_water_log(db=db, email=email, log_data=log_data)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create water log."
        )
    return {
        "id": log.id,
        "message": "Water intake logged successfully",
        "amount": log.amount,
        "timestamp": log.timestamp
    }

@router.get("/graph/{email}", response_model=schemas.WaterGraphResponse)
def get_water_graph(email: str, period: str = "week", db: Session = Depends(get_db)):
    """
    Retrieves water intake graph data for a user based on the period: 'day', 'week', or 'month'.
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
        logs = db.query(models.WaterLog).filter(
            models.WaterLog.user_id == user.id,
            models.WaterLog.timestamp >= today_start
        ).all()
        
        # Initialize 24 hours
        hourly_data = {f"{h:02d}:00": 0 for h in range(24)}
        for log in logs:
            hour_str = log.timestamp.strftime("%H:00")
            if hour_str in hourly_data:
                hourly_data[hour_str] += log.amount
                
        data_points = [schemas.WaterGraphDataPoint(label=k, amount=v) for k, v in hourly_data.items()]
        
    elif period == "week":
        # Last 7 days
        start_date = today - timedelta(days=6)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        logs = db.query(models.WaterLog).filter(
            models.WaterLog.user_id == user.id,
            models.WaterLog.timestamp >= start_datetime
        ).all()
        
        # Initialize last 7 days
        daily_data = {}
        for i in range(7):
            d = start_date + timedelta(days=i)
            daily_data[d.strftime("%Y-%m-%d")] = 0
            
        for log in logs:
            date_str = log.timestamp.strftime("%Y-%m-%d")
            if date_str in daily_data:
                daily_data[date_str] += log.amount
                
        data_points = [schemas.WaterGraphDataPoint(label=k, amount=v) for k, v in daily_data.items()]
        
    elif period == "month":
        # Last 30 days
        start_date = today - timedelta(days=29)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        logs = db.query(models.WaterLog).filter(
            models.WaterLog.user_id == user.id,
            models.WaterLog.timestamp >= start_datetime
        ).all()
        
        # Initialize last 30 days
        daily_data = {}
        for i in range(30):
            d = start_date + timedelta(days=i)
            daily_data[d.strftime("%Y-%m-%d")] = 0
            
        for log in logs:
            date_str = log.timestamp.strftime("%Y-%m-%d")
            if date_str in daily_data:
                daily_data[date_str] += log.amount
                
        data_points = [schemas.WaterGraphDataPoint(label=k, amount=v) for k, v in daily_data.items()]
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Choose from 'day', 'week', or 'month'."
        )
        
    return schemas.WaterGraphResponse(period=period, data=data_points)

@router.put("/log/{log_id}", response_model=schemas.WaterLogSubmitResponse)
def update_log(log_id: int, log_data: schemas.WaterLogCreate, db: Session = Depends(get_db)):
    """
    Updates a specific water log's amount and/or timestamp.
    """
    db_log = crud.get_water_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Water log with ID {log_id} not found."
        )
    log = crud.update_water_log(db=db, db_log=db_log, log_data=log_data)
    return {
        "id": log.id,
        "message": "Water intake logged successfully",
        "amount": log.amount,
        "timestamp": log.timestamp
    }

@router.delete("/log/{log_id}", response_model=schemas.MessageResponse)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """
    Deletes a specific water log.
    """
    db_log = crud.get_water_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Water log with ID {log_id} not found."
        )
    crud.delete_water_log(db=db, db_log=db_log)
    return {"message": "Water log deleted successfully"}

