from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/sos",
    tags=["SOS & Emergency"]
)


def _require_user(db: Session, email: str):
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found. Please complete onboarding first."
        )
    return user


# ---------------------------------------------------------------------------
# Emergency contacts CRUD  (must be registered before /{email})
# ---------------------------------------------------------------------------

@router.get("/contacts/{email}", response_model=schemas.SOSContactListResponse)
def list_contacts(email: str, db: Session = Depends(get_db)):
    """List all emergency contacts for a user."""
    _require_user(db, email)
    contacts = crud.list_sos_contacts(db, email) or []
    return {"contacts": contacts, "total": len(contacts)}


@router.post(
    "/contacts/{email}",
    response_model=schemas.SOSContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(
    email: str,
    data: schemas.SOSContactCreate,
    db: Session = Depends(get_db),
):
    """Add a new emergency contact for a user."""
    _require_user(db, email)
    contact = crud.create_sos_contact(db, email, data)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create emergency contact.",
        )
    return contact


@router.put("/contacts/{contact_id}", response_model=schemas.SOSContactResponse)
def update_contact(
    contact_id: int,
    data: schemas.SOSContactUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing emergency contact by id."""
    contact = crud.get_sos_contact(db, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with id {contact_id} not found.",
        )
    if data.name is None and data.phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: name, phone.",
        )
    updated = crud.update_sos_contact(db, contact_id, data)
    return updated


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_200_OK)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete an emergency contact by id."""
    contact = crud.get_sos_contact(db, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency contact with id {contact_id} not found.",
        )
    crud.delete_sos_contact(db, contact_id)
    return {"message": "Emergency contact deleted successfully", "id": contact_id}


# ---------------------------------------------------------------------------
# Emergency service numbers CRUD (police / ambulance / fire)
# ---------------------------------------------------------------------------

@router.get("/emergency/{email}", response_model=schemas.SOSEmergencyResponse)
def get_emergency_numbers(email: str, db: Session = Depends(get_db)):
    """Get police, ambulance, and fire emergency numbers for a user."""
    user = _require_user(db, email)
    return crud.get_or_create_sos_config(db, user.id)


@router.put("/emergency/{email}", response_model=schemas.SOSEmergencyResponse)
def update_emergency_numbers(
    email: str,
    data: schemas.SOSEmergencyUpdate,
    db: Session = Depends(get_db),
):
    """
    Create or update police / ambulance / fire numbers.
    Only fields that are sent are updated; others keep their current values.
    """
    _require_user(db, email)
    if data.police_number is None and data.ambulance_number is None and data.fire_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: police_number, ambulance_number, fire_number.",
        )
    config = crud.update_sos_emergency(db, email, data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update emergency numbers.",
        )
    return config


@router.delete("/emergency/{email}", response_model=schemas.SOSEmergencyResponse)
def reset_emergency_numbers(email: str, db: Session = Depends(get_db)):
    """Reset police / ambulance / fire numbers back to defaults (112 / 102 / 101)."""
    _require_user(db, email)
    config = crud.reset_sos_emergency(db, email)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset emergency numbers.",
        )
    return config


# ---------------------------------------------------------------------------
# Trigger SOS alert
# ---------------------------------------------------------------------------

@router.post("/trigger/{email}", response_model=schemas.SOSTriggerResponse)
def trigger_sos(
    email: str,
    trigger_data: schemas.SOSTriggerRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers an emergency SOS alert. Simulates broadcasting messages to all
    registered emergency contacts and returns local emergency numbers.
    """
    user = _require_user(db, email)

    contacts = crud.list_sos_contacts(db, email) or []
    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No emergency contacts configured. Please add at least one contact first.",
        )

    emergency = crud.get_or_create_sos_config(db, user.id)

    location_info = None
    loc_msg = ""
    if trigger_data.latitude is not None and trigger_data.longitude is not None:
        location_info = {
            "latitude": trigger_data.latitude,
            "longitude": trigger_data.longitude,
        }
        loc_msg = f" at location (Lat: {trigger_data.latitude}, Lng: {trigger_data.longitude})"

    print(f"[SOS ALERT] User {user.name} ({user.email}) has triggered an SOS alert{loc_msg}!")
    for contact in contacts:
        print(
            f"[SMS SENT] To {contact.name} ({contact.phone}): "
            f"'EMERGENCY! {user.name} needs help! Current Location: {loc_msg or 'Unknown location'}'"
        )

    emergency_nums = {
        "police": emergency.police_number,
        "ambulance": emergency.ambulance_number,
        "fire": emergency.fire_number,
    }

    return {
        "message": (
            f"SOS emergency alert triggered successfully. "
            f"Notification alerts dispatched to {len(contacts)} emergency contact(s)."
        ),
        "notified_contacts": contacts,
        "emergency_numbers": emergency_nums,
        "location": location_info,
    }


# ---------------------------------------------------------------------------
# Full SOS overview (catch-all path — keep last)
# ---------------------------------------------------------------------------

@router.get("/{email}", response_model=schemas.SOSResponse)
def get_sos(email: str, db: Session = Depends(get_db)):
    """
    Retrieves the full SOS setup for a user: emergency contacts and
    police / ambulance / fire numbers (defaults applied if not customized yet).
    """
    user = _require_user(db, email)
    contacts = crud.list_sos_contacts(db, email) or []
    emergency = crud.get_or_create_sos_config(db, user.id)
    return {
        "user_id": user.id,
        "contacts": contacts,
        "emergency_numbers": emergency,
    }
