import uuid
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    provider = Column(String, default="google")
    hashed_password = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    notification_permission = relationship("NotificationPermission", back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_permission = relationship("HealthPermission", back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_data = relationship("HealthData", back_populates="user", cascade="all, delete-orphan")
    water_logs = relationship("WaterLog", back_populates="user", cascade="all, delete-orphan")
    nutrition_logs = relationship("NutritionLog", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    dob = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_name = Column(String, nullable=False)

    # Relationships
    user = relationship("User", back_populates="goals")


class NotificationPermission(Base):
    __tablename__ = "notification_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    ai_tips = Column(Boolean, default=True)
    rewards = Column(Boolean, default=False)
    daily_reminder = Column(Boolean, default=True)
    sleep_reminder = Column(Boolean, default=True)
    activity_reminder = Column(Boolean, default=True)
    challenge_updates = Column(Boolean, default=False)
    hydration_reminder = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="notification_permission")


class HealthPermission(Base):
    __tablename__ = "health_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    health_connect_connected = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="health_permission")


class HealthData(Base):
    __tablename__ = "health_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    steps = Column(Integer, default=0)
    calories = Column(Integer, default=0)
    sleep_duration_hours = Column(Float, default=0.0)
    water_intake_ml = Column(Integer, default=0)
    workouts_count = Column(Integer, default=0)
    heart_rate_bpm = Column(Integer, default=70)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    user = relationship("User", back_populates="health_data")



class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WaterLog(Base):
    __tablename__ = "water_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)  # in ml
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="water_logs")


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    food_name = Column(String, nullable=False)
    calories = Column(Float, default=0.0, nullable=False)
    protein = Column(Float, default=0.0, nullable=False)  # in grams
    fat = Column(Float, default=0.0, nullable=False)  # in grams
    carbs = Column(Float, default=0.0, nullable=False)  # in grams
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="nutrition_logs")


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    shortDescription = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    infoText = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., Daily, Weekly, Monthly, Fitness
    challengeType = Column(String(50), nullable=False)  # e.g., steps, water, sleep
    difficulty = Column(String(50), nullable=False)  # EASY, MEDIUM, HARD
    targetValue = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)  # steps, ml, hours, etc.
    rewardPoints = Column(Integer, default=0)
    rewardBadge = Column(String(255), nullable=True)
    bannerImage = Column(String(255), nullable=True)
    participantsCount = Column(Integer, default=0)
    startDate = Column(DateTime, nullable=False)
    endDate = Column(DateTime, nullable=False)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, COMPLETED, EXPIRED
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class UserChallenge(Base):
    __tablename__ = "user_challenges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id = Column(String(36), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    joinedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    currentProgress = Column(Float, default=0.0)
    progressPercentage = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    rewardClaimed = Column(Boolean, default=False)
    completedAt = Column(DateTime, nullable=True)

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

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    challengeId = Column(String(36), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    userId = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=True)
    progress = Column(Float, default=0.0)
    percentile = Column(Float, default=0.0)
    completedAt = Column(DateTime, nullable=True)
    lastUpdated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('challengeId', 'userId', name='_challenge_user_leaderboard_uc'),)

    # Relationships
    user = relationship("User")
    challenge = relationship("Challenge")


class GymCheckIn(Base):
    __tablename__ = "gym_check_ins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    qr_data = Column(String(255), nullable=False)
    gym_name = Column(String(255), nullable=False)
    check_in_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    check_out_time = Column(DateTime, nullable=True)
    exercises_done = Column(Text, nullable=True) # JSON list of exercise names and sets
    calories_burned = Column(Float, default=0.0)

    user = relationship("User")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=True)


