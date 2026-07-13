from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Optional

from app.database import get_db
from app import models, schemas, security, crud

router = APIRouter(tags=["Challenges"])
security_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme), db: Session = Depends(get_db)) -> models.User:
    token = credentials.credentials
    payload = security.decode_token(token)
    if "error" in payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials / Token invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload["sub"]
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def seed_challenges_if_empty(db: Session):
    if db.query(models.Challenge).count() == 0:
        now = datetime.now(timezone.utc)
        # Create some default challenges
        default_challenges = [
            models.Challenge(
                id="challenge_001",
                title="Walk 5,000 Steps",
                shortDescription="Kickstart your activity today",
                description="Get moving and hit 5,000 steps today to stay active.",
                infoText="To complete this challenge, you need to walk at least 5,000 steps within a single day. Make sure your Health Connect or step tracker is synced! Points will be awarded instantly upon reaching the goal.",
                category="Daily",
                challengeType="steps",
                difficulty="EASY",
                targetValue=5000.0,
                unit="steps",
                rewardPoints=50,
                rewardBadge="badge_daily_5k",
                bannerImage="https://api.prabhash.site/static/images/challenges/steps_5k.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            ),
            models.Challenge(
                id="challenge_002",
                title="Walk 10,000 Steps",
                shortDescription="The gold standard of daily steps",
                description="Challenge yourself to reach the healthy milestone of 10,000 steps.",
                infoText="Reach the 10,000 steps daily milestone. Maintain a steady pace throughout the day to reach this healthy target. Highly recommended for improving cardiovascular fitness and endurance.",
                category="Daily",
                challengeType="steps",
                difficulty="MEDIUM",
                targetValue=10000.0,
                unit="steps",
                rewardPoints=100,
                rewardBadge="badge_daily_10k",
                bannerImage="https://api.prabhash.site/static/images/challenges/steps_10k.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            ),
            models.Challenge(
                id="challenge_003",
                title="Drink 2L Water",
                shortDescription="Stay hydrated throughout the day",
                description="Log and drink at least 2 liters (2000 ml) of water today.",
                infoText="Log your water intake throughout the day. Drinking 2L (2000 ml) of water helps you stay energized and hydrated. Keep tracking in your water log to fulfill the challenge.",
                category="Daily",
                challengeType="water",
                difficulty="EASY",
                targetValue=2000.0,
                unit="ml",
                rewardPoints=40,
                rewardBadge="badge_hydrate_2l",
                bannerImage="https://api.prabhash.site/static/images/challenges/water_2l.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            ),
            models.Challenge(
                id="challenge_004",
                title="Sleep 8 Hours",
                shortDescription="Prioritize rest and recovery",
                description="Get at least 8 hours of sleep tonight to improve cognitive function.",
                infoText="Track your sleep duration. Logging 8 hours of sleep supports muscle recovery, boosts immune system, and guarantees mental clarity for the next day.",
                category="Daily",
                challengeType="sleep_duration",
                difficulty="MEDIUM",
                targetValue=8.0,
                unit="hours",
                rewardPoints=60,
                rewardBadge="badge_sleep_8h",
                bannerImage="https://api.prabhash.site/static/images/challenges/sleep_8h.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            ),
            models.Challenge(
                id="challenge_005",
                title="Walk 70,000 Steps",
                shortDescription="Consistent weekly activity",
                description="Accumulate 70,000 steps over 7 days to maintain strong cardiovascular health.",
                infoText="Accumulate 70,000 steps over a 7-day period. Consistent daily walking is key to completing this weekly challenge. Ensure steps are synced from Health Connect daily.",
                category="Weekly",
                challengeType="steps",
                difficulty="HARD",
                targetValue=70000.0,
                unit="steps",
                rewardPoints=300,
                rewardBadge="badge_weekly_70k",
                bannerImage="https://api.prabhash.site/static/images/challenges/weekly_70k.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            ),
            models.Challenge(
                id="challenge_006",
                title="Gym Check-in Challenge",
                shortDescription="Visit the gym consistently",
                description="Check-in to the gym and scan the QR code to complete workouts.",
                infoText="Check-in and checkout at the gym 5 times. Scan the QR code at your gym to check-in, and select the exercises you performed during check-out.",
                category="Fitness",
                challengeType="gym_check_in",
                difficulty="MEDIUM",
                targetValue=5.0,
                unit="count",
                rewardPoints=200,
                rewardBadge="badge_gym_5",
                bannerImage="https://api.prabhash.site/static/images/challenges/gym_checkin.png",
                startDate=now,
                endDate=now + timedelta(days=365),
                status="ACTIVE",
                participantsCount=0,
                createdAt=now,
                updatedAt=now
            )
        ]
        for c in default_challenges:
            db.add(c)
        db.commit()


def seed_exercises_if_empty(db: Session):
    if db.query(models.Exercise).count() == 0:
        exercises = [
            models.Exercise(name="Bench Press", category="Strength"),
            models.Exercise(name="Squats", category="Strength"),
            models.Exercise(name="Deadlift", category="Strength"),
            models.Exercise(name="Treadmill Running", category="Cardio"),
            models.Exercise(name="Bicep Curls", category="Strength"),
            models.Exercise(name="Lat Pulldown", category="Strength"),
            models.Exercise(name="Shoulder Press", category="Strength"),
            models.Exercise(name="Leg Press", category="Strength"),
            models.Exercise(name="Dumbbell Flyes", category="Strength"),
            models.Exercise(name="Plank", category="Core"),
            models.Exercise(name="Yoga", category="Flexibility"),
            models.Exercise(name="HIIT", category="Cardio"),
        ]
        for e in exercises:
            db.add(e)
        db.commit()


def sync_user_challenges_progress(db: Session, user_id: int):
    # Fetch all active user challenges
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == user_id,
        models.UserChallenge.completed == False
    ).all()
    
    for uc in user_challenges:
        challenge = uc.challenge
        if not challenge:
            continue
            
        start_date = max(challenge.startDate.date(), uc.joinedAt.date())
        end_date = challenge.endDate.date()
        
        progress = 0.0
        
        # Calculate progress based on challenge type
        if challenge.challengeType == "steps":
            # Sum steps in the period
            steps_sum = db.query(func.sum(models.HealthData.steps)).filter(
                models.HealthData.user_id == user_id,
                models.HealthData.date >= start_date,
                models.HealthData.date <= end_date
            ).scalar()
            progress = float(steps_sum or 0)
            
        elif challenge.challengeType == "water":
            # Sum water in the period
            water_sum = db.query(func.sum(models.HealthData.water_intake_ml)).filter(
                models.HealthData.user_id == user_id,
                models.HealthData.date >= start_date,
                models.HealthData.date <= end_date
            ).scalar()
            progress = float(water_sum or 0)
            
        elif challenge.challengeType == "sleep_duration":
            # Sum sleep duration
            sleep_sum = db.query(func.sum(models.HealthData.sleep_duration_hours)).filter(
                models.HealthData.user_id == user_id,
                models.HealthData.date >= start_date,
                models.HealthData.date <= end_date
            ).scalar()
            progress = float(sleep_sum or 0)
            
        elif challenge.challengeType == "gym_check_in":
            # Count completed check-ins (where check_out_time is within the period)
            check_ins_count = db.query(models.GymCheckIn).filter(
                models.GymCheckIn.user_id == user_id,
                models.GymCheckIn.check_out_time != None,
                func.date(models.GymCheckIn.check_in_time) >= start_date,
                func.date(models.GymCheckIn.check_in_time) <= end_date
            ).count()
            progress = float(check_ins_count)
            
        else:
            # Keep existing progress
            continue
            
        # Update progress
        uc.currentProgress = progress
        uc.progressPercentage = min(100.0, round((uc.currentProgress / challenge.targetValue) * 100.0, 1))
        
        if uc.currentProgress >= challenge.targetValue:
            uc.completed = True
            uc.completedAt = datetime.now(timezone.utc)
            
    db.commit()

def populate_user_challenge_history(db: Session, uc: models.UserChallenge) -> dict:
    """
    Populates completedToday and dailyHistory for a UserChallenge.
    """
    challenge = uc.challenge
    if not challenge:
        return {
            "id": uc.id,
            "userId": uc.user_id,
            "challengeId": uc.challenge_id,
            "joinedAt": uc.joinedAt,
            "currentProgress": uc.currentProgress,
            "progressPercentage": uc.progressPercentage,
            "completed": uc.completed,
            "rewardClaimed": uc.rewardClaimed,
            "completedAt": uc.completedAt,
            "completedToday": False,
            "doneToday": False,
            "dailyHistory": []
        }
        
    start_date = challenge.startDate.date()
    end_date = challenge.endDate.date()
    today = datetime.now(timezone.utc).date()
    
    # Restrict tracking to the challenge period up to today
    track_start = max(start_date, uc.joinedAt.date())
    track_end = min(end_date, today)
    
    # Calculate daily target
    duration_days = max(1, (end_date - start_date).days)
    if challenge.challengeType == "gym_check_in":
        daily_target = 1.0
    elif challenge.category == "Daily":
        daily_target = challenge.targetValue
    elif challenge.category == "Weekly":
        daily_target = challenge.targetValue / 7.0
    else:
        daily_target = challenge.targetValue / duration_days
        
    completed_today = False
    if uc.completed and uc.completedAt and uc.completedAt.date() == today:
        completed_today = True
        
    daily_history = []
    
    if track_start <= track_end:
        current_date = track_start
        dates = []
        while current_date <= track_end:
            dates.append(current_date)
            current_date += timedelta(days=1)
            
        for d in dates:
            progress = 0.0
            if challenge.challengeType == "steps":
                progress = db.query(func.sum(models.HealthData.steps)).filter(
                    models.HealthData.user_id == uc.user_id,
                    models.HealthData.date == d
                ).scalar() or 0.0
            elif challenge.challengeType == "water":
                progress = db.query(func.sum(models.HealthData.water_intake_ml)).filter(
                    models.HealthData.user_id == uc.user_id,
                    models.HealthData.date == d
                ).scalar() or 0.0
            elif challenge.challengeType == "sleep_duration":
                progress = db.query(func.sum(models.HealthData.sleep_duration_hours)).filter(
                    models.HealthData.user_id == uc.user_id,
                    models.HealthData.date == d
                ).scalar() or 0.0
            elif challenge.challengeType == "gym_check_in":
                progress = db.query(models.GymCheckIn).filter(
                    models.GymCheckIn.user_id == uc.user_id,
                    models.GymCheckIn.check_out_time != None,
                    func.date(models.GymCheckIn.check_in_time) == d
                ).count()
                
            progress = float(progress)
            
            # Status check
            if progress >= daily_target:
                status_str = "completed"
            elif d == today:
                status_str = "in_progress"
            else:
                status_str = "missed"
                
            if challenge.category == "Daily" and d == today and progress >= daily_target:
                completed_today = True
                
            daily_history.append({
                "date": d.isoformat(),
                "status": status_str,
                "progress": progress,
                "target": float(daily_target)
            })
            
    return {
        "id": uc.id,
        "userId": uc.user_id,
        "challengeId": uc.challenge_id,
        "joinedAt": uc.joinedAt,
        "currentProgress": uc.currentProgress,
        "progressPercentage": uc.progressPercentage,
        "completed": uc.completed,
        "rewardClaimed": uc.rewardClaimed,
        "completedAt": uc.completedAt,
        "completedToday": completed_today,
        "doneToday": completed_today,
        "dailyHistory": daily_history
    }


def recalculate_leaderboard_ranks(db: Session, challenge_id: str):
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.challenge_id == challenge_id
    ).all()
    
    # Tie-breaker logic: 
    # 1. completed status (completed first)
    # 2. current progress (descending)
    # 3. completion time (earliest completed first)
    def sort_key(uc):
        comp_time = uc.completedAt.timestamp() if (uc.completed and uc.completedAt) else 9999999999
        return (-int(uc.completed), -uc.currentProgress, comp_time)
        
    sorted_ucs = sorted(user_challenges, key=sort_key)
    total_participants = len(sorted_ucs)
    
    for i, uc in enumerate(sorted_ucs):
        rank = i + 1
        percentile = round(((total_participants - rank) / total_participants) * 100, 1) if total_participants > 0 else 100.0
        
        entry = db.query(models.Leaderboard).filter(
            models.Leaderboard.challengeId == challenge_id,
            models.Leaderboard.userId == uc.user_id
        ).first()
        if not entry:
            entry = models.Leaderboard(
                id=str(uuid.uuid4()),
                challengeId=challenge_id,
                userId=uc.user_id
            )
            db.add(entry)
            
        entry.rank = rank
        entry.progress = uc.currentProgress
        entry.percentile = percentile
        entry.completedAt = uc.completedAt
        entry.lastUpdated = datetime.now(timezone.utc)
        
    db.commit()


# --- API ENDPOINTS ---

@router.get("/challenges", response_model=List[schemas.ChallengeResponse])
def get_challenges(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. ACTIVE)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve all challenges available in the system.
    Supports filtering by category and status. Includes inline user-specific status
    (joined, completed, and current progress) if the user is authenticated.
    """
    seed_challenges_if_empty(db)
    sync_user_challenges_progress(db, current_user.id)
    
    query = db.query(models.Challenge)
    if category:
        query = query.filter(models.Challenge.category == category)
    if status:
        query = query.filter(models.Challenge.status == status)
        
    challenges = query.order_by(models.Challenge.id.asc()).all()
    
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id
    ).all()
    user_challenge_map = {uc.challenge_id: uc for uc in user_challenges}
    
    response = []
    for c in challenges:
        uc = user_challenge_map.get(c.id)
        joined = uc is not None
        completed = uc.completed if uc else False
        progress = uc.currentProgress if uc else 0.0
        
        completed_today = False
        daily_history = []
        if uc:
            history_data = populate_user_challenge_history(db, uc)
            completed_today = history_data["completedToday"]
            daily_history = history_data["dailyHistory"]
            
        response.append(schemas.ChallengeResponse(
            id=c.id,
            title=c.title,
            shortDescription=c.shortDescription,
            description=c.description,
            infoText=c.infoText if not joined else None,
            category=c.category,
            challengeType=c.challengeType,
            difficulty=c.difficulty,
            targetValue=c.targetValue,
            unit=c.unit,
            rewardPoints=c.rewardPoints,
            rewardBadge=c.rewardBadge,
            bannerImage=c.bannerImage,
            participantsCount=c.participantsCount,
            startDate=c.startDate,
            endDate=c.endDate,
            status=c.status,
            createdAt=c.createdAt,
            updatedAt=c.updatedAt,
            joined=joined,
            completed=completed,
            currentProgress=progress,
            completedToday=completed_today,
            doneToday=completed_today,
            dailyHistory=daily_history
        ))
    return response


@router.get("/challenges/{id}", response_model=schemas.ChallengeResponse)
def get_challenge(
    id: str = Path(..., description="The challenge UUID or ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve detailed configuration and parameters of a single challenge by its ID.
    Includes the user's current progress and participation status.
    """
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {id} not found."
        )
        
    sync_user_challenges_progress(db, current_user.id)
    
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    completed_today = False
    daily_history = []
    if uc:
        history_data = populate_user_challenge_history(db, uc)
        completed_today = history_data["completedToday"]
        daily_history = history_data["dailyHistory"]
        
    return schemas.ChallengeResponse(
        id=challenge.id,
        title=challenge.title,
        shortDescription=challenge.shortDescription,
        description=challenge.description,
        infoText=challenge.infoText if (uc is None) else None,
        category=challenge.category,
        challengeType=challenge.challengeType,
        difficulty=challenge.difficulty,
        targetValue=challenge.targetValue,
        unit=challenge.unit,
        rewardPoints=challenge.rewardPoints,
        rewardBadge=challenge.rewardBadge,
        bannerImage=challenge.bannerImage,
        participantsCount=challenge.participantsCount,
        startDate=challenge.startDate,
        endDate=challenge.endDate,
        status=challenge.status,
        createdAt=challenge.createdAt,
        updatedAt=challenge.updatedAt,
        joined=uc is not None,
        completed=uc.completed if uc else False,
        currentProgress=uc.currentProgress if uc else 0.0,
        completedToday=completed_today,
        doneToday=completed_today,
        dailyHistory=daily_history
    )


@router.post("/challenges/{id}/join", response_model=schemas.UserChallengeResponse)
def join_challenge(
    id: str = Path(..., description="The challenge ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Join a specific challenge.
    Increments the participant count and adds the user to the challenge's active leaderboard.
    """
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {id} not found."
        )
        
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if uc:
        return populate_user_challenge_history(db, uc)
        
    uc = models.UserChallenge(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        challenge_id=id,
        currentProgress=0.0,
        progressPercentage=0.0,
        completed=False,
        rewardClaimed=False
    )
    
    challenge.participantsCount += 1
    db.add(uc)
    db.commit()
    db.refresh(uc)
    
    # Leaderboard record
    leaderboard_entry = db.query(models.Leaderboard).filter(
        models.Leaderboard.challengeId == id,
        models.Leaderboard.userId == current_user.id
    ).first()
    if not leaderboard_entry:
        leaderboard_entry = models.Leaderboard(
            id=str(uuid.uuid4()),
            challengeId=id,
            userId=current_user.id,
            progress=0.0,
            percentile=100.0,
            rank=None
        )
        db.add(leaderboard_entry)
        db.commit()
        
    sync_user_challenges_progress(db, current_user.id)
    db.refresh(uc)
        
    recalculate_leaderboard_ranks(db, id)
    return populate_user_challenge_history(db, uc)


@router.post("/challenges/{id}/leave")
def leave_challenge(
    id: str = Path(..., description="The challenge ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Opt-out/leave a specific challenge.
    Decrements the participant count and removes the user from the challenge leaderboard.
    """
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if not uc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not joined in this challenge."
        )
        
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    if challenge:
        challenge.participantsCount = max(0, challenge.participantsCount - 1)
        
    db.query(models.Leaderboard).filter(
        models.Leaderboard.challengeId == id,
        models.Leaderboard.userId == current_user.id
    ).delete()
    
    db.delete(uc)
    db.commit()
    
    recalculate_leaderboard_ranks(db, id)
    return {"message": "Successfully left the challenge."}


@router.get("/users/me/challenges", response_model=List[schemas.ChallengeResponse])
def get_my_challenges(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve all challenges that the authenticated user has joined.
    """
    sync_user_challenges_progress(db, current_user.id)
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id
    ).all()
    
    response = []
    for uc in user_challenges:
        c = uc.challenge
        if c:
            history_data = populate_user_challenge_history(db, uc)
            response.append(schemas.ChallengeResponse(
                id=c.id,
                title=c.title,
                shortDescription=c.shortDescription,
                description=c.description,
                infoText=None,
                category=c.category,
                challengeType=c.challengeType,
                difficulty=c.difficulty,
                targetValue=c.targetValue,
                unit=c.unit,
                rewardPoints=c.rewardPoints,
                rewardBadge=c.rewardBadge,
                bannerImage=c.bannerImage,
                participantsCount=c.participantsCount,
                startDate=c.startDate,
                endDate=c.endDate,
                status=c.status,
                createdAt=c.createdAt,
                updatedAt=c.updatedAt,
                joined=True,
                completed=uc.completed,
                currentProgress=uc.currentProgress,
                completedToday=history_data["completedToday"],
                doneToday=history_data["doneToday"],
                dailyHistory=history_data["dailyHistory"]
            ))
    return response


@router.get("/users/me/challenges/active", response_model=List[schemas.ChallengeResponse])
def get_my_active_challenges(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve all currently active (joined but not completed) challenges for the authenticated user.
    """
    sync_user_challenges_progress(db, current_user.id)
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.completed == False
    ).all()
    
    response = []
    for uc in user_challenges:
        c = uc.challenge
        if c:
            history_data = populate_user_challenge_history(db, uc)
            response.append(schemas.ChallengeResponse(
                id=c.id,
                title=c.title,
                shortDescription=c.shortDescription,
                description=c.description,
                infoText=None,
                category=c.category,
                challengeType=c.challengeType,
                difficulty=c.difficulty,
                targetValue=c.targetValue,
                unit=c.unit,
                rewardPoints=c.rewardPoints,
                rewardBadge=c.rewardBadge,
                bannerImage=c.bannerImage,
                participantsCount=c.participantsCount,
                startDate=c.startDate,
                endDate=c.endDate,
                status=c.status,
                createdAt=c.createdAt,
                updatedAt=c.updatedAt,
                joined=True,
                completed=False,
                currentProgress=uc.currentProgress,
                completedToday=history_data["completedToday"],
                doneToday=history_data["doneToday"],
                dailyHistory=history_data["dailyHistory"]
            ))
    return response


@router.get("/users/me/challenges/completed", response_model=List[schemas.ChallengeResponse])
def get_my_completed_challenges(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve all completed challenges for the authenticated user.
    """
    sync_user_challenges_progress(db, current_user.id)
    user_challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.completed == True
    ).all()
    
    response = []
    for uc in user_challenges:
        c = uc.challenge
        if c:
            history_data = populate_user_challenge_history(db, uc)
            response.append(schemas.ChallengeResponse(
                id=c.id,
                title=c.title,
                shortDescription=c.shortDescription,
                description=c.description,
                infoText=None,
                category=c.category,
                challengeType=c.challengeType,
                difficulty=c.difficulty,
                targetValue=c.targetValue,
                unit=c.unit,
                rewardPoints=c.rewardPoints,
                rewardBadge=c.rewardBadge,
                bannerImage=c.bannerImage,
                participantsCount=c.participantsCount,
                startDate=c.startDate,
                endDate=c.endDate,
                status=c.status,
                createdAt=c.createdAt,
                updatedAt=c.updatedAt,
                joined=True,
                completed=True,
                currentProgress=uc.currentProgress,
                completedToday=history_data["completedToday"],
                doneToday=history_data["doneToday"],
                dailyHistory=history_data["dailyHistory"]
            ))
    return response


@router.post("/challenges/{id}/progress", response_model=schemas.UserChallengeResponse)
def update_challenge_progress(
    id: str = Path(..., description="The challenge ID"),
    req: schemas.ProgressSubmitRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update the user's progress value for a joined challenge.
    Automatically calculates completion percentage, marks the challenge as completed if the target value is met,
    and updates the leaderboard rankings.
    """
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if not uc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not joined in this challenge."
        )
        
    challenge = uc.challenge
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge details not found."
        )
        
    uc.currentProgress = req.progress
    uc.progressPercentage = min(100.0, round((uc.currentProgress / challenge.targetValue) * 100.0, 1))
    
    if uc.currentProgress >= challenge.targetValue:
        if not uc.completed:
            uc.completed = True
            uc.completedAt = datetime.now(timezone.utc)
    else:
        uc.completed = False
        uc.completedAt = None
        
    db.commit()
    db.refresh(uc)
    
    recalculate_leaderboard_ranks(db, id)
    return populate_user_challenge_history(db, uc)


@router.post("/challenges/{id}/claim-reward", response_model=schemas.RewardClaimResponse)
def claim_challenge_reward(
    id: str = Path(..., description="The challenge ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Claim the reward points and badges associated with a successfully completed challenge.
    """
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if not uc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have not joined this challenge."
        )
        
    if not uc.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge is not completed yet."
        )
        
    if uc.rewardClaimed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reward has already been claimed."
        )
        
    uc.rewardClaimed = True
    db.commit()
    
    challenge = uc.challenge
    return schemas.RewardClaimResponse(
        message="Reward claimed successfully",
        rewardPoints=challenge.rewardPoints,
        rewardBadge=challenge.rewardBadge,
        rewardClaimed=True
    )


@router.get("/challenges/{challengeId}/leaderboard", response_model=schemas.LeaderboardResponse)
def get_challenge_leaderboard(
    challengeId: str = Path(..., description="The challenge ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, description="Limit per page"),
    leaderboardType: str = Query("GLOBAL", description="Leaderboard type: GLOBAL, WEEKLY, MONTHLY, ALL_TIME"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve the ranked leaderboard list for a specific challenge.
    Includes pagination, overall participant counts, and the current user's summary (rank and percentile).
    """
    challenge = db.query(models.Challenge).filter(models.Challenge.id == challengeId).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with ID {challengeId} not found."
        )
        
    recalculate_leaderboard_ranks(db, challengeId)
    
    query = db.query(models.Leaderboard).filter(
        models.Leaderboard.challengeId == challengeId
    ).order_by(models.Leaderboard.rank.asc())
    
    total_participants = query.count()
    
    offset = (page - 1) * limit
    leaderboard_entries = query.offset(offset).limit(limit).all()
    
    curr_user_entry = db.query(models.Leaderboard).filter(
        models.Leaderboard.challengeId == challengeId,
        models.Leaderboard.userId == current_user.id
    ).first()
    
    curr_user_data = None
    if curr_user_entry:
        curr_user_data = schemas.CurrentUserLeaderboard(
            rank=curr_user_entry.rank or 0,
            progress=curr_user_entry.progress,
            percentile=curr_user_entry.percentile
        )
        
    leaders = []
    for entry in leaderboard_entries:
        user_name = entry.user.name if entry.user else "Anonymous"
        leaders.append(schemas.LeaderboardUser(
            rank=entry.rank or 0,
            userId=str(entry.userId),
            name=user_name,
            progress=entry.progress
        ))
        
    return schemas.LeaderboardResponse(
        challengeId=challengeId,
        leaderboardType=leaderboardType.upper(),
        totalParticipants=total_participants,
        currentUser=curr_user_data,
        leaders=leaders
    )


# --- GYM ENDPOINTS ---

@router.get("/gym/exercises", response_model=List[schemas.ExerciseResponse])
def get_exercises(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a list of all exercises available in the system for user selection.
    """
    seed_exercises_if_empty(db)
    return db.query(models.Exercise).order_by(models.Exercise.name.asc()).all()


@router.post("/gym/check-in", response_model=schemas.GymCheckInResponse)
def gym_check_in(
    req: schemas.GymCheckInRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check-in to a gym by scanning a QR code.
    If the user already has an active check-in session, that session is returned.
    """
    # Check for active check-in (where check_out_time is null)
    active_session = db.query(models.GymCheckIn).filter(
        models.GymCheckIn.user_id == current_user.id,
        models.GymCheckIn.check_out_time == None
    ).first()
    
    if active_session:
        return schemas.GymCheckInResponse(
            id=active_session.id,
            userId=active_session.user_id,
            qr_data=active_session.qr_data,
            gym_name=active_session.gym_name,
            check_in_time=active_session.check_in_time,
            check_out_time=active_session.check_out_time,
            exercises_done=active_session.exercises_done,
            calories_burned=active_session.calories_burned,
            message="Already checked in. Active session returned."
        )
        
    # Check if there is a recently checked-out session on the same day to extend/reopen it
    today = datetime.now(timezone.utc).date()
    recent_session = db.query(models.GymCheckIn).filter(
        models.GymCheckIn.user_id == current_user.id,
        models.GymCheckIn.check_out_time != None,
        func.date(models.GymCheckIn.check_in_time) == today
    ).order_by(models.GymCheckIn.check_out_time.desc()).first()
    
    if recent_session:
        # Extend the session by clearing check_out_time
        recent_session.check_out_time = None
        db.commit()
        db.refresh(recent_session)
        return schemas.GymCheckInResponse(
            id=recent_session.id,
            userId=recent_session.user_id,
            qr_data=recent_session.qr_data,
            gym_name=recent_session.gym_name,
            check_in_time=recent_session.check_in_time,
            check_out_time=recent_session.check_out_time,
            exercises_done=recent_session.exercises_done,
            calories_burned=recent_session.calories_burned,
            message="Gym check-in extended. Reopened recent session."
        )
        
    session = models.GymCheckIn(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        qr_data=req.qr_data,
        gym_name=req.gym_name,
        check_in_time=datetime.now(timezone.utc),
        check_out_time=None,
        exercises_done=None,
        calories_burned=0.0
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return schemas.GymCheckInResponse(
        id=session.id,
        userId=session.user_id,
        qr_data=session.qr_data,
        gym_name=session.gym_name,
        check_in_time=session.check_in_time,
        check_out_time=session.check_out_time,
        exercises_done=session.exercises_done,
        calories_burned=session.calories_burned,
        message="Gym check-in successful."
    )


@router.post("/gym/check-out", response_model=schemas.GymCheckInResponse)
def gym_check_out(
    req: schemas.GymCheckOutRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check-out of the gym and submit the list of exercises performed.
    Automatically updates the user's progress on active Gym Check-in challenges.
    """
    import json
    
    active_session = db.query(models.GymCheckIn).filter(
        models.GymCheckIn.user_id == current_user.id,
        models.GymCheckIn.check_out_time == None
    ).first()
    
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active gym check-in session found."
        )
        
    # Calorie calculation logic based on sets and categories, adjusted by user weight and height
    has_profile = (
        current_user.profile is not None
        and current_user.profile.weight is not None
        and current_user.profile.height is not None
    )
    
    total_calories = 0.0
    serialized_exercises = []
    
    if has_profile:
        weight = current_user.profile.weight
        height = current_user.profile.height
        factor = (weight / 75.0) * (height / 175.0)
        
        for ex_input in req.exercises:
            sets = ex_input.sets
            name_lower = ex_input.name.lower()
            
            # Calculate calories based on category keywords
            if any(c in name_lower for c in ["running", "treadmill", "hiit"]):
                kcal_per_set = 25.0
            elif any(s in name_lower for s in ["plank", "core"]):
                kcal_per_set = 10.0
            elif "yoga" in name_lower:
                kcal_per_set = 8.0
            else:
                # Strength default
                kcal_per_set = 12.0
                
            base_calories = sets * kcal_per_set
            calories_burned = round(base_calories * factor, 1)
            total_calories += calories_burned
            
            serialized_exercises.append({
                "name": ex_input.name,
                "sets": sets,
                "calories_burned": calories_burned
            })
    else:
        # Don't calculate if required details are not present
        for ex_input in req.exercises:
            serialized_exercises.append({
                "name": ex_input.name,
                "sets": ex_input.sets,
                "calories_burned": 0.0
            })
            
    active_session.check_out_time = datetime.now(timezone.utc)
    active_session.exercises_done = json.dumps(serialized_exercises)
    active_session.calories_burned = total_calories
    
    # Also update the daily aggregated health data for today
    today = datetime.now(timezone.utc).date()
    db_health = db.query(models.HealthData).filter(
        models.HealthData.user_id == current_user.id,
        models.HealthData.date == today
    ).first()
    
    if not db_health:
        db_health = models.HealthData(
            user_id=current_user.id,
            date=today,
            calories=total_calories
        )
        db.add(db_health)
    else:
        db_health.calories = (db_health.calories or 0.0) + total_calories
        db_health.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(active_session)
    
    # Trigger challenge progress sync
    sync_user_challenges_progress(db, current_user.id)
    
    return schemas.GymCheckInResponse(
        id=active_session.id,
        userId=active_session.user_id,
        qr_data=active_session.qr_data,
        gym_name=active_session.gym_name,
        check_in_time=active_session.check_in_time,
        check_out_time=active_session.check_out_time,
        exercises_done=active_session.exercises_done,
        calories_burned=active_session.calories_burned,
        message="Gym check-out successful."
    )


@router.get("/profile", response_model=schemas.UserDetailResponse, tags=["User Profile"], summary="Retrieve Authenticated User Profile Details")
def get_profile(
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves the complete profile, goal list, and permissions of the currently authenticated user.
    """
    return crud.get_user_auth_details(current_user)


@router.put("/profile", response_model=schemas.UserDetailResponse, tags=["User Profile"], summary="Update User Profile Details")
def update_profile(
    data: schemas.ProfileUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Updates the authenticated user's name, profile metrics (dob, gender, height, weight),
    wellness goals, or permissions selectively.
    """
    updated_user = crud.update_user_profile(db=db, user=current_user, data=data)
    return crud.get_user_auth_details(updated_user)
