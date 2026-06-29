from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/health",
    tags=["Health Sync"]
)

@router.post("/sync/{email}", response_model=schemas.HealthDataResponse)
def sync_health_data(email: str, sync_data: schemas.HealthDataSync, db: Session = Depends(get_db)):
    """
    Syncs health data (steps, calories, sleep duration, water, workouts, heart rate) for a user.
    Requires the user's email.
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

    updated_data = crud.sync_user_health_data(db=db, email=email, sync_data=sync_data)
    return updated_data

@router.get("/data/{email}", response_model=schemas.HealthDataResponse)
def get_health_data(email: str, db: Session = Depends(get_db)):
    """
    Fetches the synced health data details for a user.
    """
    health_data = crud.get_user_health_data(db=db, email=email)
    if not health_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health data found for user '{email}'."
        )
    return health_data
