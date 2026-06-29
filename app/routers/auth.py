from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, crud, models
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_google_token,
    verify_apple_token
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/signup", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(data: schemas.UserSignUp, db: Session = Depends(get_db)):
    """
    Registers a new email/password user, hashes their password,
    and returns JWT access/refresh tokens alongside basic user profile data.
    """
    db_user = crud.get_user_by_email(db, data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )
    
    # Create the user
    user = crud.create_email_user(db=db, signup_data=data)
    
    # Generate tokens
    token_payload = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
    
    user_details = crud.get_user_auth_details(user)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_details
    }

@router.post("/login", response_model=schemas.AuthResponse)
def login(data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates a user via email and password,
    returning JWT access/refresh tokens alongside basic user profile data.
    """
    user = crud.authenticate_email_user(db=db, login_data=data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password."
        )
    
    token_payload = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
    
    user_details = crud.get_user_auth_details(user)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_details
    }

@router.post("/social-signup", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
def social_signup(data: schemas.SocialSignUpRequest, db: Session = Depends(get_db)):
    """
    Unified social auth endpoint (registers if not exists, otherwise logs in).
    
    **Deprecated**: Prefer using `/social-login` directly, which handles both registration and login.
    """
    login_data = schemas.SocialLoginRequest(
        provider=data.provider,
        token=data.token,
        name=data.name
    )
    return social_login(data=login_data, db=db)

@router.post("/social-login", response_model=schemas.AuthResponse, summary="Unified Social Login and Registration")
def social_login(data: schemas.SocialLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates or registers a user using their Google or Apple ID/Access token.
    
    **Unified Flow**:
    - **If the user does not exist**: Automatically registers (signs up) the user and returns the JWT access/refresh tokens.
    - **If the user already exists**: Logs them in, updates their profile name if it changed, and returns the tokens.
    """
    provider = data.provider.lower()
    if provider == "google":
        token_info = verify_google_token(data.token)
    elif provider == "apple":
        token_info = verify_apple_token(data.token)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported social provider. Only 'google' and 'apple' are allowed."
        )

    if "error" in token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token_info["error"]
        )

    email = token_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Social token did not contain a valid email address."
        )

    user = crud.get_user_by_email(db, email)
    if not user:
        # User does not exist, create the account (Sign Up)
        name = data.name or token_info.get("name") or f"Social {provider.capitalize()} User"
        user = models.User(
            email=email,
            name=name,
            provider=provider,
            onboarding_completed=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Optionally update name if it changed
        name_in_token = token_info.get("name")
        if name_in_token and user.name != name_in_token:
            user.name = name_in_token
            db.commit()
            db.refresh(user)
        
    token_payload = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
    
    user_details = crud.get_user_auth_details(user)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_details
    }


@router.post("/refresh", response_model=schemas.AuthResponse)
def refresh_tokens(data: schemas.TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Validates a JWT refresh token and issues a new access token
    along with updated user details.
    """
    payload = decode_token(data.refresh_token, is_refresh=True)
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {payload['error']}"
        )
        
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )
        
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )
        
    token_payload = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_payload)
    
    # We keep the same refresh token or generate a new one
    user_details = crud.get_user_auth_details(user)
    
    return {
        "access_token": access_token,
        "refresh_token": data.refresh_token,
        "token_type": "bearer",
        "user": user_details
    }


@router.post("/forgot-password", response_model=schemas.MessageResponse)
def forgot_password(data: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates the forgot password flow by generating a 6-digit OTP
    and printing/logging it to the server console.
    """
    user = crud.get_user_by_email(db, data.email)
    if not user:
        # Prevent user enumeration by returning a generic success message
        return {
            "message": "If an account with this email exists, a password reset OTP has been sent."
        }
        
    if user.provider != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account is registered via {user.provider.capitalize()} social authentication. Please use social sign-in."
        )
        
    # Generate OTP (saves it and prints to server console logs)
    crud.create_password_reset_otp(db, data.email)
    
    return {
        "message": "If an account with this email exists, a password reset OTP has been sent."
    }

@router.post("/verify-otp", response_model=schemas.VerifyOTPResponse)
def verify_otp(data: schemas.VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verifies the email OTP. If correct, returns a short-lived password reset token.
    """
    is_valid = crud.verify_password_reset_otp(db, data.email, data.otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )
        
    # Generate a short-lived reset token (valid for 10 minutes)
    from datetime import timedelta
    reset_payload = {
        "sub": data.email,
        "type": "reset_password"
    }
    reset_token = create_access_token(data=reset_payload, expires_delta=timedelta(minutes=10))
    
    return {
        "message": "OTP verified successfully.",
        "reset_token": reset_token
    }

@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Resets the user's password using the verified reset token.
    """
    payload = decode_token(data.reset_token, is_refresh=False)
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )
        
    token_type = payload.get("type")
    if token_type != "reset_password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type."
        )
        
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload."
        )
        
    success = crud.reset_user_password(db, email, data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    return {
        "message": "Password has been reset successfully."
    }

