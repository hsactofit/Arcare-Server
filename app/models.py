from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, ForeignKey
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
    steps = Column(Integer, default=0)
    calories = Column(Integer, default=0)
    sleep_duration_hours = Column(Float, default=0.0)
    water_intake_ml = Column(Integer, default=0)
    workouts_count = Column(Integer, default=0)
    heart_rate_bpm = Column(Integer, default=70)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="health_data")


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

