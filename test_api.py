import json
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import Base

# Detect database configuration and verify connection
engine = None
fallback_to_sqlite = False

try:
    print(f"Attempting to connect to primary database: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    # Perform a quick connection test
    with engine.connect() as conn:
        pass
    print("Successfully connected to PostgreSQL database.")
except OperationalError:
    print("PostgreSQL database is offline or not running.")
    fallback_to_sqlite = True

if fallback_to_sqlite:
    test_db_url = "sqlite:///./test_api.db"
    print(f"Falling back to local SQLite database for testing: {test_db_url}")
    settings.DATABASE_URL = test_db_url
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    # Override app configuration
    import app.database
    app.database.engine = engine
    app.database.SessionLocal = app.database.sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Reset all tables cleanly to ensure test runs are idempotent
print("Resetting database schema...")
import app.models
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Database schema reset completed.\n")

# Import TestClient and App AFTER the settings/database overrides are applied
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test payload definitions
signup_payload = {
    "email": "testuser@arcar.com",
    "password": "Test@123",
    "name": "Test User",
    "provider": "email"
}

login_payload = {
    "email": "testuser@arcar.com",
    "password": "Test@123"
}

onboarding_payload = {
    "auth": {
        "name": "Test User",
        "email": "testuser@arcar.com",
        "provider": "email"
    },
    "goals": [
        "Lose Weight",
        "Stay Active"
    ],
    "profile": {
        "dob": "1995-05-15",
        "gender": "Male",
        "height": 175,
        "weight": 75
    },
    "permissions": {
        "notifications": {
            "ai_tips": True,
            "rewards": True,
            "daily_reminder": True,
            "sleep_reminder": False,
            "activity_reminder": True,
            "challenge_updates": True,
            "hydration_reminder": True
        },
        "health_connect_connected": True
    },
    "completed_at": "2026-06-27T22:13:26.089207Z",
    "onboarding_completed": True
}

def run_tests():
    print("--- 1. Testing User Sign Up (Local Email) ---")
    response = client.post("/api/auth/signup", json=signup_payload)
    print(f"Status Code: {response.status_code}")
    auth_data = response.json()
    print(f"Tokens Issued:")
    print(f"  - Access Token: {auth_data['access_token'][:30]}...")
    print(f"  - Refresh Token: {auth_data['refresh_token'][:30]}...")
    print(f"User Data returned in Response:")
    print(json.dumps(auth_data['user'], indent=2))
    assert response.status_code == 201
    assert auth_data["user"]["email"] == signup_payload["email"]
    assert auth_data["user"]["onboarding_completed"] is False
    assert "access_token" in auth_data
    assert "refresh_token" in auth_data

    print("\n--- 2. Testing Duplicate Sign Up Prevention ---")
    response = client.post("/api/auth/signup", json=signup_payload)
    print(f"Status Code: {response.status_code} (Expected 400)")
    print(f"Error Detail: {response.json()['detail']}")
    assert response.status_code == 400

    print("\n--- 3. Testing Incorrect Password Login ---")
    bad_login = login_payload.copy()
    bad_login["password"] = "wrongpassword"
    response = client.post("/api/auth/login", json=bad_login)
    print(f"Status Code: {response.status_code} (Expected 401)")
    print(f"Error Detail: {response.json()['detail']}")
    assert response.status_code == 401

    print("\n--- 4. Testing Correct Login ---")
    response = client.post("/api/auth/login", json=login_payload)
    print(f"Status Code: {response.status_code}")
    login_data = response.json()
    print(f"Access Token: {login_data['access_token'][:30]}...")
    assert response.status_code == 200
    assert login_data["user"]["email"] == login_payload["email"]
    
    # Store refresh token for later test
    refresh_token = login_data["refresh_token"]

    print("\n--- 5. Testing Token Refresh ---")
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    print(f"Status Code: {response.status_code}")
    refresh_data = response.json()
    print(f"New Access Token: {refresh_data['access_token'][:30]}...")
    assert response.status_code == 200
    assert "access_token" in refresh_data

    print("\n--- 6. Testing User Onboarding Flow Setup ---")
    response = client.post("/api/onboarding", json=onboarding_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 201

    print("\n--- 7. Logging in again (Verifying profile & permissions are returned) ---")
    response = client.post("/api/auth/login", json=login_payload)
    print(f"Status Code: {response.status_code}")
    post_onboarding_login_data = response.json()
    print(f"User Onboarding Completed: {post_onboarding_login_data['user']['onboarding_completed']}")
    print(f"User Goals: {post_onboarding_login_data['user']['goals']}")
    print(f"User Profile details:")
    print(json.dumps(post_onboarding_login_data['user']['profile'], indent=2))
    print(f"User Permissions details:")
    print(json.dumps(post_onboarding_login_data['user']['permissions'], indent=2))
    assert response.status_code == 200
    assert post_onboarding_login_data["user"]["onboarding_completed"] is True
    assert "Lose Weight" in post_onboarding_login_data["user"]["goals"]

    # --- Social Signups and Logins ---

    print("\n--- 8. Testing Google Social Sign Up (New User) ---")
    response = client.post("/api/auth/social-signup", json={
        "provider": "google",
        "token": "mock_google_token",
        "name": "Social Google User"
    })
    print(f"Status Code: {response.status_code}")
    google_data = response.json()
    print(f"Access Token: {google_data['access_token'][:30]}...")
    print(f"User Email: {google_data['user']['email']}")
    print(f"User Name: {google_data['user']['name']}")
    assert response.status_code == 201
    assert google_data["user"]["email"] == "socialuser_google@gmail.com"
    assert google_data["user"]["provider"] == "google"

    print("\n--- 9. Testing Google Social Sign Up Duplicate Check (Should Succeed/Log In) ---")
    response = client.post("/api/auth/social-signup", json={
        "provider": "google",
        "token": "mock_google_token"
    })
    print(f"Status Code: {response.status_code} (Expected 201)")
    assert response.status_code == 201

    print("\n--- 10. Testing Google Social Login ---")
    response = client.post("/api/auth/social-login", json={
        "provider": "google",
        "token": "mock_google_token"
    })
    print(f"Status Code: {response.status_code}")
    google_login_data = response.json()
    print(f"Access Token: {google_login_data['access_token'][:30]}...")
    assert response.status_code == 200
    assert google_login_data["user"]["email"] == "socialuser_google@gmail.com"

    print("\n--- 11. Testing Apple Social Sign Up (New User) ---")
    response = client.post("/api/auth/social-signup", json={
        "provider": "apple",
        "token": "mock_apple_token",
        "name": "Social Apple User"
    })
    print(f"Status Code: {response.status_code}")
    apple_data = response.json()
    print(f"Access Token: {apple_data['access_token'][:30]}...")
    print(f"User Email: {apple_data['user']['email']}")
    assert response.status_code == 201
    assert apple_data["user"]["email"] == "socialuser_apple@icloud.com"
    assert apple_data["user"]["provider"] == "apple"

    print("\n--- 12. Testing Apple Social Login ---")
    response = client.post("/api/auth/social-login", json={
        "provider": "apple",
        "token": "mock_apple_token"
    })
    print(f"Status Code: {response.status_code}")
    apple_login_data = response.json()
    print(f"Access Token: {apple_login_data['access_token'][:30]}...")
    assert response.status_code == 200
    assert apple_login_data["user"]["email"] == "socialuser_apple@icloud.com"

    print("\n--- 13. Testing Social Login of Unregistered User (Auto Sign Up & Log In) ---")
    response = client.post("/api/auth/social-login", json={
        "provider": "google",
        "token": "mock_unregistered_token"
    })
    print(f"Status Code: {response.status_code} (Expected 200)")
    assert response.status_code == 200
    google_unregistered_data = response.json()
    assert google_unregistered_data["user"]["email"] == "unregistered_social@gmail.com"

    print("\n--- 14. Testing Forgot Password Flow (Non-existent user) ---")
    response = client.post("/api/auth/forgot-password", json={"email": "nonexistent@arcar.com"})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "exists" in response.json()["message"]

    print("\n--- 15. Testing Forgot Password Flow (Social User) ---")
    response = client.post("/api/auth/forgot-password", json={"email": "socialuser_google@gmail.com"})
    print(f"Status Code: {response.status_code} (Expected 400)")
    print(f"Response: {response.json()}")
    assert response.status_code == 400
    assert "social" in response.json()["detail"].lower()

    print("\n--- 16. Testing Forgot Password Flow (Valid Email, OTP Gen & Verification) ---")
    response = client.post("/api/auth/forgot-password", json={"email": signup_payload["email"]})
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    # Query OTP from test DB directly to simulate reading it from logs/email
    from app.database import SessionLocal
    from app.models import PasswordResetOTP
    db = SessionLocal()
    otp_record = db.query(PasswordResetOTP).filter(PasswordResetOTP.email == signup_payload["email"]).first()
    assert otp_record is not None
    otp_code = otp_record.otp
    print(f"Retrieved OTP from DB for testing: {otp_code}")
    db.close()

    # Verify invalid OTP first
    response = client.post("/api/auth/verify-otp", json={"email": signup_payload["email"], "otp": "000000"})
    print(f"Verify bad OTP status: {response.status_code} (Expected 400)")
    assert response.status_code == 400

    # Verify correct OTP
    response = client.post("/api/auth/verify-otp", json={"email": signup_payload["email"], "otp": otp_code})
    print(f"Verify correct OTP status: {response.status_code}")
    verify_data = response.json()
    assert response.status_code == 200
    assert "reset_token" in verify_data
    reset_token = verify_data["reset_token"]

    print("\n--- 17. Testing Password Reset and Login ---")
    # Reset with new password
    response = client.post("/api/auth/reset-password", json={"reset_token": reset_token, "new_password": "NewTest@123"})
    print(f"Reset Password Status: {response.status_code}")
    assert response.status_code == 200

    # Try old login (should fail)
    response = client.post("/api/auth/login", json=login_payload)
    print(f"Login with old password status: {response.status_code} (Expected 401)")
    assert response.status_code == 401

    # Try new login (should succeed)
    new_login_payload = login_payload.copy()
    new_login_payload["password"] = "NewTest@123"
    response = client.post("/api/auth/login", json=new_login_payload)
    print(f"Login with new password status: {response.status_code}")
    assert response.status_code == 200

    print("\n--- 18. Testing Health Data Sync (Multi-day logs) ---")
    sync_payload = [
        {"date": "2026-06-30", "steps": 5000, "calories": 400, "heart_rate_bpm": 70, "workouts_count": 1, "water_intake_ml": 2000, "sleep_duration_hours": 8.0},
        {"date": "2026-06-29", "steps": 6000, "calories": 500, "heart_rate_bpm": 72, "workouts_count": 1, "water_intake_ml": 2200, "sleep_duration_hours": 7.5},
        {"date": "2026-06-28", "steps": 4000, "calories": 300, "heart_rate_bpm": 68, "workouts_count": 0, "water_intake_ml": 1800, "sleep_duration_hours": 7.0},
        {"date": "2026-06-27", "steps": 8000, "calories": 600, "heart_rate_bpm": 75, "workouts_count": 2, "water_intake_ml": 2500, "sleep_duration_hours": 8.5},
        {"date": "2026-06-26", "steps": 7000, "calories": 450, "heart_rate_bpm": 71, "workouts_count": 1, "water_intake_ml": 2000, "sleep_duration_hours": 7.8},
        {"date": "2026-06-25", "steps": 5500, "calories": 380, "heart_rate_bpm": 70, "workouts_count": 1, "water_intake_ml": 1900, "sleep_duration_hours": 7.2},
        {"date": "2026-06-24", "steps": 9000, "calories": 700, "heart_rate_bpm": 80, "workouts_count": 2, "water_intake_ml": 2800, "sleep_duration_hours": 8.2}
    ]
    response = client.post(f"/api/health/sync/{signup_payload['email']}", json=sync_payload)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    sync_result = response.json()
    print(f"Sync Result Count: {len(sync_result)}")
    assert len(sync_result) == 7
    assert sync_result[0]["steps"] == 5000
    assert sync_result[0]["date"] == "2026-06-30"

    print("\n--- 19. Testing Dashboard Data Retrieval & Wellness Score Calculation ---")
    response = client.get(f"/api/dashboard/{signup_payload['email']}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    dashboard_data = response.json()
    print(f"Last Synced Date: {dashboard_data['last_synced_date']}")
    print(f"Wellness Score: {dashboard_data['wellness_score']}")
    print(f"Daily Summary: {dashboard_data['daily_summary']}")
    
    assert dashboard_data["last_synced_date"] in ("2026-06-30", date.today().isoformat())
    # Verify wellness score is computed and valid (> 0)
    assert dashboard_data["wellness_score"] > 0
    assert "water_intake_today" in dashboard_data
    assert isinstance(dashboard_data["water_intake_today"], int)
    assert "protein_today" in dashboard_data
    assert isinstance(dashboard_data["protein_today"], (int, float))
    assert "carbs_today" in dashboard_data
    assert isinstance(dashboard_data["carbs_today"], (int, float))
    assert "fat_today" in dashboard_data
    assert isinstance(dashboard_data["fat_today"], (int, float))
    # Expected: avg steps=6357, calories=475, sleep=7.74, water=2171
    # step target=10000 (score=19.07), calories target=600 (score=19.82)
    # sleep target=8.0 (score=24.19), water target=2500 (score=17.37)
    # Total score = 19.07 + 19.82 + 25.0 + 17.37 = 81.26 -> 81
    # If a record for today is also present (due to onboarding setup), wellness score may be 75 or 76
    assert dashboard_data["wellness_score"] in (81, 76, 75, 80)
 
    print("\n--- 20. Testing Combined Dashboard Sync Endpoint ---")
    sync_payload_2 = [
        {"date": "2026-07-02", "steps": 8430, "calories": 2180, "heart_rate_bpm": 68, "workouts_count": 1, "water_intake_ml": 1800, "sleep_duration_hours": 7.4},
        {"date": "2026-07-01", "steps": 9800, "calories": 2340, "heart_rate_bpm": 70, "workouts_count": 2, "water_intake_ml": 2200, "sleep_duration_hours": 8.0},
        {"date": "2026-06-30", "steps": 5120, "calories": 1950, "heart_rate_bpm": 74, "workouts_count": 0, "water_intake_ml": 1200, "sleep_duration_hours": 6.2}
    ]
    response = client.post(f"/api/dashboard/sync/{signup_payload['email']}", json=sync_payload_2)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    sync_res = response.json()
    print("Response keys:", list(sync_res.keys()))
    print("wellness_score:", sync_res["wellness_score"])
    print("daily_summary:", sync_res["daily_summary"])
    print("recommendations:", sync_res["recommendations"])
    print("ai_buddy_message:", sync_res["ai_buddy_message"])
 
    assert "wellness_score" in sync_res
    assert "daily_summary" in sync_res
    assert "recommendations" in sync_res
    assert "ai_buddy_message" in sync_res
    assert "active_subscore" in sync_res
    assert "sleep_subscore" in sync_res
    assert "nutrition_subscore" in sync_res
    assert "mindfulness_subscore" in sync_res
    assert "water_intake_today" in sync_res
    assert "goals" in sync_res
    assert isinstance(sync_res["wellness_score"], int)
    assert isinstance(sync_res["daily_summary"], str)
    assert isinstance(sync_res["recommendations"], list)
    assert isinstance(sync_res["ai_buddy_message"], str)
    assert isinstance(sync_res["active_subscore"], int)
    assert isinstance(sync_res["sleep_subscore"], int)
    assert isinstance(sync_res["nutrition_subscore"], int)
    assert isinstance(sync_res["mindfulness_subscore"], int)
    assert isinstance(sync_res["water_intake_today"], int)
    assert isinstance(sync_res["goals"], dict)
    assert "protein_today" in sync_res
    assert isinstance(sync_res["protein_today"], (int, float))
    assert "carbs_today" in sync_res
    assert isinstance(sync_res["carbs_today"], (int, float))
    assert "fat_today" in sync_res
    assert isinstance(sync_res["fat_today"], (int, float))

    print("\n--- 21. Testing Logging Water Intake (POST /api/water/log/{email}) ---")
    water_log_payload = {"amount": 250}
    response = client.post(f"/api/water/log/{signup_payload['email']}", json=water_log_payload)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    log_data = response.json()
    assert log_data["message"] == "Water intake logged successfully"
    assert log_data["amount"] == 250
    assert "timestamp" in log_data

    # Log another one
    response = client.post(f"/api/water/log/{signup_payload['email']}", json={"amount": 500})
    assert response.status_code == 200

    print("\n--- 22. Testing Retrieving Hydration History (GET /api/water/logs/{email}) ---")
    response = client.get(f"/api/water/logs/{signup_payload['email']}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    res_data = response.json()
    print("Retrieved Data:", res_data)
    assert "water_intake_today" in res_data
    assert "logs" in res_data
    assert isinstance(res_data["water_intake_today"], int)
    assert res_data["water_intake_today"] >= 750
    logs = res_data["logs"]
    assert len(logs) >= 2
    assert logs[0]["amount"] == 500
    assert logs[1]["amount"] == 250
    assert "id" in logs[0]
    log_id = logs[0]["id"]

    print("\n--- 23. Testing Water Graph API (GET /api/water/graph/{email}) ---")
    response = client.get(f"/api/water/graph/{signup_payload['email']}?period=day")
    assert response.status_code == 200
    graph_res = response.json()
    assert graph_res["period"] == "day"
    assert len(graph_res["data"]) == 24

    response = client.get(f"/api/water/graph/{signup_payload['email']}?period=week")
    assert response.status_code == 200
    graph_res = response.json()
    assert graph_res["period"] == "week"
    assert len(graph_res["data"]) == 7

    response = client.get(f"/api/water/graph/{signup_payload['email']}?period=month")
    assert response.status_code == 200
    graph_res = response.json()
    assert graph_res["period"] == "month"
    assert len(graph_res["data"]) == 30

    print("\n--- 24. Testing Updating Water Log (PUT /api/water/log/{log_id}) ---")
    response = client.put(f"/api/water/log/{log_id}", json={"amount": 600})
    assert response.status_code == 200
    update_res = response.json()
    assert update_res["amount"] == 600
    assert update_res["id"] == log_id

    # Verify updated log total in logs list
    response = client.get(f"/api/water/logs/{signup_payload['email']}")
    assert response.json()["water_intake_today"] == 850 # 250 + 600

    print("\n--- 25. Testing Deleting Water Log (DELETE /api/water/log/{log_id}) ---")
    response = client.delete(f"/api/water/log/{log_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Water log deleted successfully"

    # Verify it is deleted and total today is reduced
    response = client.get(f"/api/water/logs/{signup_payload['email']}")
    assert response.json()["water_intake_today"] == 250

    print("\n--- 26. Testing Health Metric Logging (POST /api/health/metric/{email}) ---")
    metric_payload = {
        "metric": "steps",
        "value": 10000,
        "date": (date.today() - timedelta(days=1)).isoformat()
    }
    response = client.post(f"/api/health/metric/{signup_payload['email']}", json=metric_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["metric"] == "steps"
    assert res_data["value"] == 10000.0
    # Steps metric should calculate calories burned (e.g. 10000 * 0.0006125 * weight)
    # default weight is 70 kg, so 10000 * 0.0006125 * 70 = 428.75 -> 429 kcal (or weight of signup profile, weight is 70.0 kg in signup setup)
    assert res_data["calories_burned"] is not None
    assert res_data["calories_burned"] > 0
    assert res_data["health_data"]["steps"] == 10000
    assert res_data["health_data"]["calories"] == res_data["calories_burned"]

    # Log sleep metric
    sleep_payload = {
        "metric": "sleep",
        "value": 8.5,
        "date": (date.today() - timedelta(days=1)).isoformat()
    }
    response = client.post(f"/api/health/metric/{signup_payload['email']}", json=sleep_payload)
    assert response.status_code == 200
    assert response.json()["health_data"]["sleep_duration_hours"] == 8.5

    print("\n--- 27. Testing Metric Graph API (GET /api/health/graph/{email}) ---")
    # Test period: days
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=steps&period=days")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["metric"] == "steps"
    assert graph_data["period"] == "days"
    assert len(graph_data["data"]) == 7
    assert graph_data["average"] > 0
    assert graph_data["total"] > 0
    assert "Outstanding" in graph_data["feedback"] or "Good" in graph_data["feedback"] or "below" in graph_data["feedback"]
    
    # Assert that calories_total and calories_average are calculated
    assert graph_data["calories_total"] is not None
    assert graph_data["calories_average"] is not None
    assert graph_data["calories_total"] == round(graph_data["total"] * 0.0006125 * 75.0, 1)
    assert graph_data["calories_average"] == round(graph_data["average"] * 0.0006125 * 75.0, 1)

    # Assert each data point has calories_burned calculated
    for dp in graph_data["data"]:
        assert "calories_burned" in dp
        assert dp["calories_burned"] == round(dp["value"] * 0.0006125 * 75.0, 1)

    # Test period: weeks
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=steps&period=weeks")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["metric"] == "steps"
    assert graph_data["period"] == "weeks"
    assert len(graph_data["data"]) == 4
    assert graph_data["average"] > 0
    assert graph_data["total"] > 0

    # Test period: month
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=sleep&period=month")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["metric"] == "sleep"
    assert graph_data["period"] == "month"
    assert len(graph_data["data"]) == 3
    assert graph_data["average"] > 0
    assert graph_data["total"] > 0  # sleep now has total duration calculated

    # Test period: years (should return 400 Bad Request now)
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=heart_rate&period=years")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid period. Choose from 'days', 'weeks', or 'month'."

    print("\n--- 28. Testing Data Retention Cleanup (Only storing last 3 months) ---")
    from app.database import SessionLocal
    import app.models
    
    db = SessionLocal()
    user = db.query(app.models.User).filter(app.models.User.email == signup_payload["email"]).first()
    
    # 1. Test HealthData cleanup
    old_date = date.today() - timedelta(days=120)
    db_old_health = app.models.HealthData(user_id=user.id, date=old_date, steps=5000)
    db.add(db_old_health)
    db.commit()
    
    # Verify it exists
    assert db.query(app.models.HealthData).filter(app.models.HealthData.user_id == user.id, app.models.HealthData.date == old_date).first() is not None
    
    # Trigger cleanup by logging a metric
    today_payload = {
        "metric": "steps",
        "value": 10000,
        "date": (date.today() - timedelta(days=1)).isoformat()
    }
    response = client.post(f"/api/health/metric/{signup_payload['email']}", json=today_payload)
    assert response.status_code == 200
    
    # Verify it was cleaned up
    assert db.query(app.models.HealthData).filter(app.models.HealthData.user_id == user.id, app.models.HealthData.date == old_date).first() is None
    
    # 2. Test WaterLog cleanup
    old_datetime = datetime.combine(date.today() - timedelta(days=120), datetime.min.time())
    db_old_water = app.models.WaterLog(user_id=user.id, amount=250, timestamp=old_datetime)
    db.add(db_old_water)
    db.commit()
    
    # Verify it exists
    assert db.query(app.models.WaterLog).filter(app.models.WaterLog.user_id == user.id, app.models.WaterLog.timestamp == old_datetime).first() is not None
    
    # Trigger cleanup by logging water
    water_payload = {
        "amount": 500
    }
    response = client.post(f"/api/water/log/{signup_payload['email']}", json=water_payload)
    assert response.status_code == 200
    
    # Verify it was cleaned up
    assert db.query(app.models.WaterLog).filter(app.models.WaterLog.user_id == user.id, app.models.WaterLog.timestamp == old_datetime).first() is None
    
    # 29. Testing Challenges & Leaderboards
    print("\n--- 29. Testing Challenges & Leaderboards ---")
    response = client.post("/api/auth/login", json={
        "email": signup_payload["email"],
        "password": "NewTest@123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test GET /challenges (should seed challenges if empty)
    response = client.get("/api/challenges", headers=headers)
    assert response.status_code == 200
    challenges = response.json()
    assert len(challenges) >= 5
    assert challenges[0]["id"] == "challenge_001"
    assert challenges[0]["joined"] is False
    assert challenges[0]["infoText"] is not None
    assert "5,000 steps" in challenges[0]["infoText"]

    # Test GET /challenges/{id}
    response = client.get("/api/challenges/challenge_001", headers=headers)
    assert response.status_code == 200
    challenge = response.json()
    assert challenge["title"] == "Walk 5,000 Steps"
    assert challenge["joined"] is False
    assert challenge["infoText"] is not None

    # Test POST /challenges/{id}/join (challenge_001 is auto-completed because of onboarding's 6200 steps!)
    response = client.post("/api/challenges/challenge_001/join", headers=headers)
    assert response.status_code == 200
    user_challenge = response.json()
    print("USER CHALLENGE JOINED:", user_challenge)
    assert user_challenge["challengeId"] == "challenge_001"
    assert user_challenge["completed"] is True
    assert user_challenge["currentProgress"] == 6200.0
    assert user_challenge["completedToday"] is True
    assert user_challenge["doneToday"] is True
    assert len(user_challenge["dailyHistory"]) >= 1
    assert "status" in user_challenge["dailyHistory"][0]
    assert user_challenge["dailyHistory"][0]["target"] == 5000.0

    # Verify joined in GET /challenges
    response = client.get("/api/challenges", headers=headers)
    assert response.status_code == 200
    challenges = response.json()
    assert challenges[0]["joined"] is True
    assert challenges[0]["infoText"] is None
    assert challenges[0]["completedToday"] is True
    assert challenges[0]["doneToday"] is True
    assert len(challenges[0]["dailyHistory"]) >= 1

    # Test GET /users/me/challenges/completed
    response = client.get("/api/users/me/challenges/completed", headers=headers)
    assert response.status_code == 200
    completed_challenges = response.json()
    assert len(completed_challenges) == 1
    assert completed_challenges[0]["id"] == "challenge_001"
    assert completed_challenges[0]["completedToday"] is True
    assert completed_challenges[0]["doneToday"] is True
    assert len(completed_challenges[0]["dailyHistory"]) >= 1

    # Test GET /challenges/{challengeId}/leaderboard
    response = client.get("/api/challenges/challenge_001/leaderboard", headers=headers)
    assert response.status_code == 200
    leaderboard = response.json()
    assert leaderboard["challengeId"] == "challenge_001"
    assert leaderboard["totalParticipants"] == 1
    assert leaderboard["currentUser"]["rank"] == 1
    assert leaderboard["currentUser"]["progress"] == 6200.0

    # Test POST /challenges/{id}/claim-reward
    response = client.post("/api/challenges/challenge_001/claim-reward", headers=headers)
    assert response.status_code == 200
    reward_res = response.json()
    assert reward_res["rewardClaimed"] is True
    assert reward_res["rewardPoints"] == 50

    # Test POST /challenges/{id}/leave
    response = client.post("/api/challenges/challenge_001/leave", headers=headers)
    assert response.status_code == 200

    # Test auto-updating step challenge progress from logged metrics
    print("\n--- Testing Step Challenge Auto-Sync Progress ---")
    response = client.post("/api/challenges/challenge_005/join", headers=headers)
    assert response.status_code == 200
    uc_005 = response.json()
    assert uc_005["challengeId"] == "challenge_005"
    assert uc_005["currentProgress"] == 6200.0
    assert uc_005["completed"] is False
    assert uc_005["completedToday"] is False
    assert uc_005["doneToday"] is False

    # Log 15000 steps for today (overwrites the 6200 steps today, making total steps today = 15000, and overall challenge total = 10000 + 15000 = 25000)
    metric_payload_today = {
        "metric": "steps",
        "value": 15000,
        "date": date.today().isoformat()
    }
    response = client.post(f"/api/health/metric/{signup_payload['email']}", json=metric_payload_today, headers=headers)
    assert response.status_code == 200

    # Retrieve challenges list (triggers sync)
    response = client.get("/api/challenges", headers=headers)
    assert response.status_code == 200
    challenges_after_sync = response.json()
    challenge_005_data = next(c for c in challenges_after_sync if c["id"] == "challenge_005")
    assert challenge_005_data["joined"] is True
    assert challenge_005_data["currentProgress"] == 15000.0
    print("Steps metric update correctly auto-synced to active Challenge progress!")

    # Clean up
    client.post("/api/challenges/challenge_005/leave", headers=headers)


    # --- 30. Testing Gym Check-in & Exercises API ---
    print("\n--- 30. Testing Gym Check-in & Exercises API ---")
    
    # Get Exercises List
    response = client.get("/api/gym/exercises", headers=headers)
    assert response.status_code == 200
    exercises = response.json()
    assert len(exercises) > 0
    assert any(e["name"] == "Bench Press" for e in exercises)
    print(f"Exercises available: {[e['name'] for e in exercises[:5]]}...")

    # Join Gym Check-in Challenge
    response = client.post("/api/challenges/challenge_006/join", headers=headers)
    assert response.status_code == 200
    uc_gym = response.json()
    assert uc_gym["challengeId"] == "challenge_006"
    assert uc_gym["currentProgress"] == 0.0

    # Perform Gym Check-in
    checkin_payload = {
        "qr_data": "gym_qr_branch_south_123",
        "gym_name": "Gold's Gym South Branch"
    }
    response = client.post("/api/gym/check-in", json=checkin_payload, headers=headers)
    assert response.status_code == 200
    checkin_res = response.json()
    assert checkin_res["gym_name"] == "Gold's Gym South Branch"
    assert checkin_res["check_out_time"] is None
    
    # Try checking in again (should return active session)
    response = client.post("/api/gym/check-in", json=checkin_payload, headers=headers)
    assert response.status_code == 200
    assert "Already checked in" in response.json()["message"]

    # Perform Gym Check-out with exercises list and sets
    checkout_payload = {
        "exercises": [
            {"name": "Bench Press", "sets": 4},
            {"name": "Squats", "sets": 3},
            {"name": "Treadmill Running", "sets": 2}
        ]
    }
    response = client.post("/api/gym/check-out", json=checkout_payload, headers=headers)
    assert response.status_code == 200
    checkout_res = response.json()
    assert checkout_res["check_out_time"] is not None
    assert checkout_res["calories_burned"] == 134.0
    assert "Bench Press" in checkout_res["exercises_done"]
    assert "sets" in checkout_res["exercises_done"]

    # Verify that the Gym Check-in Challenge progress automatically synced/updated!
    response = client.get("/api/challenges/challenge_006", headers=headers)
    assert response.status_code == 200
    challenge_gym = response.json()
    assert challenge_gym["joined"] is True
    assert challenge_gym["currentProgress"] == 1.0
    assert challenge_gym["completedToday"] is False
    assert challenge_gym["doneToday"] is False
    print("Gym Challenge progress automatically updated to 1.0 check-ins!")

    # Perform Gym Check-in again (should extend/reopen the session since it is on the same day!)
    response = client.post("/api/gym/check-in", json=checkin_payload, headers=headers)
    assert response.status_code == 200
    extend_res = response.json()
    assert extend_res["id"] == checkout_res["id"]
    assert extend_res["check_out_time"] is None
    assert "extended" in extend_res["message"]
    print("Re-checked in to extend session successfully!")
    
    # Check out again to close it
    response = client.post("/api/gym/check-out", json=checkout_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["check_out_time"] is not None

    # Verify the dashboard returns the latest gym session
    response = client.get(f"/api/dashboard/{signup_payload['email']}")
    assert response.status_code == 200
    dashboard_data = response.json()
    assert "latest_gym_session" in dashboard_data
    assert dashboard_data["latest_gym_session"] is not None
    assert dashboard_data["latest_gym_session"]["id"] == checkout_res["id"]
    print("Latest gym session verified on dashboard successfully!")

    # Test Auto Checkout at Midnight for old active sessions
    db_session = db
    yesterday_checkin = app.models.GymCheckIn(
        id="test-yesterday-session-id",
        user_id=1,
        qr_data="gym_qr_yesterday",
        gym_name="Yesterday Gym",
        check_in_time=datetime.now() - timedelta(days=1),
        check_out_time=None
    )
    db_session.add(yesterday_checkin)
    db_session.commit()

    # Query the dashboard, which should trigger auto-checkout
    response = client.get(f"/api/dashboard/{signup_payload['email']}")
    assert response.status_code == 200
    
    # Verify it is closed
    db_session.expire_all()
    session_in_db = db_session.query(app.models.GymCheckIn).filter(app.models.GymCheckIn.id == "test-yesterday-session-id").first()
    assert session_in_db.check_out_time is not None
    print("Old active gym session auto-checked out at midnight successfully!")
    
    # Clean up
    db_session.delete(session_in_db)
    db_session.commit()


    # Test GET /api/profile
    print("\n--- Testing GET /api/profile ---")
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == 200
    profile_details = response.json()
    assert profile_details["email"] == signup_payload["email"]
    assert profile_details["name"] == signup_payload["name"]
    assert "profile" in profile_details
    assert profile_details["profile"]["height"] == 175.0
    assert profile_details["profile"]["weight"] == 75.0
    print("GET /api/profile returned all user details successfully!")

    # Test PUT /api/profile
    print("\n--- Testing PUT /api/profile ---")
    update_payload = {
        "name": "Updated Name",
        "profile": {
            "weight": 80.0,
            "height": 180.0
        },
        "goals": ["Lose Weight", "Stay Active", "Manage Stress"],
        "permissions": {
            "notifications": {
                "sleep_reminder": True
            }
        }
    }
    response = client.put("/api/profile", json=update_payload, headers=headers)
    assert response.status_code == 200
    updated_details = response.json()
    assert updated_details["name"] == "Updated Name"
    assert updated_details["profile"]["weight"] == 80.0
    assert updated_details["profile"]["height"] == 180.0
    assert "Manage Stress" in updated_details["goals"]
    assert updated_details["permissions"]["notifications"]["sleep_reminder"] is True
    print("PUT /api/profile successfully updated user profile!")

    # --- 31. Testing Health Progress Trends API ---
    print("\n--- 31. Testing Health Progress Trends API ---")
    
    # 1. Test GET /api/health/trends/{email} with daily (default)
    response = client.get(f"/api/health/trends/{signup_payload['email']}", headers=headers)
    assert response.status_code == 200
    trends_daily = response.json()
    assert trends_daily["period"] == "daily"
    assert "averages" in trends_daily
    assert "targets" in trends_daily
    assert "history" in trends_daily
    assert "graph_data" in trends_daily
    assert len(trends_daily["history"]) == 7
    assert len(trends_daily["graph_data"]) == 7
    # Verify that first entry of history has expected metrics
    day0 = trends_daily["history"][0]
    assert "date" in day0
    assert "steps" in day0
    assert "calories" in day0
    assert "sleep" in day0
    assert "water" in day0
    assert "targets_completed" in day0
    assert day0["targets_completed"]["steps"] in ("yes", "no")
    assert day0["targets_completed"]["hydration"] in ("yes", "no")

    # 2. Test GET /api/health/trends/{email} with weekly (with pagination checks)
    response = client.get(f"/api/health/trends/{signup_payload['email']}?period=weekly&page=1&limit=10", headers=headers)
    assert response.status_code == 200
    trends_weekly = response.json()
    assert trends_weekly["period"] == "weekly"
    assert trends_weekly["page"] == 1
    assert trends_weekly["limit"] == 10
    assert trends_weekly["total_items"] == 28
    assert trends_weekly["total_pages"] == 3
    assert len(trends_weekly["history"]) == 10
    assert len(trends_weekly["graph_data"]) == 4

    # Test GET weekly with a limit covering all items
    response = client.get(f"/api/health/trends/{signup_payload['email']}?period=weekly&limit=100", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["history"]) == 28

    # 3. Test GET /api/health/trends/{email} with monthly (with pagination checks)
    response = client.get(f"/api/health/trends/{signup_payload['email']}?period=monthly&page=2&limit=20", headers=headers)
    assert response.status_code == 200
    trends_monthly = response.json()
    assert trends_monthly["period"] == "monthly"
    assert trends_monthly["page"] == 2
    assert trends_monthly["limit"] == 20
    assert trends_monthly["total_items"] == 90
    assert trends_monthly["total_pages"] == 5
    assert len(trends_monthly["history"]) == 20
    assert len(trends_monthly["graph_data"]) == 3

    # 4. Test GET /api/health/trends/{email} with invalid period
    response = client.get(f"/api/health/trends/{signup_payload['email']}?period=yearly", headers=headers)
    assert response.status_code == 400

    print("Health Progress Trends API tests passed successfully!")

    # --- 32. Testing Nutrition Intake API ---
    print("\n--- 32. Testing Nutrition Intake API ---")
    
    # Log nutrition intake
    nutrition_payload = {
        "food_name": "Chicken Breast and Rice",
        "calories": 650.5,
        "protein": 45.0,
        "fat": 12.5,
        "carbs": 70.0
    }
    response = client.post(f"/api/nutrition/log/{signup_payload['email']}", json=nutrition_payload, headers=headers)
    assert response.status_code == 200
    log_data = response.json()
    assert log_data["food_name"] == "Chicken Breast and Rice"
    assert log_data["calories"] == 650.5
    assert log_data["protein"] == 45.0
    assert log_data["fat"] == 12.5
    assert log_data["carbs"] == 70.0
    nutrition_log_id = log_data["id"]

    # Log second nutrition item
    nutrition_payload_2 = {
        "food_name": "Whey Protein Shake",
        "calories": 150.0,
        "protein": 30.0,
        "fat": 1.5,
        "carbs": 3.0
    }
    response = client.post(f"/api/nutrition/log/{signup_payload['email']}", json=nutrition_payload_2, headers=headers)
    assert response.status_code == 200

    # Get nutrition logs
    response = client.get(f"/api/nutrition/logs/{signup_payload['email']}", headers=headers)
    assert response.status_code == 200
    history = response.json()
    assert history["calories_today"] == 800.5
    assert history["protein_today"] == 75.0
    assert history["fat_today"] == 14.0
    assert history["carbs_today"] == 73.0
    assert len(history["logs"]) >= 2
    assert history["logs"][0]["food_name"] == "Whey Protein Shake"

    # Get nutrition graph
    response = client.get(f"/api/nutrition/graph/{signup_payload['email']}?period=week", headers=headers)
    assert response.status_code == 200
    graph = response.json()
    assert graph["period"] == "week"
    assert len(graph["data"]) == 7

    # Update nutrition log
    update_payload = {
        "food_name": "Chicken Breast, Rice & Broccoli",
        "calories": 700.0,
        "protein": 50.0,
        "fat": 13.0,
        "carbs": 75.0
    }
    response = client.put(f"/api/nutrition/log/{nutrition_log_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["food_name"] == "Chicken Breast, Rice & Broccoli"

    # Re-verify totals
    response = client.get(f"/api/nutrition/logs/{signup_payload['email']}", headers=headers)
    assert response.json()["calories_today"] == 850.0
    assert response.json()["protein_today"] == 80.0

    # Delete nutrition log
    response = client.delete(f"/api/nutrition/log/{nutrition_log_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Nutrition log deleted successfully"

    # Re-verify totals after deletion
    response = client.get(f"/api/nutrition/logs/{signup_payload['email']}", headers=headers)
    assert response.json()["calories_today"] == 150.0

    print("Nutrition Intake API tests passed successfully!")

    db.close()

    print("\nALL AUTHENTICATION, OTP, HEALTH, DASHBOARD, HYDRATION, NUTRITION, GRAPH, AND GYM/CHALLENGE TESTS PASSED SUCCESSFULLY!")



if __name__ == "__main__":
    run_tests()


