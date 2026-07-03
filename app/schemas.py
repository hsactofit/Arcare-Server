from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, date

# Auth schema
class AuthSchema(BaseModel):
    name: str = Field(..., description="Full Name of the user")
    email: EmailStr = Field(..., description="Email address of the user")
    provider: str = Field(default="google", description="Auth provider (e.g., google, apple, email)")

# Profile schema
class ProfileSchema(BaseModel):
    dob: date = Field(..., description="Date of birth")
    gender: str = Field(..., description="Gender")
    height: Optional[float] = Field(None, description="Height in cm")
    weight: Optional[float] = Field(None, description="Weight in kg")

    class Config:
        from_attributes = True

# Notification Permissions
class NotificationPermissionSchema(BaseModel):
    ai_tips: bool = True
    rewards: bool = False
    daily_reminder: bool = True
    sleep_reminder: bool = True
    activity_reminder: bool = True
    challenge_updates: bool = False
    hydration_reminder: bool = True

    class Config:
        from_attributes = True

# Permissions schema container
class PermissionsSchema(BaseModel):
    notifications: NotificationPermissionSchema
    health_connect_connected: bool = False

# Onboarding Submission Schema (Matches frontend structure exactly)
class OnboardingSubmission(BaseModel):
    auth: AuthSchema
    goals: List[str] = Field(default_factory=list)
    profile: ProfileSchema
    permissions: PermissionsSchema
    completed_at: datetime
    onboarding_completed: bool = True

# Health Data Sync Request Schema
class DailyHealthData(BaseModel):
    date: date
    steps: Optional[int] = 0
    calories: Optional[int] = 0
    sleep_duration_hours: Optional[float] = 0.0
    water_intake_ml: Optional[int] = 0
    workouts_count: Optional[int] = 0
    heart_rate_bpm: Optional[int] = 70

class DailyHealthDataResponse(BaseModel):
    date: date
    steps: int
    calories: int
    sleep_duration_hours: float
    water_intake_ml: int
    workouts_count: int
    heart_rate_bpm: int
    updated_at: datetime

    class Config:
        from_attributes = True

# Dashboard Widgets / Response Schema
class DashboardWidget(BaseModel):
    title: str
    value: str
    target: Optional[str] = None
    unit: Optional[str] = None
    status: Optional[str] = None

class DashboardResponse(BaseModel):
    wellness_score: int
    daily_summary: str
    recommendations: List[str]
    widgets: List[DashboardWidget]
    last_synced_date: Optional[date] = None

class DashboardSyncResponse(BaseModel):
    wellness_score: int
    daily_summary: str
    recommendations: List[str]
    ai_buddy_message: str



# Generic API message
class MessageResponse(BaseModel):
    message: str

# Auth / Credentials Validation
class UserSignUp(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    name: str = Field(..., description="User's Full Name")
    provider: Optional[str] = Field("email", description="Auth provider (defaults to email)")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SocialSignUpRequest(BaseModel):
    provider: str = Field(..., description="google or apple")
    token: str = Field(..., description="ID Token or Identity Token from the OAuth provider")
    name: Optional[str] = Field(None, description="Optional user name if not included in the token (mostly Apple signups)")

class SocialLoginRequest(BaseModel):
    provider: str = Field(..., description="google or apple")
    token: str = Field(..., description="ID Token or Identity Token from the OAuth provider")
    name: Optional[str] = Field(None, description="Optional user name if not included in the token (mostly Apple signups)")


class TokenRefreshRequest(BaseModel):
    refresh_token: str

class UserDetailResponse(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    provider: str
    onboarding_completed: bool
    completed_at: Optional[datetime] = None
    last_sync_date: Optional[datetime] = None
    profile: Optional[ProfileSchema] = None
    goals: List[str] = Field(default_factory=list)
    permissions: Optional[PermissionsSchema] = None

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserDetailResponse


# Forgot Password Flow Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

class VerifyOTPResponse(BaseModel):
    message: str
    reset_token: str

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=6, description="New password must be at least 6 characters")


