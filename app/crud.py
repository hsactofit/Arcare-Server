from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, date, time, timedelta
from typing import List, Optional
from app import models, schemas
from app.security import hash_password, verify_password
from app.config import IST, get_now_naive


def get_water_logs_sum_for_date(db: Session, user_id: int, on_date: date) -> int:
    """
    Sum WaterLog amounts for a calendar day using an explicit [start, end) range.
    Avoids DB/server timezone issues with func.date().
    Timestamps are stored as naive IST via get_now_naive().
    """
    day_start = datetime.combine(on_date, time.min)
    day_end = day_start + timedelta(days=1)
    total = (
        db.query(func.coalesce(func.sum(models.WaterLog.amount), 0))
        .filter(
            models.WaterLog.user_id == user_id,
            models.WaterLog.timestamp >= day_start,
            models.WaterLog.timestamp < day_end,
        )
        .scalar()
    )
    return int(total or 0)


def get_daily_water_intake(db: Session, user_id: int, on_date: Optional[date] = None) -> int:
    """
    Authoritative daily water total (ml) for dashboard / hydration APIs.

    Combines:
    - Sum of manual WaterLog entries for the day
    - HealthData.water_intake_ml for the day (Health Connect / wearables)

    Uses max() so neither source is under-reported when they are out of sync
    (e.g. HC overwrite vs logs, or logs present while health row is stale).
    """
    if on_date is None:
        on_date = get_now_naive().date()

    logs_total = get_water_logs_sum_for_date(db, user_id, on_date)

    health = (
        db.query(models.HealthData)
        .filter(
            models.HealthData.user_id == user_id,
            models.HealthData.date == on_date,
        )
        .first()
    )
    health_total = int(health.water_intake_ml or 0) if health else 0

    return max(logs_total, health_total)


def _get_or_create_health_for_date(db: Session, user_id: int, on_date: date) -> models.HealthData:
    health = (
        db.query(models.HealthData)
        .filter(
            models.HealthData.user_id == user_id,
            models.HealthData.date == on_date,
        )
        .first()
    )
    if not health:
        health = models.HealthData(user_id=user_id, date=on_date, water_intake_ml=0)
        db.add(health)
        db.flush()
    return health


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def cleanup_old_user_data(db: Session, user_id: int):
    """
    Deletes HealthData and WaterLog records older than 3 months (first day of the month 2 months ago).
    """
    today = date.today()
    current_year = today.year
    current_month = today.month
    target_month = current_month - 2
    target_year = current_year
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    cutoff_date = date(target_year, target_month, 1)
    cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())

    db.query(models.HealthData).filter(
        models.HealthData.user_id == user_id,
        models.HealthData.date < cutoff_date
    ).delete()

    db.query(models.WaterLog).filter(
        models.WaterLog.user_id == user_id,
        models.WaterLog.timestamp < cutoff_datetime
    ).delete()

    db.query(models.NutritionLog).filter(
        models.NutritionLog.user_id == user_id,
        models.NutritionLog.timestamp < cutoff_datetime
    ).delete()

def get_full_onboarding_data(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    # Format to match the onboarding JSON schema
    goals_list = [g.goal_name for g in user.goals]
    
    profile_data = None
    if user.profile:
        profile_data = {
            "dob": user.profile.dob.isoformat() if user.profile.dob else None,
            "gender": user.profile.gender,
            "height": user.profile.height,
            "weight": user.profile.weight
        }
        
    notifications_data = None
    if user.notification_permission:
        notifications_data = {
            "ai_tips": user.notification_permission.ai_tips,
            "rewards": user.notification_permission.rewards,
            "daily_reminder": user.notification_permission.daily_reminder,
            "sleep_reminder": user.notification_permission.sleep_reminder,
            "activity_reminder": user.notification_permission.activity_reminder,
            "challenge_updates": user.notification_permission.challenge_updates,
            "hydration_reminder": user.notification_permission.hydration_reminder
        }
        
    health_connect = False
    if user.health_permission:
        health_connect = user.health_permission.health_connect_connected

    return {
        "auth": {
            "name": user.name,
            "email": user.email,
            "provider": user.provider
        },
        "goals": goals_list,
        "profile": profile_data,
        "permissions": {
            "notifications": notifications_data,
            "health_connect_connected": health_connect
        },
        "completed_at": user.completed_at.isoformat() if user.completed_at else None,
        "onboarding_completed": user.onboarding_completed
    }

def save_user_onboarding(db: Session, data: schemas.OnboardingSubmission):
    # 1. User
    db_user = get_user_by_email(db, data.auth.email)
    if not db_user:
        db_user = models.User(
            email=data.auth.email,
            name=data.auth.name,
            provider=data.auth.provider,
            onboarding_completed=data.onboarding_completed,
            completed_at=data.completed_at
        )
        db.add(db_user)
        db.flush()  # to get db_user.id
    else:
        db_user.name = data.auth.name
        db_user.provider = data.auth.provider
        db_user.onboarding_completed = data.onboarding_completed
        db_user.completed_at = data.completed_at

    # 2. Profile
    if db_user.profile:
        db_user.profile.dob = data.profile.dob
        db_user.profile.gender = data.profile.gender
        db_user.profile.height = data.profile.height
        db_user.profile.weight = data.profile.weight
    else:
        db_profile = models.Profile(
            user_id=db_user.id,
            dob=data.profile.dob,
            gender=data.profile.gender,
            height=data.profile.height,
            weight=data.profile.weight
        )
        db.add(db_profile)

    # 3. Goals (clear old ones and replace)
    db.query(models.Goal).filter(models.Goal.user_id == db_user.id).delete()
    for goal_name in data.goals:
        db_goal = models.Goal(user_id=db_user.id, goal_name=goal_name)
        db.add(db_goal)

    # 4. Notification Permissions
    notif_data = data.permissions.notifications
    if db_user.notification_permission:
        db_user.notification_permission.ai_tips = notif_data.ai_tips
        db_user.notification_permission.rewards = notif_data.rewards
        db_user.notification_permission.daily_reminder = notif_data.daily_reminder
        db_user.notification_permission.sleep_reminder = notif_data.sleep_reminder
        db_user.notification_permission.activity_reminder = notif_data.activity_reminder
        db_user.notification_permission.challenge_updates = notif_data.challenge_updates
        db_user.notification_permission.hydration_reminder = notif_data.hydration_reminder
    else:
        db_notif = models.NotificationPermission(
            user_id=db_user.id,
            ai_tips=notif_data.ai_tips,
            rewards=notif_data.rewards,
            daily_reminder=notif_data.daily_reminder,
            sleep_reminder=notif_data.sleep_reminder,
            activity_reminder=notif_data.activity_reminder,
            challenge_updates=notif_data.challenge_updates,
            hydration_reminder=notif_data.hydration_reminder
        )
        db.add(db_notif)

    # 5. Health Permission
    h_connected = data.permissions.health_connect_connected
    if db_user.health_permission:
        db_user.health_permission.health_connect_connected = h_connected
    else:
        db_health_perm = models.HealthPermission(
            user_id=db_user.id,
            health_connect_connected=h_connected
        )
        db.add(db_health_perm)

    # 6. Initialize default health data for today if not existing.
    # Water starts at 0 — never seed a fake value (it was inflating dashboard water_intake_today
    # when users also logged water via /api/water/log).
    today = get_now_naive().date()
    db_health = db.query(models.HealthData).filter(
        models.HealthData.user_id == db_user.id,
        models.HealthData.date == today
    ).first()
    if not db_health:
        db_health = models.HealthData(
            user_id=db_user.id,
            date=today,
            steps=6200 if h_connected else 0,
            calories=350 if h_connected else 0,
            sleep_duration_hours=7.2 if h_connected else 0.0,
            water_intake_ml=0,
            workouts_count=1 if h_connected else 0,
            heart_rate_bpm=72 if h_connected else 0,
        )
        db.add(db_health)

    cleanup_old_user_data(db, db_user.id)
    db.commit()
    db.refresh(db_user)
    return db_user

def sync_user_health_data(db: Session, email: str, sync_list: List[schemas.DailyHealthData]):
    user = get_user_by_email(db, email)
    if not user:
        return None

    updated_records = []
    for item in sync_list:
        db_health = db.query(models.HealthData).filter(
            models.HealthData.user_id == user.id,
            models.HealthData.date == item.date
        ).first()

        if not db_health:
            db_health = models.HealthData(
                user_id=user.id,
                date=item.date
            )
            db.add(db_health)

        # Update fields that are provided
        if item.steps is not None:
            db_health.steps = item.steps
            # Calculate calories burned if steps is provided but calories is not
            if item.calories is None or item.calories == 0:
                weight = 70.0
                if user.profile and user.profile.weight:
                    weight = user.profile.weight
                db_health.calories = int(round(item.steps * 0.0006125 * weight))

        if item.calories is not None and (item.calories != 0 or item.steps is None):
            db_health.calories = item.calories
        if item.sleep_duration_hours is not None:
            db_health.sleep_duration_hours = item.sleep_duration_hours
        if item.water_intake_ml is not None:
            # Health Connect sends a daily total — never wipe higher manual log totals
            logs_total = get_water_logs_sum_for_date(db, user.id, item.date)
            db_health.water_intake_ml = max(
                int(item.water_intake_ml or 0),
                logs_total,
                int(db_health.water_intake_ml or 0) if db_health.water_intake_ml is not None else 0,
            )
        if item.workouts_count is not None:
            db_health.workouts_count = item.workouts_count
        if item.heart_rate_bpm is not None:
            db_health.heart_rate_bpm = item.heart_rate_bpm

        db_health.updated_at = get_now_naive()
        updated_records.append(db_health)

    cleanup_old_user_data(db, user.id)
    db.commit()
    for r in updated_records:
        db.refresh(r)
    return updated_records

def get_latest_user_health_data(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    return db.query(models.HealthData).filter(
        models.HealthData.user_id == user.id
    ).order_by(models.HealthData.date.desc()).first()

def get_recent_user_health_data(db: Session, email: str, limit: int = 7):
    user = get_user_by_email(db, email)
    if not user:
        return []
    return db.query(models.HealthData).filter(
        models.HealthData.user_id == user.id
    ).order_by(models.HealthData.date.desc()).limit(limit).all()


def create_email_user(db: Session, signup_data: schemas.UserSignUp):
    db_user = models.User(
        email=signup_data.email,
        name=signup_data.name,
        provider=signup_data.provider or "email",
        hashed_password=hash_password(signup_data.password),
        onboarding_completed=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_email_user(db: Session, login_data: schemas.UserLogin):
    user = get_user_by_email(db, login_data.email)
    if not user or user.provider != "email":
        return None
    if not verify_password(login_data.password, user.hashed_password):
        return None
    return user

def get_user_auth_details(user: models.User):
    goals_list = [g.goal_name for g in user.goals]
    
    profile_data = None
    if user.profile:
        profile_data = {
            "dob": user.profile.dob,
            "gender": user.profile.gender,
            "height": user.profile.height,
            "weight": user.profile.weight
        }
        
    notifications_data = None
    if user.notification_permission:
        notifications_data = {
            "ai_tips": user.notification_permission.ai_tips,
            "rewards": user.notification_permission.rewards,
            "daily_reminder": user.notification_permission.daily_reminder,
            "sleep_reminder": user.notification_permission.sleep_reminder,
            "activity_reminder": user.notification_permission.activity_reminder,
            "challenge_updates": user.notification_permission.challenge_updates,
            "hydration_reminder": user.notification_permission.hydration_reminder
        }
        
    permissions_data = None
    if user.health_permission or user.notification_permission:
        permissions_data = {
            "notifications": notifications_data,
            "health_connect_connected": user.health_permission.health_connect_connected if user.health_permission else False
        }

    recent_syncs = [h.updated_at for h in user.health_data if h.updated_at is not None]
    last_sync_date = max(recent_syncs) if recent_syncs else None

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "provider": user.provider,
        "onboarding_completed": user.onboarding_completed,
        "completed_at": user.completed_at,
        "last_sync_date": last_sync_date,
        "profile": profile_data,
        "goals": goals_list,
        "permissions": permissions_data
    }


def create_password_reset_otp(db: Session, email: str) -> str:
    import secrets
    from datetime import timedelta
    
    # Clean up any existing OTPs for this email to prevent spam/duplicate entries
    db.query(models.PasswordResetOTP).filter(models.PasswordResetOTP.email == email).delete()
    
    # Generate 6-digit numeric OTP
    otp = "".join(secrets.choice("0123456789") for _ in range(6))
    
    # Expires in 10 minutes
    expires_at = get_now_naive() + timedelta(minutes=10)
    
    db_otp = models.PasswordResetOTP(
        email=email,
        otp=otp,
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()
    
    # Log to live stdout/server logs as requested by the user
    print(f"\n[PASSWORD RESET OTP] Generated for user {email}: {otp} (Expires at: {expires_at.isoformat()})\n", flush=True)
    
    return otp

def verify_password_reset_otp(db: Session, email: str, otp_code: str) -> bool:
    db_otp = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == email,
        models.PasswordResetOTP.otp == otp_code
    ).first()
    
    if not db_otp:
        return False
        
    # Check expiry
    if db_otp.expires_at < get_now_naive():
        return False
        
    return True

def reset_user_password(db: Session, email: str, new_password: str) -> bool:
    user = get_user_by_email(db, email)
    if not user:
        return False
        
    # Update hashed password
    user.hashed_password = hash_password(new_password)
    
    # Clean up OTP codes for this email
    db.query(models.PasswordResetOTP).filter(models.PasswordResetOTP.email == email).delete()
    
    db.commit()
    return True


def get_user_water_logs(db: Session, email: str, limit: int = 7):
    user = get_user_by_email(db, email)
    if not user:
        return []
    return db.query(models.WaterLog).filter(
        models.WaterLog.user_id == user.id
    ).order_by(models.WaterLog.timestamp.desc()).limit(limit).all()


def create_water_log(db: Session, email: str, log_data: schemas.WaterLogCreate):
    user = get_user_by_email(db, email)
    if not user:
        return None
    ts = log_data.timestamp or get_now_naive()
    db_log = models.WaterLog(
        user_id=user.id,
        amount=log_data.amount,
        timestamp=ts,
    )
    db.add(db_log)

    # Additively update the daily HealthData aggregate for the log's day
    log_date = ts.date() if hasattr(ts, "date") else get_now_naive().date()
    db_health = _get_or_create_health_for_date(db, user.id, log_date)
    db_health.water_intake_ml = int(db_health.water_intake_ml or 0) + int(log_data.amount)
    db_health.updated_at = get_now_naive()

    cleanup_old_user_data(db, user.id)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_water_log_by_id(db: Session, log_id: int):
    return db.query(models.WaterLog).filter(models.WaterLog.id == log_id).first()


def update_water_log(db: Session, db_log: models.WaterLog, log_data: schemas.WaterLogCreate):
    old_amount = int(db_log.amount)
    old_date = db_log.timestamp.date()

    db_log.amount = log_data.amount
    if log_data.timestamp:
        db_log.timestamp = log_data.timestamp

    new_date = db_log.timestamp.date()
    new_amount = int(log_data.amount)

    if old_date == new_date:
        db_health = _get_or_create_health_for_date(db, db_log.user_id, old_date)
        db_health.water_intake_ml = max(0, int(db_health.water_intake_ml or 0) + (new_amount - old_amount))
        db_health.updated_at = get_now_naive()
    else:
        db_health_old = (
            db.query(models.HealthData)
            .filter(
                models.HealthData.user_id == db_log.user_id,
                models.HealthData.date == old_date,
            )
            .first()
        )
        if db_health_old:
            db_health_old.water_intake_ml = max(0, int(db_health_old.water_intake_ml or 0) - old_amount)
            db_health_old.updated_at = get_now_naive()

        db_health_new = _get_or_create_health_for_date(db, db_log.user_id, new_date)
        db_health_new.water_intake_ml = int(db_health_new.water_intake_ml or 0) + new_amount
        db_health_new.updated_at = get_now_naive()

    cleanup_old_user_data(db, db_log.user_id)
    db.commit()
    db.refresh(db_log)
    return db_log


def delete_water_log(db: Session, db_log: models.WaterLog):
    amount = int(db_log.amount)
    log_date = db_log.timestamp.date()
    user_id = db_log.user_id

    db.delete(db_log)

    db_health = (
        db.query(models.HealthData)
        .filter(
            models.HealthData.user_id == user_id,
            models.HealthData.date == log_date,
        )
        .first()
    )
    if db_health:
        db_health.water_intake_ml = max(0, int(db_health.water_intake_ml or 0) - amount)
        db_health.updated_at = get_now_naive()

    db.commit()


def update_user_profile(db: Session, user: models.User, data: schemas.ProfileUpdateRequest) -> models.User:
    # 1. Update user fields
    if data.name is not None:
        user.name = data.name

    # 2. Update Profile fields
    if data.profile is not None:
        if not user.profile:
            user.profile = models.Profile(user_id=user.id)
            db.add(user.profile)
        if data.profile.dob is not None:
            user.profile.dob = data.profile.dob
        if data.profile.gender is not None:
            user.profile.gender = data.profile.gender
        if data.profile.height is not None:
            user.profile.height = data.profile.height
        if data.profile.weight is not None:
            user.profile.weight = data.profile.weight

    # 3. Update Goals (overwrite list if goals is provided)
    if data.goals is not None:
        db.query(models.Goal).filter(models.Goal.user_id == user.id).delete()
        for goal_name in data.goals:
            db_goal = models.Goal(user_id=user.id, goal_name=goal_name)
            db.add(db_goal)

    # 4. Update Permissions
    if data.permissions is not None:
        # Notifications
        if data.permissions.notifications is not None:
            if not user.notification_permission:
                user.notification_permission = models.NotificationPermission(user_id=user.id)
                db.add(user.notification_permission)
            notif = data.permissions.notifications
            if notif.ai_tips is not None:
                user.notification_permission.ai_tips = notif.ai_tips
            if notif.rewards is not None:
                user.notification_permission.rewards = notif.rewards
            if notif.daily_reminder is not None:
                user.notification_permission.daily_reminder = notif.daily_reminder
            if notif.sleep_reminder is not None:
                user.notification_permission.sleep_reminder = notif.sleep_reminder
            if notif.activity_reminder is not None:
                user.notification_permission.activity_reminder = notif.activity_reminder
            if notif.challenge_updates is not None:
                user.notification_permission.challenge_updates = notif.challenge_updates
            if notif.hydration_reminder is not None:
                user.notification_permission.hydration_reminder = notif.hydration_reminder
        # Health Connect
        if data.permissions.health_connect_connected is not None:
            if not user.health_permission:
                user.health_permission = models.HealthPermission(user_id=user.id)
                db.add(user.health_permission)
            user.health_permission.health_connect_connected = data.permissions.health_connect_connected

    db.commit()
    db.refresh(user)
    return user


def get_user_nutrition_logs(db: Session, email: str, limit: int = 7):
    user = get_user_by_email(db, email)
    if not user:
        return []
    return db.query(models.NutritionLog).filter(
        models.NutritionLog.user_id == user.id
    ).order_by(models.NutritionLog.timestamp.desc()).limit(limit).all()


def create_nutrition_log(db: Session, email: str, log_data: schemas.NutritionLogCreate):
    user = get_user_by_email(db, email)
    if not user:
        return None
    db_log = models.NutritionLog(
        user_id=user.id,
        food_name=log_data.food_name,
        calories=log_data.calories,
        protein=log_data.protein,
        fat=log_data.fat,
        carbs=log_data.carbs,
        timestamp=log_data.timestamp or get_now_naive()
    )
    db.add(db_log)
    cleanup_old_user_data(db, user.id)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_nutrition_log_by_id(db: Session, log_id: int):
    return db.query(models.NutritionLog).filter(models.NutritionLog.id == log_id).first()


def update_nutrition_log(db: Session, db_log: models.NutritionLog, log_data: schemas.NutritionLogCreate):
    db_log.food_name = log_data.food_name
    db_log.calories = log_data.calories
    db_log.protein = log_data.protein
    db_log.fat = log_data.fat
    db_log.carbs = log_data.carbs
    if log_data.timestamp:
        db_log.timestamp = log_data.timestamp
    
    cleanup_old_user_data(db, db_log.user_id)
    db.commit()
    db.refresh(db_log)
    return db_log


def delete_nutrition_log(db: Session, db_log: models.NutritionLog):
    db.delete(db_log)
    db.commit()


def auto_checkout_gym_sessions(db: Session, user_id: int):
    from datetime import timedelta
    today = get_now_naive().date()
    open_sessions = db.query(models.GymCheckIn).filter(
        models.GymCheckIn.user_id == user_id,
        models.GymCheckIn.check_out_time == None
    ).all()
    
    updated = False
    for session in open_sessions:
        session_date = session.check_in_time.date()
        if session_date < today:
            # Auto check-out at midnight of that check-in date
            midnight = datetime.combine(session_date + timedelta(days=1), datetime.min.time())
            session.check_out_time = midnight
            session.exercises_done = None
            session.calories_burned = 0.0
            updated = True
            
    if updated:
        db.commit()


def get_latest_gym_session(db: Session, user_id: int):
    auto_checkout_gym_sessions(db, user_id)
    return db.query(models.GymCheckIn).filter(
        models.GymCheckIn.user_id == user_id
    ).order_by(models.GymCheckIn.check_in_time.desc()).first()


# --- SOS Emergency numbers (police / ambulance / fire) ---

def get_or_create_sos_config(db: Session, user_id: int) -> models.SOSConfig:
    """Return the user's SOS emergency-number config, creating defaults if missing."""
    config = db.query(models.SOSConfig).filter(models.SOSConfig.user_id == user_id).first()
    if config:
        return config
    config = models.SOSConfig(
        user_id=user_id,
        police_number="112",
        ambulance_number="102",
        fire_number="101",
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_user_sos_config(db: Session, email: str) -> models.SOSConfig | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    return get_or_create_sos_config(db, user.id)


def update_sos_emergency(
    db: Session, email: str, data: schemas.SOSEmergencyUpdate
) -> models.SOSConfig | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    config = get_or_create_sos_config(db, user.id)
    if data.police_number is not None:
        config.police_number = data.police_number
    if data.ambulance_number is not None:
        config.ambulance_number = data.ambulance_number
    if data.fire_number is not None:
        config.fire_number = data.fire_number
    db.commit()
    db.refresh(config)
    return config


def reset_sos_emergency(db: Session, email: str) -> models.SOSConfig | None:
    """Reset police/ambulance/fire numbers back to defaults."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    config = get_or_create_sos_config(db, user.id)
    config.police_number = "112"
    config.ambulance_number = "102"
    config.fire_number = "101"
    db.commit()
    db.refresh(config)
    return config


# --- SOS Contacts ---

def list_sos_contacts(db: Session, email: str) -> list[models.SOSContact] | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    return (
        db.query(models.SOSContact)
        .filter(models.SOSContact.user_id == user.id)
        .order_by(models.SOSContact.id.asc())
        .all()
    )


def create_sos_contact(
    db: Session, email: str, data: schemas.SOSContactCreate
) -> models.SOSContact | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    contact = models.SOSContact(
        user_id=user.id,
        name=data.name,
        phone=data.phone,
    )
    db.add(contact)
    # Ensure emergency defaults exist once the user starts using SOS
    get_or_create_sos_config(db, user.id)
    db.commit()
    db.refresh(contact)
    return contact


def get_sos_contact(db: Session, contact_id: int) -> models.SOSContact | None:
    return db.query(models.SOSContact).filter(models.SOSContact.id == contact_id).first()


def update_sos_contact(
    db: Session, contact_id: int, data: schemas.SOSContactUpdate
) -> models.SOSContact | None:
    contact = get_sos_contact(db, contact_id)
    if not contact:
        return None
    if data.name is not None:
        contact.name = data.name
    if data.phone is not None:
        contact.phone = data.phone
    db.commit()
    db.refresh(contact)
    return contact


def delete_sos_contact(db: Session, contact_id: int) -> bool:
    contact = get_sos_contact(db, contact_id)
    if not contact:
        return False
    db.delete(contact)
    db.commit()
    return True


# --- Workout plans (date-range) ---

def create_workout_plan(db: Session, user_id: int, data: dict) -> models.WorkoutPlan:
    plan = models.WorkoutPlan(user_id=user_id, **data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_workout_plan(db: Session, plan: models.WorkoutPlan, data: dict) -> models.WorkoutPlan:
    from sqlalchemy.orm.attributes import flag_modified
    from app.config import get_now_naive

    for key, value in data.items():
        setattr(plan, key, value)
    if "days" in data:
        flag_modified(plan, "days")
    plan.updated_at = get_now_naive()
    db.commit()
    db.refresh(plan)
    return plan


def list_workout_plans(db: Session, user_id: int, limit: int = 50) -> list[models.WorkoutPlan]:
    return (
        db.query(models.WorkoutPlan)
        .filter(models.WorkoutPlan.user_id == user_id)
        .order_by(models.WorkoutPlan.start_date.desc(), models.WorkoutPlan.id.desc())
        .limit(limit)
        .all()
    )


def get_workout_plan_by_id(db: Session, plan_id: int) -> models.WorkoutPlan | None:
    return db.query(models.WorkoutPlan).filter(models.WorkoutPlan.id == plan_id).first()


def get_workout_plan_covering_date(db: Session, user_id: int, on_date) -> models.WorkoutPlan | None:
    return (
        db.query(models.WorkoutPlan)
        .filter(
            models.WorkoutPlan.user_id == user_id,
            models.WorkoutPlan.start_date <= on_date,
            models.WorkoutPlan.end_date >= on_date,
        )
        .order_by(models.WorkoutPlan.id.desc())
        .first()
    )


def delete_workout_plan(db: Session, plan: models.WorkoutPlan) -> None:
    db.delete(plan)
    db.commit()


# --- Nutrition plans (date-range) ---

def create_nutrition_plan(db: Session, user_id: int, data: dict) -> models.NutritionPlan:
    plan = models.NutritionPlan(user_id=user_id, **data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_nutrition_plan(db: Session, plan: models.NutritionPlan, data: dict) -> models.NutritionPlan:
    from sqlalchemy.orm.attributes import flag_modified
    from app.config import get_now_naive

    for key, value in data.items():
        setattr(plan, key, value)
    if "days" in data:
        flag_modified(plan, "days")
    plan.updated_at = get_now_naive()
    db.commit()
    db.refresh(plan)
    return plan


def list_nutrition_plans(db: Session, user_id: int, limit: int = 50) -> list[models.NutritionPlan]:
    return (
        db.query(models.NutritionPlan)
        .filter(models.NutritionPlan.user_id == user_id)
        .order_by(models.NutritionPlan.start_date.desc(), models.NutritionPlan.id.desc())
        .limit(limit)
        .all()
    )


def get_nutrition_plan_by_id(db: Session, plan_id: int) -> models.NutritionPlan | None:
    return db.query(models.NutritionPlan).filter(models.NutritionPlan.id == plan_id).first()


def get_nutrition_plan_covering_date(db: Session, user_id: int, on_date) -> models.NutritionPlan | None:
    return (
        db.query(models.NutritionPlan)
        .filter(
            models.NutritionPlan.user_id == user_id,
            models.NutritionPlan.start_date <= on_date,
            models.NutritionPlan.end_date >= on_date,
        )
        .order_by(models.NutritionPlan.id.desc())
        .first()
    )


def delete_nutrition_plan(db: Session, plan: models.NutritionPlan) -> None:
    db.delete(plan)
    db.commit()






