import json
from datetime import datetime, timezone
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

    print("\nALL AUTHENTICATION AND OTP TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

