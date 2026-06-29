from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"]
)

@router.post("", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
def submit_onboarding(data: schemas.OnboardingSubmission, db: Session = Depends(get_db)):
    """
    Submits user onboarding flow details.
    If the user already exists, it updates their onboarding data.
    """
    try:
        crud.save_user_onboarding(db=db, data=data)
        return {"message": "Onboarding completed and saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while saving onboarding details: {str(e)}"
        )

@router.get("/{email}", response_model=schemas.OnboardingSubmission)
def get_onboarding_details(email: str, db: Session = Depends(get_db)):
    """
    Fetches full onboarding details for a user by email.
    """
    onboarding_data = crud.get_full_onboarding_data(db=db, email=email)
    if not onboarding_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' has not started or completed onboarding."
        )
    return onboarding_data

@router.get("/status/{email}")
def check_onboarding_status(email: str, db: Session = Depends(get_db)):
    """
    Checks if onboarding has been completed for a given user email.
    """
    user = crud.get_user_by_email(db=db, email=email)
    if not user:
        return {"onboarding_completed": False, "exists": False}
    return {
        "onboarding_completed": user.onboarding_completed,
        "completed_at": user.completed_at,
        "exists": True
    }
