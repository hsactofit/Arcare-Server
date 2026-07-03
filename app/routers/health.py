from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud

from typing import List

router = APIRouter(
    prefix="/health",
    tags=["Health Sync"]
)

@router.post("/sync/{email}", response_model=List[schemas.DailyHealthDataResponse])
def sync_health_data(email: str, sync_list: List[schemas.DailyHealthData], db: Session = Depends(get_db)):
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
def get_health_data(email: str, db: Session = Depends(get_db)):
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

