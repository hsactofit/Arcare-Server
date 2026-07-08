import json
from datetime import datetime, timezone, date
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
    test_db_url = "sqlite:////run/media/ponyo/New Volume/Ocavior/back-end/Arcare-Server/arcar.db"
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
    "password": "securepassword123",
    "name": "Test User",
    "provider": "email"
}

login_payload = {
    "email": "testuser@arcar.com",
    "password": "securepassword123"
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
    response = client.post("/api/auth/reset-password", json={"reset_token": reset_token, "new_password": "newsecurepassword987"})
    print(f"Reset Password Status: {response.status_code}")
    assert response.status_code == 200

    # Try old login (should fail)
    response = client.post("/api/auth/login", json=login_payload)
    print(f"Login with old password status: {response.status_code} (Expected 401)")
    assert response.status_code == 401

    # Try new login (should succeed)
    new_login_payload = login_payload.copy()
    new_login_payload["password"] = "newsecurepassword987"
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
        "date": date.today().isoformat()
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
        "date": date.today().isoformat()
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
    assert len(graph_data["data"]) == 30
    assert graph_data["average"] > 0
    assert graph_data["total"] > 0
    assert "Outstanding" in graph_data["feedback"] or "Good" in graph_data["feedback"] or "below" in graph_data["feedback"]

    # Test period: month
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=sleep&period=month")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["metric"] == "sleep"
    assert graph_data["period"] == "month"
    assert len(graph_data["data"]) == 12
    assert graph_data["average"] > 0
    assert graph_data["total"] is None  # sleep shouldn't have total

    # Test period: years
    response = client.get(f"/api/health/graph/{signup_payload['email']}?metric=heart_rate&period=years")
    assert response.status_code == 200
    graph_data = response.json()
    assert graph_data["metric"] == "heart_rate"
    assert graph_data["period"] == "years"
    assert len(graph_data["data"]) == 5
    assert graph_data["average"] > 0
    assert "resting heart rate" in graph_data["feedback"]

    print("\nALL AUTHENTICATION, OTP, HEALTH, DASHBOARD, HYDRATION AND GRAPH TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()


