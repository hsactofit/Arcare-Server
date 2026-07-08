from sqlalchemy.orm import Session
from datetime import datetime, timezone, date
from typing import List
from app import models, schemas
from app.security import hash_password, verify_password

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

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

    # 6. Initialize default health data for today if not existing
    today = date.today()
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
            water_intake_ml=1200 if h_connected else 0,
            workouts_count=1 if h_connected else 0,
            heart_rate_bpm=72 if h_connected else 0,
        )
        db.add(db_health)

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
            db_health.water_intake_ml = item.water_intake_ml
        if item.workouts_count is not None:
            db_health.workouts_count = item.workouts_count
        if item.heart_rate_bpm is not None:
            db_health.heart_rate_bpm = item.heart_rate_bpm

        db_health.updated_at = datetime.now(timezone.utc)
        updated_records.append(db_health)

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
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
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
    if db_otp.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
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
    db_log = models.WaterLog(
        user_id=user.id,
        amount=log_data.amount,
        timestamp=log_data.timestamp or datetime.now(timezone.utc)
    )
    db.add(db_log)
    
    # Also update the daily aggregated health data for today
    today = datetime.now(timezone.utc).date()
    db_health = db.query(models.HealthData).filter(
        models.HealthData.user_id == user.id,
        models.HealthData.date == today
    ).first()
    
    if not db_health:
        db_health = models.HealthData(
            user_id=user.id,
            date=today,
            water_intake_ml=log_data.amount
        )
        db.add(db_health)
    else:
        db_health.water_intake_ml += log_data.amount
        db_health.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(db_log)
    return db_log


def get_water_log_by_id(db: Session, log_id: int):
    return db.query(models.WaterLog).filter(models.WaterLog.id == log_id).first()


def update_water_log(db: Session, db_log: models.WaterLog, log_data: schemas.WaterLogCreate):
    old_amount = db_log.amount
    old_date = db_log.timestamp.date()
    
    # Update log properties
    db_log.amount = log_data.amount
    if log_data.timestamp:
        db_log.timestamp = log_data.timestamp
    
    new_date = db_log.timestamp.date()
    amount_diff = log_data.amount - old_amount
    
    # Update aggregated health data
    if old_date == new_date:
        db_health = db.query(models.HealthData).filter(
            models.HealthData.user_id == db_log.user_id,
            models.HealthData.date == old_date
        ).first()
        if db_health:
            db_health.water_intake_ml += amount_diff
            db_health.updated_at = datetime.now(timezone.utc)
    else:
        # Subtract from old date
        db_health_old = db.query(models.HealthData).filter(
            models.HealthData.user_id == db_log.user_id,
            models.HealthData.date == old_date
        ).first()
        if db_health_old:
            db_health_old.water_intake_ml = max(0, db_health_old.water_intake_ml - old_amount)
            db_health_old.updated_at = datetime.now(timezone.utc)
            
        # Add to new date
        db_health_new = db.query(models.HealthData).filter(
            models.HealthData.user_id == db_log.user_id,
            models.HealthData.date == new_date
        ).first()
        if not db_health_new:
            db_health_new = models.HealthData(
                user_id=db_log.user_id,
                date=new_date,
                water_intake_ml=log_data.amount
            )
            db.add(db_health_new)
        else:
            db_health_new.water_intake_ml += log_data.amount
            db_health_new.updated_at = datetime.now(timezone.utc)
            
    db.commit()
    db.refresh(db_log)
    return db_log


def delete_water_log(db: Session, db_log: models.WaterLog):
    amount = db_log.amount
    log_date = db_log.timestamp.date()
    user_id = db_log.user_id
    
    # Delete the log
    db.delete(db_log)
    
    # Subtract from aggregated health data
    db_health = db.query(models.HealthData).filter(
        models.HealthData.user_id == user_id,
        models.HealthData.date == log_date
    ).first()
    if db_health:
        db_health.water_intake_ml = max(0, db_health.water_intake_ml - amount)
        db_health.updated_at = datetime.now(timezone.utc)
        
    db.commit()




