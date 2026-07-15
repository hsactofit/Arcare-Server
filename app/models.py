import uuid
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, ForeignKey, UniqueConstraint, Text, JSON
from sqlalchemy.orm import relationship, Mapped
from datetime import datetime, timezone, date
from typing import Optional
from app.database import Base
from app.config import IST, get_now_naive

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    email: Mapped[str] = Column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = Column(String, nullable=True)
    provider: Mapped[str] = Column(String, default="google")
    hashed_password: Mapped[Optional[str]] = Column(String, nullable=True)
    onboarding_completed: Mapped[bool] = Column(Boolean, default=False)

    completed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=get_now_naive)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    notification_permission = relationship("NotificationPermission", back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_permission = relationship("HealthPermission", back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_data = relationship("HealthData", back_populates="user", cascade="all, delete-orphan")
    water_logs = relationship("WaterLog", back_populates="user", cascade="all, delete-orphan")
    nutrition_logs = relationship("NutritionLog", back_populates="user", cascade="all, delete-orphan")
    sos_config = relationship("SOSConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sos_contacts = relationship("SOSContact", back_populates="user", cascade="all, delete-orphan")
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")
    nutrition_plans = relationship("NutritionPlan", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    dob: Mapped[Optional[date]] = Column(Date, nullable=True)
    gender: Mapped[Optional[str]] = Column(String, nullable=True)
    height: Mapped[Optional[float]] = Column(Float, nullable=True)
    weight: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_name: Mapped[str] = Column(String, nullable=False)

    # Relationships
    user = relationship("User", back_populates="goals")


class NotificationPermission(Base):
    __tablename__ = "notification_permissions"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    ai_tips: Mapped[bool] = Column(Boolean, default=True)
    rewards: Mapped[bool] = Column(Boolean, default=False)
    daily_reminder: Mapped[bool] = Column(Boolean, default=True)
    sleep_reminder: Mapped[bool] = Column(Boolean, default=True)
    activity_reminder: Mapped[bool] = Column(Boolean, default=True)
    challenge_updates: Mapped[bool] = Column(Boolean, default=False)
    hydration_reminder: Mapped[bool] = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="notification_permission")


class HealthPermission(Base):
    __tablename__ = "health_permissions"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    health_connect_connected: Mapped[bool] = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="health_permission")


class HealthData(Base):
    __tablename__ = "health_data"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = Column(Date, nullable=False)
    steps: Mapped[int] = Column(Integer, default=0)
    calories: Mapped[int] = Column(Integer, default=0)
    sleep_duration_hours: Mapped[float] = Column(Float, default=0.0)
    water_intake_ml: Mapped[int] = Column(Integer, default=0)
    workouts_count: Mapped[int] = Column(Integer, default=0)
    heart_rate_bpm: Mapped[int] = Column(Integer, default=70)
    updated_at: Mapped[datetime] = Column(DateTime, default=get_now_naive, onupdate=get_now_naive)

    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    user = relationship("User", back_populates="health_data")



class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    email: Mapped[str] = Column(String, index=True, nullable=False)
    otp: Mapped[str] = Column(String, nullable=False)
    expires_at: Mapped[datetime] = Column(DateTime, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=get_now_naive)


class WaterLog(Base):
    __tablename__ = "water_logs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = Column(Integer, nullable=False)  # in ml
    timestamp: Mapped[datetime] = Column(DateTime, default=get_now_naive, nullable=False)

    user = relationship("User", back_populates="water_logs")


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    food_name: Mapped[str] = Column(String, nullable=False)
    calories: Mapped[float] = Column(Float, default=0.0, nullable=False)
    protein: Mapped[float] = Column(Float, default=0.0, nullable=False)  # in grams
    fat: Mapped[float] = Column(Float, default=0.0, nullable=False)  # in grams
    carbs: Mapped[float] = Column(Float, default=0.0, nullable=False)  # in grams
    timestamp: Mapped[datetime] = Column(DateTime, default=get_now_naive, nullable=False)

    user = relationship("User", back_populates="nutrition_logs")


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = Column(String(255), nullable=False)
    shortDescription: Mapped[Optional[str]] = Column(String(255), nullable=True)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    infoText: Mapped[Optional[str]] = Column(Text, nullable=True)
    category: Mapped[str] = Column(String(50), nullable=False)  # e.g., Daily, Weekly, Monthly, Fitness
    challengeType: Mapped[str] = Column(String(50), nullable=False)  # e.g., steps, water, sleep
    difficulty: Mapped[str] = Column(String(50), nullable=False)  # EASY, MEDIUM, HARD
    targetValue: Mapped[float] = Column(Float, nullable=False)
    unit: Mapped[str] = Column(String(50), nullable=False)  # steps, ml, hours, etc.
    rewardPoints: Mapped[int] = Column(Integer, default=0)
    rewardBadge: Mapped[Optional[str]] = Column(String(255), nullable=True)
    bannerImage: Mapped[Optional[str]] = Column(String(255), nullable=True)
    participantsCount: Mapped[int] = Column(Integer, default=0)
    startDate: Mapped[datetime] = Column(DateTime, nullable=False)
    endDate: Mapped[datetime] = Column(DateTime, nullable=False)
    status: Mapped[str] = Column(String(50), default="ACTIVE")  # ACTIVE, COMPLETED, EXPIRED
    createdAt: Mapped[datetime] = Column(DateTime, default=get_now_naive)
    updatedAt: Mapped[datetime] = Column(DateTime, default=get_now_naive, onupdate=get_now_naive)


class UserChallenge(Base):
    __tablename__ = "user_challenges"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id: Mapped[str] = Column(String(36), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    joinedAt: Mapped[datetime] = Column(DateTime, default=get_now_naive)
    currentProgress: Mapped[float] = Column(Float, default=0.0)
    progressPercentage: Mapped[float] = Column(Float, default=0.0)
    completed: Mapped[bool] = Column(Boolean, default=False)
    rewardClaimed: Mapped[bool] = Column(Boolean, default=False)
    completedAt: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint('user_id', 'challenge_id', name='_user_challenge_uc'),)

    # Relationships
    user = relationship("User")
    challenge = relationship("Challenge")

    @property
    def userId(self):
        return self.user_id

    @property
    def challengeId(self):
        return self.challenge_id



class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    challengeId: Mapped[str] = Column(String(36), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[Optional[int]] = Column(Integer, nullable=True)
    progress: Mapped[float] = Column(Float, default=0.0)
    percentile: Mapped[float] = Column(Float, default=0.0)
    completedAt: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    lastUpdated: Mapped[datetime] = Column(DateTime, default=get_now_naive, onupdate=get_now_naive)

    __table_args__ = (UniqueConstraint('challengeId', 'userId', name='_challenge_user_leaderboard_uc'),)

    # Relationships
    user = relationship("User")
    challenge = relationship("Challenge")


class GymCheckIn(Base):
    __tablename__ = "gym_check_ins"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    qr_data: Mapped[str] = Column(String(255), nullable=False)
    gym_name: Mapped[str] = Column(String(255), nullable=False)
    check_in_time: Mapped[datetime] = Column(DateTime, default=get_now_naive, nullable=False)
    check_out_time: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    exercises_done: Mapped[Optional[str]] = Column(Text, nullable=True) # JSON list of exercise names and sets
    calories_burned: Mapped[float] = Column(Float, default=0.0)

    user = relationship("User")

    @property
    def userId(self):
        return self.user_id



class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), unique=True, nullable=False)
    category: Mapped[Optional[str]] = Column(String(100), nullable=True)


class SOSConfig(Base):
    """Per-user emergency service numbers (police, ambulance, fire)."""
    __tablename__ = "sos_configs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    police_number: Mapped[str] = Column(String(50), default="112", nullable=False)
    ambulance_number: Mapped[str] = Column(String(50), default="102", nullable=False)
    fire_number: Mapped[str] = Column(String(50), default="101", nullable=False)

    user = relationship("User", back_populates="sos_config")


class SOSContact(Base):
    """Individual emergency contact for a user (CRUD-able)."""
    __tablename__ = "sos_contacts"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = Column(String(255), nullable=False)
    phone: Mapped[str] = Column(String(50), nullable=False)

    user = relationship("User", back_populates="sos_contacts")


class WorkoutPlan(Base):
    """User workout plan for a date range (which exercises, how, how much)."""
    __tablename__ = "workout_plans"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = Column(String(255), nullable=False)
    goal: Mapped[Optional[str]] = Column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    start_date: Mapped[date] = Column(Date, nullable=False, index=True)
    end_date: Mapped[date] = Column(Date, nullable=False, index=True)
    # [{date, focus, exercises: [{name, how_to, sets, reps, duration_minutes, rest_seconds, equipment, image_url}]}]
    days: Mapped[list] = Column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = Column(DateTime, default=get_now_naive)
    updated_at: Mapped[datetime] = Column(DateTime, default=get_now_naive, onupdate=get_now_naive)

    user = relationship("User", back_populates="workout_plans")


class NutritionPlan(Base):
    """User nutrition plan for a date range (what to eat, how, how much)."""
    __tablename__ = "nutrition_plans"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = Column(String(255), nullable=False)
    goal: Mapped[Optional[str]] = Column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    start_date: Mapped[date] = Column(Date, nullable=False, index=True)
    end_date: Mapped[date] = Column(Date, nullable=False, index=True)
    daily_calories_target: Mapped[Optional[int]] = Column(Integer, nullable=True)
    # [{date, meals: [{meal_type, name, how_to, portion, calories, protein_g, carbs_g, fat_g, image_url}], snacks: [...]}]
    days: Mapped[list] = Column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = Column(DateTime, default=get_now_naive)
    updated_at: Mapped[datetime] = Column(DateTime, default=get_now_naive, onupdate=get_now_naive)

    user = relationship("User", back_populates="nutrition_plans")
