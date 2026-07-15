from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime, date
import datetime as dt_module


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
    water_intake_ml: Optional[int] = None
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

# Health Metrics Logging & Graph API Schemas
class MetricLogRequest(BaseModel):
    metric: str = Field(..., description="Metric type: e.g., steps, calories, sleep, water, workouts, heart_rate")
    value: float = Field(..., description="Value to log for the metric")
    date: Optional[dt_module.date] = Field(default=None, description="Date of the log (defaults to today)")

class MetricLogResponse(BaseModel):
    message: str
    metric: str
    value: float
    date: dt_module.date
    calories_burned: Optional[int] = None
    health_data: DailyHealthDataResponse

class MetricGraphDataPoint(BaseModel):
    label: str = Field(..., description="Date label (e.g. YYYY-MM-DD or YYYY-MM)")
    value: float = Field(..., description="Metric value or aggregated value")
    calories_burned: Optional[float] = Field(None, description="Calculated calories burned if the metric is 'steps'")

class MetricGraphResponse(BaseModel):
    metric: str
    period: str
    data: List[MetricGraphDataPoint]
    feedback: str
    average: float
    total: Optional[float] = None
    calories_total: Optional[float] = None
    calories_average: Optional[float] = None


# Dashboard Widgets / Response Schema
class GymSessionResponse(BaseModel):
    id: str
    userId: int
    qr_data: str
    gym_name: str
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    exercises_done: Optional[str] = None
    calories_burned: float = 0.0

    class Config:
        from_attributes = True


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
    water_intake_today: int
    last_synced_date: Optional[date] = None
    protein_today: float = 0.0
    carbs_today: float = 0.0
    fat_today: float = 0.0
    latest_gym_session: Optional[GymSessionResponse] = None

class DashboardSyncResponse(BaseModel):
    wellness_score: int
    active_subscore: int
    sleep_subscore: int
    nutrition_subscore: int
    mindfulness_subscore: int
    daily_summary: str
    recommendations: List[str]
    ai_buddy_message: str
    water_intake_today: int
    goals: dict[str, float]
    protein_today: float = 0.0
    carbs_today: float = 0.0
    fat_today: float = 0.0
    latest_gym_session: Optional[GymSessionResponse] = None





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


class WaterLogResponse(BaseModel):
    id: int
    amount: int
    timestamp: datetime

    class Config:
        from_attributes = True


class WaterLogCreate(BaseModel):
    amount: int
    timestamp: Optional[datetime] = None


class HydrationHistoryResponse(BaseModel):
    water_intake_today: int
    logs: List[WaterLogResponse]


class WaterLogSubmitResponse(BaseModel):
    id: int
    message: str = "Water intake logged successfully"
    amount: int
    timestamp: datetime

    class Config:
        from_attributes = True


class WaterGraphDataPoint(BaseModel):
    label: str
    amount: int


class WaterGraphResponse(BaseModel):
    period: str
    data: List[WaterGraphDataPoint]


class NutritionLogResponse(BaseModel):
    id: int
    food_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    timestamp: datetime

    class Config:
        from_attributes = True


class NutritionLogCreate(BaseModel):
    food_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    timestamp: Optional[datetime] = None


class NutritionHistoryResponse(BaseModel):
    calories_today: float
    protein_today: float
    fat_today: float
    carbs_today: float
    logs: List[NutritionLogResponse]


class NutritionLogSubmitResponse(BaseModel):
    id: int
    message: str = "Nutrition intake logged successfully"
    food_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    timestamp: datetime

    class Config:
        from_attributes = True


class NutritionGraphDataPoint(BaseModel):
    label: str
    calories: float
    protein: float
    fat: float
    carbs: float


class NutritionGraphResponse(BaseModel):
    period: str
    data: List[NutritionGraphDataPoint]


# --- CHALLENGES SCHEMAS ---

class ChallengeBase(BaseModel):
    title: str
    shortDescription: Optional[str] = None
    description: Optional[str] = None
    infoText: Optional[str] = None
    category: str
    challengeType: str
    difficulty: str
    targetValue: float
    unit: str
    rewardPoints: int = 0
    rewardBadge: Optional[str] = None
    bannerImage: Optional[str] = None
    startDate: datetime
    endDate: datetime
    status: str = "ACTIVE"

class ChallengeCreate(ChallengeBase):
    pass

class DailyHistoryItem(BaseModel):
    date: str
    status: str  # "completed", "missed", "in_progress"
    progress: float
    target: float

class ChallengeResponse(ChallengeBase):
    id: str
    participantsCount: int
    createdAt: datetime
    updatedAt: datetime
    joined: Optional[bool] = False
    completed: Optional[bool] = False
    currentProgress: Optional[float] = 0.0
    completedToday: Optional[bool] = False
    doneToday: Optional[bool] = False
    dailyHistory: Optional[List[DailyHistoryItem]] = []

    class Config:
        from_attributes = True

class UserChallengeResponse(BaseModel):
    id: str
    userId: int
    challengeId: str
    joinedAt: datetime
    currentProgress: float
    progressPercentage: float
    completed: bool
    rewardClaimed: bool
    completedAt: Optional[datetime] = None
    completedToday: Optional[bool] = False
    doneToday: Optional[bool] = False
    dailyHistory: Optional[List[DailyHistoryItem]] = []

    class Config:
        from_attributes = True

class ProgressSubmitRequest(BaseModel):
    progress: float

class RewardClaimResponse(BaseModel):
    message: str = "Reward claimed successfully"
    rewardPoints: int
    rewardBadge: Optional[str] = None
    rewardClaimed: bool

class LeaderboardUser(BaseModel):
    rank: int
    userId: str
    name: str
    progress: float

class CurrentUserLeaderboard(BaseModel):
    rank: int
    progress: float
    percentile: float

class LeaderboardResponse(BaseModel):
    challengeId: str
    leaderboardType: str
    totalParticipants: int
    currentUser: Optional[CurrentUserLeaderboard] = None
    leaders: List[LeaderboardUser]


# --- GYM CHECK-IN SCHEMAS ---

class GymCheckInRequest(BaseModel):
    qr_data: str = Field(..., description="The scanned QR code content")
    gym_name: str = Field(..., description="Name of the gym")

class GymExerciseSetInput(BaseModel):
    name: str = Field(..., description="Name of the exercise")
    sets: int = Field(..., ge=1, description="Number of sets performed")

class GymCheckOutRequest(BaseModel):
    exercises: List[GymExerciseSetInput] = Field(..., description="List of exercises and sets performed during the session")

class GymCheckInResponse(BaseModel):
    id: str
    userId: int
    qr_data: str
    gym_name: str
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    exercises_done: Optional[str] = None
    calories_burned: float = 0.0
    message: str

    class Config:
        from_attributes = True

class ExerciseResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


# --- PROGRESS TRENDS SCHEMAS ---

class TrendTargetCompletion(BaseModel):
    steps: str  # "yes" / "no"
    calories: str  # "yes" / "no"
    sleep: str  # "yes" / "no"
    hydration: str  # "yes" / "no"

class TrendHistoryItem(BaseModel):
    date: str
    steps: float
    calories: float
    sleep: float
    water: float
    targets_completed: TrendTargetCompletion

class TrendGraphDataPoint(BaseModel):
    label: str
    steps: float
    calories: float
    sleep: float
    water: float

class TrendAverages(BaseModel):
    steps: float
    calories: float
    sleep: float
    hydration: float

class TrendTargets(BaseModel):
    steps: float
    calories: float
    sleep: float
    hydration: float

class ProgressTrendsResponse(BaseModel):
    period: str
    averages: TrendAverages
    targets: TrendTargets
    history: List[TrendHistoryItem]
    graph_data: List[TrendGraphDataPoint]
    page: int
    limit: int
    total_items: int
    total_pages: int


# Edit Profile request schemas
class ProfileUpdateSchema(BaseModel):
    dob: Optional[date] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None

class NotificationPermissionUpdateSchema(BaseModel):
    ai_tips: Optional[bool] = None
    rewards: Optional[bool] = None
    daily_reminder: Optional[bool] = None
    sleep_reminder: Optional[bool] = None
    activity_reminder: Optional[bool] = None
    challenge_updates: Optional[bool] = None
    hydration_reminder: Optional[bool] = None

class PermissionsUpdateSchema(BaseModel):
    notifications: Optional[NotificationPermissionUpdateSchema] = None
    health_connect_connected: Optional[bool] = None

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    profile: Optional[ProfileUpdateSchema] = None
    goals: Optional[List[str]] = None
    permissions: Optional[PermissionsUpdateSchema] = None


# --- SOS Contact schemas ---
class SOSContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the emergency contact")
    phone: str = Field(..., min_length=1, max_length=50, description="Phone number of the emergency contact")


class SOSContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the emergency contact")
    phone: Optional[str] = Field(None, min_length=1, max_length=50, description="Phone number of the emergency contact")


class SOSContactResponse(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str

    class Config:
        from_attributes = True


class SOSContactListResponse(BaseModel):
    contacts: List[SOSContactResponse]
    total: int


# --- SOS Emergency service numbers schemas ---
class SOSEmergencyUpdate(BaseModel):
    police_number: Optional[str] = Field(None, min_length=1, max_length=50, description="Police emergency number")
    ambulance_number: Optional[str] = Field(None, min_length=1, max_length=50, description="Ambulance emergency number")
    fire_number: Optional[str] = Field(None, min_length=1, max_length=50, description="Fire emergency number")


class SOSEmergencyResponse(BaseModel):
    id: int
    user_id: int
    police_number: str
    ambulance_number: str
    fire_number: str

    class Config:
        from_attributes = True


# --- Combined SOS overview ---
class SOSResponse(BaseModel):
    user_id: int
    contacts: List[SOSContactResponse]
    emergency_numbers: SOSEmergencyResponse

    class Config:
        from_attributes = True


class SOSTriggerRequest(BaseModel):
    latitude: Optional[float] = Field(None, description="Current latitude of the user")
    longitude: Optional[float] = Field(None, description="Current longitude of the user")


class SOSTriggerResponse(BaseModel):
    message: str
    notified_contacts: List[SOSContactResponse]
    emergency_numbers: dict
    location: Optional[dict] = None


# --- Workout plan (date range + exercises) ---
class WorkoutExerciseItem(BaseModel):
    name: str = Field(..., description="Which exercise to do")
    how_to: str = Field(..., description="How to perform the exercise")
    sets: Optional[int] = Field(None, ge=1, description="How many sets")
    reps: Optional[str] = Field(None, description="How many reps, e.g. '10-12' or 'AMRAP'")
    duration_minutes: Optional[float] = Field(None, ge=0, description="Duration if timed (minutes)")
    rest_seconds: Optional[int] = Field(None, ge=0, description="Rest between sets")
    equipment: Optional[str] = Field(None, description="Equipment needed")
    muscle_groups: Optional[List[str]] = None
    image_url: Optional[str] = None


class WorkoutDayItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    day_date: date = Field(..., description="Calendar date for this workout day", alias="date")
    focus: Optional[str] = Field(None, description="e.g. Upper body, Legs, Rest")
    is_rest_day: bool = False
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseItem] = Field(default_factory=list)


class WorkoutPlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    start_date: date
    end_date: date
    goal: Optional[str] = None
    notes: Optional[str] = None
    days: Optional[List[WorkoutDayItem]] = Field(
        None,
        description="Optional day-by-day schedule. If omitted, empty days are created for the range.",
    )


class WorkoutPlanUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    notes: Optional[str] = None
    days: Optional[List[WorkoutDayItem]] = None


class WorkoutPlanGenerateRequest(BaseModel):
    """Optional AI fill for a date-range workout plan."""
    title: Optional[str] = None
    start_date: date
    end_date: date
    goal: Optional[str] = Field(None, description="e.g. Build muscle, Lose weight")
    experience_level: Optional[str] = Field(None, description="Beginner / Intermediate / Advanced")
    location: Optional[str] = Field(None, description="Home / Gym / Outdoor")
    equipment: Optional[List[str]] = None
    focus_areas: Optional[List[str]] = None
    session_duration_minutes: Optional[int] = Field(None, ge=10, le=180)
    notes: Optional[str] = None


class WorkoutPlanResponse(BaseModel):
    id: int
    user_id: int
    title: str
    goal: Optional[str] = None
    notes: Optional[str] = None
    start_date: date
    end_date: date
    days: List[WorkoutDayItem]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkoutPlanListResponse(BaseModel):
    plans: List[WorkoutPlanResponse]
    total: int


class WorkoutDayScheduleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    day_date: date = Field(..., alias="date")
    plan_id: Optional[int] = None
    plan_title: Optional[str] = None
    focus: Optional[str] = None
    is_rest_day: bool = False
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseItem] = Field(default_factory=list)


# --- Nutrition plan (date range + meals) ---
class NutritionMealItem(BaseModel):
    meal_type: str = Field(..., description="breakfast | lunch | dinner | snack")
    name: str = Field(..., description="What to eat")
    how_to: Optional[str] = Field(None, description="How to prepare / eat")
    portion: Optional[str] = Field(None, description="How much, e.g. '1 bowl', '200g'")
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    ingredients: Optional[List[str]] = None
    image_url: Optional[str] = None


class NutritionDayItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    day_date: date = Field(..., alias="date")
    notes: Optional[str] = None
    meals: List[NutritionMealItem] = Field(default_factory=list)


class NutritionPlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    start_date: date
    end_date: date
    goal: Optional[str] = None
    notes: Optional[str] = None
    daily_calories_target: Optional[int] = Field(None, ge=800, le=6000)
    days: Optional[List[NutritionDayItem]] = Field(
        None,
        description="Optional day-by-day meals. If omitted, empty days are created for the range.",
    )


class NutritionPlanUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    notes: Optional[str] = None
    daily_calories_target: Optional[int] = Field(None, ge=800, le=6000)
    days: Optional[List[NutritionDayItem]] = None


class NutritionPlanGenerateRequest(BaseModel):
    title: Optional[str] = None
    start_date: date
    end_date: date
    goal: Optional[str] = None
    dietary_preference: Optional[str] = None
    allergies: Optional[List[str]] = None
    meals_per_day: Optional[int] = Field(3, ge=2, le=6)
    cuisine: Optional[str] = None
    daily_calories_target: Optional[int] = Field(None, ge=800, le=6000)
    notes: Optional[str] = None


class NutritionPlanResponse(BaseModel):
    id: int
    user_id: int
    title: str
    goal: Optional[str] = None
    notes: Optional[str] = None
    start_date: date
    end_date: date
    daily_calories_target: Optional[int] = None
    days: List[NutritionDayItem]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NutritionPlanListResponse(BaseModel):
    plans: List[NutritionPlanResponse]
    total: int


class NutritionDayScheduleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    day_date: date = Field(..., alias="date")
    plan_id: Optional[int] = None
    plan_title: Optional[str] = None
    notes: Optional[str] = None
    meals: List[NutritionMealItem] = Field(default_factory=list)








